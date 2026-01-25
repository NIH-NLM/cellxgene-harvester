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
    
    # Add columns: normal_cell_count, organ (tissue_general), development_stage_summary, primary_development_stage, primary_stage_ontology_id
    fieldnames = original_fieldnames.copy()
    
    new_columns = [
        ("normal_cell_count", "total_cell_count"),  # Insert before total_cell_count
        ("organ", "tissue"),  # Insert before tissue (or after if tissue not found)
        ("development_stage_summary", None),  # Append at end
        ("primary_development_stage", None),
        ("primary_stage_ontology_id", None)
    ]
    
    for col_name, insert_before in new_columns:
        if col_name not in fieldnames:
            if insert_before and insert_before in fieldnames:
                idx = fieldnames.index(insert_before)
                fieldnames.insert(idx, col_name)
            else:
                fieldnames.append(col_name)
    
    # Initialize all new columns with empty values
    for row in rows:
        for col_name, _ in new_columns:
            if col_name not in row:
                row[col_name] = ""
    
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
            # Unpack results
            normal_adult_count = result['normal_adult_count']
            census_total = result['total_count']
            adult_count = result['adult_count']
            dev_stage_summary = result['dev_stage_summary']
            primary_stage = result['primary_stage']
            primary_stage_id = result['primary_stage_id']
            embeddings = result['embeddings']
            tissue_general = result['tissue_general']
            
            # Update row with all information
            row["normal_cell_count"] = str(normal_adult_count)
            row["embedding"] = embeddings  # Populate the existing embedding column
            row["organ"] = tissue_general  # Add organ (tissue_general from Census)
            row["development_stage_summary"] = dev_stage_summary
            row["primary_development_stage"] = primary_stage
            row["primary_stage_ontology_id"] = primary_stage_id
            
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
            row["normal_cell_count"] = ""
            row["embedding"] = ""
            row["organ"] = ""
            row["development_stage_summary"] = ""
            row["primary_development_stage"] = ""
            row["primary_stage_ontology_id"] = ""
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
