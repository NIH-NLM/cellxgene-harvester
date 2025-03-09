import requests
import json
import sys

CELLXGENE_API = "https://api.cellxgene.cziscience.com/curation/v1/collections?visibility=PUBLIC"

def fetch_collections():
    """
    Fetch all publicly available dataset collections from CellxGene.
    """
    response = requests.get(CELLXGENE_API)

    if response.status_code != 200:
        print(f"Error fetching collections: {response.status_code}")
        print(f"Response body: {response.text}")
        raise Exception(f"Failed to fetch collections: {response.status_code}")

    collections = response.json()  # Expecting a list

    if not isinstance(collections, list):
        raise Exception(f"Unexpected API response format: {type(collections)}")

    return collections

def save_collections_metadata(test_mode=False):
    """
    Fetches collections and saves metadata as JSON.
    """
    collections = fetch_collections()

    collections_metadata = []
    for collection in collections:
        collection_id = collection.get("id", "N/A")
        collection_version_id = collection.get("version_id", "N/A")
        collection_url = collection.get("url", "N/A")
        datasets = collection.get("datasets", [])

        if not isinstance(datasets, list):
            print(f"Warning: Collection {collection_id} has an unexpected datasets format", file=sys.stderr)
            datasets = []

        # Append collection metadata
        collections_metadata.append({
            "collection_id": collection_id,
            "collection_version_id": collection_version_id,
            "collection_url": collection_url,
            "datasets": datasets
        })

    # Save collections metadata
    with open("collections_info.json", "w") as f:
        json.dump(collections_metadata, f, indent=4)

    print(f"Collection metadata saved. Total collections: {len(collections_metadata)}")

if __name__ == "__main__":
    try:
        save_collections_metadata()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

