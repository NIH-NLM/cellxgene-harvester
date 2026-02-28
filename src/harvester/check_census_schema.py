#!/usr/bin/env python3
"""
Developer utility: inspect available columns and embeddings in CellxGene Census.

NOT part of the public harvester API — this is a one-off diagnostic script.
All Census I/O is inside main() so that Sphinx autodoc can import this module
without triggering any network calls.

Run directly:

    python -m harvester.check_census_schema
    python src/harvester/check_census_schema.py
"""


def main() -> None:
    """Print Census obs columns and available embeddings for Homo sapiens."""
    import cellxgene_census  # local import keeps this out of module-level scope

    print("Opening Census...")
    with cellxgene_census.open_soma(census_version="stable") as census:
        obs_keys = list(census["census_data"]["homo_sapiens"].obs.keys())

        print(f"\nFound {len(obs_keys)} columns in Census obs data:\n")

        tissue_related = [
            k for k in obs_keys
            if 'tissue' in k.lower() or 'organ' in k.lower()
        ]

        print("TISSUE/ORGAN RELATED COLUMNS:")
        for key in sorted(tissue_related):
            print(f"  - {key}")

        print("\nALL COLUMNS (sorted):")
        for key in sorted(obs_keys):
            print(f"  - {key}")

        print("\n" + "=" * 70)
        print("Checking embeddings availability...")
        print("=" * 70)

        print("\nFetching sample data to check embeddings...")
        try:
            adata = cellxgene_census.get_anndata(
                census=census,
                organism="Homo sapiens",
                obs_value_filter="tissue == 'lung'",
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


if __name__ == "__main__":
    main()
