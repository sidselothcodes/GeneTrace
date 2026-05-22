import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.pop("OPENAI_API_KEY", None)
