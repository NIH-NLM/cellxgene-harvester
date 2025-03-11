import os
import requests
import json
import sys

# Define API endpoint
COLLECTIONS_API_URL = "https://api.cellxgene.cziscience.com/curation/v1/collections?visibility=PUBLIC"

def fetch_collections(output_filename):
    """Fetch collections from CellxGene API and save to collections_info.json."""
    response = requests.get(COLLECTIONS_API_URL)
    
    if response.status_code != 200:
        raise Exception(f"ERROR: Failed to fetch collections (HTTP {response.status_code})")
    
    collections = response.json()

    with open(output_filename, "w") as f:
        json.dump(collections, f, indent=2)
    
    print(f"Saved collections info to {output_filename}")

# Run script
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fetch_collections.py <output_filename>")
        sys.exit(1)
    
    output_filename = sys.argv[1]
    print(f"output file name is {output_filename}")
    fetch_collections(output_filename)

