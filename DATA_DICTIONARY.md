# Data dictionary

## Source data

| Field | Meaning |
| --- | --- |
| `Ticker` | Stock ticker identifying a company. |
| `Market_capital` | Market-capitalization value in the numerical scale supplied in the course dataset. The file does not document its currency, unit, observation date, or provider. |
| `PEG ratio` | Positive price/earnings-to-growth value supplied in the course dataset. Its trailing, forward, or estimated convention is not documented. |

## Generated model fields

| Field | Meaning |
| --- | --- |
| `Log10_Market_capital` | Base-10 logarithm of market capitalization. |
| `Log10_PEG_ratio` | Base-10 logarithm of the PEG ratio. |
| `Market_capital_z` | Standardized log-market-capital feature used by K-means. |
| `PEG_ratio_z` | Standardized log-PEG feature used by K-means. |
| `Raw_Cluster` | Internal K-means label; its integer value has no economic ordering. |
| `Cluster_ID` | Stable 1-9 identifier ordered by the final Size × Style labels. |
| `Capitalization_Label` | Small, Mid, or Large relative label assigned from centroid ordering. |
| `Growth_Label` | Value, Core, or Growth relative label assigned from PEG-centroid ordering within each size group. |
| `Style_Label` | Combined project label. |
| `Center_Market_capital` | Back-transformed log-space centroid, not the arithmetic mean of the cluster. |
| `Center_PEG_ratio` | Back-transformed log-space centroid, not the arithmetic mean of the cluster. |
| `Centroid_Distance` | Euclidean distance from a stock to its assigned K-means center in standardized log-feature space. The smallest value in each cluster identifies its representative stock. |
| `Model_Label` | Project Size × Style label for a supplementary representative stock. |
| `Morningstar_Label` | Size × Style label transcribed from the team-provided comparison image. |
| `Difference` | Which part of the model label differs from the team-provided label: `None`, `Size`, `Style`, or `Both`. |
| `Evidence_Status` | Provenance note for the supplementary team-provided label. |

The nine labels are project-specific interpretations used to satisfy the assignment. They are compared with Morningstar Style Box labels, but they do not reproduce Morningstar's multi-factor methodology.

`favorite_stock_comparison.csv` contains the five documented Morningstar cases. `representative_stock_comparison.csv` is a separate supplementary output covering one stock per cluster. Its external labels come from `K-Means Comparison.png`; the original Morningstar links and access dates were not supplied, so the two comparisons are not pooled.
