Pipeline
========

cellxgene-harvester is implemented as a Nextflow DSL2 pipeline with one module per step,
following the same modular pattern as `sc-nsforest-qc-nf`.

Each module in ``modules/harvester/`` can be included independently in downstream workflows::

    include { filter_datasets_process }    from './modules/harvester/filter_datasets.nf'
    include { count_normal_cells_process } from './modules/harvester/count_normal_cells.nf'

Modules
-------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Description
   * - ``resolve_uberon``
     - Resolves tissue labels to UBERON ontology terms via OLS4 API. Outputs JSON + CSV.
   * - ``fetch_collections``
     - Fetches all public collections from CellxGene API. Runs once, cached by Nextflow.
   * - ``generate_metadata``
     - Generates base metadata CSV from collections JSON.
   * - ``append_details``
     - Appends dataset titles, cell counts, h5ad URLs. Slow step (~10-20 min), cached.
   * - ``filter_datasets``
     - Filters by UBERON labels, organism, preprint, cancer, spatial criteria.
   * - ``count_normal_cells``
     - Counts normal adult cells via Census API. Scatters by dataset_id (parallel).
   * - ``final_cleanup``
     - Removes datasets with 0 normal cells.

Parallelism
-----------

Step 5 (``count_normal_cells``) scatters by ``dataset_id`` — one Nextflow process per
dataset runs in parallel. On Lifebit CloudOS this reduces wall time from ~40 minutes
sequential to ~5 minutes concurrent across 100+ datasets.

Profiles
--------

Run with ``-profile <name>``:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Profile
     - Description
   * - ``local``
     - Conda environment, no container. For development.
   * - ``docker``
     - Docker container from GHCR. Default for testing.
   * - ``singularity``
     - Singularity for HPC environments.
   * - ``lifebit``
     - Lifebit CloudOS on AWS with Kubernetes executor.
   * - ``test``
     - Small fast run for CI/CD regression testing.
