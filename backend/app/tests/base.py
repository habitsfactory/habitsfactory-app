"""Shared fixtures for the API tests.

Run everything with:  python manage.py test
"""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APITestCase

from ..models import Completion, Habit


class HabitApiTestCase(APITestCase):
    def setUp(self):
        # Rate limits are counted in the cache: start every test from zero
        cache.clear()
        self.user = User.objects.create_user("alice", "alice@example.com", "pw-alice-123")
        self.other = User.objects.create_user("bob", "bob@example.com", "pw-bob-123")
        self.admin = User.objects.create_superuser("root", "root@example.com", "pw-root-123")
        self.client.force_authenticate(self.user)
        self.today = date.today()

    def make_habit(self, name="Run", habit_type="boolean", user=None, **extra):
        return Habit.objects.create(
            name=name, habit_type=habit_type, user=user or self.user, **extra
        )

    def log(self, habit, days_ago, value=1):
        return Completion.objects.create(
            habit=habit, date=self.today - timedelta(days=days_ago), value=value
        )

    def summary(self, days=30):
        response = self.client.get(
            "/api/habits/summary/",
            {
                "start_date": (self.today - timedelta(days=days - 1)).isoformat(),
                "end_date": self.today.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.data
