"""
MCP server for cellxgene-harvester.

Exposes each pipeline step as an MCP tool so AI agents (Claude Code,
Claude Desktop, etc.) can orchestrate the full pipeline through natural language.

Steps 0-4 and 6 run in-process (lightweight API calls).
Step 5 (count_normal_cells) dispatches to Lifebit CloudOS when
CLOUDOS_API_KEY and related env vars are configured; otherwise it
runs locally (useful for development and small datasets).

Usage
-----
Start the server (stdio transport for Claude Code / Claude Desktop):

    cellxgene-harvester-mcp

Configure in ~/.claude.json (Claude Code):

    {
      "mcpServers": {
        "cellxgene-harvester": {
          "command": "cellxgene-harvester-mcp",
          "env": {
            "CLOUDOS_API_KEY": "<your-key>",
            "CLOUDOS_WORKSPACE_ID": "<workspace-id>",
            "CLOUDOS_PROJECT_ID": "<project-id>",
            "CLOUDOS_WORKFLOW_ID": "<nextflow-workflow-id>"
          }
        }
      }
    }

NIH migration note
------------------
To deploy as a remote HTTP/SSE server on NIH NLM infrastructure, change
the main() call to:

    mcp.run(transport="sse", host="0.0.0.0", port=8000)

All tool logic stays the same; only the transport layer changes.
"""

import io
import os
import re
import sys
from contextlib import redirect_stdout
from typing import Optional

from fastmcp import FastMCP

mcp = FastMCP(
    "cellxgene-harvester",
    instructions=(
        "Pipeline for harvesting normal cells from CellxGene Census. "
        "Run steps in order: resolve_uberon → fetch_collections → "
        "generate_metadata → append_dataset_details → filter_datasets → "
        "count_normal_cells → final_cleanup. "
        "Each tool returns the output file path(s) to pass into the next step."
    ),
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run(func, *args, **kwargs):
    """Call a harvester run_*() function, routing its stdout to stderr.

    The MCP stdio protocol uses stdout; any print() calls from harvester
    functions would corrupt the protocol. This helper captures stdout and
    re-emits it on stderr so it appears in server logs without affecting
    the MCP channel.
    """
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = func(*args, **kwargs)
    output = buf.getvalue()
    if output:
        print(output, file=sys.stderr, end="")
    return result


def _uberon_prefix(queries: list[str], output_prefix: Optional[str]) -> str:
    """Replicate resolve_uberon.py's prefix logic so the tool can return paths."""
    if output_prefix:
        return output_prefix
    slug = re.sub(r"[^a-z0-9]+", "_", queries[0].lower()).strip("_")
    return os.path.join("data", f"uberon_{slug}")


# ---------------------------------------------------------------------------
# Step 0 — Resolve UBERON terms
# ---------------------------------------------------------------------------

@mcp.tool
def resolve_uberon(
    queries: list[str],
    output_prefix: Optional[str] = None,
    multi: bool = False,
) -> dict:
    """Step 0: Resolve tissue labels or UBERON IDs to descendant ontology terms.

    Queries the OLS4 API to find all hierarchical descendants of each term,
    then writes JSON and CSV files for use in filter_datasets and count_normal_cells.

    Parameters
    ----------
    queries:       One or more tissue labels (e.g. ["kidney"]) or UBERON IDs
                   (e.g. ["UBERON:0002113"]).
    output_prefix: File path prefix for output files (without extension).
                   Defaults to data/uberon_<tissue>.
    multi:         If True, combine all queries into a single output file.

    Returns
    -------
    json_file: Path to the UBERON JSON (pass to filter_datasets and count_normal_cells).
    csv_file:  Path to the flat ontology CSV.
    """
    from harvester.resolve_uberon import run_resolve_uberon  # noqa: PLC0415

    _run(run_resolve_uberon, queries, output_prefix, multi)

    prefix = _uberon_prefix(queries, output_prefix)
    return {
        "json_file": f"{prefix}.json",
        "csv_file": f"{prefix}.csv",
    }


# ---------------------------------------------------------------------------
# Step 1 — Fetch collections
# ---------------------------------------------------------------------------

@mcp.tool
def fetch_collections() -> dict:
    """Step 1: Fetch all public collections from the CellxGene API.

    Downloads collection metadata (IDs, names, associated datasets) and
    saves it locally. No arguments required.

    Returns
    -------
    output_file: Path to the saved collections JSON.
    """
    from harvester.fetch_collections import run_fetch_collections  # noqa: PLC0415

    _run(run_fetch_collections)
    return {"output_file": "data/collections_metadata.json"}


# ---------------------------------------------------------------------------
# Step 2 — Generate metadata CSV
# ---------------------------------------------------------------------------

@mcp.tool
def generate_metadata() -> dict:
    """Step 2: Parse the collections JSON and generate a base metadata CSV.

    Reads data/collections_metadata.json (from fetch_collections), selects
    the latest version of each dataset, and writes a CSV with ~40 metadata
    fields including publication info, tissue, assay, and ontology columns.

    Returns
    -------
    output_file: Path to the generated metadata CSV.
    """
    from harvester.generate_metadata import run_generate_metadata  # noqa: PLC0415

    _run(run_generate_metadata)
    return {"output_file": "data/all_datasets.csv"}


# ---------------------------------------------------------------------------
# Step 3 — Append dataset details
# ---------------------------------------------------------------------------

@mcp.tool
def append_dataset_details() -> dict:
    """Step 3: Enrich the metadata CSV with per-dataset details from the CellxGene API.

    For each dataset in data/all_datasets.csv, fetches: title, total cell
    count, H5AD download URL, and Explorer URL. Rate-limited to be polite
    to the CellxGene API (0.2 s between requests).

    Returns
    -------
    output_file: Path to the enriched CSV.
    """
    from harvester.append_dataset_details import run_append_details  # noqa: PLC0415

    _run(run_append_details)
    return {"output_file": "data/all_datasets_complete.csv"}


# ---------------------------------------------------------------------------
# Step 4 — Filter datasets
# ---------------------------------------------------------------------------

@mcp.tool
def filter_datasets(
    output_csv: str,
    input_csv: str = "data/all_datasets_complete.csv",
    uberon_json: Optional[str] = None,
    organism: Optional[str] = None,
    no_preprints: bool = False,
    exclude_cancer: bool = False,
    exclude_spatial: bool = False,
    disease: Optional[str] = None,
) -> dict:
    """Step 4: Filter datasets by tissue, organism, and study type.

    Parameters
    ----------
    output_csv:      Path for the filtered output CSV (required).
    input_csv:       Input CSV (default: data/all_datasets_complete.csv).
    uberon_json:     UBERON JSON from resolve_uberon — restricts to datasets
                     whose tissue column matches any term label in the file.
    organism:        Filter by organism string (e.g. "Homo sapiens").
    no_preprints:    If True, exclude preprint-only datasets.
    exclude_cancer:  If True, exclude datasets with cancer/carcinoma disease.
    exclude_spatial: If True, exclude spatial transcriptomics datasets
                     (Visium, MERFISH, Xenium, etc.).
    disease:         Keep only datasets whose disease column contains this
                     substring (case-insensitive).

    Returns
    -------
    output_file:    Path to the filtered CSV.
    """
    from harvester.filter_datasets import run_filter_datasets  # noqa: PLC0415

    _run(
        run_filter_datasets,
        input_csv=input_csv,
        output_csv=output_csv,
        uberon_json=uberon_json,
        organism=organism,
        no_preprints=no_preprints,
        exclude_cancer=exclude_cancer,
        exclude_spatial=exclude_spatial,
        disease=disease,
    )
    return {"output_file": output_csv}


# ---------------------------------------------------------------------------
# Step 5 — Count normal cells
# ---------------------------------------------------------------------------

@mcp.tool
def count_normal_cells(
    input_csv: str,
    uberon_json: str,
    min_age: int = 15,
) -> dict:
    """Step 5: Count normal (non-diseased, adult, primary) cells via CellxGene Census.

    For each dataset in input_csv, queries CellxGene Census for cells that:
      - Are from the specified UBERON tissues
      - Have disease == 'normal'
      - Have is_primary_data == True
      - Are from donors aged >= min_age (fetal/embryo stages excluded)

    Execution
    ---------
    If CloudOS environment variables are configured (CLOUDOS_API_KEY,
    CLOUDOS_WORKSPACE_ID, CLOUDOS_PROJECT_ID, CLOUDOS_WORKFLOW_ID), the
    job is submitted to Lifebit CloudOS as a Nextflow workflow and this
    tool blocks until it completes.

    If CloudOS is not configured, the step runs locally. This works for
    development and small datasets but requires sufficient local memory
    for CellxGene Census access.

    Parameters
    ----------
    input_csv:   Filtered datasets CSV from filter_datasets.
    uberon_json: UBERON JSON from resolve_uberon.
    min_age:     Minimum donor age for adult filtering (default 15).

    Returns
    -------
    output_file:  Path to the output CSV with a normal_cell_count column added.
    execution:    "cloudos" or "local" — where the step ran.
    job_id:       CloudOS job ID (only present when execution == "cloudos").
    """
    from harvester.mcp import cloudos_client  # noqa: PLC0415

    base = os.path.splitext(input_csv)[0]
    output_csv = f"{base}_with_normal_counts.csv"

    if cloudos_client.is_configured():
        result = cloudos_client.run_via_cloudos(
            input_csv_path=input_csv,
            uberon_json_path=uberon_json,
            min_age=min_age,
        )
        return {
            "output_file": result.get("output_path") or output_csv,
            "execution": "cloudos",
            "job_id": result["job_id"],
        }

    # Local fallback
    print(
        "[cellxgene-harvester-mcp] CloudOS not configured — running count_normal_cells locally. "
        "Set CLOUDOS_API_KEY and related env vars to dispatch to CloudOS.",
        file=sys.stderr,
    )
    from harvester.count_normal_cells import run_count_normal_cells  # noqa: PLC0415

    _run(run_count_normal_cells, input_csv=input_csv, uberon_json=uberon_json, min_age=min_age)
    return {
        "output_file": output_csv,
        "execution": "local",
    }


# ---------------------------------------------------------------------------
# Step 6 — Final cleanup
# ---------------------------------------------------------------------------

@mcp.tool
def final_cleanup(input_csv: str) -> dict:
    """Step 6: Remove datasets with zero normal cells.

    Reads input_csv and drops any row where normal_cell_count is 0, blank,
    or non-numeric. Writes the cleaned result alongside the input file.

    Parameters
    ----------
    input_csv: CSV with normal_cell_count column (output from count_normal_cells).

    Returns
    -------
    output_file:     Path to the final cleaned CSV.
    """
    from harvester.final_cleanup import run_final_cleanup  # noqa: PLC0415

    _run(run_final_cleanup, input_csv)

    base = os.path.splitext(input_csv)[0]
    if base.endswith("_with_normal_counts"):
        base = base.replace("_with_normal_counts", "")
    return {"output_file": f"{base}_final.csv"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Start the MCP server.

    Runs in stdio mode by default (for Claude Code / Claude Desktop).
    To switch to HTTP/SSE for remote deployment, change to:
        mcp.run(transport="sse", host="0.0.0.0", port=8000)
    """
    mcp.run()


if __name__ == "__main__":
    main()
