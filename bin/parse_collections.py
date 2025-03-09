import json
import sys

def extract_datasets(collections_json_file, output_file):
    """
    Parses collections JSON and extracts datasets.
    """
    with open(collections_json_file, "r") as f:
        collections_data = json.load(f)

    datasets_list = []
    for collection in collections_data:
        collection_id = collection.get("collection_id", "UNKNOWN")
        for dataset in collection.get("datasets", []):
            dataset_entry = {
                "collection_id": collection_id,
                "dataset_id": dataset.get("dataset_id", "UNKNOWN"),
                "dataset_version_id": dataset.get("dataset_version_id", "UNKNOWN"),
                "dataset_url": f"https://cellxgene.cziscience.com/d/{dataset.get('dataset_id', 'UNKNOWN')}"
            }
            datasets_list.append(dataset_entry)

    with open(output_file, "w") as f:
        json.dump(datasets_list, f, indent=4)

    print(f"✅ Parsed {len(datasets_list)} datasets into {output_file}")

if __name__ == "__main__":
    collections_json_file = sys.argv[1]
    output_file = sys.argv[2]
    extract_datasets(collections_json_file, output_file)

