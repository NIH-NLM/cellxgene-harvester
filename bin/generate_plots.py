import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys

def plot_silhouette_scores(input_csv, output_png):
    df = pd.read_csv(input_csv)

    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x="cluster", y="silhouette_score")
    plt.xticks(rotation=90)
    plt.title("Cluster-Level Silhouette Scores")
    plt.xlabel("Cluster")
    plt.ylabel("Silhouette Score")
    plt.savefig(output_png)
    print(f"Plot saved to: {output_png}")

if __name__ == "__main__":
    plot_silhouette_scores(sys.argv[1], sys.argv[2])

