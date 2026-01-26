#!/usr/bin/env python3
"""
Step 5: Count normal cells using CellxGene Census API

Clean pandas implementation with separated functions:
- extract_age_from_stage() - Parse age from string
- filter_adult_cells() - Filter for age >= 18
- count_normal_cells() - Count normal disease cells
- extract_census_metadata() - Extract all Census fields

Usage:
    python bin/5_count_normal_cells.py <filtered_csv>
"""

import os
import sys
import pandas as pd
import numpy as np
import cellxgene_census
from typing import Optional
import logging
from datetime import datetime
import re


def setup_logging(output_csv):
    """Setup logging to file and console"""
    log_file = output_csv.replace('.csv', '_log.txt')
    
    logger = logging.getLogger('cellxgene_harvester')
    logger.setLevel(logging.INFO)
    logger.handlers = []
    
    fh = logging.FileHandler(log_file, mode='w')
    ch = logging.StreamHandler(sys.stdout)
    
    formatter = logging.Formatter('%(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger, log_file


def extract_age_from_stage(stage_label: str) -> Optional[int]:
    """
    Extract age in years from development stage label.
    
    Examples:
        "18-year-old human stage" -> 18
        "25 year old" -> 25
        
    Returns:
        Age in years, or None if no age found
    """
    if not stage_label or not isinstance(stage_label, str):
        return None
    
    pattern = r'(\d+)[- ]?(?:year|yr)'
    match = re.search(pattern, stage_label.lower())
    
    if match:
        return int(match.group(1))
    
    return None


def filter_adult_cells(obs_df: pd.DataFrame, logger) -> pd.DataFrame:
    """
    Filter for adult cells (age >= 18 years).
    
    Strategy:
    1. Parse age from development_stage - include if >= 18
    2. Check for "adult" keyword - include if present
    3. Check for fetal/newborn keywords - EXCLUDE if present
    4. If unparseable and no keywords - EXCLUDE (conservative)
    """
    if 'development_stage' not in obs_df.columns:
        logger.info(f"      No development_stage column - including all cells")
        return obs_df
    
    # Exclusion terms (fetal, embryonic, newborn)
    EXCLUDE_TERMS = ['fetal', 'embryo', 'newborn', 'prenatal', 'lmp', 
                     'post-fertilization', 'week post', 'Carnegie stage',
                     'trimester', 'gestational']
    
    adult_mask = []
    total_cells = len(obs_df)
    cells_with_age = 0
    cells_adult = 0
    cells_child = 0
    cells_excluded_fetal = 0
    
    for stage_val in obs_df['development_stage'].astype(str):
        stage_lower = stage_val.lower()
        
        # Empty/null - EXCLUDE (conservative)
        if not stage_val or stage_val == 'nan' or stage_val.strip() == '' or stage_val == 'None':
            adult_mask.append(False)
            continue
        
        # Check for exclusion terms (fetal, embryonic, etc.)
        is_excluded = any(term in stage_lower for term in EXCLUDE_TERMS)
        if is_excluded:
            adult_mask.append(False)
            cells_excluded_fetal += 1
            continue
        
        # Check for "adult" keyword
        if 'adult' in stage_lower:
            adult_mask.append(True)
            cells_adult += 1
            continue
        
        # Try to parse age
        age = extract_age_from_stage(stage_val)
        if age is not None:
            cells_with_age += 1
            if age >= 18:
                adult_mask.append(True)
                cells_adult += 1
            else:
                adult_mask.append(False)
                cells_child += 1
        else:
            # Unparseable and no "adult" keyword - EXCLUDE (conservative)
            adult_mask.append(False)
    
    adult_df = obs_df[adult_mask]
    
    logger.info(f"      Age filtering:")
    logger.info(f"        Total cells: {total_cells:,}")
    logger.info(f"        Cells with parseable age: {cells_with_age:,}")
    logger.info(f"        Adult (age >= 18 or contains 'adult'): {cells_adult:,}")
    logger.info(f"        Child (age < 18): {cells_child:,}")
    logger.info(f"        Excluded (fetal/newborn): {cells_excluded_fetal:,}")
    logger.info(f"        After filter: {len(adult_df):,}")
    
    return adult_df


def count_normal_cells(obs_df: pd.DataFrame, logger) -> int:
    """
    Count cells with normal disease status.
    
    Normal = disease contains "normal" or "PATO:0000461"
    """
    if 'disease' not in obs_df.columns:
        logger.warning(f"      No disease column - cannot count normal cells")
        return 0
    
    # Case-insensitive search
    disease_lower = obs_df['disease'].str.lower()
    normal_mask = (
        disease_lower.str.contains('normal', na=False) |
        disease_lower.str.contains('pato:0000461', na=False)
    )
    
    normal_count = normal_mask.sum()
    
    logger.info(f"      Disease filtering:")
    logger.info(f"        Total cells: {len(obs_df):,}")
    logger.info(f"        Normal cells: {normal_count:,}")
    
    return int(normal_count)

def extract_census_metadata(obs_df: pd.DataFrame, adata, census, dataset_id: str, logger) -> dict:
    """Extract all Census metadata fields"""
    
    def get_most_common(column_name):
        """Get most common value in a column"""
        if column_name in obs_df.columns:
            value_counts = obs_df[column_name].value_counts()
            if len(value_counts) > 0:
                return str(value_counts.index[0])
        return ''
    
    # Extract embeddings using experimental API
    embeddings = []
    try:
        # Get all available embeddings for this dataset
        embedding_data = cellxgene_census.experimental.get_embeddings(
            census=census,
            organism="Homo sapiens",
            obs_value_filter=f"dataset_id == '{dataset_id}'"
        )
        # Extract embedding names from the returned data
        if hasattr(embedding_data, 'keys'):
            embeddings = list(embedding_data.keys())
            embeddings = [e.replace('X_', '') if e.startswith('X_') else e for e in embeddings]

    except Exception as e:
        logger.warning(f"      Could not fetch embeddings: {e}")
        embeddings = []

    embeddings_str = '|'.join(sorted(embeddings)) if embeddings else ''

    
    # Human-readable fields
    census_tissue = get_most_common('tissue')
    census_disease = get_most_common('disease')
    census_development_stage = get_most_common('development_stage')
    
    # Ontology IDs
    tissue_ontology_term_id = get_most_common('tissue_ontology_term_id')
    assay_ontology_term_id = get_most_common('assay_ontology_term_id')
    cell_type_ontology_term_id = get_most_common('cell_type_ontology_term_id')
    disease_ontology_term_id = get_most_common('disease_ontology_term_id')
    development_stage_ontology_term_id = get_most_common('development_stage_ontology_term_id')
    sex_ontology_term_id = get_most_common('sex_ontology_term_id')
    is_primary_data = get_most_common('is_primary_data')
    
    # Donor count
    donor_id_count = obs_df['donor_id'].nunique() if 'donor_id' in obs_df.columns else 0
    
    # Development stage summary (top 3)
    dev_stage_summary = ''
    if 'development_stage' in obs_df.columns:
        stage_counts = obs_df['development_stage'].value_counts().head(3)
        parts = [f"{stage}: {count:,}" for stage, count in stage_counts.items()]
        dev_stage_summary = "; ".join(parts)
    
    logger.info(f"    Census metadata:")
    logger.info(f"      Tissue (specific): {census_tissue or 'N/A'}")
    logger.info(f"      Dev stages: {dev_stage_summary or 'N/A'}")
    logger.info(f"      Embeddings: {embeddings_str or 'None'}")
    logger.info(f"      Donors: {donor_id_count}")
    
    return {
        'embeddings': embeddings_str,
        'census_tissue': census_tissue,
        'census_disease': census_disease,
        'census_development_stage': census_development_stage,
        'tissue_ontology_term_id': tissue_ontology_term_id,
        'assay_ontology_term_id': assay_ontology_term_id,
        'cell_type_ontology_term_id': cell_type_ontology_term_id,
        'disease_ontology_term_id': disease_ontology_term_id,
        'development_stage_ontology_term_id': development_stage_ontology_term_id,
        'sex_ontology_term_id': sex_ontology_term_id,
        'is_primary_data': is_primary_data,
        'donor_id_count': donor_id_count,
        'development_stage_summary': dev_stage_summary
    }

def process_dataset(dataset_id: str, tissue_filter: str, logger) -> Optional[dict]:
    """
    Process one dataset: query Census, filter by tissue, filter adults, count normal cells
    """
    try:
        logger.info(f"    Querying Census API...")

        with cellxgene_census.open_soma(census_version="latest") as census:
            build_date = "2025-11-08"  # Latest stable release date
            
            adata = cellxgene_census.get_anndata(
                census=census,
                organism="Homo sapiens",
                obs_value_filter=f"dataset_id == '{dataset_id}'"
            )

            if adata is None or adata.n_obs == 0:
                logger.warning(f"    WARNING: Census returned 0 cells")
                logger.warning(f"      Dataset may not be in Census or ID mismatch")
                return None

            obs_df = adata.obs
            initial_count = len(obs_df)
            logger.info(f"    Census returned {initial_count:,} total cells")

            # Always FILTER BY TISSUE - Handle multiple patterns separated by |
            # Split by | and strip whitespace
            tissue_patterns = [t.strip() for t in tissue_filter.split('|')]
            
            # Create mask that matches ANY of the patterns
            tissue_mask = pd.Series([False] * len(obs_df), index=obs_df.index)
            for pattern in tissue_patterns:
                tissue_mask |= obs_df['tissue'].str.contains(pattern, case=False, na=False, regex=False)
            
            obs_df = obs_df[tissue_mask]
            logger.info(f"    After tissue filter ({tissue_filter}): {len(obs_df):,} cells")
            
            # Extract metadata
            metadata = extract_census_metadata(obs_df, adata, census, dataset_id, logger)

            # Check if primary data - skip if not
            if metadata.get('is_primary_data', '').upper() != 'TRUE':
                logger.warning(f"    SKIPPED: is_primary_data = {metadata.get('is_primary_data')}")
                return None

            # Filter for adults
            adult_df = filter_adult_cells(obs_df, logger)
            adult_count = len(adult_df)

            # Count normal cells in adult population
            normal_cell_count = count_normal_cells(adult_df, logger)

            return {
                'normal_cell_count': normal_cell_count,
                'total_count': len(obs_df),  # Count after tissue filter
                'adult_count': adult_count,
                'build_date': build_date,
                **metadata
            }

    except Exception as e:
        logger.error(f"    ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def process_all_datasets(input_csv, output_csv, tissue_filter, logger):
    """Main processing loop using pandas"""
    
    # Load data
    df = pd.read_csv(input_csv)
    logger.info(f"Loaded {len(df)} datasets from {input_csv}\n")
    
    # Define new columns
    new_columns = [
        'normal_cell_count', 'development_stage',
        'assay_ontology_term_id', 'cell_type_ontology_term_id',
        'disease_ontology_term_id', 'development_stage_ontology_term_id',
        'sex_ontology_term_id', 'is_primary_data', 'donor_id_count',
        'development_stage_summary'
    ]
    
    # Initialize new columns
    for col in new_columns:
        if col not in df.columns:
            df[col] = ''
            
    # Force all new columns to object dtype (allows any value type)
    df = df.astype(object)
    
    # Define column order
    column_order = [
        'collection_name', 'dataset_title', 'normal_cell_count', 'total_cell_count',
        'author_cell_type', 'embedding',
        'tissue', 'disease', 'development_stage',
        'first_author', 'journal', 'year', 'collection_url', 'explorer_url',
        'collection_id', 'collection_version_id', 'dataset_id', 'dataset_version_id',
        'is_preprint', 'revised_at', 'visibility', 'organism',
        'filter_normal', 'metric', 'save_scores', 'save_cluster_summary', 'save_annotation',
        'h5ad_url',
        'tissue_ontology_term_id',
        'assay_ontology_term_id', 'cell_type_ontology_term_id',
        'disease_ontology_term_id', 'development_stage_ontology_term_id',
        'sex_ontology_term_id', 'is_primary_data', 'donor_id_count',
        'development_stage_summary'
    ]
    
    # Reorder columns (keep existing columns not in order at end)
    existing_ordered = [c for c in column_order if c in df.columns]
    remaining = [c for c in df.columns if c not in existing_ordered]
    df = df[existing_ordered + remaining]
    
    # Save initial file
    df.to_csv(output_csv, index=False)
    logger.info(f"Initialized output: {output_csv}\n")
    
    # Process each dataset
    logger.info(f"Processing {len(df)} datasets...")
    logger.info(f"Progress saved after each dataset\n")
    
    stats = {'successful': 0, 'failed': 0, 'skipped': 0}
    
    for idx, row in df.iterrows():
        dataset_id = row.get('dataset_id', '')
        total_cells_csv = row.get('total_cell_count', 0)
        
        logger.info(f"\n[{idx+1}/{len(df)}] Processing {dataset_id}")
        logger.info(f"  Expected cells (from CSV): {total_cells_csv}")
        
        if not dataset_id:
            logger.warning(f"  SKIPPED: Missing dataset_id")
            stats['skipped'] += 1
            continue
        
        # Process
        result = process_dataset(dataset_id, tissue_filter, logger)
        
        if result is not None:
            # Update row with all results
            df.loc[idx, 'revised_at'] = result['build_date']
            df.loc[idx, 'normal_cell_count'] = str(result['normal_cell_count'])
            df.loc[idx, 'embedding'] = result['embeddings']
            df.loc[idx, 'development_stage'] = result['census_development_stage']
            df.loc[idx, 'tissue_ontology_term_id'] = result['tissue_ontology_term_id']
            df.loc[idx, 'assay_ontology_term_id'] = result['assay_ontology_term_id']
            df.loc[idx, 'cell_type_ontology_term_id'] = result['cell_type_ontology_term_id']
            df.loc[idx, 'disease_ontology_term_id'] = result['disease_ontology_term_id']
            df.loc[idx, 'development_stage_ontology_term_id'] = result['development_stage_ontology_term_id']
            df.loc[idx, 'sex_ontology_term_id'] = result['sex_ontology_term_id']
            df.loc[idx, 'is_primary_data'] = result['is_primary_data']
            df.loc[idx, 'donor_id_count'] = str(result['donor_id_count'])
            df.loc[idx, 'development_stage_summary'] = result['development_stage_summary']
            
            logger.info(f"  SUCCESS: {result['normal_cell_count']:,} normal cells")
            logger.info(f"    (Adult: {result['adult_count']:,} / Total: {result['total_count']:,})")
            stats['successful'] += 1
        else:
            logger.warning(f"  FAILED")
            stats['failed'] += 1
        
        # Save progress after each dataset
        df.to_csv(output_csv, index=False)
        logger.info(f"  Progress saved ({sum(stats.values())}/{len(df)} complete)")
    
    # Final summary
    logger.info(f"\n{'='*70}")
    logger.info(f"COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"Total datasets: {len(df)}")
    logger.info(f"Successful: {stats['successful']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Skipped: {stats['skipped']}")
    logger.info(f"\nOutput: {output_csv}")

if __name__ == "__main__":
    import argparse
    
    print("="*70)
    print("CellxGene Harvester - Step 5: Count Normal Cells")
    print("="*70)
    
    parser = argparse.ArgumentParser(
        description='Count normal cells from CellxGene Census API'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input CSV file (output from step 4)'
    )
    parser.add_argument(
        '--tissue',
        required=True,
        help='Tissue(s) to filter (e.g., "liver" or "pancreas | islet of langerhans")'
    )
    
    args = parser.parse_args()
    
    input_csv = args.input
    tissue_filter = args.tissue
    base = os.path.splitext(input_csv)[0]
    output_csv = f"{base}_with_normal_counts.csv"
    
    # Setup logging
    logger, log_file = setup_logging(output_csv)
    
    logger.info(f"Starting: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Input: {input_csv}")
    logger.info(f"Tissue filter: {tissue_filter}")
    logger.info(f"Output: {output_csv}")
    logger.info(f"Log: {log_file}\n")
    
    # Check dependencies
    try:
        import cellxgene_census
    except ImportError:
        logger.error("ERROR: cellxgene_census not found")
        logger.error("Install: conda install -c conda-forge cellxgene-census")
        sys.exit(1)
    
    process_all_datasets(input_csv, output_csv, tissue_filter, logger)
    
    logger.info(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log saved to: {log_file}")

