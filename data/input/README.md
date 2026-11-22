# Input data and selection rationale

This folder contains the manually collected inputs used for the Morningstar comparison and the new-stock classification. In the GitHub repository, the Russell 2000 training sample remains at `data/equity_data.csv`; the local Python project stores its working copy at `data/raw/equity_data.csv`.

## Files to share

- `favorite_stocks.csv`: five stocks from the training sample and their Morningstar Stock Style Box classifications.
- `new_stock.csv`: one stock outside the training sample for KNN and K-means classification.

Upload both CSV files and this README to `data/input/`. Model results, figures, and Python code can be added after the final analysis is run.

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

- Market capitalization: USD 6,120,000,000. Bloomberg displayed `Mkt Cap (USD) 6,120.0M`; the CSV stores the equivalent amount in raw dollars to match the training data.
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
- `Market_capital`: market capitalization in raw USD, matching the training-data convention.
- `PEG ratio`: positive PEG ratio used as the second model feature.
- `Data_As_Of_Date`: date the displayed values were observed.
- `Source_URL`: data provider and terminal path or public source link.

## Evidence handling

Keep Morningstar and Bloomberg screenshots outside the public repository. The public GitHub repository should contain the recorded values, source links or terminal paths, and access dates rather than subscription-screen screenshots.
