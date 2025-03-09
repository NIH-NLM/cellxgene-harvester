process fetchCellxgene {
    output:
    path "collections_info.json"

    script:
    """
    python "${launchDir}/bin/fetch_cellxgene.py"
    echo "🔹 DEBUG: Collections info saved to collections_info.json"
    """
}

