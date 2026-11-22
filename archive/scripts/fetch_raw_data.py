#!/usr/bin/env python3
"""Download Dave Cook OpenRocket component DB (.orc) + certified motor DB (motors.db.gz) into data/raw/."""
import sys
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ORC_DIR = RAW / "orc"

ORC_REPO = "https://github.com/openrocket/openrocket-database.git"
ORC_FALLBACK_REPO = "https://github.com/dbcook/openrocket-database.git"
MOTOR_DB_URL = "https://openrocket.github.io/motor-database/motors.db.gz"
MOTOR_META_URL = "https://openrocket.github.io/motor-database/metadata.json"

def run(cmd, cwd=None):
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    ORC_DIR.mkdir(parents=True, exist_ok=True)

    repo_dir = RAW / "openrocket-database"
    if not (repo_dir / ".git").exists():
        try:
            run(["git", "clone", "--depth", "1", ORC_REPO, str(repo_dir)])
        except subprocess.CalledProcessError:
            print(f"primary {ORC_REPO} failed, trying {ORC_FALLBACK_REPO}", file=sys.stderr)
            run(["git", "clone", "--depth", "1", ORC_FALLBACK_REPO, str(repo_dir)])
    else:
        print(f"exists: {repo_dir}, pulling latest")
        try:
            run(["git", "-C", str(repo_dir), "pull", "--ff-only"])
        except subprocess.CalledProcessError as e:
            print(f"pull failed (offline OK): {e}")

    # copy .orc/.ORC out of repo
    n = 0
    for f in sorted((repo_dir / "meta" / "orc").glob("*")):
        if f.is_file() and f.suffix.lower() == ".orc":
            dest = ORC_DIR / f.name
            dest.write_bytes(f.read_bytes())
            n += 1
    print(f"orc files staged: {n} -> {ORC_DIR}")
    if n == 0:
        raise SystemExit("no .orc files found — clone failed?")

    for url, out in [(MOTOR_DB_URL, RAW / "motors.db.gz"), (MOTOR_META_URL, RAW / "metadata.json")]:
        print(f"downloading {url} -> {out}")
        run(["curl", "-sL", url, "-o", str(out)])
        print(f"  {out.stat().st_size} bytes")

    print("fetch OK")

if __name__ == "__main__":
    main()
