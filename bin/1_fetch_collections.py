#!/usr/bin/env python3
"""
Step 1: Fetch all collections from CellxGene API
Uses pandas for clean data handling
"""

import requests
import json
import os
import sys
import pandas as pd

def fetch_all_collections():
    """Fetch all collections from CellxGene API"""
    url = "https://api.cellxgene.cziscience.com/curation/v1/collections"
    
    print(f"Fetching collections from: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        collections = response.json()
        
        print(f"Successfully fetched {len(collections)} collections")
        return collections
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching collections: {e}", file=sys.stderr)
        sys.exit(1)

def save_collections(collections, data_dir="data"):
    """Save collections to JSON and create DataFrame"""
    os.makedirs(data_dir, exist_ok=True)
    
    # Save raw JSON
    json_path = os.path.join(data_dir, "collections.json")
    with open(json_path, "w") as f:
        json.dump(collections, f, indent=2)
    print(f"Saved raw JSON: {json_path}")
    
    # Convert to DataFrame for easy inspection
    df = pd.DataFrame(collections)
    csv_path = os.path.join(data_dir, "collections_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved summary CSV: {csv_path}")
    print(f"Columns: {list(df.columns)}")
    
    return json_path

if __name__ == "__main__":
    print("="*70)
    print("CellxGene Data Harvester - Step 1: Fetch Collections")
    print("="*70)
    
    collections = fetch_all_collections()
    json_path = save_collections(collections)
    
    print(f"\nNext step:")
    print(f"  python bin/2_generate_metadata_csv.py")
