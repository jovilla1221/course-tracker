#!/usr/bin/env python3
"""Build courses.json, commit, push to gh-pages. Run from cron."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/ec2-user/course-tracker")
BUILDER = REPO / "build_courses.py"


def run(cmd):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def main():
    print("[1/3] Building courses.json...")
    rc, out, err = run(["python3", str(BUILDER)])
    print(out, end="")
    if err:
        print(err, end="", file=sys.stderr)
    if rc != 0:
        print("Build failed", file=sys.stderr)
        return rc

    courses_json = REPO / "courses.json"
    if not courses_json.exists():
        print("courses.json missing", file=sys.stderr)
        return 1
    payload = json.loads(courses_json.read_text())
    total = payload.get("total", 0)

    print(f"[2/3] Committing {total} courses...")
    run(["git", "add", "courses.json", "index.html"])
    rc, out, err = run(["git", "diff", "--cached", "--stat"])
    if rc != 0 or not out.strip():
        print("No changes to commit")
        return 0
    msg = f"Auto-update: {total} courses ({payload.get('from_feeds', 0)} from feeds)"
    rc, _, err = run(["git", "commit", "-m", msg])
    if rc != 0:
        print(f"Commit failed: {err}", file=sys.stderr)
        return rc

    print("[3/3] Pushing to gh-pages...")
    rc, out, err = run(["git", "push", "origin", "gh-pages"])
    if rc != 0:
        print(f"Push failed: {err}", file=sys.stderr)
        return rc
    print(out, end="")
    print("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())