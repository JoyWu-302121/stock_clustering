# Input data and selection rationale

This folder contains the manually collected inputs used for the Morningstar comparison and the new-stock classification. The provided training sample remains at `data/equity_data.csv`; no duplicate raw-data copy is required.

## Files to share

- `favorite_stocks.csv`: five stocks from the training sample and their Morningstar Stock Style Box classifications.
- `new_stock.csv`: one stock outside the training sample for KNN and K-means classification.
- `representative_stock_morningstar_claims.csv`: Morningstar labels transcribed from the team-provided nine-cluster comparison image, with the evidence file and commit recorded separately from the documented five-stock sample.

Upload all three CSV files and this README to `data/input/`. Generated model results, figures, and Python code are stored elsewhere in the project.

## Favorite stock selection

The five stocks were selected as illustrative cases across the model's size and style labels. They are not a random sample and should not be used to estimate the model's overall accuracy.

| Ticker | Model label | Morningstar label | Reason for selection |
| --- | --- | --- | --- |
| KODK | Small Value | Small Core | Provides a small-cap case where the size classification agrees but the style classification differs. |
| PZZA | Small Growth | Small Value | Has a market capitalization close to KODK but a much higher PEG ratio, allowing comparison within the model's small-cap region. |
| ROOT | Mid Value | Small Growth | Provides the mid-cap model case and a comparison where both size and style differ from Morningstar. |
| HOG | Large Core | Small Value | Provides a higher-market-cap core case and a clear contrast with Morningstar. |
| RRR | Large Growth | Small Core | Provides a higher-market-cap growth case and completes the value, core, and growth coverage. |

Morningstar's Stock Style Box, not the one-to-five-star rating, supplies the external classifications. The Style Box effective date was not displayed on the reviewed pages. The classifications were accessed on November 22, 2026, and the direct Morningstar links are stored in `favorite_stocks.csv`.

## New stock selection

ELF (`e.l.f. Beauty, Inc.`) was selected because it is not present in the training data and has positive, documented values for both model features. Its values also fall within a reasonable range for applying the trained classifiers.

- Market capitalization: USD 6,120,000,000. Bloomberg displayed `Mkt Cap (USD) 6,120.0M`; the CSV stores the equivalent raw-dollar amount to align with the numerical scale of the training column. The training file itself does not document its currency or unit.
- PEG ratio: `1.87`, labeled `Est PEG` on Bloomberg.
- Source: Bloomberg Terminal, `ELF US Equity > DES > Profile`.
- Access date: November 22, 2026.

The exact forecast horizon for `Est PEG` was not displayed. The value should therefore be described as **Estimated PEG**, not as a specific trailing or forward PEG measure. `BEST_PEG_RATIO` was unavailable and is not the source of the recorded value.

## Input conventions

### `favorite_stocks.csv`

- `Ticker`: ticker used in the training data.
- `Company_Name`: full company name.
- `Morningstar_Size`: `Small`, `Mid`, or `Large` from the Morningstar Stock Style Box.
- `Morningstar_Style`: `Value`, `Core`, or `Growth` from the Morningstar Stock Style Box.
- `Morningstar_As_Of_Date`: Style Box effective date shown by Morningstar; `Not shown` when unavailable.
- `Morningstar_Access_Date`: date the Morningstar page was reviewed.
- `Morningstar_Source_URL`: direct Morningstar stock-page link.

### `new_stock.csv`

- `Ticker`: stock ticker.
- `Company_Name`: full company name.
- `Market_capital`: Bloomberg market capitalization converted to raw USD. The training file has a similar numerical scale, but its currency/unit metadata were not supplied.
- `PEG ratio`: positive PEG ratio used as the second model feature.
- `Data_As_Of_Date`: date the displayed values were accessed/observed; it is not asserted to be a common effective date for both fields.
- `Source_URL`: data provider and terminal path or public source link.

### `representative_stock_morningstar_claims.csv`

- `Ticker`: stock selected by the model as closest to one fitted cluster centroid.
- `Morningstar_Size` and `Morningstar_Style`: labels shown in the team-provided comparison image.
- `Morningstar_As_Of_Date` and `Morningstar_Access_Date`: recorded as `Not supplied` because the image does not show them.
- `Evidence_File`, `Evidence_URL`, and `Evidence_Commit`: location and GitHub commit for the team summary.
- `Evidence_Status`: states that the original Morningstar links, access dates, and individual source screenshots were not supplied and that the classifications were not independently verified.

## Evidence handling

Keep the individual Morningstar and Bloomberg terminal screenshots outside the public repository. `K-Means Comparison.png` is already part of the team repository and can remain as the evidence file for the supplementary comparison. The CSV does not treat the GitHub commit date as a Morningstar access date.
