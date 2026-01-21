#!/bin/bash
#
# CellxGene Harvester - Setup Script
#
# This script sets up the environment and verifies dependencies
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================================"
echo "CellxGene Harvester - Setup"
echo "======================================================================"
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✓ Found Python $PYTHON_VERSION"
else
    echo "✗ ERROR: Python 3 is not installed"
    echo "  Please install Python 3.8 or higher"
    exit 1
fi

# Check pip
echo ""
echo "Checking pip..."
if command -v pip3 &> /dev/null; then
    echo "✓ pip3 is available"
else
    echo "✗ ERROR: pip3 is not installed"
    exit 1
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
echo "This may take a few minutes..."
pip3 install -r "$SCRIPT_DIR/requirements.txt" --quiet

echo ""
echo "✓ Core dependencies installed"

# Create data directory
echo ""
echo "Creating data directory..."
mkdir -p "$SCRIPT_DIR/data"
echo "✓ Data directory created: $SCRIPT_DIR/data"

# Test API connection
echo ""
echo "Testing API connection..."
if curl -s --max-time 10 https://api.cellxgene.cziscience.com/curation/v1/collections?per_page=1 > /dev/null; then
    echo "✓ API connection successful"
else
    echo "✗ WARNING: Could not connect to CellxGene API"
    echo "  Check your internet connection"
fi

echo ""
echo "======================================================================"
echo "Setup Complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Run the complete pipeline:"
echo "     bash bin/run_pipeline.sh"
echo ""
echo "  2. Or run individual steps:"
echo "     python bin/1_fetch_collections.py"
echo "     python bin/2_generate_metadata_csv.py"
echo "     python bin/3_append_dataset_details.py"
echo "     python bin/4_count_normal_cells.py"
echo "     python bin/5_filter_datasets.py --organism 'Homo sapiens' --output filtered.csv"
echo ""
echo "  3. View documentation:"
echo "     cat README.md"
echo "     cat QUICK_REFERENCE.md"
echo ""
