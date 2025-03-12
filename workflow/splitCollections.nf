process splitCollections {
    tag 'split_collections'

    publishDir "${launchDir}/${params.collections_split}", mode: 'copy'

    input:
        path collections_json
        
    output:
        path "collection_*.json", emit: collection_jsons

    script:
    """
    bash "${launchDir}/bin/splitCollections.sh"
    """
}

