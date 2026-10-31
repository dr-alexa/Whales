import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_id: int = int(os.getenv("ADMIN_ID", "0"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///whale_bot.db")
    tz: str = os.getenv("TZ_NAME", "Europe/Moscow")  # часовой пояс «дней» и напоминаний


settings = Settings()
