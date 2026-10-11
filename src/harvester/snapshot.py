#!/usr/bin/env python3
"""
The snapshot of the CellxGene API.

Steps 1 to 3 ask the CellxGene API for every collection and every dataset. The API has no
release number: it is live, and its answer changes. The three files the steps write are
one snapshot, made from the same fetch:

  collections_metadata.json   Step 1   the collections and their datasets
  all_datasets.csv            Step 2   one row for each dataset
  all_datasets_complete.csv   Step 3   the rows with title, cell count, h5ad address, schema version

api_snapshot.provenance.json holds the date of the fetch, the API address, the harvester
version, and for each file its SHA-256 and the time it was made. The date is in this file and
in no path: the folder holds the current files, and git keeps the older ones.

Step 1 always asks the API (one call, a few seconds). If the answer is the same as the
collections file already in the folder (same SHA-256), nothing has changed: the folder and its
provenance file are left as they are, and Steps 2 and 3 find their files already there. If the
answer is different, a new provenance file is started and Steps 2 and 3 are made again (Step 3
asks the API once for each dataset and takes about ten minutes).

Every dataset file written by Step 4 records the snapshot it came from in
filter_choices.snapshot, so the date travels with the data.

Usage:
    snapshot.fetched(".", version)            # Step 1, after the fetch
    snapshot.is_current(".", "all_datasets.csv")   # Steps 2 and 3: True if the file is already there
    snapshot.record(".", "all_datasets.csv")  # Steps 2 and 3, after making the file
    snapshot.filter_choices_entry(".")        # Step 4
"""

import hashlib
import json
import os
from datetime import datetime, timezone

PROVENANCE = "api_snapshot.provenance.json"
API_URL = "https://api.cellxgene.cziscience.com/curation/v1/collections"
FILES = ("collections_metadata.json", "all_datasets.csv", "all_datasets_complete.csv")


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(folder):
    """The provenance of the snapshot in folder, or None if there is none."""
    path = os.path.join(folder, PROVENANCE)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(folder, info):
    """Write the provenance file. The file is replaced, not written through: in a workflow the
    file may be a link to the output of an earlier task, which must stay as it was."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, PROVENANCE)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def start(folder, version="unknown"):
    """A new snapshot begins with a fresh fetch (Step 1): today's date, and no files yet."""
    write(folder, {"kind": "api", "date": now()[:10], "api_url": API_URL,
                   "harvester_version": version, "fetched_at": now(), "files": {}})


def record(folder, name):
    """Record the SHA-256 and the time of a file that was just built in folder."""
    info = read(folder)
    if info is None:
        info = {"kind": "api", "date": now()[:10], "api_url": API_URL, "fetched_at": None, "files": {}}
    info["files"][name] = {"sha256": sha256_of(os.path.join(folder, name)), "built_at": now()}
    write(folder, info)


def fetched(folder, version="unknown"):
    """Step 1, after the fetch. If the collections file is the same as the one the provenance file
    lists, nothing has changed and the provenance file is left as it is. Otherwise a new snapshot
    begins, with today's date."""
    path = os.path.join(folder, "collections_metadata.json")
    info = read(folder)
    if info and info.get("files", {}).get("collections_metadata.json", {}).get("sha256") == sha256_of(path):
        print(f"The API has not changed since {info['date']}")
        return
    start(folder, version)
    record(folder, "collections_metadata.json")
    print(f"This is the snapshot of {read(folder)['date']}")


def is_current(folder, name):
    """True if the file called name is already in folder, is the one the provenance file lists, and
    was made from the collections file that is in folder now. Then it is not made again."""
    info = read(folder)
    path = os.path.join(folder, name)
    if not info or not os.path.exists(path):
        return False
    files = info.get("files", {})
    collections = os.path.join(folder, "collections_metadata.json")
    return (os.path.exists(collections)
            and files.get("collections_metadata.json", {}).get("sha256") == sha256_of(collections)
            and files.get(name, {}).get("sha256") == sha256_of(path))


def filter_choices_entry(folder):
    """What Step 4 writes in filter_choices.snapshot: the date of the snapshot and the SHA-256
    of its files. None if the folder has no provenance file (a CSV made by an older version)."""
    info = read(folder)
    if info is None:
        return None
    return {"kind": info["kind"], "date": info["date"],
            "files": {name: entry["sha256"] for name, entry in info.get("files", {}).items()}}
