import json
import pandas as pd
import scanpy as sc
import sklearn.metrics as skm
import sys

def compute_silhouette(input_json, output_csv):
    """
    Computes silhouette scores per cluster and ensures dataset URLs exist.
    """
    try:
        with open(input_json, 'r') as f:
            datasets = json.load(f)

        results = []

        for dataset in datasets:
            dataset_id = dataset['dataset_id']
            dataset_url = dataset['dataset_url']

            if dataset_url == "N/A" or not dataset_url.strip():
                print(f"Skipping dataset {dataset_id} due to missing dataset URL.", file=sys.stderr)
                continue  # Skip datasets with missing URLs

            print(f"Processing dataset: {dataset_id}")

            try:
                # Load dataset from valid URL
                adata = sc.read(dataset_url)

                # Compute PCA
                sc.tl.pca(adata, svd_solver="arpack")
                pca = adata.obsm['X_pca']
                labels = adata.obs['author_cell_type']

                # Compute silhouette scores per cluster
                unique_clusters = labels.unique()
                cluster_scores = []
                for cluster in unique_clusters:
                    cluster_indices = labels == cluster
                    if sum(cluster_indices) > 1:
                        score = skm.silhouette_score(pca[cluster_indices], labels[cluster_indices], metric='cosine')
                        cluster_scores.append({"dataset_id": dataset_id, "cluster": cluster, "silhouette_score": score})

                results.extend(cluster_scores)

            except Exception as e:
                print(f"Error processing dataset {dataset_id}: {str(e)}", file=sys.stderr)
                continue  # Skip to next dataset

        # Save results to CSV
        df = pd.DataFrame(results)
        df.to_csv(output_csv, index=False)
        print(f"Silhouette scores saved to: {output_csv}")

    except Exception as e:
        print(f"Error computing silhouette scores: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    input_json = sys.argv[1]
    output_csv = sys.argv[2]
    compute_silhouette(input_json, output_csv)

