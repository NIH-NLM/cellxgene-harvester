#!/bin/bash

# Activate environment
conda activate scrnaseq_silhouette

# Run Nextflow pipeline
nextflow run workflow/main.nf -profile local

# Start Jupyter Lab for additional analysis
jupyter lab
