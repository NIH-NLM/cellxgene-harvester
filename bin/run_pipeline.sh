#!/bin/bash
#
# Run the complete CellxGene data harvesting pipeline
#
# 4 Steps (Step 3 removed - not needed):
# 1. Fetch collections from API
# 2. Generate complete metadata CSV (extracts everything from collections.json)
# 3. Filter by organism and tissue
# 4. Count normal cells in filtered datasets

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR"
DATA_DIR="$SCRIPT_DIR/../data"

echo "======================================================================"
echo "CellxGene Data Harvester - Complete Pipeline"
echo "======================================================================"
echo ""

# Step 1: Fetch collections
echo "Step 1/4: Fetching collections..."
python "$BIN_DIR/1_fetch_collections.py"
echo ""

# Step 2: Generate complete metadata CSV (no Step 3 needed!)
echo "Step 2/4: Generating complete metadata CSV..."
python "$BIN_DIR/2_generate_metadata_csv.py"
echo ""

# Step 3: Filter datasets
echo "Step 3/4: Filtering datasets..."
echo ""

mkdir -p "$DATA_DIR"

# Homo sapiens (all tissues)
python "$BIN_DIR/4_filter_datasets.py" \
    --input "data/cellxgene_complete_metadata.csv" \
    --organism "Homo sapiens" \
    --no-preprints \
    --exclude-cancer \
    --exclude-spatial \
    --output "$DATA_DIR/homo_sapiens_all.csv"

# Homo sapiens lung
python "$BIN_DIR/4_filter_datasets.py" \
    --input "data/cellxgene_complete_metadata.csv" \
    --organism "Homo sapiens" \
    --tissue "lung" \
    --no-preprints \
    --exclude-cancer \
    --exclude-spatial \
    --output "$DATA_DIR/homo_sapiens_lung_harvester.csv"

# Homo sapiens pancreas
python "$BIN_DIR/4_filter_datasets.py" \
    --input "data/cellxgene_complete_metadata.csv" \
    --organism "Homo sapiens" \
    --tissue "pancreas|isle" \
    --no-preprints \
    --exclude-cancer \
    --exclude-spatial \
    --output "$DATA_DIR/homo_sapiens_pancreas_harvester.csv"

# Homo sapiens kidney
python "$BIN_DIR/4_filter_datasets.py" \
    --input "data/cellxgene_complete_metadata.csv" \
    --organism "Homo sapiens" \
    --tissue "kidney" \
    --no-preprints \
    --exclude-cancer \
    --exclude-spatial \
    --output "$DATA_DIR/homo_sapiens_kidney_harvester.csv"

echo ""
echo "Step 4/4: Counting normal cells (this takes time)..."
echo ""

# Count normal cells for each filtered dataset
for filtered_csv in "$DATA_DIR"/*_harvester.csv; do
    if [ -f "$filtered_csv" ]; then
        echo "Processing: $(basename "$filtered_csv")"
        python "$BIN_DIR/5_count_normal_cells.py" "$filtered_csv"
        echo ""
    fi
done

echo ""
echo "======================================================================"
echo "Pipeline Complete!"
echo "======================================================================"
echo ""
echo "Output files in $DATA_DIR:"
echo "  - cellxgene_complete_metadata.csv"
echo "  - homo_sapiens_lung_harvester_with_normal_counts.csv"
echo "  - homo_sapiens_pancreas_harvester_with_normal_counts.csv"
echo "  - homo_sapiens_kidney_harvester_with_normal_counts.csv"
echo ""
