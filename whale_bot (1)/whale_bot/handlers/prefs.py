import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards import MENU, RemindCb, reminder_kb
from services import get_or_create_user

router = Router()
TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def settings_text(user) -> str:
    state = f"🔔 каждый день в <b>{user.reminder_time}</b>" if user.reminders_enabled else "🔕 выключены"
    return (f"⚙️ <b>Настройки</b>\n\nНапоминания: {state}\n\n"
            "Выбери время кнопкой или отправь свой вариант: <code>/settime 19:30</code>")


@router.message(F.text == MENU["settings"])
@router.message(Command("settings"))
async def settings_menu(message: Message, session: AsyncSession):
    user = await get_or_create_user(session, message.from_user)
    await message.answer(settings_text(user), reply_markup=reminder_kb())


@router.callback_query(RemindCb.filter())
async def set_reminder(cb: CallbackQuery, callback_data: RemindCb, session: AsyncSession):
    user = await get_or_create_user(session, cb.from_user)
    if callback_data.value == "off":
        user.reminders_enabled = False
    else:
        v = callback_data.value
        user.reminder_time, user.reminders_enabled = f"{v[:2]}:{v[2:]}", True
    try:
        await cb.message.edit_text(settings_text(user), reply_markup=reminder_kb())
    except TelegramBadRequest:  # то же самое значение — Telegram ругается «not modified»
        pass
    await cb.answer("Сохранено ✅")


@router.message(Command("settime"))
async def set_time(message: Message, command: CommandObject, session: AsyncSession):
    m = TIME_RE.match((command.args or "").strip())
    if not m:
        await message.answer("Формат: <code>/settime 19:30</code>")
        return
    user = await get_or_create_user(session, message.from_user)
    user.reminder_time, user.reminders_enabled = f"{int(m[1]):02d}:{m[2]}", True
    await message.answer(f"🔔 Буду напоминать в <b>{user.reminder_time}</b> 🐋")
