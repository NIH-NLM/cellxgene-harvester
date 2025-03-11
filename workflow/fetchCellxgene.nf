process fetchCellxgene {
    tag 'fetchCellxgene'

    publishDir "${launchDir}/${params.datadir}", mode: 'copy'

    input:
        val test_mode

    output:
        path "${params.datadir}/collections_info.json", emit: collections_json

    script:
    """
    echo "Fetching collections from CellxGene API (Test Mode: $test_mode)"

    python "${launchDir}/bin/fetch_cellxgene.py" fetch_collections $test_mode
    """
}
