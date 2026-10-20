"""Check revised-manuscript claims against existing origin_safe result files.

This audit does not fit models, select thresholds, or change result files.
The earlier-manuscript audit remains available separately in audit_results.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(output: str | Path) -> dict:
    output = Path(output)
    fixture = json.loads((ROOT / 'revised_manuscript_claims.json').read_text(encoding='utf-8'))
    sources = {}
    for check in fixture['checks']:
        filename = check['source']
        if filename in sources:
            continue
        path = output / filename
        if not path.exists():
            sources[filename] = None
        elif path.suffix == '.json':
            sources[filename] = json.loads(path.read_text(encoding='utf-8'))
        else:
            with path.open(encoding='utf-8', newline='') as handle:
                sources[filename] = list(csv.DictReader(handle))

    rows = []
    for check in fixture['checks']:
        source = sources[check['source']]
        selector = dict(check['selector'])
        if check['protocol_specific']:
            selector['protocol'] = 'origin_safe'
        actual, error = None, None
        if source is None:
            error = 'missing_source'
        else:
            if isinstance(source, list):
                candidates = []
                for row in source:
                    matches = True
                    for key, wanted in selector.items():
                        if key not in row:
                            matches = False
                        elif isinstance(wanted, (int, float)):
                            matches &= float(row[key]) == wanted
                        else:
                            matches &= row[key] == wanted
                    if matches:
                        candidates.append(row)
                if len(candidates) != 1:
                    error = 'missing_row' if not candidates else 'ambiguous_rows'
                else:
                    source = candidates[0]
            if error is None:
                if check['metric'] not in source:
                    error = 'missing_value'
                else:
                    value = source[check['metric']]
                    if check['transform'] == 'length':
                        value = len(value)
                    try:
                        actual = float(value) * check['scale']
                        if not math.isfinite(actual):
                            error = 'nonfinite_value'
                    except (TypeError, ValueError):
                        error = 'nonnumeric_value'
        digits = check['decimals']
        reported = check['reported']
        matches = error is None and (
            actual == reported if check['unit'] == 'count'
            else format(actual, f'.{digits}f') == format(reported, f'.{digits}f')
        )
        rows.append({
            'manuscript_version': fixture['manuscript_version'],
            'protocol': 'origin_safe' if check['protocol_specific'] else 'source',
            'location': check['location'],
            'selector': json.dumps(selector, sort_keys=True),
            'metric': check['metric'], 'unit': check['unit'],
            'reported': reported, 'reported_decimals': digits,
            'recomputed': actual,
            'status': error or ('match' if matches else 'mismatch'),
            'source_file': check['source'],
        })

    with (output / 'revised_manuscript_comparison.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = {}
    for row in rows:
        counts[row['status']] = counts.get(row['status'], 0) + 1
    summary = {
        'manuscript_version': fixture['manuscript_version'],
        'fixture_source': fixture['source'],
        'scope': fixture['scope'],
        'interpretation': 'Direct comparison with revised-manuscript claims using origin_safe and source-data outputs; no comparison with legacy results.',
        'reported_values_used_for_fitting_or_tuning': False,
        'checked_quantities': len(rows),
        'status_counts': counts,
        'all_quantities_match': all(row['status'] == 'match' for row in rows),
        'all_quantities_available': all(row['status'] in ('match', 'mismatch') for row in rows),
    }
    (output / 'revised_audit_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=ROOT / 'results')
    args = parser.parse_args()
    summary = run(args.output)
    print(json.dumps(summary['status_counts'], sort_keys=True))
    raise SystemExit(0 if summary['all_quantities_match'] else 1)
