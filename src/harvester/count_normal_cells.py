#!/usr/bin/env python3
"""
Step 5: Count normal cells using CellxGene Census API

Opens Census ONCE and reuses connection across all datasets.
Resumes automatically - skips rows where normal_cell_count is already set.

Usage:
1. Python module execution:
python -m harvester.count_normal_cells \
        --input data/homo_sapiens_kidney_harvester.csv \
        --uberon data/uberon_kidney.json \
        --min-age 15
2. CLI command (after pip install -e .):
cellxgene-harvester count-normal-cells \
        --input data/homo_sapiens_kidney_harvester.csv \
        --uberon data/uberon_kidney.json \
        --min-age 15
"""

import os
import sys
import json
import pandas as pd
import re
from typing import Optional
from harvester.logger import setup_logger, log_command, log_counts, log_finish


def extract_age_from_stage(stage_label: str) -> Optional[int]:
    if not stage_label or not isinstance(stage_label, str):
        return None
    match = re.search(r'(\d+)[- ]?(?:year|yr)', stage_label.lower())
    return int(match.group(1)) if match else None


def filter_adult_cells(obs_df: pd.DataFrame, min_age: int, logger) -> pd.DataFrame:
    if 'development_stage' not in obs_df.columns or min_age == 0:
        return obs_df

    EXCLUDE_TERMS = ['fetal', 'embryo', 'newborn', 'prenatal', 'lmp',
                     'post-fertilization', 'week post', 'Carnegie stage',
                     'trimester', 'gestational']

    adult_mask           = []
    cells_adult          = 0
    cells_child          = 0
    cells_excluded_fetal = 0

    for stage_val in obs_df['development_stage'].astype(str):
        stage_lower = stage_val.lower()

        if not stage_val or stage_val in ('nan', 'None') or stage_val.strip() == '':
            adult_mask.append(False)
            continue

        if any(term in stage_lower for term in EXCLUDE_TERMS):
            adult_mask.append(False)
            cells_excluded_fetal += 1
            continue

        if 'adult' in stage_lower:
            adult_mask.append(True)
            cells_adult += 1
            continue

        age = extract_age_from_stage(stage_val)
        if age is not None:
            if age >= min_age:
                adult_mask.append(True)
                cells_adult += 1
            else:
                adult_mask.append(False)
                cells_child += 1
        else:
            adult_mask.append(False)

    adult_df = obs_df[adult_mask]
    log_counts(logger, f"age filter (>= {min_age})",
               before=len(obs_df), after=len(adult_df), unit="cells")
    logger.info(f"        Adult: {cells_adult:,}  Child: {cells_child:,}  Fetal: {cells_excluded_fetal:,}")
    return adult_df


def filter_normal_cells(obs_df: pd.DataFrame, logger) -> pd.DataFrame:
    if 'disease' not in obs_df.columns:
        return obs_df
    normal_mask = (
        obs_df['disease'].str.lower().str.contains('normal',      na=False) |
        obs_df['disease'].str.lower().str.contains('pato:0000461', na=False)
    )
    normal_df = obs_df[normal_mask]
    log_counts(logger, "normal disease filter",
               before=len(obs_df), after=len(normal_df), unit="cells")
    return normal_df


def filter_primary_data(obs_df: pd.DataFrame, logger) -> pd.DataFrame:
    if 'is_primary_data' not in obs_df.columns:
        return obs_df
    # Handle both boolean True and string "True" from Census
    col        = obs_df['is_primary_data']
    mask       = (col == True) | (col.astype(str).str.lower() == 'true')
    primary_df = obs_df[mask]
    log_counts(logger, "primary data filter",
               before=len(obs_df), after=len(primary_df), unit="cells")
    return primary_df


def extract_census_metadata(obs_df: pd.DataFrame) -> dict:
    def get_most_common(col):
        if col in obs_df.columns and len(obs_df) > 0:
            vc = obs_df[col].value_counts()
            return str(vc.index[0]) if len(vc) > 0 else ''
        return ''

    def get_all_unique(col):
        if col in obs_df.columns and len(obs_df) > 0:
            uv = obs_df[col].dropna().unique()
            return ' | '.join(sorted([str(v) for v in uv])) if len(uv) > 0 else ''
        return ''

    # Tissue ontology summary
    tissue_summary = ''
    if 'tissue_ontology_term_id' in obs_df.columns:
        tissue_counts = obs_df['tissue_ontology_term_id'].value_counts()
        parts = [f"{tid}: {count:,}" for tid, count in tissue_counts.items() if count > 0]
        tissue_summary = "; ".join(parts)

    # Assay ontology summary
    assay_summary = ''
    if 'assay_ontology_term_id' in obs_df.columns:
        assay_counts = obs_df['assay_ontology_term_id'].value_counts()
        parts = [f"{aid}: {count:,}" for aid, count in assay_counts.items() if count > 0]
        assay_summary = "; ".join(parts)

    # Cell type ontology summary
    cell_type_summary = ''
    if 'cell_type_ontology_term_id' in obs_df.columns:
        ct_counts = obs_df['cell_type_ontology_term_id'].value_counts()
        parts = [f"{ct}: {count:,}" for ct, count in ct_counts.items() if count > 0]
        cell_type_summary = "; ".join(parts)

    # Disease ontology summary
    disease_summary = ''
    if 'disease_ontology_term_id' in obs_df.columns:
        dis_counts = obs_df['disease_ontology_term_id'].value_counts()
        parts = [f"{did}: {count:,}" for did, count in dis_counts.items() if count > 0]
        disease_summary = "; ".join(parts)

    # Sex ontology summary
    sex_summary = ''
    if 'sex_ontology_term_id' in obs_df.columns:
        sex_counts = obs_df['sex_ontology_term_id'].value_counts()
        parts = [f"{sid}: {count:,}" for sid, count in sex_counts.items() if count > 0]
        sex_summary = "; ".join(parts)

    dev_stage_summary = ''
    if 'development_stage' in obs_df.columns and len(obs_df) > 0:
        counts            = obs_df['development_stage'].value_counts()
        dev_stage_summary = "; ".join(f"{s}: {c:,}" for s, c in counts.items())

    donor_count = obs_df['donor_id'].nunique() if 'donor_id' in obs_df.columns else 0

    return {
        'tissue_ontology_term_id':            all_unique('tissue_ontology_term_id'),
        'assay_ontology_term_id':             all_unique('assay_ontology_term_id'),
        'cell_type_ontology_term_id':         all_unique('cell_type_ontology_term_id'),
        'disease_ontology_term_id':           all_unique('disease_ontology_term_id'),
        'development_stage_ontology_term_id': all_unique('development_stage_ontology_term_id'),
        'sex_ontology_term_id':               all_unique('sex_ontology_term_id'),
        'is_primary_data':                    most_common('is_primary_data'),
        'donor_id_count':                     donor_count,
        'tissue_ontology_summary':            tissue_summary,
        'assay_ontology_summary':             assay_summary,
        'cell_type_ontology_summary':         cell_type_summary,
        'disease_ontology_summary':           disease_summary,
        'development_stage_summary':          dev_stage_summary,
        'sex_ontology_summary':               sex_summary,
    }


def process_dataset(dataset_id: str, uberon_ids: set, min_age: int, census, logger) -> Optional[dict]:
    """Process one dataset using an already-open Census connection.
    
    Pushes UBERON tissue + primary data + normal disease filters into the
    Census query to avoid loading millions of cells into RAM.
    """
    try:
        import cellxgene_census

        # Build server-side filter string - only download what we need
        tissue_ids_str = ", ".join(f"\'{t}\'" for t in sorted(uberon_ids))
        obs_filter = (
            f"dataset_id == '{dataset_id}' "
            f"and tissue_ontology_term_id in [{tissue_ids_str}] "
            f"and disease == 'normal'"
        )
        logger.info(f"    Querying Census (server-side filtered)...")

        adata = cellxgene_census.get_anndata(
            census=census,
            organism="Homo sapiens",
            obs_value_filter=obs_filter,
            obs_column_names=["tissue",
                              "tissue_ontology_term_id",
                              "disease",
                              "disease_ontology_term_id",
                              "development_stage",
                              "development_stage_ontology_term_id",
                              "assay_ontology_term_id",
                              "cell_type_ontology_term_id",
                              "sex_ontology_term_id",
                              "is_primary_data",
                              "donor_id",
                              "suspension_type"]
        )

        if adata is None or adata.n_obs == 0:
            logger.info(f"    Census returned 0 cells after server-side filters")
            return {'normal_cell_count': 0, 'total_count': 0, 'adult_count': 0,
                    **extract_census_metadata(pd.DataFrame())}

        obs_df = adata.obs
        logger.info(f"    Census returned {len(obs_df):,} cells (tissue+primary+normal filtered)")

        metadata = extract_census_metadata(obs_df)

        # Age filter (must be done client-side - no Census query support)
        adult_df    = filter_adult_cells(obs_df, min_age, logger)
        adult_count = len(adult_df)

        if adult_count == 0:
            return {'normal_cell_count': 0, 'total_count': len(obs_df),
                    'adult_count': 0, **metadata}

        normal_cell_count = len(adult_df)

        return {
            'normal_cell_count': normal_cell_count,
            'total_count':       len(obs_df),
            'adult_count':       adult_count,
            **metadata
        }

    except Exception as e:
        logger.error(f"    ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def process_all_datasets(input_csv, output_csv, uberon_json, min_age, logger):
    import cellxgene_census

    # Load UBERON IDs
    with open(uberon_json) as f:
        uberon_data = json.load(f)
    uberon_ids = set(uberon_data["obo_ids"])
    roots      = [t["label"] for t in uberon_data["root_terms"]]
    logger.info(f"UBERON terms: {len(uberon_ids):,} IDs  (roots: {', '.join(roots)})\n")

    # Load input - use output if it exists (resume)
    if os.path.exists(output_csv):
        df = pd.read_csv(output_csv, dtype=str)
        logger.info(f"Resuming from: {output_csv} ({len(df):,} datasets)")
    else:
        df = pd.read_csv(input_csv, dtype=str)
        logger.info(f"Starting fresh: {input_csv} ({len(df):,} datasets)")

    # Ensure output columns exist
    for col in ['normal_cell_count',
                'tissue_ontology_term_id',
                'assay_ontology_term_id',
                'cell_type_ontology_term_id',
                'disease_ontology_term_id',
                'development_stage_ontology_term_id',
                'sex_ontology_term_id',
                'is_primary_data',
                'donor_id_count',
                'tissue_ontology_summary',
                'assay_ontology_summary',
                'cell_type_ontology_summary',
                'disease_ontology_summary',
                'development_stage_summary',
                'sex_ontology_summary']:
        if col not in df.columns:
            df[col] = ''

    df.to_csv(output_csv, index=False)

    # Count already done
    already_done = df['normal_cell_count'].notna() & (df['normal_cell_count'] != '')
    logger.info(f"Already processed: {already_done.sum():,} / {len(df):,}\n")

    stats = {'successful': 0, 'failed': 0, 'skipped': 0, 'resumed': int(already_done.sum())}

    # Open Census ONCE for all datasets
    logger.info("Opening Census connection (once for all datasets)...")
    with cellxgene_census.open_soma(census_version="latest") as census:
        logger.info("Census connection open\n")

        for idx, row in df.iterrows():
            dataset_id   = str(row.get('dataset_id', '')).strip()
            first_author = row.get('first_author', 'Unknown')
            year         = row.get('year', 'Unknown')
            journal      = row.get('journal', 'Unknown')

            # Resume: skip already processed
            existing = str(row.get('normal_cell_count', '')).strip()
            if existing and existing not in ('', 'nan', 'None'):
                logger.info(f"[{idx+1}/{len(df)}] SKIP (already done: {existing} normal cells) - {dataset_id}")
                continue

            logger.info(f"\n[{idx+1}/{len(df)}] {dataset_id}")
            logger.info(f"  {first_author} ({year}) - {journal}")

            if not dataset_id or dataset_id == 'nan':
                logger.warning(f"  SKIPPED: Missing dataset_id")
                stats['skipped'] += 1
                continue

            result = process_dataset(dataset_id, uberon_ids, min_age, census, logger)

            if result is not None:
                for key, val in result.items():
                    if key in df.columns:
                        df.loc[idx, key] = str(val)
                logger.info(f"  SUCCESS: {result['normal_cell_count']:,} normal cells")
                stats['successful'] += 1
            else:
                logger.warning(f"  FAILED")
                stats['failed'] += 1

            df.to_csv(output_csv, index=False)

    logger.info(f"\n{'='*70}")
    logger.info(f"  Resumed (already done) : {stats['resumed']:,}")
    logger.info(f"  Newly processed        : {stats['successful']:,}")
    logger.info(f"  Failed                 : {stats['failed']:,}")
    logger.info(f"  Skipped (no ID)        : {stats['skipped']:,}")

# =============================================================================
# run_count_normal_cells
# =============================================================================
def run_count_normal_cells(
        input_csv: str,
        uberon_json: str,
        min_age: int
    ):
    """Main entry point called by CLI"""
    base = os.path.splitext(input_csv)[0]
    output_csv = f"{base}_with_normal_counts.csv"
    
    logger = setup_logger("5_count_normal_cells", output_csv=output_csv)
    log_command(logger)
    logger.info(f"UBERON file: {uberon_json}")
    logger.info(f"Min age    : {min_age}")
    logger.info(f"Output     : {output_csv}\n")
    
    try:
        import cellxgene_census
    except ImportError:
        logger.error("ERROR: cellxgene_census not found")
        sys.exit(1)
    
    process_all_datasets(input_csv, output_csv, uberon_json, min_age, logger)
    log_finish(logger, output_csv)

