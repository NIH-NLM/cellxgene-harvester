Installation
============

Requirements
------------

- Python 3.11
- conda / mamba
- Nextflow >= 23.04
- Docker or Singularity (for containerized runs)

From source
-----------

.. code-block:: bash

    git clone https://github.com/NIH-NLM/cellxgene-harvester
    cd cellxgene-harvester
    mamba env create -f environment.yml
    mamba activate cellxgene

Docker
------

The container is published to GitHub Container Registry::

    docker pull ghcr.io/nih-nlm/cellxgene-harvester:latest

Build locally::

    docker build -t ghcr.io/nih-nlm/cellxgene-harvester:1.0.0 .
