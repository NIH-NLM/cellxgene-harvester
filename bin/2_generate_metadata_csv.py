#!/usr/bin/env python3
"""
Step 2: Generate complete metadata CSV from collections

Extracts all available fields from collections.json including:
- Dataset titles and cell counts (already in the collections data)
- Collection metadata
- All IDs (the "quad": collection_id, collection_version_id, dataset_id, dataset_version_id)
"""

import json
import os
import sys
import pandas as pd
from datetime import datetime

def load_collections(json_path="data/collections.json"):
    """Load collections from JSON"""
    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found", file=sys.stderr)
        print("Run step 1 first: python bin/1_fetch_collections.py", file=sys.stderr)
        sys.exit(1)
    
    with open(json_path) as f:
        return json.load(f)

def generate_metadata_df(collections):
    """Generate complete metadata DataFrame from collections"""
    rows = []
    
    for collection in collections:
        # Collection-level fields
        collection_id = collection.get("collection_id", "")
        collection_version_id = collection.get("collection_version_id", "")
        collection_name = collection.get("name", "")
        collection_url = collection.get("collection_url", "")
        
        # Collection metadata
        contact_name = collection.get("contact_name", "")
        first_author = contact_name.split()[0] if contact_name else ""
        publisher = collection.get("publisher_metadata", {})
        journal = publisher.get("journal", "") if isinstance(publisher, dict) else ""
        
        # Extract year from published_at
        year = ""
        if collection.get("published_at"):
            try:
                year = str(datetime.fromisoformat(collection["published_at"].replace("Z", "+00:00")).year)
            except:
                pass
        
        is_preprint = collection.get("is_preprint")
        revised_at = collection.get("revised_at", "")
        visibility = collection.get("visibility", "")
        
        # Process each dataset in the collection
        for dataset in collection.get("datasets", []):
            dataset_id = dataset.get("dataset_id", "")
            dataset_version_id = dataset.get("dataset_version_id", "")
            
            # These ARE available in the collections endpoint!
            dataset_title = dataset.get("title", "")
            cell_count = dataset.get("cell_count", 0)
            
            # Parse assets for H5AD URL
            h5ad_url = ""
            for asset in dataset.get("assets", []):
                if asset.get("filetype") == "H5AD":
                    h5ad_url = asset.get("url", "")
                    break
            
            # Explorer URL
            explorer_url = f"https://cellxgene.cziscience.com/e/{dataset_id}.cxg/"
            
            # Extract organism, tissue, disease (first entry)
            organism = ""
            if dataset.get("organism") and len(dataset["organism"]) > 0:
                organism = dataset["organism"][0].get("label", "")
            
            tissue = ""
            if dataset.get("tissue") and len(dataset["tissue"]) > 0:
                tissue = dataset["tissue"][0].get("label", "")
            
            disease = ""
            if dataset.get("disease") and len(dataset["disease"]) > 0:
                disease = dataset["disease"][0].get("label", "")
            
            row = {
                "collection_name": collection_name,
                "dataset_title": dataset_title,
                "total_cell_count": cell_count,
                "author_cell_type": "",
                "embedding": "",
                "first_author": first_author,
                "journal": journal,
                "year": year,
                "collection_url": collection_url,
                "explorer_url": explorer_url,
                "tissue": tissue,
                "disease": disease,
                "collection_id": collection_id,
                "collection_version_id": collection_version_id,
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "is_preprint": is_preprint,
                "revised_at": revised_at,
                "visibility": visibility,
                "organism": organism,
                "filter_normal": "TRUE",
                "metric": "euclidean",
                "save_scores": "FALSE",
                "save_cluster_summary": "FALSE",
                "save_annotation": "FALSE",
                "h5ad_url": h5ad_url,
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

if __name__ == "__main__":
    print("="*70)
    print("CellxGene Data Harvester - Step 2: Generate Complete Metadata CSV")
    print("="*70)
    
    collections = load_collections()
    print(f"Loaded {len(collections)} collections")
    
    df = generate_metadata_df(collections)
    print(f"Generated {len(df)} dataset rows")
    
    # Show sample to verify
    print(f"\nSample of first row:")
    print(f"  Title: {df.iloc[0]['dataset_title']}")
    print(f"  Cell count: {df.iloc[0]['total_cell_count']}")
    print(f"  Tissue: {df.iloc[0]['tissue']}")
    print(f"  Organism: {df.iloc[0]['organism']}")
    
    output_path = "data/cellxgene_complete_metadata.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved: {output_path}")
    print(f"Columns: {len(df.columns)}")
    
    print(f"\nNext step:")
    print(f"  python bin/4_filter_datasets.py --input data/cellxgene_complete_metadata.csv --organism 'Homo sapiens' --tissue lung --output filtered.csv")
