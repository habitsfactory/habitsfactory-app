"""Accounts: first-admin setup, invite-only registration, login, profile."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from ..models import InviteLink, SiteSettings

PASSWORD = "correct-horse-battery"


class RegisterAdminTests(APITestCase):
    URL = "/api/auth/register-admin/"

    def payload(self, **overrides):
        data = {
            "username": "root",
            "email": "root@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return data

    def test_reports_whether_an_admin_exists(self):
        self.assertEqual(
            self.client.get(self.URL).data,
            {"superuser_exists": False, "redirect_url": None},
        )

        User.objects.create_superuser("root", "root@example.com", PASSWORD)

        self.assertEqual(
            self.client.get(self.URL).data,
            {"superuser_exists": True, "redirect_url": "/register"},
        )

    def test_creates_the_first_admin(self):
        response = self.client.post(self.URL, self.payload(), format="json")

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="root")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(SiteSettings.get_settings().updated_by, user)
        self.assertNotIn("password", str(response.data))

    def test_refuses_a_second_admin(self):
        User.objects.create_superuser("root", "root@example.com", PASSWORD)

        response = self.client.post(
            self.URL, self.payload(username="evil", email="evil@example.com"), format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["redirect_url"], "/register")
        self.assertFalse(User.objects.filter(username="evil").exists())

    def test_validation_errors(self):
        User.objects.create_user("taken", "taken@example.com", PASSWORD)
        cases = [
            ({"username": ""}, "username"),
            ({"email": ""}, "email"),
            ({"password1": "", "password2": ""}, "password1"),
            ({"password2": "something-else"}, "password2"),
            ({"password1": "short", "password2": "short"}, "password1"),
            ({"username": "taken"}, "username"),
            ({"email": "taken@example.com"}, "email"),
        ]
        for overrides, field in cases:
            response = self.client.post(self.URL, self.payload(**overrides), format="json")
            self.assertEqual(response.status_code, 400, overrides)
            self.assertIn(field, response.data, overrides)
        self.assertFalse(User.objects.filter(is_superuser=True).exists())


class InviteOnlyRegistrationTests(APITestCase):
    URL = "/api/auth/registration/"

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser("root", "root@example.com", PASSWORD)

    def invite(self, **extra):
        defaults = {"created_by": self.admin, "expires_at": timezone.now() + timedelta(hours=24)}
        defaults.update(extra)
        return InviteLink.objects.create(**defaults)

    def register(self, token=None, username="newbie", email="newbie@example.com"):
        data = {"username": username, "email": email, "password1": PASSWORD, "password2": PASSWORD}
        if token is not None:
            data["invite_token"] = str(token)
        return self.client.post(self.URL, data, format="json")

    def test_registers_with_a_valid_invite_and_consumes_it(self):
        invite = self.invite()

        response = self.register(invite.token)

        self.assertIn(response.status_code, (201, 204))
        user = User.objects.get(email="newbie@example.com")
        self.assertFalse(user.is_staff)
        invite.refresh_from_db()
        self.assertEqual(invite.used_by, user)
        self.assertIsNotNone(invite.used_at)
        self.assertFalse(invite.is_valid)

    def test_an_invite_works_only_once(self):
        invite = self.invite()
        self.register(invite.token)
        self.client.logout()
        self.client.cookies.clear()

        response = self.register(invite.token, username="second", email="second@example.com")

        self.assertEqual(response.status_code, 403)
        self.assertIn("already been used", response.data["detail"])
        self.assertFalse(User.objects.filter(username="second").exists())

    def test_requires_a_token(self):
        self.assertEqual(self.register().status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_rejects_unknown_and_malformed_tokens(self):
        for token in ["3f0c1a7e-58b1-4c9a-9a51-0f8f6b1f2a11", "not-a-uuid"]:
            response = self.register(token)
            self.assertEqual(response.status_code, 403, token)
        self.assertEqual(User.objects.count(), 1)

    def test_rejects_an_expired_invite(self):
        invite = self.invite(expires_at=timezone.now() - timedelta(minutes=1))

        response = self.register(invite.token)

        self.assertEqual(response.status_code, 403)
        self.assertIn("expired", response.data["detail"])

    def test_a_failed_registration_does_not_burn_the_invite(self):
        invite = self.invite()

        response = self.client.post(
            self.URL,
            {
                "username": "newbie",
                "email": "newbie@example.com",
                "password1": PASSWORD,
                "password2": "does-not-match",
                "invite_token": str(invite.token),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        invite.refresh_from_db()
        self.assertTrue(invite.is_valid)


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("alice", "alice@example.com", PASSWORD)

    def login(self, email="alice@example.com", password=PASSWORD):
        return self.client.post(
            "/api/auth/login/", {"email": email, "password": password}, format="json"
        )

    def test_login_sets_cookies_that_authenticate_later_requests(self):
        self.assertEqual(self.client.get("/api/auth/user/").status_code, 401)

        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertIn("auth-token", response.cookies)
        self.assertIn("refresh-token", response.cookies)
        me = self.client.get("/api/auth/user/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["email"], "alice@example.com")

    def test_wrong_password_is_rejected(self):
        response = self.login(password="nope-nope-nope")

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("auth-token", response.cookies)

    def test_unknown_email_is_rejected(self):
        self.assertEqual(self.login(email="ghost@example.com").status_code, 400)

    def test_logout_ends_the_session(self):
        self.login()

        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 200)

        self.assertEqual(self.client.get("/api/auth/user/").status_code, 401)

    def test_refresh_issues_a_new_access_token_from_the_cookie(self):
        self.login()

        response = self.client.post("/api/auth/token/refresh/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/user/").status_code, 200)

    def test_repeated_failures_get_blocked(self):
        statuses = [self.login(password="wrong-password").status_code for _ in range(8)]

        self.assertEqual(statuses[0], 400)
        # Throttled (429) and/or locked out by django-axes
        self.assertNotEqual(statuses[-1], 400)
        # ...and the right password no longer gets through either
        self.assertNotEqual(self.login().status_code, 200)


class ProfileTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        self.client.force_authenticate(self.user)

    def test_user_info(self):
        response = self.client.get("/api/auth/user/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "id": self.user.id,
                "username": "alice",
                "email": "alice@example.com",
                "first_name": "",
                "last_name": "",
                "is_staff": False,
                "is_superuser": False,
            },
        )

    def test_user_info_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/auth/user/").status_code, 401)

    def test_email_can_be_changed(self):
        response = self.client.patch("/api/auth/user/", {"email": "new@example.com"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "new@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")

    def test_login_follows_the_new_email(self):
        self.client.patch("/api/auth/user/", {"email": "new@example.com"}, format="json")
        self.client.force_authenticate(None)

        def login(email):
            return self.client.post("/api/auth/login/", {"email": email, "password": PASSWORD}, format="json")

        self.assertEqual(login("alice@example.com").status_code, 400)
        self.assertEqual(login("new@example.com").status_code, 200)

    def test_email_change_is_validated(self):
        User.objects.create_user("bob", "bob@example.com", PASSWORD)
        for email in ["", "not-an-email", "bob@example.com", "BOB@example.com"]:
            response = self.client.patch("/api/auth/user/", {"email": email}, format="json")
            self.assertEqual(response.status_code, 400, email)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "alice@example.com")

    def test_profile_update_cannot_escalate_privileges(self):
        self.client.patch(
            "/api/auth/user/",
            {"email": "new@example.com", "is_staff": True, "is_superuser": True, "username": "root"},
            format="json",
        )

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.username, "alice")

    def change_password(self, old, new="another-long-passphrase"):
        return self.client.post(
            "/api/auth/password/change/",
            {"old_password": old, "new_password1": new, "new_password2": new},
            format="json",
        )

    def test_password_change(self):
        self.assertEqual(self.change_password(PASSWORD).status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("another-long-passphrase"))

    def test_password_change_requires_the_current_password(self):
        response = self.change_password("not-my-password")

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_password_change_rejects_weak_passwords(self):
        self.assertEqual(self.change_password(PASSWORD, new="12345678").status_code, 400)
