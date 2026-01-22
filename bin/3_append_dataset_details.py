#!/usr/bin/env python3
"""
Step 3: Append dataset details (H5AD URLs, cell counts, titles)

Fetches detailed information for each dataset using the CellxGene API:
- Dataset title
- Total cell count
- H5AD file download URL

NOTE: This step does NOT download H5AD files - it only gets the URLs.
H5AD files are downloaded in step 5, after filtering.

Usage:
    python bin/3_append_dataset_details.py
"""

import os
import sys
import csv
import time
import requests
from typing import Tuple

# Input/Output configuration
DATA_DIR = "data"
INPUT_CSV = os.path.join(DATA_DIR, "all_datasets.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "all_datasets_complete.csv")

# API configuration
API_TEMPLATE = (
    "https://api.cellxgene.cziscience.com/curation/v1/"
    "collections/{collection_id}/datasets/{dataset_id}"
)
REQUEST_DELAY = 0.2  # seconds between requests


def fetch_dataset_details(collection_id: str, dataset_id: str) -> Tuple[str, str, str]:
    """
    Fetch dataset details from CellxGene API.
    
    Args:
        collection_id: Collection UUID
        dataset_id: Dataset UUID
        
    Returns:
        Tuple of (dataset_title, total_cell_count, h5ad_url)
    """
    url = API_TEMPLATE.format(
        collection_id=collection_id,
        dataset_id=dataset_id
    )
    
    try:
        response = requests.get(url, headers={"accept": "application/json"}, timeout=30)
        
        if response.status_code != 200:
            print(f"  ⚠ Warning: HTTP {response.status_code} for {dataset_id}", file=sys.stderr)
            return "", "", ""
        
        data = response.json()
        
        # Extract dataset title
        dataset_title = data.get("title", "")
        
        # Extract cell count
        total_cell_count = str(data.get("cell_count", ""))
        
        # Extract H5AD URL
        h5ad_url = ""
        for asset in data.get("assets", []):
            if asset.get("filetype") == "H5AD":
                h5ad_url = asset.get("url", "")
                break
        
        return dataset_title, total_cell_count, h5ad_url
        
    except requests.exceptions.Timeout:
        print(f"  ⚠ Warning: Timeout for {dataset_id}", file=sys.stderr)
        return "", "", ""
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Warning: Request failed for {dataset_id}: {e}", file=sys.stderr)
        return "", "", ""
    except Exception as e:
        print(f"  ⚠ Warning: Unexpected error for {dataset_id}: {e}", file=sys.stderr)
        return "", "", ""


def append_details():
    """Append dataset details to the metadata CSV."""
    
    # Load input CSV
    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: Input file not found: {INPUT_CSV}", file=sys.stderr)
        print("Please run '2_generate_metadata_csv.py' first.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading datasets from: {INPUT_CSV}")
    with open(INPUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        original_fieldnames = reader.fieldnames or []
    
    print(f"Loaded {len(rows)} datasets")
    
    # Add new columns if they don't exist
    fieldnames = original_fieldnames.copy()
    new_fields = ["total_cell_count", "h5ad_url"]
    for field in new_fields:
        if field not in fieldnames:
            fieldnames.append(field)
    
    # Process each dataset
    print(f"\nFetching dataset details from CellxGene API...")
    print(f"(This will take ~{len(rows) * REQUEST_DELAY / 60:.1f} minutes)")
    
    successful = 0
    failed = 0
    
    for i, row in enumerate(rows, 1):
        collection_id = row.get("collection_id", "")
        dataset_id = row.get("dataset_id", "")
        
        # Progress indicator
        if i % 50 == 0:
            print(f"Progress: {i}/{len(rows)} ({i/len(rows)*100:.1f}%)")
        
        # Skip if missing IDs
        if not collection_id or not dataset_id:
            row["dataset_title"] = ""
            row["total_cell_count"] = ""
            row["h5ad_url"] = ""
            failed += 1
            continue
        
        # Fetch details
        dataset_title, total_cell_count, h5ad_url = fetch_dataset_details(collection_id, dataset_id)
        
        # Update row
        row["dataset_title"] = dataset_title
        row["total_cell_count"] = total_cell_count
        row["h5ad_url"] = h5ad_url
        
        if h5ad_url:
            successful += 1
        else:
            failed += 1
        
        # Rate limiting
        time.sleep(REQUEST_DELAY)
    
    # Write output CSV
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nResults:")
    print(f"  Total datasets: {len(rows)}")
    print(f"  Successfully fetched: {successful}")
    print(f"  Failed/skipped: {failed}")
    print(f"\nOutput saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    print("=" * 70)
    print("CellxGene Data Harvester - Step 3: Append Dataset Details")
    print("=" * 70)
    append_details()
    print("\nNext step: Run 'python bin/4_filter_datasets.py' to filter results")
