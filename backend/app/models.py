import uuid

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=128)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name}"


class Tag(models.Model):
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default="#6B7280")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tags")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["name", "user"]

    def __str__(self):
        return self.name


class Habit(models.Model):
    TYPE_CHOICES = [
        ("boolean", "Yes/No"),
        ("counter", "Counter"),
        ("value", "Decimal Value"),
        ("rating", "Rating"),
    ]
    name = models.CharField(max_length=100)
    habit_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default="boolean"
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="habits",
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habits")
    creation_date = models.DateTimeField(auto_now_add=True, editable=False)

    icon = models.CharField(max_length=50, default="calendar")
    color = models.CharField(max_length=20, default="#1F85DE")
    max_value = models.IntegerField(null=True, blank=True)
    unit = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Optional unit for value habit (e.g., 'km', 'miles', 'hours')",
    )
    archived = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True, related_name="habits")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Completion(models.Model):
    habit = models.ForeignKey(
        Habit, related_name="completions", on_delete=models.CASCADE
    )
    date = models.DateField(default=timezone.now)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ["habit", "date"]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.habit.name} - {self.date}"


class HabitCorrelation(models.Model):
    """
    Stores correlation data between pairs of habits for a user.
    Updated nightly to show which habits tend to be done together.

    Supports multiple correlation methods:
    - Pearson: Linear relationships
    - Spearman: Rank-based (monotonic) relationships
    - DTW: Dynamic Time Warping distance (time-shifted patterns)
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="habit_correlations"
    )
    habit1 = models.ForeignKey(
        Habit, on_delete=models.CASCADE, related_name="correlations_as_habit1"
    )
    habit2 = models.ForeignKey(
        Habit, on_delete=models.CASCADE, related_name="correlations_as_habit2"
    )

    # Pearson correlation coefficient (-1 to 1) - linear relationships
    pearson_coefficient = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Pearson correlation (linear relationships)",
    )

    # Spearman rank correlation coefficient (-1 to 1) - monotonic relationships
    spearman_coefficient = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Spearman rank correlation (handles ordinal data better)",
    )

    # DTW distance (0+) - normalized 0-1, lower = more similar
    dtw_distance = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Dynamic Time Warping distance (detects time-shifted patterns)",
    )

    # Number of days used in calculation
    sample_size = models.IntegerField()

    # Date range used for calculation
    start_date = models.DateField()
    end_date = models.DateField()

    # Metadata
    calculated_at = models.DateTimeField(auto_now=True)

    # Cached max correlation for ordering/indexing (updated on save)
    max_correlation = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        help_text="Maximum correlation strength across all methods (0-1)",
    )

    class Meta:
        unique_together = ["user", "habit1", "habit2"]
        ordering = ["-max_correlation"]
        indexes = [
            models.Index(fields=["user", "-max_correlation"]),
        ]

    def __str__(self):
        return f"{self.habit1.name} ↔ {self.habit2.name}: {self.max_correlation}"

    def _compute_max_correlation(self):
        """
        Computes the maximum correlation strength across all three methods.

        Takes the absolute value for Pearson and Spearman coefficients
        (since both -1 and +1 indicate strong correlation),
        and inverts DTW distance (since lower DTW = stronger similarity).

        Returns a value between 0 and 1, where 1 = strongest correlation.
        """
        correlations = []

        # Pearson correlation: -1 to 1, use absolute value
        if self.pearson_coefficient is not None:
            correlations.append(abs(float(self.pearson_coefficient)))

        # Spearman correlation: -1 to 1, use absolute value
        if self.spearman_coefficient is not None:
            correlations.append(abs(float(self.spearman_coefficient)))

        # DTW distance: 0+ (normalized 0-1), invert it (1 - distance)
        # so that 0 distance becomes 1 (perfect match)
        if self.dtw_distance is not None:
            correlations.append(1 - float(self.dtw_distance))

        return max(correlations) if correlations else 0.0

    def save(self, *args, **kwargs):
        self.max_correlation = self._compute_max_correlation()
        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    """
    Site-wide settings that can only be modified by admin users.
    This uses a singleton pattern - only one instance should exist.
    """

    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settings_updates",
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton pattern)
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion of settings
        pass


class InviteLink(models.Model):
    """
    Invite links generated by admins to allow new user registration.
    Each link has a unique token and expires after 24 hours.
    """

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="invite_links"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_invite_link",
    )
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite {self.token} (expires {self.expires_at})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        return self.used_by is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_used
