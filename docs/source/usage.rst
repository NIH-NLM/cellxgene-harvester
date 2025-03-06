Usage
=====

To run the pipeline:

.. code-block:: bash

   nextflow run workflow/main.nf -profile local

Available Execution Modes:
--------------------------

- **Local:** Runs on your local machine.
- **SLURM:** Runs on a SLURM-based cluster.
- **AWS Batch:** Runs on AWS cloud.

Results:
--------

The results will be stored in the `results/output.csv` file.
