import os

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "cambiame")
DEFAULT_SLUG = os.getenv("DEFAULT_SLUG", "justicia9373")
DB_PATH = os.getenv("DB_PATH", "./data/app.db")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT", "")