# Steel Peak Warning — Reproducibility Reconstruction

A runnable reconstruction of the experiment described in *Early Warning of Peak Electricity Consumption in Steel Production under a False Warning Budget*, using the public UCI Steel Industry Energy Consumption data.

**Status:** this implementation was originally reconstructed from an earlier manuscript because its executable code, saved predictions and claimed reproducibility archive were not available. The revised PIERE manuscript now reports the supplied `origin_safe` results, including CatBoost-classifier recall **12.9%** and regressor recall **19.5%**. Its checked numerical claims agree with the stored outputs at the reported precision. The differences from the **earlier manuscript** remain visible in a separate historical audit; they are not discrepancies with the revised manuscript.

## Run

Use Python **3.12.14**, the version recorded for the supplied run. From the repository directory:

```bash
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or `source .venv/bin/activate` on macOS/Linux. Then run:

```bash
python -m pip install -r requirements.txt
python reproduce.py
python audit_revised_manuscript.py results
python -m unittest discover -s tests
```

The script evaluates all six methods at one-, two- and four-hour leads in both protocols below at three calibration allowances, and writes tables, predictions, bootstrap samples and figures to `results/`. Running the full experiment again replaces files with the same names. Use `python reproduce.py --output results_new` to keep a separate run. A partial horizon run requires a new or empty output directory, for example `python reproduce.py --horizons 8 --output results_two_hours`, so earlier figures or audit files cannot be mixed with new results. Bootstrap intervals, figures and the historical manuscript audit are generated only when the one-hour horizon (`4`) is included; the historical audit explicitly marks unavailable horizons when the run is partial. The CSV is bundled; if it is absent, the script downloads it from UCI and verifies its SHA-256 hash.

[reproduction.ipynb](reproduction.ipynb) is the notebook companion. It uses the same implementation; `reproduce.py` is the command-line entry point. Notebook support packages are included in `requirements.txt`; a notebook editor or frontend can be selected separately.

Direct package versions are pinned. The actual scientific-package versions and operating system for the supplied run are recorded in [results/environment.json](results/environment.json). This is not a complete lockfile of transitive dependencies.

The publication PNG figures use **Times New Roman at 8 pt**, at a final width of 3.3791667 inches and 480 dpi. Install an appropriately licensed copy of Times New Roman for identical figure typography. If it is unavailable, the plotter emits a warning and uses DejaVu Serif; that fallback preserves the plotted data but does not meet the manuscript's font specification. The supplied publication figures were generated with Times New Roman. The figure-formatting revision does not change the numerical result files. The notebook also contains separate, larger exploratory plots.

## What is evaluated

The target is one future 15-minute consumption record, at row offsets 4, 8 or 16. A peak exceeds the training-period 90th percentile, **85.82 kWh**. It is a statistical label, not a plant's contractual or equipment limit.

The training segment contains the first 181 source-day blocks; the next 62 blocks calibrate warning thresholds, and the final 122 blocks test them. Each block contains 96 records. A false warning is a false-positive target record; consecutive warnings are not merged into episodes. The primary allowance permits at most 31 calibration false positives, or 0.5 per calibration calendar day. It does not guarantee the same rate on future data.

The revised manuscript uses `origin_safe`. The repository also retains `legacy` to document a boundary issue in the earlier manuscript:

| Protocol | Meaning | One-hour calibration/test records |
| --- | --- | ---: |
| `legacy` | Splits by target row, matching the earlier manuscript's stated sample sizes. Initial forecast origins precede the next segment, so some fitted/calibrated information would not yet have been available at those origins. | 5,952 / 11,712 |
| `origin_safe` | Keeps training fixed and requires calibration/test origins to start in their own segment. It omits the first horizon-length target block at each later boundary. | 5,948 / 11,708 |

Both use 62/122 calendar-day denominators; the omitted initial forecast intervals remain part of that calendar exposure. The supplied one-hour recall, precision and false-warning counts happen to agree between protocols, but their evaluated rows differ. Their equivalence must not be assumed for other horizons or data.

The source CSV has **365 non-increasing timestamp steps**, associated with the midnight entries. Its original bytes, row order and date strings are retained. Records are not sorted by parsed timestamps or silently corrected; row offsets define the observation sequence. See [results/data_audit.json](results/data_audit.json) and [METHODOLOGY.md](METHODOLOGY.md).

## Computed results and the revised manuscript

One-hour test results at the 0.5 calibration allowance, using `origin_safe`: **11,708 eligible records, 681 peaks, 122 calendar days**. Values below come from [results/metrics.csv](results/metrics.csv).

| Method | TP | FP | Recall (%) | Precision (%) | False/day | Average precision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Persistence | 86 | 110 | 12.6 | 43.9 | 0.902 | 0.330 |
| Previous day | 29 | 148 | 4.3 | 16.4 | 1.213 | 0.142 |
| Previous week | 35 | 137 | 5.1 | 20.3 | 1.123 | 0.171 |
| Logistic regression | 99 | 65 | 14.5 | 60.4 | 0.533 | 0.405 |
| CatBoost classifier | 88 | 79 | 12.9 | 52.7 | 0.648 | 0.438 |
| CatBoost regressor | 133 | 109 | 19.5 | 55.0 | 0.893 | 0.440 |

All six rows agree with Table I of the revised manuscript, including both CatBoost models. [results/revised_manuscript_comparison.csv](results/revised_manuscript_comparison.csv) checks Table I, Table II, the stated monthly rates, TP/FP and detected-onset counts, marginal and paired confidence intervals, split sizes, and source-data counts against the revised manuscript. [results/revised_audit_summary.json](results/revised_audit_summary.json) records the coverage and status. The check uses fixed reported values in [revised_manuscript_claims.json](revised_manuscript_claims.json); it does not fit models or tune thresholds. It is a consistency check of stored outputs, not a new model-training run.

The revised manuscript specifies the `origin_safe` sample sizes: training **16,701 / 16,697 / 16,689**, calibration **5,948 / 5,944 / 5,936**, and test **11,708 / 11,704 / 11,696** records at one / two / four hours. Every horizon retains 405 calibration peaks and 681 test peaks. The one-hour classifier's monthly false-warning rates are **0.267 / 0.452 / 0.900 / 0.968** from September through December.

### Historical comparison with the earlier manuscript

The historical audit preserves the originally reported quantities without replacing them with the revised values:

| Method | Earlier manuscript recall / false per day | Reconstruction and revised manuscript recall / false per day |
| --- | --- | --- |
| CatBoost classifier | 10.6% / 0.631 | 12.9% / 0.648 |
| CatBoost regressor | 16.9% / 0.730 | 19.5% / 0.893 |

[results/manuscript_comparison.csv](results/manuscript_comparison.csv) and [results/audit_summary.json](results/audit_summary.json) refer **only to the earlier manuscript**. Their `legacy` and source-data rows directly test that earlier version; their `origin_safe` rows compare it with the modified protocol. They must not be read as an audit of the revised PIERE manuscript. They are regenerated with `python audit_results.py results`; the revised audit is regenerated separately with `python audit_revised_manuscript.py results`. Missing result files or quantities are reported, not counted as matches.

The historical CatBoost discrepancies occur under both protocols, so the boundary correction did not explain them. The reconstruction made explicit choices left ambiguous in the earlier text, including lag indexing, cyclic encodings and threshold candidates. Their actual contribution to the earlier discrepancies cannot be identified without the earlier implementation. The revised text now specifies those choices and reports this implementation's outputs. No model or threshold was tuned on test results to force agreement.

The former documentation is preserved at [commit 68b65b3](https://github.com/maksv2003/steel-peak-warning-reproducibility/tree/68b65b37b2809f37e21f22fa15a31535b3c7a6b0). An immutable link to that commit will continue to display the earlier README. When citing this documentation revision, use the full commit identifier containing it; the experiment outputs themselves are unchanged.

The supplied run still illustrates the operational tradeoff: the regressor detects more peaks than logistic regression, with more false warnings. All six primary one-hour operating points exceed the historical allowance on the test period. This does not establish plant-level savings or intervention benefits.

## Files

| File | Purpose |
| --- | --- |
| [reproduce.py](reproduce.py) | Data checks, features, fitting, calibration, evaluation and plotting |
| [audit_results.py](audit_results.py) | Historical audit against fixed earlier-manuscript values without fitting or tuning |
| [audit_revised_manuscript.py](audit_revised_manuscript.py), [revised_manuscript_claims.json](revised_manuscript_claims.json) | Separate numeric consistency audit and fixed claims from the revised manuscript |
| [METHODOLOGY.md](METHODOLOGY.md) | Explicit definitions, protocol boundaries and reconstruction decisions |
| [reproduction.ipynb](reproduction.ipynb) | Notebook companion |
| `tests/` | Checks of the implementation's core rules |
| `data/Steel_industry_data.csv` | Unmodified public source data |
| [DATA_LICENSE.md](DATA_LICENSE.md) | Dataset attribution, provenance, license and checksum |
| [SOURCES.md](SOURCES.md) | The ten external references, access notes and scope of support; the revised manuscript adds this repository as [11] |
| [references_audit.json](references_audit.json) | Detailed reference audit dated 2026-10-20 |
| `results/metrics.csv`, `monthly_metrics.csv` | All model/horizon/allowance operating points and monthly breakdowns |
| `results/predictions.csv.gz` | Calibration/test scores with origin and target row indices |
| `results/split_audit.csv`, `feature_names.json` | Sample membership and feature order |
| `results/bootstrap_intervals.csv`, `paired_recall_intervals.csv`, `bootstrap_samples.csv.gz` | Seven-day circular block-bootstrap outputs |
| [results/manuscript_comparison.csv](results/manuscript_comparison.csv), [results/audit_summary.json](results/audit_summary.json) | Historical numerical comparisons and audit summary for the earlier manuscript |
| [results/revised_manuscript_comparison.csv](results/revised_manuscript_comparison.csv), [results/revised_audit_summary.json](results/revised_audit_summary.json) | Separate comparison and audit summary for the revised manuscript |
| `results/*.png` | Operating-point and monthly false-warning figures |

