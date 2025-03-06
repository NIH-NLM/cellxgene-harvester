# scRNAseq Silhouette Score

This Nextflow pipeline retrieves scRNA-seq datasets from **CellxGene**, computes **cosine silhouette scores**, and outputs the results as a CSV file.

# Setting Up the Environment

## Install Conda

Ensure you have Conda installed. If not, install **Miniconda**:
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

## Creating the environment

All the scripts dependencies are in the **`environment.yml`** file
A fresh environment is created.

```bash
conda env create -f environment.yml
conda activate scrnaseq_silhouette
```


## Running the Nextflow Workflow

To execute locally:
```bash
nextflow run workflow/main.nf -profile local
```

## Directory Structure

scRNAseq_silhouette_score/
│── bin/                           # Executable scripts
│   ├── fetch_cellxgene.py         # Fetch datasets from CellxGene
│   ├── compute_silhouette.py      # Compute silhouette scores
│
│── conf/                          
│   ├── slurm.config               # SLURM executor config
│   ├── aws.config                 # AWS Batch config
│
│── workflow/
│   ├── main.nf                    # Main Nextflow script
│   ├── pull_cellxgene.nf          # Fetch datasets
│   ├── compute_silhouette.nf      # Compute silhouette scores
│   ├── merge_results.nf           # Merge results
│
│── results/                        # Output directory
│   ├── logs/                       # Execution logs
│   ├── reports/                    # Reports, Timeline, DAG
│   ├── output.csv                   # Final output file
│
│── docs/                           # Sphinx Documentation
│   ├── source/
│   │   ├── conf.py                  # Sphinx Configuration
│   │   ├── index.rst                # Main Documentation Index
│   │   ├── usage.rst                # How to Use the Pipeline
│   │   ├── modules.rst              # Python Module Docs
│   │   ├── nextflow_docs.rst        # Nextflow Documentation
│   ├── build/                        # Generated HTML Files
│   └── Makefile                      # Build documentation
│
│── notebooks/                       # Jupyter Notebooks
│   ├── analyze_silhouette_scores.ipynb  # Notebook for additional analysis
│
│── README.md                        # Project Overview
│── nextflow.config                   # Main pipeline config
│── run.sh                            # Execution script
│── environment.yml                    # Conda environment file
│── setup.py                           # Sphinx setup
│── sphinx_build.sh                    # Script to generate Sphinx docs


## AWS Batch Configuration Parameters

| Parameter            | Value                         | Description |
|----------------------|-----------------------------|-------------|
| **executor**        | `awsbatch`                   | Enables execution on **AWS Batch**. |
| **queue**           | `nextflow-job-queue`         | Specifies the AWS Batch job queue. |
| **memory**          | `32GB`                        | Allocates **32GB RAM** per job. |
| **cpus**            | `8`                          | Allocates **8 vCPUs** per job. |
| **time**            | `12h`                        | Limits job runtime to **12 hours**. |
| **batch.queue**     | `nextflow-job-queue`         | Defines the **AWS Batch job queue**. |
| **batch.compute_env** | `nextflow-compute-env`     | AWS Batch **Compute Environment**. |
| **batch.job_role**  | `arn:aws:iam::123456789012:role/NextflowBatchJobRole` | IAM role for job execution. |
| **batch.job_definition** | `nextflow-job-definition` | AWS Batch **Job Definition**. |
| **wave.enabled**    | `true`                        | Enables **Wave container support** for efficiency. |
| **pollInterval**    | `30 sec`                      | Nextflow checks AWS Batch job status **every 30 seconds**. |
