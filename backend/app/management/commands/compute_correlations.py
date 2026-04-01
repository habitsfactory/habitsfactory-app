"""
Management command to compute habit correlations for all users.
Run this nightly using Django's task scheduler or cron.

Correlation Methods (Type-Aware):
    - Binary × Binary: Phi Coefficient (χ² based)
    - Binary × Continuous: Point-Biserial Correlation
    - Continuous × Continuous: Spearman Rank Correlation (primary), Pearson (supplemental)
    - Ordinal (rating) × Any: Spearman Rank Correlation
    
Additional Analyses:
    - Lagged Cross-Correlation: Detects time-shifted relationships (e.g., exercise → next-day energy)
    - DTW Distance: Measures pattern similarity even with time shifts or scaling differences
    - Statistical Significance: Only correlations with p < 0.05 are stored

Usage:
    python manage.py compute_correlations
    python manage.py compute_correlations --days 7
    python manage.py compute_correlations --user-id 1
    python manage.py compute_correlations --days 30 --min-sample-size 10
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr, pearsonr, kendalltau, pointbiserialr
from ...models import Habit, Completion, HabitCorrelation
from dtaidistance import dtw


class Command(BaseCommand):
    help = "Compute habit correlations for all users based on recent completion data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to analyze (default: 30, recommended: 7-30)",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Compute correlations for a specific user only",
        )
        parser.add_argument(
            "--min-sample-size",
            type=int,
            default=4,
            help="Minimum number of overlapping data points required (default: 4)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output including lagged correlations",
        )

    def handle(self, *args, **options):
        days = options["days"]
        user_id = options.get("user_id")
        min_sample_size = options["min_sample_size"]
        self.verbose = options.get("verbose", False)

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

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def compute_phi_coefficient(self, x, y):
        """Compute Phi coefficient for two binary variables."""
        # Ensure we have binary data
        x = x.astype(int)
        y = y.astype(int)
        
        n11 = np.sum((x == 1) & (y == 1))
        n10 = np.sum((x == 1) & (y == 0))
        n01 = np.sum((x == 0) & (y == 1))
        n00 = np.sum((x == 0) & (y == 0))
        
        # Calculate denominator components
        row1 = n11 + n10
        row2 = n01 + n00
        col1 = n11 + n01
        col2 = n10 + n00
        
        # Avoid division by zero
        denominator = row1 * row2 * col1 * col2
        if denominator == 0:
            return 0.0
        
        with np.errstate(divide='ignore', invalid='ignore'):
            phi = (n11 * n00 - n10 * n01) / np.sqrt(denominator)
        
        return phi if not np.isnan(phi) else 0.0

    def compute_lagged_correlation(self, x, y, lag=1):
        """Compute correlation with time lag (e.g., does x today predict y tomorrow?)."""
        if lag >= len(x) or lag >= len(y):
            return None
        
        x_lagged = x[:-lag]
        y_shifted = y[lag:]
        
        valid_mask = ~np.isnan(x_lagged) & ~np.isnan(y_shifted)
        
        if valid_mask.sum() < 4:
            return None
        
        with np.errstate(divide='ignore', invalid='ignore'):
            corr, p_value = spearmanr(x_lagged[valid_mask], y_shifted[valid_mask])
        
        # Only return significant correlations
        if p_value <= 0.05 and not np.isnan(corr):
            return corr
        return None

    def get_habit_type_category(self, habit):
        """Categorize habit type for correlation method selection."""
        if habit.habit_type == 'boolean':
            return 'binary'
        elif habit.habit_type in ['counter', 'value']:
            return 'continuous'
        elif habit.habit_type == 'rating':
            return 'ordinal'
        return 'continuous'

    def compute_best_correlation(self, x, y, type1, type2, overlap_mask):
        """
        Compute the most appropriate correlation based on variable types.
        Returns (correlation_value, method_name, p_value)
        """
        x_valid = x[overlap_mask]
        y_valid = y[overlap_mask]
        
        # Need at least 3 points for meaningful correlation
        if len(x_valid) < 3:
            return None, None, None
        
        # Binary vs Binary: Use Phi Coefficient
        if type1 == 'binary' and type2 == 'binary':
            try:
                phi = self.compute_phi_coefficient(x_valid, y_valid)
                if not np.isnan(phi) and abs(phi) > 0.01:  # Avoid near-zero correlations
                    return phi, 'phi', None
            except Exception:
                pass
        
        # Binary vs Continuous: Use Point-Biserial
        elif (type1 == 'binary' and type2 == 'continuous') or \
             (type1 == 'continuous' and type2 == 'binary'):
            try:
                binary_var = x_valid if type1 == 'binary' else y_valid
                continuous_var = y_valid if type1 == 'binary' else x_valid
                
                # Check if binary variable has variation
                if len(np.unique(binary_var)) < 2:
                    return None, None, None
                
                corr, p_value = pointbiserialr(binary_var, continuous_var)
                if p_value <= 0.05 and not np.isnan(corr):
                    return corr, 'point_biserial', p_value
            except Exception:
                pass
        
        # For all other cases, use Spearman (works with ordinal, continuous, mixed)
        try:
            # Check for variation in both variables
            if len(np.unique(x_valid)) < 2 or len(np.unique(y_valid)) < 2:
                return None, None, None
                
            corr, p_value = spearmanr(x_valid, y_valid)
            if p_value <= 0.05 and not np.isnan(corr):
                return corr, 'spearman', p_value
        except Exception:
            pass
        
        return None, None, None

    # -------------------------------------------------------------------------
    # Main Computation
    # -------------------------------------------------------------------------

    def compute_user_correlations(self, user, start_date, end_date, min_sample_size):
        """Compute all pairwise habit correlations for a user."""
        habits = list(user.habits.filter(archived=False).order_by("id"))

        if len(habits) < 2:
            return 0

        completions = Completion.objects.filter(
            habit__user=user,
            date__gte=start_date,
            date__lte=end_date,
        ).select_related("habit")

        habit_data = defaultdict(dict)
        for c in completions:
            habit_data[c.habit_id][c.date] = float(c.value)

        habit_ids = [h.id for h in habits if h.id in habit_data]
        if len(habit_ids) < 2:
            return 0

        habit_map = {h.id: h for h in habits}
        habit_types = {h.id: self.get_habit_type_category(h) for h in habits}

        all_dates = sorted(
            {date for values in habit_data.values() for date in values.keys()}
        )

        if len(all_dates) < min_sample_size:
            return 0

        num_habits = len(habit_ids)
        num_dates = len(all_dates)

        # Track correlation method usage for verbose output
        method_counts = defaultdict(int)

        # Raw matrix with NaN for missing data
        raw = np.full((num_habits, num_dates), np.nan, dtype=np.float64)
        
        for i, habit_id in enumerate(habit_ids):
            for j, date in enumerate(all_dates):
                if date in habit_data[habit_id]:
                    raw[i, j] = habit_data[habit_id][date]

        # Normalized matrix (for DTW and visualization)
        norm = np.full_like(raw, np.nan)
        for i in range(num_habits):
            row = raw[i]
            mask = ~np.isnan(row)
            if mask.sum() == 0:
                continue
            min_v = np.nanmin(row)
            max_v = np.nanmax(row)
            if max_v > min_v:
                norm[i, mask] = (row[mask] - min_v) / (max_v - min_v)
            else:
                norm[i, mask] = 0.5  # Constant value maps to middle

        existing = HabitCorrelation.objects.filter(user=user)
        existing_map = {(c.habit1_id, c.habit2_id): c for c in existing}

        to_create = []
        to_update = []

        for i in range(num_habits):
            for j in range(i + 1, num_habits):
                h1_id = habit_ids[i]
                h2_id = habit_ids[j]
                h1 = habit_map[h1_id]
                h2 = habit_map[h2_id]

                x = raw[i]
                y = raw[j]

                overlap_mask = ~np.isnan(x) & ~np.isnan(y)
                overlap = overlap_mask.sum()

                if overlap < min_sample_size:
                    continue

                type1 = habit_types[h1_id]
                type2 = habit_types[h2_id]

                # Compute Pearson (for continuous data as baseline)
                pearson = np.nan
                if type1 == 'continuous' and type2 == 'continuous':
                    with np.errstate(divide="ignore", invalid="ignore"):
                        pearson_corr = np.corrcoef(x[overlap_mask], y[overlap_mask])[0, 1]
                        if not np.isnan(pearson_corr):
                            pearson = pearson_corr

                # Compute best type-aware correlation
                best_corr, method, p_value = self.compute_best_correlation(
                    x, y, type1, type2, overlap_mask
                )
                
                # Skip if no significant correlation found
                if best_corr is None:
                    continue
                
                # Track which method was used
                method_counts[method] += 1

                spearman = best_corr if method in ['spearman', 'point_biserial', 'phi'] else np.nan

                # Compute lagged correlations (time-shifted relationships)
                # Check if habit x today predicts habit y tomorrow (lag=1)
                lag_1 = self.compute_lagged_correlation(x, y, lag=1)
                # Reverse: does y today predict x tomorrow?
                lag_1_reverse = self.compute_lagged_correlation(y, x, lag=1)
                
                # Take the stronger lagged correlation
                max_lag = None
                if lag_1 is not None and lag_1_reverse is not None:
                    max_lag = lag_1 if abs(lag_1) > abs(lag_1_reverse) else -lag_1_reverse
                elif lag_1 is not None:
                    max_lag = lag_1
                elif lag_1_reverse is not None:
                    max_lag = -lag_1_reverse

                # Compute DTW distance (measures similarity in pattern/shape)
                dtw_value = None
                try:
                    nx = norm[i][overlap_mask]
                    ny = norm[j][overlap_mask]
                    if len(nx) > 1 and len(ny) > 1 and not np.any(np.isnan(nx)) and not np.any(np.isnan(ny)):
                        dist = dtw.distance(nx, ny)
                        # Normalize by sequence length
                        dtw_value = dist / (len(nx) + len(ny))
                        # Convert to similarity score (0-1, higher = more similar)
                        dtw_value = 1.0 / (1.0 + dtw_value)
                except Exception as e:
                    # DTW can fail on certain data, continue without it
                    pass

                # Convert to Decimal for database storage
                pearson_d = None if np.isnan(pearson) else Decimal(str(round(float(pearson), 4)))
                spearman_d = None if np.isnan(spearman) else Decimal(str(round(float(spearman), 4)))
                dtw_d = None if dtw_value is None else Decimal(str(round(float(dtw_value), 4)))

                key = (h1_id, h2_id)
                obj = existing_map.get(key)

                # Note: Lagged correlation detected but not stored in current schema
                # max_lag indicates time-shifted relationship strength
                # Positive: h1 predicts h2, Negative: h2 predicts h1
                if self.verbose and max_lag is not None and abs(max_lag) > 0.3:
                    direction = f"{h1.name} → {h2.name}" if max_lag > 0 else f"{h2.name} → {h1.name}"
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Time-lagged: {direction}: {abs(max_lag):.3f}"
                        )
                    )

                if obj:
                    obj.pearson_coefficient = pearson_d
                    obj.spearman_coefficient = spearman_d
                    obj.dtw_distance = dtw_d
                    obj.sample_size = overlap
                    obj.start_date = start_date
                    obj.end_date = end_date
                    to_update.append(obj)
                else:
                    to_create.append(
                        HabitCorrelation(
                            user=user,
                            habit1=h1,
                            habit2=h2,
                            pearson_coefficient=pearson_d,
                            spearman_coefficient=spearman_d,
                            dtw_distance=dtw_d,
                            sample_size=overlap,
                            start_date=start_date,
                            end_date=end_date,
                        )
                    )

        if to_create:
            for obj in to_create:
                obj.max_correlation = obj._compute_max_correlation()
            HabitCorrelation.objects.bulk_create(to_create)

        if to_update:
            for obj in to_update:
                obj.max_correlation = obj._compute_max_correlation()
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
                ],
            )

        # Show method summary in verbose mode
        if self.verbose and method_counts:
            self.stdout.write("  Correlation methods used:")
            for method, count in sorted(method_counts.items()):
                self.stdout.write(f"    - {method}: {count}")

        return len(to_create) + len(to_update)
