import requests
import json

CELLXGENE_API = "https://api.cellxgene.cziscience.com/curation/v1/collections?visibility=PUBLIC"

response = requests.get(CELLXGENE_API)
collections_json = response.json()

# Print first 3 entries to check structure
print(json.dumps(collections_json[:3], indent=2))
