import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database import DbSessionMiddleware, init_db
from handlers import admin, daily, feedback, menu, payments, prefs, quiz, referral
from scheduler import setup_scheduler


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not settings.bot_token:
        raise SystemExit("Укажите BOT_TOKEN в .env")
    await init_db()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(DbSessionMiddleware())
    # payments первым: successful_payment не должен попасть в FSM-хендлер отзыва;
    # feedback вторым: он перехватывает сообщения только в состоянии ожидания отзыва
    dp.include_routers(payments.router, feedback.router, admin.router, menu.router, referral.router,
                       daily.router, quiz.router, prefs.router)

    scheduler = setup_scheduler(bot)
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)  # allowed_updates (в т.ч. poll_answer) определяются автоматически


if __name__ == "__main__":
    asyncio.run(main())
