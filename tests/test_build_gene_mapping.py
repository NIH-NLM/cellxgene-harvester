"""
Tests for build-gene-mapping.

A tiny GENCODE-style annotation is written here, so nothing is downloaded. The download
and the MD5 check are tested with the network calls replaced.
"""

import csv
import gzip
import hashlib
import json

import pytest
from typer.testing import CliRunner

from harvester import build_gene_mapping as step
from harvester.cli import app

HEADER = [
    "##description: evidence-based annotation of the human genome (GRCh38), version 48 (Ensembl 114)",
    "##provider: GENCODE",
]


def gtf_line(feature, attributes, chrom="chr1"):
    return "\t".join([chrom, "HAVANA", feature, "1", "100", ".", "+", ".", attributes])


GENES = [
    gtf_line("gene", 'gene_id "ENSG00000223972.6"; gene_type "transcribed_unprocessed_pseudogene"; '
                     'gene_name "DDX11L1"; level 2; hgnc_id "HGNC:37102";'),
    gtf_line("transcript", 'gene_id "ENSG00000223972.6"; transcript_id "ENST00000456328.2"; '
                           'gene_name "DDX11L1";'),
    gtf_line("exon", 'gene_id "ENSG00000223972.6"; transcript_id "ENST00000456328.2";'),
    gtf_line("gene", 'gene_id "ENSG00000254180.1"; gene_type "lncRNA"; gene_name "ENSG00000254180";'),
    gtf_line("gene", 'gene_id "ENSG00000000003.16"; gene_type "protein_coding"; gene_name "TSPAN6"; '
                     'hgnc_id "HGNC:11858";'),
    gtf_line("gene", 'gene_id "ENSG00000182378.14_PAR_Y"; gene_type "protein_coding"; gene_name "PLCXD1";',
             chrom="chrY"),
    gtf_line("gene", 'gene_id "ENSG00000290825.2"; gene_type "lncRNA";'),
]


def write_gtf(path, lines=None):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write("\n".join(HEADER + (GENES if lines is None else lines)) + "\n")
    return str(path)


def read_table(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_the_version_suffix_goes_and_other_suffixes_stay():
    assert step.strip_version("ENSG00000223972.6") == "ENSG00000223972"
    assert step.strip_version("ENSG00000182378.14_PAR_Y") == "ENSG00000182378_PAR_Y"
    assert step.strip_version("ENSG00000223972") == "ENSG00000223972"


def test_only_gene_lines_are_read():
    assert step.parse_gene_line(GENES[1]) is None and step.parse_gene_line(GENES[2]) is None
    assert step.parse_gene_line("##description: x") is None
    assert step.parse_gene_line(GENES[0])["gene_name"] == "DDX11L1"


def test_the_table_has_one_sorted_row_for_each_gene_and_marks_genes_without_a_name(tmp_path):
    gtf = write_gtf(tmp_path / "a.gtf.gz")
    csv_path, _ = step.build(48, str(tmp_path / "out"), gtf)
    rows = read_table(csv_path)
    assert [r["ensembl_gene_id"] for r in rows] == sorted(r["ensembl_gene_id"] for r in rows)
    by_id = {r["ensembl_gene_id"]: r for r in rows}
    assert len(rows) == 5
    assert by_id["ENSG00000223972"] == {
        "ensembl_gene_id": "ENSG00000223972", "gene_name": "DDX11L1",
        "gene_type": "transcribed_unprocessed_pseudogene", "hgnc_id": "HGNC:37102",
        "has_symbol": "True", "gencode_release": "48"}
    assert by_id["ENSG00000254180"]["has_symbol"] == "False"      # the name is the id
    assert by_id["ENSG00000290825"]["gene_name"] == "ENSG00000290825"   # no gene_name at all
    assert by_id["ENSG00000290825"]["has_symbol"] == "False" and by_id["ENSG00000290825"]["hgnc_id"] == ""
    assert "ENSG00000182378_PAR_Y" in by_id


def test_the_same_input_gives_the_same_bytes(tmp_path):
    gtf = write_gtf(tmp_path / "a.gtf.gz")
    first, _ = step.build(48, str(tmp_path / "one"), gtf)
    second, _ = step.build(48, str(tmp_path / "two"), gtf)
    assert open(first, "rb").read() == open(second, "rb").read()


def test_the_row_order_does_not_depend_on_the_order_of_the_annotation(tmp_path):
    forward = write_gtf(tmp_path / "f.gtf.gz")
    backward = write_gtf(tmp_path / "b.gtf.gz", list(reversed(GENES)))
    a, _ = step.build(48, str(tmp_path / "one"), forward)
    b, _ = step.build(48, str(tmp_path / "two"), backward)
    assert open(a, "rb").read() == open(b, "rb").read()


def test_the_provenance_file_says_where_the_table_came_from(tmp_path):
    gtf = write_gtf(tmp_path / "a.gtf.gz")
    csv_path, prov_path = step.build(48, str(tmp_path / "out"), gtf)
    info = json.load(open(prov_path))
    assert info["gencode_release"] == 48 and info["genes"] == 5
    assert info["genes_with_symbol"] == 3 and info["genes_without_symbol"] == 2
    assert info["description"].endswith("version 48 (Ensembl 114)")
    assert info["source_sha256"] == hashlib.sha256(open(gtf, "rb").read()).hexdigest()
    assert info["table_sha256"] == hashlib.sha256(open(csv_path, "rb").read()).hexdigest()
    assert info["cellxgene_schema_versions"] == ["7.0.0", "7.1.0"]
    assert info["source_md5_verified"] is False and info["source_md5_published"] is None
    assert info["built_at"].endswith("+00:00")


def test_a_download_is_checked_against_the_published_md5_and_deleted(tmp_path, monkeypatch):
    source = write_gtf(tmp_path / "source.gtf.gz")
    md5 = hashlib.md5(open(source, "rb").read()).hexdigest()
    monkeypatch.setattr(step, "download", lambda url, path: open(path, "wb").write(open(source, "rb").read()))
    monkeypatch.setattr(step, "published_md5", lambda release, name: md5)
    out = tmp_path / "out"
    _, prov_path = step.build(48, str(out))
    info = json.load(open(prov_path))
    assert info["source_md5_verified"] is True
    assert info["source_url"].endswith("release_48/gencode.v48.primary_assembly.annotation.gtf.gz")
    assert not (out / "gencode.v48.primary_assembly.annotation.gtf.gz").exists()


def test_a_download_with_the_wrong_md5_is_refused_and_no_table_is_written(tmp_path, monkeypatch):
    source = write_gtf(tmp_path / "source.gtf.gz")
    monkeypatch.setattr(step, "download", lambda url, path: open(path, "wb").write(open(source, "rb").read()))
    monkeypatch.setattr(step, "published_md5", lambda release, name: "0" * 32)
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="does not match"):
        step.build(48, str(out))
    assert not list(out.glob("gene_mapping_*"))
    assert not list(out.glob("*.gtf.gz"))


def test_an_annotation_without_genes_is_refused(tmp_path):
    gtf = write_gtf(tmp_path / "a.gtf.gz", [GENES[1]])
    with pytest.raises(ValueError, match="no gene lines"):
        step.build(48, str(tmp_path / "out"), gtf)


def test_the_command_builds_the_files_from_a_local_annotation(tmp_path):
    gtf = write_gtf(tmp_path / "a.gtf.gz")
    out = tmp_path / "out"
    result = CliRunner().invoke(app, ["build-gene-mapping", "--gencode-release", "48",
                                      "--output-dir", str(out), "--gtf", gtf])
    assert result.exit_code == 0, result.output
    assert (out / "gene_mapping_gencode_v48.csv").exists()
    assert (out / "gene_mapping_gencode_v48.provenance.json").exists()
