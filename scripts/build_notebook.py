"""Build the executed-analysis presentation notebook from reusable project code."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "model" / "model.ipynb"


def code(source: str):
    return nbf.v4.new_code_cell(source.strip())


def markdown(source: str):
    return nbf.v4.new_markdown_cell(source.strip())


notebook = nbf.v4.new_notebook()
notebook["metadata"]["kernelspec"] = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}
notebook["metadata"]["language_info"] = {"name": "python", "version": "3"}
notebook["cells"] = [
    markdown(
        """
# Stock Classification with K-means and KNN

**FIM 590-003 — Project 02**  
**Group:** Joy Wu, Luolin Zhang, Jialin Zhang

This notebook reproduces the final nine-cluster model, the documented five-stock Morningstar comparison, a supplementary representative-stock check, KNN model selection, and ELF classification. The reusable implementation is in `src/stock_clustering.py`.
"""
    ),
    markdown("## 1. Setup and reproducible run"),
    code(
        """
from pathlib import Path
import sys
import pandas as pd
from IPython.display import Image, display

ROOT = Path.cwd().resolve()
while ROOT != ROOT.parent and not (ROOT / "src" / "stock_clustering.py").exists():
    ROOT = ROOT.parent
if not (ROOT / "src" / "stock_clustering.py").exists():
    raise FileNotFoundError("Run this notebook from inside the project directory.")
sys.path.insert(0, str(ROOT))

from src.stock_clustering import run_analysis

results = run_analysis(ROOT)
pd.Series(results["metrics"], name="Value").to_frame()
"""
    ),
    markdown(
        """
The model uses only market capitalization and PEG ratio. Ticker is an identifier, not a feature. Rows with a missing or nonpositive feature are excluded; both retained features are transformed with `log10` before distance-based modeling.
"""
    ),
    markdown("## 2. Data audit and exploratory summary"),
    code("pd.read_csv(ROOT / 'data/processed/data_quality_summary.csv')"),
    code(
        """
raw = pd.read_csv(ROOT / "data/equity_data.csv")
raw[["Market_capital", "PEG ratio"]].describe(percentiles=[.25, .5, .75]).T
"""
    ),
    markdown(
        """
PEG is missing for 797 of 1,958 rows (40.70%), leaving 1,161 complete positive-feature observations. Log transformation reduces right-skew, and standardization prevents either logged feature from dominating Euclidean distance.
"""
    ),
    markdown("## 3. K-means model and nine project labels"),
    code(
        """
cluster_summary = pd.read_csv(ROOT / "data/processed/cluster_summary.csv")
cluster_summary[[
    "Cluster_ID", "Raw_Cluster", "Style_Label", "Center_Market_capital_billions",
    "Center_PEG_ratio", "Stock_Count", "Stock_Share"
]].style.format({
    "Center_Market_capital_billions": "{:.3f}",
    "Center_PEG_ratio": "{:.3f}",
    "Stock_Share": "{:.1%}",
})
"""
    ),
    code("display(Image(filename=ROOT / 'outputs/figures/kmeans_clusters.png'))"),
    markdown(
        """
K-means uses `n_clusters=9`, `n_init=50`, and `random_state=42`. Cluster centroids are ordered by market capitalization and split into three groups of three (Small, Mid, Large). Inside each group, PEG centroids are ordered low-to-high and named Value, Core, and Growth. These are relative project labels; the colored regions are K-means Voronoi regions in standardized log-feature space, not Morningstar boundaries.
"""
    ),
    code("display(Image(filename=ROOT / 'outputs/figures/cluster_sizes.png'))"),
    markdown("## 4. Five-stock comparison with Morningstar"),
    code(
        """
favorite = pd.read_csv(ROOT / "data/processed/favorite_stock_comparison.csv")
favorite[[
    "Ticker", "KMeans_Style_Label", "Morningstar_Style_Label",
    "Size_Match", "Style_Match", "Overall_Match", "Morningstar_Access_Date"
]]
"""
    ),
    markdown(
        """
KODK and PZZA agree with Morningstar on size only. ROOT, HOG, and RRR differ on both dimensions. Style agrees in 0 of 5 cases and no case is an exact match. Because these cases were deliberately selected for discussion, the counts are not a population accuracy estimate.
"""
    ),
    code("display(Image(filename=ROOT / 'outputs/figures/selected_stocks.png'))"),
    markdown("## 5. Supplementary nine-cluster representative check"),
    code(
        """
representatives = pd.read_csv(
    ROOT / "data/processed/representative_stock_comparison.csv",
    keep_default_na=False,
)
representatives[[
    "Ticker", "Model_Label", "Morningstar_Label", "Size_Match",
    "Style_Match", "Exact_Match", "Difference", "Evidence_Status"
]]
"""
    ),
    markdown(
        """
For each fitted cluster, the program selects the stock closest to its centroid in standardized log-feature space. The team-provided comparison reports three size matches, three style matches, and one exact match among the nine representatives. The uploaded summary does not include the original Morningstar URLs, access dates, or individual source screenshots, so this check remains separate from the five documented cases and is not treated as a population accuracy estimate.
"""
    ),
    code("display(Image(filename=ROOT / 'K-Means Comparison.png'))"),
    markdown("## 6. KNN model selection"),
    code(
        """
cv = pd.read_csv(ROOT / "outputs/tables/knn_cv_results.csv")
cv.style.format({"Mean_CV_Accuracy": "{:.2%}", "SD_CV_Accuracy": "{:.2%}"})
"""
    ),
    code("display(Image(filename=ROOT / 'outputs/figures/knn_cross_validation.png'))"),
    markdown(
        """
A distance-weighted KNN classifier is trained on the two logged features to reproduce the nine K-means labels. Candidate values are evaluated with shuffled, stratified five-fold cross-validation. Scaling is inside the Pipeline, so it is fitted independently in every fold. The best candidate is `k=15`, with 96.90% mean agreement (1.40 percentage-point standard deviation). This does not measure Morningstar accuracy.
"""
    ),
    markdown("## 7. New-stock classification: ELF"),
    code(
        """
prediction = pd.read_csv(ROOT / "data/processed/new_stock_prediction.csv")
prediction.T
"""
    ),
    markdown(
        """
ELF uses Bloomberg market capitalization of USD 6.120 billion and `Est PEG` of 1.87, accessed November 22, 2026. It is not present in the training sample. KNN and the direct K-means consistency check both classify ELF as **Large Core**. Its values lie within the observed training ranges, although the original training PEG convention is not documented.
"""
    ),
    markdown(
        """
## 8. Limitations

- PEG is missing for 40.70% of the supplied rows, so complete-case selection may be biased.
- The training file omits constituent date, observation date, provider, market-capitalization unit/currency, and PEG convention.
- ELF uses Bloomberg Estimated PEG, which may not match the undocumented training PEG definition.
- A two-feature clustering model is much simpler than Morningstar's multi-factor Style Box methodology.
- The supplementary nine-stock comparison is based on a team-provided summary image without the original Morningstar links or access dates.
- Nine clusters are required by the assignment; the silhouette score of 0.3423 indicates overlapping rather than sharply separated groups.
- KNN validation measures reproduction of K-means-derived labels, not financial forecasting, Morningstar agreement, or investment performance.
"""
    ),
    markdown(
        """
## 9. Reproducibility

All generated CSVs and PNGs are created by `run_analysis(ROOT)`. The complete implementation—including validation, transformations, K-means, deterministic label mapping, KNN cross-validation, prediction, and plotting—is in `src/stock_clustering.py` and can be rerun from a clean environment using `requirements.txt`.
"""
    ),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(notebook, OUTPUT)
print(f"Wrote {OUTPUT}")
