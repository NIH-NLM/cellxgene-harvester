import json
import sys
import requests
import os

# API Endpoints
SMALLEST_DATASET_ID = "0895c838-e550-48a3-a777-dbcd35d30272"
SMALLEST_DATASET_URL = f"https://api.cellxgene.cziscience.com/curation/v1/datasets/{SMALLEST_DATASET_ID}/versions"
COLLECTIONS_API = "https://api.cellxgene.cziscience.com/curation/v1/collections?visibility=PUBLIC"

def fetch_collections(test_mode):
    """
    Fetch collection metadata from CellxGene API.
    - Always retrieves all collections.
    - If test_mode is enabled, fetches only the smallest dataset.
    """
    print("🔹 Fetching all collections from CellxGene API...")
    response = requests.get(COLLECTIONS_API)

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch collections! Status: {response.status_code}", file=sys.stderr)
        sys.exit(1)

    collections_data = response.json()

    if not isinstance(collections_data, list):
        print(f"❌ ERROR: Expected a list but got {type(collections_data)}. Full response: {collections_data}", file=sys.stderr)
        sys.exit(1)

    if not collections_data:
        print("❌ ERROR: No collections found!", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Retrieved {len(collections_data)} collections.")

    # If test mode, fetch only the smallest dataset
    if test_mode.lower() == "true":
        print("🔹 Running in TEST MODE: Fetching only the smallest dataset.")

        # Fetch dataset metadata
        response = requests.get(SMALLEST_DATASET_URL)
        if response.status_code != 200:
            print(f"❌ ERROR: Failed to fetch test dataset! Status: {response.status_code}", file=sys.stderr)
            sys.exit(1)

        dataset_versions = response.json()
        if not isinstance(dataset_versions, list) or not dataset_versions:
            print(f"❌ ERROR: Unexpected dataset structure: {dataset_versions}", file=sys.stderr)
            sys.exit(1)

        # Select the latest version
        dataset_info = dataset_versions[0]

        # Extract dataset file URL
        dataset_assets = dataset_info.get("assets", [])
        h5ad_url = next((asset["url"] for asset in dataset_assets if asset["filetype"] == "H5AD"), None)

        if not h5ad_url:
            print(f"❌ ERROR: No H5AD file found in assets: {json.dumps(dataset_assets, indent=4)}", file=sys.stderr)
            sys.exit(1)

        # Extract the real collection ID from dataset metadata
        collection_id = dataset_info.get("collection_id", "UNKNOWN")
        collection_url = f"https://cellxgene.cziscience.com/collections/{collection_id}"

        # Replace collections with only this dataset
        collections_data = [{
            "collection_id": collection_id,
            "collection_url": collection_url,
            "datasets": [{
                "dataset_id": dataset_info["dataset_id"],
                "dataset_version_id": dataset_info["dataset_version_id"],
                "dataset_url": h5ad_url,
            }]
        }]

    return collections_data

def save_collections_metadata(test_mode):
    """
    Fetch and save collections metadata, limiting datasets if in test mode.
    """
    collections = fetch_collections(test_mode)

    # Ensure we have data before writing the file
    if not collections:
        print("❌ ERROR: No collections fetched. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Save to collections_info.json
    collections_file = "collections_info.json"
    with open(collections_file, "w", encoding="utf-8") as f:
        json.dump(collections, f, indent=4)

    print(f"✅ Collection metadata saved to {collections_file}. Total collections: {len(collections)}")

if __name__ == "__main__":
    test_mode_flag = sys.argv[1]
    save_collections_metadata(test_mode_flag)

