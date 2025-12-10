process computeSilhouette {
    tag 'computeSilhouette'

    publishDir "${launchDir}/${params.outdir}", mode: 'copy'

    input:
        path dataset_json

    output:
        path "silhouette_scores_*.csv", emit: scores_csvs

    script:
    """
    echo "Computing Silhouette Scores for datasets"

    python "${launchDir}/bin/compute_silhouette.py" "$dataset_json"
    """
}
