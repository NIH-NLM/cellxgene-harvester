import requests
import json
import pandas as pd
import sys
from jsonpath_ng import parse
import pooch

# API Endpoints
COLLECTIONS_API = "https://api.cellxgene.cziscience.com/curation/v1/collections?visibility=PUBLIC"
COLLECTION_DETAILS_API = "https://api.cellxgene.cziscience.com/curation/v1/collections/"

# Cache directory for datasets
CACHE_DIR = pooch.os_cache("cellxgene")

def fetch_collections():
    """
    Fetch all publicly available dataset collections from CellxGene.
    """
    response = requests.get(COLLECTIONS_API)

    if response.status_code != 200:
        print(f"❌ Error fetching collections: {response.status_code}")
        print(f"Response body: {response.text}")
        raise Exception(f"Failed to fetch collections: {response.status_code}")

    collections_json = response.json()  # Expecting a list, not a dictionary

    # 🔹 DEBUG: Print first 3 entries to verify structure
    print(f"DEBUG: First 3 collections:\n{json.dumps(collections_json[:3], indent=2)}", file=sys.stderr)

    if not isinstance(collections_json, list):
        raise Exception(f"Unexpected API response format: {type(collections_json)}")

    # Convert to Pandas DataFrame
    collections_df = pd.DataFrame.from_records(collections_json)

    return collections_df

def fetch_datasets_for_collection(collection_id):
    """
    Fetch dataset assets for a given collection.
    """
    response = requests.get(f"{COLLECTION_DETAILS_API}{collection_id}")

    if response.status_code != 200:
        print(f"❌ Error fetching datasets for collection {collection_id}: {response.status_code}")
        print(f"Response body: {response.text}")
        return []

    rec = response.json()

    # Use JSONPath to extract datasets
    collection_assets = [
        x.value for x in parse("datasets[*].dataset_assets[*]").find(rec)
        if x.value["filetype"] == "H5AD"
    ]

    return collection_assets

def save_collections_metadata(test_mode=False):
    """
    Fetches collections and saves metadata including datasets.
    """
    collections_df = fetch_collections()

    # ✅ Print DataFrame column names to confirm `collection_id` exists
    print(f"\n🔹 DEBUG: DataFrame Columns -> {collections_df.columns.tolist()}")

    collections_metadata = []
    for _, collection in collections_df.iterrows():
        # ✅ Print available row keys
        print(f"\n🔹 DEBUG: Row Keys -> {collection.keys()}")

        # ✅ Try using `.id` if `collection_id` is missing
        collection_id = collection.get("id", collection.get("collection_id", "UNKNOWN"))
        collection_version_id = collection.get("collection_version_id", "N/A")
        collection_url = collection.get("collection_url", "N/A")
        
        print(f"🔹 Processing Collection: {collection_id}")  # Debug output

        # Fetch datasets for this collection
        datasets = collection.get("datasets", [])

        collections_metadata.append({
            "collection_id": collection_id,
            "collection_version_id": collection_version_id,
            "collection_url": collection_url,
            "datasets": datasets
        })

    # ✅ Debug print before saving
    print("\n🔹 DEBUG: JSON Data Before Saving")
    print(json.dumps(collections_metadata[:3], indent=2))  # Print first 3 entries

    # Save collections metadata
    with open("collections_info.json", "w") as f:
        json.dump(collections_metadata, f, indent=4)

    print(f"✅ Collection metadata saved. Total collections: {len(collections_metadata)}")

if __name__ == "__main__":
    try:
        save_collections_metadata()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

