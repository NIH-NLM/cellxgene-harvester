#!/usr/bin/env python3
"""
The dated snapshot of the CellxGene API.

Steps 1 to 3 ask the CellxGene API for every collection and every dataset. The API has no
release number: it is live, and the answer changes from day to day. A snapshot gives the
answer of one day a name, so it can be kept, used again, and cited.

A snapshot is three files, all made from the same fetch:

  collections_metadata.json   Step 1   the collections and their datasets
  all_datasets.csv            Step 2   one row for each dataset
  all_datasets_complete.csv   Step 3   the rows with title, cell count, h5ad address, schema version

and one provenance file, api_snapshot.provenance.json, that holds the date of the fetch, the
API address, the harvester version, and for each file its SHA-256 and the time it was made.

In a store, a snapshot is the folder api_snapshot_<YYYY-MM-DD>. A step given --snapshot DATE
and --store takes its file from there, after checking its SHA-256 against the provenance file,
and does not ask the API again. Without --snapshot the step asks the API, and the snapshot
is the date of today.

Every dataset file written by Step 4 records the snapshot it came from in
filter_choices.snapshot, so the date travels with the data.

Usage:
    snapshot.start(run_dir())                       # Step 1, after a fresh fetch
    snapshot.record(run_dir(), "all_datasets.csv")  # Steps 2 and 3, after a fresh build
    snapshot.reuse(store, "2026-08-03", "all_datasets.csv", run_dir(), logger)
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


def folder_name(date):
    """The folder of a snapshot in a store."""
    return f"api_snapshot_{date}"


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


def reuse(store, date, name, folder, logger):
    """Take the file called name of the snapshot of this date from the store.

    Return True if it was copied into folder. A snapshot or a file that is not in the store
    is an error: the date was asked for by name, so building another one would give the user
    a different snapshot from the one they asked for. So is a file whose SHA-256 is not the one
    in the provenance file.
    """
    where = folder_name(date)
    with tempfile.TemporaryDirectory() as tmp:
        prov_file = store_module.fetch(store, f"{where}/{PROVENANCE}", tmp)
        if prov_file is None:
            raise FileNotFoundError(f"the store {store} has no snapshot {where}")
        info = json.load(open(prov_file, encoding="utf-8"))
        expected = info.get("files", {}).get(name, {}).get("sha256")
        if not expected:
            raise ValueError(f"the provenance file of {where} has no entry for {name}")
        found = store_module.fetch(store, f"{where}/{name}", tmp)
        if found is None:
            raise FileNotFoundError(f"the store {store} has no {name} in {where}")
        if sha256_of(found) != expected:
            raise ValueError(f"{where}/{name}: its SHA-256 is not the one in the provenance file; "
                             f"the file is not used")
        os.makedirs(folder, exist_ok=True)
        shutil.copyfile(found, os.path.join(folder, name))
        shutil.copyfile(prov_file, os.path.join(folder, PROVENANCE))
    logger.info(f"Reused {name} of the snapshot {date} from the store {store} (sha256 {expected})")
    return True


def filter_choices_entry(folder):
    """What Step 4 writes in filter_choices.snapshot: the date of the snapshot and the SHA-256
    of its files. None if the folder has no provenance file (a CSV made by an older version)."""
    info = read(folder)
    if info is None:
        return None
    return {"kind": info["kind"], "date": info["date"],
            "files": {name: entry["sha256"] for name, entry in info.get("files", {}).items()}}
