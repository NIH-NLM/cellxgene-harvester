import os
import sys

# Point to the bin/ scripts for autodoc
sys.path.insert(0, os.path.abspath('../../bin'))

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

templates_path   = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme        = 'sphinx_rtd_theme'
html_static_path  = ['_static']

autodoc_member_order      = 'bysource'
autodoc_typehints         = 'description'
napoleon_google_docstring = True
napoleon_numpy_docstring  = False
