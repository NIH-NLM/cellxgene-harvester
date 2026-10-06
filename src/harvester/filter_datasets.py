#!/usr/bin/env python3
"""
Step 4: Filter datasets using UBERON and disease ontology IDs

Reads all_datasets_complete.csv (Step 3 output), keeps the datasets that are
relevant for a tissue and a disease state, and writes one JSON file for each
dataset that is kept: <dataset_id>.filtered.json.

Both ontology filters are INCLUSIVE:
  - Tissue : keep if ANY of the dataset's tissue IDs are in the uberon obo_ids
  - Disease: keep if ANY of the dataset's disease IDs are in the disease obo_ids
             (a dataset with [normal, COVID-19] is kept: it has normal cells)

Cancer and spatial datasets are NOT screened here. The disease file already
decides which disease states count, and a technique is screened by its assay
ontology id in Step 5 (--exclude-assay). Text matching does not find either
reliably; see the README.

Age filtering (HsapDv) is NOT applied here. Development stage is absent at the
dataset level and is only available after the Census query in Step 5. The
optional --hsapdv file is only recorded, so the age choice is on file from
this step on.

Each JSON file records the choices made here (filter_choices), the organ (the
root term given to resolve-uberon), and the source_ values for tissue and
disease. The filtered_ values stay empty until Step 5.

Usage:
1. Python module execution:
python -m harvester.filter_datasets \
        2026-08-03-run/all_datasets_complete.csv \
        --uberon  2026-08-03-run/uberon_kidney.json \
        --disease 2026-08-03-run/disease_normal.json \
        --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
        --organism "Homo sapiens" \
        --no-preprints \
        --output  2026-08-03-run/homo_sapiens_kidney_harvester

2. CLI command (after pip install -e .):
cellxgene-harvester filter-datasets 2026-08-03-run/all_datasets_complete.csv \
        --uberon  2026-08-03-run/uberon_kidney.json \
        --disease 2026-08-03-run/disease_normal.json \
        --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
        --organism "Homo sapiens" \
        --no-preprints \
        --output  2026-08-03-run/homo_sapiens_kidney_harvester

The --output value is a folder.
"""

import os
from datetime import date

import pandas as pd

from harvester import __version__, ontology_files
from harvester.io_utils import merge_curation, write_json
from harvester.logger import setup_logger, log_command, log_counts, log_finish
from harvester.records import new_record, split_cell


def read_rows(input_csv):
    """Read the CSV with every cell as text, so "2022" stays text."""
    return pd.read_csv(input_csv, dtype=str, keep_default_na=False)


def overlaps(cell, ids):
    """True if any id in a " | " joined cell is in the set of ids."""
    return bool(set(split_cell(cell)) & ids)


def keep_tissue(df, uberon_ids):
    return df[df["tissue_ontology_term_id"].apply(lambda cell: overlaps(cell, uberon_ids))]


def keep_disease(df, disease_ids):
    return df[df["disease_ontology_term_id"].apply(lambda cell: overlaps(cell, disease_ids))]


def keep_organism(df, organism):
    return df[df["organism"].str.lower() == organism.lower()]


def drop_preprints(df):
    return df[df["is_preprint"].str.lower() == "false"]


def log_ontology_file(logger, label, path):
    info = ontology_files.describe(path)
    roots = ", ".join(t["label"] for t in info["root_terms"])
    logger.info(f"  Loaded {label} JSON : {path}")
    logger.info(f"  Root terms          : {roots}")
    logger.info(f"  Total obo_ids       : {info['term_count']}")


def filter_rows(df, logger, uberon_json, disease_json, organism, no_preprints):
    """Apply the filters in order and log the counts after each one."""
    steps = []
    if uberon_json:
        uberon_ids = ontology_files.load_obo_ids(uberon_json)
        steps.append(("UBERON ontology ID tissue filter",
                      lambda d: keep_tissue(d, uberon_ids)))
    else:
        logger.warning("  WARNING: No --uberon file provided - skipping tissue filter")
    if disease_json:
        disease_ids = ontology_files.load_obo_ids(disease_json)
        steps.append(("disease ontology ID filter (inclusive)",
                      lambda d: keep_disease(d, disease_ids)))
    else:
        logger.warning("  WARNING: No --disease file provided - skipping disease filter")
    if organism:
        steps.append((f"organism filter ({organism})", lambda d: keep_organism(d, organism)))
    if no_preprints:
        steps.append(("preprint exclusion", drop_preprints))

    for name, step in steps:
        before = len(df)
        df = step(df)
        log_counts(logger, name, before=before, after=len(df))
    return df


def make_filter_choices(uberon_json, disease_json, hsapdv_json, organism, no_preprints):
    """Everything the user chose in this step, to be written in each file."""
    choices = {
        "organism": organism,
        "no_preprints": no_preprints,
    }
    for name, path in (("uberon", uberon_json), ("disease", disease_json), ("hsapdv", hsapdv_json)):
        if path:
            choices[name] = ontology_files.describe(path)
    choices["harvester_version"] = __version__
    choices["run_date"] = date.today().isoformat()
    return choices


def write_records(df, output_dir, organ, filter_choices):
    """Write one <dataset_id>.filtered.json for each row. Return the paths."""
    paths = []
    for _, row in df.iterrows():
        path = os.path.join(output_dir, f"{row['dataset_id']}.filtered.json")
        record = new_record(row, organ, filter_choices)
        write_json(path, merge_curation(record, path))
        paths.append(path)
    return paths


def filter_datasets(input_csv, output_dir, logger,
                    uberon_json=None, disease_json=None, hsapdv_json=None,
                    organism=None, no_preprints=False):

    logger.info(f"Input : {input_csv}")
    df = read_rows(input_csv)
    initial_count = len(df)
    logger.info(f"Loaded {initial_count} datasets\n")

    for label, path in (("UBERON", uberon_json), ("disease", disease_json), ("HsapDv", hsapdv_json)):
        if path:
            log_ontology_file(logger, label, path)

    df = filter_rows(df, logger, uberon_json, disease_json, organism, no_preprints)

    logger.info("")
    log_counts(logger, "TOTAL", before=initial_count, after=len(df))

    organ = ontology_files.organ_from(uberon_json) if uberon_json else None
    choices = make_filter_choices(uberon_json, disease_json, hsapdv_json, organism, no_preprints)
    paths = write_records(df, output_dir, organ, choices)
    logger.info(f"Wrote {len(paths)} JSON files to {output_dir}")


# =============================================================================
# run_filter_datasets
# =============================================================================
def run_filter_datasets(
        input_csv,
        output_dir,
        uberon_json=None,
        disease_json=None,
        hsapdv_json=None,
        organism=None,
        no_preprints=False):

    """Main entry point called by CLI"""
    output_dir = output_dir.rstrip("/")
    os.makedirs(output_dir, exist_ok=True)
    logger = setup_logger("4_filter_datasets", output_csv=f"{output_dir}.filter.log")
    log_command(logger)

    filter_datasets(
        input_csv=input_csv,
        output_dir=output_dir,
        logger=logger,
        uberon_json=uberon_json,
        disease_json=disease_json,
        hsapdv_json=hsapdv_json,
        organism=organism,
        no_preprints=no_preprints,
    )

    log_finish(logger, output_dir)
