"""Crée le compte démo Apple Review sur le VPS (mytimalove.com)."""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMALOVE = os.path.join(BASE, "timalove")


def main() -> None:
    os.chdir(TIMALOVE)
    cmd = [
        sys.executable,
        "manage.py",
        "create_apple_review_account",
        "--reset-partners",
    ]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=TIMALOVE)
    print("")
    print("N'oubliez pas sur le VPS (.env) :")
    print("  QUOTA_EXEMPT_EMAILS=apple.review@timalove.local,gooteste@gmail.com")


if __name__ == "__main__":
    main()
