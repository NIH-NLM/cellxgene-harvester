#!/usr/bin/env python3
"""
Step 7: Export the final CSV and the final JSON

Reads the folder of <dataset_id>.filtered.json files (after Step 6) and writes,
side by side, with the same name apart from the ending:

  homo_sapiens_kidney_harvester_final.csv   one row for each dataset that has
        cells after filtering; the fields that sc-nsforest-qc-nf uses, and the organ
        block of the JSON (organ, organ_uberon_id) so a table says which organ its
        rows belong to
  homo_sapiens_kidney_harvester_final.json  one JSON array with the full record
        of the same datasets, in the same order, for the consumers that read JSON

Datasets whose filtered_cell_count is 0 or empty are left out, and the empty
ones are listed in the log.

The JSON file is named like the CSV, with .json in place of .csv, unless
--output-json gives another path.

Usage:
1. Python module execution:
python -m harvester.export_datasets_csv 2026-08-03-run/homo_sapiens_kidney_harvester \
        --output 2026-08-03-run/homo_sapiens_kidney_harvester_final.csv

2. CLI command (after pip install -e .):
cellxgene-harvester export-datasets-csv 2026-08-03-run/homo_sapiens_kidney_harvester \
        --output 2026-08-03-run/homo_sapiens_kidney_harvester_final.csv
"""

import glob
import os

from harvester.io_utils import load_json, write_csv, write_json_list
from harvester.logger import setup_logger, log_command, log_counts, log_finish

# sc-nsforest-qc-nf reads these columns by name.
COLUMNS = [
    "reference", "collection_name", "dataset_title", "author_cell_type", "embedding",
    "first_author", "journal", "year", "doi", "collection_url", "explorer_url",
    "disease", "dataset_id", "dataset_version_id", "h5ad_url",
    "organ", "organ_uberon_id",
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


def to_row(record):
    """The CSV row of one dataset record."""
    dataset = record["dataset"]
    curation = record["curation"]
    organ = record.get("organ") or {}
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
        "disease": DISEASE_JOIN.join(sorted(
            term["label"] for term in record["source_disease"] if term["label"])),
        "dataset_id": text(dataset["dataset_id"]),
        "dataset_version_id": text(dataset["dataset_version_id"]),
        "h5ad_url": text(record.get("filtered_h5ad_url") or dataset["h5ad_url"]),
        # the organ block of the JSON, so a table says which organ its rows belong to
        "organ": text(organ.get("name")),
        "organ_uberon_id": text(organ.get("uberon_id")),
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
            if not record.get("filtered_h5ad_url"):
                logger.warning(f"  NO filtered h5ad, the original CellxGene URL is used : "
                               f"{os.path.basename(path)}")
            kept.append(record)
        else:
            logger.info(f"  0 filtered cells, left out : {os.path.basename(path)}")
    return kept


def json_path_for(output_csv):
    """The final JSON path that goes with a CSV path: the same name, .json at the end."""
    stem, _ = os.path.splitext(output_csv)
    return stem + ".json"


def export_folder(folder, output_csv, logger, output_json=None):
    """Write the CSV and the JSON. Return the number of datasets written."""
    paths = list_files(folder)
    records = select_records(paths, logger)
    log_counts(logger, "datasets with filtered cells", before=len(paths), after=len(records))
    write_csv(output_csv, COLUMNS, [to_row(r) for r in records])
    write_json_list(output_json or json_path_for(output_csv), records)
    return len(records)


# =============================================================================
# run_export_datasets_csv
# =============================================================================
def run_export_datasets_csv(folder: str, output_csv: str, output_json: str = None):
    """Main entry point called by CLI"""
    folder = folder.rstrip("/")
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    logger = setup_logger("7_export_datasets_csv", output_csv=output_csv)
    log_command(logger)
    export_folder(folder, output_csv, logger, output_json)
    log_finish(logger, output_csv)
