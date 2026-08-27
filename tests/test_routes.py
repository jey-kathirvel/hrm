import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("SESSION_SECRET", "test-session-secret-at-least-thirty-two-characters")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import main  # noqa: E402
from app.auth.dependencies import login_required  # noqa: E402
from app.hrm.routes import form_int  # noqa: E402


class RouteRegressionTests(unittest.TestCase):
    def test_health_contract_is_stable(self):
        self.assertEqual(main.health(), {"status": "ok", "application": "ADS HRM"})

    def test_login_dependency_accepts_authenticated_session(self):
        request = MagicMock()
        request.session = {"user_id": 1}
        self.assertTrue(login_required(request))

    def test_expected_routes_remain_and_foundation_routes_exist(self):
        paths = {route.path for route in main.app.routes}
        for path in ("/health", "/login", "/hrm", "/hrm/employees", "/hrm/attendance", "/hrm/leaves", "/hrm/holidays", "/hrm/settings", "/hrm/settings/masters", "/hrm/settings/company", "/hrm/attendance/monthly", "/hrm/payslips"):
            self.assertIn(path, paths)

    def test_optional_employee_form_ids_accept_blank_values(self):
        self.assertIsNone(form_int("", "Employee ID"))
        self.assertIsNone(form_int("  ", "Reporting manager"))
        self.assertIsNone(form_int(None, "Work location"))

    def test_employee_form_ids_accept_selected_values(self):
        self.assertEqual(form_int("42", "Reporting manager"), 42)

    def test_required_and_invalid_employee_form_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Department is required"):
            form_int("", "Department", required=True)
        with self.assertRaisesRegex(ValueError, "Invalid reporting manager"):
            form_int("not-an-id", "Reporting manager")

    def test_base_layout_uses_persistent_iframe_navigation(self):
        layout = Path("app/templates/layouts/base.html").read_text(encoding="utf-8")
        self.assertIn('id="hrm-content-frame"', layout)
        self.assertIn("window.self !== window.top", layout)
        self.assertIn("event.preventDefault()", layout)
        self.assertIn("frame.src = path", layout)


if __name__ == "__main__":
    unittest.main()
