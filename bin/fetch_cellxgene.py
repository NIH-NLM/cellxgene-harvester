import requests
import json
import sys

# ✅ Standard API endpoints
COLLECTIONS_API_URL = "https://api.cellxgene.cziscience.com/curation/v1/collections?visibility=PUBLIC"
DATASET_API_BASE = "https://api.cellxgene.cziscience.com/curation/v1/datasets"

# ✅ Smallest dataset for testing
TEST_DATASET_ID = "0895c838-e550-48a3-a777-dbcd35d30272"

def fetch_collections():
    """ Fetch all collections from the API """
    print(f"🔹 Fetching collections from: {COLLECTIONS_API_URL}")
    response = requests.get(COLLECTIONS_API_URL)
    if response.status_code != 200:
        raise Exception(f"❌ ERROR: Failed to fetch collections (HTTP {response.status_code})")
    return response.json()["collections"]

def fetch_datasets_from_collections(collections, test_mode):
    """ Extract dataset information from collections """
    datasets = []
    for collection in collections:
        for dataset in collection.get("datasets", []):
            if test_mode and dataset["dataset_id"] != TEST_DATASET_ID:
                continue  # ✅ In test mode, only include the small dataset
            datasets.append({
                "collection_id": collection["collection_id"],
                "dataset_id": dataset["dataset_id"],
                "dataset_version_id": dataset["dataset_version_id"],
                "dataset_url": f"https://cellxgene.cziscience.com/d/{dataset['dataset_id']}"
            })
    return datasets

def save_datasets_metadata(test_mode):
    """ Save dataset metadata; only fetch one dataset in test mode """
    collections = fetch_collections()
    datasets = fetch_datasets_from_collections(collections, test_mode)

    with open("datasets_info.json", "w") as f:
        json.dump(datasets, f, indent=4)
    
    print(f"✅ Saved {len(datasets)} datasets to datasets_info.json")

# ✅ Run the script
if __name__ == "__main__":
    test_mode_flag = sys.argv[1].lower() == "true"
    save_datasets_metadata(test_mode_flag)

