#!/usr/bin/env python3
"""
Step 6: Final cleanup - Remove datasets with no cells after filtering

Reads the folder of <dataset_id>.filtered.json files from Step 5 and deletes
the file of every dataset whose filtered_cell_count is 0.

A file whose filtered_cell_count is empty (null) was never counted, or its
Census query failed. It is NOT deleted. It is listed in the log, so it can be
counted again with Step 5.

Every deleted dataset id is written to the log.

Usage:
1. Python module execution:
python -m harvester.final_cleanup 2026-08-03-run/homo_sapiens_kidney_harvester

2. CLI command (after pip install -e .):
cellxgene-harvester final-cleanup 2026-08-03-run/homo_sapiens_kidney_harvester
"""

import glob
import os
import sys

from harvester.io_utils import load_json
from harvester.logger import setup_logger, log_command, log_counts, log_finish


def list_files(folder):
    return sorted(glob.glob(os.path.join(folder, "*.filtered.json")))


def sort_by_count(paths):
    """Return (empty, uncounted): files with a count of 0, and files with no count."""
    empty, uncounted = [], []
    for path in paths:
        count = load_json(path)["filtered_cell_count"]
        if count is None:
            uncounted.append(path)
        elif count == 0:
            empty.append(path)
    return empty, uncounted


def delete_files(paths):
    for path in paths:
        os.remove(path)


def cleanup_folder(folder, logger):
    """Delete the files with a count of 0. Return the number deleted."""
    paths = list_files(folder)
    empty, uncounted = sort_by_count(paths)

    delete_files(empty)
    log_counts(logger, "datasets with 0 filtered cells",
               before=len(paths), after=len(paths) - len(empty))

    for path in empty:
        logger.info(f"  Deleted : {os.path.basename(path)}")
    for path in uncounted:
        logger.warning(f"  NOT COUNTED, kept : {os.path.basename(path)}")
    return len(empty)


# =============================================================================
# run_final_cleanup
# =============================================================================
def run_final_cleanup(folder: str):
    """Main entry point called by CLI"""
    folder = folder.rstrip("/")
    if not os.path.isdir(folder):
        print(f"ERROR: folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    logger = setup_logger("6_final_cleanup", output_csv=f"{folder}.cleanup.log")
    log_command(logger)
    cleanup_folder(folder, logger)
    log_finish(logger, folder)
