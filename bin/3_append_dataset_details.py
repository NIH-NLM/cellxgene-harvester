#!/usr/bin/env python3
"""
Step 3: Append dataset details via API

Fetches detailed information for each dataset using the correct API endpoint:
- Dataset title
- Total cell count  
- H5AD file download URL
- Explorer URL

API endpoint: /curation/v1/collections/{collection_id}/datasets/{dataset_id}

Usage:
    python bin/3_append_dataset_details.py
"""

import os
import sys
import pandas as pd
import requests
import time

# Configuration
DATA_DIR = "data"
INPUT_CSV = os.path.join(DATA_DIR, "cellxgene_metadata.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "cellxgene_complete_metadata.csv")

API_TEMPLATE = (
    "https://api.cellxgene.cziscience.com/curation/v1/"
    "collections/{collection_id}/datasets/{dataset_id}"
)
REQUEST_DELAY = 0.2  # seconds between requests


def fetch_dataset_details(collection_id: str, dataset_id: str):
    """
    Fetch dataset details from CellxGene API.
    
    Returns:
        dict with dataset_title, total_cell_count, h5ad_url, explorer_url
    """
    url = API_TEMPLATE.format(
        collection_id=collection_id,
        dataset_id=dataset_id
    )
    
    try:
        response = requests.get(url, headers={"accept": "application/json"}, timeout=30)
        
        if response.status_code != 200:
            print(f"  Warning: HTTP {response.status_code} for {dataset_id}")
            return None
        
        data = response.json()
        
        # Extract fields
        dataset_title = data.get("title", "")
        total_cell_count = data.get("cell_count", 0)
        
        # Extract H5AD URL
        h5ad_url = ""
        for asset in data.get("assets", []):
            if asset.get("filetype") == "H5AD":
                h5ad_url = asset.get("url", "")
                break
        
        explorer_url = data.get("explorer_url", "")
        
        return {
            "dataset_title": dataset_title,
            "total_cell_count": total_cell_count,
            "h5ad_url": h5ad_url,
            "explorer_url": explorer_url
        }
        
    except Exception as e:
        print(f"  Warning: Failed to fetch {dataset_id}: {e}")
        return None


def append_dataset_details():
    """Append dataset details to metadata CSV"""
    
    # Load input
    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: Input file not found: {INPUT_CSV}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading datasets from: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} datasets")
    
    # Add columns for details
    df['dataset_title'] = ''
    df['total_cell_count'] = 0
    df['h5ad_url'] = ''
    df['explorer_url'] = ''
    
    # Also add fields that will be populated later
    df['author_cell_type'] = ''
    df['embedding'] = ''
    df['first_author'] = ''
    df['journal'] = ''
    df['year'] = ''
    df['tissue'] = ''
    df['disease'] = ''
    df['is_preprint'] = ''
    df['revised_at'] = ''
    df['visibility'] = ''
    df['organism'] = ''
    df['filter_normal'] = 'TRUE'
    df['metric'] = 'euclidean'
    df['save_scores'] = 'FALSE'
    df['save_cluster_summary'] = 'FALSE'
    df['save_annotation'] = 'FALSE'
    
    print(f"\nFetching dataset details from API...")
    print(f"(This takes ~{len(df) * REQUEST_DELAY / 60:.1f} minutes)")
    
    successful = 0
    failed = 0
    
    for idx, row in df.iterrows():
        collection_id = row['collection_id']
        dataset_id = row['dataset_id']
        
        if (idx + 1) % 50 == 0:
            print(f"Progress: {idx + 1}/{len(df)} ({(idx + 1)/len(df)*100:.1f}%)")
        
        if not collection_id or not dataset_id:
            failed += 1
            continue
        
        # Fetch details using BOTH collection_id and dataset_id
        details = fetch_dataset_details(collection_id, dataset_id)
        
        if details:
            df.at[idx, 'dataset_title'] = details['dataset_title']
            df.at[idx, 'total_cell_count'] = details['total_cell_count']
            df.at[idx, 'h5ad_url'] = details['h5ad_url']
            df.at[idx, 'explorer_url'] = details['explorer_url']
            successful += 1
        else:
            failed += 1
        
        # Rate limiting
        time.sleep(REQUEST_DELAY)
    
    # Save
    df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"\nResults:")
    print(f"  Total datasets: {len(df)}")
    print(f"  Successfully fetched: {successful}")
    print(f"  Failed: {failed}")
    print(f"\nSaved: {OUTPUT_CSV}")
    
    # Show sample
    print(f"\nSample of first row:")
    print(f"  Title: {df.iloc[0]['dataset_title']}")
    print(f"  Cell count: {df.iloc[0]['total_cell_count']}")


if __name__ == "__main__":
    print("="*70)
    print("CellxGene Data Harvester - Step 3: Append Dataset Details")
    print("="*70)
    
    append_dataset_details()
    
    print(f"\nNext step:")
    print(f"  python bin/4_filter_datasets.py --input data/cellxgene_complete_metadata.csv --organism 'Homo sapiens' --tissue lung --output filtered.csv")
