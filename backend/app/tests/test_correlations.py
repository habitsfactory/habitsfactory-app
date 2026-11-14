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
    from ..management.commands.compute_correlations import Command
except ImportError:  # pragma: no cover
    np = None
    Command = None

needs_numpy = unittest.skipIf(np is None, "numpy / scipy / dtaidistance are not installed")


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

    def test_takes_the_strongest_method(self):
        self.assertEqual(self.strength(pearson_coefficient="0.3", spearman_coefficient="0.8"), 0.8)

    def test_negative_coefficients_count_by_magnitude(self):
        self.assertEqual(self.strength(pearson_coefficient="-0.9", spearman_coefficient="0.2"), 0.9)

    def test_dtw_is_a_distance_so_it_is_inverted(self):
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

    def test_description_names_both_habits(self):
        for coefficient in ["0.95", "0.8", "0.6", "0.3"]:
            description = self.serialize(coefficient)["description"]
            self.assertIn("Run", description)
            self.assertIn("Mood", description)
            HabitCorrelation.objects.all().delete()
            self.user.habits.all().delete()


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
    def setUp(self):
        self.command = Command()

    def test_phi_coefficient(self):
        x = np.array([1, 0, 1, 0, 1, 0, 1, 0])
        self.assertAlmostEqual(self.command.compute_phi_coefficient(x, x), 1.0)
        self.assertAlmostEqual(self.command.compute_phi_coefficient(x, 1 - x), -1.0)
        self.assertAlmostEqual(self.command.compute_phi_coefficient(x, np.array([1, 1, 0, 0, 1, 1, 0, 0])), 0.0)

    def test_phi_is_zero_when_a_habit_never_varies(self):
        x = np.array([1, 0, 1, 0])
        self.assertEqual(self.command.compute_phi_coefficient(x, np.ones(4)), 0.0)

    def test_habit_type_categories(self):
        class Stub:
            def __init__(self, habit_type):
                self.habit_type = habit_type

        categories = {t: self.command.get_habit_type_category(Stub(t)) for t in ["boolean", "counter", "value", "rating", ""]}
        self.assertEqual(
            categories,
            {"boolean": "binary", "counter": "continuous", "value": "continuous", "rating": "ordinal", "": "continuous"},
        )

    def best(self, x, y, type1, type2):
        x, y = np.array(x, dtype=float), np.array(y, dtype=float)
        return self.command.compute_best_correlation(x, y, type1, type2, np.ones(len(x), dtype=bool))

    def test_method_is_chosen_from_the_habit_types(self):
        binary = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        rising = [9, 1, 8, 2, 9, 1, 7, 2, 8, 1]
        ramp = list(range(10))

        self.assertEqual(self.best(binary, binary, "binary", "binary")[1], "phi")
        self.assertEqual(self.best(binary, rising, "binary", "continuous")[1], "point_biserial")
        self.assertEqual(self.best(rising, binary, "continuous", "binary")[1], "point_biserial")
        self.assertEqual(self.best(ramp, ramp, "continuous", "continuous")[1], "spearman")
        self.assertEqual(self.best(ramp, ramp, "ordinal", "binary")[1], "spearman")

    def test_sign_follows_the_relationship(self):
        ramp = list(range(10))
        self.assertAlmostEqual(self.best(ramp, ramp, "continuous", "continuous")[0], 1.0)
        self.assertAlmostEqual(self.best(ramp, ramp[::-1], "continuous", "continuous")[0], -1.0)

    def test_nothing_is_reported_without_evidence(self):
        ramp = list(range(10))
        noise = [3, 9, 1, 7, 2, 8, 4, 6, 5, 5]
        none = (None, None, None)

        self.assertEqual(self.best(ramp, noise, "continuous", "continuous"), none)  # not significant
        self.assertEqual(self.best(ramp, [4] * 10, "continuous", "continuous"), none)  # no variation
        self.assertEqual(self.best([1] * 10, ramp, "binary", "continuous"), none)
        self.assertEqual(self.best([1, 2], [1, 2], "continuous", "continuous"), none)  # too few points

    def test_lagged_correlation_detects_a_one_day_shift(self):
        x = np.array([1, 5, 2, 8, 3, 9, 4, 7, 6, 10, 2, 5], dtype=float)
        y = np.concatenate([[0.0], x[:-1]])  # y today = x yesterday

        self.assertAlmostEqual(self.command.compute_lagged_correlation(x, y, lag=1), 1.0)

    def test_lagged_correlation_needs_enough_points(self):
        short = np.array([1.0, 2.0, 3.0])
        self.assertIsNone(self.command.compute_lagged_correlation(short, short, lag=1))
        self.assertIsNone(self.command.compute_lagged_correlation(short, short, lag=5))
        gaps = np.array([1.0, np.nan, 2.0, np.nan, 3.0, np.nan, 4.0, np.nan])
        self.assertIsNone(self.command.compute_lagged_correlation(gaps, gaps, lag=1))


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
        self.assertIsNotNone(correlation.dtw_distance)

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
        self.series(stretch, [None] * 12 + [1, 0] * 4)  # logged on the last 8 days only

        self.run_command()

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

        self.assertIn("phi: 1", self.run_command("--verbose"))
