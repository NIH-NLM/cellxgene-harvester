#!/usr/bin/env python3
"""
Step 2: Generate metadata CSV from collections

Extracts collection and dataset IDs plus available metadata.
Dataset titles and cell counts require Step 3 API calls.

Usage:
    python bin/2_generate_metadata_csv.py
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime

DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "collections.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "cellxgene_metadata.csv")


def safe_label(entry, sep=" | "):
    """Extract labels from CellxGene metadata fields"""
    if isinstance(entry, list):
        labels = [
            item.get("label", "")
            for item in entry
            if isinstance(item, dict) and item.get("label")
        ]
        return sep.join(labels)
    return ""


def extract_publication_metadata(collection):
    """Extract publication metadata from collection"""
    publisher = collection.get("publisher_metadata") or {}
    
    metadata = {
        "first_author": "",
        "journal": "",
        "is_preprint": "",
        "year": ""
    }
    
    if isinstance(publisher, dict):
        # Extract first author
        authors = publisher.get("authors", [])
        if isinstance(authors, list) and authors and isinstance(authors[0], dict):
            metadata["first_author"] = authors[0].get("family", "")
        
        # Extract journal and preprint status
        metadata["journal"] = publisher.get("journal", "")
        is_preprint = publisher.get("is_preprint")
        metadata["is_preprint"] = "TRUE" if is_preprint else "FALSE" if is_preprint is False else ""
        
        # Extract year
        year_val = publisher.get("published_year")
        if year_val is not None:
            metadata["year"] = str(year_val)
    
    return metadata


def generate_metadata():
    """Generate metadata CSV from collections JSON"""
    
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found", file=sys.stderr)
        print("Run Step 1 first: python bin/1_fetch_collections.py", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading collections from: {INPUT_FILE}")
    with open(INPUT_FILE) as f:
        collections = json.load(f)
    
    print(f"Processing {len(collections)} collections...")
    
    rows = []
    
    for collection in collections:
        collection_id = collection.get("collection_id", "")
        collection_version_id = collection.get("collection_version_id", "")
        collection_name = collection.get("name", "")
        collection_url = collection.get("collection_url", "")
        visibility = collection.get("visibility", "")
        
        # Extract publication metadata
        pub_metadata = extract_publication_metadata(collection)
        
        # Process each dataset
        for dataset in collection.get("datasets", []):
            dataset_id = dataset.get("dataset_id", "")
            dataset_version_id = dataset.get("dataset_version_id", "")
            revised_at = dataset.get("revised_at", "")
            
            # Extract organism, tissue, disease from dataset
            organism = safe_label(dataset.get("organism"))
            tissue = safe_label(dataset.get("tissue"))
            disease = safe_label(dataset.get("disease"))
            
            row = {
                "collection_name": collection_name,
                "collection_id": collection_id,
                "collection_version_id": collection_version_id,
                "collection_url": collection_url,
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "organism": organism,
                "tissue": tissue,
                "disease": disease,
                "visibility": visibility,
                "revised_at": revised_at,
                "first_author": pub_metadata["first_author"],
                "journal": pub_metadata["journal"],
                "year": pub_metadata["year"],
                "is_preprint": pub_metadata["is_preprint"],
            }
            rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"\nGenerated {len(df)} dataset rows")
    print(f"Saved: {OUTPUT_CSV}")
    
    # Show sample
    print(f"\nSample of first row:")
    print(f"  Collection: {df.iloc[0]['collection_name']}")
    print(f"  Organism: {df.iloc[0]['organism']}")
    print(f"  Tissue: {df.iloc[0]['tissue']}")


if __name__ == "__main__":
    print("="*70)
    print("CellxGene Data Harvester - Step 2: Generate Metadata CSV")
    print("="*70)
    
    generate_metadata()
    
    print(f"\nNext step (fetches titles and cell counts):")
    print(f"  python bin/3_append_dataset_details.py")
