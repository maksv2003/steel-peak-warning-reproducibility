"""Reconstruct the manuscript experiment from public data, with auditable choices.

The original authors' code was unavailable. See METHODOLOGY.md before interpreting
agreement with the manuscript as evidence of exact historical reproducibility.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import platform
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
DATA_URL = 'https://archive.ics.uci.edu/static/public/851/steel+industry+energy+consumption.zip'
DATA_SHA256 = '9b1cee6f9cb9cd9df2b95814ca90a9a2ff15b7f5f1fba0fae3c643e82072eacc'
TRAIN_END, CAL_END, N_ROWS = 181 * 96, 243 * 96, 365 * 96
BUDGETS = (0.25, 0.5, 1.0)
METHODS = ('Persistence', 'Previous day', 'Previous week', 'Logistic', 'CB classifier', 'CB regressor')


def peak_onsets(peak: np.ndarray) -> np.ndarray:
    """Identify episode starts on the complete original sequence, before subsets."""
    peak = np.asarray(peak, dtype=bool)
    return peak & ~np.r_[False, peak[:-1]] if peak.size else peak.copy()


def load_data(path: Path) -> tuple[pd.DataFrame, dict]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(DATA_URL, headers={'User-Agent': 'steel-peak-warning-reproduction/1.0'})
        payload = urllib.request.urlopen(request, timeout=120).read()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            name = next(n for n in archive.namelist() if n.endswith('Steel_industry_data.csv'))
            path.write_bytes(archive.read(name))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != DATA_SHA256:
        raise ValueError(f'Data checksum mismatch: {digest}; expected {DATA_SHA256}')
    raw = pd.read_csv(path)
    assert raw.shape == (N_ROWS, 11)
    assert not raw.isna().any().any()
    expected_nsm = np.tile(np.r_[np.arange(900, 86400, 900), 0], 365)
    np.testing.assert_array_equal(raw['NSM'], expected_nsm)
    dates = pd.to_datetime(raw['date'], format='%d/%m/%Y %H:%M')
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    assert raw['Day_of_week'].tolist() == [day_names[i] for i in dates.dt.dayofweek]
    assert raw['WeekStatus'].eq('Weekend').equals(dates.dt.dayofweek.ge(5))
    audit = {
        'source_url': DATA_URL, 'source_doi': '10.24432/C52G8C',
        'license': 'CC BY 4.0', 'sha256': digest, 'rows': len(raw),
        'columns': list(raw.columns), 'missing_cells': int(raw.isna().sum().sum()),
        'timestamp_nonincreasing_steps': int((dates.diff().dropna() <= pd.Timedelta(0)).sum()),
        'time_axis': 'original row order; 96 records per source day; timestamps not corrected or sorted',
        'raw_date_first': raw['date'].iloc[0], 'raw_date_last': raw['date'].iloc[-1],
    }
    return raw, audit


def make_features(raw: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    x = raw['Usage_kWh'].astype(float)
    origins = np.arange(671, len(raw) - horizon)
    targets = origins + horizon
    cols = {}
    for k in range(24):
        cols[f'lag_{k}'] = x.shift(k).iloc[origins].to_numpy()
    for k in (47, 95, 671):
        cols[f'lag_{k}'] = x.shift(k).iloc[origins].to_numpy()
    for window in (12, 24, 96, 672):
        rolling = x.rolling(window, min_periods=window)
        for stat in ('mean', 'std', 'min', 'max'):
            series = rolling.std(ddof=1) if stat == 'std' else getattr(rolling, stat)()
            cols[f'rolling_{window}_{stat}'] = series.iloc[origins].to_numpy()
    for lag in (4, 96):
        cols[f'change_{lag}'] = (x - x.shift(lag)).iloc[origins].to_numpy()
    seconds = raw['NSM'].iloc[targets].to_numpy()
    dow = pd.to_datetime(raw['date'], format='%d/%m/%Y %H:%M').dt.dayofweek.iloc[targets].to_numpy()
    cols['target_time_sin'] = np.sin(2 * np.pi * seconds / 86400)
    cols['target_time_cos'] = np.cos(2 * np.pi * seconds / 86400)
    cols['target_weekday_sin'] = np.sin(2 * np.pi * dow / 7)
    cols['target_weekday_cos'] = np.cos(2 * np.pi * dow / 7)
    cols['target_weekend'] = (dow >= 5).astype(float)
    cols['target_previous_day'] = x.iloc[targets - 96].to_numpy()
    cols['target_previous_week'] = x.iloc[targets - 672].to_numpy()
    features = pd.DataFrame(cols)
    assert features.shape == (len(targets), 52)
    assert np.isfinite(features.to_numpy()).all()
    assert np.all(targets - 96 <= origins) and np.all(targets - 672 <= origins)
    return features, origins, targets


def split_masks(origins: np.ndarray, targets: np.ndarray, protocol: str) -> dict[str, np.ndarray]:
    masks = {
        'train': targets < TRAIN_END,
        'calibration': (targets >= TRAIN_END) & (targets < CAL_END),
        'test': targets >= CAL_END,
    }
    if protocol == 'origin_safe':
        masks['calibration'] &= origins >= TRAIN_END
        masks['test'] &= origins >= CAL_END
    elif protocol != 'legacy':
        raise ValueError(protocol)
    return masks


def select_threshold(scores: np.ndarray, y: np.ndarray, max_false: int) -> float:
    """Smallest feasible observed calibration score; accept whole tied groups."""
    scores = np.asarray(scores, dtype=float)
    y = np.asarray(y, dtype=bool)
    if not np.isfinite(scores).all():
        raise ValueError('Scores must be finite')
    candidates, group = np.unique(scores, return_inverse=True)
    false_per_group = np.bincount(group, weights=(~y).astype(int), minlength=len(candidates))
    false_at_threshold = np.cumsum(false_per_group[::-1])[::-1]
    feasible = np.flatnonzero(false_at_threshold <= max_false)
    return float(candidates[feasible[0]]) if feasible.size else float('inf')


def measure(y: np.ndarray, scores: np.ndarray, threshold: float, onset: np.ndarray, days: int) -> dict:
    alarm = scores >= threshold
    tp, fp = int(np.sum(alarm & y)), int(np.sum(alarm & ~y))
    peaks = int(y.sum())
    return {
        'records': len(y), 'peaks': peaks, 'onsets': int(onset.sum()),
        'tp': tp, 'fp': fp, 'fn': peaks - tp, 'warnings': tp + fp,
        'recall': tp / peaks if peaks else 0.,
        'precision': tp / (tp + fp) if tp + fp else 0.,
        'false_per_day': fp / days,
        'average_precision': float(average_precision_score(y, scores)),
        'onsets_detected': int(np.sum(alarm & onset)),
        'onset_recall': float(np.sum(alarm & onset) / onset.sum()) if onset.any() else 0.,
    }


def bootstrap_daily(predictions: pd.DataFrame, metrics: pd.DataFrame, n_boot: int, output: Path) -> None:
    rng = np.random.default_rng(2026)
    starts = rng.integers(0, 122, size=(n_boot, math.ceil(122 / 7)))
    indices = ((starts[:, :, None] + np.arange(7)) % 122).reshape(n_boot, -1)[:, :122]
    rows, differences = [], []
    all_samples = {}
    for protocol in ('legacy', 'origin_safe'):
        samples = {}
        for method in METHODS:
            p = predictions[(predictions.protocol == protocol) & (predictions.horizon_hours == 1) & (predictions.method == method) & (predictions.segment == 'test')]
            setting = metrics[(metrics.protocol == protocol) & (metrics.horizon_hours == 1) & (metrics.method == method) & (metrics.budget == .5)].iloc[0]
            day = p.target_row.to_numpy() // 96 - 243
            yy = p.peak.to_numpy(dtype=bool)
            alarm = p.score.to_numpy() >= float(setting.threshold)
            daily_p = np.bincount(day, weights=yy, minlength=122)
            daily_tp = np.bincount(day, weights=yy & alarm, minlength=122)
            daily_fp = np.bincount(day, weights=~yy & alarm, minlength=122)
            recall = daily_tp[indices].sum(axis=1) / daily_p[indices].sum(axis=1)
            false_day = daily_fp[indices].sum(axis=1) / 122
            samples[method] = recall
            all_samples[f'{protocol}_{method}_recall'] = recall
            all_samples[f'{protocol}_{method}_false_per_day'] = false_day
            for metric, values in [('recall', recall), ('false_per_day', false_day)]:
                lo, hi = np.quantile(values, [.025, .975], method='linear')
                rows.append({'protocol': protocol, 'method': method, 'metric': metric, 'lower': float(lo), 'upper': float(hi), 'replicates': n_boot})
        for a, b in [('CB classifier', 'Logistic'), ('CB classifier', 'CB regressor'), ('CB regressor', 'Logistic'), ('CB regressor', 'Persistence')]:
            lo, hi = np.quantile(samples[a] - samples[b], [.025, .975], method='linear')
            differences.append({'protocol': protocol, 'contrast': f'{a} minus {b}', 'lower': float(lo), 'upper': float(hi)})
    pd.DataFrame(rows).to_csv(output / 'bootstrap_intervals.csv', index=False)
    pd.DataFrame(differences).to_csv(output / 'paired_recall_intervals.csv', index=False)
    pd.DataFrame(all_samples).to_csv(output / 'bootstrap_samples.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})


def plot_results(metrics: pd.DataFrame, monthly: pd.DataFrame, output: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import warnings

    # Match the article's 4,866-twip image width so 8 pt remains 8 pt in print.
    font_path = Path('C:/Windows/Fonts/times.ttf')
    if font_path.is_file():
        font_manager.fontManager.addfont(str(font_path))
    try:
        resolved_font = font_manager.findfont(
            font_manager.FontProperties(family='Times New Roman'),
            fallback_to_default=False,
        )
        font_family = font_manager.FontProperties(fname=resolved_font).get_name()
    except ValueError:
        font_family = 'DejaVu Serif'
        warnings.warn(
            'Times New Roman is unavailable; figures use DejaVu Serif. '
            'Install Times New Roman to regenerate manuscript-compliant figures.',
            RuntimeWarning,
            stacklevel=2,
        )
    typography = {
        'font.family': font_family, 'font.size': 8,
        'axes.labelsize': 8, 'axes.titlesize': 8,
        'xtick.labelsize': 8, 'ytick.labelsize': 8,
        'legend.fontsize': 8, 'legend.title_fontsize': 8,
        'figure.titlesize': 8, 'figure.labelsize': 8,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': .6, 'axes.labelpad': 3, 'axes.axisbelow': True,
        'xtick.major.width': .6, 'ytick.major.width': .6,
        'xtick.major.pad': 2, 'ytick.major.pad': 2,
        'figure.dpi': 480, 'savefig.dpi': 480,
    }
    paper_width = 4866 / 1440
    styles = {'Persistence': ('#777777', 's'), 'Logistic': ('#0072B2', '^'), 'CB classifier': ('#D55E00', 'o'), 'CB regressor': ('#009E73', 'D')}
    with plt.rc_context(typography):
        for protocol in ('legacy', 'origin_safe'):
            fig, ax = plt.subplots(figsize=(paper_width, 2.5), constrained_layout=True)
            for method, (color, marker) in styles.items():
                subset = metrics[(metrics.protocol == protocol) & (metrics.horizon_hours == 1) & (metrics.method == method)].sort_values('budget')
                ax.plot(subset.false_per_day, subset.recall * 100, label=method,
                        color=color, marker=marker, markersize=3.2, linewidth=.9)
            ax.axvline(.5, color='#444444', linestyle=':', linewidth=.8,
                       label='Calibration allowance')
            ax.set(xlabel='False warnings per calendar day', ylabel='Peak-record recall (%)', ylim=(0, None))
            ax.grid(axis='y', alpha=.25, linewidth=.5)
            ax.legend(loc='upper left', fontsize=8, borderpad=.3,
                      labelspacing=.25, handlelength=1.5, framealpha=.95)
            fig.savefig(output / f'operating_points_{protocol}.png')
            plt.close(fig)

            subset = monthly[(monthly.protocol == protocol) & (monthly.method == 'CB classifier') & (monthly.horizon_hours == 1) & (monthly.budget == .5)].sort_values('month')
            fig, ax = plt.subplots(figsize=(paper_width, 2.15), constrained_layout=True)
            bars = ax.bar(['Sep', 'Oct', 'Nov', 'Dec'], subset.false_per_day, color='#0072B2')
            ax.bar_label(bars, fmt='%.3f', padding=-10, color='white', fontsize=8)
            ax.axhline(.5, color='#444444', linestyle='--', linewidth=.8,
                       label='Calibration allowance')
            ax.set(xlabel='Test month in 2018', ylabel='False warnings per calendar day', ylim=(0, max(1.15, subset.false_per_day.max() * 1.2)))
            ax.grid(axis='y', alpha=.25, linewidth=.5)
            ax.legend(loc='upper left', fontsize=8, borderpad=.3, handlelength=1.5)
            fig.savefig(output / f'monthly_false_warnings_{protocol}.png')
            plt.close(fig)


def run(data_path: Path, output: Path, horizons=(4, 8, 16), n_boot=2000):
    output = Path(output)
    if set(horizons) != {4, 8, 16} and output.exists() and any(output.iterdir()):
        raise ValueError(
            'Partial horizon runs require an empty output directory. '
            'Select a fresh --output path to avoid mixing new results with existing artifacts.'
        )
    raw, audit = load_data(data_path)
    output.mkdir(parents=True, exist_ok=True)
    x = raw.Usage_kWh.to_numpy(float)
    peak_cutoff = float(np.quantile(x[:TRAIN_END], .9, method='linear'))
    assert np.isclose(peak_cutoff, 85.82)
    peak = x > peak_cutoff
    onset = peak_onsets(peak)
    audit.update(peak_cutoff=peak_cutoff, calibration_peaks=int(peak[TRAIN_END:CAL_END].sum()), test_peaks=int(peak[CAL_END:].sum()), test_onsets=int(onset[CAL_END:].sum()))
    metrics_rows, prediction_frames, monthly_rows, split_rows = [], [], [], []
    month = pd.to_datetime(raw.date, format='%d/%m/%Y %H:%M').dt.month.to_numpy()
    for h in horizons:
        features, origins, targets = make_features(raw, h)
        train_mask = targets < TRAIN_END
        expected_train = TRAIN_END - 671 - h
        assert train_mask.sum() == expected_train
        common = dict(iterations=500, depth=5, learning_rate=.04, l2_leaf_reg=5, random_seed=42, thread_count=1, verbose=False, allow_writing_files=False)
        models = {
            'Logistic': make_pipeline(StandardScaler(), LogisticRegression(C=1, penalty='l2', max_iter=2000, solver='lbfgs', class_weight=None)),
            'CB classifier': CatBoostClassifier(loss_function='Logloss', **common),
            'CB regressor': CatBoostRegressor(loss_function='RMSE', **common),
        }
        all_scores = {'Persistence': x[origins], 'Previous day': x[targets - 96], 'Previous week': x[targets - 672]}
        with threadpool_limits(limits=1):
            for name, model in models.items():
                yy = x[targets[train_mask]] if name == 'CB regressor' else peak[targets[train_mask]].astype(int)
                print(f'Fitting h={h / 4:g}h {name}, n={int(train_mask.sum())}', flush=True)
                model.fit(features.loc[train_mask], yy)
                all_scores[name] = model.predict(features) if name == 'CB regressor' else model.predict_proba(features)[:, 1]
        for protocol in ('legacy', 'origin_safe'):
            masks = split_masks(origins, targets, protocol)
            for segment, mask in masks.items():
                split_rows.append({'protocol': protocol, 'horizon_hours': h / 4, 'segment': segment, 'records': int(mask.sum()), 'peaks': int(peak[targets[mask]].sum()), 'first_origin_row': int(origins[mask][0]), 'first_target_row': int(targets[mask][0]), 'last_target_row': int(targets[mask][-1])})
            cal, test = masks['calibration'], masks['test']
            for name, scores in all_scores.items():
                for segment, mask in [('calibration', cal), ('test', test)]:
                    prediction_frames.append(pd.DataFrame({'protocol': protocol, 'horizon_hours': h / 4, 'method': name, 'segment': segment, 'origin_row': origins[mask], 'target_row': targets[mask], 'source_date': raw.date.iloc[targets[mask]].to_numpy(), 'usage_kwh': x[targets[mask]], 'peak': peak[targets[mask]], 'peak_onset': onset[targets[mask]], 'score': scores[mask]}))
                for budget in BUDGETS:
                    threshold = select_threshold(scores[cal], peak[targets[cal]], math.floor(budget * 62))
                    assert int(np.sum((scores[cal] >= threshold) & ~peak[targets[cal]])) <= math.floor(budget * 62)
                    row = dict(protocol=protocol, method=name, horizon_hours=h / 4, budget=budget, threshold=threshold, calibration_fp=int(np.sum((scores[cal] >= threshold) & ~peak[targets[cal]])))
                    row.update(measure(peak[targets[test]], scores[test], threshold, onset[targets[test]], 122))
                    metrics_rows.append(row)
                    for m, days in [(9, 30), (10, 31), (11, 30), (12, 31)]:
                        mask = test & (month[targets] == m)
                        mrow = dict(protocol=protocol, method=name, horizon_hours=h / 4, budget=budget, month=m, days=days)
                        mrow.update(measure(peak[targets[mask]], scores[mask], threshold, onset[targets[mask]], days))
                        monthly_rows.append(mrow)
        print(pd.DataFrame(metrics_rows).query('protocol == "legacy" and budget == 0.5 and horizon_hours == @h / 4')[['method', 'tp', 'fp', 'recall', 'average_precision']].to_string(index=False), flush=True)
    metrics = pd.DataFrame(metrics_rows)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    monthly = pd.DataFrame(monthly_rows)
    metrics.to_csv(output / 'metrics.csv', index=False)
    monthly.to_csv(output / 'monthly_metrics.csv', index=False)
    pd.DataFrame(split_rows).to_csv(output / 'split_audit.csv', index=False)
    predictions.to_csv(output / 'predictions.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    (output / 'data_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    (output / 'feature_names.json').write_text(json.dumps(list(features.columns), indent=2), encoding='utf-8')
    import scipy, sklearn, catboost, matplotlib
    versions = {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__, 'scipy': scipy.__version__, 'scikit-learn': sklearn.__version__, 'catboost': catboost.__version__, 'matplotlib': matplotlib.__version__, 'platform': platform.platform()}
    (output / 'environment.json').write_text(json.dumps(versions, indent=2), encoding='utf-8')
    if 4 in horizons:
        bootstrap_daily(predictions, metrics, n_boot, output)
        from audit_results import audit
        audit(output)
        plot_results(metrics, monthly, output)
    print('Finished:', output, flush=True)
    return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data' / 'Steel_industry_data.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    parser.add_argument('--horizons', nargs='+', type=int, default=[4, 8, 16], choices=[4, 8, 16])
    parser.add_argument('--bootstrap', type=int, default=2000)
    args = parser.parse_args()
    run(args.data, args.output, tuple(args.horizons), args.bootstrap)
