process processDataset {
    input:
        val dataset

    output:
        path "silhouette_scores_${dataset.dataset_id}.csv"

    script:
    """
    python "${launchDir}/bin/compute_silhouette.py" '${dataset}' "silhouette_scores_${dataset.dataset_id}.csv"
    """
}

