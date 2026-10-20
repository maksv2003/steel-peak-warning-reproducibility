"""Historical audit against numeric claims in the earlier manuscript.

Reported values below preserve the earlier manuscript, not the revised PIERE version.
Use audit_revised_manuscript.py for the revised manuscript. These historical
fixtures are read-only comparison values, never model inputs.
The legacy protocol is the direct comparison with the earlier manuscript. origin_safe values
are compared for transparency but represent a deliberately modified protocol.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent


def fixtures() -> list[dict]:
    """One fixture per checked manuscript quantity, with explicit units."""
    checks = []

    def add(location, source, metric, reported, decimals, selector=None,
            scale=1, unit='count', protocol_specific=True, transform=None):
        checks.append(dict(location=location, source=source, metric=metric,
                           reported=reported, decimals=decimals,
                           selector=selector or {}, scale=scale, unit=unit,
                           protocol_specific=protocol_specific, transform=transform))

    table_i = {
        'Persistence': (12.6, 43.9, .902, .330),
        'Previous day': (4.3, 16.4, 1.213, .142),
        'Previous week': (5.1, 20.3, 1.123, .171),
        'Logistic': (14.5, 60.4, .533, .405),
        'CB classifier': (10.6, 48.3, .631, .426),
        'CB regressor': (16.9, 56.4, .730, .437),
    }
    metric_specs = [('recall', 100, 1, 'percent'), ('precision', 100, 1, 'percent'),
                    ('false_per_day', 1, 3, 'false/calendar_day'),
                    ('average_precision', 1, 3, 'score')]
    for method, values in table_i.items():
        selector = dict(method=method, horizon_hours=1, budget=.5)
        for value, (metric, scale, decimals, unit) in zip(values, metric_specs):
            add('Table I', 'metrics.csv', metric, value, decimals, selector, scale, unit)

    exact_counts = {
        'Persistence': (86, 110, 15), 'Logistic': (99, 65, 18),
        'CB classifier': (72, 77, 14), 'CB regressor': (115, 89, 22),
    }
    for method, (tp, fp, onsets) in exact_counts.items():
        selector = dict(method=method, horizon_hours=1, budget=.5)
        add('One Hour Warning Results: detected peaks', 'metrics.csv', 'tp', tp, 0, selector)
        add('One Hour Warning Results: false warnings', 'metrics.csv', 'fp', fp, 0, selector)
        add('One Hour Warning Results: detected onsets', 'metrics.csv', 'onsets_detected', onsets, 0, selector)

    table_ii = [
        (1, .25, 5.3, .295), (1, .5, 10.6, .631), (1, 1., 20.4, 1.148),
        (2, .25, .7, .705), (2, .5, 1.9, 1.393), (2, 1., 6.6, 2.115),
        (4, .25, .4, .393), (4, .5, .6, .762), (4, 1., 1.3, 1.328),
    ]
    for horizon, budget, recall, false_day in table_ii:
        selector = dict(method='CB classifier', horizon_hours=horizon, budget=budget)
        add('Table II', 'metrics.csv', 'recall', recall, 1, selector, 100, 'percent')
        add('Table II', 'metrics.csv', 'false_per_day', false_day, 3, selector, 1, 'false/calendar_day')

    for month, reported in [(9, .233), (10, .452), (11, .833), (12, 1.000)]:
        selector = dict(method='CB classifier', horizon_hours=1, budget=.5, month=month)
        add('Monthly Test Results / Figure 2', 'monthly_metrics.csv', 'false_per_day',
            reported, 3, selector, 1, 'false/calendar_day')

    intervals = {
        'Logistic': ((8.5, 22.1), (.344, .713)),
        'CB classifier': ((5.4, 17.2), (.344, 1.000)),
        'CB regressor': ((9.5, 26.8), (.385, 1.107)),
    }
    for method, (recall_interval, false_interval) in intervals.items():
        for metric, bounds, scale, decimals, unit in [
            ('recall', recall_interval, 100, 1, 'percent'),
            ('false_per_day', false_interval, 1, 3, 'false/calendar_day'),
        ]:
            for endpoint, reported in zip(('lower', 'upper'), bounds):
                add(f'One Hour Warning Results: 95% {metric} CI',
                    'bootstrap_intervals.csv', endpoint, reported, decimals,
                    dict(method=method, metric=metric), scale, unit)

    for contrast, bounds in [
        ('CB classifier minus Logistic', (-9.4, 1.5)),
        ('CB classifier minus CB regressor', (-10.7, -2.6)),
    ]:
        for endpoint, reported in zip(('lower', 'upper'), bounds):
            add('One Hour Warning Results: paired 95% recall-difference CI',
                'paired_recall_intervals.csv', endpoint, reported, 1,
                dict(contrast=contrast), 100, 'percentage_points')

    for horizon, training_count in [(1, 16701), (2, 16697), (4, 16689)]:
        for segment, records in [('train', training_count), ('calibration', 5952), ('test', 11712)]:
            selector = dict(horizon_hours=horizon, segment=segment)
            add('Chronological Protocol: sample size', 'split_audit.csv', 'records', records, 0, selector)
        for segment, peaks in [('calibration', 405), ('test', 681)]:
            add('Chronological Protocol: peak count', 'split_audit.csv', 'peaks', peaks, 0,
                dict(horizon_hours=horizon, segment=segment))

    # Global source properties are not duplicated for each evaluation protocol.
    for metric, reported, decimals, unit in [
        ('rows', 35040, 0, 'count'), ('missing_cells', 0, 0, 'count'),
        ('peak_cutoff', 85.82, 2, 'kWh'),
        ('calibration_peaks', 405, 0, 'count'), ('test_peaks', 681, 0, 'count'),
        ('test_onsets', 228, 0, 'count'),
    ]:
        add('Data and Observation Sequence / test event counts', 'data_audit.json',
            metric, reported, decimals, unit=unit, protocol_specific=False)
    add('Data and Observation Sequence: number of columns', 'data_audit.json',
        'columns', 11, 0, protocol_specific=False, transform='length')
    return checks


def _lookup(source, check: dict, protocol: str | None):
    if source is None:
        return None, 'missing_source'
    if isinstance(source, dict):
        if check['metric'] not in source:
            return None, 'missing_value'
        value = source[check['metric']]
        if check['transform'] == 'length':
            value = len(value)
    else:
        selector = dict(check['selector'])
        if protocol is not None:
            selector['protocol'] = protocol
        subset = source
        for field, wanted in selector.items():
            if field not in subset.columns:
                return None, 'missing_column'
            subset = subset[subset[field] == wanted]
        if len(subset) == 0:
            return None, 'missing_row'
        if len(subset) != 1:
            return None, 'ambiguous_rows'
        if check['metric'] not in subset.columns:
            return None, 'missing_column'
        value = subset.iloc[0][check['metric']]
    try:
        value = float(value) * check['scale']
    except (TypeError, ValueError):
        return None, 'nonnumeric_value'
    return (value, None) if math.isfinite(value) else (value, 'nonfinite_value')


def run(output: str | Path) -> pd.DataFrame:
    """Write a complete manuscript audit from existing result files; no fitting."""
    output = Path(output)
    checks = fixtures()
    sources = {}
    for filename in {check['source'] for check in checks}:
        path = output / filename
        if not path.exists():
            sources[filename] = None
        elif path.suffix == '.json':
            sources[filename] = json.loads(path.read_text(encoding='utf-8'))
        else:
            sources[filename] = pd.read_csv(path)
    rows = []
    for check in checks:
        protocols = ('legacy', 'origin_safe') if check['protocol_specific'] else (None,)
        for protocol in protocols:
            actual, error = _lookup(sources[check['source']], check, protocol)
            reported = check['reported']
            digits = check['decimals']
            matched = None
            if error is None:
                # Exact counts; other quantities compare at the printed precision.
                matched = (actual == reported) if check['unit'] == 'count' else (
                    format(actual, f'.{digits}f') == format(reported, f'.{digits}f'))
            selector = check['selector']
            comparison_role = 'modified_protocol_reference' if protocol == 'origin_safe' else 'direct_manuscript_comparison'
            rows.append({
                'protocol': protocol or 'source', 'comparison_role': comparison_role,
                'location': check['location'], 'method': selector.get('method', ''),
                'horizon_hours': selector.get('horizon_hours', ''),
                'budget': selector.get('budget', ''), 'month': selector.get('month', ''),
                'segment': selector.get('segment', ''),
                'contrast': selector.get('contrast', ''),
                'metric': check['metric'], 'interval_metric': selector.get('metric', ''),
                'unit': check['unit'], 'reported': reported, 'reported_decimals': digits,
                'recomputed': actual, 'delta': actual - reported if error is None else None,
                'matches_reported_rounding': matched,
                'status': error or ('match' if matched else 'mismatch'),
                'source_file': check['source'],
            })
    comparison = pd.DataFrame(rows)
    comparison.to_csv(output / 'manuscript_comparison.csv', index=False)
    summary = {
        'scope': 'Table I; Table II; prose confusion and onset counts; monthly rates; marginal and paired confidence intervals; split sizes and source data counts',
        'interpretation': 'legacy and source rows directly audit manuscript quantities; origin_safe rows compare a deliberately modified protocol and are not exact-replication claims',
        'original_code_available': False,
        'reported_values_used_for_fitting_or_tuning': False,
        'figures': 'Numerically stated operating points and monthly rates are covered. Unlabelled plot coordinates are not treated as independent exact numeric claims.',
        'by_protocol': {},
    }
    for protocol, group in comparison.groupby('protocol', sort=False):
        counts = group.status.value_counts().to_dict()
        summary['by_protocol'][protocol] = {
            'checked_quantities': len(group), 'status_counts': {key: int(value) for key, value in counts.items()},
        }
    direct = comparison[comparison.comparison_role == 'direct_manuscript_comparison']
    summary['all_direct_quantities_match'] = bool(direct.status.eq('match').all())
    summary['all_direct_quantities_available'] = bool(direct.status.isin(['match', 'mismatch']).all())
    (output / 'audit_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return comparison


def audit(output: str | Path) -> pd.DataFrame:
    """Notebook-facing entry point; equivalent to run(output)."""
    return run(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=ROOT / 'results', help='Directory containing computed result files')
    args = parser.parse_args()
    result = run(args.output)
    print(result.groupby(['protocol', 'status']).size().to_string())
