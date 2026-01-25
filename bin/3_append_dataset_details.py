#!/usr/bin/env python3
"""
Step 3: Append dataset details from collections
Uses pandas for efficient data operations
"""

import json
import os
import sys
import pandas as pd
from datetime import datetime

def load_collections(json_path="data/collections.json"):
    """Load collections JSON"""
    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found", file=sys.stderr)
        sys.exit(1)
    with open(json_path) as f:
        return json.load(f)

def extract_dataset_details(collections):
    """Extract detailed dataset information"""
    details = []
    
    for collection in collections:
        collection_id = collection.get("collection_id", "")
        collection_version_id = collection.get("collection_version_id", "")
        
        # Collection-level metadata
        first_author = ""
        if collection.get("contact_name"):
            first_author = collection["contact_name"].split()[0] if collection["contact_name"] else ""
        
        journal = collection.get("publisher", "")
        year = ""
        if collection.get("published_at"):
            try:
                year = str(datetime.fromisoformat(collection["published_at"].replace("Z", "+00:00")).year)
            except:
                pass
        
        is_preprint = collection.get("is_preprint", None)
        revised_at = collection.get("revised_at", "")
        visibility = collection.get("visibility", "")
        
        for dataset in collection.get("datasets", []):
            dataset_id = dataset.get("dataset_id", "")
            dataset_version_id = dataset.get("dataset_version_id", "")
            
            # Parse assets for H5AD URL
            h5ad_url = ""
            for asset in dataset.get("assets", []):
                if asset.get("filetype") == "H5AD":
                    h5ad_url = asset.get("url", "")
                    break
            
            # Explorer URL
            explorer_url = f"https://cellxgene.cziscience.com/e/{dataset_id}.cxg/"
            
            # Dataset metadata
            organism = dataset.get("organism", [{}])[0].get("label", "") if dataset.get("organism") else ""
            tissue = dataset.get("tissue", [{}])[0].get("label", "") if dataset.get("tissue") else ""
            disease = dataset.get("disease", [{}])[0].get("label", "") if dataset.get("disease") else ""
            
            details.append({
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "collection_id": collection_id,
                "collection_version_id": collection_version_id,
                "first_author": first_author,
                "journal": journal,
                "year": year,
                "is_preprint": is_preprint,
                "revised_at": revised_at,
                "visibility": visibility,
                "organism": organism,
                "tissue": tissue,
                "disease": disease,
                "h5ad_url": h5ad_url,
                "explorer_url": explorer_url,
            })
    
    return pd.DataFrame(details)

def append_details(input_csv, output_csv):
    """Append details to metadata CSV"""
    # Load base metadata
    df_base = pd.read_csv(input_csv)
    print(f"Loaded {len(df_base)} rows from {input_csv}")
    
    # Extract details
    collections = load_collections()
    df_details = extract_dataset_details(collections)
    print(f"Extracted details for {len(df_details)} datasets")
    
    # Merge on dataset_id
    df_merged = df_base.merge(df_details, on='dataset_id', how='left', suffixes=('', '_detail'))
    
    # Add static columns
    df_merged['author_cell_type'] = ""
    df_merged['embedding'] = ""
    df_merged['filter_normal'] = "TRUE"
    df_merged['metric'] = "euclidean"
    df_merged['save_scores'] = "FALSE"
    df_merged['save_cluster_summary'] = "FALSE"
    df_merged['save_annotation'] = "FALSE"
    
    # Reorder columns for readability
    column_order = [
        'collection_name', 'dataset_title', 'total_cell_count',
        'author_cell_type', 'embedding',
        'first_author', 'journal', 'year',
        'collection_url', 'explorer_url',
        'tissue', 'disease',
        'collection_id', 'collection_version_id',
        'dataset_id', 'dataset_version_id',
        'is_preprint', 'revised_at', 'visibility', 'organism',
        'filter_normal', 'metric', 'save_scores',
        'save_cluster_summary', 'save_annotation',
        'h5ad_url'
    ]
    
    # Keep columns in order, add any extras at end
    final_columns = [c for c in column_order if c in df_merged.columns]
    extra_columns = [c for c in df_merged.columns if c not in final_columns]
    final_columns.extend(extra_columns)
    
    df_merged = df_merged[final_columns]
    
    # Save
    df_merged.to_csv(output_csv, index=False)
    print(f"Saved {len(df_merged)} rows to {output_csv}")
    print(f"Columns: {len(df_merged.columns)}")

if __name__ == "__main__":
    print("="*70)
    print("CellxGene Data Harvester - Step 3: Append Dataset Details")
    print("="*70)
    
    append_details(
        input_csv="data/cellxgene_metadata.csv",
        output_csv="data/cellxgene_full_metadata.csv"
    )
    
    print(f"\nNext step:")
    print(f"  python bin/4_filter_datasets.py --organism 'Homo sapiens' --tissue lung --output filtered.csv")
