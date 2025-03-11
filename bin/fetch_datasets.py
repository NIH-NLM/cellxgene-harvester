import os
import requests
import json
import sys

# Define API endpoint
DATASET_API_BASE_URL = "https://api.cellxgene.cziscience.com/curation/v1/datasets/"

def fetch_dataset_info(dataset_id):
    """Fetch dataset details for a given dataset ID."""
    dataset_url = f"{DATASET_API_BASE_URL}{dataset_id}/versions"
    response = requests.get(dataset_url, headers={"accept": "application/json"})

    if response.status_code != 200:
        raise Exception(f"ERROR: Failed to fetch dataset {dataset_id} (HTTP {response.status_code})")

    dataset_info_list = response.json()
    
    if not dataset_info_list:
        raise Exception(f"ERROR: No dataset versions found for dataset {dataset_id}!")
    
    return dataset_info_list

def save_datasets_metadata(dataset_ids, output_filename):
    """Fetch and save dataset metadata for multiple datasets."""
    datasets_metadata = {}
    
    for dataset_id in dataset_ids:
        datasets_metadata[dataset_id] = fetch_dataset_info(dataset_id)
    
    os.makedirs("data/datasets", exist_ok=True)
    output_path = os.path.join("data/datasets", output_filename)
    
    with open(output_path, "w") as f:
        json.dump(datasets_metadata, f, indent=2)
    
    print(f"Saved dataset metadata to {output_path}")

# Run script
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fetch_datasets.py <datasets_info.json> <output_filename>")
        sys.exit(1)
    
    datasets_info_file = sys.argv[1]
    output_filename = sys.argv[2]
    
    # Load dataset IDs from input JSON
    with open(datasets_info_file, "r") as f:
        datasets_info = json.load(f)
        dataset_ids = datasets_info.get("dataset_ids", [])
    
    save_datasets_metadata(dataset_ids, output_filename)

