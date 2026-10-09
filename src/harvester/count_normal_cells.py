#!/usr/bin/env python3
"""
Step 5: Count cells for each dataset, and write the filtered cells to an h5ad file

Reads the folder of <dataset_id>.filtered.json files written by Step 4. For
each dataset that is not counted yet, reads the cells of the dataset, then
fills in both sides of every pair:

  source_X   : all cells of the dataset
  filtered_X : the cells whose tissue id is in the uberon file, whose disease
               id is in the disease file, whose development stage id is in
               the hsapdv file and, when an assay file is given, whose assay id
               is in it (the same choices recorded in Step 4)

The cells come from the dataset's h5ad file (--source h5ad, the default): the
address in the dataset's h5ad_url, a local path or an http(s) address. Only the
metadata is read into memory. The cells that pass the filters are written to
<h5ad-out>/<dataset_id>.filtered.h5ad, and filtered_h5ad_url in the JSON file
says where that file is published. With --h5ad-url-prefix it is
<prefix>/<dataset_id>.filtered.h5ad; without it, the path of the file written.
sc-nsforest-qc-nf reads this filtered file. A dataset with no cells after
filtering gets no file and a filtered_h5ad_url of null.

With --source census the counts are read from the CellxGene Census instead.
Nothing is written then and filtered_h5ad_url stays null.

for the cell count, the donor count, and the six facets tissue, assay,
cell_type, disease, development_stage and sex. Each facet is a list of term
objects {"ontology_id", "label", "source_count"} (and "filtered_count" on the
filtered side). Only values that occur in the cells are counted. The terms are
ordered by cell count, largest first, then by id. A filtered_ list has the same
terms in the same order as the source_ list, with 0 for a term whose cells were
all removed by the filters.

NOTE (2026-10-05): is_primary_data == True is NOT used as a filter. It is an
unreliable filter at this time, so it is not read from Census and does not
change any count. Revisit this decision before using it.

With --source census, Census is opened ONCE and the connection is reused for
all datasets. Each file is written as soon as its dataset is counted. A file that already has a
filtered_cell_count is skipped, so a stopped run can be started again.

Usage:
1. Python module execution:
python -m harvester.count_normal_cells \
        2026-08-03-run/homo_sapiens_kidney_harvester \
        --uberon  2026-08-03-run/uberon_kidney.json \
        --disease 2026-08-03-run/disease_normal.json \
        --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
        --assay 2026-08-03-run/assay_published.json \
        --h5ad-out 2026-08-03-run/homo_sapiens_kidney_harvester_h5ad \
        --h5ad-url-prefix s3://my-public-bucket/prod/kidney
2. CLI command (after pip install -e .):
cellxgene-harvester count-normal-cells 2026-08-03-run/homo_sapiens_kidney_harvester \
        --uberon  2026-08-03-run/uberon_kidney.json \
        --disease 2026-08-03-run/disease_normal.json \
        --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
        --assay 2026-08-03-run/assay_published.json \
        --h5ad-out 2026-08-03-run/homo_sapiens_kidney_harvester_h5ad \
        --h5ad-url-prefix s3://my-public-bucket/prod/kidney

--assay is optional: a file from resolve-assay that lists the assays you want.
When it is given, only the cells whose assay ontology id is in it are counted
on the filtered side. Every other assay, for example every spatial technique,
is left out by not being in the file. The cells of the other assays stay in the
source counts. Without --assay no assay is left out.

--census-version is used only with --source census. It defaults to latest, and
the release that was used is recorded in each file.
"""

import glob
import os
import sys
import tempfile
import traceback

import pandas as pd

from harvester import ontology_files
from harvester.h5ad_source import (fetch_h5ad, id_column, obs_columns, open_h5ad,
                                   read_obs as read_h5ad_obs, write_filtered)
from harvester.io_utils import FACETS, load_json, terms_from, write_json
from harvester.logger import setup_logger, log_command, log_finish

CENSUS_VERSION = "latest"
FILTER_FILES = ("uberon", "disease", "hsapdv", "assay")


def census_columns():
    """The Census obs columns that are read: the same as the h5ad obs columns."""
    return obs_columns()


def read_obs(census, dataset_id):
    """Read the obs table of one whole dataset. The expression matrix is not read."""
    obs = census["census_data"]["homo_sapiens"].obs
    table = obs.read(value_filter=f"dataset_id == '{dataset_id}'",
                     column_names=census_columns())
    return table.concat().to_pandas()


def count_terms(obs, facet):
    """Return {ontology id: (label, cell count)} for one facet over the cells in obs.

    The terms are ordered by cell count, largest first, then by id. A label is
    the one most cells of that id carry. A value that does not occur is not listed.
    """
    frame = pd.DataFrame({"id": obs[id_column(facet)].astype("object"),
                          "label": obs[facet].astype("object")}).dropna(subset=["id"])
    frame["id"] = frame["id"].astype(str)
    counts = frame.groupby("id").size()
    labelled = frame.dropna(subset=["label"])
    label_of = labelled.groupby("id")["label"].agg(lambda s: str(s.value_counts().index[0]))
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return {name: (label_of.get(name), int(n)) for name, n in ordered}


def describe_cells(obs):
    """Count the cells, the donors and the terms of the six facets of the cells in obs."""
    return {
        "cell_count": len(obs),
        "donor_count": int(obs["donor_id"].nunique()),
        "facets": {facet: count_terms(obs, facet) for facet in FACETS},
    }


def keep_mask(obs, uberon_ids, disease_ids, hsapdv_ids, assay_ids=frozenset()):
    """True for each cell that passes the tissue, disease and age filters and,
    when assay_ids is not empty, whose assay is in it.

    is_primary_data is not a filter here. It is unreliable at this time
    (decision of 2026-10-05), so it is not read and not used.
    """
    keep = (obs[id_column("tissue")].isin(uberon_ids)
            & obs[id_column("disease")].isin(disease_ids)
            & obs[id_column("development_stage")].isin(hsapdv_ids))
    if assay_ids:
        keep &= obs[id_column("assay")].isin(assay_ids)
    return keep


def keep_matching(obs, uberon_ids, disease_ids, hsapdv_ids, assay_ids=frozenset()):
    """The cells of obs that keep_mask keeps."""
    return obs[keep_mask(obs, uberon_ids, disease_ids, hsapdv_ids, assay_ids)]


def api_values(record):
    """The source_ values that Step 4 took from the CellxGene API."""
    return {
        "tissue ids": sorted(term["ontology_id"] for term in record["source_tissue"]),
        "disease ids": sorted(term["ontology_id"] for term in record["source_disease"]),
        "cell count": record["source_cell_count"],
    }


def fill_record(record, obs, uberon_ids, disease_ids, hsapdv_ids, assay_ids=frozenset()):
    """Fill both sides of every pair in the record from the cells in obs.

    Return a list of messages about values that differ from what Step 4
    wrote: the API tissue ids, the API disease ids and the API cell count.
    """
    before = api_values(record)

    source = describe_cells(obs)
    kept = describe_cells(keep_matching(obs, uberon_ids, disease_ids, hsapdv_ids, assay_ids))

    record["source_cell_count"] = source["cell_count"]
    record["filtered_cell_count"] = kept["cell_count"]
    record["source_donor_count"] = source["donor_count"]
    record["filtered_donor_count"] = kept["donor_count"]

    for facet in FACETS:
        source_terms = source["facets"][facet]
        kept_counts = kept["facets"][facet]
        # the filtered list has the same terms in the same order, with 0 for a term
        # whose cells were all removed by the filters
        record[f"source_{facet}"] = terms_from("source", source_terms)
        record[f"filtered_{facet}"] = terms_from(
            "filtered", {name: (label, kept_counts.get(name, (None, 0))[1])
                         for name, (label, _) in source_terms.items()})

    after = api_values(record)
    return [f"Counted {name} {after[name]} differ from the Step 4 (API) value {before[name]}"
            for name in before if before[name] and before[name] != after[name]]


def record_filter_files(record, paths, census_label=None):
    """Record the filter files used in this step. Return messages about any
    file that is not the one recorded in Step 4. A census label is recorded
    only when the cells are read from the Census."""
    messages = []
    choices = record["filter_choices"]
    for name in FILTER_FILES:
        if not paths.get(name):
            if choices.get(name):
                messages.append(f"{name} file {choices[name]['file']} was chosen in Step 4 "
                                f"but no {name} file is given here")
            continue
        current = ontology_files.describe(paths[name])
        recorded = choices.get(name)
        if recorded and recorded["sha256"] != current["sha256"]:
            messages.append(f"{name} file {paths[name]} is not the file recorded in Step 4 "
                            f"({recorded['file']}); the file in use is now recorded")
        choices[name] = current
    if census_label is not None:
        choices["census_version"] = census_label
    return messages


def count_one(path, census, census_label, ids, paths, logger):
    """Count one dataset and write its file. Return True if it was counted."""
    record = load_json(path)
    dataset_id = record["dataset"]["dataset_id"]
    try:
        messages = record_filter_files(record, paths, census_label)
        logger.info("    Reading the Census obs table for the whole dataset...")
        obs = read_obs(census, dataset_id)
        logger.info(f"    Census returned {len(obs)} cells")
        messages += fill_record(record, obs, ids["uberon"], ids["disease"], ids["hsapdv"],
                                ids["assay"])
        write_json(path, record)
    except Exception as e:
        logger.error(f"    ERROR: {e}")
        logger.error(traceback.format_exc())
        return False

    for message in messages:
        logger.warning(f"    WARNING: {message}")
    logger.info(f"    {record['filtered_cell_count']} of {record['source_cell_count']} "
                f"cells pass the filters")
    return True


def count_one_h5ad(path, ids, paths, logger, workdir, out_dir, url_prefix=None, h5ad=None):
    """Count one dataset from its h5ad file and write its file. Return True if it
    was counted.

    The cells are read from h5ad if given, else from the address in the
    dataset's h5ad_url (a local path or an http(s) address, which is downloaded
    into workdir and deleted afterwards). The cells that pass the filters are
    written to out_dir/<dataset_id>.filtered.h5ad.
    """
    record = load_json(path)
    dataset = record["dataset"]
    location = h5ad or dataset["h5ad_url"]
    adata, local, downloaded = None, None, False
    try:
        messages = record_filter_files(record, paths)
        logger.info(f"    Reading {location}")
        local, downloaded = fetch_h5ad(location, workdir)
        adata = open_h5ad(local)
        obs = read_h5ad_obs(adata)
        logger.info(f"    The file has {len(obs)} cells")
        messages += fill_record(record, obs, ids["uberon"], ids["disease"], ids["hsapdv"],
                                ids["assay"])

        record["filtered_h5ad_url"] = None
        if record["filtered_cell_count"] > 0:
            name = f"{dataset['dataset_id']}.filtered.h5ad"
            mask = keep_mask(obs, ids["uberon"], ids["disease"], ids["hsapdv"], ids["assay"])
            write_filtered(adata, mask.to_numpy(), os.path.join(out_dir, name))
            record["filtered_h5ad_url"] = (f"{url_prefix.rstrip('/')}/{name}" if url_prefix
                                           else os.path.join(out_dir, name))
            logger.info(f"    Wrote {record['filtered_cell_count']} cells to {os.path.join(out_dir, name)}")

        choices = record["filter_choices"]
        choices.pop("census_version", None)
        choices["h5ad"] = {"file": os.path.basename(location)}
        write_json(path, record)
    except Exception as e:
        logger.error(f"    ERROR: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        if adata is not None and adata.isbacked:
            adata.file.close()
        if downloaded and local and os.path.exists(local):
            os.remove(local)

    for message in messages:
        logger.warning(f"    WARNING: {message}")
    logger.info(f"    {record['filtered_cell_count']} of {record['source_cell_count']} "
                f"cells pass the filters")
    return True


def list_files(folder):
    return sorted(glob.glob(os.path.join(folder, "*.filtered.json")))


def is_counted(path):
    return load_json(path)["filtered_cell_count"] is not None


def process_folder(folder, uberon_json, disease_json, hsapdv_json, logger,
                   assay_json=None, census_version=CENSUS_VERSION):
    import cellxgene_census

    paths = {"uberon": uberon_json, "disease": disease_json, "hsapdv": hsapdv_json,
             "assay": assay_json}
    ids = {name: ontology_files.load_obo_ids(path) if path else set() for name, path in paths.items()}

    files = list_files(folder)
    done = [p for p in files if is_counted(p)]
    logger.info(f"Datasets in {folder}: {len(files)}")
    logger.info(f"Already counted     : {len(done)}\n")

    stats = {"counted": 0, "failed": 0}
    logger.info("Opening Census connection (once for all datasets)...")
    with cellxgene_census.open_soma(census_version=census_version) as census:
        description = cellxgene_census.get_census_version_description(census_version)
        census_label = description.get("release_build", census_version)
        logger.info(f"Census connection open (release {census_label})\n")

        for i, path in enumerate(files, 1):
            if path in done:
                continue
            logger.info(f"[{i}/{len(files)}] {os.path.basename(path)}")
            counted = count_one(path, census, census_label, ids, paths, logger)
            stats["counted" if counted else "failed"] += 1

    logger.info(f"\n{'='*70}")
    logger.info(f"  Already counted : {len(done)}")
    logger.info(f"  Newly counted   : {stats['counted']}")
    logger.info(f"  Failed          : {stats['failed']}")


def process_folder_h5ad(folder, uberon_json, disease_json, hsapdv_json, logger,
                        assay_json=None, out_dir=None, url_prefix=None):
    """Count every dataset of the folder from its h5ad file."""
    paths = {"uberon": uberon_json, "disease": disease_json, "hsapdv": hsapdv_json,
             "assay": assay_json}
    ids = {name: ontology_files.load_obo_ids(path) if path else set() for name, path in paths.items()}
    out_dir = out_dir or f"{folder}_h5ad"

    files = list_files(folder)
    done = [p for p in files if is_counted(p)]
    logger.info(f"Datasets in {folder}: {len(files)}")
    logger.info(f"Already counted     : {len(done)}")
    logger.info(f"Filtered h5ad files : {out_dir}\n")

    stats = {"counted": 0, "failed": 0}
    with tempfile.TemporaryDirectory() as workdir:
        for i, path in enumerate(files, 1):
            if path in done:
                continue
            logger.info(f"[{i}/{len(files)}] {os.path.basename(path)}")
            counted = count_one_h5ad(path, ids, paths, logger, workdir, out_dir, url_prefix)
            stats["counted" if counted else "failed"] += 1

    logger.info(f"\n{'='*70}")
    logger.info(f"  Already counted : {len(done)}")
    logger.info(f"  Newly counted   : {stats['counted']}")
    logger.info(f"  Failed          : {stats['failed']}")


# =============================================================================
# run_count_normal_cells
# =============================================================================
def run_count_normal_cells(
        folder:       str,
        uberon_json:  str,
        disease_json: str,
        hsapdv_json:  str,
        assay_json: str = None,
        census_version:     str = CENSUS_VERSION,
        source:             str = "h5ad",
        h5ad_out:           str = None,
        h5ad_url_prefix:    str = None,
    ):
    """Main entry point called by CLI"""
    folder = folder.rstrip("/")
    logger = setup_logger("5_count_normal_cells", output_csv=f"{folder}.count.log")
    log_command(logger)
    logger.info(f"UBERON file  : {uberon_json}")
    logger.info(f"Disease file : {disease_json}")
    logger.info(f"HsapDv file  : {hsapdv_json}")
    logger.info(f"Assay file   : {assay_json or 'none'}")
    logger.info(f"Cells from   : {source}")
    logger.info(f"Folder       : {folder}\n")

    if source == "h5ad":
        process_folder_h5ad(folder, uberon_json, disease_json, hsapdv_json, logger,
                            assay_json, h5ad_out, h5ad_url_prefix)
    elif source == "census":
        logger.info(f"Census       : {census_version}")
        try:
            import cellxgene_census  # noqa: F401
        except ImportError:
            logger.error("ERROR: cellxgene_census not found")
            sys.exit(1)
        process_folder(folder, uberon_json, disease_json, hsapdv_json, logger,
                       assay_json, census_version)
    else:
        logger.error(f"ERROR: --source must be h5ad or census, not {source}")
        sys.exit(1)
    log_finish(logger, folder)
