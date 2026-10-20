# Methodology and reconstruction decisions

## Scope and status

This repository reconstructs the experiment described in *Early Warning of Peak Electricity Consumption in Steel Production under a False Warning Budget*. The earlier manuscript was available; its original executable code, saved predictions, and reproducibility archive were not supplied. This repository began as a new implementation of that written method. The revised PIERE manuscript now specifies and reports this implementation's `origin_safe` experiment. References below to unresolved choices or discrepancies concern the earlier manuscript; the revised numerical claims are audited separately.

Two different questions must be kept separate:

1. **Is this implementation reproducible?** The supplied data, configuration, dependency information, code, predictions, and derived outputs should allow its results to be regenerated.
2. **Does this implementation reproduce the earlier manuscript's numbers?** This requires comparison with the reported quantities. A deterministic implementation can still disagree with the manuscript because the written description leaves implementation choices unspecified, because an environment differs, or because the original analysis used a different procedure.

The reconstruction choices below are explicit. They are not established facts about the unavailable original code. Parameters and feature definitions must not be adjusted against test results merely to obtain the manuscript's numbers. Historical numerical agreements and disagreements belong in `manuscript_comparison.csv`; discrepancies must remain visible rather than being overwritten with reported values. No experimental result is asserted in this document before it has been computed.

## Source data and observation index

The source is the UCI **Steel Industry Energy Consumption** dataset, DOI [10.24432/C52G8C](https://doi.org/10.24432/C52G8C). The manuscript describes 35,040 records, 11 columns, and 365 consecutive blocks of 96 records. `Usage_kWh` is the response variable. The original data file and its checksum establish the exact input used by this implementation.

Let `x[i]` be `Usage_kWh` in original, zero-based row `i`, for `i = 0, ..., 35039`. Preserve row order and source dates. Do not sort the rows by parsed timestamps, correct dates, interpolate, remove outliers, or aggregate observations. Use the original `NSM` and `Day_of_week` values for the calendar features defined below. Data checks should report unexpected structure rather than silently repair it.

The manuscript's 15-minute observation step is represented by adjacent source rows. Its expected `NSM` sequence in each 96-record block is `900, 1800, ..., 85500, 0`. Horizons are therefore implemented as row offsets. This does not independently prove that every pair of source timestamps has the expected elapsed-time difference; any source timestamp anomalies must remain disclosed.

Define the source day index as `floor(i / 96)`. Use these original 96-record blocks for chronological partitioning and daily bootstrap units. The partition boundaries are:

| Boundary | Source day count | First row after boundary |
| --- | ---: | ---: |
| End of training | 181 | 17376 |
| End of calibration | 243 | 23328 |
| End of data | 365 | 35040 |

These correspond to the manuscript's January-June, July-August, and September-December segments. Raw calendar metadata is retained; the fixed row boundaries determine membership.

## Prediction target and peak definition

Let `o` denote a forecast origin: the latest observed row available when the prediction is made. For horizon `h`, the target row is `j = o + h`. The one-, two-, and four-hour settings use `h = 4, 8, 16`, respectively.

The regression target is `x[j]`, a single recorded 15-minute consumption value. It is not a sum, maximum, or average over the intervening horizon. The classification label is:

```text
q = linear_interpolated_90th_percentile(x[0:17376])
y[j] = 1 if x[j] > q, otherwise 0
```

The quantile is calculated from all observations in the first 181 source day blocks, including the initial history period. It is not calculated from calibration or test data, nor only from the training rows that remain after feature construction. The same computed `q` is used throughout both evaluation modes. The manuscript reports `q = 85.82 kWh`; this value is a comparison target, not a replacement for the computed quantile.

This is a distribution-based high-consumption label. It does not establish a contractual power limit, equipment protection threshold, intervention benefit, or economic saving.

## Feature specification

Only the three learned models use the full 52-feature vector. The three baselines use their individual scalar scores. All consumption features must refer to rows at or before `o`. Calendar information for the target is treated as known in advance.

Feature order is fixed as listed below. In each cyclic pair, sine precedes cosine. Within each rolling window, the order is mean, sample standard deviation, minimum, maximum.

| Group | Definition at origin `o`, target `j` | Count |
| --- | --- | ---: |
| Recent values | `x[o-k]` for `k = 0, 1, ..., 23`, in that order | 24 |
| Additional lags | `x[o-47]`, `x[o-95]`, `x[o-671]` | 3 |
| Rolling statistics | For window sizes `w = 12, 24, 96, 672`, in that order: mean, standard deviation with `ddof=1`, minimum, maximum of `x[o-w+1:o+1]` | 16 |
| Absolute changes | `x[o]-x[o-4]`, followed by `x[o]-x[o-96]` | 2 |
| Target time cycle | `sin(2*pi*NSM[j]/86400)`, `cos(2*pi*NSM[j]/86400)` | 2 |
| Target weekday cycle | `sin(2*pi*dow[j]/7)`, `cos(2*pi*dow[j]/7)` | 2 |
| Target weekend | `1` for Saturday or Sunday, otherwise `0` | 1 |
| Target-aligned seasonal values | `x[j-96]`, followed by `x[j-672]` | 2 |
| **Total** | | **52** |

Map the source `Day_of_week` labels to Monday=0, Tuesday=1, ..., Sunday=6. Derive the weekend indicator from this target weekday. All rolling windows end at and include the origin and require a complete window. No forward-looking rolling calculation or imputation is permitted. The earliest eligible origin is consequently `o = 671`.

The earlier manuscript explicitly specified sample standard deviation but did not fully specify recent-lag conventions, the meaning of "changes," weekday encoding, cyclic phase, or feature order. The choices above resolve those ambiguities for this implementation. In particular, the recent values include `x[o]`, and changes are differences in kWh rather than percentage changes.

## Models and scores

Fit each learned model independently for each horizon. Its training rows are those defined in the partition rules below. Do not refit a model on calibration observations before testing.

| Method | Score |
| --- | --- |
| Persistence | `x[o]` |
| Previous day | `x[j-96]` |
| Previous week | `x[j-672]` |
| Logistic regression | Estimated probability that `y[j]=1` |
| CatBoost classifier | Estimated probability that `y[j]=1` |
| CatBoost regressor | Predicted `x[j]` |

The seasonal baselines align to the **target** position. For example, the one-hour previous-day score is `x[o-92]`, not `x[o-96]`.

Logistic regression uses training-fitted standardization, an L2 penalty, `C=1`, an intercept, unweighted binary log loss, and a maximum of 2,000 iterations. Standardization statistics are fitted only on training features and then reused unchanged. Standard scaling uses its population-variance convention; this is distinct from the sample standard deviation used as a rolling feature.

The CatBoost classifier uses `Logloss`, and the regressor uses `RMSE`. Both use 500 trees, depth 5, learning rate 0.04, L2 regularization 5, random seed 42, and one CPU thread. Neither class weights nor sample weights are supplied. Any additional implementation defaults are governed by the recorded package versions and executable configuration; they should not be silently presented as settings specified by the manuscript.

The manuscript lists Python 3.12.14, NumPy 1.26.4, pandas 2.2.3, SciPy 1.15.1, scikit-learn 1.6.1, and CatBoost 1.2.8. The environment actually used for reconstruction must be recorded separately, including any deviation from this list.

## Evaluation modes

### `legacy`: retain the earlier manuscript's target-based partition

For eligible origins `o >= 671` and targets `j = o+h`:

```text
training:     j < 17376
calibration:  17376 <= j < 23328
test:         23328 <= j < 35040
```

This produces the following sizes by construction:

| Horizon | First training target | Training records | Calibration records | Test records |
| --- | ---: | ---: | ---: | ---: |
| 1 hour (`h=4`) | 675 | 16701 | 5952 | 11712 |
| 2 hours (`h=8`) | 679 | 16697 | 5952 | 11712 |
| 4 hours (`h=16`) | 687 | 16689 | 5952 | 11712 |

The training count is `17376-(671+h)`. Thus, the sizes match the earlier manuscript's stated indexing convention, not the revised manuscript's calibration/test sizes.

This mode has an availability limitation at segment boundaries. The first `h` origins for calibration lie in the preceding training segment; the first `h` origins for testing lie in the preceding calibration segment. For the first `h-1` of these origins, the final outcome used to fit the model or select the warning threshold occurs strictly after the forecast origin. Nonoverlapping target segments alone therefore do not establish a fully deployable chronological experiment. This limitation is retained and disclosed in `legacy` so that the written experiment can be reconstructed without silently changing its sample membership.

### `origin_safe`: the revised manuscript protocol

Keep the training targets unchanged, but require origins to occur in the new segment before making its forecasts:

```text
training:     j < 17376
calibration:  o >= 17376 and j < 23328
test:         o >= 23328 and j < 35040
```

The peak definition and fitted models are available before every calibration origin. All calibration target outcomes are available before every test origin, so the chosen warning threshold is also available. Consumption history from preceding segments remains permissible because it is observed before the forecast origin.

| Horizon | Training records | Calibration records | Test records | Initial target records omitted per later segment |
| --- | ---: | ---: | ---: | ---: |
| 1 hour (`h=4`) | 16701 | 5948 | 11708 | 4 |
| 2 hours (`h=8`) | 16697 | 5944 | 11704 | 8 |
| 4 hours (`h=16`) | 16689 | 5936 | 11696 | 16 |

These initial omitted targets are an explicit horizon warmup, not failed predictions or imputed no-warning predictions. Compute recall, precision, average precision, and onset recall using only eligible target records in the selected mode. Peak and onset denominators may consequently differ between modes and must be reported from the actual eligible records.

### Calendar-day exposure convention

Both modes retain the manuscript's fixed denominators of **62 calibration calendar days** and **122 test calendar days**. This is a calendar-day warning burden, including the initial horizon warmup in `origin_safe`; it is not a rate per 96 eligible predictions. The reduced number of eligible records in `origin_safe` is reported explicitly above.

Accordingly, the allowed calibration false-positive counts remain `floor(budget*62)`: 15, 31, and 62 at budgets 0.25, 0.5, and 1.0 false warnings per day. Using eligible-record exposure `n/96` instead would change these counts; that alternative is not silently substituted here. Monthly rates likewise use the calendar-day lengths of their test months.

## Warning-threshold selection

Select a warning threshold separately for every method, horizon, budget, and evaluation mode. Calibration and test scores must be finite. The decision is `warning = (score >= threshold)`.

Let `B = floor(budget*62)`. Define candidate thresholds as the distinct observed calibration scores together with positive infinity. For each candidate, count calibration records that both issue a warning and have `y=0`. Select the **smallest candidate threshold** whose false-positive count is at most `B`. Positive infinity provides a valid no-warning choice when necessary. Equal scores are never split to meet a budget.

Candidate-set specification matters: a threshold just above a forbidden score, calculated with a floating-point `nextafter` operation, can give identical calibration predictions but different test predictions from the next observed candidate score. The earlier manuscript did not settle this detail; the revised manuscript specifies the observed-score candidate rule. This repository uses the discrete observed-score candidate rule above and does not adjust thresholds using test outcomes.

Keep each selected threshold fixed during the corresponding test evaluation. The empirical calibration allowance is not a statistical guarantee about future false-warning rates.

## Metrics and events

For eligible targets, define TP, FP, FN, and TN from the fixed warning rule and the strict peak label. Report:

- Peak recall: `TP / (TP+FN)`.
- Precision: `TP / (TP+FP)`.
- False warnings per day: `FP / 122` on the full test segment, with the calendar-day convention above.
- Average precision: the score-based precision-recall summary, calculated before applying a warning threshold.
- Peak-onset recall: warned eligible onset records divided by all eligible onset records.

A false warning is an individual false-positive target record. Consecutive false-positive records are not merged into episodes. These counts must not be interpreted as counts of separate operator interventions without an additional event policy.

Define onset labels on the original sequence before selecting a partition or resampling:

```text
onset[j] = y[j] and not y[j-1]
```

The predecessor is the original preceding row even if it lies outside the eligible target subset. Do not create new onsets at artificial partition or bootstrap block boundaries.

## Paired circular moving-block bootstrap

The manuscript's primary uncertainty analysis concerns one-hour test performance at the calibration budget of 0.5 false warnings per day. Preserve each fitted model and selected threshold during bootstrap resampling; the intervals are conditional on those fitted objects and do not include training or calibration uncertainty.

Use the following explicit reconstruction:

1. Form daily test counts for the 122 original test day blocks, retaining the original day memberships. In `origin_safe`, the first day contains only its eligible targets; it remains one calendar day under the stated exposure convention.
2. Initialize NumPy `default_rng(2026)`.
3. For each of 2,000 replicates, draw 18 block-start indices independently and uniformly from `0, ..., 121`.
4. Expand every start into seven consecutive day indices, wrapping modulo 122. Concatenate the 18 blocks in drawn order and retain their first 122 day indices.
5. Use this same day-index sequence for every model and every paired comparison in the replicate. Repeated days contribute repeated counts.
6. Calculate recall as `sum(TP)/sum(positive_targets)`, not as the unweighted average of daily recall. Calculate false warnings per day as `sum(FP)/122`.
7. Calculate paired recall differences within the same replicate. The revised manuscript's named comparisons are classifier minus logistic regression, classifier minus regressor, and regressor minus logistic regression.
8. Report the 0.025 and 0.975 quantiles of the replicate values using linear quantile interpolation.

The RNG API, block assembly and truncation, and quantile convention were reconstruction choices not fully specified by the earlier manuscript's seed and block length alone. The revised manuscript now states this full procedure. A seed does not make two different bootstrap algorithms identical.

Circular block resampling preserves some local temporal dependence but does not establish stationarity or generalization to other plants or years. Month-to-month changes in the data limit the interpretation of its intervals. An observed test false-warning rate above a budget and evidence that an underlying expected rate exceeds that budget are distinct claims. Likewise, the largest observed metric value is not by itself evidence of a statistically significant model advantage.

## Interpreting outputs and comparisons

Keep results from `legacy` and `origin_safe` distinguishable in all outputs. Use `origin_safe` for direct comparison with the revised manuscript. Use `legacy` for the historical comparison with the earlier manuscript's target-based sample sizes and metrics. Its different sample membership means that it is not the protocol reported in the revised manuscript.

Record actual confusion counts, eligible sample sizes, peak and onset counts, selected thresholds, daily and monthly counts, model scores, and environment information alongside rounded display metrics. The manuscript reports many quantities only to limited precision. Comparison should identify both the reported precision and the actual computed value, rather than claim exact equality from rounded values alone.

`manuscript_comparison.csv` is the historical audit of the earlier manuscript. `revised_manuscript_comparison.csv` is the separate numerical audit of the revised manuscript, using fixed claims in `revised_manuscript_claims.json` and the `origin_safe` outputs. Agreement there supports only the quantities actually checked; disagreement is a finding to investigate and disclose. Neither successful script execution nor matching a few headline numbers establishes that all original results have been reproduced.
