#!/usr/bin/env python3
"""
Step 2: Generate metadata CSV from collections

Extracts collection and dataset information into a CSV file.
Includes collection names and basic metadata for each dataset.

Usage:
    python bin/generate_metadata_csv.py
"""

import os
import sys
import json
import csv
from datetime import datetime

# Input/Output configuration
DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "collections_metadata.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "all_datasets.csv")

STATIC_FIELDS = {
    "filter_normal": "TRUE",
    "metric": "euclidean",
    "save_scores": "TRUE",
    "save_cluster_summary": "TRUE",
    "save_annotation": "TRUE",
}

# CSV header with collection_name and dataset_title placeholders
# CSV header with user-friendly ordering
CSV_HEADER = [
    # Human-readable fields first (for easy editing)
    "reference",
    "collection_name",
    "dataset_title",
    "normal_cell_count",
    "total_cell_count",
    "author_cell_type",
    "embedding",
    "first_author",
    "journal",
    "year",
    "doi",
    "collection_url",
    "explorer_url",
    "tissue",
    "disease",
    # Technical IDs and metadata
    "collection_id",
    "collection_version_id",
    "dataset_id",
    "dataset_version_id",
    "is_preprint",
    "revised_at",
    "visibility",
    "organism",
    # Static processing fields
    "filter_normal",
    "metric",
    "save_scores",
    "save_cluster_summary",
    "save_annotation",
    "h5ad_url",
    'tissue_ontology_term_id',
    'assay_ontology_term_id', 
    'cell_type_ontology_term_id',
    'disease_ontology_term_id',
    'development_stage_ontology_term_id',
    'sex_ontology_term_id',
    'is_primary_data',
    'donor_id_count',
    'tissue_ontology_summary',
    'assay_ontology_summary',
    'cell_type_ontology_summary',
    'disease_ontology_summary',
    'sex_ontology_summary',
    'development_stage_summary',

]


def safe_label(entry, sep=" | "):
    """
    Extract labels from CellxGene metadata fields.
    
    Args:
        entry: List of dicts with 'label' keys, or other type
        sep: Separator for multiple labels
        
    Returns:
        String of joined labels or empty string
    """
    if isinstance(entry, list):
        labels = [
            item.get("label", "")
            for item in entry
            if isinstance(item, dict) and item.get("label")
        ]
        return sep.join(labels)
    return ""


def extract_publication_metadata(collection_data):
    """
    Extract publication metadata from collection.
    
    Returns:
        dict with first_author, journal, is_preprint, year
    """
    publisher = collection_data.get("publisher_metadata") or {}
    
    metadata = {
        "first_author": "",
        "journal": "",
        "is_preprint": "",
        "year": "",
        "doi": ""
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
        metadata["doi"] = publisher.get("doi", "") 

    return metadata


def get_latest_dataset_versions(datasets):
    """
    Get the latest version of each dataset.
    
    Args:
        datasets: List of dataset dicts from collection
        
    Returns:
        Dict mapping dataset_id to latest version metadata
    """
    latest_versions = {}
    version_counts = {}  # Track how many versions per dataset
    
    for ds in datasets:
        if not isinstance(ds, dict):
            continue
            
        ds_id = ds.get("dataset_id", "")
        if not ds_id:
            continue
        
        # Count versions
        version_counts[ds_id] = version_counts.get(ds_id, 0) + 1
        
        ds_version_id = ds.get("dataset_version_id", "")
        revised_at = ds.get("revised_at", "")
        
        # Keep the latest version based on revised_at timestamp
        current = latest_versions.get(ds_id)
        if not current or revised_at > current.get("revised_at", ""):
            latest_versions[ds_id] = {
                "dataset_id": ds_id,
                "dataset_version_id": ds_version_id,
                "organism": safe_label(ds.get("organism")),
                "tissue": safe_label(ds.get("tissue")),
                "disease": safe_label(ds.get("disease")),
                "revised_at": revised_at,
            }
    
    # Report datasets with multiple versions
    multiple_versions = {k: v for k, v in version_counts.items() if v > 1}
    if multiple_versions:
        print(f"  Note: Found {len(multiple_versions)} datasets with multiple versions")
        for ds_id, count in multiple_versions.items():
            print(f"    {ds_id}: {count} versions")
    
    return latest_versions


def generate_csv():
    """Generate metadata CSV from collections JSON."""
    
    # Load collections
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}", file=sys.stderr)
        print("Please run '1_fetch_collections.py' first.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading collections from: {INPUT_FILE}")
    with open(INPUT_FILE) as f:
        collections = json.load(f)
    
    if not isinstance(collections, list):
        print("ERROR: Invalid collections format", file=sys.stderr)
        sys.exit(1)
    
    print(f"Processing {len(collections)} collections...")
    
    rows = []
    skipped_collections = 0
    
    for collection in collections:
        collection_id = collection.get("collection_id", "")
        collection_version_id = collection.get("collection_version_id", "")
        collection_name = collection.get("name", "")
        collection_url = collection.get("collection_url", "")
        doi = collection.get("doi","")
        visibility = collection.get("visibility", "")
        
        if not collection_id:
            skipped_collections += 1
            continue
        
        # Extract publication metadata
        pub_metadata = extract_publication_metadata(collection)
        
        # Get latest version of each dataset
        datasets = collection.get("datasets", [])
        if not datasets:
            skipped_collections += 1
            continue
        
        latest_datasets = get_latest_dataset_versions(datasets)
        
        # Create a row for each dataset
        for ds in latest_datasets.values():
            row = {
                # Human-readable fields (will be filled in subsequent steps)
                "reference": "unk",
                "collection_name": collection_name,
                "dataset_title": "",  # Will be filled in step 3
                "total_cell_count": "",  # Will be filled in step 3
                "author_cell_type": "",  # Empty for user to fill in
                "embedding": "",  # Empty for user to fill in
                "first_author": pub_metadata["first_author"],
                "journal": pub_metadata["journal"],
                "year": pub_metadata["year"],
                "doi": doi,
                "collection_url": collection_url,
                "explorer_url": "",  # Will be filled in step 3
                "tissue": ds["tissue"],
                "disease": ds["disease"],
                # Technical IDs and metadata
                "collection_id": collection_id,
                "collection_version_id": collection_version_id,
                "dataset_id": ds["dataset_id"],
                "dataset_version_id": ds["dataset_version_id"],
                "is_preprint": pub_metadata["is_preprint"],
                "revised_at": ds["revised_at"],
                "visibility": visibility,
                "organism": ds["organism"],
                # Static processing fields
                **STATIC_FIELDS,
                "h5ad_url": "",  # Will be filled in step 3
            }
            rows.append(row)
    
    # Write CSV
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nResults:")
    print(f"  Total collections processed: {len(collections)}")
    print(f"  Collections skipped (no datasets): {skipped_collections}")
    print(f"  Datasets written: {len(rows)}")
    print(f"\nOutput saved to: {OUTPUT_CSV}")
    print(f"\nNote: If any datasets had multiple versions, only the latest was included.")

def run_generate_metadata():
    """Main entry point called by CLI"""
    print("=" * 70)
    print("CellxGene Data Harvester - Step 2: Generate Metadata CSV")
    print("=" * 70)
    generate_csv()
    print("\nNext step: cellxgene-harvester append-details")
