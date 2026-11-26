import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT, "App")

# Make `Ai`, `Leaderboard` and `app` importable the same way App/app.py does.
for path in (ROOT, APP_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

# Keep the test leaderboard out of the real database file.
os.environ.setdefault("LEADERBOARD_DB_DIR", tempfile.mkdtemp(prefix="leaderboard-test-"))
