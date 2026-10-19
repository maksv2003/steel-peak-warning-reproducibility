# Steel Peak Warning — Reproducibility Reconstruction

A runnable reconstruction of the experiment described in *Early Warning of Peak Electricity Consumption in Steel Production under a False Warning Budget*, using the public UCI Steel Industry Energy Consumption data.

**Status:** this is newly written code based on the manuscript. The original executable code, saved predictions and claimed reproducibility archive were not available. The supplied results are results of this reconstruction, not a recovered original experiment. In particular, the CatBoost results differ from the manuscript.

## Run

Use Python **3.12.14**, the version recorded for the supplied run. From the repository directory:

```bash
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or `source .venv/bin/activate` on macOS/Linux. Then run:

```bash
python -m pip install -r requirements.txt
python reproduce.py
python -m unittest discover -s tests
```

The script evaluates all six methods at one-, two- and four-hour leads in both protocols below at three calibration allowances, and writes tables, predictions, bootstrap samples and figures to `results/`. Running the full experiment again replaces files with the same names. Use `python reproduce.py --output results_new` to keep a separate run. A partial horizon run requires a new or empty output directory, for example `python reproduce.py --horizons 8 --output results_two_hours`, so earlier figures or audit files cannot be mixed with new results. Bootstrap intervals, figures and the manuscript audit are generated only when the one-hour horizon (`4`) is included; the audit explicitly marks unavailable horizons when the run is partial. The CSV is bundled; if it is absent, the script downloads it from UCI and verifies its SHA-256 hash.

[reproduction.ipynb](reproduction.ipynb) is the notebook companion. It uses the same implementation; `reproduce.py` is the command-line entry point. Notebook support packages are included in `requirements.txt`; a notebook editor or frontend can be selected separately.

Direct package versions are pinned. The actual scientific-package versions and operating system for the supplied run are recorded in [results/environment.json](results/environment.json). This is not a complete lockfile of transitive dependencies.

## What is evaluated

The target is one future 15-minute consumption record, at row offsets 4, 8 or 16. A peak exceeds the training-period 90th percentile, **85.82 kWh**. It is a statistical label, not a plant's contractual or equipment limit.

The training segment contains the first 181 source-day blocks; the next 62 blocks calibrate warning thresholds, and the final 122 blocks test them. Each block contains 96 records. A false warning is a false-positive target record; consecutive warnings are not merged into episodes. The primary allowance permits at most 31 calibration false positives, or 0.5 per calibration calendar day. It does not guarantee the same rate on future data.

Two protocols expose a boundary issue in the written experiment:

| Protocol | Meaning | One-hour calibration/test records |
| --- | --- | ---: |
| `legacy` | Splits by target row, matching the manuscript's stated sample sizes. Initial forecast origins precede the next segment, so some fitted/calibrated information would not yet have been available at those origins. | 5,952 / 11,712 |
| `origin_safe` | Keeps training fixed and requires calibration/test origins to start in their own segment. It omits the first horizon-length target block at each later boundary. | 5,948 / 11,708 |

Both use 62/122 calendar-day denominators; the omitted initial forecast intervals remain part of that calendar exposure. The supplied one-hour recall, precision and false-warning counts happen to agree between protocols, but their evaluated rows differ. Their equivalence must not be assumed for other horizons or data.

The source CSV has **365 non-increasing timestamp steps**, associated with the midnight entries. Its original bytes, row order and date strings are retained. Records are not sorted by parsed timestamps or silently corrected; row offsets define the observation sequence. See [results/data_audit.json](results/data_audit.json) and [METHODOLOGY.md](METHODOLOGY.md).

## Computed results and manuscript comparison

One-hour test results at the 0.5 calibration allowance, using `origin_safe`: **11,708 eligible records, 681 peaks, 122 calendar days**. Values below come from [results/metrics.csv](results/metrics.csv).

| Method | TP | FP | Recall (%) | Precision (%) | False/day | Average precision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Persistence | 86 | 110 | 12.6 | 43.9 | 0.902 | 0.330 |
| Previous day | 29 | 148 | 4.3 | 16.4 | 1.213 | 0.142 |
| Previous week | 35 | 137 | 5.1 | 20.3 | 1.123 | 0.171 |
| Logistic regression | 99 | 65 | 14.5 | 60.4 | 0.533 | 0.405 |
| CatBoost classifier | 88 | 79 | 12.9 | 52.7 | 0.648 | 0.438 |
| CatBoost regressor | 133 | 109 | 19.5 | 55.0 | 0.893 | 0.440 |

The three baselines and logistic regression match the manuscript's Table I at its reported rounding. **Both CatBoost rows do not match.** For example:

| Method | Manuscript recall / false per day | Reconstruction recall / false per day |
| --- | --- | --- |
| CatBoost classifier | 10.6% / 0.631 | 12.9% / 0.648 |
| CatBoost regressor | 16.9% / 0.730 | 19.5% / 0.893 |

The same CatBoost discrepancies occur under `legacy`; the boundary correction does not explain them. [results/manuscript_comparison.csv](results/manuscript_comparison.csv) audits Table I and Table II, the stated monthly rates, TP/FP and detected-onset counts, marginal and paired confidence intervals, split sizes, and source-data counts. [results/audit_summary.json](results/audit_summary.json) summarizes matches, discrepancies and unavailable quantities. `legacy` and source-data rows directly test the manuscript's claims; `origin_safe` rows are explicitly marked as comparisons with a modified protocol. Unlabelled figure coordinates are not treated as independent exact numerical claims.

The reconstruction specifies choices left ambiguous by the text, including lag indexing, cyclic encodings and threshold candidates. These choices and version-dependent defaults may contribute to discrepancies; their actual cause cannot be identified without the original implementation. No model or threshold is tuned on test results to force agreement. Reported manuscript values serve only as comparison fixtures.

The supplied run still illustrates the operational tradeoff: the regressor detects more peaks than logistic regression, with more false warnings. All six primary one-hour operating points exceed the historical allowance on the test period. This does not establish plant-level savings or intervention benefits.

## Files

| File | Purpose |
| --- | --- |
| [reproduce.py](reproduce.py) | Data checks, features, fitting, calibration, evaluation and plotting |
| [audit_results.py](audit_results.py) | Compare computed outputs with fixed manuscript values without fitting or tuning |
| [METHODOLOGY.md](METHODOLOGY.md) | Explicit definitions, protocol boundaries and reconstruction decisions |
| [reproduction.ipynb](reproduction.ipynb) | Notebook companion |
| `tests/` | Checks of the implementation's core rules |
| `data/Steel_industry_data.csv` | Unmodified public source data |
| [DATA_LICENSE.md](DATA_LICENSE.md) | Dataset attribution, provenance, license and checksum |
| [SOURCES.md](SOURCES.md) | All ten manuscript references, access notes and scope of support |
| [references_audit.json](references_audit.json) | Detailed reference audit dated 2026-10-20 |
| `results/metrics.csv`, `monthly_metrics.csv` | All model/horizon/allowance operating points and monthly breakdowns |
| `results/predictions.csv.gz` | Calibration/test scores with origin and target row indices |
| `results/split_audit.csv`, `feature_names.json` | Sample membership and feature order |
| `results/bootstrap_intervals.csv`, `paired_recall_intervals.csv`, `bootstrap_samples.csv.gz` | Seven-day circular block-bootstrap outputs |
| [results/manuscript_comparison.csv](results/manuscript_comparison.csv), [results/audit_summary.json](results/audit_summary.json) | Detailed numerical comparisons and audit coverage/status summary |
| `results/*.png` | Operating-point and monthly false-warning figures |

## Attribution

[CITATION.cff](CITATION.cff) credits the repository maintainer **maksv2003** for this software reconstruction. It does not assign authorship of the underlying study or third-party sources. Cite the original research and dataset separately as appropriate; see [SOURCES.md](SOURCES.md).

The redistributed dataset is covered by its original **CC BY 4.0** license. No software license is declared in this repository at this stage; the dataset license does not license the code or third-party papers.

## Кратко по-русски

Это новая реализация метода по тексту статьи, а не найденный оригинальный архив авторов. Базовые модели и логистическая регрессия совпали с Table I после округления; **результаты CatBoost не совпали** и сохранены без подгонки. Режим `legacy` повторяет описанное разбиение, `origin_safe` устраняет проблему доступности модели и порога на границах периодов. Исходные даты с 365 нарушениями возрастания сохранены; вычисления идут по порядку строк. Основная команда: `python reproduce.py`.
