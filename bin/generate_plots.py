import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

def plot_silhouette_scores(input_csv, output_dir):
    df = pd.read_csv(input_csv)

    # Validate required columns
    required_columns = {"cluster", "silhouette_score", "dataset_version_id"}
    if not required_columns.issubset(df.columns):
        raise ValueError(f"CSV is missing required columns: {required_columns - set(df.columns)}")

    dataset_version_id = df["dataset_version_id"].unique()[0]
    output_png = os.path.join(output_dir, f"silhouette_plot_{dataset_version_id}.png")

    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x="cluster", y="silhouette_score")
    plt.xticks(rotation=90)
    plt.title(f"Cluster-Level Silhouette Scores for {dataset_version_id}")
    plt.xlabel("Cluster")
    plt.ylabel("Silhouette Score")
    plt.savefig(output_png)
    print(f"Plot saved to: {output_png}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_plots.py <input_csv> <output_directory>")
        sys.exit(1)

    plot_silhouette_scores(sys.argv[1], sys.argv[2])
