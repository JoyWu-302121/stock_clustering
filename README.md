# Stock Classification with K-means and KNN

This repository is the complete, reproducible project for FIM 590-003 Project 02. It classifies the provided Russell 2000 stock sample into nine relative Size × Style groups using market capitalization and PEG ratio, compares five documented stocks with Morningstar Stock Style Box labels, adds a supplementary check using one representative from each cluster, and classifies ELF with KNN.

## Authors

- Joy Wu
- Luolin Zhang
- Jialin Zhang

## Key results

- Source rows: 1,958
- Complete positive-feature rows used: 1,161
- PEG rows missing and excluded: 797 (40.70%)
- K-means: 9 clusters, `n_init=50`, `random_state=42`
- Silhouette score: 0.3423
- KNN: distance-weighted, selected `k=15` by stratified five-fold cross-validation
- ELF classification: Large Core by both KNN and K-means
- Documented Morningstar cases: 2/5 size matches, 0/5 style matches, 0/5 exact matches
- Supplementary cluster representatives: 3/9 size matches, 3/9 style matches, 1/9 exact match; source links and access dates were not supplied with the team summary

The KNN validation score measures agreement with the K-means-derived project labels. It is not an accuracy estimate against Morningstar or a measure of investment performance.

## Run from the project root

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_analysis.py
python scripts/build_notebook.py
jupyter nbconvert --execute --to notebook --inplace model/model.ipynb \
  --ExecutePreprocessor.timeout=600
python scripts/build_report.py
```

The source dataset is read directly from `data/equity_data.csv`. Generated tables are written to `data/processed/` and `outputs/tables/`; figures are written to `outputs/figures/`.
The report script rebuilds the Word report. The checked-in PDF is the reviewed submission copy.

## Project structure

```text
.
├── data/
│   ├── equity_data.csv
│   ├── input/
│   └── processed/
├── K-Means Comparison.png
├── EDA/EDA.ipynb
├── model/model.ipynb
├── outputs/
│   ├── figures/
│   └── tables/
├── scripts/
│   ├── build_notebook.py
│   └── build_report.py
├── src/stock_clustering.py
├── run_analysis.py
├── DATA_DICTIONARY.md
├── Stock_Clustering_Final_Report.docx
└── Stock_Clustering_Final_Report.pdf
```

## Data provenance limitation

The supplied `equity_data.csv` does not include the Russell 2000 constituent date, observation date, provider, market-capitalization currency/unit, or PEG definition. The analysis therefore treats it as the course-provided sample and discloses the missing metadata rather than inferring it. ELF uses Bloomberg `Mkt Cap (USD)` and `Est PEG` values accessed November 22, 2026.

The nine-cluster representative comparison comes from the team-provided `K-Means Comparison.png`. The repository records the image and commit as evidence, but the original Morningstar links and access dates were not supplied. These values are kept separate from the five documented Morningstar cases.
