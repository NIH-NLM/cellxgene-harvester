#!/usr/bin/env python3
"""
Step 7: Export the datasets CSV that sc-nsforest-qc-nf reads

Reads the folder of <dataset_id>.filtered.json files (after Step 6) and writes
one CSV with a row for each dataset that has cells after filtering. The CSV
holds only the fields that sc-nsforest-qc-nf uses. The JSON files stay the full
record, for the consumers that read JSON.

Datasets whose filtered_cell_count is 0 or empty are left out, and the empty
ones are listed in the log.

Usage:
1. Python module execution:
python -m harvester.export_datasets_csv 2026-08-03-run/homo_sapiens_kidney_harvester \
        --output 2026-08-03-run/homo_sapiens_kidney_nsforest_datasets.csv

2. CLI command (after pip install -e .):
cellxgene-harvester export-datasets-csv 2026-08-03-run/homo_sapiens_kidney_harvester \
        --output 2026-08-03-run/homo_sapiens_kidney_nsforest_datasets.csv
"""

import glob
import os

from harvester.io_utils import load_json, write_csv
from harvester.logger import setup_logger, log_command, log_counts, log_finish

# sc-nsforest-qc-nf reads these columns by name.
COLUMNS = [
    "reference", "collection_name", "dataset_title", "author_cell_type", "embedding",
    "first_author", "journal", "year", "doi", "collection_url", "explorer_url",
    "disease", "dataset_id", "dataset_version_id", "filter_normal", "h5ad_url",
]

# sc-nsforest-qc-nf passes the disease column to scsilhouette as one text, as
# the Step 2 CSV wrote it: the labels joined with " | ". This is the only
# place a list is joined back into text.
DISEASE_JOIN = " | "


def list_files(folder):
    return sorted(glob.glob(os.path.join(folder, "*.filtered.json")))


def text(value):
    """Empty cells are empty text, not "None"."""
    return "" if value is None else str(value)


def flag(value):
    """True and False as the text True and False; None as empty text.

    sc-nsforest-qc-nf applies its disease and age filters when this text is
    exactly True.
    """
    return "" if value is None else str(value)


def to_row(record):
    """The CSV row of one dataset record."""
    dataset = record["dataset"]
    curation = record["curation"]
    return {
        "reference": text(curation["reference"]),
        "collection_name": text(dataset["collection_name"]),
        "dataset_title": text(dataset["dataset_title"]),
        "author_cell_type": text(curation["author_cell_type"]),
        "embedding": text(curation["embedding"]),
        "first_author": text(dataset["first_author"]),
        "journal": text(dataset["journal"]),
        "year": text(dataset["year"]),
        "doi": text(dataset["doi"]),
        "collection_url": text(dataset["collection_url"]),
        "explorer_url": text(dataset["explorer_url"]),
        "disease": DISEASE_JOIN.join(record["source_disease"]),
        "dataset_id": text(dataset["dataset_id"]),
        "dataset_version_id": text(dataset["dataset_version_id"]),
        "filter_normal": flag(record["curation"]["filter_normal"]),
        "h5ad_url": text(dataset["h5ad_url"]),
    }


def select_records(paths, logger):
    """Return the records with cells after filtering. Log each one left out."""
    kept = []
    for path in paths:
        record = load_json(path)
        count = record["filtered_cell_count"]
        if count is None:
            logger.warning(f"  NOT COUNTED, left out : {os.path.basename(path)}")
        elif count > 0:
            kept.append(record)
        else:
            logger.info(f"  0 filtered cells, left out : {os.path.basename(path)}")
    return kept


def export_folder(folder, output_csv, logger):
    """Write the CSV. Return the number of datasets written."""
    paths = list_files(folder)
    records = select_records(paths, logger)
    log_counts(logger, "datasets with filtered cells", before=len(paths), after=len(records))
    empty = [r["dataset"]["dataset_id"] for r in records if r["curation"]["filter_normal"] is None]
    if empty:
        logger.warning(f"  WARNING: filter_normal is empty for {len(empty)} datasets. "
                       f"Set it to true or false in the curation block of each JSON file. "
                       f"sc-nsforest-qc-nf applies its disease and age filters only when it is True.")
    write_csv(output_csv, COLUMNS, [to_row(r) for r in records])
    return len(records)


# =============================================================================
# run_export_datasets_csv
# =============================================================================
def run_export_datasets_csv(folder: str, output_csv: str):
    """Main entry point called by CLI"""
    folder = folder.rstrip("/")
    logger = setup_logger("7_export_datasets_csv", output_csv=output_csv)
    log_command(logger)
    export_folder(folder, output_csv, logger)
    log_finish(logger, output_csv)
