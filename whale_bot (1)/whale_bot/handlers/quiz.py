import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, PollAnswer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards import MENU, AnswerCb, QuizCb, next_kb, quiz_menu_kb
from models import Question
from senders import POLLS, notify_referrer, result_text, send_blitz, send_question
from services import get_or_create_user, pick_quiz_question, record_answer, today

router = Router()
ALL_DONE = "🎉 Ты ответил на все доступные вопросы! Загляни позже — океан полон тайн 🌊"
NO_QUESTIONS = "🌊 Вопросы ещё загружаются — загляни чуть позже!"
log = logging.getLogger(__name__)


async def _empty_reply(session: AsyncSession, done_text: str) -> str:
    """Если вопросов в базе нет совсем — это не «всё пройдено», а ошибка настройки (не запускали seed.py)."""
    total = await session.scalar(select(func.count()).select_from(Question))
    if not total:
        log.warning("Таблица questions пуста — выполните `python seed.py`")
        return NO_QUESTIONS
    return done_text


@router.message(F.text == MENU["quiz"])
@router.message(Command("quiz"))
async def quiz_menu(message: Message):
    await message.answer("🧠 <b>Квиз</b>\n\nВыбери формат:", reply_markup=quiz_menu_kb())


@router.callback_query(QuizCb.filter(F.action == "next"))
async def quiz_next(cb: CallbackQuery, session: AsyncSession, bot: Bot):
    await cb.answer()
    q = await pick_quiz_question(session, cb.from_user.id)
    if q is None:
        await cb.message.answer(await _empty_reply(session, ALL_DONE))
        return
    await send_question(bot, cb.message.chat.id, q, mode="q")


@router.callback_query(QuizCb.filter(F.action == "blitz"))
async def quiz_blitz(cb: CallbackQuery, session: AsyncSession, bot: Bot):
    await cb.answer()
    q = await pick_quiz_question(session, cb.from_user.id, only_text=True)
    if q is None:
        await cb.message.answer(await _empty_reply(
            session, "⚡ Блиц-вопросы закончились. Попробуй обычный квиз 🎯"))
        return
    await send_blitz(bot, cb.message.chat.id, q)


# ── Ответ на inline-вопрос ────────────────────────────────────────────
@router.callback_query(AnswerCb.filter())
async def on_answer(cb: CallbackQuery, callback_data: AnswerCb, session: AsyncSession, bot: Bot):
    user = await get_or_create_user(session, cb.from_user)
    q = await session.get(Question, callback_data.qid)
    if q is None:
        await cb.answer("Вопрос не найден", show_alert=True)
        return
    if callback_data.mode == "d" and user.last_daily_date == today():
        await cb.answer("Сегодняшнее задание уже выполнено ✅", show_alert=True)
        return

    res = await record_answer(session, user, q, callback_data.idx, callback_data.mode)
    await cb.message.edit_reply_markup(reply_markup=None)  # убираем кнопки у вопроса (работает и для медиа)
    await cb.message.answer(result_text(q, res, user),
                            reply_markup=next_kb() if callback_data.mode == "q" else None)
    await cb.answer()
    await notify_referrer(bot, res)


# ── Ответ на блиц-опрос (send_poll) ───────────────────────────────────
@router.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer, session: AsyncSession, bot: Bot):
    qid = POLLS.get(poll_answer.poll_id)
    if qid is None or not poll_answer.option_ids:
        return
    user = await get_or_create_user(session, poll_answer.user)
    q = await session.get(Question, qid)
    res = await record_answer(session, user, q, poll_answer.option_ids[0], mode="q")
    await bot.send_message(user.id, result_text(q, res, user), reply_markup=next_kb())
    await notify_referrer(bot, res)
