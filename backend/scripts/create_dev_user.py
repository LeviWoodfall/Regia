"""Utility to ensure a development login exists for automated tests/CI."""

import argparse
from app.config import load_config
from app.database import Database
from app.auth import AuthManager


def ensure_dev_user(username: str, password: str, email: str, display_name: str):
    settings = load_config()
    db = Database(settings.db_path)
    auth = AuthManager(db, settings.auth.session_timeout_minutes)

    existing = db.execute("SELECT id FROM users WHERE username = ?", (username,))
    if not existing:
        auth.create_user(username, password, email, display_name)
        print(f"Created dev user '{username}'")
    else:
        auth.set_password(username, password)
        print(f"Updated password for dev user '{username}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed/update a development login")
    parser.add_argument("--username", default="dev")
    parser.add_argument("--password", default="DevPassword!123")
    parser.add_argument("--email", default="dev@example.com")
    parser.add_argument("--display-name", default="Dev User")
    args = parser.parse_args()
    ensure_dev_user(args.username, args.password, args.email, args.display_name)
