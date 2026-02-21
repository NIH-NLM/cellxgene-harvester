"""
CloudOS client for dispatching Step 5 (count_normal_cells) to Lifebit CloudOS.

This module submits a Nextflow job to CloudOS and polls for completion.
Steps 0-4 and 6 run locally inside the MCP server process; only Step 5
is dispatched to CloudOS because of its memory requirements (CellxGene Census).

Prerequisites
-------------
Set these environment variables before starting the MCP server:

  CLOUDOS_API_KEY       CloudOS API key (Settings > API in CloudOS UI)
  CLOUDOS_WORKSPACE_ID  Workspace / team ID
  CLOUDOS_PROJECT_ID    Project ID where jobs will run
  CLOUDOS_WORKFLOW_ID   ID of the count_normal_cells Nextflow workflow in CloudOS

Optional:
  CLOUDOS_URL           CloudOS instance URL (default: https://cloudos.lifebit.ai)

The Nextflow workflow referenced by CLOUDOS_WORKFLOW_ID must already be
configured in CloudOS. It should scatter count_normal_cells_single.py across
datasets in the input CSV and collect results into a single output CSV.
See nextflow/count_normal_cells.nf for the workflow definition.

Install the client library:
  pip install cloudos-cli

NIH migration note
------------------
When moving to NIH NLM servers, replace the CloudOS job dispatch with NIH HPC
submission (e.g., SLURM via biowulf) or local execution on NIH-provisioned
high-memory nodes. The interface here stays the same; only the implementation
of submit_count_normal_cells() changes.
"""

import os
import sys
import time

CLOUDOS_URL_DEFAULT = "https://cloudos.lifebit.ai"
POLL_INTERVAL_SECONDS = 30
MAX_POLL_ATTEMPTS = 120  # polls for up to 60 minutes


def is_configured() -> bool:
    """Return True if all required CloudOS environment variables are set."""
    required = [
        "CLOUDOS_API_KEY",
        "CLOUDOS_WORKSPACE_ID",
        "CLOUDOS_PROJECT_ID",
        "CLOUDOS_WORKFLOW_ID",
    ]
    return all(os.environ.get(k) for k in required)


def _get_config() -> dict:
    return {
        "api_key": os.environ["CLOUDOS_API_KEY"],
        "url": os.environ.get("CLOUDOS_URL", CLOUDOS_URL_DEFAULT),
        "workspace_id": os.environ["CLOUDOS_WORKSPACE_ID"],
        "project_id": os.environ["CLOUDOS_PROJECT_ID"],
        "workflow_id": os.environ["CLOUDOS_WORKFLOW_ID"],
    }


def _get_cloudos_client(cfg: dict):
    """Instantiate the cloudos-cli Cloudos object. Raises ImportError if not installed."""
    try:
        from cloudos.utils.cloudos import Cloudos  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "cloudos-cli is required for CloudOS job dispatch. "
            "Install it with: pip install 'cellxgene-harvester[cloudos]'"
        ) from exc
    return Cloudos(cloudos_url=cfg["url"], apikey=cfg["api_key"], cromwell_token=None)


def submit_count_normal_cells(
    input_csv_path: str,
    uberon_json_path: str,
    min_age: int = 15,
    job_name: str = "count-normal-cells",
) -> str:
    """Submit a count_normal_cells Nextflow job to CloudOS.

    Parameters
    ----------
    input_csv_path:   Path (cloud storage URI or local path mounted by CloudOS)
                      to the filtered datasets CSV from Step 4.
    uberon_json_path: Path to the UBERON JSON produced by Step 0.
    min_age:          Minimum donor age for adult filtering (default 15).
    job_name:         Display name for the job in CloudOS.

    Returns
    -------
    str: The CloudOS job ID (used to poll status).

    Notes
    -----
    Input files must be accessible from the CloudOS compute environment.
    If they are local files, upload them to cloud storage (S3/GCS) first
    and pass the cloud URIs here.
    """
    cfg = _get_config()
    client = _get_cloudos_client(cfg)

    # cloudos-cli job submission API
    # See: https://github.com/lifebit-ai/cloudos-cli
    job_params = [
        {"name": "input_csv",   "value": input_csv_path},
        {"name": "uberon_json", "value": uberon_json_path},
        {"name": "min_age",     "value": str(min_age)},
    ]

    response = client.job_submit(
        workflow_id=cfg["workflow_id"],
        project_id=cfg["project_id"],
        workspace_id=cfg["workspace_id"],
        job_name=job_name,
        job_params=job_params,
    )

    job_id = response.get("_id") or response.get("id") or response.get("jobId")
    if not job_id:
        raise RuntimeError(f"CloudOS job submission did not return a job ID. Response: {response}")

    print(f"[CloudOS] Submitted job '{job_name}' → job_id={job_id}", file=sys.stderr)
    return job_id


def wait_for_completion(job_id: str) -> dict:
    """Poll CloudOS until the job reaches a terminal state.

    Parameters
    ----------
    job_id: The job ID returned by submit_count_normal_cells().

    Returns
    -------
    dict with at least:
      status:      "completed" | "failed" | "cancelled"
      output_path: cloud path to the output CSV (if completed successfully)

    Raises
    ------
    RuntimeError:  If the job fails or is cancelled.
    TimeoutError:  If the job does not finish within MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS.
    """
    cfg = _get_config()
    client = _get_cloudos_client(cfg)

    terminal_states = {"completed", "failed", "cancelled", "aborted"}

    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        status_info = client.get_job_status(
            job_id=job_id, workspace_id=cfg["workspace_id"]
        )
        status = (status_info.get("status") or "unknown").lower()

        print(
            f"[CloudOS] Job {job_id}: {status} (poll {attempt}/{MAX_POLL_ATTEMPTS})",
            file=sys.stderr,
        )

        if status in terminal_states:
            if status != "completed":
                raise RuntimeError(
                    f"CloudOS job {job_id} ended with status '{status}'. "
                    f"Check the CloudOS dashboard for logs."
                )
            return status_info

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"CloudOS job {job_id} did not complete within "
        f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS // 60} minutes."
    )


def run_via_cloudos(
    input_csv_path: str,
    uberon_json_path: str,
    min_age: int = 15,
    job_name: str = "count-normal-cells",
) -> dict:
    """Submit and wait for a count_normal_cells CloudOS job.

    Returns a dict with:
      job_id:      CloudOS job ID
      status:      "completed"
      output_path: path/URI of the output CSV (from CloudOS status response)
    """
    job_id = submit_count_normal_cells(
        input_csv_path=input_csv_path,
        uberon_json_path=uberon_json_path,
        min_age=min_age,
        job_name=job_name,
    )
    status_info = wait_for_completion(job_id)
    return {
        "job_id": job_id,
        "status": "completed",
        "output_path": status_info.get("outputPath") or status_info.get("output_path", ""),
        "cloudos_details": status_info,
    }
