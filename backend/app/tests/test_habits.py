"""Habits: CRUD, ordering, logging values, summary, graph data and CSV."""

from datetime import date, timedelta

from ..models import Category, Completion, Habit, Tag
from .base import HabitApiTestCase


class HabitCrudTests(HabitApiTestCase):
    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/habits/").status_code, 401)

    def test_create_saves_category_and_tags(self):
        category = Category.objects.create(name="Health", user=self.user)
        tag = Tag.objects.create(name="Morning", user=self.user)

        response = self.client.post(
            "/api/habits/",
            {
                "name": "Run",
                "habit_type": "boolean",
                "category_id": category.id,
                "tag_ids": [tag.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        habit = Habit.objects.get(id=response.data["id"])
        self.assertEqual(habit.user, self.user)
        self.assertEqual(habit.category, category)
        self.assertEqual(list(habit.tags.all()), [tag])
        self.assertEqual(response.data["category"]["name"], "Health")

    def test_cannot_use_someone_elses_category(self):
        foreign = Category.objects.create(name="Private", user=self.other)
        response = self.client.post(
            "/api/habits/",
            {"name": "Run", "habit_type": "boolean", "category_id": foreign.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_list_only_returns_own_active_habits(self):
        self.make_habit("Mine")
        self.make_habit("Archived", archived=True)
        self.make_habit("Theirs", user=self.other)

        names = [h["name"] for h in self.client.get("/api/habits/").data]
        self.assertEqual(names, ["Mine"])

        archived = self.client.get("/api/habits/", {"archived_only": "true"}).data
        self.assertEqual([h["name"] for h in archived], ["Archived"])

    def test_list_reports_value_for_requested_date(self):
        habit = self.make_habit("Water", "counter")
        self.log(habit, days_ago=2, value=6)

        day = (self.today - timedelta(days=2)).isoformat()
        self.assertEqual(self.client.get("/api/habits/", {"date": day}).data[0]["today_value"], 6)
        self.assertEqual(self.client.get("/api/habits/").data[0]["today_value"], 0)


class HabitOrderTests(HabitApiTestCase):
    def names(self):
        return [h["name"] for h in self.client.get("/api/habits/").data]

    def test_new_habits_are_appended(self):
        for name in ["Zebra", "Apple", "Mango"]:
            self.client.post("/api/habits/", {"name": name, "habit_type": "boolean"}, format="json")
        self.assertEqual(self.names(), ["Zebra", "Apple", "Mango"])

    def test_reorder(self):
        a, b, c = (self.make_habit(name) for name in ["A", "B", "C"])

        response = self.client.post("/api/habits/reorder/", {"order": [c.id, a.id, b.id]}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.names(), ["C", "A", "B"])

    def test_reorder_ignores_other_users_habits(self):
        mine = self.make_habit("Mine")
        theirs = self.make_habit("Theirs", user=self.other, order=7)

        response = self.client.post("/api/habits/reorder/", {"order": [theirs.id, mine.id]}, format="json")

        self.assertEqual(response.status_code, 200)
        theirs.refresh_from_db()
        self.assertEqual(theirs.order, 7)

    def test_reorder_rejects_malformed_payload(self):
        for payload in [{}, {"order": "1,2"}, {"order": ["a"]}]:
            response = self.client.post("/api/habits/reorder/", payload, format="json")
            self.assertEqual(response.status_code, 400, payload)


class CompletionTests(HabitApiTestCase):
    def complete(self, habit, value, day=None):
        return self.client.post(
            f"/api/habits/{habit.id}/complete/",
            {"value": value, "date": (day or self.today).isoformat()},
            format="json",
        )

    def test_creates_then_updates_the_same_day(self):
        habit = self.make_habit("Water", "counter")

        self.assertEqual(self.complete(habit, 3).data["status"], "created")
        self.assertEqual(self.complete(habit, 5).data["status"], "updated")

        completion = Completion.objects.get(habit=habit)
        self.assertEqual(completion.date, self.today)
        self.assertEqual(completion.value, 5)

    def test_decimal_values_are_kept(self):
        habit = self.make_habit("Sleep", "value")
        self.assertEqual(self.complete(habit, 7.5).data["new_value"], 7.5)

    def test_zero_clears_a_rating(self):
        habit = self.make_habit("Mood", "rating", max_value=5)
        self.complete(habit, 4)
        self.assertEqual(self.complete(habit, 0).data["new_value"], 0)

    def test_rejects_invalid_values(self):
        cases = [
            (self.make_habit("Water", "counter"), -1),
            (self.make_habit("Sleep", "value"), "lots"),
            (self.make_habit("Weight", "value"), 1e12),
            (self.make_habit("Run", "boolean"), 2),
            (self.make_habit("Mood", "rating", max_value=5), 6),
            (self.make_habit("Energy", "rating", max_value=5), 2.5),
            (self.make_habit("Focus", "rating"), 6),  # default scale is 5
        ]
        for habit, value in cases:
            response = self.complete(habit, value)
            self.assertEqual(response.status_code, 400, f"{habit.name}={value!r}")
        self.assertEqual(Completion.objects.count(), 0)

    def test_rejects_future_dates(self):
        habit = self.make_habit()
        self.assertEqual(self.complete(habit, 1, self.today + timedelta(days=2)).status_code, 400)
        # One day of slack: the server is in UTC, the user may be ahead of it
        self.assertEqual(self.complete(habit, 1, self.today + timedelta(days=1)).status_code, 200)

    def test_rejects_malformed_date(self):
        habit = self.make_habit()
        response = self.client.post(
            f"/api/habits/{habit.id}/complete/", {"value": 1, "date": "14/11/2026"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_log_someone_elses_habit(self):
        habit = self.make_habit(user=self.other)
        self.assertEqual(self.complete(habit, 1).status_code, 404)


class SummaryTests(HabitApiTestCase):
    def test_untouched_habits_are_listed_with_zeroes(self):
        self.make_habit("Run", "boolean")
        self.make_habit("Water", "counter")
        self.make_habit("Sleep", "value", unit="h")
        self.make_habit("Mood", "rating", max_value=5)

        data = self.summary()

        self.assertEqual(data["boolean"][0]["metrics"]["completion_rate"], 0)
        self.assertEqual(data["boolean"][0]["metrics"]["current_streak"], 0)
        self.assertEqual(data["counter"][0]["metrics"]["total"], 0)
        self.assertEqual(data["value"][0]["metrics"]["days_tracked"], 0)
        self.assertEqual(data["rating"][0]["metrics"]["average"], 0)

    def test_boolean_metrics(self):
        habit = self.make_habit()
        for days_ago in [0, 1, 2, 10, 11, 12, 13]:
            self.log(habit, days_ago)

        metrics = self.summary(days=30)["boolean"][0]["metrics"]

        self.assertEqual(metrics["total_completions"], 7)
        self.assertEqual(metrics["completion_rate"], 23.3)
        self.assertEqual(metrics["current_streak"], 3)
        self.assertEqual(metrics["best_streak"], 4)

    def test_current_streak_survives_until_the_day_is_over(self):
        habit = self.make_habit()
        for days_ago in [1, 2]:  # not done today (yet)
            self.log(habit, days_ago)
        self.assertEqual(self.summary()["boolean"][0]["metrics"]["current_streak"], 2)

    def test_current_streak_is_zero_once_broken(self):
        habit = self.make_habit()
        for days_ago in [2, 3, 4]:  # missed yesterday
            self.log(habit, days_ago)

        metrics = self.summary()["boolean"][0]["metrics"]

        self.assertEqual(metrics["current_streak"], 0)
        self.assertEqual(metrics["best_streak"], 3)

    def test_current_streak_counts_days_before_the_range(self):
        habit = self.make_habit()
        for days_ago in range(10):
            self.log(habit, days_ago)

        metrics = self.summary(days=7)["boolean"][0]["metrics"]

        self.assertEqual(metrics["current_streak"], 10)
        self.assertEqual(metrics["best_streak"], 7)

    def test_numeric_metrics(self):
        water = self.make_habit("Water", "counter")
        sleep = self.make_habit("Sleep", "value", unit="h")
        mood = self.make_habit("Mood", "rating", max_value=5)
        for days_ago, glasses, hours, stars in [(0, 4, 7.5, 5), (1, 6, 6.5, 2)]:
            self.log(water, days_ago, glasses)
            self.log(sleep, days_ago, hours)
            self.log(mood, days_ago, stars)

        data = self.summary(days=10)

        # Counters average over the whole range, values/ratings over tracked days
        self.assertEqual(data["counter"][0]["metrics"], {
            "total": 10, "average": 1.0, "max": 6, "days_tracked": 2, "days_in_range": 10,
        })
        self.assertEqual(data["value"][0]["metrics"]["average"], 7.0)
        self.assertEqual(data["value"][0]["metrics"]["max_value"], 7.5)
        self.assertEqual(data["rating"][0]["metrics"]["average"], 3.5)
        self.assertEqual(data["rating"][0]["metrics"]["min"], 2)

    def test_requires_a_valid_range(self):
        self.assertEqual(self.client.get("/api/habits/summary/").status_code, 400)
        response = self.client.get("/api/habits/summary/", {"start_date": "x", "end_date": "y"})
        self.assertEqual(response.status_code, 400)


class GraphDataTests(HabitApiTestCase):
    def test_points_are_grouped_by_type_and_sorted_by_date(self):
        run = self.make_habit("Run", "boolean")
        sleep = self.make_habit("Sleep", "value")
        self.make_habit("Never logged", "counter")
        foreign = self.make_habit("Theirs", "boolean", user=self.other)
        self.log(run, 0)
        self.log(run, 3)
        self.log(sleep, 1, 7.5)
        self.log(sleep, 40, 8)  # outside the range
        self.log(foreign, 0)

        with self.assertNumQueries(2):  # habits + all completions
            response = self.client.get(
                "/api/habits/graph_data/",
                {
                    "start_date": (self.today - timedelta(days=6)).isoformat(),
                    "end_date": self.today.isoformat(),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["boolean"],
            [{
                "habit_id": run.id,
                "habit_name": "Run",
                "color": run.color,
                "data": [
                    {"date": (self.today - timedelta(days=3)).isoformat(), "value": 1.0},
                    {"date": self.today.isoformat(), "value": 1.0},
                ],
            }],
        )
        self.assertEqual(len(response.data["value"][0]["data"]), 1)
        self.assertEqual(response.data["counter"], [])


class CsvRoundTripTests(HabitApiTestCase):
    def test_export_then_import_restores_everything(self):
        category = Category.objects.create(name="Health", user=self.user)
        tag = Tag.objects.create(name="Morning", user=self.user)
        run = self.make_habit("Run", "boolean", category=category, icon="footprints", color="#22c55e")
        run.tags.add(tag)
        sleep = self.make_habit("Sleep", "value", unit="h")
        mood = self.make_habit("Mood", "rating", max_value=10)
        self.log(run, 0)
        self.log(run, 2)
        self.log(sleep, 1, 7.5)
        self.log(mood, 0, 8)

        params = {
            "start_date": (self.today - timedelta(days=6)).isoformat(),
            "end_date": self.today.isoformat(),
        }
        exported = self.client.get("/api/habits/export_csv/", params)
        self.assertEqual(exported.status_code, 200)

        Habit.objects.filter(user=self.user).delete()
        Category.objects.filter(user=self.user).delete()
        Tag.objects.filter(user=self.user).delete()

        imported = self.client.post(
            "/api/habits/import_csv/", {"csv_content": exported.data["csv_content"]}, format="json"
        )
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(imported.data["habits_created"], 3)
        self.assertEqual(imported.data["completions_created"], 4)

        run = Habit.objects.get(user=self.user, name="Run")
        self.assertEqual(run.habit_type, "boolean")
        self.assertEqual(run.icon, "footprints")
        self.assertEqual(run.color, "#22c55e")
        self.assertEqual(run.category.name, "Health")
        self.assertEqual([t.name for t in run.tags.all()], ["Morning"])
        self.assertEqual(
            sorted(run.completions.values_list("date", flat=True)),
            [self.today - timedelta(days=2), self.today],
        )

        sleep = Habit.objects.get(user=self.user, name="Sleep")
        self.assertEqual(sleep.unit, "h")
        self.assertEqual(float(sleep.completions.get().value), 7.5)
        self.assertEqual(Habit.objects.get(user=self.user, name="Mood").max_value, 10)

    def test_import_requires_content(self):
        self.assertEqual(self.client.post("/api/habits/import_csv/", {}, format="json").status_code, 400)


class PercentageHabitTests(HabitApiTestCase):
    """The 0-100 score type (e.g. a sleep score)."""

    def complete(self, habit, value):
        return self.client.post(
            f"/api/habits/{habit.id}/complete/",
            {"value": value, "date": self.today.isoformat()},
            format="json",
        )

    def test_can_be_created_through_the_api(self):
        response = self.client.post(
            "/api/habits/", {"name": "Sleep score", "habit_type": "percentage"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["habit_type"], "percentage")

    def test_accepts_0_to_100_only(self):
        habit = self.make_habit("Sleep score", "percentage")

        for value in [1, 82, 100, 0]:
            self.assertEqual(self.complete(habit, value).status_code, 200, value)
        for value in [101, 250, -5, "high"]:
            self.assertEqual(self.complete(habit, value).status_code, 400, value)

    def test_summary_reports_average_and_extremes(self):
        habit = self.make_habit("Sleep score", "percentage")
        for days_ago, score in [(0, 90), (1, 70), (2, 83)]:
            self.log(habit, days_ago, score)
        self.make_habit("Body battery", "percentage")  # never logged

        metrics = {h["habit_name"]: h["metrics"] for h in self.summary(days=10)["percentage"]}

        self.assertEqual(
            metrics["Sleep score"],
            {"average": 81.0, "max": 90.0, "min": 70.0, "days_tracked": 3, "days_in_range": 10},
        )
        self.assertEqual(metrics["Body battery"]["days_tracked"], 0)

    def test_graph_data_has_its_own_series(self):
        habit = self.make_habit("Sleep score", "percentage")
        self.log(habit, 1, 77)

        response = self.client.get(
            "/api/habits/graph_data/",
            {"start_date": (self.today - timedelta(days=6)).isoformat(), "end_date": self.today.isoformat()},
        )

        self.assertEqual(response.data["percentage"][0]["data"][0]["value"], 77.0)
        self.assertEqual(response.data["rating"], [])

    def test_survives_a_csv_round_trip(self):
        habit = self.make_habit("Sleep score", "percentage")
        self.log(habit, 0, 88)
        params = {"start_date": self.today.isoformat(), "end_date": self.today.isoformat()}
        exported = self.client.get("/api/habits/export_csv/", params).data["csv_content"]
        habit.delete()

        self.client.post("/api/habits/import_csv/", {"csv_content": exported}, format="json")

        restored = Habit.objects.get(name="Sleep score")
        self.assertEqual(restored.habit_type, "percentage")
        self.assertEqual(float(restored.completions.get().value), 88.0)
