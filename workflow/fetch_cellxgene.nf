process fetchCellxgene {
    output:
    path "collections_info.json"

    script:
    """
    python "${launchDir}/bin/fetch_cellxgene.py"
    """
}

