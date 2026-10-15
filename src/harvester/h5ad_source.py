#!/usr/bin/env python3
"""
Read the cells of a dataset from an h5ad file, and write the cells that pass
the filters to a new h5ad file.

The h5ad file is opened lazily (LazyH5ad): only obs and var are read into memory.
Every matrix (X, raw.X and each layer) stays on disk, and is read and written a
block of cells at a time when the filtered cells are written. anndata's own backed
mode reads the layers, obsm, obsp and uns completely when it opens a file, which
needs more memory than a file with large layers has.

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


def _elements():
    """read_elem, write_elem and sparse_dataset of the installed anndata (the names moved in 0.11)."""
    try:
        from anndata.io import read_elem, sparse_dataset, write_elem
    except ImportError:                      # anndata 0.10
        from anndata.experimental import read_elem, sparse_dataset, write_elem
    return read_elem, write_elem, sparse_dataset


class LazyH5ad:
    """An h5ad file opened for counting and for writing a filtered copy, with every matrix left on disk.

    Read into memory when the file is opened: obs and var (the metadata of the cells and genes).
    Left on disk: X, raw.X and every layer, whether they are sparse or dense. They are read
    a block of rows at a time by write_filtered. obsm, obsp, varm, varp and uns are read only when
    a filtered copy is written.
    """

    def __init__(self, path):
        import h5py
        read_elem, _, sparse_dataset = _elements()
        self.path = path
        self.file = h5py.File(path, "r")
        f = self.file
        self.obs = read_elem(f["obs"])
        self.var = read_elem(f["var"])
        self.n_obs, self.n_vars = len(self.obs), len(self.var)
        self.X = self._matrix(f["X"]) if "X" in f else None
        self.layers = {k: self._matrix(f["layers"][k]) for k in f["layers"]} if "layers" in f else {}
        self.raw = None
        if "raw" in f:
            self.raw = {"X": self._matrix(f["raw/X"]), "var": read_elem(f["raw/var"]),
                        "varm": read_elem(f["raw/varm"]) if "varm" in f["raw"] else {}}

    @staticmethod
    def _matrix(node):
        """A dense h5py dataset as it is, or a sparse group as a backed sparse matrix."""
        import h5py
        if isinstance(node, h5py.Dataset):
            return node
        return _elements()[2](node)

    def schema_version(self):
        """The CellxGene schema version of the file (uns["schema_version"]), or None."""
        if "uns" in self.file and "schema_version" in self.file["uns"]:
            value = self.file["uns/schema_version"][()]
            return value.decode() if isinstance(value, bytes) else str(value)
        return None

    def read(self, name):
        """One of obsm, varm, obsp, varp, uns, as the dict anndata reads it (empty when the file has none)."""
        return _elements()[0](self.file[name]) if name in self.file else {}

    def close(self):
        self.file.close()


def open_h5ad(path):
    """Open an h5ad file lazily: obs and var are read, every matrix stays on disk."""
    return LazyH5ad(path)


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


# Matrices are written this many cells at a time, so memory does not grow with the dataset.
BLOCK_CELLS = 20000


def take_rows(source, rows):
    """The given rows (increasing) of a dense h5py dataset or a backed sparse matrix."""
    import numpy as np
    if hasattr(source, "format"):                                   # a backed sparse matrix
        return source[rows]
    if len(rows) and rows[-1] - rows[0] + 1 == len(rows):           # one run of rows: one slice
        return source[int(rows[0]):int(rows[-1]) + 1]
    return source[np.asarray(rows)]


def stream_rows(source, group, name, rows, block):
    """Write the given rows of a matrix to group[name], one block of rows at a time."""
    _, write_elem, sparse_dataset = _elements()
    for start in range(0, len(rows), block):
        part = take_rows(source, rows[start:start + block])
        if hasattr(part, "format"):                                 # sparse
            if start == 0:
                write_elem(group, name, part, dataset_kwargs={"compression": "gzip"})
            else:
                sparse_dataset(group[name]).append(part)
        else:                                                       # dense
            if start == 0:
                dataset = group.create_dataset(name, data=part, maxshape=(None,) + part.shape[1:],
                                               chunks=True, compression="gzip")
                dataset.attrs["encoding-type"] = "array"
                dataset.attrs["encoding-version"] = "0.2.0"
            else:
                dataset = group[name]
                dataset.resize(dataset.shape[0] + part.shape[0], axis=0)
                dataset[-part.shape[0]:] = part


def write_filtered(adata, mask, path, block=BLOCK_CELLS):
    """Write the cells where mask is True to a new h5ad file. Return their number.

    adata is a LazyH5ad and mask is a boolean array in the order of adata.obs. The new
    file keeps X, obs, var, obsm, obsp, varm, varp, layers, raw and uns of those cells.
    Every matrix is written block cells at a time, so a dataset of any size, with any
    number of layers, needs about the same memory.
    """
    import anndata
    import h5py
    import numpy as np

    read_elem, write_elem, _ = _elements()
    rows = np.flatnonzero(np.asarray(mask))
    # what is not a large matrix: obs, var, the embeddings (a few numbers for each cell), the
    # neighbour graphs, and uns
    pairwise = lambda graph: graph.tocsr()[rows][:, rows] if hasattr(graph, "tocsr") else graph[np.ix_(rows, rows)]
    small = anndata.AnnData(
        obs=adata.obs.iloc[rows].copy(), var=adata.var.copy(), uns=adata.read("uns"),
        obsm={k: v[rows] if not hasattr(v, "iloc") else v.iloc[rows] for k, v in adata.read("obsm").items()},
        varm=adata.read("varm"), varp=adata.read("varp"),
        obsp={k: pairwise(v) for k, v in adata.read("obsp").items()})
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    small.write_h5ad(path, compression="gzip")
    with h5py.File(path, "r+") as f:
        if adata.X is not None:
            stream_rows(adata.X, f, "X", rows, block)
        if adata.layers:
            layers = f.require_group("layers")
            for name, matrix in adata.layers.items():
                stream_rows(matrix, layers, name, rows, block)
        if adata.raw is not None:
            raw = f.create_group("raw")
            raw.attrs["encoding-type"] = "raw"
            raw.attrs["encoding-version"] = "0.1.0"
            write_elem(raw, "var", adata.raw["var"])
            if adata.raw["varm"]:
                write_elem(raw, "varm", adata.raw["varm"])
            stream_rows(adata.raw["X"], raw, "X", rows, block)
    return int(len(rows))
