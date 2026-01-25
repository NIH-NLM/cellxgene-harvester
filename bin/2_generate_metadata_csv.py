#!/usr/bin/env python3
"""
Step 2: Generate basic metadata CSV from collections

Note: Dataset titles and cell counts require individual API calls in Step 3.
The collections endpoint only provides collection-level info and basic dataset IDs.
"""

import json
import os
import sys
import pandas as pd

def load_collections(json_path="data/collections.json"):
    """Load collections from JSON"""
    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found", file=sys.stderr)
        print("Run step 1 first: python bin/1_fetch_collections.py", file=sys.stderr)
        sys.exit(1)
    
    with open(json_path) as f:
        return json.load(f)

def generate_metadata_df(collections):
    """Generate basic metadata DataFrame from collections"""
    rows = []
    
    for collection in collections:
        collection_id = collection.get("collection_id", "")
        collection_version_id = collection.get("collection_version_id", "")
        collection_name = collection.get("name", "")
        collection_url = collection.get("collection_url", "")
        
        for dataset in collection.get("datasets", []):
            dataset_id = dataset.get("dataset_id", "")
            dataset_version_id = dataset.get("dataset_version_id", "")
            
            # Note: title and cell_count are NOT in collections endpoint
            # They will be fetched in Step 3
            
            row = {
                "collection_name": collection_name,
                "collection_id": collection_id,
                "collection_version_id": collection_version_id,
                "collection_url": collection_url,
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

if __name__ == "__main__":
    print("="*70)
    print("CellxGene Data Harvester - Step 2: Generate Basic Metadata CSV")
    print("="*70)
    
    collections = load_collections()
    print(f"Loaded {len(collections)} collections")
    
    df = generate_metadata_df(collections)
    print(f"Generated {len(df)} dataset rows")
    
    output_path = "data/cellxgene_metadata.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved: {output_path}")
    print(f"Columns: {len(df.columns)}")
    
    print(f"\nNext step (fetches titles and cell counts via API):")
    print(f"  python bin/3_append_dataset_details.py")
