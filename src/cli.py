import argparse
import os

from pydantic import ValidationError

from src.db.connection import SessionLocal
from src.user.schemas import UserCreate
from src.user.service import bootstrap_admin


def _bootstrap_admin() -> int:
    missing = [
        name
        for name in (
            "BOOTSTRAP_ADMIN_USERNAME",
            "BOOTSTRAP_ADMIN_EMAIL",
            "BOOTSTRAP_ADMIN_PASSWORD",
        )
        if not os.getenv(name)
    ]
    if missing:
        print(f"Missing required deployment secrets: {', '.join(missing)}")
        return 2
    try:
        payload = UserCreate(
            username=os.environ["BOOTSTRAP_ADMIN_USERNAME"],
            email=os.environ["BOOTSTRAP_ADMIN_EMAIL"],
            password=os.environ["BOOTSTRAP_ADMIN_PASSWORD"],
        )
    except ValidationError as exc:
        print(f"Invalid bootstrap administrator configuration: {exc}")
        return 2

    db = SessionLocal()
    try:
        user, error = bootstrap_admin(db, payload)
        if error is not None:
            print(f"Administrator bootstrap refused: {error}")
            return 1
        print(f"Created administrator {user.username} (id={user.id}).")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Lab storage deployment commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "bootstrap-admin",
        help="Create the first admin from BOOTSTRAP_ADMIN_* deployment secrets",
    )
    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        return _bootstrap_admin()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
