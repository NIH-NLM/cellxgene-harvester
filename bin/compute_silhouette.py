import json
import pandas as pd
import scanpy as sc
import pooch
import sklearn.metrics as skm
import os
import sys

CACHE_DIR = os.path.expanduser("~/.cellxgene_cache")

def download_dataset(dataset_url, dataset_id):
    """
    Uses pooch to fetch datasets from CellxGene.
    """
    return pooch.retrieve(
        url=dataset_url,
        fname=f"{dataset_id}.h5ad",
        path=CACHE_DIR,
        known_hash=None
    )

def compute_silhouette(dataset_json_str, output_csv):
    """
    Computes silhouette scores per cluster for a single dataset.
    """
    try:
        dataset = json.loads(dataset_json_str)

        dataset_id = dataset['dataset_id']
        dataset_url = dataset['dataset_url']

        if not dataset_url.strip():
            print(f"Skipping dataset {dataset_id}: Missing URL", file=sys.stderr)
            sys.exit(1)

        print(f"Processing dataset: {dataset_id}")

        dataset_path = download_dataset(dataset_url, dataset_id)
        adata = sc.read_h5ad(dataset_path)

        sc.tl.pca(adata, svd_solver="arpack")
        pca = adata.obsm['X_pca']
        labels = adata.obs['author_cell_type']

        unique_clusters = labels.unique()
        cluster_scores = []
        for cluster in unique_clusters:
            cluster_indices = labels == cluster
            if sum(cluster_indices) > 1:
                score = skm.silhouette_score(pca[cluster_indices], labels[cluster_indices], metric='cosine')
                cluster_scores.append({"dataset_id": dataset_id, "cluster": cluster, "silhouette_score": score})

        df = pd.DataFrame(cluster_scores)
        df.to_csv(output_csv, index=False)

    except Exception as e:
        print(f"Error processing dataset {dataset_id}: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    dataset_json_str = sys.argv[1]  # Read dataset JSON from Nextflow
    output_csv = sys.argv[2]
    compute_silhouette(dataset_json_str, output_csv)

