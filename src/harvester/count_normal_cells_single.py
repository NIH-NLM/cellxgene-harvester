#!/usr/bin/env python3
"""
Step 5 (single dataset): Count cells for one dataset via the CellxGene Census.

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
        --exclude-assay 2026-08-03-run/assay_spatial.json \
        --census-version latest
"""

import argparse
import sys

from harvester import ontology_files
from harvester.count_normal_cells import CENSUS_VERSION, count_one
from harvester.logger import setup_logger, log_command, log_finish


def count_single(record_path, uberon_json, disease_json, hsapdv_json, logger,
                 exclude_assay_json=None, census_version=CENSUS_VERSION):
    """Count the one dataset in record_path. Return True if it was counted."""
    import cellxgene_census

    paths = {"uberon": uberon_json, "disease": disease_json, "hsapdv": hsapdv_json,
             "exclude_assay": exclude_assay_json}
    ids = {name: ontology_files.load_obo_ids(path) if path else set() for name, path in paths.items()}

    with cellxgene_census.open_soma(census_version=census_version) as census:
        description = cellxgene_census.get_census_version_description(census_version)
        census_label = description.get("release_build", census_version)
        return count_one(record_path, census, census_label, ids, paths, logger)


def main():
    parser = argparse.ArgumentParser(
        description="Count cells for one dataset file via the CellxGene Census")
    parser.add_argument("--record",  required=True, help="<dataset_id>.filtered.json from step 4")
    parser.add_argument("--uberon",  required=True, help="UBERON JSON from resolve-uberon")
    parser.add_argument("--disease", required=True, help="Disease JSON from resolve-disease")
    parser.add_argument("--hsapdv",  required=True, help="HsapDv JSON from resolve-hsapdv")
    parser.add_argument("--exclude-assay", default=None, help="Assay JSON from resolve-assay: its cells are left out of the filtered counts")
    parser.add_argument("--census-version", default=CENSUS_VERSION, help="Census release (default: latest)")
    args = parser.parse_args()

    logger = setup_logger("5_count_single", output_csv=f"{args.record}.count.log")
    log_command(logger)

    try:
        import cellxgene_census  # noqa: F401
    except ImportError:
        logger.error("ERROR: cellxgene_census not installed")
        sys.exit(1)

    counted = count_single(args.record, args.uberon, args.disease, args.hsapdv, logger,
                           args.exclude_assay, args.census_version)
    log_finish(logger, args.record)
    sys.exit(0 if counted else 1)


if __name__ == "__main__":
    main()
