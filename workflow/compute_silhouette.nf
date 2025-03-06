process computeSilhouette {
    input:
        path datasets_info
    
    output:
        path "silhouette_scores.csv"

    script:
    """
    python bin/compute_silhouette.py --input datasets_info.json --output silhouette_scores.csv
    """
}
