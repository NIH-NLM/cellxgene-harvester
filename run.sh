#!/bin/bash

# Ensure script runs from the project root
cd "$(dirname "$0")"

# Run Nextflow
nextflow run workflow/main.nf -profile local --test_mode true

