import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("SESSION_SECRET", "test-session-secret-at-least-thirty-two-characters")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import main  # noqa: E402
from app.auth.dependencies import login_required  # noqa: E402


class RouteRegressionTests(unittest.TestCase):
    def test_health_contract_is_stable(self):
        self.assertEqual(main.health(), {"status": "ok", "application": "ADS HRM"})

    def test_login_dependency_accepts_authenticated_session(self):
        request = MagicMock()
        request.session = {"user_id": 1}
        self.assertTrue(login_required(request))

    def test_expected_routes_remain_and_foundation_routes_exist(self):
        paths = {route.path for route in main.app.routes}
        for path in ("/health", "/login", "/hrm", "/hrm/employees", "/hrm/attendance", "/hrm/leaves", "/hrm/holidays", "/hrm/settings/masters", "/hrm/settings/company", "/hrm/attendance/monthly", "/hrm/payslips"):
            self.assertIn(path, paths)


if __name__ == "__main__":
    unittest.main()
