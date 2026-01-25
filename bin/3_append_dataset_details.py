#!/usr/bin/env python3
"""
Step 3: Append dataset details from API
Fetches title and cell_count for each dataset (requires individual API calls)
"""

import pandas as pd
import requests
import time
import sys

def fetch_dataset_details(dataset_id):
    """Fetch detailed info for a single dataset"""
    url = f"https://api.cellxgene.cziscience.com/curation/v1/datasets/{dataset_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  WARNING: Failed to fetch {dataset_id}: {e}")
        return None

def append_dataset_details(input_csv, output_csv):
    """Append dataset details to metadata CSV"""
    
    # Load base metadata
    df = pd.read_csv(input_csv)
    print(f"Loaded {len(df)} datasets from {input_csv}")
    
    # Fetch details for each dataset
    print(f"\nFetching dataset details (this takes ~10-20 minutes for {len(df)} datasets)...")
    
    titles = []
    cell_counts = []
    
    for idx, row in df.iterrows():
        dataset_id = row['dataset_id']
        
        if (idx + 1) % 50 == 0:
            print(f"  Progress: {idx + 1}/{len(df)} datasets...")
        
        details = fetch_dataset_details(dataset_id)
        
        if details:
            titles.append(details.get('title', ''))
            cell_counts.append(details.get('cell_count', 0))
        else:
            titles.append('')
            cell_counts.append(0)
        
        # Rate limiting
        time.sleep(0.1)
    
    # Update DataFrame
    df['dataset_title'] = titles
    df['total_cell_count'] = cell_counts
    
    # Save
    df.to_csv(output_csv, index=False)
    print(f"\nSaved {len(df)} datasets to {output_csv}")
    
    # Show sample
    print(f"\nSample of first row after update:")
    print(f"  Title: {df.iloc[0]['dataset_title']}")
    print(f"  Cell count: {df.iloc[0]['total_cell_count']}")

if __name__ == "__main__":
    print("="*70)
    print("CellxGene Data Harvester - Step 3: Append Dataset Details")
    print("="*70)
    
    append_dataset_details(
        input_csv="data/cellxgene_full_metadata.csv",
        output_csv="data/cellxgene_complete_metadata.csv"
    )
    
    print(f"\nNext step:")
    print(f"  python bin/4_filter_datasets.py --input data/cellxgene_complete_metadata.csv --organism 'Homo sapiens' --tissue lung --output filtered.csv")
