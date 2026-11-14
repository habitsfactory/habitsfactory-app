"""Insights: the correlation model, its API and the nightly computation."""

import unittest
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command

from ..models import Completion, HabitCorrelation
from ..serializers import HabitCorrelationSerializer
from .base import HabitApiTestCase

try:  # the computation needs the scientific stack
    import numpy as np
    from ..management.commands.compute_correlations import (
        benjamini_hochberg,
        build_series,
        correlate,
    )
except ImportError:  # pragma: no cover
    np = None

needs_numpy = unittest.skipIf(np is None, "numpy / scipy are not installed")


class CorrelationFixtureMixin:
    def correlation(self, habit1, habit2, user=None, **coefficients):
        return HabitCorrelation.objects.create(
            user=user or self.user,
            habit1=habit1,
            habit2=habit2,
            sample_size=20,
            start_date=self.today - timedelta(days=30),
            end_date=self.today - timedelta(days=1),
            **coefficients,
        )


class CorrelationModelTests(CorrelationFixtureMixin, HabitApiTestCase):
    def strength(self, **coefficients):
        a, b = self.make_habit("A"), self.make_habit("B")
        return float(self.correlation(a, b, **coefficients).max_correlation)

    def test_strength_is_the_spearman_coefficient(self):
        # Pearson is stored for reference only: an outlier can inflate it
        self.assertEqual(self.strength(pearson_coefficient="0.99", spearman_coefficient="0.6"), 0.6)

    def test_negative_coefficients_count_by_magnitude(self):
        self.assertEqual(self.strength(spearman_coefficient="-0.9"), 0.9)

    def test_direction(self):
        a, b, c = self.make_habit("A"), self.make_habit("B"), self.make_habit("C")
        self.assertEqual(self.correlation(a, b, spearman_coefficient="0.9").direction, "positive")
        self.assertEqual(self.correlation(a, c, spearman_coefficient="-0.9").direction, "negative")

    def test_rows_from_the_old_analysis_still_get_a_score(self):
        self.assertEqual(self.strength(pearson_coefficient="-0.7"), 0.7)
        HabitCorrelation.objects.all().delete()
        self.user.habits.all().delete()
        self.assertEqual(self.strength(dtw_distance="0.25"), 0.75)

    def test_no_coefficient_means_zero(self):
        self.assertEqual(self.strength(), 0.0)

    def test_is_recomputed_on_every_save(self):
        correlation = self.correlation(self.make_habit("A"), self.make_habit("B"), spearman_coefficient="0.4")
        correlation.spearman_coefficient = Decimal("0.95")
        correlation.save()
        correlation.refresh_from_db()
        self.assertEqual(float(correlation.max_correlation), 0.95)


class CorrelationSerializerTests(CorrelationFixtureMixin, HabitApiTestCase):
    def serialize(self, coefficient):
        run, mood = self.make_habit("Run"), self.make_habit("Mood", "rating")
        return HabitCorrelationSerializer(self.correlation(run, mood, spearman_coefficient=coefficient)).data

    def test_strength_buckets(self):
        expected = {
            "0.95": "very_strong", "0.9": "very_strong",
            "0.8": "strong", "0.7": "strong",
            "0.6": "moderate", "0.5": "moderate",
            "0.4": "weak", "0.3": "weak",
            "0.1": "very_weak",
        }
        for index, (coefficient, strength) in enumerate(expected.items()):
            a, b = self.make_habit(f"A{index}"), self.make_habit(f"B{index}")
            data = HabitCorrelationSerializer(self.correlation(a, b, spearman_coefficient=coefficient)).data
            self.assertEqual(data["strength"], strength, coefficient)

    def test_payload_shape(self):
        data = self.serialize("0.8")

        self.assertEqual(data["habit1"]["name"], "Run")
        self.assertEqual(data["habit2"]["habit_type"], "rating")
        self.assertIsNone(data["habit1"]["category_name"])
        self.assertEqual(float(data["max_correlation"]), 0.8)
        self.assertEqual(data["sample_size"], 20)

    def test_description_names_both_habits_and_follows_the_direction(self):
        seen = set()
        for coefficient in ["0.95", "0.6", "0.3", "-0.3", "-0.6", "-0.95"]:
            data = self.serialize(coefficient)
            self.assertIn("Run", data["description"])
            self.assertIn("Mood", data["description"])
            self.assertEqual(data["direction"], "negative" if coefficient.startswith("-") else "positive")
            self.assertEqual("opposite" in data["description"] or "down" in data["description"], coefficient.startswith("-"))
            seen.add(data["description"])
            HabitCorrelation.objects.all().delete()
            self.user.habits.all().delete()
        self.assertEqual(len(seen), 6)


class CorrelationApiTests(CorrelationFixtureMixin, HabitApiTestCase):
    def setUp(self):
        super().setUp()
        self.habits = [self.make_habit(name) for name in "ABCD"]
        a, b, c, d = self.habits
        self.correlation(a, b, spearman_coefficient="0.95")
        self.correlation(a, c, spearman_coefficient="0.75")
        self.correlation(b, c, spearman_coefficient="0.55")
        self.correlation(c, d, spearman_coefficient="0.2")
        x, y = self.make_habit("X", user=self.other), self.make_habit("Y", user=self.other)
        self.correlation(x, y, user=self.other, spearman_coefficient="0.99")

    def strengths(self, **params):
        response = self.client.get("/api/correlations/", params)
        self.assertEqual(response.status_code, 200)
        return [float(i["max_correlation"]) for i in response.data["insights"]]

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/correlations/").status_code, 401)

    def test_lists_my_strongest_pairs_first(self):
        self.assertEqual(self.strengths(), [0.95, 0.75, 0.55])  # default threshold 0.5

    def test_threshold_and_limit(self):
        self.assertEqual(self.strengths(min_correlation=0.7), [0.95, 0.75])
        self.assertEqual(self.strengths(min_correlation=0), [0.95, 0.75, 0.55, 0.2])
        self.assertEqual(self.strengths(min_correlation=0, limit=2), [0.95, 0.75])

    def test_parameters_are_clamped_or_defaulted(self):
        self.assertEqual(self.strengths(limit=0, min_correlation=0), [0.95])
        self.assertEqual(self.strengths(limit=9999, min_correlation=-3), [0.95, 0.75, 0.55, 0.2])
        self.assertEqual(self.strengths(limit="abc", min_correlation="xyz"), [0.95, 0.75, 0.55])
        self.assertEqual(self.strengths(min_correlation=5), [])

    def test_reports_the_filters_used(self):
        data = self.client.get("/api/correlations/", {"limit": 3, "min_correlation": 0.6}).data
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["filters"], {"min_correlation": 0.6, "limit": 3})

    def test_summary(self):
        data = self.client.get("/api/correlations/summary/").data

        self.assertTrue(data["has_data"])
        self.assertEqual(data["total_correlations"], 4)
        self.assertEqual(data["strongest_correlation"], {"habit1": "A", "habit2": "B", "correlation": 0.95})
        self.assertEqual(data["distribution"], {"very_strong": 1, "strong": 1, "moderate": 1, "weak": 1})

    def test_summary_without_data(self):
        self.client.force_authenticate(self.admin)
        data = self.client.get("/api/correlations/summary/").data
        self.assertEqual((data["has_data"], data["total_correlations"]), (False, 0))

    def test_for_habit_matches_either_side_of_the_pair(self):
        c = self.habits[2]

        data = self.client.get(f"/api/correlations/for-habit/{c.id}/").data

        self.assertEqual(data["habit_id"], c.id)
        self.assertEqual([float(i["max_correlation"]) for i in data["insights"]], [0.75, 0.55, 0.2])

    def test_for_habit_with_nothing_to_show(self):
        foreign = self.other.habits.first()
        for target in [foreign.id, 999999, "abc"]:
            response = self.client.get(f"/api/correlations/for-habit/{target}/")
            self.assertEqual(response.status_code, 200, target)
            self.assertEqual(response.data["insights"], [], target)

    def test_deleting_a_habit_removes_its_correlations(self):
        self.habits[0].delete()
        self.assertEqual(HabitCorrelation.objects.filter(user=self.user).count(), 2)


@needs_numpy
class CorrelationMathTests(unittest.TestCase):
    DAYS = [date(2026, 1, 1) + timedelta(days=i) for i in range(6)]

    def series(self, habit_type, logged, first_logged=DAYS[0]):
        values = {self.DAYS[i]: v for i, v in logged.items()}
        return build_series(habit_type, values, self.DAYS, first_logged).tolist()

    def assert_series(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for got, want in zip(actual, expected):
            if want is None:
                self.assertTrue(np.isnan(got), actual)
            else:
                self.assertEqual(got, want, actual)

    def test_a_blank_day_means_not_done_for_yes_no_and_counter_habits(self):
        self.assert_series(self.series("boolean", {0: 1, 3: 1}), [1, 0, 0, 1, 0, 0])
        self.assert_series(self.series("counter", {1: 4}), [0, 4, 0, 0, 0, 0])

    def test_a_blank_day_means_unknown_for_measurements(self):
        for habit_type in ["value", "rating", "percentage"]:
            self.assert_series(self.series(habit_type, {1: 7.5, 4: 8}), [None, 7.5, None, None, 8, None])

    def test_days_before_the_habit_existed_are_unknown(self):
        started = self.DAYS[2]
        self.assert_series(self.series("boolean", {2: 1, 4: 1}, first_logged=started), [None, None, 1, 0, 1, 0])

    def test_a_habit_first_logged_before_the_window_counts_from_day_one(self):
        self.assert_series(self.series("boolean", {}, first_logged=date(2025, 6, 1)), [0, 0, 0, 0, 0, 0])

    def compare(self, x, y, min_sample_size=4):
        return correlate(np.array(x, dtype=float), np.array(y, dtype=float), min_sample_size)

    def test_identical_and_opposite_series(self):
        pattern = [1, 0, 1, 1, 0, 0, 1, 0, 1, 0]
        spearman, p_value, pearson, days = self.compare(pattern, pattern)
        self.assertAlmostEqual(spearman, 1.0)
        self.assertAlmostEqual(pearson, 1.0)
        self.assertLess(p_value, 0.001)
        self.assertEqual(days, 10)

        spearman, _, pearson, _ = self.compare(pattern, [1 - v for v in pattern])
        self.assertAlmostEqual(spearman, -1.0)
        self.assertAlmostEqual(pearson, -1.0)

    def test_rank_correlation_ignores_the_scale(self):
        hours = [5, 6, 7, 8, 9, 10, 11, 12]
        score = [h ** 3 for h in hours]  # monotonic, far from linear
        spearman, _, pearson, _ = self.compare(hours, score)
        self.assertAlmostEqual(spearman, 1.0)
        self.assertLess(pearson, 0.99)

    def test_only_days_known_for_both_are_compared(self):
        nan = float("nan")
        x = [1, 0, 1, 0, 1, 0, nan, nan]
        y = [nan, nan, 1, 0, 1, 0, 1, 0]
        self.assertEqual(self.compare(x, y)[3], 4)

    def test_not_comparable(self):
        ramp = list(range(10))
        self.assertIsNone(self.compare(ramp, [3] * 10))  # one never changes
        self.assertIsNone(self.compare([1] * 10, ramp))
        self.assertIsNone(self.compare(ramp[:3], ramp[:3]))  # too few days
        self.assertIsNone(self.compare(ramp, ramp, min_sample_size=11))

    def test_benjamini_hochberg(self):
        self.assertEqual(benjamini_hochberg([]), [])
        self.assertEqual(benjamini_hochberg([0.01]), [True])
        self.assertEqual(benjamini_hochberg([0.2]), [False])
        # 0.04 would pass alone, but not as one of four tests...
        self.assertEqual(benjamini_hochberg([0.04, 0.5, 0.6, 0.7]), [False, False, False, False])
        # ...whereas a group of small p-values supports each other
        self.assertEqual(benjamini_hochberg([0.03, 0.001, 0.02, 0.9]), [True, True, True, False])

    def test_random_habits_produce_almost_no_false_insights(self):
        rng = np.random.default_rng(42)
        habits = [rng.integers(0, 2, size=90).astype(float) for _ in range(28)]
        p_values = [
            correlate(habits[i], habits[j], 10)[1]
            for i in range(28)
            for j in range(i + 1, 28)
        ]

        naive = sum(p < 0.05 for p in p_values)
        kept = sum(benjamini_hochberg(p_values))

        self.assertGreater(naive, 8)  # plain p < 0.05 lets ~5% of 378 pairs through
        self.assertLessEqual(kept, 1)


@needs_numpy
class ComputeCorrelationsCommandTests(HabitApiTestCase):
    DAYS = 20

    def series(self, habit, values):
        """Log one value per day, ending yesterday (the command ignores today)."""
        for offset, value in enumerate(reversed(values), start=1):
            if value is not None:
                Completion.objects.create(habit=habit, date=self.today - timedelta(days=offset), value=value)

    def run_command(self, *args):
        out = StringIO()
        call_command("compute_correlations", *args, stdout=out)
        return out.getvalue()

    def pair(self, habit1, habit2):
        return HabitCorrelation.objects.filter(habit1=habit1, habit2=habit2).first()

    def test_habits_done_on_the_same_days_correlate_perfectly(self):
        pattern = [1, 0] * (self.DAYS // 2)
        run, stretch = self.make_habit("Run"), self.make_habit("Stretch")
        self.series(run, pattern)
        self.series(stretch, pattern)

        output = self.run_command()

        correlation = self.pair(run, stretch)
        self.assertIsNotNone(correlation, output)
        self.assertEqual(correlation.user, self.user)
        self.assertEqual(float(correlation.spearman_coefficient), 1.0)
        self.assertEqual(float(correlation.max_correlation), 1.0)
        self.assertEqual(correlation.sample_size, self.DAYS)
        self.assertEqual(correlation.end_date, self.today - timedelta(days=1))
        self.assertIn("alice: 1 correlations", output)

    def test_opposite_habits_correlate_negatively(self):
        pattern = [1, 0] * (self.DAYS // 2)
        early, late = self.make_habit("Early night"), self.make_habit("Late night")
        self.series(early, pattern)
        self.series(late, [1 - v for v in pattern])

        self.run_command()

        correlation = self.pair(early, late)
        self.assertEqual(float(correlation.spearman_coefficient), -1.0)
        self.assertEqual(float(correlation.max_correlation), 1.0)

    def test_numeric_habits_get_a_pearson_coefficient_too(self):
        steps, distance = self.make_habit("Steps", "counter"), self.make_habit("Distance", "value")
        self.series(steps, list(range(1, self.DAYS + 1)))
        self.series(distance, [v * 0.7 + 1 for v in range(1, self.DAYS + 1)])

        self.run_command()

        correlation = self.pair(steps, distance)
        self.assertAlmostEqual(float(correlation.pearson_coefficient), 1.0, places=3)
        self.assertAlmostEqual(float(correlation.spearman_coefficient), 1.0, places=3)
        self.assertIsNone(correlation.dtw_distance)

    def test_unrelated_habits_are_not_stored(self):
        a, b = self.make_habit("A", "value"), self.make_habit("B", "value")
        self.series(a, list(range(1, 11)))
        self.series(b, [3, 9, 1, 7, 2, 8, 4, 6, 5, 5])

        self.run_command()

        self.assertEqual(HabitCorrelation.objects.count(), 0)

    def test_running_twice_updates_instead_of_duplicating(self):
        pattern = [1, 0] * (self.DAYS // 2)
        run, stretch = self.make_habit("Run"), self.make_habit("Stretch")
        self.series(run, pattern)
        self.series(stretch, pattern)
        self.run_command()

        Completion.objects.filter(habit=stretch).delete()
        self.series(stretch, [1 - v for v in pattern])
        self.run_command()

        self.assertEqual(HabitCorrelation.objects.count(), 1)
        self.assertEqual(float(self.pair(run, stretch).spearman_coefficient), -1.0)

    def test_only_the_requested_window_is_used(self):
        pattern = [1, 0] * 5
        run, stretch = self.make_habit("Run"), self.make_habit("Stretch")
        for habit in (run, stretch):  # 10 matching days, 40 to 31 days ago
            for offset, value in enumerate(pattern, start=31):
                Completion.objects.create(habit=habit, date=self.today - timedelta(days=offset), value=value)

        self.run_command("--days", "30")
        self.assertEqual(HabitCorrelation.objects.count(), 0)

        self.run_command("--days", "60")
        self.assertEqual(HabitCorrelation.objects.count(), 1)

    def test_today_is_excluded(self):
        """The day is not over: a habit not done *yet* must not count as skipped."""
        run, stretch = self.make_habit("Run"), self.make_habit("Stretch")
        self.series(run, [1, 0] * 5)
        self.series(stretch, [1, 0] * 5)
        Completion.objects.create(habit=run, date=self.today, value=1)
        Completion.objects.create(habit=stretch, date=self.today, value=0)

        self.run_command()

        correlation = self.pair(run, stretch)
        self.assertEqual(correlation.sample_size, 10)
        self.assertEqual(float(correlation.spearman_coefficient), 1.0)

    def test_min_sample_size(self):
        run, stretch = self.make_habit("Run"), self.make_habit("Stretch")
        self.series(run, [1, 0, 1, 0, 1, 0])
        self.series(stretch, [1, 0, 1, 0, 1, 0])

        self.run_command("--min-sample-size", "10")
        self.assertEqual(HabitCorrelation.objects.count(), 0)

        self.run_command("--min-sample-size", "4")
        self.assertEqual(HabitCorrelation.objects.count(), 1)

    def test_only_overlapping_days_are_compared(self):
        run, stretch = self.make_habit("Run"), self.make_habit("Stretch")
        self.series(run, [1, 0] * 10)
        self.series(stretch, [None] * 12 + [1, 0] * 4)  # started 8 days ago

        self.run_command("--min-sample-size", "4")

        self.assertEqual(self.pair(run, stretch).sample_size, 8)

    def test_archived_habits_are_ignored(self):
        pattern = [1, 0] * (self.DAYS // 2)
        run, old = self.make_habit("Run"), self.make_habit("Old", archived=True)
        self.series(run, pattern)
        self.series(old, pattern)

        self.run_command()

        self.assertEqual(HabitCorrelation.objects.count(), 0)

    def test_a_single_habit_has_nothing_to_correlate_with(self):
        self.series(self.make_habit("Run"), [1, 0] * 5)
        self.assertIn("0 total correlations", self.run_command())

    def test_users_are_computed_separately(self):
        pattern = [1, 0] * (self.DAYS // 2)
        mine, theirs = self.make_habit("Mine"), self.make_habit("Theirs", user=self.other)
        self.series(mine, pattern)
        self.series(theirs, pattern)

        self.run_command()

        self.assertEqual(HabitCorrelation.objects.count(), 0)  # never across accounts

    def test_user_id_limits_the_run(self):
        pattern = [1, 0] * (self.DAYS // 2)
        for user in (self.user, self.other):
            a, b = self.make_habit("A", user=user), self.make_habit("B", user=user)
            self.series(a, pattern)
            self.series(b, pattern)

        self.run_command("--user-id", str(self.other.id))

        self.assertEqual(HabitCorrelation.objects.filter(user=self.other).count(), 1)
        self.assertEqual(HabitCorrelation.objects.filter(user=self.user).count(), 0)

    def test_the_result_is_served_by_the_api(self):
        pattern = [1, 0] * (self.DAYS // 2)
        run, stretch = self.make_habit("Run"), self.make_habit("Stretch")
        self.series(run, pattern)
        self.series(stretch, pattern)
        self.run_command()

        insights = self.client.get("/api/correlations/").data["insights"]

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]["strength"], "very_strong")
        self.assertEqual({insights[0]["habit1"]["name"], insights[0]["habit2"]["name"]}, {"Run", "Stretch"})

    def test_verbose_output_lists_the_methods_used(self):
        pattern = [1, 0] * (self.DAYS // 2)
        run, stretch = self.make_habit("Run"), self.make_habit("Stretch")
        self.series(run, pattern)
        self.series(stretch, pattern)

        self.assertIn("2 habits, 1 pairs tested, 1 kept", self.run_command("--verbose"))

    def test_blank_days_count_as_not_done(self):
        """Yes/no habits logged only on the days they happen (the usual way)."""
        gym, protein = self.make_habit("Gym"), self.make_habit("Protein shake")
        pattern = [1, None, None, 1, None, 1, 1, None, None, None, 1, None, 1, None, None, 1, None, None, 1, 1]
        self.series(gym, pattern)
        self.series(protein, pattern)

        self.run_command()

        correlation = self.pair(gym, protein)
        self.assertIsNotNone(correlation)
        self.assertEqual(float(correlation.spearman_coefficient), 1.0)
        self.assertEqual(correlation.sample_size, self.DAYS)

    def test_blank_days_of_a_measurement_are_not_zero(self):
        gym, sleep = self.make_habit("Gym"), self.make_habit("Sleep", "value")
        self.series(gym, [1, 0] * 10)
        # Slept more on gym days; half of the nights were not logged at all
        self.series(sleep, [9, 6, None, None] * 5)

        self.run_command("--min-sample-size", "4")

        correlation = self.pair(gym, sleep)
        self.assertEqual(correlation.sample_size, 10)
        self.assertEqual(float(correlation.spearman_coefficient), 1.0)

    def test_results_that_no_longer_hold_are_removed(self):
        run, stretch = self.make_habit("Run"), self.make_habit("Stretch")
        self.series(run, [1, 0] * 10)
        self.series(stretch, [1, 0] * 10)
        self.run_command()
        self.assertEqual(HabitCorrelation.objects.count(), 1)

        Completion.objects.filter(habit=stretch).delete()
        self.run_command()

        self.assertEqual(HabitCorrelation.objects.count(), 0)

    def test_a_handful_of_days_is_not_enough(self):
        """Five matching days are a coincidence, not an insight."""
        a, b = self.make_habit("A", "value"), self.make_habit("B", "value")
        self.series(a, [1, 2, 3, 4, 5])
        self.series(b, [2, 4, 6, 8, 10])

        self.run_command()

        self.assertEqual(HabitCorrelation.objects.count(), 0)

    def test_the_direction_reaches_the_api(self):
        early, late = self.make_habit("Early night"), self.make_habit("Late night")
        self.series(early, [1, 0] * 10)
        self.series(late, [0, 1] * 10)
        self.run_command()

        insight = self.client.get("/api/correlations/").data["insights"][0]

        self.assertEqual(insight["direction"], "negative")
        self.assertEqual(float(insight["max_correlation"]), 1.0)


@needs_numpy
class ComputeEndpointTests(CorrelationFixtureMixin, HabitApiTestCase):
    """The "Recompute" button of the Insights tab."""

    URL = "/api/correlations/compute/"

    def series(self, habit, values):
        for offset, value in enumerate(reversed(values), start=1):
            Completion.objects.create(habit=habit, date=self.today - timedelta(days=offset), value=value)

    def matching_pair(self, user=None):
        a, b = self.make_habit("Run", user=user), self.make_habit("Stretch", user=user)
        self.series(a, [1, 0] * 10)
        self.series(b, [1, 0] * 10)
        return a, b

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(self.URL).status_code, 401)

    def test_computes_my_correlations_on_demand(self):
        self.matching_pair()

        response = self.client.post(self.URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["correlations"], 1)
        self.assertEqual(response.data["end_date"], self.today - timedelta(days=1))
        insights = self.client.get("/api/correlations/").data["insights"]
        self.assertEqual(insights[0]["strength"], "very_strong")

    def test_only_touches_my_data(self):
        self.matching_pair()
        x, y = self.matching_pair(user=self.other)
        theirs = self.correlation(x, y, user=self.other, spearman_coefficient="0.5")

        self.client.post(self.URL)

        self.assertEqual(HabitCorrelation.objects.filter(user=self.user).count(), 1)
        theirs.refresh_from_db()  # still there, untouched
        self.assertEqual(float(theirs.spearman_coefficient), 0.5)

    def test_replaces_stale_results(self):
        a, b = self.make_habit("Old A"), self.make_habit("Old B")
        self.correlation(a, b, spearman_coefficient="0.9")  # no data behind it any more

        response = self.client.post(self.URL)

        self.assertEqual(response.data["correlations"], 0)
        self.assertEqual(HabitCorrelation.objects.filter(user=self.user).count(), 0)

    def test_window_can_be_widened_and_is_clamped(self):
        a, b = self.make_habit("Run"), self.make_habit("Stretch")
        for habit in (a, b):  # only data from 40 to 31 days ago
            for offset, value in enumerate([1, 0] * 5, start=31):
                Completion.objects.create(habit=habit, date=self.today - timedelta(days=offset), value=value)

        self.assertEqual(self.client.post(self.URL, {"days": 30}, format="json").data["correlations"], 0)
        self.assertEqual(self.client.post(self.URL, {"days": 60}, format="json").data["correlations"], 1)

        default = self.client.post(self.URL).data
        self.assertEqual(default["start_date"], self.today - timedelta(days=90))
        clamped = self.client.post(self.URL, {"days": 99999}, format="json").data
        self.assertEqual(clamped["start_date"], self.today - timedelta(days=730))
        garbage = self.client.post(self.URL, {"days": "soon"}, format="json")
        self.assertEqual(garbage.status_code, 200)

    def test_is_rate_limited(self):
        statuses = {self.client.post(self.URL).status_code for _ in range(25)}
        self.assertEqual(statuses, {200, 429})
