#!/usr/bin/env python3
"""
Step 5: Count normal cells in filtered datasets using CellxGene Census

Uses the cellxgene_census Python package to query datasets directly
without downloading H5AD files. Much faster and more efficient!

POPULATES:
- normal_cell_count: Count of normal adult cells
- embedding: Available embedding types (e.g., "umap|tsne|pca")
- organ: Tissue general classification from Census
- development stage information (labels and ontology IDs)

FILTERS APPLIED:
- Only adult development stages (age >= 18 years OR contains "adult")
- Only normal/healthy cells (disease == "normal")

Age parsing examples:
- "18-year-old human stage" -> age 18 (included)
- "25 year old" -> age 25 (included)  
- "10-year-old" -> age 10 (excluded, < 18)
- "adult" -> always included
- "fetal", "child" -> always excluded

Usage:
    python bin/5_count_normal_cells.py <filtered_csv>
    
Example:
    python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
"""

import os
import sys
import csv
import cellxgene_census
from typing import Optional


# Development stage filtering strategy:
# 1. Include "adult" stages
# 2. Include stages with age >= 18 years (e.g., "18-year-old", "25 year old")
# 3. Exclude embryonic, fetal, newborn, child, adolescent stages explicitly
#
# Common patterns in development stage labels:
# - "18-year-old human stage"
# - "25 year old"
# - "adult"
# - "10-year-old" (exclude, < 18)

EXCLUDE_DEVELOPMENTAL_STAGES = [
    'embryo', 'fetal', 'fetus', 'newborn', 'infant', 'child', 
    'adolescent', 'juvenile', 'prenatal', 'postnatal day'
]

import re

def extract_age_from_stage(stage_label: str) -> Optional[int]:
    """
    Extract age in years from development stage label.
    
    Examples:
        "18-year-old human stage" -> 18
        "25 year old" -> 25
        "10-year-old" -> 10
        "adult" -> None (handled separately)
        
    Returns:
        Age in years, or None if no age found
    """
    if not stage_label:
        return None
    
    # Pattern: capture number before "year" or "yr"
    # Matches: "18-year-old", "25 year old", "30-yr-old", "15 years old"
    pattern = r'(\d+)[- ]?(?:year|yr)'
    match = re.search(pattern, stage_label.lower())
    
    if match:
        return int(match.group(1))
    
    return None


def count_normal_adult_cells_census(dataset_version_id: str) -> Optional[dict]:
    """
    Count normal adult cells and capture all Census metadata.
    
    Returns dict with cell counts, embeddings, and Census metadata fields.
    """
    try:
        # Open census
        with cellxgene_census.open_soma(census_version="stable") as census:
            # Get AnnData for this specific dataset
            adata = cellxgene_census.get_anndata(
                census=census,
                organism="Homo sapiens",
                obs_value_filter=f"dataset_id == '{dataset_version_id}'"
            )
            
            if adata is None or adata.n_obs == 0:
                print(f"  WARNING: No cells found for dataset {dataset_version_id}")
                return {
                    'normal_adult_count': 0,
                    'total_count': 0,
                    'adult_count': 0,
                    'embeddings': '',
                    'tissue_general': '',
                    'census_tissue': '',
                    'census_disease': '',
                    'census_development_stage': '',
                    'tissue_general_ontology_term_id': '',
                    'tissue_ontology_term_id': '',
                    'assay_ontology_term_id': '',
                    'cell_type_ontology_term_id': '',
                    'disease_ontology_term_id': '',
                    'development_stage_ontology_term_id': '',
                    'sex_ontology_term_id': '',
                    'is_primary_data': '',
                    'donor_id_count': 0,
                    'development_stage_summary': ''
                }
            
            # Extract embeddings from obsm
            embeddings = []
            if hasattr(adata, 'obsm') and adata.obsm is not None:
                for key in adata.obsm.keys():
                    emb_name = key.replace('X_', '') if key.startswith('X_') else key
                    embeddings.append(emb_name)
            embeddings_str = '|'.join(sorted(embeddings)) if embeddings else ''
            
            # Get obs DataFrame
            obs_df = adata.obs
            total_count = len(obs_df)
            
            # Helper function to get most common value
            def get_most_common(column_name):
                if column_name in obs_df.columns:
                    counts = obs_df[column_name].value_counts()
                    if len(counts) > 0:
                        return str(counts.index[0])
                return ''
            
            # Extract human-readable Census fields (most common values)
            tissue_general = get_most_common('tissue_general')
            census_tissue = get_most_common('tissue')
            census_disease = get_most_common('disease')
            census_development_stage = get_most_common('development_stage')
            
            # Extract ontology IDs (most common values)
            tissue_general_ontology_term_id = get_most_common('tissue_general_ontology_term_id')
            tissue_ontology_term_id = get_most_common('tissue_ontology_term_id')
            assay_ontology_term_id = get_most_common('assay_ontology_term_id')
            cell_type_ontology_term_id = get_most_common('cell_type_ontology_term_id')
            disease_ontology_term_id = get_most_common('disease_ontology_term_id')
            development_stage_ontology_term_id = get_most_common('development_stage_ontology_term_id')
            sex_ontology_term_id = get_most_common('sex_ontology_term_id')
            
            # Extract is_primary_data (most common boolean)
            is_primary_data = get_most_common('is_primary_data')
            
            # Count unique donors
            donor_id_count = 0
            if 'donor_id' in obs_df.columns:
                donor_id_count = obs_df['donor_id'].nunique()
            
            # Create development stage summary (top 3 stages)
            dev_stage_summary = ''
            if 'development_stage' in obs_df.columns:
                stage_counts = obs_df['development_stage'].value_counts()
                summary_parts = []
                for stage, count in list(stage_counts.head(3).items()):
                    summary_parts.append(f"{stage}: {count:,}")
                dev_stage_summary = "; ".join(summary_parts)
            
            print(f"  Census metadata extracted:")
            print(f"    Tissue (general): {tissue_general if tissue_general else 'N/A'}")
            print(f"    Tissue (specific): {census_tissue if census_tissue else 'N/A'}")
            print(f"    Development stages: {dev_stage_summary if dev_stage_summary else 'N/A'}")
            print(f"    Embeddings: {embeddings_str if embeddings_str else 'None'}")
            print(f"    Unique donors: {donor_id_count}")
            
            # Filter for adult stages (age >= 18 OR contains "adult")
            adult_mask = []
            if 'development_stage' in obs_df.columns:
                dev_values = obs_df['development_stage'].astype(str)
                
                for stage_val in dev_values:
                    stage_lower = stage_val.lower()
                    
                    # Exclude non-adult developmental stages
                    exclude = False
                    for exclude_term in EXCLUDE_DEVELOPMENTAL_STAGES:
                        if exclude_term in stage_lower:
                            exclude = True
                            break
                    
                    if exclude:
                        adult_mask.append(False)
                        continue
                    
                    # Include if contains "adult"
                    if 'adult' in stage_lower:
                        adult_mask.append(True)
                        continue
                    
                    # Include if age >= 18
                    age = extract_age_from_stage(stage_val)
                    if age is not None and age >= 18:
                        adult_mask.append(True)
                        continue
                    
                    adult_mask.append(False)
                
                adult_df = obs_df[adult_mask]
            else:
                adult_df = obs_df  # If no dev stage, include all
            
            adult_count = len(adult_df)
            
            if adult_count == 0:
                print(f"  WARNING: No adult cells found")
                return {
                    'normal_adult_count': 0,
                    'total_count': total_count,
                    'adult_count': 0,
                    'embeddings': embeddings_str,
                    'tissue_general': tissue_general,
                    'census_tissue': census_tissue,
                    'census_disease': census_disease,
                    'census_development_stage': census_development_stage,
                    'tissue_general_ontology_term_id': tissue_general_ontology_term_id,
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
            
            # Count normal cells within adult population
            normal_adult_count = 0
            if 'disease' in adult_df.columns:
                disease_values = adult_df['disease'].astype(str).str.lower()
                normal_mask = (
                    disease_values.str.contains('normal', na=False) | 
                    disease_values.str.contains('pato:0000461', na=False)
                )
                normal_adult_count = normal_mask.sum()
            
            return {
                'normal_adult_count': int(normal_adult_count),
                'total_count': int(total_count),
                'adult_count': int(adult_count),
                'embeddings': embeddings_str,
                'tissue_general': tissue_general,
                'census_tissue': census_tissue,
                'census_disease': census_disease,
                'census_development_stage': census_development_stage,
                'tissue_general_ontology_term_id': tissue_general_ontology_term_id,
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
            
    except Exception as e:
        print(f"  ERROR querying Census: {e}")
        import traceback
        traceback.print_exc()
        return None
    """
    Count normal adult cells and capture development stage info, embeddings, and organ using CellxGene Census API.
    
    Args:
        dataset_version_id: Dataset version UUID
        
    Returns:
        Dict with normal_adult_count, total_count, adult_count, dev_stage_summary, 
        primary_stage, primary_stage_id, embeddings, tissue_general
        or None if failed
    """
    try:
        # Open census
        with cellxgene_census.open_soma(census_version="stable") as census:
            # Get AnnData for this specific dataset to capture embeddings
            adata = cellxgene_census.get_anndata(
                census=census,
                organism="Homo sapiens",
                obs_value_filter=f"dataset_id == '{dataset_version_id}'"
            )
            
            if adata is None or adata.n_obs == 0:
                print(f"  WARNING: No cells found for dataset {dataset_version_id}")
                return {
                    'normal_adult_count': 0,
                    'total_count': 0,
                    'adult_count': 0,
                    'dev_stage_summary': '',
                    'primary_stage': '',
                    'primary_stage_id': '',
                    'embeddings': '',
                    'tissue_general': ''
                }
            
            # Extract embeddings from obsm (e.g., X_umap, X_tsne, X_pca)
            embeddings = []
            if hasattr(adata, 'obsm') and adata.obsm is not None:
                for key in adata.obsm.keys():
                    # Remove X_ prefix if present for cleaner display
                    emb_name = key.replace('X_', '') if key.startswith('X_') else key
                    embeddings.append(emb_name)
            embeddings_str = '|'.join(sorted(embeddings)) if embeddings else ''
            
            # Get obs DataFrame for further analysis
            obs_df = adata.obs
            total_count = len(obs_df)
            
            # Extract tissue_general (organ-level classification)
            # Try multiple potential fields in order of preference
            tissue_general = ''
            
            # Option 1: tissue_general (if it exists)
            if 'tissue_general' in obs_df.columns:
                tissue_counts = obs_df['tissue_general'].value_counts()
                if len(tissue_counts) > 0:
                    tissue_general = str(tissue_counts.index[0])
                    print(f"  Found tissue_general: {tissue_general}")
            
            # Option 2: tissue_general_ontology_term_id (if tissue_general not found)
            elif 'tissue_general_ontology_term_id' in obs_df.columns:
                tissue_counts = obs_df['tissue_general_ontology_term_id'].value_counts()
                if len(tissue_counts) > 0:
                    tissue_general = str(tissue_counts.index[0])
                    print(f"  Found tissue_general_ontology_term_id: {tissue_general}")
            
            # Option 3: Derive from tissue field (fallback)
            elif 'tissue' in obs_df.columns:
                tissue_counts = obs_df['tissue'].value_counts()
                if len(tissue_counts) > 0:
                    # Use most common tissue as organ approximation
                    tissue_general = str(tissue_counts.index[0])
                    print(f"  Using tissue as organ (fallback): {tissue_general}")
            
            if not tissue_general:
                print(f"  No organ/tissue_general field found")
            
            # Check for development_stage_ontology_term_id and development_stage columns
            dev_stage_id_col = 'development_stage_ontology_term_id' if 'development_stage_ontology_term_id' in obs_df.columns else None
            dev_stage_label_col = 'development_stage' if 'development_stage' in obs_df.columns else None
            
            if not dev_stage_id_col and not dev_stage_label_col:
                print(f"  WARNING: No development stage columns found")
                return {
                    'normal_adult_count': 0,
                    'total_count': total_count,
                    'adult_count': 0,
                    'dev_stage_summary': 'No development stage data',
                    'primary_stage': '',
                    'primary_stage_id': '',
                    'embeddings': embeddings_str,
                    'tissue_general': tissue_general
                }
            
            # Get development stage distribution
            stage_counts = {}
            if dev_stage_id_col:
                for idx, row in obs_df.iterrows():
                    stage_id = str(row[dev_stage_id_col])
                    stage_label = str(row[dev_stage_label_col]) if dev_stage_label_col else stage_id
                    key = f"{stage_label}|{stage_id}"  # Combined key
                    stage_counts[key] = stage_counts.get(key, 0) + 1
            elif dev_stage_label_col:
                for stage_label in obs_df[dev_stage_label_col]:
                    stage_label = str(stage_label)
                    key = f"{stage_label}|"
                    stage_counts[key] = stage_counts.get(key, 0) + 1
            
            # Sort by count
            sorted_stages = sorted(stage_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Primary stage (most common)
            primary_stage = ''
            primary_stage_id = ''
            if sorted_stages:
                primary_key = sorted_stages[0][0]
                primary_stage, primary_stage_id = primary_key.split('|')
            
            # Create summary (top 3 stages)
            summary_parts = []
            for stage_key, count in sorted_stages[:3]:
                stage_label, stage_id = stage_key.split('|')
                summary_parts.append(f"{stage_label}: {count:,}")
            dev_stage_summary = "; ".join(summary_parts)
            
            print(f"  Development stages: {dev_stage_summary}")
            print(f"  Embeddings: {embeddings_str if embeddings_str else 'None'}")
            if tissue_general:
                print(f"  Organ: {tissue_general}")
            
            # Filter for adult stages (age >= 18 OR contains "adult")
            dev_col = dev_stage_label_col or dev_stage_id_col
            dev_values = obs_df[dev_col].astype(str)
            
            adult_mask = []
            for stage_val in dev_values:
                stage_lower = stage_val.lower()
                
                # Exclude non-adult developmental stages explicitly
                exclude = False
                for exclude_term in EXCLUDE_DEVELOPMENTAL_STAGES:
                    if exclude_term in stage_lower:
                        exclude = True
                        break
                
                if exclude:
                    adult_mask.append(False)
                    continue
                
                # Include if contains "adult"
                if 'adult' in stage_lower:
                    adult_mask.append(True)
                    continue
                
                # Include if age >= 18
                age = extract_age_from_stage(stage_val)
                if age is not None and age >= 18:
                    adult_mask.append(True)
                    continue
                
                # Otherwise exclude
                adult_mask.append(False)
            
            adult_df = obs_df[adult_mask]
            adult_count = len(adult_df)
            
            if adult_count == 0:
                print(f"  WARNING: No adult cells found")
                return {
                    'normal_adult_count': 0,
                    'total_count': total_count,
                    'adult_count': 0,
                    'dev_stage_summary': dev_stage_summary,
                    'primary_stage': primary_stage,
                    'primary_stage_id': primary_stage_id,
                    'embeddings': embeddings_str,
                    'tissue_general': tissue_general
                }
            
            # Look for disease column in adult cells
            disease_col = None
            for col in adult_df.columns:
                if 'disease' in col.lower():
                    disease_col = col
                    break
            
            if not disease_col:
                print(f"  WARNING: No disease column found")
                return {
                    'normal_adult_count': 0,
                    'total_count': total_count,
                    'adult_count': adult_count,
                    'dev_stage_summary': dev_stage_summary,
                    'primary_stage': primary_stage,
                    'primary_stage_id': primary_stage_id,
                    'embeddings': embeddings_str,
                    'tissue_general': tissue_general
                }
            
            # Count normal cells within adult population
            disease_values = adult_df[disease_col].astype(str).str.lower()
            normal_mask = (
                disease_values.str.contains('normal', na=False) | 
                disease_values.str.contains('pato:0000461', na=False)
            )
            normal_adult_count = normal_mask.sum()
            
            return {
                'normal_adult_count': int(normal_adult_count),
                'total_count': int(total_count),
                'adult_count': int(adult_count),
                'dev_stage_summary': dev_stage_summary,
                'primary_stage': primary_stage,
                'primary_stage_id': primary_stage_id,
                'embeddings': embeddings_str,
                'tissue_general': tissue_general
            }
            
    except Exception as e:
        print(f"  ERROR querying Census: {e}")
        import traceback
        traceback.print_exc()
        return None


def add_normal_counts(input_csv, output_csv):
    """Add normal_cell_count column to the CSV with incremental saves."""
    
    # Load input CSV
    if not os.path.exists(input_csv):
        print(f"ERROR: Input file not found: {input_csv}", file=sys.stderr)
        print("Please run step 4 filter first.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading datasets from: {input_csv}")
    with open(input_csv, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        original_fieldnames = reader.fieldnames or []
    
    print(f"Loaded {len(rows)} datasets")
    
    # Define the exact column order
    # Columns 1-6: Core dataset info
    ordered_columns = [
        'collection_name',
        'dataset_title',
        'normal_cell_count',  # Added by step 5
        'total_cell_count',
        'author_cell_type',
        'embedding',
    ]
    
    # Columns 7-15: Human-readable fields (visible)
    ordered_columns += [
        'tissue_general',  # From Census
        'tissue',  # Existing from Collections API
        'disease',  # Existing from Collections API
        'development_stage',  # From Census
        'first_author',
        'journal',
        'year',
        'collection_url',
        'explorer_url',
    ]
    
    # Remaining columns: Technical IDs and metadata
    ordered_columns += [
        'collection_id',
        'collection_version_id',
        'dataset_id',
        'dataset_version_id',
        'is_preprint',
        'revised_at',
        'visibility',
        'organism',
        'filter_normal',
        'metric',
        'save_scores',
        'save_cluster_summary',
        'save_annotation',
        'h5ad_url',
    ]
    
    # Census ontology IDs and technical fields (right side)
    ordered_columns += [
        'tissue_general_ontology_term_id',
        'tissue_ontology_term_id',
        'assay_ontology_term_id',
        'cell_type_ontology_term_id',
        'disease_ontology_term_id',
        'development_stage_ontology_term_id',
        'sex_ontology_term_id',
        'is_primary_data',
        'donor_id_count',
        'development_stage_summary',
    ]
    
    # Get existing fieldnames from input CSV
    existing_fields = set(original_fieldnames)
    
    # Build final fieldnames list
    # Start with ordered columns that exist, then add any remaining fields
    fieldnames = []
    for col in ordered_columns:
        if col in existing_fields or col in [
            'normal_cell_count', 'tissue_general', 'development_stage',
            'tissue_general_ontology_term_id', 'tissue_ontology_term_id',
            'assay_ontology_term_id', 'cell_type_ontology_term_id',
            'disease_ontology_term_id', 'development_stage_ontology_term_id',
            'sex_ontology_term_id', 'is_primary_data', 'donor_id_count',
            'development_stage_summary'
        ]:
            fieldnames.append(col)
    
    # Add any remaining original fields not in ordered list
    for field in original_fieldnames:
        if field not in fieldnames:
            fieldnames.append(field)
    
    # Initialize new columns with empty values
    new_census_columns = [
        'normal_cell_count', 'tissue_general', 'development_stage',
        'tissue_general_ontology_term_id', 'tissue_ontology_term_id',
        'assay_ontology_term_id', 'cell_type_ontology_term_id',
        'disease_ontology_term_id', 'development_stage_ontology_term_id',
        'sex_ontology_term_id', 'is_primary_data', 'donor_id_count',
        'development_stage_summary'
    ]
    
    for row in rows:
        for col in new_census_columns:
            if col not in row:
                row[col] = ""
    
    # Write initial CSV with empty normal_cell_count values
    print(f"\nInitializing output file: {output_csv}")
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✓ Output file created with {len(rows)} datasets")
    
    # Process each dataset using Census API
    print(f"\nQuerying CellxGene Census for normal adult cell counts...")
    print(f"(Using Census API - no file downloads required!)")
    print(f"FILTERS: Age >= 18 years OR 'adult' stage + Normal disease status")
    print(f"Progress saved after each dataset - safe to interrupt!")
    
    successful = 0
    failed = 0
    skipped = 0
    
    for i, row in enumerate(rows, 1):
        dataset_version_id = row.get("dataset_version_id", "")
        total_cells_csv = row.get("total_cell_count", "0")
        
        # Progress indicator
        print(f"\n[{i}/{len(rows)}] Processing {dataset_version_id}")
        
        # Skip if missing ID
        if not dataset_version_id:
            print(f"  Skipped: Missing dataset_version_id")
            row["normal_cell_count"] = ""
            skipped += 1
            # Save progress
            with open(output_csv, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            continue
        
        print(f"  Expected cells (from CSV): {total_cells_csv}")
        
        # Count normal adult cells using Census
        result = count_normal_adult_cells_census(dataset_version_id)
        
        if result is not None:
            # Populate all Census fields
            row["normal_cell_count"] = str(result['normal_adult_count'])
            row["embedding"] = result['embeddings']
            row["tissue_general"] = result['tissue_general']
            row["development_stage"] = result['census_development_stage']
            
            # Populate ontology IDs and technical fields
            row["tissue_general_ontology_term_id"] = result['tissue_general_ontology_term_id']
            row["tissue_ontology_term_id"] = result['tissue_ontology_term_id']
            row["assay_ontology_term_id"] = result['assay_ontology_term_id']
            row["cell_type_ontology_term_id"] = result['cell_type_ontology_term_id']
            row["disease_ontology_term_id"] = result['disease_ontology_term_id']
            row["development_stage_ontology_term_id"] = result['development_stage_ontology_term_id']
            row["sex_ontology_term_id"] = result['sex_ontology_term_id']
            row["is_primary_data"] = result['is_primary_data']
            row["donor_id_count"] = str(result['donor_id_count'])
            row["development_stage_summary"] = result['development_stage_summary']
            
            # Display results
            census_total = result['total_count']
            adult_count = result['adult_count']
            normal_adult_count = result['normal_adult_count']
            
            print(f"  ✓ Success: {normal_adult_count:,} normal ADULT cells")
            print(f"    (Adult cells: {adult_count:,} / Total: {census_total:,})")
            
            # Note if Census total differs from CSV
            try:
                csv_total = int(total_cells_csv) if total_cells_csv else 0
                if census_total != csv_total and csv_total > 0:
                    print(f"    Note: Census count ({census_total:,}) differs from CSV ({csv_total:,})")
            except (ValueError, TypeError):
                pass
            
            successful += 1
        else:
            # Clear all Census fields on failure
            row["normal_cell_count"] = ""
            row["embedding"] = ""
            row["tissue_general"] = ""
            row["development_stage"] = ""
            row["tissue_general_ontology_term_id"] = ""
            row["tissue_ontology_term_id"] = ""
            row["assay_ontology_term_id"] = ""
            row["cell_type_ontology_term_id"] = ""
            row["disease_ontology_term_id"] = ""
            row["development_stage_ontology_term_id"] = ""
            row["sex_ontology_term_id"] = ""
            row["is_primary_data"] = ""
            row["donor_id_count"] = ""
            row["development_stage_summary"] = ""
            print(f"  ✗ Failed: Could not count normal adult cells")
            failed += 1
        
        # CRITICAL: Save progress after EVERY dataset
        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"  Progress saved ({successful + failed + skipped}/{len(rows)} complete)")
    
    # Final summary
    print(f"\n{'='*70}")
    print(f"COMPLETE!")
    print(f"{'='*70}")
    print(f"Results:")
    print(f"  Total datasets: {len(rows)}")
    print(f"  Successfully processed: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Skipped (missing IDs): {skipped}")
    print(f"\nFinal output: {output_csv}")
    print(f"\nNote: Counts are for cells with:")
    print(f"      - Age >= 18 years OR 'adult' in development stage")
    print(f"      - Normal disease status")


if __name__ == "__main__":
    print("=" * 70)
    print("CellxGene Data Harvester - Step 5: Count Normal Adult Cells")
    print("Filters: Age >= 18 years OR 'adult' stage + Normal disease")
    print("=" * 70)
    
    # Check for input CSV argument
    if len(sys.argv) != 2:
        print("\nUsage: python bin/5_count_normal_cells.py <filtered_csv>")
        print("\nExample:")
        print("  python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    
    # Generate output filename
    base = os.path.splitext(input_csv)[0]
    output_csv = f"{base}_with_normal_counts.csv"
    
    # Check dependencies
    try:
        import cellxgene_census
    except ImportError:
        print(f"\nERROR: cellxgene_census package not found", file=sys.stderr)
        print("Install with: conda install -c conda-forge cellxgene-census", file=sys.stderr)
        sys.exit(1)
    
    add_normal_counts(input_csv, output_csv)
    print(f"\nDone! Final output: {output_csv}")
