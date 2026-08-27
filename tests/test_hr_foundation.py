import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SESSION_SECRET", "test-session-secret-at-least-thirty-two-characters")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.auth.models import User  # noqa: E402,F401
from app.hrm.models import (  # noqa: E402
    Attendance, AttendanceRegularization, Department, Designation, Employee,
    Holiday, LeaveBalance, LeaveRequest, LeaveType, WorkLocation,
)
from app.hrm.service import HRMService  # noqa: E402
from app.models.base import Base  # noqa: E402


class HRFoundationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.department = Department(name="Engineering", code="ENG")
        self.designation = Designation(name="Developer", code="DEV")
        self.location = WorkLocation(name="Chennai")
        self.paid_leave = LeaveType(code="CASUAL", name="Casual Leave", requires_balance=True)
        self.unpaid_leave = LeaveType(code="UNPAID", name="Unpaid Leave", is_paid=False, requires_balance=False)
        self.db.add_all([self.department, self.designation, self.location, self.paid_leave, self.unpaid_leave])
        self.db.commit()
        self.employee = HRMService.save_employee(
            self.db, full_name="Test Employee", department_id=self.department.id,
            designation_id=self.designation.id, work_location_id=self.location.id,
            employment_type="FULL_TIME", join_date=date(2026, 1, 1),
            basic_salary=Decimal("10000"), is_active=True,
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_managed_masters_keep_legacy_strings_in_sync(self):
        self.assertEqual(self.employee.department, "Engineering")
        self.assertEqual(self.employee.designation, "Developer")
        self.assertEqual(self.employee.work_location.name, "Chennai")

    def test_paid_leave_validates_and_consumes_balance_once(self):
        HRMService.set_leave_balance(self.db, self.employee.id, self.paid_leave.id, 2026, Decimal("2"), Decimal("0"), Decimal("0"))
        leave = HRMService.create_leave(self.db, self.employee.id, self.paid_leave.id, date(2026, 3, 2), date(2026, 3, 3), "Personal")
        HRMService.update_leave_status(self.db, leave.id, "APPROVED")
        HRMService.update_leave_status(self.db, leave.id, "APPROVED")
        balance = self.db.query(LeaveBalance).one()
        self.assertEqual(balance.used, Decimal("2.00"))
        self.assertTrue(leave.balance_applied)

    def test_paid_leave_rejects_insufficient_balance(self):
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            HRMService.create_leave(self.db, self.employee.id, self.paid_leave.id, date(2026, 4, 1), date(2026, 4, 1))

    def test_unpaid_leave_does_not_require_balance(self):
        leave = HRMService.create_leave(self.db, self.employee.id, self.unpaid_leave.id, date(2026, 5, 1), date(2026, 5, 2))
        self.assertEqual(leave.leave_type, "UNPAID")

    def test_overlap_validation_preserves_existing_request(self):
        HRMService.create_leave(self.db, self.employee.id, self.unpaid_leave.id, date(2026, 6, 1), date(2026, 6, 3))
        with self.assertRaisesRegex(ValueError, "overlaps"):
            HRMService.create_leave(self.db, self.employee.id, self.unpaid_leave.id, date(2026, 6, 3), date(2026, 6, 4))

    def test_regularization_approval_upserts_attendance(self):
        request = HRMService.request_regularization(self.db, employee_id=self.employee.id, attendance_date=date(2026, 7, 1), requested_status="WFH", reason="Worked remotely")
        HRMService.review_regularization(self.db, request.id, "APPROVED")
        attendance = self.db.query(Attendance).one()
        self.assertEqual(attendance.status, "WFH")
        self.assertEqual(request.status, "APPROVED")

    def test_holiday_duplicate_is_rejected(self):
        HRMService.save_holiday(self.db, name="Founders Day", holiday_date=date(2026, 8, 1), category="COMPANY", is_optional=False)
        with self.assertRaisesRegex(ValueError, "already exists"):
            HRMService.save_holiday(self.db, name="Founders Day", holiday_date=date(2026, 8, 1), category="COMPANY", is_optional=False)


if __name__ == "__main__":
    unittest.main()
