#!/usr/bin/env python3
"""
Step 4: Filter datasets
Uses pandas for clean filtering operations
"""

import sys
import re
import pandas as pd

def filter_datasets(input_csv, output_csv, organism=None, tissue_pattern=None,
                   no_preprints=False, exclude_cancer=False, exclude_spatial=False, disease=None):
    """Filter datasets using pandas boolean indexing"""
    
    # Load data
    df = pd.read_csv(input_csv)
    print(f"Loaded {len(df)} datasets from {input_csv}")
    
    initial_count = len(df)
    
    # Filter by organism
    if organism:
        df = df[df['organism'].astype(str).str.lower() == organism.lower()]
        print(f"After organism filter: {len(df)} datasets")
    
    # Filter by tissue pattern (checks 'tissue' field from Collections API)
    # Note: 'tissue_general' is populated in Step 5 (Census), not available yet
    if tissue_pattern:
        pattern = re.compile(tissue_pattern, re.IGNORECASE)
        
        # Check tissue field (from Collections API) - convert to string to avoid dtype issues
        tissue_match = df['tissue'].astype(str).str.contains(pattern, na=False)
        
        # Also check tissue_general if it exists (defensive coding)
        if 'tissue_general' in df.columns:
            tissue_general_match = df['tissue_general'].astype(str).str.contains(pattern, na=False)
            df = df[tissue_match | tissue_general_match]
        else:
            df = df[tissue_match]
        
        print(f"After tissue filter: {len(df)} datasets")
    
    # Filter by preprint status
    if no_preprints:
        # Convert to string and compare case-insensitively
        preprint_values = df['is_preprint'].astype(str).str.lower()
        df = df[preprint_values == 'false']
        print(f"After preprint filter: {len(df)} datasets")
    
    # Exclude cancer
    if exclude_cancer:
        cancer_mask = (
            df['disease'].astype(str).str.lower().str.contains('cancer', na=False) |
            df['disease'].astype(str).str.lower().str.contains('carcinoma', na=False)
        )
        df = df[~cancer_mask]
        print(f"After cancer filter: {len(df)} datasets")
    
    # Exclude spatial transcriptomics
    if exclude_spatial:
        spatial_terms = ['spatial', 'visium', 'slide-seq', 'slideseq', 'merfish',
                        'seqfish', 'cosmx', 'xenium', 'stereo-seq', 'stereoseq']
        
        spatial_mask = pd.Series([False] * len(df), index=df.index)
        for term in spatial_terms:
            spatial_mask |= df['dataset_title'].astype(str).str.lower().str.contains(term, na=False)
            spatial_mask |= df['disease'].astype(str).str.lower().str.contains(term, na=False)
            spatial_mask |= df['tissue'].astype(str).str.lower().str.contains(term, na=False)
        
        df = df[~spatial_mask]
        print(f"After spatial filter: {len(df)} datasets")
    
    # Filter by disease
    if disease:
        df = df[df['disease'].astype(str).str.lower().str.contains(disease.lower(), na=False)]
        print(f"After disease filter: {len(df)} datasets")
    
    # Save filtered results
    df.to_csv(output_csv, index=False)
    
    print(f"\nFiltering Summary:")
    print(f"  Original datasets: {initial_count}")
    print(f"  Filtered datasets: {len(df)}")
    print(f"  Removed: {initial_count - len(df)}")
    print(f"\nFilters applied:")
    if organism:
        print(f"  - Organism: {organism}")
    if tissue_pattern:
        print(f"  - Tissue pattern: {tissue_pattern}")
    if no_preprints:
        print(f"  - Exclude preprints: Yes")
    if exclude_cancer:
        print(f"  - Exclude cancer/carcinoma: Yes")
    if exclude_spatial:
        print(f"  - Exclude spatial transcriptomics: Yes")
    if disease:
        print(f"  - Disease: {disease}")
    
    print(f"\nOutput saved to: {output_csv}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Filter CellxGene datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Filter for Homo sapiens lung tissue (recommended)
  python 4_filter_datasets.py --input data/all_datasets_complete.csv \\
    --organism "Homo sapiens" --tissue "lung" \\
    --no-preprints --exclude-cancer --exclude-spatial --output homo_sapiens_lung.csv
  
  # Filter for pancreas
  python 4_filter_datasets.py --input data/all_datasets_complete.csv \\
    --organism "Homo sapiens" --tissue "pancreas|isle" \\
    --no-preprints --exclude-cancer --exclude-spatial --output homo_sapiens_pancreas.csv
        """
    )
    
    parser.add_argument("--input", default="data/all_datasets_complete.csv")
    parser.add_argument("--output", required=True)
    parser.add_argument("--organism")
    parser.add_argument("--tissue")
    parser.add_argument("--no-preprints", action="store_true")
    parser.add_argument("--exclude-cancer", action="store_true")
    parser.add_argument("--exclude-spatial", action="store_true")
    parser.add_argument("--disease")
    
    args = parser.parse_args()
    
    if not any([args.organism, args.tissue, args.no_preprints, args.exclude_cancer, args.exclude_spatial, args.disease]):
        print("WARNING: No filters specified. Output will be identical to input.")
    
    filter_datasets(
        input_csv=args.input,
        output_csv=args.output,
        organism=args.organism,
        tissue_pattern=args.tissue,
        no_preprints=args.no_preprints,
        exclude_cancer=args.exclude_cancer,
        exclude_spatial=args.exclude_spatial,
        disease=args.disease
    )
