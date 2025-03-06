import requests
import json

API_URL = "https://api.cellxgene.cziscience.com/v2/collections"

def fetch_collections():
    response = requests.get(API_URL)
    response.raise_for_status()
    collections = response.json()
    
    datasets = []
    for collection in collections.get('collections', []):
        collection_id = collection['id']
        collection_version_id = collection['version_id']
        collection_url = collection['url']
        
        for dataset in collection['datasets']:
            dataset_id = dataset['id']
            dataset_version_id = dataset['version_id']
            dataset_url = dataset['url']
            
            datasets.append({
                "collection_id": collection_id,
                "collection_version_id": collection_version_id,
                "collection_url": collection_url,
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "dataset_url": dataset_url
            })
    
    with open("datasets_info.json", "w") as f:
        json.dump(datasets, f)

if __name__ == "__main__":
    fetch_collections()
