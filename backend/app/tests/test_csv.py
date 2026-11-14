"""CSV import: the formats and edge cases it has to cope with."""

from datetime import date

from ..models import Category, Completion, Habit, Tag
from .base import HabitApiTestCase

HEADER = "Habit Name,Type,Color,Icon,Category,Tags,Unit,Max Value"


class CsvImportTests(HabitApiTestCase):
    def import_csv(self, *lines):
        return self.client.post(
            "/api/habits/import_csv/", {"csv_content": "\n".join(lines)}, format="json"
        )

    def test_creates_habits_categories_tags_and_values(self):
        response = self.import_csv(
            f"{HEADER},2026-01-01,2026-01-02,2026-01-03",
            "Run,boolean,#22c55e,footprints,Health,Morning:Outdoor,,,1,,1",
            "Sleep,value,#6366f1,moon,Health,,h,,7.5,8,",
            "Mood,rating,#f59e0b,smile,,,,10,7,,9",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {k: response.data[k] for k in ("habits_created", "completions_created", "categories_created", "tags_created")},
            {"habits_created": 3, "completions_created": 6, "categories_created": 1, "tags_created": 2},
        )
        run = Habit.objects.get(name="Run")
        self.assertEqual(run.user, self.user)
        self.assertEqual(run.category.name, "Health")
        self.assertEqual(sorted(t.name for t in run.tags.all()), ["Morning", "Outdoor"])
        self.assertEqual(
            sorted(run.completions.values_list("date", flat=True)), [date(2026, 1, 1), date(2026, 1, 3)]
        )
        self.assertEqual(Habit.objects.get(name="Sleep").unit, "h")
        self.assertEqual(Habit.objects.get(name="Mood").max_value, 10)

    def test_blank_or_unknown_types_fall_back_to_yes_no(self):
        self.import_csv(
            HEADER,
            "Work,,#111111,briefcase,,,,",
            "Odd,nonsense,#111111,star,,,,",
            "Shouty,COUNTER,#111111,star,,,,",
        )

        types = dict(Habit.objects.values_list("name", "habit_type"))

        self.assertEqual(types, {"Work": "boolean", "Odd": "boolean", "Shouty": "counter"})
        # ...and the stats endpoints cope with what was imported
        self.assertEqual(len(self.summary()["boolean"]), 2)

    def test_habits_keep_the_order_of_the_file(self):
        self.make_habit("Existing", order=4)

        self.import_csv(HEADER, "Zebra,boolean,,,,,,", "Apple,boolean,,,,,,", "Mango,boolean,,,,,,")

        names = [h["name"] for h in self.client.get("/api/habits/").data]
        self.assertEqual(names, ["Existing", "Zebra", "Apple", "Mango"])

    def test_reimport_updates_instead_of_duplicating(self):
        self.import_csv(f"{HEADER},2026-01-01", "Run,boolean,#111111,star,Health,Morning,,,1")

        response = self.import_csv(f"{HEADER},2026-01-01,2026-01-02", "Run,counter,#222222,flame,Fitness,,,,3,4")

        self.assertEqual(response.data["habits_created"], 0)
        self.assertEqual(response.data["habits_updated"], 1)
        self.assertEqual(response.data["completions_created"], 1)
        habit = Habit.objects.get(name="Run")
        self.assertEqual((habit.habit_type, habit.color, habit.icon), ("counter", "#222222", "flame"))
        self.assertEqual(habit.category.name, "Fitness")
        self.assertEqual(habit.tags.count(), 0)
        self.assertEqual(
            sorted(float(v) for v in habit.completions.values_list("value", flat=True)), [3.0, 4.0]
        )

    def test_semicolons_and_decimal_commas(self):
        """Spreadsheets with a French locale export this way."""
        response = self.import_csv(
            "Habit Name;Type;Color;Icon;Category;Tags;Unit;Max Value;2026-01-01;2026-01-02",
            "Sommeil;value;#6366f1;moon;Santé;;h;;7,5;8",
        )

        self.assertEqual(response.status_code, 200)
        habit = Habit.objects.get(name="Sommeil")
        self.assertEqual(habit.category.name, "Santé")
        self.assertEqual(sorted(float(v) for v in habit.completions.values_list("value", flat=True)), [7.5, 8.0])

    def test_bad_cells_are_skipped_not_fatal(self):
        response = self.import_csv(
            f"{HEADER},2026-01-01,not-a-date,2026-01-03",
            "Run,boolean,#111111,star,,,,,1,1,oops",
            ",boolean,#111111,star,,,,,1,1,1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["habits_created"], 1)
        self.assertEqual(Completion.objects.count(), 1)

    def test_a_missing_color_gets_a_generated_one(self):
        self.import_csv(HEADER, "Run,boolean,,star,,,,")
        self.assertRegex(Habit.objects.get(name="Run").color, r"^#[0-9a-f]{6}$")

    def test_import_never_touches_other_users(self):
        theirs = self.make_habit("Run", user=self.other, color="#abcdef")
        Category.objects.create(name="Health", user=self.other)
        Tag.objects.create(name="Morning", user=self.other)

        self.import_csv(f"{HEADER},2026-01-01", "Run,counter,#000000,star,Health,Morning,,,5")

        theirs.refresh_from_db()
        self.assertEqual((theirs.habit_type, theirs.color), ("boolean", "#abcdef"))
        self.assertEqual(theirs.completions.count(), 0)
        self.assertEqual(Habit.objects.filter(user=self.user, name="Run").count(), 1)
        self.assertEqual(Category.objects.filter(name="Health").count(), 2)

    def test_export_requires_a_valid_range(self):
        self.assertEqual(self.client.get("/api/habits/export_csv/").status_code, 400)
        response = self.client.get("/api/habits/export_csv/", {"start_date": "x", "end_date": "y"})
        self.assertEqual(response.status_code, 400)

    def test_export_layout(self):
        habit = self.make_habit("Run", icon="footprints", color="#22c55e")
        Completion.objects.create(habit=habit, date=date(2026, 1, 2), value=1)
        self.make_habit("Archived", archived=True)

        response = self.client.get(
            "/api/habits/export_csv/", {"start_date": "2026-01-01", "end_date": "2026-01-03"}
        )

        lines = response.data["csv_content"].strip().splitlines()
        self.assertEqual(lines[0], f"{HEADER},2026-01-01,2026-01-02,2026-01-03")
        self.assertEqual(lines[1:], ["Run,boolean,#22c55e,footprints,,,,,,1.0,"])
