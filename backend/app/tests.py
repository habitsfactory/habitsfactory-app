from django.test import TestCase
from rest_framework.test import APIClient


class HealthCheckTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check_returns_ok(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_check_no_auth_required(self):
        # Ensure endpoint works without authentication
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)

    def test_health_check_post_not_allowed(self):
        response = self.client.post("/api/health/")
        self.assertEqual(response.status_code, 405)
