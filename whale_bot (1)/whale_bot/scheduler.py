import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import or_, select

from config import settings
from database import SessionMaker
from models import User
from services import today

log = logging.getLogger(__name__)
REMINDER = "🌊 Привет! Твои киты скучают. Пора пройти ежедневное задание!"


async def send_reminders(bot: Bot) -> None:
    """Каждую минуту: находим тех, у кого сейчас время напоминания и задание не выполнено."""
    hhmm = datetime.now(ZoneInfo(settings.tz)).strftime("%H:%M")
    async with SessionMaker() as session:
        users = (await session.scalars(
            select(User).where(
                User.reminders_enabled.is_(True),
                User.reminder_time == hhmm,
                or_(User.last_daily_date.is_(None), User.last_daily_date < today()),
            ))).all()
        for u in users:
            text = REMINDER + (f"\n🔥 Не потеряй серию в {u.current_streak} дн.!" if u.current_streak else "")
            try:
                await bot.send_message(u.id, text)
            except TelegramForbiddenError:      # бот заблокирован — больше не беспокоим
                u.reminders_enabled = False
            except TelegramAPIError as e:
                log.warning("reminder to %s failed: %s", u.id, e)
            await asyncio.sleep(0.05)           # мягко держимся в лимитах Telegram
        await session.commit()


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.tz))
    scheduler.add_job(send_reminders, CronTrigger(minute="*"), args=[bot],
                      max_instances=1, coalesce=True)
    return scheduler
