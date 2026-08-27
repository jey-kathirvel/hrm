import os
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SESSION_SECRET", "test-session-secret-at-least-thirty-two-characters")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.auth.models import User  # noqa: E402,F401
from app.config.settings import settings  # noqa: E402
from app.hrm.company import save_company_profile  # noqa: E402
from app.hrm.models import CompanyProfile, Employee  # noqa: E402
from app.hrm.payroll import calculate, email_payslip, render_pdf, save_payslip  # noqa: E402
from app.hrm.payroll_models import Payslip  # noqa: E402
from app.models.base import Base  # noqa: E402


class PayslipTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine); self.db = sessionmaker(bind=self.engine)()
        self.employee = Employee(employee_code="EMP00001", full_name="Jey", email="jey@example.com", department="Engineering", designation="Developer", join_date=date(2025,1,1), basic_salary=Decimal("30000"), is_active=True)
        self.db.add(self.employee); self.db.commit()
        save_company_profile(self.db, legal_name="ADS Private Limited", display_name="ADS", gstin="29ABCDE1234F1Z5", registered_address="Chennai")

    def tearDown(self): self.db.close(); self.engine.dispose()

    def test_manual_totals(self):
        result = calculate({"basic":"30000","hra":"12000","employee_pf":"1800","tds":"1000"})
        self.assertEqual(result["gross_earnings"], Decimal("42000.00")); self.assertEqual(result["net_pay"], Decimal("39200.00"))

    def test_negative_net_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            calculate({"basic":"100", "tds":"101"})

    def test_snapshot_and_duplicate_prevention(self):
        item = save_payslip(self.db, employee_id=self.employee.id, payroll_month="2026-08", employee_name="Edited Name", basic="30000", hra="10000", employee_pf="1800", working_days="31", paid_days="31")
        self.employee.full_name="Changed Later"; self.db.commit(); self.db.refresh(item)
        self.assertEqual(item.employee_name,"Edited Name"); self.assertEqual(item.net_pay,Decimal("38200.00")); self.assertEqual(item.company_name,"ADS")
        with self.assertRaisesRegex(ValueError,"already exists"):
            save_payslip(self.db, employee_id=self.employee.id, payroll_month="2026-08", basic="1")

    def test_sensitive_identifiers_are_masked(self):
        item=save_payslip(self.db,employee_id=self.employee.id,payroll_month="2026-11",basic="30000",bank_account_display="123456789012",pan_display="ABCDE1234F")
        self.assertEqual(item.bank_account_display,"********9012"); self.assertEqual(item.pan_display,"******234F")

    def test_pdf_is_generated(self):
        item=save_payslip(self.db,employee_id=self.employee.id,payroll_month="2026-09",basic="30000")
        pdf=render_pdf(item); self.assertTrue(pdf.startswith(b"%PDF")); self.assertGreater(len(pdf),1000)

    @patch("app.hrm.payroll.smtplib.SMTP_SSL")
    def test_email_uses_configured_sender_and_pdf_attachment(self, smtp):
        item=save_payslip(self.db,employee_id=self.employee.id,payroll_month="2026-10",basic="30000")
        old=settings.smtp_password; settings.smtp_password="secret"
        try: email_payslip(item,b"%PDF-test")
        finally: settings.smtp_password=old
        message=smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        self.assertEqual(message["From"],"tech@ads-ai.in"); self.assertEqual(message["To"],"jey@example.com"); self.assertEqual(len(list(message.iter_attachments())),1)


if __name__ == "__main__": unittest.main()
