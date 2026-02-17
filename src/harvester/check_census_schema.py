#!/usr/bin/env python3
"""
Quick script to check what columns are available in CellxGene Census
"""

import cellxgene_census

print("Opening Census...")
with cellxgene_census.open_soma(census_version="stable") as census:
    # Get the obs (cell-level metadata) column names
    obs_keys = list(census["census_data"]["homo_sapiens"].obs.keys())
    
    print(f"\nFound {len(obs_keys)} columns in Census obs data:\n")
    
    # Look for tissue/organ related fields
    tissue_related = [k for k in obs_keys if 'tissue' in k.lower() or 'organ' in k.lower()]
    
    print("TISSUE/ORGAN RELATED COLUMNS:")
    for key in sorted(tissue_related):
        print(f"  - {key}")
    
    print("\nALL COLUMNS (sorted):")
    for key in sorted(obs_keys):
        print(f"  - {key}")
    
    # Check if embeddings are in obsm
    print("\n" + "="*70)
    print("Checking embeddings availability...")
    print("="*70)
    
    # Get a small sample dataset to check obsm
    print("\nFetching sample data to check embeddings...")
    try:
        adata = cellxgene_census.get_anndata(
            census=census,
            organism="Homo sapiens",
            obs_value_filter="tissue == 'lung'",  # Just get a small sample
        )
        
        if hasattr(adata, 'obsm') and adata.obsm is not None:
            print(f"\nFound {len(adata.obsm.keys())} embedding types in sample:")
            for key in adata.obsm.keys():
                print(f"  - {key}")
        else:
            print("\nNo obsm (embeddings) found in sample")
    except Exception as e:
        print(f"\nCouldn't fetch sample: {e}")

print("\nDone!")
