import os
import sys
sys.path.insert(0, os.path.abspath('../../bin'))

# Project Information
project = 'scRNAseq Silhouette Score'
authors = 'Ajith Viswanathan, Ph.D.,
           Anne Deslattes Mays, Ph.D.'
release = '1.0'

# Sphinx Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosummary',
    'sphinx.ext.githubpages'
]

# Theme
html_theme = "sphinx_rtd_theme"
