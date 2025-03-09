import json
import sys
import requests

# Define smallest test dataset
SMALLEST_DATASET_ID = "0895c838-e550-48a3-a777-dbcd35d30272"
SMALLEST_DATASET_URL = f"https://api.cellxgene.cziscience.com/curation/v1/datasets/{SMALLEST_DATASET_ID}/versions"

COLLECTIONS_API = "https://api.cellxgene.cziscience.com/curation/v1/collections?visibility=PUBLIC"

def fetch_collections():
    """
    Fetches collections from the CellxGene API.
    If test mode is enabled, fetches only the smallest dataset.
    """
    response = requests.get(COLLECTIONS_API)
    
    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch collections! Status: {response.status_code}", file=sys.stderr)
        sys.exit(1)

    collections_data = response.json()["collections"]
    return collections_data

def fetch_test_dataset():
    """
    Fetch only the smallest test dataset.
    """
    response = requests.get(SMALLEST_DATASET_URL)
    
    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch test dataset! Status: {response.status_code}", file=sys.stderr)
        sys.exit(1)

    dataset_info = response.json()
    return [{
        "collection_id": "TEST_COLLECTION",
        "collection_url": "https://cellxgene.cziscience.com/collections/test",
        "dataset_id": dataset_info["id"],
        "dataset_version_id": dataset_info["version_id"],
        "dataset_url": dataset_info["dataset_assets"][0]["url"],  # Assuming the first asset is the H5AD file
    }]

def save_datasets_metadata(test_mode):
    """
    Fetch datasets from CellxGene and save as JSON.
    """
    if test_mode.lower() == "true":
        print("🔹 Running in TEST MODE: Fetching only the smallest dataset.")
        datasets = fetch_test_dataset()
    else:
        print("🔹 Running in FULL MODE: Fetching all datasets.")
        collections = fetch_collections()
        datasets = [
            {
                "collection_id": col["collection_id"],
                "collection_url": col["collection_url"],
                "dataset_id": ds["dataset_id"],
                "dataset_version_id": ds["dataset_version_id"],
                "dataset_url": ds["dataset_assets"][0]["url"],
            }
            for col in collections for ds in col["datasets"]
        ]

    with open("datasets_info.json", "w", encoding="utf-8") as f:
        json.dump(datasets, f, indent=4)

    print(f"✅ Dataset metadata saved. Total datasets: {len(datasets)}")

if __name__ == "__main__":
    test_mode_flag = sys.argv[1]
    save_datasets_metadata(test_mode_flag)

