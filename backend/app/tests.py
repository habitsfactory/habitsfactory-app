from django.test import TestCase
from rest_framework.test import APIClient


class HealthEndpointTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_returns_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_no_auth_required(self):
        # Ensure unauthenticated requests succeed
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)

    def test_health_only_allows_get(self):
        response = self.client.post("/health/")
        self.assertEqual(response.status_code, 405)
