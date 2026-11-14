"""
Management command to compute habit correlations ("insights") for all users.
Run nightly; the Insights tab can also trigger it for one user on demand.

How it works
    1. Each habit becomes one value per day over the analysed window:
       - yes/no and counter habits: a day without an entry counts as 0
         ("not done"), from the first day the habit was ever logged;
       - value, rating and percentage habits: a day without an entry is
         unknown and left out (an unlogged night is not 0 hours of sleep).
    2. Every pair of habits is compared on the days both are known, with the
       Spearman rank correlation. It suits every mix of habit types: on two
       yes/no habits it equals the phi coefficient, and it is not thrown off
       by outliers or by the scale of the values.
    3. Only pairs that are statistically solid are kept: enough days in
       common, and a p-value that survives a Benjamini-Hochberg correction
       across all the pairs tested (with dozens of habits there are hundreds
       of pairs, so plain "p < 0.05" would let many flukes through).

    The Pearson coefficient is stored alongside for reference.
    Results that no longer hold are deleted on the next run.

Usage:
    python manage.py compute_correlations
    python manage.py compute_correlations --days 180
    python manage.py compute_correlations --user-id 1
    python manage.py compute_correlations --min-sample-size 14 --verbose
"""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

import numpy as np
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Min
from django.utils import timezone
from scipy.stats import spearmanr

from ...models import Completion, HabitCorrelation

DEFAULT_DAYS = 90
DEFAULT_MIN_SAMPLE_SIZE = 10

# Share of reported pairs we accept to be flukes (false discovery rate)
FALSE_DISCOVERY_RATE = 0.05

# Habit types where "no entry that day" means zero rather than unknown
ZERO_WHEN_MISSING = {"boolean", "counter"}


def benjamini_hochberg(p_values, alpha=FALSE_DISCOVERY_RATE):
    """Return a list of booleans: which p-values stay significant once the
    number of tests is taken into account (Benjamini-Hochberg procedure)."""
    count = len(p_values)
    if count == 0:
        return []
    order = sorted(range(count), key=lambda index: p_values[index])
    # Largest rank k such that p(k) <= k / m * alpha; everything up to it passes
    cutoff = 0
    for rank, index in enumerate(order, start=1):
        if p_values[index] <= rank / count * alpha:
            cutoff = rank
    keep = [False] * count
    for index in order[:cutoff]:
        keep[index] = True
    return keep


def build_series(habit_type, values_by_date, dates, first_logged):
    """One value per date: the logged value, 0 or NaN (see module docstring)."""
    fill_zero = habit_type in ZERO_WHEN_MISSING
    series = np.full(len(dates), np.nan, dtype=np.float64)
    for position, day in enumerate(dates):
        if day in values_by_date:
            series[position] = values_by_date[day]
        elif fill_zero and first_logged is not None and day >= first_logged:
            series[position] = 0.0
    return series


def correlate(x, y, min_sample_size):
    """Compare two daily series. Returns (spearman, p_value, pearson, days)
    or None when they cannot be compared (too few common days, or one of
    them never changes)."""
    both_known = ~np.isnan(x) & ~np.isnan(y)
    days = int(both_known.sum())
    if days < min_sample_size or days < 3:
        return None
    x, y = x[both_known], y[both_known]
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return None

    spearman, p_value = spearmanr(x, y)
    if np.isnan(spearman) or np.isnan(p_value):
        return None
    pearson = float(np.corrcoef(x, y)[0, 1])
    return float(spearman), float(p_value), pearson, days


def to_decimal(value):
    if value is None or np.isnan(value):
        return None
    return Decimal(str(round(max(-1.0, min(1.0, float(value))), 4)))


class Command(BaseCommand):
    help = "Compute habit correlations for all users based on recent completion data"

    verbose = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=DEFAULT_DAYS,
            help=f"Number of days to analyze (default: {DEFAULT_DAYS})",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Compute correlations for a specific user only",
        )
        parser.add_argument(
            "--min-sample-size",
            type=int,
            default=DEFAULT_MIN_SAMPLE_SIZE,
            help="Minimum number of days two habits must have in common "
            f"(default: {DEFAULT_MIN_SAMPLE_SIZE})",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show how many pairs were tested and kept",
        )

    def handle(self, *args, **options):
        days = options["days"]
        user_id = options.get("user_id")
        min_sample_size = options["min_sample_size"]
        self.verbose = options.get("verbose", False)

        # Up to yesterday: today is not over, so "not done yet" would count as 0
        end_date = timezone.now().date() - timedelta(days=1)
        start_date = end_date - timedelta(days=days - 1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Computing correlations from {start_date} to {end_date} ({days} days)"
            )
        )
        self.stdout.write(f"Min sample size: {min_sample_size}")

        users = User.objects.filter(id=user_id) if user_id else User.objects.all()
        total = 0

        for user in users:
            count = self.compute_user_correlations(
                user, start_date, end_date, min_sample_size
            )
            total += count
            self.stdout.write(f"  User {user.username}: {count} correlations")

        self.stdout.write(self.style.SUCCESS(f"✓ Computed {total} total correlations"))

    def compute_user_correlations(self, user, start_date, end_date, min_sample_size):
        """Recompute every pairwise correlation of a user's active habits.

        Replaces the user's previous results: pairs that are no longer
        significant are deleted. Returns the number of correlations stored.
        """
        habits = list(user.habits.filter(archived=False).order_by("id"))

        values = defaultdict(dict)
        for habit_id, day, value in Completion.objects.filter(
            habit__in=habits, date__gte=start_date, date__lte=end_date
        ).values_list("habit_id", "date", "value"):
            values[habit_id][day] = float(value)

        first_logged = dict(
            Completion.objects.filter(habit__in=habits)
            .values("habit_id")
            .annotate(first=Min("date"))
            .values_list("habit_id", "first")
        )

        dates = [
            start_date + timedelta(days=offset)
            for offset in range((end_date - start_date).days + 1)
        ]
        series = {
            habit.id: build_series(
                habit.habit_type, values[habit.id], dates, first_logged.get(habit.id)
            )
            for habit in habits
            if habit.id in first_logged
        }
        tracked = [habit for habit in habits if habit.id in series]

        # 1. Compare every pair that has enough days in common
        candidates = []
        for index, habit1 in enumerate(tracked):
            for habit2 in tracked[index + 1:]:
                result = correlate(series[habit1.id], series[habit2.id], min_sample_size)
                if result is not None:
                    candidates.append((habit1, habit2, *result))

        # 2. Keep the pairs that survive the multiple-comparison correction
        keep = benjamini_hochberg([candidate[3] for candidate in candidates])
        significant = [c for c, kept in zip(candidates, keep) if kept]

        if self.verbose:
            self.stdout.write(
                f"  {user.username}: {len(tracked)} habits, "
                f"{len(candidates)} pairs tested, {len(significant)} kept"
            )

        # 3. Store them, replacing the previous run
        existing = {
            (c.habit1_id, c.habit2_id): c
            for c in HabitCorrelation.objects.filter(user=user)
        }
        to_create, to_update, fresh_keys = [], [], set()

        for habit1, habit2, spearman, _p_value, pearson, days in significant:
            key = (habit1.id, habit2.id)
            fresh_keys.add(key)
            obj = existing.get(key) or HabitCorrelation(
                user=user, habit1=habit1, habit2=habit2
            )
            obj.spearman_coefficient = to_decimal(spearman)
            obj.pearson_coefficient = to_decimal(pearson)
            obj.dtw_distance = None  # no longer computed
            obj.sample_size = days
            obj.start_date = start_date
            obj.end_date = end_date
            obj.calculated_at = timezone.now()
            # bulk_create / bulk_update do not call save()
            obj.max_correlation = obj._compute_max_correlation()
            (to_update if key in existing else to_create).append(obj)

        stale = [obj.pk for key, obj in existing.items() if key not in fresh_keys]
        if stale:
            HabitCorrelation.objects.filter(pk__in=stale).delete()
        if to_create:
            HabitCorrelation.objects.bulk_create(to_create)
        if to_update:
            HabitCorrelation.objects.bulk_update(
                to_update,
                [
                    "pearson_coefficient",
                    "spearman_coefficient",
                    "dtw_distance",
                    "sample_size",
                    "start_date",
                    "end_date",
                    "max_correlation",
                    "calculated_at",
                ],
            )

        return len(significant)
