import json
import pandas as pd
import scanpy as sc
import sklearn.metrics as skm
import sys

def compute_silhouette(input_json, output_csv):
    """
    Computes silhouette scores for datasets and saves to a CSV file.
    """
    try:
        # Load dataset metadata
        with open(input_json, 'r') as f:
            datasets = json.load(f)

        results = []

        for dataset in datasets:
            dataset_id = dataset['dataset_id']
            dataset_url = dataset['dataset_url']

            print(f"Processing dataset: {dataset_id}")

            # Load dataset from URL
            adata = sc.read(dataset_url)  # Ensure this URL is accessible

            # Compute PCA
            sc.tl.pca(adata, svd_solver="arpack")
            pca = adata.obsm['X_pca']
            labels = adata.obs['author_cell_type']

            # Compute silhouette score
            silhouette_score = skm.silhouette_score(pca, labels, metric='cosine')

            results.append({
                "dataset_id": dataset_id,
                "dataset_url": dataset_url,
                "silhouette_score": silhouette_score
            })

        # Save results to CSV
        df = pd.DataFrame(results)
        df.to_csv(output_csv, index=False)
        print(f"Silhouette scores saved to: {output_csv}")

    except Exception as e:
        print(f"Error computing silhouette scores: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compute_silhouette.py <input_json> <output_csv>")
        sys.exit(1)

    input_json = sys.argv[1]
    output_csv = sys.argv[2]

    compute_silhouette(input_json, output_csv)
