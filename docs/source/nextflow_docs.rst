Nextflow Pipeline
=================

This pipeline automates the fetching of datasets from **CellxGene**, computes **cosine silhouette scores**, and generates output CSVs.

Pipeline Processes:
-------------------

1. **pull_cellxgene.nf** - Fetches dataset metadata.
2. **compute_silhouette.nf** - Computes silhouette scores for each dataset.
3. **merge_results.nf** - Merges all results into a CSV.

Pipeline Execution:
-------------------

.. code-block:: bash

   nextflow run workflow/main.nf -profile local
