"""
Tests that nothing in the package can write a number with a thousands comma.

Run from the repository root:
    python -m pytest tests/test_no_thousands_formatting.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import glob
import os
import re

SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "harvester")


def sources():
    for path in sorted(glob.glob(os.path.join(SRC, "*.py"))):
        yield os.path.basename(path), open(path, encoding="utf-8").read()


def test_no_format_asks_for_a_thousands_separator():
    """Input: the source of every module. Pass: no f-string or format call has a
    format such as {n:,} or {n:>8,} (these write 11,464 instead of 11464)."""
    # a format spec is the part after ":" in a replacement field; "," in it asks for the separator
    pattern = re.compile(r":[<>^=+\-0-9#]*,[.0-9a-z%]*\}")
    offenders = [(name, m.group(0)) for name, text in sources() for m in pattern.finditer(text)]
    assert offenders == []


def test_csv_is_written_in_one_place_only():
    """Input: the source of every module. Pass: only io_utils.py calls to_csv or
    DictWriter, so the thousands-comma check covers every CSV the steps write."""
    pattern = re.compile(r"\.to_csv\(|DictWriter\(|csv\.writer\(")
    offenders = [name for name, text in sources() if name != "io_utils.py" and pattern.search(text)]
    assert offenders == []
