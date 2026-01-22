#!/usr/bin/env python3
"""
Step 4: Filter datasets by organism, tissue, and publication status

Filters the complete dataset CSV based on:
- Organism (exact match)
- Tissue (regex pattern matching)
- Publication status (--no-preprints flag)

IMPORTANT: When using --no-preprints, ONLY is_preprint=FALSE is accepted.
Blank values and TRUE are both filtered out for strict quality control.

Usage:
    python bin/4_filter_datasets.py --organism "Homo sapiens" --output filtered.csv
    python bin/4_filter_datasets.py --organism "Homo sapiens" --tissue "lung" --no-preprints
    python bin/4_filter_datasets.py --organism "Homo sapiens" --tissue "pancreas|isle" --no-preprints
"""

import os
import sys
import csv
import re
import argparse

# Default configuration
DATA_DIR = "data"
DEFAULT_INPUT = os.path.join(DATA_DIR, "all_datasets_complete.csv")


def filter_datasets(input_csv, output_csv, organism=None, tissue_pattern=None, 
                   no_preprints=False, exclude_cancer=False, disease=None):
    """
    Filter datasets based on criteria.
    
    Args:
        input_csv: Input CSV file path
        output_csv: Output CSV file path
        organism: Organism to filter for (exact match, case-insensitive)
        tissue_pattern: Regex pattern for tissue filtering
        no_preprints: If True, exclude preprints
        exclude_cancer: If True, exclude cancer/carcinoma datasets
        disease: Disease to filter for (substring match)
    """
    
    # Load input CSV
    if not os.path.exists(input_csv):
        print(f"ERROR: Input file not found: {input_csv}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading datasets from: {input_csv}")
    with open(input_csv, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    
    print(f"Loaded {len(rows)} datasets")
    
    # Apply filters
    filtered_rows = []
    
    for row in rows:
        # Filter by organism
        if organism:
            row_organism = row.get("organism", "")
            if organism.lower() not in row_organism.lower():
                continue
        
        # Filter by tissue (regex)
        if tissue_pattern:
            row_tissue = row.get("tissue", "")
            if not re.search(tissue_pattern, row_tissue, re.IGNORECASE):
                continue
        
        # Filter by preprint status (strict: ONLY accept FALSE)
        if no_preprints:
            is_preprint = row.get("is_preprint", "").strip()
            # ONLY accept explicit FALSE - reject TRUE or blank
            if is_preprint.upper() != "FALSE":
                continue
        
        # Exclude cancer/carcinoma datasets (no normal cells expected)
        if exclude_cancer:
            row_disease = row.get("disease", "").lower()
            if "cancer" in row_disease or "carcinoma" in row_disease:
                continue
        
        # Filter by disease
        if disease:
            row_disease = row.get("disease", "")
            if disease.lower() not in row_disease.lower():
                continue
        
        filtered_rows.append(row)
    
    # Write output CSV
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)
    
    # Print summary
    print(f"\nFiltering Summary:")
    print(f"  Original datasets: {len(rows)}")
    print(f"  Filtered datasets: {len(filtered_rows)}")
    print(f"  Removed: {len(rows) - len(filtered_rows)}")
    print(f"\nFilters applied:")
    if organism:
        print(f"  - Organism: {organism}")
    if tissue_pattern:
        print(f"  - Tissue pattern: {tissue_pattern}")
    if no_preprints:
        print(f"  - Exclude preprints: Yes")
    if exclude_cancer:
        print(f"  - Exclude cancer/carcinoma: Yes")
    if disease:
        print(f"  - Disease: {disease}")
    print(f"\nOutput saved to: {output_csv}")


def main():
    parser = argparse.ArgumentParser(
        description="Filter CellxGene datasets by organism, tissue, and publication status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Filter for Homo sapiens
  python 4_filter_datasets.py --organism "Homo sapiens" --output homo_sapiens.csv
  
  # Filter for Homo sapiens lung tissue (no preprints, exclude cancer)
  python 4_filter_datasets.py --organism "Homo sapiens" --tissue "lung" \\
    --no-preprints --exclude-cancer --output homo_sapiens_lung_harvester.csv
  
  # Filter for Homo sapiens pancreas (including islets)
  python 4_filter_datasets.py --organism "Homo sapiens" --tissue "pancreas|isle" \\
    --no-preprints --exclude-cancer --output homo_sapiens_pancreas_harvester.csv
  
  # Filter for disease datasets (if you DO want cancer data)
  python 4_filter_datasets.py --organism "Homo sapiens" --disease "cancer" \\
    --output homo_sapiens_cancer.csv
        """
    )
    
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help=f"Input CSV file (default: {DEFAULT_INPUT})"
    )
    
    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV file path"
    )
    
    parser.add_argument(
        "--organism",
        help="Filter by organism (case-insensitive, e.g., 'Homo sapiens')"
    )
    
    parser.add_argument(
        "--tissue",
        help="Filter by tissue using regex pattern (e.g., 'lung', 'pancreas|isle')"
    )
    
    parser.add_argument(
        "--no-preprints",
        action="store_true",
        help="Exclude preprints (only include peer-reviewed publications)"
    )
    
    parser.add_argument(
        "--exclude-cancer",
        action="store_true",
        help="Exclude cancer/carcinoma datasets (no normal cells expected in these)"
    )
    
    parser.add_argument(
        "--disease",
        help="Filter by disease (case-insensitive substring match)"
    )
    
    args = parser.parse_args()
    
    # Validate that at least one filter is provided
    if not any([args.organism, args.tissue, args.no_preprints, args.exclude_cancer, args.disease]):
        print("WARNING: No filters specified. Output will be identical to input.")
    
    print("=" * 70)
    print("CellxGene Data Harvester - Step 4: Filter Datasets")
    print("=" * 70)
    
    filter_datasets(
        input_csv=args.input,
        output_csv=args.output,
        organism=args.organism,
        tissue_pattern=args.tissue,
        no_preprints=args.no_preprints,
        exclude_cancer=args.exclude_cancer,
        disease=args.disease
    )


if __name__ == "__main__":
    main()
