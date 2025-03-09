process parseCollections {
    input:
    path collections_json_file  // Pass collections_info.json as input

    output:
    path "datasets_info.json"  // Output parsed datasets as JSON

    script:
    """
    python "${launchDir}/bin/parse_collections.py" "$collections_json_file" "datasets_info.json"
    """
}

