#!/usr/bin/env python3

import os
import json
import csv
from glob import glob

DATA_DIR = "data"
OUTPUT_CSV = os.path.join(DATA_DIR, "all_datasets.csv")

STATIC_FIELDS = {
    "filter_normal": "TRUE",
    "metric": "euclidean",
    "save_scores": "TRUE",
    "save_cluster_summary": "TRUE",
    "save_annotation": "TRUE",
}

CSV_HEADER = [
    "collection_url",
    "collection_id",
    "collection_version_id",
    "dataset_id",
    "dataset_version_id",
    "first_author",
    "journal",
    "is_preprint",
    "year",
    "revised_at",
    "visibility",
    "organism",
    "tissue",
    "disease",
    "author_cell_type",
    "cell_count",
    "filter_normal",
    "metric",
    "save_scores",
    "save_cluster_summary",
    "save_annotation",
]

def safe_label(entry):
    if isinstance(entry, list) and entry:
        return entry[0].get("label", "")
    return ""

def main():
    rows = []

    print("Scanning collections...")
    collection_dirs = glob(os.path.join(DATA_DIR, "collection_*"))

    for collection_dir in collection_dirs:
        collection_file = glob(os.path.join(collection_dir, "collection_*.pretty.json"))
        if not collection_file:
            continue
        collection_file = collection_file[0]

        with open(collection_file) as f:
            collection_data = json.load(f)

        collection_url = collection_data.get("collection_url", "")
        collection_id = collection_data.get("collection_id", "")
        collection_version_id = collection_data.get("collection_version_id", "")
        revised_at = collection_data.get("revised_at", "")
        visibility = collection_data.get("visibility", "")

        publisher = collection_data.get("publisher_metadata") or {}
        first_author = ""
        journal = ""
        is_preprint = ""
        year = ""

        if isinstance(publisher, dict):
            authors = publisher.get("authors", [])
            if isinstance(authors, list) and authors and isinstance(authors[0], dict):
                first_author = authors[0].get("family", "")
            journal = publisher.get("journal", "")
            is_preprint = publisher.get("is_preprint", "")
            year_val = publisher.get("published_year")
            if year_val is not None:
                year = str(year_val)

        dataset_files = glob(os.path.join(collection_dir, "dataset_*.pretty.json"))
        latest_versions = {}

        for dataset_file in dataset_files:
            with open(dataset_file) as f:
                try:
                    ds = json.load(f)
                except json.JSONDecodeError:
                    continue

            ds_id = ds.get("dataset_id", "")
            ds_version_id = ds.get("dataset_version_id", "")

            if not ds_id:
                continue

            current = latest_versions.get(ds_id)
            if not current or created_at > current.get("created_at", ""):
                latest_versions[ds_id] = {
                    "dataset_id": ds_id,
                    "dataset_version_id": ds_version_id,
                    "organism": safe_label(ds.get("organism")),
                    "tissue": safe_label(ds.get("tissue")),
                    "disease": safe_label(ds.get("disease")),
                }

        for ds in latest_versions.values():
            row = {
                "collection_url": collection_url,
                "collection_id": collection_id,
                "collection_version_id": collection_version_id,
                "dataset_id": ds["dataset_id"],
                "dataset_version_id": ds["dataset_version_id"],
                "first_author": first_author,
                "journal": journal,
                "is_preprint": is_preprint,
                "year": year,
                "revised_at": revised_at,
                "visibility": visibility,
                "organism": ds["organism"],
                "tissue": ds["tissue"],
                "disease": ds["disease"],
                "author_cell_type": "",
                "cell_count": "",
                **STATIC_FIELDS,
            }
            rows.append(row)

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done: {len(rows)} datasets written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()

