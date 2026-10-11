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
nowhere in a path: a store holds the current files, and git keeps the older ones.

Step 1 always asks the API (one call, a few seconds). Steps 2 and 3 take --store, a folder or
web address that holds the current files. If the collections file just fetched has the same
SHA-256 as the one the stored provenance file lists, nothing in the API has changed: the stored
file is used and the step is not run again (Step 3 asks the API once for each dataset and takes
about ten minutes). If it differs, or the store has no such file, the step is run.

Every dataset file written by Step 4 records the snapshot it came from in
filter_choices.snapshot, so the date travels with the data.

Usage:
    snapshot.start(run_dir())                       # Step 1, after a fetch
    snapshot.record(run_dir(), "all_datasets.csv")  # Steps 2 and 3, after a build
    snapshot.reuse_if_current(store, "all_datasets.csv", run_dir(), logger)
    snapshot.filter_choices_entry(run_dir())        # Step 4
"""

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone

from harvester import store as store_module

PROVENANCE = "api_snapshot.provenance.json"
API_URL = "https://api.cellxgene.cziscience.com/curation/v1/collections"
FILES = ("collections_metadata.json", "all_datasets.csv", "all_datasets_complete.csv")


class PrintLogger:
    """The steps 1 to 3 print their messages; this lets reuse() write in the same way."""
    info = staticmethod(print)
    warning = staticmethod(print)


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


def reuse_if_current(store, name, folder, logger):
    """Take the file called name from the store if the API has not changed since it was made.

    The API has not changed when the collections file in folder (just fetched by Step 1) has the
    SHA-256 that the stored provenance file lists for collections_metadata.json. The stored file
    must also be intact: its SHA-256 must be the one the provenance file lists for it.
    Return True if the file was copied into folder together with the stored provenance file, so
    the snapshot keeps the date of the fetch that made it. Return False if the step has to run:
    the store has no such file, or the API has changed.
    """
    fresh = os.path.join(folder, "collections_metadata.json")
    if not os.path.exists(fresh):
        raise FileNotFoundError(f"{fresh}: run Step 1 first")
    with tempfile.TemporaryDirectory() as tmp:
        prov_file = store_module.fetch(store, PROVENANCE, tmp)
        found = store_module.fetch(store, name, tmp)
        if prov_file is None or found is None:
            logger.info(f"The store {store} has no {name} with its provenance file: {name} is built")
            return False
        info = json.load(open(prov_file, encoding="utf-8"))
        files = info.get("files", {})
        if files.get("collections_metadata.json", {}).get("sha256") != sha256_of(fresh):
            logger.info(f"The API has changed since the files in the store {store} were made: {name} is built")
            return False
        expected = files.get(name, {}).get("sha256")
        if not expected or sha256_of(found) != expected:
            raise ValueError(f"{name} in the store {store}: its SHA-256 is not the one in the provenance "
                             f"file; the file is not used")
        shutil.copyfile(found, os.path.join(folder, name))
        shutil.copyfile(prov_file, os.path.join(folder, PROVENANCE))
    logger.info(f"The API has not changed since {info['date']}: reused {name} from the store {store} (sha256 {expected})")
    return True


def filter_choices_entry(folder):
    """What Step 4 writes in filter_choices.snapshot: the date of the snapshot and the SHA-256
    of its files. None if the folder has no provenance file (a CSV made by an older version)."""
    info = read(folder)
    if info is None:
        return None
    return {"kind": info["kind"], "date": info["date"],
            "files": {name: entry["sha256"] for name, entry in info.get("files", {}).items()}}
