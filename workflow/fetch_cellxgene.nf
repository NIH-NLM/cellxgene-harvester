process fetchCellxgene {
    input:
        val test_mode_flag

    output:
        path "collections_info.json"

    // ✅ `publishDir` must be outside `script:`
    publishDir "${launchDir}/results/", mode: 'copy'

    script:
    """
    python "${launchDir}/bin/fetch_cellxgene.py" ${test_mode_flag}
    """
}
