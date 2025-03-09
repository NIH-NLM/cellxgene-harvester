import requests
import json
import sys

# API endpoints
CELLXGENE_API = "https://api.cellxgene.cziscience.com/v2/collections"
SMALLEST_DATASET_ID = "0895c838-e550-48a3-a777-dbcd35d30272"
SMALLEST_DATASET_URL = f"https://api.cellxgene.cziscience.com/curation/v1/datasets/{SMALLEST_DATASET_ID}/versions"

def fetch_all_datasets():
    """
    Fetches all datasets available in CellxGene.
    Returns a list of dataset metadata.
    """
    response = requests.get(CELLXGENE_API)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch collections: {response.status_code}")

    collections = response.json()

    datasets = []
    for collection in collections.get("collections", []):
        collection_id = collection["id"]
        collection_version_id = collection["version_id"]
        collection_url = collection["url"]

        for dataset in collection["datasets"]:
            dataset_id = dataset["id"]
            dataset_version_id = dataset["version_id"]
            dataset_url = dataset["url"]

            datasets.append({
                "collection_id": collection_id,
                "collection_version_id": collection_version_id,
                "collection_url": collection_url,
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "dataset_url": dataset_url
            })
    
    return datasets

def fetch_smallest_dataset():
    """
    Fetches metadata for the smallest dataset (147 cells).
    Returns dataset metadata.
    """
    response = requests.get(SMALLEST_DATASET_URL)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch smallest dataset metadata: {response.status_code}")

    dataset_list = response.json()  # Expecting a list, not a dictionary

    if not isinstance(dataset_list, list) or len(dataset_list) == 0:
        raise Exception("Unexpected API response: dataset list is empty or not formatted correctly.")

    # Extract the first dataset from the list
    dataset_info = dataset_list[0]  # Fix: Select first dataset

    return [{
        "collection_id": dataset_info.get("collection_id", "N/A"),
        "collection_version_id": dataset_info.get("collection_version_id", "N/A"),
        "collection_url": f"https://cellxgene.cziscience.com/collections/{dataset_info.get('collection_id', '')}",
        "dataset_id": dataset_info.get("id", "N/A"),
        "dataset_version_id": dataset_info.get("version_id", "N/A"),
        "dataset_url": dataset_info.get("dataset_url", "N/A"),
        "total_cells": dataset_info.get("total_cell_count", "N/A"),
        "dataset_name": dataset_info.get("name", "N/A")
    }]

def save_dataset_metadata(test_mode=False):
    """
    Fetches dataset metadata based on the test_mode flag.
    Saves the dataset metadata to a JSON file.
    """
    if test_mode:
        print("Running in TEST MODE: Fetching only the smallest dataset.")
        datasets = fetch_smallest_dataset()
    else:
        print("Running in FULL MODE: Fetching all datasets.")
        datasets = fetch_all_datasets()
    
    with open("datasets_info.json", "w") as f:
        json.dump(datasets, f, indent=4)

    print(f"Dataset metadata saved. Total datasets: {len(datasets)}")

if __name__ == "__main__":
    # Read test mode flag from Nextflow args
    test_mode_flag = sys.argv[1] if len(sys.argv) > 1 else "false"
    test_mode = test_mode_flag.lower() == "true"

    save_dataset_metadata(test_mode)

