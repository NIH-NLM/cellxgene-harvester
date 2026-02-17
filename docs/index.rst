cellxgene-harvester
===================

Harvest, filter, and count normal cells from the CellxGene Census using
UBERON ontology-based tissue filtering.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview
   installation
   usage
   pipeline
   api/modules

Overview
--------

cellxgene-harvester is a Nextflow pipeline that:

1. Resolves tissue labels to UBERON ontology terms
2. Fetches all public collections from CellxGene
3. Builds a master dataset catalog
4. Filters by ontology terms, organism, and quality criteria
5. Counts normal adult cells via CellxGene Census API
6. Produces a clean final dataset list for downstream analysis

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
