"""Verify that revised-manuscript checks identify changed or unavailable results."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import audit_revised_manuscript as audit


class RevisedAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='revised-audit-', dir=ROOT / 'tests')
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        fixture = json.loads((ROOT / 'revised_manuscript_claims.json').read_text(encoding='utf-8'))
        for name in {check['source'] for check in fixture['checks']}:
            shutil.copyfile(ROOT / 'results' / name, self.output / name)

    def change_recall(self, protocol):
        path = self.output / 'metrics.csv'
        with path.open(encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle))
        row = next(row for row in rows if row['protocol'] == protocol
                   and row['method'] == 'CB classifier'
                   and float(row['horizon_hours']) == 1 and float(row['budget']) == .5)
        row['recall'] = '0'
        with path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_supplied_outputs_match_all_revised_claims(self):
        summary = audit.run(self.output)
        self.assertTrue(summary['all_quantities_match'])
        self.assertEqual(summary['status_counts'], {'match': 99})

    def test_modified_origin_safe_recall_is_reported_as_mismatch(self):
        self.change_recall('origin_safe')
        summary = audit.run(self.output)
        self.assertFalse(summary['all_quantities_match'])
        self.assertTrue(summary['all_quantities_available'])
        self.assertEqual(summary['status_counts']['mismatch'], 2)  # Tables I and II.

    def test_legacy_values_do_not_enter_revised_comparison(self):
        self.change_recall('legacy')
        self.assertTrue(audit.run(self.output)['all_quantities_match'])

    def test_missing_metrics_are_not_counted_as_matches(self):
        (self.output / 'metrics.csv').unlink()
        summary = audit.run(self.output)
        self.assertFalse(summary['all_quantities_match'])
        self.assertFalse(summary['all_quantities_available'])
        self.assertEqual(summary['status_counts']['missing_source'], 54)


if __name__ == '__main__':
    unittest.main()
