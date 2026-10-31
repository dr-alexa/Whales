import html

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config import settings
from keyboards import MENU

router = Router()


class Feedback(StatesGroup):
    waiting = State()


@router.message(Command("feedback"))
@router.message(F.text == MENU["feedback"])
async def feedback_start(message: Message, state: FSMContext):
    await state.set_state(Feedback.waiting)
    await message.answer("💬 Напиши отзыв или идею — можно приложить фото, аудио или видео.\nОтмена: /cancel")


@router.message(Command("cancel"), Feedback.waiting)
async def feedback_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Окей, отменено 🌊")


@router.message(Feedback.waiting)
async def feedback_forward(message: Message, state: FSMContext, bot: Bot):
    # Нажал кнопку меню / другую команду — выходим из режима и отдаём апдейт дальше.
    if message.text and (message.text.startswith("/") or message.text in MENU.values()):
        await state.clear()
        raise SkipHandler
    await state.clear()
    if not settings.admin_id:
        await message.answer("Обратная связь пока не настроена 🙈")
        return
    u = message.from_user
    await bot.send_message(
        settings.admin_id,
        f"📩 Отзыв от <b>{html.escape(u.full_name)}</b> (@{u.username or '—'}, id <code>{u.id}</code>)")
    await message.copy_to(settings.admin_id)  # копирует текст и любое медиа
    await message.answer("Спасибо! 🐳 Твой отзыв передан команде.")
