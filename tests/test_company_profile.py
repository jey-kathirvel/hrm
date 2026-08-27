import os
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SESSION_SECRET", "test-session-secret-at-least-thirty-two-characters")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.auth.models import User  # noqa: E402,F401
from app.config.settings import settings  # noqa: E402
from app.hrm.company import normalize_gstin, save_company_profile, store_company_logo  # noqa: E402
from app.hrm.models import CompanyProfile  # noqa: E402
from app.models.base import Base  # noqa: E402


class CompanyProfileTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_gstin_is_normalized_and_validated(self):
        self.assertEqual(normalize_gstin("29abcde1234f1z5"), "29ABCDE1234F1Z5")
        with self.assertRaisesRegex(ValueError, "valid 15-character"):
            normalize_gstin("NOT-A-GSTIN")

    def test_profile_is_created_and_updated_as_singleton(self):
        first = save_company_profile(self.db, legal_name="ADS Private Limited", gstin="29ABCDE1234F1Z5")
        second = save_company_profile(self.db, legal_name="ADS Private Limited", display_name="ADS", gstin="29ABCDE1234F1Z5")
        self.assertEqual(first.id, 1)
        self.assertEqual(second.id, 1)
        self.assertEqual(self.db.query(CompanyProfile).count(), 1)
        self.assertEqual(second.display_name, "ADS")

    def test_database_enforces_singleton(self):
        self.db.add(CompanyProfile(id=2, legal_name="Another Company"))
        with self.assertRaises(IntegrityError):
            self.db.commit()

    def test_png_logo_is_stored_under_safe_relative_path(self):
        with tempfile.TemporaryDirectory() as directory:
            content = b"\x89PNG\r\n\x1a\n" + b"test-image-data"
            relative = store_company_logo(content, Path(directory))
            self.assertEqual(relative, "company/company-logo.png")
            self.assertEqual((Path(directory) / relative).read_bytes(), content)

    def test_logo_rejects_disguised_and_oversize_files(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "PNG, JPEG, or WebP"):
                store_company_logo(b"<svg><script>alert(1)</script></svg>", Path(directory))
            with self.assertRaisesRegex(ValueError, "configured upload limit"):
                store_company_logo(b"\x89PNG\r\n\x1a\n" + b"x" * settings.max_logo_bytes, Path(directory))


if __name__ == "__main__":
    unittest.main()
