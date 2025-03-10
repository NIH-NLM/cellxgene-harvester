process computeSilhouette {
    input:
        path datasets_json_file
        val test_mode

    output:
        path "silhouette_scores.json"
        path "collections/"

    script:
    """
    python "${launchDir}/bin/compute_silhouette.py" '${datasets_json_file}' "silhouette_scores.json" "collections/" '${test_mode}'
    """
}

