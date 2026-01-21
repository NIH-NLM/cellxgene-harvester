#!/usr/bin/env python3
"""
Step 4: Count normal cells in each dataset

Downloads H5AD files and counts cells where disease == "normal".
Adds normal_cell_count column to the CSV.

This step is important for quality control - we want to know how many
cells are from healthy/normal samples versus diseased samples.

Usage:
    python bin/4_count_normal_cells.py
"""

import os
import sys
import csv
import time
import tempfile
import scanpy as sc
import pandas as pd
from typing import Optional

# Input/Output configuration
DATA_DIR = "data"
INPUT_CSV = os.path.join(DATA_DIR, "all_datasets_complete.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "all_datasets_with_normal_counts.csv")

# Cache configuration
CACHE_DIR = "datasets_cache"
CACHE_ENABLED = True  # Set to False to always re-download


def download_h5ad(url: str, dataset_version_id: str) -> Optional[str]:
    """
    Download H5AD file with caching.
    
    Args:
        url: Direct download URL
        dataset_version_id: Dataset version ID for filename
        
    Returns:
        Path to downloaded file or None if failed
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{dataset_version_id}.h5ad")
    
    # Return cached file if it exists
    if CACHE_ENABLED and os.path.exists(cache_path):
        return cache_path
    
    # Download file
    try:
        import requests
        print(f"  Downloading {dataset_version_id}...")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        # Write to cache
        with open(cache_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return cache_path
        
    except Exception as e:
        print(f"  Warning: Download failed: {e}", file=sys.stderr)
        return None


def count_normal_cells(h5ad_path: str) -> Optional[int]:
    """
    Count cells where disease/disease_ontology_term_id indicates "normal".
    
    Args:
        h5ad_path: Path to H5AD file
        
    Returns:
        Number of normal cells or None if failed
    """
    try:
        # Load dataset
        adata = sc.read_h5ad(h5ad_path)
        
        # Check for disease annotation columns
        disease_columns = [
            'disease',
            'disease_ontology_term_id',
            'assay_ontology_term_id',
        ]
        
        disease_col = None
        for col in disease_columns:
            if col in adata.obs.columns:
                disease_col = col
                break
        
        if disease_col is None:
            print(f"  Warning: No disease column found in dataset")
            return None
        
        # Count normal cells
        # Normal is indicated by disease == "normal" or disease_ontology_term_id == "PATO:0000461"
        disease_values = adata.obs[disease_col].astype(str).str.lower()
        
        normal_mask = (
            disease_values.str.contains('normal', na=False) |
            disease_values.str.contains('pato:0000461', na=False)
        )
        
        normal_count = normal_mask.sum()
        
        return int(normal_count)
        
    except Exception as e:
        print(f"  Warning: Failed to count normal cells: {e}", file=sys.stderr)
        return None


def add_normal_counts():
    """Add normal_cell_count column to the CSV."""
    
    # Load input CSV
    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: Input file not found: {INPUT_CSV}", file=sys.stderr)
        print("Please run '3_append_dataset_details.py' first.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading datasets from: {INPUT_CSV}")
    with open(INPUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        original_fieldnames = reader.fieldnames or []
    
    print(f"Loaded {len(rows)} datasets")
    
    # Add new column
    fieldnames = original_fieldnames.copy()
    if "normal_cell_count" not in fieldnames:
        # Insert after cell_count
        cell_count_idx = fieldnames.index("cell_count")
        fieldnames.insert(cell_count_idx + 1, "normal_cell_count")
    
    # Process each dataset
    print(f"\nCounting normal cells in each dataset...")
    print(f"(This will take a while - downloading and processing H5AD files)")
    print(f"Caching enabled: {CACHE_ENABLED} (cache dir: {CACHE_DIR})")
    
    successful = 0
    failed = 0
    skipped = 0
    
    for i, row in enumerate(rows, 1):
        dataset_version_id = row.get("dataset_version_id", "")
        h5ad_url = row.get("h5ad_url", "")
        total_cells = row.get("cell_count", "0")
        
        # Progress indicator
        print(f"\n[{i}/{len(rows)}] Processing {dataset_version_id}")
        
        # Skip if missing URL
        if not h5ad_url:
            print(f"  Skipped: No H5AD URL")
            row["normal_cell_count"] = ""
            skipped += 1
            continue
        
        # Download H5AD file
        h5ad_path = download_h5ad(h5ad_url, dataset_version_id)
        if not h5ad_path:
            print(f"  Failed: Could not download")
            row["normal_cell_count"] = ""
            failed += 1
            continue
        
        # Count normal cells
        normal_count = count_normal_cells(h5ad_path)
        
        if normal_count is not None:
            row["normal_cell_count"] = str(normal_count)
            print(f"  Success: {normal_count:,} normal cells (out of {total_cells:,} total)")
            successful += 1
        else:
            row["normal_cell_count"] = ""
            print(f"  Failed: Could not count normal cells")
            failed += 1
    
    # Write output CSV
    print(f"\nWriting results to: {OUTPUT_CSV}")
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nResults:")
    print(f"  Total datasets: {len(rows)}")
    print(f"  Successfully processed: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Skipped (no URL): {skipped}")
    print(f"\nOutput saved to: {OUTPUT_CSV}")
    
    if CACHE_ENABLED:
        print(f"\nH5AD files cached in: {CACHE_DIR}")
        print(f"(Delete this directory to free up disk space)")


if __name__ == "__main__":
    print("=" * 70)
    print("CellxGene Data Harvester - Step 4: Count Normal Cells")
    print("=" * 70)
    
    # Check dependencies
    try:
        import scanpy
        import requests
    except ImportError as e:
        print(f"\nERROR: Missing required dependency: {e}", file=sys.stderr)
        print("Install with: pip install scanpy requests", file=sys.stderr)
        sys.exit(1)
    
    add_normal_counts()
    print("\nNext step: Run 'python bin/5_filter_datasets.py' to filter results")
