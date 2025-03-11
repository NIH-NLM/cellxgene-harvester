import os
import json

def parse_collections(collections_file, test_mode):
    """Parse collections and extract dataset IDs, saving to datasets_info.json."""
    
    # Ensure output directory exists
    os.makedirs("results", exist_ok=True)

    # Correct output file path
    output_path = os.path.join("results", "datasets_info.json")

    # Read collections file
    with open(collections_file, "r") as f:
        collections = json.load(f)

    # Extract dataset IDs
    datasets = []
    for collection in collections:
        datasets.extend(collection.get("datasets", []))

    # Write datasets info to the correct output path
    with open(output_path, "w") as f:
        json.dump(datasets, f, indent=2)

    print(f"Parsed {len(datasets)} datasets and saved to {output_path}")

# Call the function (assuming CLI arguments)
if __name__ == "__main__":
    import sys
    collections_file = sys.argv[1]
    test_mode = sys.argv[2].lower() == "true"
    parse_collections(collections_file, test_mode)

