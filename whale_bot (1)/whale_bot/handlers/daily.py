from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards import MENU
from senders import send_question
from services import effective_streak, get_or_create_user, pick_daily_question, today

router = Router()


@router.message(F.text == MENU["daily"])
@router.message(Command("daily"))
async def daily(message: Message, session: AsyncSession, bot: Bot):
    user = await get_or_create_user(session, message.from_user)
    if user.last_daily_date == today():
        await message.answer(f"✅ Сегодняшнее задание уже выполнено!\n🔥 Серия: {effective_streak(user)} дн.\n"
                             "Возвращайся завтра — киты приготовят новый вопрос 🐋")
        return
    q = await pick_daily_question(session, user.id)
    if q is None:
        await message.answer("🎉 Ты прошёл все вопросы! Скоро появятся новые.")
        return
    await send_question(bot, message.chat.id, q, mode="d")
