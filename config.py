from flask_mail import Mail
import urllib.parse

mail = Mail()

# ── Secret key ────────────────────────────────
SECRET_KEY = "hms-super-secret-key-change-in-prod"

# ── Database Configuration ────────────────────
import os
from flask_mail import Mail

mail = Mail()

SECRET_KEY = os.environ.get("SECRET_KEY")

SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

SQLALCHEMY_TRACK_MODIFICATIONS = False


# ── Pagination ────────────────────────────────
PAGINATION = {
    "default":      10,
    "patients":     10,
    "doctors":      10,
    "appointments": 10,
    "billing":      10,
    "audit_logs":   15,
    "users":        10,
    "departments":  10,
    "treatments":   10,
}

# ── Mail Configuration ───────────────────────
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True

MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

MAIL_DEFAULT_SENDER = (
    "HMS",
    os.environ.get("MAIL_USERNAME")
)

# ── App meta ─────────────────────────────────
APP_NAME = "Hospital Management System"
APP_ABBR = "HMS"