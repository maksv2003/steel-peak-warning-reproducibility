"""Protocol checks using synthetic records; no model training or network access."""
from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import reproduce as rp


def synthetic_raw(n=1200):
    row = np.arange(n)
    seconds = ((row % 96 + 1) * 900) % 86400
    dates = pd.Timestamp('2018-01-01') + pd.to_timedelta(row // 96, unit='D') + pd.to_timedelta(seconds, unit='s')
    return pd.DataFrame({
        'Usage_kWh': 20 + np.sin(row / 13) + row / 1000,
        'NSM': seconds,
        'date': dates.strftime('%d/%m/%Y %H:%M'),
        'Day_of_week': dates.day_name(),
    })


class FeatureTests(unittest.TestCase):
    def test_future_consumption_cannot_change_features_at_origin(self):
        raw = synthetic_raw()
        for h in (4, 8, 16):
            expected, origins, _ = rp.make_features(raw, h)
            for origin in (671, 703, 1000):
                with self.subTest(horizon=h, origin=origin):
                    modified = raw.copy()
                    modified.loc[origin + 1:, 'Usage_kWh'] = 1e7 + np.arange(len(raw) - origin - 1)
                    actual, _, _ = rp.make_features(modified, h)
                    where = np.flatnonzero(origins == origin)[0]
                    np.testing.assert_allclose(actual.iloc[where], expected.iloc[where], rtol=0, atol=1e-12)

    def test_history_window_and_target_alignment_have_exact_boundaries(self):
        raw = synthetic_raw()
        raw['Usage_kWh'] = np.arange(len(raw), dtype=float)
        for h in (4, 8, 16):
            features, origins, targets = rp.make_features(raw, h)
            self.assertEqual(features.shape[1], 52)
            self.assertEqual(origins[0], 671)
            self.assertEqual(targets[0], 671 + h)
            first = features.iloc[0]
            self.assertEqual(first['lag_0'], 671)
            self.assertEqual(first['lag_23'], 648)
            self.assertEqual(first['lag_671'], 0)
            self.assertEqual(first['rolling_672_min'], 0)
            self.assertEqual(first['rolling_672_max'], 671)
            self.assertEqual(first['rolling_672_mean'], 335.5)
            self.assertAlmostEqual(first['rolling_672_std'], np.std(np.arange(672), ddof=1))
            self.assertNotAlmostEqual(first['rolling_672_std'], np.std(np.arange(672), ddof=0))
            self.assertEqual(first['change_4'], 4)
            self.assertEqual(first['change_96'], 96)
            self.assertEqual(first['target_previous_day'], 671 + h - 96)
            self.assertEqual(first['target_previous_week'], h - 1)
            self.assertLessEqual(671 + h - 96, origins[0])
            self.assertLessEqual(671 + h - 672, origins[0])

    def test_calendar_is_for_target_not_origin_at_midnight_and_weekend(self):
        raw = synthetic_raw()
        # Source day 11 is Friday; this horizon moves into Saturday.
        features, origins, targets = rp.make_features(raw, 16)
        origin = 12 * 96 - 5
        pos = np.flatnonzero(origins == origin)[0]
        target = targets[pos]
        self.assertEqual(pd.to_datetime(raw.date.iloc[origin], dayfirst=True).dayofweek, 4)
        self.assertEqual(pd.to_datetime(raw.date.iloc[target], dayfirst=True).dayofweek, 5)
        self.assertEqual(features.target_weekend.iloc[pos], 1)
        self.assertAlmostEqual(features.target_weekday_sin.iloc[pos], math.sin(2 * math.pi * 5 / 7))
        self.assertAlmostEqual(features.target_time_cos.iloc[pos], math.cos(2 * math.pi * raw.NSM.iloc[target] / 86400))


class PartitionTests(unittest.TestCase):
    def test_counts_disjointness_and_origin_availability(self):
        for h, n_train in ((4, 16701), (8, 16697), (16, 16689)):
            with self.subTest(horizon=h):
                origins = np.arange(671, rp.N_ROWS - h)
                targets = origins + h
                legacy = rp.split_masks(origins, targets, 'legacy')
                safe = rp.split_masks(origins, targets, 'origin_safe')
                self.assertEqual(legacy['train'].sum(), n_train)
                self.assertEqual(legacy['calibration'].sum(), 5952)
                self.assertEqual(legacy['test'].sum(), 11712)
                self.assertEqual(safe['calibration'].sum(), 5952 - h)
                self.assertEqual(safe['test'].sum(), 11712 - h)
                np.testing.assert_array_equal(safe['train'], legacy['train'])
                self.assertEqual(origins[safe['calibration']][0], rp.TRAIN_END)
                self.assertEqual(origins[safe['test']][0], rp.CAL_END)
                self.assertLess(targets[safe['train']][-1], origins[safe['calibration']][0])
                self.assertLess(targets[safe['calibration']][-1], origins[safe['test']][0])
                self.assertEqual(np.sum(origins[legacy['calibration']] < rp.TRAIN_END - 1), h - 1)
                self.assertEqual(np.sum(origins[legacy['test']] < rp.CAL_END - 1), h - 1)
                for masks in (legacy, safe):
                    multiplicity = sum(mask.astype(int) for mask in masks.values())
                    self.assertTrue(np.all(multiplicity <= 1))
                self.assertTrue(np.all(~safe['calibration'] | legacy['calibration']))
                self.assertTrue(np.all(~safe['test'] | legacy['test']))

    def test_unknown_protocol_fails(self):
        with self.assertRaises(ValueError):
            rp.split_masks(np.array([671]), np.array([675]), 'unknown')


class ThresholdTests(unittest.TestCase):
    def test_ties_budget_minimality_and_permutation_invariance(self):
        scores = np.array([.1, .2, .2, .4, .4, .4, .9, .9, 1.])
        y = np.array([False, True, False, False, True, False, True, False, False])
        permutation = np.array([8, 3, 6, 0, 5, 4, 1, 7, 2])
        candidates = np.r_[np.unique(scores), np.inf]
        for budget in range(7):
            with self.subTest(budget=budget):
                threshold = rp.select_threshold(scores, y, budget)
                self.assertIn(threshold, candidates)
                alarms = scores >= threshold
                self.assertLessEqual(np.count_nonzero(alarms & ~y), budget)
                for lower in candidates[candidates < threshold]:
                    self.assertGreater(np.count_nonzero((scores >= lower) & ~y), budget)
                for score in np.unique(scores):
                    self.assertEqual(len(np.unique(alarms[scores == score])), 1)
                self.assertEqual(threshold, rp.select_threshold(scores[permutation], y[permutation], budget))

    def test_infinite_threshold_can_be_necessary_and_all_positive_is_permitted(self):
        self.assertTrue(math.isinf(rp.select_threshold(np.array([.7, .7]), np.array([True, False]), 0)))
        self.assertEqual(rp.select_threshold(np.array([.2, .7]), np.array([True, True]), 0), .2)

    def test_nonfinite_scores_are_rejected(self):
        for invalid in (np.nan, np.inf, -np.inf):
            with self.subTest(score=invalid), self.assertRaises(ValueError):
                rp.select_threshold(np.array([.3, invalid]), np.array([True, False]), 1)


class MetricTests(unittest.TestCase):
    def test_onset_uses_original_predecessor_before_subset_and_warmup(self):
        peak = np.zeros(rp.CAL_END + 30, dtype=bool)
        peak[rp.CAL_END - 1:rp.CAL_END + 18] = True
        peak[rp.CAL_END + 22:rp.CAL_END + 24] = True
        onset = rp.peak_onsets(peak)
        self.assertTrue(onset[rp.CAL_END - 1])
        for first_target in (rp.CAL_END, rp.CAL_END + 4, rp.CAL_END + 8, rp.CAL_END + 16):
            selected = np.arange(first_target, len(peak))
            self.assertTrue(peak[selected[0]])
            self.assertFalse(onset[selected[0]])
            self.assertEqual(onset[selected].sum(), 1)
            self.assertTrue(onset[rp.CAL_END + 22])

    def test_calendar_day_denominator_not_eligible_record_exposure(self):
        y = np.array([True, True, False, False, False])
        scores = np.array([.9, .1, .8, .7, .2])
        onset = np.array([True, False, False, False, False])
        result = rp.measure(y, scores, .5, onset, 122)
        self.assertEqual(result['tp'], 1)
        self.assertEqual(result['fp'], 2)
        self.assertEqual(result['fn'], 1)
        self.assertEqual(result['recall'], .5)
        self.assertAlmostEqual(result['precision'], 1 / 3)
        self.assertAlmostEqual(result['false_per_day'], 2 / 122)
        self.assertEqual(result['onset_recall'], 1)
        monthly = rp.measure(y, scores, .5, onset, 30)
        self.assertAlmostEqual(monthly['false_per_day'], 2 / 30)

    def test_no_warning_precision_and_counts(self):
        y = np.array([True, False])
        result = rp.measure(y, np.array([.2, .4]), np.inf, y.copy(), 122)
        for field in ('tp', 'fp', 'warnings', 'recall', 'precision', 'false_per_day', 'onsets_detected', 'onset_recall'):
            self.assertEqual(result[field], 0)


class BootstrapTests(unittest.TestCase):
    def test_shared_circular_indices_micro_recall_and_calendar_exposure(self):
        records, settings, daily_reference = [], [], {}
        for protocol in ('legacy', 'origin_safe'):
            for method_number, method in enumerate(rp.METHODS):
                daily_p, daily_tp, daily_fp = np.zeros(122), np.zeros(122), np.zeros(122)
                for day in range(122):
                    entries = [(slot, True, slot < ((day + method_number) % 4)) for slot in range(1 + day % 3)]
                    entries += [(10, False, (day + method_number) % 5 == 0)]
                    for slot, is_peak, alarm in entries:
                        if protocol == 'origin_safe' and day == 0 and slot < 4:
                            continue
                        records.append(dict(protocol=protocol, horizon_hours=1, method=method, segment='test', target_row=rp.CAL_END + day * 96 + slot, peak=is_peak, score=float(alarm)))
                        daily_p[day] += is_peak
                        daily_tp[day] += is_peak and alarm
                        daily_fp[day] += not is_peak and alarm
                settings.append(dict(protocol=protocol, horizon_hours=1, method=method, budget=.5, threshold=.5))
                daily_reference[(protocol, method)] = (daily_p, daily_tp, daily_fp)
        n_boot = 32
        rng = np.random.default_rng(2026)
        selected_days = []
        for _ in range(n_boot):
            days = []
            for start in rng.integers(0, 122, size=18):
                days.extend((int(start) + step) % 122 for step in range(7))
            selected_days.append(days[:122])
        selected_days = np.array(selected_days)
        with tempfile.TemporaryDirectory(prefix='protocol-test-', dir=Path(__file__).resolve().parent) as directory:
            output = Path(directory)
            rp.bootstrap_daily(pd.DataFrame(records), pd.DataFrame(settings), n_boot, output)
            samples = pd.read_csv(output / 'bootstrap_samples.csv.gz')
            intervals = pd.read_csv(output / 'paired_recall_intervals.csv')
            expected_recalls = {}
            for (protocol, method), (peaks, tp, fp) in daily_reference.items():
                expected_recall = tp[selected_days].sum(axis=1) / peaks[selected_days].sum(axis=1)
                expected_recalls[(protocol, method)] = expected_recall
                expected_false = fp[selected_days].sum(axis=1) / 122
                np.testing.assert_allclose(samples[f'{protocol}_{method}_recall'], expected_recall, rtol=0, atol=1e-14)
                np.testing.assert_allclose(samples[f'{protocol}_{method}_false_per_day'], expected_false, rtol=0, atol=1e-14)
            for protocol in ('legacy', 'origin_safe'):
                delta = expected_recalls[(protocol, 'CB classifier')] - expected_recalls[(protocol, 'Logistic')]
                expected_interval = np.quantile(delta, [.025, .975], method='linear')
                actual = intervals[(intervals.protocol == protocol) & (intervals.contrast == 'CB classifier minus Logistic')].iloc[0]
                np.testing.assert_allclose([actual.lower, actual.upper], expected_interval, rtol=0, atol=1e-14)


if __name__ == '__main__':
    unittest.main()
