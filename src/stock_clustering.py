"""Reproducible K-means and KNN workflow for the stock classification project."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


RANDOM_STATE = 42
N_CLUSTERS = 9
FEATURE_COLUMNS = ["Market_capital", "PEG ratio"]
LOG_FEATURE_COLUMNS = ["Log10_Market_capital", "Log10_PEG_ratio"]
STYLE_ORDER = [
    "Small Value",
    "Small Core",
    "Small Growth",
    "Mid Value",
    "Mid Core",
    "Mid Growth",
    "Large Value",
    "Large Core",
    "Large Growth",
]


def _ensure_directories(project_root: Path) -> dict[str, Path]:
    paths = {
        "data": project_root / "data",
        "input": project_root / "data" / "input",
        "processed": project_root / "data" / "processed",
        "figures": project_root / "outputs" / "figures",
        "tables": project_root / "outputs" / "tables",
        "models": project_root / "models",
        "model": project_root / "model",
        "scripts": project_root / "scripts",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _load_and_validate(raw_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(raw_path)
    required = ["Ticker", *FEATURE_COLUMNS]
    missing_columns = [column for column in required if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df = df[required].copy()
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    for column in FEATURE_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_feature = df[FEATURE_COLUMNS].isna().any(axis=1)
    nonpositive_feature = (df[FEATURE_COLUMNS].fillna(1) <= 0).any(axis=1)
    valid = ~(missing_feature | nonpositive_feature)

    clean = df.loc[valid].copy()
    excluded = df.loc[~valid].copy()
    excluded["Exclusion_reason"] = np.select(
        [
            excluded[FEATURE_COLUMNS].isna().any(axis=1),
            (excluded[FEATURE_COLUMNS].fillna(1) <= 0).any(axis=1),
        ],
        ["Missing model feature", "Nonpositive model feature"],
        default="Other validation issue",
    )

    quality = pd.DataFrame(
        {
            "Metric": [
                "Source rows",
                "Unique tickers",
                "Duplicate tickers",
                "Missing market capitalization",
                "Missing PEG ratio",
                "Nonpositive market capitalization",
                "Nonpositive PEG ratio",
                "Rows excluded from modeling",
                "Rows used for modeling",
                "Rows retained (%)",
            ],
            "Value": [
                len(df),
                df["Ticker"].nunique(),
                int(df["Ticker"].duplicated().sum()),
                int(df["Market_capital"].isna().sum()),
                int(df["PEG ratio"].isna().sum()),
                int((df["Market_capital"] <= 0).sum()),
                int((df["PEG ratio"] <= 0).sum()),
                len(excluded),
                len(clean),
                100.0 * len(clean) / len(df),
            ],
        }
    )
    return clean, excluded, quality


def _assign_style_labels(centers: pd.DataFrame) -> pd.DataFrame:
    """Create the requested nine project labels from ordered centroids.

    Centroids are ordered by market capitalization and split into three groups
    of three. Within each group, PEG centroids are ordered from low to high and
    labeled Value, Core, and Growth. These are relative project labels, not
    Morningstar thresholds.
    """

    result = centers.copy()
    market_order = result.sort_values("Center_Market_capital").index.to_list()
    label_rows: list[dict[str, Any]] = []
    for size_index, size_name in enumerate(["Small", "Mid", "Large"]):
        group = market_order[size_index * 3 : (size_index + 1) * 3]
        peg_order = result.loc[group].sort_values("Center_PEG_ratio").index.to_list()
        for growth_name, raw_cluster in zip(["Value", "Core", "Growth"], peg_order):
            label_rows.append(
                {
                    "Raw_Cluster": int(raw_cluster),
                    "Capitalization_Label": size_name,
                    "Growth_Label": growth_name,
                    "Style_Label": f"{size_name} {growth_name}",
                }
            )
    return result.join(pd.DataFrame(label_rows).set_index("Raw_Cluster"))


def _fit_kmeans(
    clean: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, StandardScaler, KMeans, float]:
    modeled = clean.copy()
    modeled[LOG_FEATURE_COLUMNS[0]] = np.log10(modeled["Market_capital"])
    modeled[LOG_FEATURE_COLUMNS[1]] = np.log10(modeled["PEG ratio"])

    scaler = StandardScaler()
    scaled = scaler.fit_transform(modeled[LOG_FEATURE_COLUMNS])
    modeled["Market_capital_z"] = scaled[:, 0]
    modeled["PEG_ratio_z"] = scaled[:, 1]

    kmeans = KMeans(n_clusters=N_CLUSTERS, n_init=50, random_state=RANDOM_STATE)
    raw_labels = kmeans.fit_predict(scaled)
    modeled["Raw_Cluster"] = raw_labels

    centers_log = scaler.inverse_transform(kmeans.cluster_centers_)
    centers = pd.DataFrame(
        {
            "Center_Log10_Market_capital": centers_log[:, 0],
            "Center_Log10_PEG_ratio": centers_log[:, 1],
            "Center_Market_capital": np.power(10.0, centers_log[:, 0]),
            "Center_PEG_ratio": np.power(10.0, centers_log[:, 1]),
        },
        index=pd.Index(range(N_CLUSTERS), name="Raw_Cluster"),
    )
    centers["Center_Market_capital_billions"] = centers["Center_Market_capital"] / 1e9
    centers = _assign_style_labels(centers)

    label_columns = ["Capitalization_Label", "Growth_Label", "Style_Label"]
    modeled = modeled.merge(
        centers[label_columns],
        left_on="Raw_Cluster",
        right_index=True,
        how="left",
        validate="many_to_one",
    )
    style_to_id = {label: index + 1 for index, label in enumerate(STYLE_ORDER)}
    modeled["Cluster_ID"] = modeled["Style_Label"].map(style_to_id).astype(int)
    centers["Cluster_ID"] = centers["Style_Label"].map(style_to_id).astype(int)

    counts = modeled.groupby("Raw_Cluster").size().rename("Stock_Count")
    centers = centers.join(counts)
    centers["Stock_Share"] = centers["Stock_Count"] / len(modeled)
    centers = centers.sort_values("Cluster_ID")

    silhouette = float(silhouette_score(scaled, raw_labels))
    return modeled, centers, scaler, kmeans, silhouette


def _fit_knn(modeled: pd.DataFrame) -> tuple[Pipeline, pd.DataFrame, int, float, float]:
    x = modeled[LOG_FEATURE_COLUMNS]
    y = modeled["Style_Label"]
    candidate_k = [3, 5, 7, 9, 11, 15, 21]
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    rows: list[dict[str, float]] = []

    for k in candidate_k:
        pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("knn", KNeighborsClassifier(n_neighbors=k, weights="distance")),
            ]
        )
        scores = cross_val_score(pipeline, x, y, cv=cv, scoring="accuracy")
        rows.append(
            {
                "k": k,
                "Mean_CV_Accuracy": float(scores.mean()),
                "SD_CV_Accuracy": float(scores.std(ddof=1)),
            }
        )

    ranked = pd.DataFrame(rows).sort_values(
        ["Mean_CV_Accuracy", "k"], ascending=[False, True]
    )
    best = ranked.iloc[0]
    best_k = int(best["k"])
    knn = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("knn", KNeighborsClassifier(n_neighbors=best_k, weights="distance")),
        ]
    )
    knn.fit(x, y)
    return (
        knn,
        ranked.sort_values("k"),
        best_k,
        float(best["Mean_CV_Accuracy"]),
        float(best["SD_CV_Accuracy"]),
    )


def _favorite_comparison(input_path: Path, modeled: pd.DataFrame) -> pd.DataFrame:
    source_columns = [
        "Ticker",
        "Company_Name",
        "Morningstar_Size",
        "Morningstar_Style",
        "Morningstar_As_Of_Date",
        "Morningstar_Access_Date",
        "Morningstar_Source_URL",
    ]
    if not input_path.exists():
        return pd.DataFrame(columns=source_columns)
    favorites = pd.read_csv(input_path)
    if favorites.empty:
        return pd.DataFrame(columns=source_columns)
    missing = [column for column in source_columns if column not in favorites.columns]
    if missing:
        raise ValueError(f"favorite_stocks.csv is missing columns: {missing}")

    favorites = favorites[source_columns].copy()
    favorites["Ticker"] = favorites["Ticker"].astype(str).str.strip().str.upper()
    favorites["Morningstar_Style_Label"] = (
        favorites["Morningstar_Size"].astype(str).str.strip()
        + " "
        + favorites["Morningstar_Style"].astype(str).str.strip()
    )
    lookup = modeled[
        [
            "Ticker",
            "Market_capital",
            "PEG ratio",
            "Cluster_ID",
            "Capitalization_Label",
            "Growth_Label",
            "Style_Label",
        ]
    ].rename(
        columns={
            "Capitalization_Label": "KMeans_Size",
            "Growth_Label": "KMeans_Style",
            "Style_Label": "KMeans_Style_Label",
        }
    )
    result = favorites.merge(lookup, on="Ticker", how="left", validate="many_to_one")
    valid = result["Cluster_ID"].notna()
    for column in ["Size_Match", "Style_Match", "Overall_Match"]:
        result[column] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    result.loc[valid, "Size_Match"] = (
        result.loc[valid, "Morningstar_Size"].str.strip().str.lower()
        == result.loc[valid, "KMeans_Size"].str.strip().str.lower()
    )
    result.loc[valid, "Style_Match"] = (
        result.loc[valid, "Morningstar_Style"].str.strip().str.lower()
        == result.loc[valid, "KMeans_Style"].str.strip().str.lower()
    )
    result.loc[valid, "Overall_Match"] = (
        result.loc[valid, "Size_Match"] & result.loc[valid, "Style_Match"]
    )
    return result


def _cluster_representatives(
    modeled: pd.DataFrame, kmeans: KMeans
) -> pd.DataFrame:
    """Select the stock nearest each fitted center in standardized log space."""

    working = modeled.copy()
    coordinates = working[["Market_capital_z", "PEG_ratio_z"]].to_numpy()
    assigned_centers = kmeans.cluster_centers_[working["Raw_Cluster"].to_numpy()]
    working["Centroid_Distance"] = np.linalg.norm(
        coordinates - assigned_centers, axis=1
    )
    representatives = (
        working.sort_values(["Raw_Cluster", "Centroid_Distance", "Ticker"])
        .groupby("Raw_Cluster", as_index=False)
        .first()
        .rename(
            columns={
                "Capitalization_Label": "Model_Size",
                "Growth_Label": "Model_Style",
                "Style_Label": "Model_Label",
            }
        )
    )
    if len(representatives) != N_CLUSTERS:
        raise ValueError(
            f"Expected {N_CLUSTERS} cluster representatives; found {len(representatives)}"
        )
    return representatives[
        [
            "Ticker",
            "Cluster_ID",
            "Raw_Cluster",
            "Model_Size",
            "Model_Style",
            "Model_Label",
            "Market_capital",
            "PEG ratio",
            "Centroid_Distance",
        ]
    ].sort_values("Cluster_ID")


def _representative_stock_comparison(
    input_path: Path, representatives: pd.DataFrame
) -> pd.DataFrame:
    """Join model-selected representatives to the team-provided summary labels."""

    claim_columns = [
        "Ticker",
        "Morningstar_Size",
        "Morningstar_Style",
        "Morningstar_As_Of_Date",
        "Morningstar_Access_Date",
        "Evidence_File",
        "Evidence_URL",
        "Evidence_Commit",
        "Evidence_Status",
    ]
    output_columns = [
        *representatives.columns,
        "Morningstar_Size",
        "Morningstar_Style",
        "Morningstar_Label",
        "Size_Match",
        "Style_Match",
        "Exact_Match",
        "Difference",
        "Morningstar_As_Of_Date",
        "Morningstar_Access_Date",
        "Evidence_File",
        "Evidence_URL",
        "Evidence_Commit",
        "Evidence_Status",
    ]
    if not input_path.exists():
        return pd.DataFrame(columns=output_columns)
    claims = pd.read_csv(input_path)
    if claims.empty:
        return pd.DataFrame(columns=output_columns)
    missing = [column for column in claim_columns if column not in claims.columns]
    if missing:
        raise ValueError(
            "representative_stock_morningstar_claims.csv is missing columns: "
            f"{missing}"
        )

    claims = claims[claim_columns].copy()
    claims["Ticker"] = claims["Ticker"].astype(str).str.strip().str.upper()
    if claims["Ticker"].duplicated().any():
        duplicates = claims.loc[claims["Ticker"].duplicated(), "Ticker"].tolist()
        raise ValueError(f"Duplicate representative-stock claims: {duplicates}")

    expected = set(representatives["Ticker"])
    provided = set(claims["Ticker"])
    if expected != provided:
        raise ValueError(
            "Representative-stock claims do not match the fitted cluster representatives. "
            f"Missing: {sorted(expected - provided)}; extra: {sorted(provided - expected)}"
        )

    claims["Morningstar_Label"] = (
        claims["Morningstar_Size"].astype(str).str.strip()
        + " "
        + claims["Morningstar_Style"].astype(str).str.strip()
    )
    result = representatives.merge(claims, on="Ticker", how="left", validate="one_to_one")
    result["Size_Match"] = (
        result["Model_Size"].str.lower()
        == result["Morningstar_Size"].str.strip().str.lower()
    )
    result["Style_Match"] = (
        result["Model_Style"].str.lower()
        == result["Morningstar_Style"].str.strip().str.lower()
    )
    result["Exact_Match"] = result["Size_Match"] & result["Style_Match"]
    result["Difference"] = np.select(
        [
            result["Exact_Match"],
            ~result["Size_Match"] & ~result["Style_Match"],
            ~result["Size_Match"],
            ~result["Style_Match"],
        ],
        ["None", "Both", "Size", "Style"],
        default="Unknown",
    )
    return result[output_columns]


def _predict_new_stocks(
    input_path: Path,
    modeled: pd.DataFrame,
    scaler: StandardScaler,
    kmeans: KMeans,
    centers: pd.DataFrame,
    knn: Pipeline,
) -> pd.DataFrame:
    source_columns = [
        "Ticker",
        "Company_Name",
        "Market_capital",
        "PEG ratio",
        "Data_As_Of_Date",
        "Source_URL",
    ]
    output_columns = source_columns + [
        "KNN_Size",
        "KNN_Style",
        "KNN_Style_Label",
        "KMeans_Size",
        "KMeans_Style",
        "KMeans_Style_Label",
        "Prediction_Agreement",
        "Already_In_Training_Data",
        "Market_capital_percentile",
        "PEG_ratio_percentile",
    ]
    if not input_path.exists():
        return pd.DataFrame(columns=output_columns)
    new_stocks = pd.read_csv(input_path)
    if new_stocks.empty:
        return pd.DataFrame(columns=output_columns)
    missing = [column for column in source_columns if column not in new_stocks.columns]
    if missing:
        raise ValueError(f"new_stock.csv is missing columns: {missing}")

    new_stocks = new_stocks[source_columns].copy()
    new_stocks["Ticker"] = new_stocks["Ticker"].astype(str).str.strip().str.upper()
    for column in FEATURE_COLUMNS:
        new_stocks[column] = pd.to_numeric(new_stocks[column], errors="coerce")
    invalid = new_stocks[FEATURE_COLUMNS].isna().any(axis=1) | (
        new_stocks[FEATURE_COLUMNS] <= 0
    ).any(axis=1)
    if invalid.any():
        tickers = new_stocks.loc[invalid, "Ticker"].tolist()
        raise ValueError(f"New-stock rows require positive market cap and PEG ratio: {tickers}")

    log_features = pd.DataFrame(
        {
            LOG_FEATURE_COLUMNS[0]: np.log10(new_stocks["Market_capital"]),
            LOG_FEATURE_COLUMNS[1]: np.log10(new_stocks["PEG ratio"]),
        }
    )
    new_stocks["KNN_Style_Label"] = knn.predict(log_features)
    raw_cluster = kmeans.predict(scaler.transform(log_features))
    raw_to_style = centers["Style_Label"].to_dict()
    new_stocks["KMeans_Style_Label"] = [raw_to_style[int(cluster)] for cluster in raw_cluster]

    knn_split = new_stocks["KNN_Style_Label"].str.split(" ", n=1, expand=True)
    kmeans_split = new_stocks["KMeans_Style_Label"].str.split(" ", n=1, expand=True)
    new_stocks["KNN_Size"] = knn_split[0]
    new_stocks["KNN_Style"] = knn_split[1]
    new_stocks["KMeans_Size"] = kmeans_split[0]
    new_stocks["KMeans_Style"] = kmeans_split[1]
    new_stocks["Prediction_Agreement"] = (
        new_stocks["KNN_Style_Label"] == new_stocks["KMeans_Style_Label"]
    )
    training_tickers = set(modeled["Ticker"])
    new_stocks["Already_In_Training_Data"] = new_stocks["Ticker"].isin(training_tickers)
    new_stocks["Market_capital_percentile"] = [
        float((modeled["Market_capital"] <= value).mean()) for value in new_stocks["Market_capital"]
    ]
    new_stocks["PEG_ratio_percentile"] = [
        float((modeled["PEG ratio"] <= value).mean()) for value in new_stocks["PEG ratio"]
    ]
    return new_stocks[output_columns]


def _plot_kmeans_boundaries(
    modeled: pd.DataFrame,
    centers: pd.DataFrame,
    scaler: StandardScaler,
    kmeans: KMeans,
    output_path: Path,
) -> None:
    palette_values = sns.color_palette("colorblind", n_colors=9)
    palette = dict(zip(STYLE_ORDER, palette_values))
    style_to_index = {style: index for index, style in enumerate(STYLE_ORDER)}
    raw_to_index = {
        int(raw_cluster): style_to_index[style]
        for raw_cluster, style in centers["Style_Label"].items()
    }

    x_min, x_max = modeled[LOG_FEATURE_COLUMNS[0]].min(), modeled[LOG_FEATURE_COLUMNS[0]].max()
    y_min, y_max = modeled[LOG_FEATURE_COLUMNS[1]].min(), modeled[LOG_FEATURE_COLUMNS[1]].max()
    x_pad = 0.04 * (x_max - x_min)
    y_pad = 0.04 * (y_max - y_min)
    grid_x, grid_y = np.meshgrid(
        np.linspace(x_min - x_pad, x_max + x_pad, 420),
        np.linspace(y_min - y_pad, y_max + y_pad, 420),
    )
    grid_log = pd.DataFrame(
        np.c_[grid_x.ravel(), grid_y.ravel()], columns=LOG_FEATURE_COLUMNS
    )
    grid_raw = kmeans.predict(scaler.transform(grid_log))
    grid_style = np.array([raw_to_index[int(value)] for value in grid_raw]).reshape(grid_x.shape)

    fig, ax = plt.subplots(figsize=(11.5, 7.2))
    ax.contourf(
        grid_x,
        grid_y,
        grid_style,
        levels=np.arange(-0.5, 9.5, 1),
        cmap=ListedColormap(palette_values),
        alpha=0.18,
    )
    sns.scatterplot(
        data=modeled,
        x=LOG_FEATURE_COLUMNS[0],
        y=LOG_FEATURE_COLUMNS[1],
        hue="Style_Label",
        hue_order=STYLE_ORDER,
        palette=palette,
        s=25,
        alpha=0.65,
        linewidth=0,
        ax=ax,
    )
    for _, row in centers.iterrows():
        ax.scatter(
            row["Center_Log10_Market_capital"],
            row["Center_Log10_PEG_ratio"],
            marker="X",
            s=170,
            color="black",
            edgecolor="white",
            linewidth=1.1,
            zorder=6,
        )
        ax.annotate(
            row["Style_Label"],
            (row["Center_Log10_Market_capital"], row["Center_Log10_PEG_ratio"]),
            xytext=(6, 5),
            textcoords="offset points",
            fontsize=7.7,
            weight="bold",
        )
    ax.set(
        title=f"K-means clusters and decision regions (complete cases, n={len(modeled):,})",
        xlabel="log10(Market capitalization; source units)",
        ylabel="log10(PEG ratio)",
    )
    ax.legend(title="Project cluster label", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(output_path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def _plot_selected_stocks(
    modeled: pd.DataFrame,
    favorite_comparison: pd.DataFrame,
    new_predictions: pd.DataFrame,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.6))
    ax.scatter(
        modeled[LOG_FEATURE_COLUMNS[0]],
        modeled[LOG_FEATURE_COLUMNS[1]],
        color="#9aa3ad",
        alpha=0.32,
        s=18,
        linewidth=0,
        label="Training stocks",
    )
    if not favorite_comparison.empty:
        valid = favorite_comparison.dropna(subset=["Market_capital", "PEG ratio"])
        x = np.log10(valid["Market_capital"])
        y = np.log10(valid["PEG ratio"])
        ax.scatter(
            x,
            y,
            marker="*",
            s=170,
            color="#d97706",
            edgecolor="white",
            linewidth=0.9,
            label="Morningstar comparison stocks",
            zorder=5,
        )
        for ticker, x_value, y_value in zip(valid["Ticker"], x, y):
            ax.annotate(ticker, (x_value, y_value), xytext=(5, 5), textcoords="offset points", fontsize=8)
    if not new_predictions.empty:
        x = np.log10(new_predictions["Market_capital"])
        y = np.log10(new_predictions["PEG ratio"])
        ax.scatter(
            x,
            y,
            marker="D",
            s=95,
            color="#2563eb",
            edgecolor="white",
            linewidth=1.0,
            label="New stock",
            zorder=6,
        )
        for ticker, x_value, y_value in zip(new_predictions["Ticker"], x, y):
            ax.annotate(
                f"{ticker} ({new_predictions.loc[new_predictions['Ticker'] == ticker, 'KNN_Style_Label'].iloc[0]})",
                (x_value, y_value),
                xytext=(7, -12),
                textcoords="offset points",
                fontsize=8,
                weight="bold",
            )
    ax.set(
        title="Selected Morningstar cases and the ELF prediction",
        xlabel="log10(Market capitalization; source units)",
        ylabel="log10(PEG ratio)",
    )
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def _save_figures(
    modeled: pd.DataFrame,
    centers: pd.DataFrame,
    cv_results: pd.DataFrame,
    favorite_comparison: pd.DataFrame,
    new_predictions: pd.DataFrame,
    scaler: StandardScaler,
    kmeans: KMeans,
    figures_path: Path,
) -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    _plot_kmeans_boundaries(
        modeled, centers, scaler, kmeans, figures_path / "kmeans_clusters.png"
    )

    palette = dict(zip(STYLE_ORDER, sns.color_palette("colorblind", n_colors=9)))
    count_data = modeled["Style_Label"].value_counts().reindex(STYLE_ORDER)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(
        count_data.index,
        count_data.values,
        color=[palette[label] for label in STYLE_ORDER],
    )
    ax.set(title="Stocks per K-means cluster", xlabel="", ylabel="Number of stocks")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(figures_path / "cluster_sizes.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.errorbar(
        cv_results["k"],
        cv_results["Mean_CV_Accuracy"],
        yerr=cv_results["SD_CV_Accuracy"],
        marker="o",
        capsize=4,
        linewidth=1.8,
        color="#2563eb",
    )
    ax.set(
        title="KNN five-fold cross-validation accuracy",
        xlabel="Number of neighbors (k)",
        ylabel="Mean accuracy reproducing K-means labels",
    )
    ax.set_ylim(0.90, 1.0)
    fig.tight_layout()
    fig.savefig(figures_path / "knn_cross_validation.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    _plot_selected_stocks(
        modeled,
        favorite_comparison,
        new_predictions,
        figures_path / "selected_stocks.png",
    )


def run_analysis(project_root: Path | str) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    paths = _ensure_directories(project_root)
    raw_path = paths["data"] / "equity_data.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"Source data not found: {raw_path}")

    clean, excluded, quality = _load_and_validate(raw_path)
    modeled, centers, scaler, kmeans, silhouette = _fit_kmeans(clean)
    knn, cv_results, best_k, cv_mean, cv_sd = _fit_knn(modeled)
    favorite_comparison = _favorite_comparison(
        paths["input"] / "favorite_stocks.csv", modeled
    )
    cluster_representatives = _cluster_representatives(modeled, kmeans)
    representative_comparison = _representative_stock_comparison(
        paths["input"] / "representative_stock_morningstar_claims.csv",
        cluster_representatives,
    )
    new_predictions = _predict_new_stocks(
        paths["input"] / "new_stock.csv", modeled, scaler, kmeans, centers, knn
    )

    modeled_output = modeled[
        [
            "Ticker",
            "Market_capital",
            "PEG ratio",
            *LOG_FEATURE_COLUMNS,
            "Market_capital_z",
            "PEG_ratio_z",
            "Cluster_ID",
            "Capitalization_Label",
            "Growth_Label",
            "Style_Label",
        ]
    ].sort_values(["Cluster_ID", "Ticker"])
    cluster_summary = centers.reset_index()[
        [
            "Cluster_ID",
            "Raw_Cluster",
            "Capitalization_Label",
            "Growth_Label",
            "Style_Label",
            "Center_Market_capital",
            "Center_Market_capital_billions",
            "Center_PEG_ratio",
            "Stock_Count",
            "Stock_Share",
        ]
    ]
    cluster_summary = cluster_summary.round(
        {
            "Center_Market_capital": 6,
            "Center_Market_capital_billions": 9,
            "Center_PEG_ratio": 9,
            "Stock_Share": 9,
        }
    )

    source_rows = int(quality.loc[quality["Metric"] == "Source rows", "Value"].iloc[0])
    missing_peg = int(quality.loc[quality["Metric"] == "Missing PEG ratio", "Value"].iloc[0])
    metrics: dict[str, float | int] = {
        "source_rows": source_rows,
        "modeled_rows": int(len(modeled)),
        "excluded_rows": int(len(excluded)),
        "missing_peg_rows": missing_peg,
        "missing_peg_percent": float(missing_peg / source_rows),
        "kmeans_clusters": N_CLUSTERS,
        "kmeans_inertia": float(kmeans.inertia_),
        "silhouette_score": silhouette,
        "knn_best_k": best_k,
        "knn_cv_accuracy_mean": cv_mean,
        "knn_cv_accuracy_sd": cv_sd,
    }
    if not favorite_comparison.empty:
        valid = favorite_comparison["Overall_Match"].notna()
        metrics.update(
            {
                "favorite_cases": int(valid.sum()),
                "favorite_size_matches": int(favorite_comparison.loc[valid, "Size_Match"].sum()),
                "favorite_style_matches": int(favorite_comparison.loc[valid, "Style_Match"].sum()),
                "favorite_overall_matches": int(favorite_comparison.loc[valid, "Overall_Match"].sum()),
            }
        )
    if not representative_comparison.empty:
        metrics.update(
            {
                "supplementary_representative_cases": int(
                    len(representative_comparison)
                ),
                "supplementary_representative_size_matches": int(
                    representative_comparison["Size_Match"].sum()
                ),
                "supplementary_representative_style_matches": int(
                    representative_comparison["Style_Match"].sum()
                ),
                "supplementary_representative_exact_matches": int(
                    representative_comparison["Exact_Match"].sum()
                ),
            }
        )
    metrics_table = pd.DataFrame({"Metric": metrics.keys(), "Value": metrics.values()})
    metrics_table["Value"] = metrics_table["Value"].map(
        lambda value: round(value, 12) if isinstance(value, float) else value
    )
    cv_results = cv_results.round(
        {"Mean_CV_Accuracy": 12, "SD_CV_Accuracy": 12}
    )

    modeled_output.to_csv(paths["processed"] / "equity_clustered.csv", index=False)
    excluded.to_csv(paths["processed"] / "equity_excluded.csv", index=False)
    quality.to_csv(paths["processed"] / "data_quality_summary.csv", index=False)
    cluster_summary.to_csv(paths["processed"] / "cluster_summary.csv", index=False)
    favorite_comparison.to_csv(
        paths["processed"] / "favorite_stock_comparison.csv", index=False
    )
    cluster_representatives.to_csv(
        paths["processed"] / "cluster_representatives.csv", index=False
    )
    representative_comparison.to_csv(
        paths["processed"] / "representative_stock_comparison.csv", index=False
    )
    new_predictions.to_csv(paths["processed"] / "new_stock_prediction.csv", index=False)
    cv_results.to_csv(paths["tables"] / "knn_cv_results.csv", index=False)
    metrics_table.to_csv(paths["tables"] / "model_metrics.csv", index=False)

    _save_figures(
        modeled,
        centers,
        cv_results,
        favorite_comparison,
        new_predictions,
        scaler,
        kmeans,
        paths["figures"],
    )
    joblib.dump(
        {
            "feature_columns": FEATURE_COLUMNS,
            "log_feature_columns": LOG_FEATURE_COLUMNS,
            "kmeans_scaler": scaler,
            "kmeans": kmeans,
            "knn": knn,
            "cluster_summary": cluster_summary,
            "random_state": RANDOM_STATE,
        },
        paths["models"] / "stock_classification_models.joblib",
    )

    return {
        "metrics": metrics,
        "cluster_summary": cluster_summary,
        "modeled": modeled_output,
        "favorite_comparison": favorite_comparison,
        "cluster_representatives": cluster_representatives,
        "representative_comparison": representative_comparison,
        "new_predictions": new_predictions,
        "cv_results": cv_results,
    }
