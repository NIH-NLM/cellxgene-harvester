import os
import sys

# src/ layout: conf.py lives at docs/source/conf.py → package is at ../../src
sys.path.insert(0, os.path.abspath('../../src'))

project   = 'cellxgene-harvester'
copyright = '2026, NIH-NLM'
author    = 'Anne Deslattes Mays'
release   = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_autodoc_typehints',
    'myst_parser',
]

# ---------------------------------------------------------------------------
# autodoc_mock_imports — CRITICAL
#
# Sphinx autodoc imports every module to extract docstrings.  Any package
# listed here is replaced with a Mock object instead of being imported.
#
# cellxgene_census and tiledbsoma MUST be mocked: importing them triggers
# a network request and prints a "stable release" banner, which stalls the
# build.  check_census_schema.py also calls open_soma() at module level;
# mocking cellxgene_census prevents that call from ever executing.
#
# All other scientific / CLI packages must also be mocked because they are
# not installed in the lightweight docs environment.
# ---------------------------------------------------------------------------
autodoc_mock_imports = [
    # Census / TileDB — network I/O on import; MUST be first
    'cellxgene_census',
    'tiledbsoma',
    # Scientific stack
    'numpy',
    'pandas',
    'anndata',
    'scanpy',
    'sklearn',
    'scipy',
    'plotly',
    'kaleido',
    # CLI / formatting
    'typer',
    'click',
    'rich',
    # HTTP
    'requests',
    # Gene utilities
    'mygene',
]

autodoc_member_order      = 'bysource'
autodoc_typehints         = 'description'

templates_path   = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme       = 'sphinx_rtd_theme'
html_static_path = ['_static']

napoleon_google_docstring = True
napoleon_numpy_docstring  = False
