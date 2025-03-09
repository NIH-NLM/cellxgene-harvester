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
    Ensures dataset URLs are valid.
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
            dataset_url = dataset.get("url", "").strip()

            if not dataset_url:
                print(f"Warning: Dataset {dataset['id']} has no valid dataset URL", file=sys.stderr)
                continue  # Skip datasets without a URL

            datasets.append({
                "collection_id": collection_id,
                "collection_version_id": collection_version_id,
                "collection_url": collection_url,
                "dataset_id": dataset["id"],
                "dataset_version_id": dataset["version_id"],
                "dataset_url": dataset_url,  # Ensure this is not empty!
                "dataset_title": dataset["title"],
                "organism": dataset.get("organism", "N/A"),
                "tissue": dataset.get("tissue", "N/A"),
                "disease": dataset.get("disease", "N/A"),
                "assay": dataset.get("assay", "N/A"),
                "cell_count": dataset.get("cell_count", "N/A")
            })
    
    return datasets

def fetch_smallest_dataset():
    """
    Fetches metadata for the smallest dataset (147 cells) and ensures dataset URL exists.
    """
    response = requests.get(SMALLEST_DATASET_URL)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch smallest dataset metadata: {response.status_code}")

    dataset_list = response.json()

    if not isinstance(dataset_list, list) or len(dataset_list) == 0:
        raise Exception("Unexpected API response: dataset list is empty or not formatted correctly.")

    dataset_info = dataset_list[0]
    dataset_url = dataset_info.get("dataset_url", "").strip()

    if not dataset_url:
        raise Exception(f"Dataset {dataset_info['id']} is missing a valid dataset URL!")

    return [{
        "collection_id": dataset_info.get("collection_id", "N/A"),
        "collection_version_id": dataset_info.get("collection_version_id", "N/A"),
        "collection_url": f"https://cellxgene.cziscience.com/collections/{dataset_info.get('collection_id', '')}",
        "dataset_id": dataset_info.get("id", "N/A"),
        "dataset_version_id": dataset_info.get("version_id", "N/A"),
        "dataset_url": dataset_url,  # Ensure dataset URL is valid!
        "dataset_title": dataset_info.get("name", "N/A"),
        "organism": dataset_info.get("organism", "N/A"),
        "tissue": dataset_info.get("tissue", "N/A"),
        "disease": dataset_info.get("disease", "N/A"),
        "assay": dataset_info.get("assay", "N/A"),
        "cell_count": dataset_info.get("total_cell_count", "N/A")
    }]

def save_dataset_metadata(test_mode=False):
    """
    Fetches dataset metadata and ensures dataset URLs exist.
    Saves the dataset metadata to a JSON file.
    """
    datasets = fetch_smallest_dataset() if test_mode else fetch_all_datasets()

    with open("datasets_info.json", "w") as f:
        json.dump(datasets, f, indent=4)

    print(f"Dataset metadata saved. Total datasets: {len(datasets)}")

if __name__ == "__main__":
    test_mode = sys.argv[1].lower() == "true" if len(sys.argv) > 1 else False
    save_dataset_metadata(test_mode)

