from urllib.parse import quote, urlencode

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards import MENU
from services import REF_BONUS, REF_INVITEE_BONUS, get_or_create_user

router = Router()


@router.message(F.text == MENU["invite"])
@router.message(Command("invite"))
async def invite(message: Message, session: AsyncSession, bot: Bot):
    user = await get_or_create_user(session, message.from_user)
    me = await bot.me()
    link = f"https://t.me/{me.username}?start=ref_{user.id}"
    share = "https://t.me/share/url?" + urlencode(
        {"url": link, "text": "🐋 Заходи в КитоКвиз — узнаем всё о китах и дельфинах!"}, quote_via=quote)

    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Поделиться с друзьями", url=share)
    await message.answer(
        "👥 <b>Приглашай друзей!</b>\n\n"
        f"Твоя ссылка:\n<code>{link}</code>\n\n"
        f"Когда друг ответит на первый вопрос, ты получишь <b>+{REF_BONUS} 🐚</b>, а он — <b>+{REF_INVITEE_BONUS} 🐚</b>.\n"
        "5 друзей — достижение «🤝 Посол океана».\n\n"
        f"Уже приглашено: <b>{user.referrals_count}</b>",
        reply_markup=kb.as_markup())
