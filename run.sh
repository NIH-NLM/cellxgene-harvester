#!/bin/bash

# Ensure working directory is quoted
PROJECT_DIR="$(pwd)"
export PATH="$PROJECT_DIR/bin:$PATH"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Activate Conda environment
conda activate scrnaseq_silhouette

# Run Nextflow with quoted paths
nextflow run "$PROJECT_DIR/workflow/main.nf" -profile local --test_mode true | tee "$PROJECT_DIR/logs/nextflow.log"

