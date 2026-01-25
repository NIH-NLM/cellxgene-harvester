#!/usr/bin/env python3
"""
Step 2: Generate metadata CSV from collections
Fixed to properly extract dataset fields
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
    """Generate metadata DataFrame from collections"""
    rows = []
    
    for collection in collections:
        collection_id = collection.get("collection_id", "")
        collection_version_id = collection.get("collection_version_id", "")
        collection_name = collection.get("name", "")
        collection_url = collection.get("collection_url", "")
        
        # Collection-level info for datasets
        contact_name = collection.get("contact_name", "")
        first_author = contact_name.split()[0] if contact_name else ""
        
        publisher = collection.get("publisher", "")
        
        # Extract year from published_at
        year = ""
        if collection.get("published_at"):
            try:
                from datetime import datetime
                year = str(datetime.fromisoformat(collection["published_at"].replace("Z", "+00:00")).year)
            except:
                pass
        
        is_preprint = collection.get("is_preprint")
        revised_at = collection.get("revised_at", "")
        visibility = collection.get("visibility", "")
        
        for dataset in collection.get("datasets", []):
            dataset_id = dataset.get("dataset_id", "")
            dataset_version_id = dataset.get("dataset_version_id", "")
            
            # Dataset fields - these are the important ones!
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
            
            # Organism, tissue, disease from dataset
            organism = ""
            if dataset.get("organism"):
                organisms = dataset.get("organism", [])
                if organisms and len(organisms) > 0:
                    organism = organisms[0].get("label", "")
            
            tissue = ""
            if dataset.get("tissue"):
                tissues = dataset.get("tissue", [])
                if tissues and len(tissues) > 0:
                    tissue = tissues[0].get("label", "")
            
            disease = ""
            if dataset.get("disease"):
                diseases = dataset.get("disease", [])
                if diseases and len(diseases) > 0:
                    disease = diseases[0].get("label", "")
            
            row = {
                "collection_name": collection_name,
                "dataset_title": dataset_title,
                "total_cell_count": cell_count,
                "author_cell_type": "",
                "embedding": "",
                "first_author": first_author,
                "journal": publisher,
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
    print("CellxGene Data Harvester - Step 2: Generate Metadata CSV")
    print("="*70)
    
    collections = load_collections()
    print(f"Loaded {len(collections)} collections")
    
    df = generate_metadata_df(collections)
    print(f"Generated {len(df)} dataset rows")
    
    # Show sample
    print(f"\nSample of first row:")
    print(f"  Title: {df.iloc[0]['dataset_title']}")
    print(f"  Cell count: {df.iloc[0]['total_cell_count']}")
    print(f"  Tissue: {df.iloc[0]['tissue']}")
    print(f"  Organism: {df.iloc[0]['organism']}")
    
    output_path = "data/cellxgene_full_metadata.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved: {output_path}")
    print(f"Columns: {len(df.columns)}")
    
    print(f"\nNext step:")
    print(f"  python bin/3_filter_datasets.py --input data/cellxgene_full_metadata.csv --organism 'Homo sapiens' --tissue lung --output filtered.csv")
