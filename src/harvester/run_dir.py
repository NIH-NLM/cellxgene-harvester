#!/usr/bin/env python3
"""
The folder that the steps 0a to 3 write their files to.

It is the current folder. To use another folder, give --run-dir to the command,
or set HARVESTER_RUN_DIR.

Usage:
    from harvester.run_dir import run_dir

    path = os.path.join(run_dir(), "collections_metadata.json")
"""

import os

ENV_NAME = "HARVESTER_RUN_DIR"


def run_dir():
    """The folder for the files: HARVESTER_RUN_DIR if it is set, else the current folder."""
    return os.environ.get(ENV_NAME) or "."
