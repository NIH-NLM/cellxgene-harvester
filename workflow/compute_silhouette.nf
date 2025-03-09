process computeSilhouette {
    input:
        path datasets_info_json

    output:
        path "silhouette_scores.csv"

    script:
    """
    python "${launchDir}/bin/compute_silhouette.py" "${datasets_info_json}" "silhouette_scores.csv"
    """
}

