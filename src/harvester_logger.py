#!/usr/bin/env python3
"""
Shared logging utility for CellxGene Harvester pipeline.

Provides consistent logging across all pipeline steps:
- Command call capture
- Timestamps
- Before/after counts at every filtering step
- Log file alongside output CSV

Usage:
    from harvester_logger import setup_logger, log_command, log_counts

    logger = setup_logger("step_4_filter", output_csv="data/filtered.csv")
    log_command(logger)
    log_counts(logger, "organism filter", before=1000, after=800)
"""

import os
import sys
import logging
from datetime import datetime


def setup_logger(step_name: str, output_csv: str = None, log_dir: str = "data/logs") -> logging.Logger:
    """
    Set up a logger that writes to both console and a log file.

    Log file location:
    - If output_csv is provided: alongside the CSV as <output_csv>.log
    - Otherwise: data/logs/<step_name>_<timestamp>.log

    Args:
        step_name:  Short name for the step, e.g. "step_4_filter"
        output_csv: Path to the output CSV for this step (optional)
        log_dir:    Fallback directory for log files

    Returns:
        Configured logger
    """
    # Determine log file path
    if output_csv:
        log_file = os.path.splitext(output_csv)[0] + ".log"
    else:
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{step_name}_{timestamp}.log")

    # Create logger (use unique name to avoid duplicate handlers on re-import)
    logger_name = f"harvester.{step_name}.{os.getpid()}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers = []

    formatter = logging.Formatter("%(message)s")

    # File handler - captures everything
    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    # Console handler - INFO and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 70)
    logger.info(f"CellxGene Harvester - {step_name.replace('_', ' ').title()}")
    logger.info("=" * 70)
    logger.info(f"Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log file: {log_file}")

    return logger


def log_command(logger: logging.Logger) -> None:
    """
    Log the exact command used to invoke this script.

    Call at the top of __main__ before any processing.
    """
    cmd = " ".join(sys.argv)
    logger.info(f"Command : python {cmd}")
    logger.info("")


def log_counts(logger: logging.Logger, filter_name: str, before: int, after: int,
               unit: str = "datasets") -> None:
    """
    Log before/after counts for any filtering step.

    Args:
        logger:      Logger instance
        filter_name: Human-readable name for the filter (e.g. "organism filter")
        before:      Count before filtering
        after:       Count after filtering
        unit:        What is being counted (default: "datasets")
    """
    removed = before - after
    pct = (removed / before * 100) if before > 0 else 0
    logger.info(f"  [{filter_name}]")
    logger.info(f"    Before : {before:>8,} {unit}")
    logger.info(f"    After  : {after:>8,} {unit}")
    logger.info(f"    Removed: {removed:>8,} {unit}  ({pct:.1f}%)")


def log_finish(logger: logging.Logger, output_csv: str = None) -> None:
    """
    Log completion timestamp and output path.

    Call at the very end of each script.
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if output_csv:
        logger.info(f"Output  : {output_csv}")
    logger.info("=" * 70)
