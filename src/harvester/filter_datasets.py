#!/usr/bin/env python3
"""
Step 4: Filter datasets using UBERON and disease ontology IDs

Filters the all_datasets_complete.csv (Step 3 output) down to only datasets
that are relevant for a given tissue and disease state, using exact ontology
ID matching against the tissue_ontology_term_id and disease_ontology_term_id
columns populated by generate_metadata (Step 2).

Both filters are INCLUSIVE:
  - Tissue : keep if ANY of the dataset's tissue IDs are in uberon obo_ids
  - Disease: keep if the target disease ID is AMONG the dataset's disease IDs
             (a dataset with [normal, COVID-19] is retained — it has normal cells)

Age filtering (HsapDv) is NOT applied here — development_stage is absent at
the dataset level and is only available after the Census query in Step 5.

Usage:
1. Python module execution:
python -m harvester.filter_datasets \
        data/all_datasets_complete.csv \
        --uberon  data/uberon_kidney.json \
        --disease data/disease_normal.json \
        --organism "Homo sapiens" \
        --no-preprints \
        --exclude-cancer \
        --exclude-spatial \
        --output  data/homo_sapiens_kidney_harvester.csv

2. CLI command (after pip install -e .):
cellxgene-harvester filter-datasets data/all_datasets_complete.csv \
        --uberon  data/uberon_kidney.json \
        --disease data/disease_normal.json \
        --organism "Homo sapiens" \
        --no-preprints \
        --exclude-cancer \
        --exclude-spatial \
        --output  data/homo_sapiens_kidney_harvester.csv

"""

import sys
import json
import pandas as pd
from harvester.logger import setup_logger, log_command, log_counts, log_finish


def load_obo_ids(json_path: str, label: str, logger) -> set:
    """Load obo_ids from a resolve_uberon / resolve_disease JSON.

    Both JSON files share the same structure produced by their resolve steps,
    so one helper covers both. Returns a set of ontology ID strings for use
    with set intersection against the ontology_term_id columns in the CSV.

    Example (uberon_kidney.json):
        {"obo_ids": ["UBERON:0002113", "UBERON:0001225", ...], "terms": [...], ...}
    """
    with open(json_path) as f:
        data = json.load(f)
    obo_ids = set(data["obo_ids"])
    roots   = [t["label"] for t in data["root_terms"]]
    logger.info(f"  Loaded {label} JSON : {json_path}")
    logger.info(f"  Root terms          : {', '.join(roots)}")
    logger.info(f"  Total obo_ids       : {len(obo_ids):,}")
    return obo_ids


def filter_datasets(input_csv, output_csv, logger,
                    uberon_json=None, disease_json=None, organism=None,
                    no_preprints=False, exclude_cancer=False,
                    exclude_spatial=False):

    logger.info(f"Input : {input_csv}")
    df            = pd.read_csv(input_csv)
    initial_count = len(df)
    logger.info(f"Loaded {initial_count:,} datasets\n")

    # ------------------------------------------------------------------
    # UBERON tissue filter — exact ontology ID matching on
    # tissue_ontology_term_id column (populated by generate_metadata Step 2).
    # Keep a dataset if ANY of its tissue IDs are in the uberon obo_ids set.
    # This is far more precise than text matching and uses the same IDs
    # that the Census query in Step 5 will use.
    # ------------------------------------------------------------------
    if uberon_json:
        uberon_ids = load_obo_ids(uberon_json, "UBERON", logger)
        before     = len(df)

        def has_matching_tissue(id_str):
            if pd.isna(id_str) or str(id_str).strip() == "":
                return False
            # tissue_ontology_term_id is " | "-joined (safe_ontology_ids separator)
            dataset_ids = set(str(id_str).split(" | "))
            return bool(dataset_ids & uberon_ids)  # non-empty intersection

        mask = df['tissue_ontology_term_id'].apply(has_matching_tissue)
        df   = df[mask]
        log_counts(logger, "UBERON ontology ID tissue filter", before=before, after=len(df))
    else:
        logger.warning("  WARNING: No --uberon file provided - skipping tissue filter")

    # ------------------------------------------------------------------
    # Disease filter — exact ontology ID matching on disease_ontology_term_id.
    # Inclusive: keep if the target disease is AMONG the dataset's diseases,
    # not requiring all diseases to match.  A dataset with [normal, COVID-19]
    # should still be retained because it contains normal cells.
    # ------------------------------------------------------------------
    if disease_json:
        disease_ids = load_obo_ids(disease_json, "disease", logger)
        before      = len(df)

        def has_matching_disease(id_str):
            if pd.isna(id_str) or str(id_str).strip() == "":
                return False
            dataset_ids = set(str(id_str).split(" | "))
            return bool(dataset_ids & disease_ids)

        mask = df['disease_ontology_term_id'].apply(has_matching_disease)
        df   = df[mask]
        log_counts(logger, "disease ontology ID filter (inclusive)", before=before, after=len(df))
    else:
        logger.warning("  WARNING: No --disease file provided - skipping disease filter")

    # Organism filter
    if organism:
        before = len(df)
        df     = df[df['organism'].astype(str).str.lower() == organism.lower()]
        log_counts(logger, f"organism filter ({organism})", before=before, after=len(df))

    # Preprint filter
    if no_preprints:
        before          = len(df)
        preprint_values = df['is_preprint'].astype(str).str.lower()
        df              = df[preprint_values == 'false']
        log_counts(logger, "preprint exclusion", before=before, after=len(df))

    # Cancer filter
    if exclude_cancer:
        before      = len(df)
        cancer_mask = (
            df['disease'].astype(str).str.lower().str.contains('cancer',    na=False) |
            df['disease'].astype(str).str.lower().str.contains('carcinoma', na=False)
        )
        df = df[~cancer_mask]
        log_counts(logger, "cancer exclusion", before=before, after=len(df))

    # Spatial filter
    if exclude_spatial:
        before        = len(df)
        spatial_terms = ['spatial', 'visium', 'slide-seq', 'slideseq', 'merfish',
                         'seqfish', 'cosmx', 'xenium', 'stereo-seq', 'stereoseq']
        spatial_mask  = pd.Series([False] * len(df), index=df.index)
        for term in spatial_terms:
            spatial_mask |= df['dataset_title'].astype(str).str.lower().str.contains(term, na=False)
            spatial_mask |= df['disease'].astype(str).str.lower().str.contains(term, na=False)
            spatial_mask |= df['tissue'].astype(str).str.lower().str.contains(term, na=False)
        df = df[~spatial_mask]
        log_counts(logger, "spatial exclusion", before=before, after=len(df))

    # Total summary
    logger.info("")
    log_counts(logger, "TOTAL", before=initial_count, after=len(df))

    df.to_csv(output_csv, index=False)


# =============================================================================
# run_filter_datasets
# =============================================================================
def run_filter_datasets(
        input_csv,
        output_csv,
        uberon_json=None,
        disease_json=None,
        organism=None,
        no_preprints=False,
        exclude_cancer=False,
        exclude_spatial=False):

    """Main entry point called by CLI"""
    logger = setup_logger("4_filter_datasets", output_csv=output_csv)
    log_command(logger)

    filter_datasets(
        input_csv=input_csv,
        output_csv=output_csv,
        logger=logger,
        uberon_json=uberon_json,
        disease_json=disease_json,
        organism=organism,
        no_preprints=no_preprints,
        exclude_cancer=exclude_cancer,
        exclude_spatial=exclude_spatial,
    )
    
    log_finish(logger, output_csv)

