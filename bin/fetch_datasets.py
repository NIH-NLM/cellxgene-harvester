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
    response = requests.get(url, headers={"accept": "application/json"})
    
    if response.status_code != 200:
        print(f"ERROR: Failed to fetch dataset {dataset_id} (HTTP {response.status_code})", file=sys.stderr)
        return None

    return response.json()

def fetch_datasets(datasets_json, test_mode):
    """Fetch datasets from the API based on the dataset JSON file."""
    print(f"Fetching datasets from CellxGene API (Test Mode: {test_mode})")

    # Load dataset IDs from JSON file
    with open(datasets_json, "r") as f:
        datasets_info = json.load(f)

    results = []

    if test_mode:
        # Fetch only the smallest dataset for testing
        print(f"Fetching test dataset: {SMALLEST_DATASET_ID}")
        dataset_data = fetch_dataset(SMALLEST_DATASET_ID)
        if dataset_data:
            results.append(dataset_data)
    else:
        # Fetch all datasets
        for dataset in datasets_info:
            dataset_id = dataset.get("dataset_id")
            if dataset_id:
                print(f"Fetching dataset: {dataset_id}")
                dataset_data = fetch_dataset(dataset_id)
                if dataset_data:
                    results.append(dataset_data)

    # Output dataset JSON (printed, so Nextflow handles file output)
    print(json.dumps(results, indent=4))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("ERROR: Usage: python fetch_datasets.py <datasets_json> <test_mode>")
        sys.exit(1)

    datasets_json = sys.argv[1]
    test_mode = sys.argv[2].lower() == "true"

    fetch_datasets(datasets_json, test_mode)

