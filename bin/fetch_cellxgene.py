import requests
import json
import sys

CELLXGENE_API = "https://api.cellxgene.cziscience.com/v2/collections"

def fetch_collections():
    """
    Fetch all dataset collections from CellxGene.
    """
    response = requests.get(CELLXGENE_API)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch collections: {response.status_code}")

    return response.json().get("collections", [])

def save_collections_metadata(test_mode=False):
    """
    Saves collections so that Nextflow can distribute datasets.
    """
    collections = fetch_collections()
    collections_metadata = [{"collection_id": col["id"], "datasets": col["datasets"]} for col in collections]

    with open("collections_info.json", "w") as f:
        json.dump(collections_metadata, f, indent=4)

if __name__ == "__main__":
    test_mode = sys.argv[1].lower() == "true" if len(sys.argv) > 1 else False
    save_collections_metadata(test_mode)

