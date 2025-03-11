import os
import requests
import json
import sys

# Define API endpoints
COLLECTIONS_API_URL = "https://api.cellxgene.cziscience.com/curation/v1/collections?visibility=PUBLIC"
DATASET_API_BASE_URL = "https://api.cellxgene.cziscience.com/curation/v1/datasets/"

def fetch_collections():
    """Fetch collections from CellxGene API and save to collections_info.json."""
    url = "https://api.cellxgene.cziscience.com/curation/v1/collections?visibility=PUBLIC"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"ERROR: Failed to fetch collections (HTTP {response.status_code})")
    
    collections = response.json()

    # Ensure the output directory exists
    os.makedirs("data", exist_ok=True)

    # Save collections to the correct path
    output_path = os.path.join("data", "collections_info.json")
    with open(output_path, "w") as f:
        json.dump(collections, f, indent=2)
    
    print(f"Saved collections info to {output_path}")


def fetch_dataset_info(dataset_id):
    """Fetch dataset details for a given dataset ID."""
    dataset_url = f"{DATASET_API_BASE_URL}{dataset_id}/versions"
    response = requests.get(dataset_url, headers={"accept": "application/json"})

    if response.status_code != 200:
        raise Exception(f" ERROR: Failed to fetch dataset {dataset_id} (HTTP {response.status_code})")

    dataset_info = response.json()
    dataset_version_id = dataset_info[0]["dataset_version_id"]
    dataset_assets = dataset_info[0].get("assets", [])
    h5ad_file = next((asset for asset in dataset_assets if asset["filetype"] == "H5AD"), None)

    if not h5ad_file:
        raise Exception(f"ERROR: No H5AD file found for dataset {dataset_id}!")

    return {
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "dataset_url": h5ad_file["url"]
    }

import requests


def save_datasets_metadata(dataset_id):
    """Fetch and save metadata for a single dataset (Nextflow will handle parallel execution)."""
    dataset_info = fetch_dataset_info(dataset_id)
    
    # Append or create datasets_info.json
    try:
        with open("datasets_info.json", "r") as f:
            datasets = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        datasets = []

    datasets.append(dataset_info)
    
    with open("datasets_info.json", "w") as f:
        json.dump(datasets, f, indent=4)
    
    print(f"Saved dataset {dataset_id} to datasets_info.json")


# Run script
if __name__ == "__main__":
    action = sys.argv[1].lower()

    if action == "fetch_collections":
        fetch_collections()
    elif action == "fetch_dataset":
        dataset_id = sys.argv[2]
        save_datasets_metadata(dataset_id)
    else:
        print("ERROR: Invalid action. Use 'fetch_collections' or 'fetch_dataset <dataset_id>'.")

