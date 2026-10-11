#!/usr/bin/env python3
"""
Build the gene id to gene name table of one GENCODE release.

CellxGene fixes the GENCODE release of the human genes in a dataset by its schema
version (see GENCODE_BY_SCHEMA in io_utils). In a dataset, feature_name is the
gene_name of that release's gene reference, or the gene id when the release gives no
name. This table holds those names, so a lookup from it gives the names CellxGene gave.

The release is downloaded from the GENCODE site, its MD5 is checked against the MD5SUMS
file of the release, and the gene lines of the annotation are written to

  gene_mapping_gencode_v<N>.csv              one row for each gene
  gene_mapping_gencode_v<N>.provenance.json  where the table came from

The CSV holds no date, and its rows are sorted, so the same release always gives the
same bytes. The date and the checksums are in the provenance file. A file that is
published is never overwritten: a new release is a new file.

Columns of the CSV:
  ensembl_gene_id  the id without its version suffix (ENSG00000223972.6 gives ENSG00000223972;
                   a suffix such as _PAR_Y stays)
  gene_name        the gene_name of the annotation (the id when the annotation has no name)
  gene_type        for example protein_coding, lncRNA
  hgnc_id          for example HGNC:37102; empty when the gene has none
  has_symbol       True when gene_name is a name, False when it is only the gene id
  gencode_release  the release number

Usage:
    python -m harvester.build_gene_mapping --gencode-release 48 --output-dir gene_mapping
    cellxgene-harvester build-gene-mapping                       # the release of the newest CellxGene schema
    cellxgene-harvester build-gene-mapping --gencode-release 48 --gtf FILE.gtf.gz

A table of this release that is already in the output folder and is intact is not made again.
"""

import gzip
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

from harvester.io_utils import GENCODE_BY_SCHEMA, REQUIRED_GENCODE_RELEASE, write_csv
from harvester.logger import log_command, log_finish, setup_logger
from harvester.run_dir import run_dir

BASE_URL = "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{release}"
GTF_NAME = "gencode.v{release}.primary_assembly.annotation.gtf.gz"
COLUMNS = ["ensembl_gene_id", "gene_name", "gene_type", "hgnc_id", "has_symbol", "gencode_release"]

# A gene id with its version suffix: ENSG00000223972.6 or ENSG00000182378.14_PAR_Y
VERSIONED_ID = re.compile(r"^(ENSG\d+)\.\d+(.*)$")
ATTRIBUTE = re.compile(r'(\w+) "([^"]*)"')


def strip_version(gene_id):
    """ENSG00000223972.6 gives ENSG00000223972. Any suffix after the version stays."""
    match = VERSIONED_ID.match(gene_id)
    return match.group(1) + match.group(2) if match else gene_id


def parse_gene_line(line):
    """Return the attributes of a gene line of a GTF file as a dict, or None for any
    other line (a comment, an exon, a transcript, ...)."""
    if line.startswith("#"):
        return None
    fields = line.rstrip("\n").split("\t")
    if len(fields) < 9 or fields[2] != "gene":
        return None
    return dict(ATTRIBUTE.findall(fields[8]))


def read_genes(gtf_path, release):
    """Return the rows of the table, sorted by gene id, and the header lines (##) of the file."""
    rows, header = {}, []
    with gzip.open(gtf_path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("##"):
                header.append(line.rstrip("\n"))
                continue
            attributes = parse_gene_line(line)
            if not attributes or "gene_id" not in attributes:
                continue
            gene_id = strip_version(attributes["gene_id"])
            name = attributes.get("gene_name") or gene_id
            rows[gene_id] = {
                "ensembl_gene_id": gene_id,
                "gene_name": name,
                "gene_type": attributes.get("gene_type", ""),
                "hgnc_id": attributes.get("hgnc_id", ""),
                "has_symbol": name != gene_id,
                "gencode_release": release,
            }
    return [rows[key] for key in sorted(rows)], header


def write_table(rows, path):
    """Write the table through the one place that writes CSV files (it refuses a value
    such as "11,464"). The rows are already sorted, so the bytes depend only on the input."""
    write_csv(path, COLUMNS, rows)


def file_digest(path, algorithm):
    digest = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, path):
    """Download url to path."""
    with requests.get(url, stream=True, timeout=120) as reply:
        reply.raise_for_status()
        with open(path, "wb") as f:
            for chunk in reply.iter_content(chunk_size=1 << 20):
                f.write(chunk)


def published_md5(release, name):
    """The MD5 that GENCODE publishes for a file of the release, from its MD5SUMS file."""
    reply = requests.get(f"{BASE_URL.format(release=release)}/MD5SUMS", timeout=60)
    reply.raise_for_status()
    for line in reply.text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == name:
            return parts[0]
    raise ValueError(f"MD5SUMS of release {release} has no line for {name}")


def provenance(release, rows, header, csv_path, gtf_path, source_url, md5_published, script_version):
    """The facts about where the table came from."""
    named = sum(1 for row in rows if row["has_symbol"])
    md5 = file_digest(gtf_path, "md5")
    return {
        "gencode_release": release,
        "description": next((h for h in header if h.startswith("##description")), None),
        "source_url": source_url,
        "source_file": os.path.basename(gtf_path),
        "source_md5": md5,
        "source_md5_published": md5_published,
        "source_md5_verified": md5_published is not None and md5 == md5_published,
        "source_sha256": file_digest(gtf_path, "sha256"),
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "table_file": os.path.basename(csv_path),
        "table_sha256": file_digest(csv_path, "sha256"),
        "genes": len(rows),
        "genes_with_symbol": named,
        "genes_without_symbol": len(rows) - named,
        "cellxgene_schema_versions": sorted(v for v, r in GENCODE_BY_SCHEMA.items() if r == release),
        "cellxgene_schema_source": "https://github.com/chanzuckerberg/single-cell-curation/tree/main/schema",
        "script": f"cellxgene-harvester {script_version} build-gene-mapping",
    }


def table_names(release):
    return (f"gene_mapping_gencode_v{release}.csv", f"gene_mapping_gencode_v{release}.provenance.json")


def intact_table(release, output_dir):
    """The two paths of the table of this release if it is already in output_dir and is intact,
    else None. It is intact when its provenance file names this release and holds the SHA-256 of
    the table that is there."""
    csv_path, prov_path = (os.path.join(output_dir, name) for name in table_names(release))
    if not (os.path.exists(csv_path) and os.path.exists(prov_path)):
        return None
    info = json.load(open(prov_path, encoding="utf-8"))
    if info.get("gencode_release") != release or info.get("table_sha256") != file_digest(csv_path, "sha256"):
        return None
    return csv_path, prov_path


def build(release, output_dir, gtf=None, logger=None):
    """Build the table and the provenance file for one release. Return their two paths.

    gtf is a local annotation file to use instead of downloading it. Its MD5 cannot be
    checked against GENCODE then, and the provenance file says so.
    """
    from importlib.metadata import PackageNotFoundError, version
    try:
        script_version = version("cellxgene-harvester")
    except PackageNotFoundError:
        script_version = "unknown"

    existing = intact_table(release, output_dir)
    if existing:
        if logger:
            logger.info(f"The table of GENCODE v{release} is already in {output_dir} and is intact: it is not made again")
        return existing

    name = GTF_NAME.format(release=release)
    url = f"{BASE_URL.format(release=release)}/{name}"
    os.makedirs(output_dir, exist_ok=True)
    downloaded = None
    if gtf is None:
        downloaded = gtf = os.path.join(output_dir, name)
        if logger:
            logger.info(f"Downloading {url}")
        download(url, gtf)
        md5_published = published_md5(release, name)
    else:
        md5_published = None
        if logger:
            logger.info(f"Using the local file {gtf}; its MD5 cannot be checked against GENCODE")

    try:
        if md5_published is not None and file_digest(gtf, "md5") != md5_published:
            raise ValueError(f"{name}: the MD5 of the download does not match the one GENCODE publishes "
                             f"({md5_published}); the file was not used")
        rows, header = read_genes(gtf, release)
        if not rows:
            raise ValueError(f"{gtf}: no gene lines were found")
        csv_path = os.path.join(output_dir, f"gene_mapping_gencode_v{release}.csv")
        write_table(rows, csv_path)
        info = provenance(release, rows, header, csv_path, gtf, url if downloaded else None,
                          md5_published, script_version)
        prov_path = os.path.join(output_dir, f"gene_mapping_gencode_v{release}.provenance.json")
        with open(prov_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)
            f.write("\n")
    finally:
        if downloaded and os.path.exists(downloaded):
            os.remove(downloaded)
    if logger:
        logger.info(f"{info['genes']} genes, {info['genes_with_symbol']} with a symbol, "
                    f"{info['genes_without_symbol']} without")
        logger.info(f"Wrote {csv_path} and {prov_path}")
    return csv_path, prov_path


def run_build_gene_mapping(release=REQUIRED_GENCODE_RELEASE, output_dir=None, gtf=None):
    """Main entry point called by the CLI."""
    output_dir = output_dir or os.path.join(run_dir(), "gene_mapping")
    os.makedirs(output_dir, exist_ok=True)
    logger = setup_logger("build_gene_mapping", output_csv=os.path.join(output_dir, f"gene_mapping_gencode_v{release}.csv"))
    log_command(logger)
    try:
        build(release, output_dir, gtf, logger)
    except Exception as e:
        logger.error(f"ERROR: {e}")
        sys.exit(1)
    log_finish(logger)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gencode-release", type=int, default=REQUIRED_GENCODE_RELEASE)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--gtf", default=None)
    args = parser.parse_args()
    run_build_gene_mapping(args.gencode_release, args.output_dir, args.gtf)
