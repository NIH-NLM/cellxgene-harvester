#!/usr/bin/env python3
"""
Step 4: Filter datasets using UBERON ontology term labels

Uses UBERON term labels (from 0_resolve_uberon.py) for text matching
against the 'tissue' column. Precise ontology ID filtering happens in
step 5 where Census provides tissue_ontology_term_id.

Usage:
1. Python module execution:
python -m harvester.filter_datasets
        --input data/all_datasets_complete.csv \
        --uberon data/uberon_kidney.json \
        --organism "Homo sapiens" \
        --no-preprints \
        --exclude-cancer \
        --exclude-spatial \
        --output data/homo_sapiens_kidney_harvester.csv

2. CLI command (after pip install -e .):
cellxgene-harvester filter_datasets
        --input data/all_datasets_complete.csv \
        --uberon data/uberon_kidney.json \
        --organism "Homo sapiens" \
        --no-preprints \
        --exclude-cancer \
        --exclude-spatial \
        --output data/homo_sapiens_kidney_harvester.csv

"""

import sys
import json
import pandas as pd
from harvester.logger import setup_logger, log_command, log_counts, log_finish


def load_uberon_labels(uberon_json: str, logger) -> list:
    """Load UBERON term labels for text matching against tissue column."""
    with open(uberon_json) as f:
        data = json.load(f)

    labels  = [t["label"].lower() for t in data["terms"] if t.get("label")]
    queries = data["queries"]
    roots   = [t["label"] for t in data["root_terms"]]

    logger.info(f"  Loaded UBERON terms : {uberon_json}")
    logger.info(f"  Queries             : {', '.join(queries)}")
    logger.info(f"  Root terms          : {', '.join(roots)}")
    logger.info(f"  Total labels        : {len(labels):,} (root + all descendants)")
    logger.info(f"  Note: label text matching on 'tissue' column")
    logger.info(f"        (tissue_ontology_term_id precision applied in step 5)")

    return labels


def filter_datasets(input_csv, output_csv, logger,
                    uberon_json=None, organism=None,
                    no_preprints=False, exclude_cancer=False,
                    exclude_spatial=False, disease=None):

    logger.info(f"Input : {input_csv}")
    df            = pd.read_csv(input_csv)
    initial_count = len(df)
    logger.info(f"Loaded {initial_count:,} datasets\n")

    # UBERON label tissue filter
    if uberon_json:
        uberon_labels = load_uberon_labels(uberon_json, logger)
        before        = len(df)

        def matches_uberon_label(tissue_str):
            if pd.isna(tissue_str):
                return False
            tissue_lower = str(tissue_str).lower()
            return any(label in tissue_lower for label in uberon_labels)

        mask = df['tissue'].apply(matches_uberon_label)
        df   = df[mask]
        log_counts(logger, "UBERON label tissue filter", before=before, after=len(df))
    else:
        logger.warning("  WARNING: No --uberon file provided - skipping tissue filter")

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

    # Disease filter
    if disease:
        before = len(df)
        df     = df[df['disease'].astype(str).str.lower().str.contains(disease.lower(), na=False)]
        log_counts(logger, f"disease filter ({disease})", before=before, after=len(df))

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
        organism=None,
        no_preprints=False,
        exclude_cancer=False,
        exclude_spatial=False,
        disease=None):
    
    """Main entry point called by CLI"""
    logger = setup_logger("4_filter_datasets", output_csv=output_csv)
    log_command(logger)
    
    filter_datasets(
        input_csv=input_csv,
        output_csv=output_csv,
        logger=logger,
        uberon_json=uberon_json,
        organism=organism,
        no_preprints=no_preprints,
        exclude_cancer=exclude_cancer,
        exclude_spatial=exclude_spatial,
        disease=disease
    )
    
    log_finish(logger, output_csv)

