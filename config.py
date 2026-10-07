"""
Central configuration for the Online Transaction System.
Change admin credentials and security settings here only.
"""

import os
from pathlib import Path

# ── Project paths ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "transaction_system.db"
UPLOADS_DIR = BASE_DIR / "uploads" / "photos"
ASSETS_DIR = BASE_DIR / "assets"
STYLES_PATH = BASE_DIR / "styles.css"

# ── Admin credentials (ACADEMIC DEMO ONLY) ───────────────────────────────────
# Change these values to set your admin login for the demo portal.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin@Secure2026"

# ── Security ─────────────────────────────────────────────────────────────────
# AES-256 key (32 bytes). In production, load from a secure environment variable.
AES_SECRET_KEY = os.environ.get(
    "OTS_AES_KEY",
    "OnlineTxnSystem2026SecureKey!!",  # Exactly 32 characters for AES-256
)

# Password hashing salt (app-level; combined with user password before SHA-256)
PASSWORD_SALT = "OTS_SHA256_SALT_v1"

# ── Application settings ─────────────────────────────────────────────────────
APP_TITLE = "Online Transaction System with Cryptography"
APP_TAGLINE = "Secure Digital Banking with Advanced Cryptography"
CURRENCY_SYMBOL = "₹"
INITIAL_BALANCE = 0.0

# Photo upload constraints
PHOTO_MIN_SIZE_KB = 5
PHOTO_MAX_SIZE_KB = 2048
PHOTO_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# Virtual card validity (days after approval)
CARD_VALIDITY_DAYS = 1825  # ~5 years
