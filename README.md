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
## Silhouette Score Calculation

### Evaluating clustering results
One metric for evaluating clustering results, which is provided by the scikit-learn API, is the silhouette_score.

The definition of the silhouette_score is 
 
. The score can take on values between -1 and 1, with -1 being the worst, and +1 being the best scores. 0 indicates overlapping clusters.

From the scikit-learn API documentation:

```
The Silhouette Coefficient is calculated using the mean intra-cluster distance a and the mean nearest-cluster distance b for each sample. The Silhouette Coefficient for a sample is (b - a) / max(a, b). To clarify, b is the distance between a sample and the nearest cluster that the sample is not a part of. Note that Silhouette Coefficent is only defined if number of labels is 2 <= n_labels <= n_samples - 1.
```



## Directory Structure

```bash
├── LICENSE
├── README.md
├── bin
│   ├── compute_silhouette.py
│   └── fetch_cellxgene.py
├── conf
│   ├── aws.config
│   └── slurm.config
├── directory.md
├── docs
│   ├── build
│   └── source
│       ├── conf.py
│       ├── index.rst
│       ├── modules.rst
│       ├── nextflow_docs.rst
│       └── usage.rst
├── environment.yml
├── nextflow.config
├── notebooks
│   ├── analyze_silhoutte_scores.ipynb
│   └── r_analysis.ipynb
├── results
├── run.sh
├── setup.py
├── sphinx_build.sh
└── workflow
    ├── compute_silhouette.nf
    ├── main.nf
    ├── merge_results.nf
    └── pull_cellxgene.nf

9 directories, 23 files
```


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
