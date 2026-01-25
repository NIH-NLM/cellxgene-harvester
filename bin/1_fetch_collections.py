#!/usr/bin/env python3
"""
Step 1: Fetch all collections from CellxGene API

Downloads collection metadata including:
- Collection IDs and names
- Publication metadata (authors, journal, year)
- Associated datasets

Usage:
    python bin/1_fetch_collections.py
"""

import os
import requests
import json
import sys

# API endpoint (no visibility filter - retrieves all public collections)
COLLECTIONS_API_URL = "https://api.cellxgene.cziscience.com/curation/v1/collections"

# Output configuration
DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "collections_metadata.json")


def fetch_collections():
    """Fetch all collections from CellxGene API."""
    print("Fetching collections from CellxGene API...")
    print(f"API URL: {COLLECTIONS_API_URL}")
    
    response = requests.get(COLLECTIONS_API_URL)
    
    if response.status_code != 200:
        raise Exception(f"ERROR: Failed to fetch collections (HTTP {response.status_code})")
    
    collections = response.json()
    
    # Validate response
    if not isinstance(collections, list):
        print("ERROR: Unexpected API response format", file=sys.stderr)
        sys.exit(1)
    
    print(f"Successfully fetched {len(collections)} collections")
    
    # Save to file
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(collections, f, indent=2)
    
    print(f"Saved collections metadata to: {OUTPUT_FILE}")
    
    # Print summary statistics
    public_count = sum(1 for c in collections if c.get("visibility") == "PUBLIC")
    print(f"\nSummary:")
    print(f"  Total collections: {len(collections)}")
    print(f"  Public collections: {public_count}")
    print(f"  Private collections: {len(collections) - public_count}")
    
    # Sample collection info
    if collections:
        sample = collections[0]
        print(f"\nSample collection fields:")
        print(f"  - collection_id: {sample.get('collection_id', 'N/A')}")
        print(f"  - name: {sample.get('name', 'N/A')}")
        print(f"  - datasets: {len(sample.get('datasets', []))} datasets")


if __name__ == "__main__":
    print("=" * 70)
    print("CellxGene Data Harvester - Step 1: Fetch Collections")
    print("=" * 70)
    fetch_collections()
    print("\nNext step: Run 'python bin/2_generate_metadata_csv.py'")
