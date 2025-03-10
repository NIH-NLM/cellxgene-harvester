process computeSilhouette {
    input:
        path datasets_json_file
        val test_mode_flag

    output:
        path "silhouette_scores.json"

    script:
    """
    python "${launchDir}/bin/compute_silhouette.py" ${datasets_json_file} "silhouette_scores.json" "${launchDir}/results/collections/"
    """

    // ✅ Ensure silhouette_scores.json and per-collection scores are stored properly
    publishDir "${launchDir}/results/", mode: 'copy'
}
