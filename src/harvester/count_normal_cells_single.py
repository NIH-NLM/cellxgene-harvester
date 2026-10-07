#!/usr/bin/env python3
"""
Step 5 (single dataset): Count cells for one dataset from its h5ad file (or the Census).

Does for one <dataset_id>.filtered.json file what count_normal_cells does for
a whole folder, with the same counting code. Meant for running one dataset at
a time, for example as one Nextflow process per dataset.

The file is updated in place. Exit code 1 if the dataset could not be counted.

Usage:
    python -m harvester.count_normal_cells_single \
        --record  2026-08-03-run/homo_sapiens_kidney_harvester/066943a2-fdac-4b29-b348-40cede398e4e.filtered.json \
        --uberon  2026-08-03-run/uberon_kidney.json \
        --disease 2026-08-03-run/disease_normal.json \
        --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
        --assay 2026-08-03-run/assay_published.json \
        --h5ad-out 2026-08-03-run/homo_sapiens_kidney_harvester_h5ad \
        --h5ad-url-prefix s3://my-public-bucket/prod/kidney

--h5ad reads a local file instead of the address in the record (the Nextflow
workflow stages the file this way). --source census reads the Census instead.
"""

import argparse
import sys
import tempfile

from harvester import ontology_files
from harvester.count_normal_cells import CENSUS_VERSION, count_one, count_one_h5ad
from harvester.logger import setup_logger, log_command, log_finish


def count_single(record_path, uberon_json, disease_json, hsapdv_json, logger,
                 assay_json=None, census_version=CENSUS_VERSION):
    """Count the one dataset in record_path. Return True if it was counted."""
    import cellxgene_census

    paths = {"uberon": uberon_json, "disease": disease_json, "hsapdv": hsapdv_json,
             "assay": assay_json}
    ids = {name: ontology_files.load_obo_ids(path) if path else set() for name, path in paths.items()}

    with cellxgene_census.open_soma(census_version=census_version) as census:
        description = cellxgene_census.get_census_version_description(census_version)
        census_label = description.get("release_build", census_version)
        return count_one(record_path, census, census_label, ids, paths, logger)


def count_single_h5ad(record_path, uberon_json, disease_json, hsapdv_json, logger,
                      assay_json=None, out_dir=None, url_prefix=None, h5ad=None):
    """Count the one dataset in record_path from its h5ad file. Return True if counted."""
    paths = {"uberon": uberon_json, "disease": disease_json, "hsapdv": hsapdv_json,
             "assay": assay_json}
    ids = {name: ontology_files.load_obo_ids(path) if path else set() for name, path in paths.items()}
    with tempfile.TemporaryDirectory() as workdir:
        return count_one_h5ad(record_path, ids, paths, logger, workdir, out_dir or "filtered_h5ad",
                              url_prefix, h5ad)


def main():
    parser = argparse.ArgumentParser(
        description="Count cells for one dataset file via the CellxGene Census")
    parser.add_argument("--record",  required=True, help="<dataset_id>.filtered.json from step 4")
    parser.add_argument("--uberon",  required=True, help="UBERON JSON from resolve-uberon")
    parser.add_argument("--disease", required=True, help="Disease JSON from resolve-disease")
    parser.add_argument("--hsapdv",  required=True, help="HsapDv JSON from resolve-hsapdv")
    parser.add_argument("--assay", default=None, help="Assay JSON from resolve-assay: only the cells of these assays are counted on the filtered side")
    parser.add_argument("--source", choices=["h5ad", "census"], default="h5ad",
                        help="Where the cells are read (default: h5ad)")
    parser.add_argument("--h5ad", default=None, help="Local h5ad file to read instead of the record's h5ad_url")
    parser.add_argument("--h5ad-out", default="filtered_h5ad", help="Folder for the filtered h5ad file")
    parser.add_argument("--h5ad-url-prefix", default=None, help="Public address where the filtered file is published")
    parser.add_argument("--census-version", default=CENSUS_VERSION, help="Census release, with --source census (default: latest)")
    args = parser.parse_args()

    logger = setup_logger("5_count_single", output_csv=f"{args.record}.count.log")
    log_command(logger)

    if args.source == "census":
        try:
            import cellxgene_census  # noqa: F401
        except ImportError:
            logger.error("ERROR: cellxgene_census not installed")
            sys.exit(1)
        counted = count_single(args.record, args.uberon, args.disease, args.hsapdv, logger,
                               args.assay, args.census_version)
    else:
        counted = count_single_h5ad(args.record, args.uberon, args.disease, args.hsapdv, logger,
                                    args.assay, args.h5ad_out, args.h5ad_url_prefix, args.h5ad)
    log_finish(logger, args.record)
    sys.exit(0 if counted else 1)


if __name__ == "__main__":
    main()
