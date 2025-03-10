process parseCollections {
    input:
        path collections_json_file

    output:
        path "datasets_info.json"

    script:
    """
    python "${launchDir}/bin/parse_collections.py" ${collections_json_file} "datasets_info.json"
    """

    // ✅ Ensure datasets_info.json is stored properly
    publishDir "${launchDir}/results/", mode: 'copy'
}
