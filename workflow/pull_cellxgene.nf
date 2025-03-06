process fetchDatasets {
    output:
        path "datasets_info.json"

    script:
    """
    python bin/fetch_cellxgene.py --output datasets_info.json
    """
}
