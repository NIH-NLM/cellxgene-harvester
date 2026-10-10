#!/usr/bin/env python3
"""
Reuse a file that was built before.

A file that is expensive or slow to make (a resolved ontology file, the gene table of a
GENCODE release) is made once and kept in a store. A later run looks in the store first,
checks that the file is the one it needs, and uses it instead of making it again.

The store is given as one of
  a folder on this machine              /data/store
  a web address                         https://raw.githubusercontent.com/NIH-NLM/nlm-ckn/<tag>/data/prod/gencode
  an S3 address (a public bucket)       s3://bucket/folder

Pin a web address to a tag or a commit, never to main, so the same address always gives
the same file. A file that is not in the store is built as usual. --refresh skips the store.

Usage:
    path = fetch("https://.../ontology_lookup_server", "uberon_kidney.json", "run-folder")
    if path is None:
        ...build it...
"""

import os
import shutil
from urllib.parse import quote

import requests


def web_address(store, name):
    """The address of one file in a web or S3 store. S3 addresses are read over https,
    so the bucket must be public."""
    if store.startswith("s3://"):
        bucket, _, folder = store[len("s3://"):].partition("/")
        path = "/".join(part for part in (folder.strip("/"), quote(name, safe="/")) if part)
        return f"https://{bucket}.s3.amazonaws.com/{path}"
    return f"{store.rstrip('/')}/{quote(name, safe='/')}"


def fetch(store, name, dest_dir):
    """Copy the file called name from the store into dest_dir. Return its path, or None if
    the store does not have it. Any other failure (no access, a store that is not there)
    is raised, so a mistake in the store address is not mistaken for 'not built yet'."""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, name)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if store.startswith(("http://", "https://", "s3://")):
        reply = requests.get(web_address(store, name), timeout=60)
        if reply.status_code == 404:
            return None
        reply.raise_for_status()
        with open(dest, "wb") as f:
            f.write(reply.content)
        return dest
    source = os.path.join(store, name)
    if not os.path.isdir(store):
        raise FileNotFoundError(f"the store {store} is not a folder")
    if not os.path.exists(source):
        return None
    shutil.copyfile(source, dest)
    return dest
