#!/usr/bin/env python3
"""
Read the cells of a dataset from an h5ad file, and write the cells that pass
the filters to a new h5ad file.

The h5ad file is opened in backed mode, so only the metadata (obs) is read
into memory. The expression matrix is read only when the filtered cells are
written.

Usage:
    local, downloaded = fetch_h5ad(location, workdir)
    adata = open_h5ad(local)
    obs   = read_obs(adata)
    write_filtered(adata, mask, "filtered_h5ad/<dataset_id>.filtered.h5ad")
"""

import os
from urllib.parse import urlparse

import requests

from harvester.io_utils import FACETS


def id_column(facet):
    return f"{facet}_ontology_term_id"


def obs_columns():
    """The obs columns that are read: donor_id, and a label and an id for each facet."""
    columns = ["donor_id"]
    for facet in FACETS:
        columns += [facet, id_column(facet)]
    return columns


def fetch_h5ad(location, folder):
    """Return (local path, downloaded) for the h5ad file at location.

    A local path is used as it is. An http or https address is downloaded into
    folder, and downloaded is then True so the caller can delete the copy.
    Any other address, such as s3://, must be staged by the caller first.
    """
    if location.startswith(("http://", "https://")):
        os.makedirs(folder, exist_ok=True)
        local = os.path.join(folder, os.path.basename(urlparse(location).path) or "dataset.h5ad")
        with requests.get(location, stream=True, timeout=60) as reply:
            reply.raise_for_status()
            with open(local, "wb") as f:
                for chunk in reply.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        return local, True
    if "://" in location:
        raise ValueError(f"{location}: only a local path, http or https can be read here; "
                         f"stage other addresses (for example s3://) as a local file first")
    if not os.path.exists(location):
        raise FileNotFoundError(f"h5ad file not found: {location}")
    return location, False


def open_h5ad(path):
    """Open an h5ad file in backed mode (the expression matrix stays on disk)."""
    import anndata
    return anndata.read_h5ad(path, backed="r")


def read_obs(adata):
    """Return the obs columns that counting needs, as a table.

    Raises ValueError that names every column the file does not have.
    """
    columns = obs_columns()
    missing = [c for c in columns if c not in adata.obs.columns]
    if missing:
        raise ValueError(f"the h5ad file has no obs column {missing}; "
                         f"it must hold {columns}")
    return adata.obs[columns].copy()


def write_filtered(adata, mask, path):
    """Write the cells where mask is True to a new h5ad file. Return their number.

    mask is a boolean array in the order of adata.obs. The new file keeps the
    expression matrix, obs, var, obsm and uns of those cells.
    """
    kept = adata[mask].to_memory()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    kept.write_h5ad(path, compression="gzip")
    return int(kept.n_obs)
