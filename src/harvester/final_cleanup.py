#!/usr/bin/env python3
"""
Step 6: Final cleanup - Remove datasets with no normal cells

Removes rows where:
- normal_cell_count is blank, empty, or 0

Usage:
1. Python module execution:
python -m harvester.final_cleanup <input_csv>

2. CLI command (after pip install -e .):
cellxgene-harvester final-cleanup homo_sapiens_harvester_kidney_with_normal_counts.csv

"""

import os
import sys
import pandas as pd

def cleanup_dataset(input_csv, output_csv):
    """Remove rows with no normal cells"""
    
    # Load data
    df = pd.read_csv(input_csv)
    print(f"Loaded {len(df)} datasets from {input_csv}")
    
    initial_count = len(df)
    
    # Convert normal_cell_count to numeric, treating non-numeric as 0
    df['normal_cell_count'] = pd.to_numeric(df['normal_cell_count'], errors='coerce').fillna(0)
    
    # Filter: Keep only rows where normal_cell_count > 0
    df = df[df['normal_cell_count'] > 0]
    
    removed = initial_count - len(df)
    
    print(f"\nCleanup Summary:")
    print(f"  Original datasets: {initial_count}")
    print(f"  Datasets with normal cells > 0: {len(df)}")
    print(f"  Datasets removed: {removed}")
    
    # Save cleaned dataset
    df.to_csv(output_csv, index=False)
    print(f"\nCleaned dataset saved to: {output_csv}")
    
    return len(df), removed

# =============================================================================
# run_final_cleanup
# =============================================================================
def run_final_cleanup(input_csv: str):
    """Main entry point called by CLI"""
    base = os.path.splitext(input_csv)[0]
    if base.endswith('_with_normal_counts'):
        base = base.replace('_with_normal_counts', '')
    output_csv = f"{base}_final.csv"
    
    print("="*70)
    print("CellxGene Harvester - Step 6: Final Cleanup")
    print("="*70)
    
    cleanup_dataset(input_csv, output_csv)
