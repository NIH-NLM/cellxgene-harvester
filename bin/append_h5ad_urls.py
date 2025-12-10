#!/usr/bin/env python3

import csv
import requests
import time

INPUT_CSV = "data/all_datasets.csv"
OUTPUT_CSV = "data/all_datasets_with_h5ad.csv"

API_TEMPLATE = (
    "https://api.cellxgene.cziscience.com/curation/v1/"
    "collections/{collection_id}/datasets/{dataset_id}"
)

REQUEST_DELAY = 0.2  # seconds between requests


def fetch_h5ad_and_cell_count(collection_id, dataset_id):
    url = API_TEMPLATE.format(
        collection_id=collection_id,
        dataset_id=dataset_id
    )

    try:
        r = requests.get(url, headers={"accept": "application/json"}, timeout=30)
        if r.status_code != 200:
            return "", ""

        data = r.json()

        cell_count = data.get("cell_count", "")

        h5ad_url = ""
        for asset in data.get("assets", []):
            if asset.get("filetype") == "H5AD":
                h5ad_url = asset.get("url", "")
                break

        return cell_count, h5ad_url

    except Exception:
        return "", ""


def main():
    with open(INPUT_CSV, newline="") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)
        original_fieldnames = reader.fieldnames or []

        print(f"Read {len(rows)} rows from {INPUT_CSV}")

    # Append in fixed order: cell_count first, then h5ad_url
    fieldnames = original_fieldnames.copy()
    if "cell_count" not in fieldnames:
        fieldnames.append("cell_count")
    if "h5ad_url" not in fieldnames:
        fieldnames.append("h5ad_url")

    for row in rows:
        collection_id = row.get("collection_id", "")
        dataset_id = row.get("dataset_id", "")

        print(f"Fetching: collection_id={collection_id}, dataset_id={dataset_id}")
        cell_count, h5ad_url = fetch_h5ad_and_cell_count(collection_id, dataset_id)
        print(f" → cell_count={cell_count}, h5ad_url={h5ad_url}")

        if not collection_id or not dataset_id:
            row["cell_count"] = ""
            row["h5ad_url"] = ""
            continue

        cell_count, h5ad_url = fetch_h5ad_and_cell_count(collection_id, dataset_id)
        row["cell_count"] = cell_count
        row["h5ad_url"] = h5ad_url

        time.sleep(REQUEST_DELAY)

    with open(OUTPUT_CSV, "w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

