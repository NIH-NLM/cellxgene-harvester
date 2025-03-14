import os
import sys
import json
import requests

# Constants
DATASETS_API_URL = "https://api.cellxgene.cziscience.com/curation/v1/datasets"
SMALLEST_DATASET_ID = "0895c838-e550-48a3-a777-dbcd35d30272"
SMALLEST_DATASET_URL = f"{DATASETS_API_URL}/{SMALLEST_DATASET_ID}/versions"

def fetch_dataset(dataset_id):
    """Fetch dataset metadata from CellxGene API."""
    url = f"{DATASETS_API_URL}/{dataset_id}/versions"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"ERROR: Failed to fetch dataset {dataset_id} (HTTP {response.status_code})")
    
    datasets = response.json ()

    output_filename = f"data_{data_version_id}.json"

    with open(output_filename, "w") as f:
        json.dump(datasets, f, indent=2)

def fetch_datasets(collection_json, test_mode):
    """Fetch datasets from the API based on the collection JSON file."""
    print(f"Fetching datasets for a collection from CellxGene API (Test Mode will retrieve only the smallest dataset: {test_mode})")

    # Load dataset IDs from JSON file
    with open(collection_json, "r") as f:
        collection_info = json.load(f)

    results = []

    if test_mode:
        # Fetch only the smallest dataset for testing
        print(f"Fetching test dataset: {SMALLEST_DATASET_ID}")
        dataset_data = fetch_dataset(SMALLEST_DATASET_ID)
        if dataset_data:
            results.append(dataset_data)
    else:
        # Fetch all datasets
        print(f"Fetching all datasets: {dataset_id}")
        dataset_data = fetch_dataset(dataset_id)
        if dataset_data:
            results.append(dataset_data)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("ERROR: Usage: python fetch_datasets.py <datasets_json> <test_mode>")
        sys.exit(1)

    datasets_json = sys.argv[1]
    test_mode = sys.argv[2].lower() == "true"

    fetch_datasets(datasets_json, test_mode)

