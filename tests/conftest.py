import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent / "test_scheduler.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["CALENDAR_MODE"] = "demo"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "change-me-before-production"
os.environ["SECRET_KEY"] = "dev-only-change-me"
os.environ["GOOGLE_ALLOW_BROWSER_OAUTH"] = "false"

# Several unit tests call scheduler functions without entering FastAPI's lifespan.
from backend.database.models import init_db

init_db()
