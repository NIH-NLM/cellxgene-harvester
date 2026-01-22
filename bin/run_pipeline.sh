#!/bin/bash
#
# Run the complete CellxGene data harvesting pipeline
#
# This script executes all 5 steps:
# 1. Fetch collections from API
# 2. Generate metadata CSV
# 3. Append dataset details (H5AD URLs, cell counts, titles)
# 4. Filter by organism and tissue
# 5. Count normal cells in filtered datasets only
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR"
DATA_DIR="$SCRIPT_DIR/../data"

echo "======================================================================"
echo "CellxGene Data Harvester - Complete Pipeline"
echo "======================================================================"
echo ""

# Step 1: Fetch collections
echo "Step 1/5: Fetching collections..."
python3 "$BIN_DIR/1_fetch_collections.py"
echo ""

# Step 2: Generate metadata CSV
echo "Step 2/5: Generating metadata CSV..."
python3 "$BIN_DIR/2_generate_metadata_csv.py"
echo ""

# Step 3: Append dataset details
echo "Step 3/5: Fetching dataset details (this takes 10-20 minutes)..."
python3 "$BIN_DIR/3_append_dataset_details.py"
echo ""

# Step 4: Filter datasets
echo "Step 4/5: Filtering datasets..."
echo ""

# Create filtered versions for common use cases
mkdir -p "$DATA_DIR"

# Homo sapiens (all)
python3 "$BIN_DIR/4_filter_datasets.py" \
    --organism "Homo sapiens" \
    --output "$DATA_DIR/homo_sapiens_all.csv"

# Homo sapiens lung (no preprints)
python3 "$BIN_DIR/4_filter_datasets.py" \
    --organism "Homo sapiens" \
    --tissue "lung" \
    --no-preprints \
    --output "$DATA_DIR/homo_sapiens_lung_harvester.csv"

# Homo sapiens pancreas (no preprints)
python3 "$BIN_DIR/4_filter_datasets.py" \
    --organism "Homo sapiens" \
    --tissue "pancreas|isle" \
    --no-preprints \
    --output "$DATA_DIR/homo_sapiens_pancreas_harvester.csv"

# Homo sapiens kidney (no preprints)
python3 "$BIN_DIR/4_filter_datasets.py" \
    --organism "Homo sapiens" \
    --tissue "kidney" \
    --no-preprints \
    --output "$DATA_DIR/homo_sapiens_kidney_harvester.csv"

echo ""
echo "Step 5/5: Counting normal cells (downloads H5AD files for filtered datasets)..."
echo ""

# Count normal cells for each filtered dataset
for filtered_csv in "$DATA_DIR"/*_harvester.csv; do
    if [ -f "$filtered_csv" ]; then
        echo "Processing: $(basename "$filtered_csv")"
        python3 "$BIN_DIR/5_count_normal_cells.py" "$filtered_csv"
        echo ""
    fi
done

echo ""
echo "======================================================================"
echo "Pipeline Complete!"
echo "======================================================================"
echo ""
echo "Output files:"
echo "  - $DATA_DIR/collections_metadata.json"
echo "  - $DATA_DIR/all_datasets.csv"
echo "  - $DATA_DIR/all_datasets_complete.csv"
echo "  - $DATA_DIR/homo_sapiens_lung_harvester.csv"
echo "  - $DATA_DIR/homo_sapiens_lung_harvester_with_normal_counts.csv"
echo "  - $DATA_DIR/homo_sapiens_pancreas_harvester.csv"
echo "  - $DATA_DIR/homo_sapiens_pancreas_harvester_with_normal_counts.csv"
echo "  - $DATA_DIR/homo_sapiens_kidney_harvester.csv"
echo "  - $DATA_DIR/homo_sapiens_kidney_harvester_with_normal_counts.csv"
echo ""
