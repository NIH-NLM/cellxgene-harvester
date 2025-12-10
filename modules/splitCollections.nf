process splitCollections {
    tag 'split_collections'

    publishDir "${launchDir}/${params.datadir}/${params.collections_split}", mode: 'copy'

    input:
        path collection_json
        
    output:
        path "collection_*.json", emit: collection_jsons

    script:
    """
    bash "${launchDir}/bin/splitCollections.sh" "$collection_json"
    """
}

