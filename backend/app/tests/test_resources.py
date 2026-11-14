"""Categories, tags, habit lifecycle, user data deletion, settings, invites."""

from datetime import timedelta

from django.utils import timezone

from ..models import (
    Category,
    Completion,
    Habit,
    HabitCorrelation,
    InviteLink,
    SiteSettings,
    Tag,
)
from .base import HabitApiTestCase


class CategoryTests(HabitApiTestCase):
    def test_crud(self):
        created = self.client.post("/api/categories/", {"name": "Health", "order": 0}, format="json")
        self.assertEqual(created.status_code, 201)
        category = Category.objects.get(id=created.data["id"])
        self.assertEqual(category.user, self.user)

        renamed = self.client.patch(f"/api/categories/{category.id}/", {"name": "Body"}, format="json")
        self.assertEqual(renamed.data["name"], "Body")

        self.assertEqual(self.client.delete(f"/api/categories/{category.id}/").status_code, 204)
        self.assertFalse(Category.objects.filter(id=category.id).exists())

    def test_list_is_ordered_and_private(self):
        Category.objects.create(name="Second", user=self.user, order=1)
        Category.objects.create(name="First", user=self.user, order=0)
        Category.objects.create(name="Theirs", user=self.other, order=0)

        names = [c["name"] for c in self.client.get("/api/categories/").data]

        self.assertEqual(names, ["First", "Second"])

    def test_cannot_touch_someone_elses_category(self):
        foreign = Category.objects.create(name="Theirs", user=self.other)

        self.assertEqual(self.client.get(f"/api/categories/{foreign.id}/").status_code, 404)
        self.assertEqual(
            self.client.patch(f"/api/categories/{foreign.id}/", {"name": "Mine"}, format="json").status_code, 404
        )
        self.assertEqual(self.client.delete(f"/api/categories/{foreign.id}/").status_code, 404)
        self.assertTrue(Category.objects.filter(id=foreign.id, name="Theirs").exists())

    def test_update_layout(self):
        a = Category.objects.create(name="A", user=self.user, order=0)
        b = Category.objects.create(name="B", user=self.user, order=1)
        foreign = Category.objects.create(name="Theirs", user=self.other, order=5)

        response = self.client.post(
            "/api/categories/update_layout/",
            {"layout": [{"id": b.id, "order": 0}, {"id": a.id, "order": 1}, {"id": foreign.id, "order": 0}]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([c["name"] for c in self.client.get("/api/categories/").data], ["B", "A"])
        foreign.refresh_from_db()
        self.assertEqual(foreign.order, 5)

    def test_deleting_a_category_keeps_its_habits(self):
        category = Category.objects.create(name="Health", user=self.user)
        habit = self.make_habit(category=category)

        self.client.delete(f"/api/categories/{category.id}/")

        habit.refresh_from_db()
        self.assertIsNone(habit.category)


class TagTests(HabitApiTestCase):
    def test_crud(self):
        created = self.client.post("/api/tags/", {"name": "Morning", "color": "#f59e0b"}, format="json")
        self.assertEqual(created.status_code, 201)
        tag = Tag.objects.get(id=created.data["id"])
        self.assertEqual(tag.user, self.user)

        updated = self.client.patch(f"/api/tags/{tag.id}/", {"name": "AM", "color": "#000000"}, format="json")
        self.assertEqual((updated.data["name"], updated.data["color"]), ("AM", "#000000"))

        self.assertEqual(self.client.delete(f"/api/tags/{tag.id}/").status_code, 204)

    def test_list_is_alphabetical_and_private(self):
        Tag.objects.create(name="Zen", user=self.user)
        Tag.objects.create(name="Alpha", user=self.user)
        Tag.objects.create(name="Theirs", user=self.other)

        self.assertEqual([t["name"] for t in self.client.get("/api/tags/").data], ["Alpha", "Zen"])

    def test_duplicate_names_are_rejected_cleanly(self):
        Tag.objects.create(name="Morning", user=self.user)
        other_tag = Tag.objects.create(name="Evening", user=self.user)

        created = self.client.post("/api/tags/", {"name": "Morning"}, format="json")
        renamed = self.client.patch(f"/api/tags/{other_tag.id}/", {"name": "Morning"}, format="json")

        self.assertEqual(created.status_code, 400)
        self.assertEqual(renamed.status_code, 400)
        self.assertEqual(Tag.objects.filter(user=self.user, name="Morning").count(), 1)

    def test_two_users_can_use_the_same_tag_name(self):
        Tag.objects.create(name="Morning", user=self.other)
        self.assertEqual(self.client.post("/api/tags/", {"name": "Morning"}, format="json").status_code, 201)

    def test_cannot_touch_someone_elses_tag(self):
        foreign = Tag.objects.create(name="Theirs", user=self.other)
        self.assertEqual(self.client.delete(f"/api/tags/{foreign.id}/").status_code, 404)

    def test_deleting_a_tag_removes_it_from_habits(self):
        tag = Tag.objects.create(name="Morning", user=self.user)
        habit = self.make_habit()
        habit.tags.add(tag)

        self.client.delete(f"/api/tags/{tag.id}/")

        self.assertEqual(habit.tags.count(), 0)
        self.assertTrue(Habit.objects.filter(id=habit.id).exists())


class HabitLifecycleTests(HabitApiTestCase):
    def test_update_fields_and_clear_category(self):
        category = Category.objects.create(name="Health", user=self.user)
        habit = self.make_habit("Water", "counter", category=category, unit="glasses")

        response = self.client.patch(
            f"/api/habits/{habit.id}/",
            {"name": "Hydration", "unit": None, "category_id": None, "color": "#112233"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        habit.refresh_from_db()
        self.assertEqual((habit.name, habit.unit, habit.category, habit.color), ("Hydration", None, None, "#112233"))

    def test_replace_tags(self):
        first = Tag.objects.create(name="A", user=self.user)
        second = Tag.objects.create(name="B", user=self.user)
        foreign = Tag.objects.create(name="Theirs", user=self.other)
        habit = self.make_habit()
        habit.tags.add(first)

        ok = self.client.patch(f"/api/habits/{habit.id}/", {"tag_ids": [second.id]}, format="json")
        denied = self.client.patch(f"/api/habits/{habit.id}/", {"tag_ids": [foreign.id]}, format="json")

        self.assertEqual(ok.status_code, 200)
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(list(habit.tags.all()), [second])

    def test_rejects_an_unknown_type(self):
        response = self.client.post("/api/habits/", {"name": "X", "habit_type": "weird"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_cannot_edit_someone_elses_habit(self):
        foreign = self.make_habit("Theirs", user=self.other)

        self.assertEqual(
            self.client.patch(f"/api/habits/{foreign.id}/", {"name": "Mine"}, format="json").status_code, 404
        )
        self.assertEqual(self.client.delete(f"/api/habits/{foreign.id}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/habits/{foreign.id}/archive/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/habits/{foreign.id}/unarchive/").status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual((foreign.name, foreign.archived), ("Theirs", False))

    def test_archive_and_unarchive(self):
        habit = self.make_habit()
        self.log(habit, 0)

        self.assertEqual(self.client.post(f"/api/habits/{habit.id}/archive/").status_code, 200)
        self.assertEqual(self.client.get("/api/habits/").data, [])
        self.assertEqual(len(self.client.get("/api/habits/", {"include_archived": "true"}).data), 1)

        self.assertEqual(self.client.post(f"/api/habits/{habit.id}/unarchive/").status_code, 200)
        self.assertEqual(len(self.client.get("/api/habits/").data), 1)
        self.assertEqual(habit.completions.count(), 1)  # history survives

    def test_archived_habits_can_be_edited_and_deleted(self):
        habit = self.make_habit(archived=True)
        self.log(habit, 0)

        self.assertEqual(self.client.delete(f"/api/habits/{habit.id}/").status_code, 204)

        self.assertFalse(Habit.objects.filter(id=habit.id).exists())
        self.assertEqual(Completion.objects.count(), 0)

    def test_archived_habits_are_left_out_of_stats(self):
        habit = self.make_habit(archived=True)
        self.log(habit, 0)

        self.assertEqual(self.summary()["boolean"], [])

    def test_date_range(self):
        empty = self.client.get("/api/habits/date_range/")
        self.assertIsNone(empty.data["start_date"])

        habit = self.make_habit()
        self.log(habit, 10)
        self.log(habit, 2)
        self.log(self.make_habit("Theirs", user=self.other), 50)

        data = self.client.get("/api/habits/date_range/").data

        self.assertEqual(str(data["start_date"]), (self.today - timedelta(days=10)).isoformat())
        self.assertEqual(str(data["end_date"]), (self.today - timedelta(days=2)).isoformat())


class DeleteAllDataTests(HabitApiTestCase):
    def populate(self, user):
        category = Category.objects.create(name="C", user=user)
        tag = Tag.objects.create(name="T", user=user)
        first = self.make_habit("One", user=user, category=category)
        second = self.make_habit("Two", user=user)
        first.tags.add(tag)
        Completion.objects.create(habit=first, date=self.today, value=1)
        HabitCorrelation.objects.create(
            user=user, habit1=first, habit2=second, sample_size=5,
            start_date=self.today, end_date=self.today, spearman_coefficient="0.9",
        )

    def test_deletes_everything_of_mine_and_nothing_else(self):
        self.populate(self.user)
        self.populate(self.other)

        response = self.client.post("/api/auth/delete-all-data/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["deleted"],
            {"categories": 1, "tags": 1, "habits": 2, "completions": 1, "correlations": 1},
        )
        for model in (Category, Tag, Habit, HabitCorrelation):
            self.assertEqual(model.objects.filter(user=self.user).count(), 0, model.__name__)
            self.assertGreater(model.objects.filter(user=self.other).count(), 0, model.__name__)
        self.assertEqual(Completion.objects.count(), 1)
        self.user.refresh_from_db()  # the account itself stays

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post("/api/auth/delete-all-data/").status_code, 401)


class SiteSettingsTests(HabitApiTestCase):
    def test_any_user_can_read(self):
        response = self.client.get("/api/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], 1)

    def test_only_admins_can_update(self):
        self.assertEqual(self.client.post("/api/settings/update_settings/", {}, format="json").status_code, 403)

        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/settings/update_settings/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SiteSettings.get_settings().updated_by, self.admin)

    def test_settings_are_a_singleton_that_cannot_be_deleted(self):
        first = SiteSettings.get_settings()
        SiteSettings().save()
        first.delete()

        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.get_settings().pk, 1)


class InviteLinkTests(HabitApiTestCase):
    def invite(self, **extra):
        defaults = {"created_by": self.admin, "expires_at": timezone.now() + timedelta(hours=24)}
        defaults.update(extra)
        return InviteLink.objects.create(**defaults)

    def validate(self, token):
        return self.client.get("/api/invite-links/validate/", {"token": str(token)})

    def test_regular_users_cannot_manage_invites(self):
        invite = self.invite()

        self.assertEqual(self.client.get("/api/invite-links/").status_code, 403)
        self.assertEqual(self.client.post("/api/invite-links/").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/invite-links/{invite.id}/").status_code, 403)

    def test_admin_creates_lists_and_deletes(self):
        self.client.force_authenticate(self.admin)

        created = self.client.post("/api/invite-links/")

        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.data["is_valid"])
        self.assertEqual(created.data["created_by_username"], "root")
        invite = InviteLink.objects.get(id=created.data["id"])
        lifetime = invite.expires_at - timezone.now()
        self.assertTrue(timedelta(hours=23, minutes=59) < lifetime <= timedelta(hours=24))

        self.assertEqual(len(self.client.get("/api/invite-links/").data), 1)
        self.assertEqual(self.client.delete(f"/api/invite-links/{invite.id}/").status_code, 204)
        self.assertEqual(InviteLink.objects.count(), 0)

    def test_list_shows_who_used_a_link(self):
        self.invite(used_by=self.user, used_at=timezone.now())
        self.client.force_authenticate(self.admin)

        row = self.client.get("/api/invite-links/").data[0]

        self.assertEqual(row["used_by_username"], "alice")
        self.assertTrue(row["is_used"])
        self.assertFalse(row["is_valid"])

    def test_validation_is_public(self):
        invite = self.invite()
        self.client.force_authenticate(None)

        self.assertEqual(self.validate(invite.token).data, {"valid": True})

    def test_validation_explains_why_a_link_is_refused(self):
        self.client.force_authenticate(None)
        expired = self.invite(expires_at=timezone.now() - timedelta(seconds=1))
        used = self.invite(used_by=self.user, used_at=timezone.now())

        self.assertIn("expired", self.validate(expired.token).data["detail"])
        self.assertIn("already used", self.validate(used.token).data["detail"])
        for token in ["3f0c1a7e-58b1-4c9a-9a51-0f8f6b1f2a11", "not-a-uuid"]:
            response = self.validate(token)
            self.assertEqual(response.status_code, 200, token)
            self.assertEqual(response.data["valid"], False, token)
        self.assertEqual(self.client.get("/api/invite-links/validate/").status_code, 400)

    def test_invite_state_properties(self):
        fresh = self.invite()
        expired = self.invite(expires_at=timezone.now() - timedelta(seconds=1))
        used = self.invite(used_by=self.user)

        self.assertEqual((fresh.is_expired, fresh.is_used, fresh.is_valid), (False, False, True))
        self.assertEqual((expired.is_expired, expired.is_valid), (True, False))
        self.assertEqual((used.is_used, used.is_valid), (True, False))
