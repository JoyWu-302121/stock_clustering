"""Run the complete stock clustering and KNN analysis."""

from pathlib import Path

from src.stock_clustering import run_analysis


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    results = run_analysis(project_root)
    metrics = results["metrics"]
    print("Analysis complete")
    print(f"Modeled stocks: {int(metrics['modeled_rows']):,}")
    print(f"Silhouette score: {metrics['silhouette_score']:.4f}")
    print(f"Selected KNN k: {int(metrics['knn_best_k'])}")
    print(f"KNN mean CV accuracy: {metrics['knn_cv_accuracy_mean']:.4f}")
    if not results["new_predictions"].empty:
        row = results["new_predictions"].iloc[0]
        print(f"{row['Ticker']} KNN prediction: {row['KNN_Style_Label']}")
        print(f"{row['Ticker']} K-means check: {row['KMeans_Style_Label']}")
    print(f"Outputs: {project_root / 'data' / 'processed'}")

