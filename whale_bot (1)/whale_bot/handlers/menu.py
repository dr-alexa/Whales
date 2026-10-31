from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards import MENU, ShopCb, main_menu, shop_kb, shop_open_kb
from models import Question, User, UserAchievement, UserProgress
from services import (ACHIEVEMENTS, FREEZE_PRICE, MAX_FREEZES, buy_freeze,
                      effective_streak, get_or_create_user, is_plus)

router = Router()

WELCOME = (
    "🌊🐋 <b>Добро пожаловать в КитоКвиз!</b> 🐬🐳\n\n"
    "Здесь мы узнаём всё о китах, дельфинах и морских свиньях: проходим квизы, "
    "копим 🐚, держим 🔥 серию и открываем достижения.\n\n"
    "Начни с «📅 Ежедневное задание» — твои киты уже ждут!"
)
REFERRED = "\n\n🎁 Тебя пригласил друг! Ответь на первый вопрос — и вы оба получите бонус 🐚"


@router.message(CommandStart())
@router.message(Command("menu"))
async def start(message: Message, command: CommandObject, session: AsyncSession):
    tg = message.from_user
    is_new = await session.get(User, tg.id) is None
    user = await get_or_create_user(session, tg)

    # Реферальная ссылка: t.me/<bot>?start=ref_<id>. Работает только для новых пользователей.
    arg, referred = command.args or "", False
    if is_new and arg.startswith("ref_") and arg[4:].isdigit():
        ref_id = int(arg[4:])
        if ref_id != tg.id and await session.get(User, ref_id) is not None:
            user.referrer_id, referred = ref_id, True
    await message.answer(WELCOME + (REFERRED if referred else ""), reply_markup=main_menu())


@router.message(F.text == MENU["progress"])
@router.message(Command("progress"))
async def progress(message: Message, session: AsyncSession):
    user = await get_or_create_user(session, message.from_user)
    uid = user.id
    answered = await session.scalar(select(func.count()).select_from(UserProgress).where(UserProgress.user_id == uid))
    correct = await session.scalar(select(func.count()).select_from(UserProgress)
                                   .where(UserProgress.user_id == uid, UserProgress.is_correct.is_(True)))
    total = await session.scalar(select(func.count()).select_from(Question))
    plus = f"\n⭐ Кит+ до <b>{user.plus_until:%d.%m.%Y}</b>" if is_plus(user) else ""
    await message.answer(
        "📊 <b>Твой прогресс</b>\n\n"
        f"🐚 Очки: <b>{user.points}</b>\n"
        f"🔥 Серия: <b>{effective_streak(user)}</b> дн. (рекорд: {user.longest_streak})\n"
        f"🧊 Айсберги: <b>{user.freezes}</b>\n"
        f"🧠 Отвечено: <b>{answered}</b> из {total}, верно: <b>{correct}</b>\n"
        f"👥 Друзей приглашено: <b>{user.referrals_count}</b>{plus}",
        reply_markup=shop_open_kb())


@router.message(F.text == MENU["ach"])
@router.message(Command("achievements"))
async def achievements(message: Message, session: AsyncSession):
    earned = set(await session.scalars(
        select(UserAchievement.code).where(UserAchievement.user_id == message.from_user.id)))
    lines = ["🏆 <b>Достижения</b>\n"]
    for code, (title, desc) in ACHIEVEMENTS.items():
        lines.append(f"{'✅' if code in earned else '🔒'} <b>{title}</b>\n      <i>{desc}</i>")
    await message.answer("\n".join(lines))


# ── Магазин (🐚 и ⭐ Stars) ────────────────────────────────────────────
def shop_text(user: User) -> str:
    plus = f" · ⭐ Кит+ до {user.plus_until:%d.%m.%Y}" if is_plus(user) else ""
    return ("🛒 <b>Магазин</b>\n\n"
            f"🧊 <b>Айсберг</b> спасает серию, если пропустишь день. За 🐚 — {FREEZE_PRICE} шт., "
            "или купи за Telegram Stars ⭐.\n"
            "⭐ <b>Кит+</b> даёт двойные 🐚 за верные ответы.\n\n"
            f"У тебя: 🐚 {user.points} · 🧊 {user.freezes}/{MAX_FREEZES}{plus}")


@router.message(F.text == MENU["shop"])
@router.message(Command("shop"))
async def shop_cmd(message: Message, session: AsyncSession):
    user = await get_or_create_user(session, message.from_user)
    await message.answer(shop_text(user), reply_markup=shop_kb())


@router.callback_query(ShopCb.filter())
async def shop_cb(cb: CallbackQuery, callback_data: ShopCb, session: AsyncSession):
    user = await get_or_create_user(session, cb.from_user)
    if callback_data.item == "open":
        await cb.message.answer(shop_text(user), reply_markup=shop_kb())
        await cb.answer()
        return
    ok, msg = buy_freeze(user)
    await cb.answer(msg, show_alert=True)
    if ok:
        try:
            await cb.message.edit_text(shop_text(user), reply_markup=shop_kb())
        except TelegramBadRequest:
            pass
