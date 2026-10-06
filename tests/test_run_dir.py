"""
Tests for the run folder, harvester.run_dir, and for the rule that no step
writes to a folder called data.

Run from the repository root:
    python -m pytest tests/test_run_dir.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import glob
import os
import re
from datetime import date

from typer.testing import CliRunner

from harvester import run_dir as run_dir_module
from harvester.cli import app
from harvester.logger import setup_logger
from harvester.run_dir import ENV_NAME, run_dir

SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "harvester")


def test_default_run_folder_is_today_with_run_on_the_end(monkeypatch):
    """Input: HARVESTER_RUN_DIR not set. Pass: <today>-run, for example 2026-08-03-run."""
    monkeypatch.delenv(ENV_NAME, raising=False)
    assert run_dir() == f"{date.today().isoformat()}-run"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}-run", run_dir())


def test_environment_variable_sets_the_run_folder(monkeypatch):
    """Input: HARVESTER_RUN_DIR=2026-08-03-run. Pass: run_dir gives that name."""
    monkeypatch.setenv(ENV_NAME, "2026-08-03-run")
    assert run_dir() == "2026-08-03-run"


def test_run_dir_option_sets_the_run_folder(monkeypatch, tmp_path):
    """Input: the command line --run-dir X before a command. Pass: while the command
    runs, run_dir() gives X."""
    monkeypatch.delenv(ENV_NAME, raising=False)
    seen = []
    monkeypatch.setattr("harvester.final_cleanup.run_final_cleanup",
                        lambda folder: seen.append(run_dir()))
    result = CliRunner().invoke(app, ["--run-dir", "2026-08-03-run", "final-cleanup", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert seen == ["2026-08-03-run"]
    monkeypatch.delenv(ENV_NAME, raising=False)


def test_log_without_an_output_file_goes_in_the_run_folder(monkeypatch, tmp_path):
    """Input: a logger made with no output file and the run folder set. Pass: the
    log file is in <run folder>/logs."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(ENV_NAME, "2026-08-03-run")
    setup_logger("probe")
    assert glob.glob(str(tmp_path / "2026-08-03-run" / "logs" / "probe_*.log"))


def test_no_module_names_a_data_folder():
    """Input: the source of every module except the MCP server. Pass: none of them
    sets DATA_DIR or builds a path in a folder called data."""
    offenders = []
    for path in sorted(glob.glob(os.path.join(SRC, "*.py"))):
        text = open(path, encoding="utf-8").read()
        if re.search(r"DATA_DIR|[\"\']data[\"\']|[\s(=\"\']data/", text):
            offenders.append(os.path.basename(path))
    assert offenders == []
