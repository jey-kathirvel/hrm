import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.hrm.models import CompanyProfile

GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
LOGO_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
)


def normalize_gstin(value: str | None):
    gstin = (value or "").strip().upper()
    if not gstin:
        return None
    if not GSTIN_PATTERN.fullmatch(gstin):
        raise ValueError("GSTIN must be a valid 15-character Indian GSTIN")
    return gstin


def detect_logo_extension(content: bytes):
    for signature, extension in LOGO_SIGNATURES:
        if content.startswith(signature):
            return extension
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("Logo must be a PNG, JPEG, or WebP image")


def store_company_logo(content: bytes, upload_root: Path | None = None):
    if not content:
        raise ValueError("Uploaded logo is empty")
    if len(content) > settings.max_logo_bytes:
        raise ValueError("Logo exceeds the configured upload limit")
    extension = detect_logo_extension(content)
    root = (upload_root or settings.upload_root).resolve()
    company_dir = (root / "company").resolve()
    if root not in company_dir.parents:
        raise ValueError("Invalid logo storage path")
    company_dir.mkdir(parents=True, exist_ok=True)
    destination = company_dir / f"company-logo{extension}"
    temporary = company_dir / f".company-logo{extension}.tmp"
    temporary.write_bytes(content)
    temporary.replace(destination)
    for stale_extension in (".png", ".jpg", ".webp"):
        stale = company_dir / f"company-logo{stale_extension}"
        if stale != destination and stale.exists():
            stale.unlink()
    return destination.relative_to(root).as_posix()


def get_company_profile(db: Session):
    return db.get(CompanyProfile, 1)


def save_company_profile(db: Session, *, logo_path=None, **data):
    legal_name = (data.get("legal_name") or "").strip()
    if not legal_name:
        raise ValueError("Legal company name is required")
    profile = get_company_profile(db)
    if profile is None:
        profile = CompanyProfile(id=1, legal_name=legal_name)
        db.add(profile)
    normalized = {
        "legal_name": legal_name,
        "display_name": (data.get("display_name") or "").strip() or None,
        "gstin": normalize_gstin(data.get("gstin")),
        "registered_address": (data.get("registered_address") or "").strip() or None,
        "city": (data.get("city") or "").strip() or None,
        "state": (data.get("state") or "").strip() or None,
        "postal_code": (data.get("postal_code") or "").strip() or None,
        "phone": (data.get("phone") or "").strip() or None,
        "email": (data.get("email") or "").strip() or None,
        "website": (data.get("website") or "").strip() or None,
    }
    for key, value in normalized.items():
        setattr(profile, key, value)
    if logo_path is not None:
        profile.logo_path = logo_path
    db.commit()
    db.refresh(profile)
    return profile
