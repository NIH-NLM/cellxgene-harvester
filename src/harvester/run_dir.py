#!/usr/bin/env python3
"""
The folder that holds the files of one run.

Each run of the pipeline has its own folder, named by the date it was started,
for example 2026-08-03-run. The folder is made in the current directory.

To use another folder, give --run-dir to the command, or set HARVESTER_RUN_DIR.

Usage:
    from harvester.run_dir import run_dir

    path = os.path.join(run_dir(), "collections_metadata.json")
"""

import os
from datetime import date

ENV_NAME = "HARVESTER_RUN_DIR"


def run_dir():
    """The run folder: HARVESTER_RUN_DIR if it is set, else <today>-run."""
    return os.environ.get(ENV_NAME) or f"{date.today().isoformat()}-run"
