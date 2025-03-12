process splitCollections {
    tag 'split_collections'

    publishDir "${launchDir}/${params.datadir}/${collections_split}"

    input:
        path collections_json
        
    output:
        path "collection_*.json", emit: collection_jsons

    script:
    """
    bash "${launchDir}/bin/splitCollections.sh"
    """
}

