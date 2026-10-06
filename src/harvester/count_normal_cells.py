#!/usr/bin/env python3
"""
Step 5: Count cells for each dataset using the CellxGene Census

Reads the folder of <dataset_id>.filtered.json files written by Step 4. For
each dataset that is not counted yet, reads the Census obs table for the whole
dataset, then fills in both sides of every pair:

  source_X   : all cells of the dataset in Census
  filtered_X : the cells whose tissue id is in the uberon file, whose disease
               id is in the disease file, and whose development stage id is in
               the hsapdv file

for the cell count, the donor count, and the six facets tissue, assay,
cell_type, disease, development_stage and sex. Each facet has labels, ontology
ids, and a summary of ids and cell counts. Only values that occur in the cells
are counted. A filtered_ summary has the same ids as the source_ summary, with
0 for an id whose cells were all removed by the filter.

NOTE (2026-10-05): is_primary_data == True is NOT used as a filter. It is an
unreliable filter at this time, so it is not read from Census and does not
change any count. Revisit this decision before using it.

Opens Census ONCE and reuses the connection for all datasets. Each file is
written as soon as its dataset is counted. A file that already has a
filtered_cell_count is skipped, so a stopped run can be started again.

Usage:
1. Python module execution:
python -m harvester.count_normal_cells \
        2026-08-03-run/homo_sapiens_kidney_harvester \
        --uberon  2026-08-03-run/uberon_kidney.json \
        --disease 2026-08-03-run/disease_normal.json \
        --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
        --exclude-assay 2026-08-03-run/assay_spatial.json \
        --census-version latest
2. CLI command (after pip install -e .):
cellxgene-harvester count-normal-cells 2026-08-03-run/homo_sapiens_kidney_harvester \
        --uberon  2026-08-03-run/uberon_kidney.json \
        --disease 2026-08-03-run/disease_normal.json \
        --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
        --exclude-assay 2026-08-03-run/assay_spatial.json \
        --census-version latest

--exclude-assay is optional: a file from resolve-assay. The cells whose assay
ontology id is in it are left out of the filtered counts (a negative
selection, for example to leave out spatial techniques). They stay in the
source counts.

--census-version is optional and defaults to latest. The release that was
used is recorded in each file.
"""

import glob
import os
import sys
import traceback

from harvester import ontology_files
from harvester.io_utils import FACETS, load_json, write_json
from harvester.logger import setup_logger, log_command, log_finish

CENSUS_VERSION = "latest"
FILTER_FILES = ("uberon", "disease", "hsapdv", "exclude_assay")


def id_column(facet):
    return f"{facet}_ontology_term_id"


def census_columns():
    """The Census obs columns that are read."""
    columns = ["donor_id"]
    for facet in FACETS:
        columns += [facet, id_column(facet)]
    return columns


def read_obs(census, dataset_id):
    """Read the obs table of one whole dataset. The expression matrix is not read."""
    obs = census["census_data"]["homo_sapiens"].obs
    table = obs.read(value_filter=f"dataset_id == '{dataset_id}'",
                     column_names=census_columns())
    return table.concat().to_pandas()


def count_facet(obs, facet):
    """Return (labels, ids, summary) for one facet over the cells in obs.

    Labels and ids are sorted lists of the values that occur. The summary
    maps each id to its number of cells, largest first. A value that does not
    occur is not listed.
    """
    ids = obs[id_column(facet)].dropna().astype(str)
    counts = sorted(ids.value_counts().items(), key=lambda pair: (-pair[1], pair[0]))
    labels = sorted(obs[facet].dropna().astype(str).unique())
    return labels, sorted(name for name, _ in counts), {name: int(n) for name, n in counts}


def describe_cells(obs):
    """Count the cells, the donors and the six facets of the cells in obs."""
    return {
        "cell_count": len(obs),
        "donor_count": int(obs["donor_id"].nunique()),
        "facets": {facet: count_facet(obs, facet) for facet in FACETS},
    }


def keep_matching(obs, uberon_ids, disease_ids, hsapdv_ids, exclude_assay_ids=frozenset()):
    """Keep the cells that pass the tissue, disease and age filters, and whose
    assay is not in exclude_assay_ids.

    is_primary_data is not a filter here. It is unreliable at this time
    (decision of 2026-10-05), so it is not read and not used.
    """
    return obs[obs[id_column("tissue")].isin(uberon_ids)
               & obs[id_column("disease")].isin(disease_ids)
               & obs[id_column("development_stage")].isin(hsapdv_ids)
               & ~obs[id_column("assay")].isin(exclude_assay_ids)]


def api_values(record):
    """The source_ values that Step 4 took from the CellxGene API."""
    return {
        "tissue ids": sorted(record["source_tissue_ontology_id"]),
        "disease ids": sorted(record["source_disease_ontology_id"]),
        "cell count": record["source_cell_count"],
    }


def fill_record(record, obs, uberon_ids, disease_ids, hsapdv_ids, exclude_assay_ids=frozenset()):
    """Fill both sides of every pair in the record from the cells in obs.

    Return a list of messages about values that differ from what Step 4
    wrote: the API tissue ids, the API disease ids and the API cell count.
    """
    before = api_values(record)

    source = describe_cells(obs)
    kept = describe_cells(keep_matching(obs, uberon_ids, disease_ids, hsapdv_ids, exclude_assay_ids))

    record["source_cell_count"] = source["cell_count"]
    record["filtered_cell_count"] = kept["cell_count"]
    record["source_donor_count"] = source["donor_count"]
    record["filtered_donor_count"] = kept["donor_count"]

    for facet in FACETS:
        labels, ids, summary = source["facets"][facet]
        kept_labels, kept_ids, kept_summary = kept["facets"][facet]
        record[f"source_{facet}"] = labels
        record[f"filtered_{facet}"] = kept_labels
        record[f"source_{facet}_ontology_id"] = ids
        record[f"filtered_{facet}_ontology_id"] = kept_ids
        record[f"source_{facet}_ontology_id_summary"] = summary
        record[f"filtered_{facet}_ontology_id_summary"] = {
            name: kept_summary.get(name, 0) for name in summary}

    after = api_values(record)
    return [f"Census {name} {after[name]} differ from the Step 4 (API) value {before[name]}"
            for name in before if before[name] and before[name] != after[name]]


def record_filter_files(record, paths, census_label):
    """Record the filter files used in this step. Return messages about any
    file that is not the one recorded in Step 4."""
    messages = []
    choices = record["filter_choices"]
    choices.pop("exclude_assay", None)
    for name in FILTER_FILES:
        if not paths.get(name):
            continue
        current = ontology_files.describe(paths[name])
        recorded = choices.get(name)
        if recorded and recorded["sha256"] != current["sha256"]:
            messages.append(f"{name} file {paths[name]} is not the file recorded in Step 4 "
                            f"({recorded['file']}); the file in use is now recorded")
        choices[name] = current
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
                                ids["exclude_assay"])
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


def list_files(folder):
    return sorted(glob.glob(os.path.join(folder, "*.filtered.json")))


def is_counted(path):
    return load_json(path)["filtered_cell_count"] is not None


def process_folder(folder, uberon_json, disease_json, hsapdv_json, logger,
                   exclude_assay_json=None, census_version=CENSUS_VERSION):
    import cellxgene_census

    paths = {"uberon": uberon_json, "disease": disease_json, "hsapdv": hsapdv_json,
             "exclude_assay": exclude_assay_json}
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


# =============================================================================
# run_count_normal_cells
# =============================================================================
def run_count_normal_cells(
        folder:       str,
        uberon_json:  str,
        disease_json: str,
        hsapdv_json:  str,
        exclude_assay_json: str = None,
        census_version:     str = CENSUS_VERSION,
    ):
    """Main entry point called by CLI"""
    folder = folder.rstrip("/")
    logger = setup_logger("5_count_normal_cells", output_csv=f"{folder}.count.log")
    log_command(logger)
    logger.info(f"UBERON file  : {uberon_json}")
    logger.info(f"Disease file : {disease_json}")
    logger.info(f"HsapDv file  : {hsapdv_json}")
    logger.info(f"Exclude assay: {exclude_assay_json or 'none'}")
    logger.info(f"Census       : {census_version}")
    logger.info(f"Folder       : {folder}\n")

    try:
        import cellxgene_census  # noqa: F401
    except ImportError:
        logger.error("ERROR: cellxgene_census not found")
        sys.exit(1)

    process_folder(folder, uberon_json, disease_json, hsapdv_json, logger,
                   exclude_assay_json, census_version)
    log_finish(logger, folder)
