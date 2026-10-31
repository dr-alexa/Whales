from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.types import User as TgUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import Question, User, UserAchievement, UserProgress
from products import Product

POINTS_CORRECT = 10
DAILY_BONUS = 20
FREEZE_PRICE = 50
MAX_FREEZES = 5
REF_BONUS = 50          # пригласившему 🐚
REF_INVITEE_BONUS = 25  # приглашённому 🐚
PLUS_MULTIPLIER = 2     # Кит+: двойные 🐚

ACHIEVEMENTS: dict[str, tuple[str, str]] = {
    "first_step": ("👣 Первый шаг", "Ответь на свой первый вопрос"),
    "dolphin_expert": ("🐬 Знаток дельфинов", "10 правильных ответов в категории «Дельфины»"),
    "week_streak": ("🔥 Неделя с китами", "Серия 7 дней подряд"),
    "whale_patrol": ("🐋 Китовый патруль", "Серия 30 дней подряд"),
    "ambassador": ("🤝 Посол океана", "Пригласи 5 друзей, которые начали играть"),
}


def today() -> date:
    return datetime.now(ZoneInfo(settings.tz)).date()


async def get_or_create_user(session: AsyncSession, tg: TgUser) -> User:
    user = await session.get(User, tg.id)
    if user is None:
        user = User(id=tg.id, username=tg.username, points=0, current_streak=0,
                    longest_streak=0, freezes=0, reminder_time="19:00", reminders_enabled=True,
                    referrals_count=0, referral_rewarded=False)
        session.add(user)
    else:
        user.username = tg.username
    return user


# ── Серии ──────────────────────────────────────────────────────────────
def effective_streak(user: User) -> int:
    """Серия для показа: «сгоревшая» серия отображается как 0, пока пользователь не зайдёт."""
    if not user.last_active_date:
        return 0
    missed = (today() - user.last_active_date).days - 1
    return user.current_streak if missed <= 0 or user.freezes >= missed else 0


def register_activity(user: User) -> int:
    """Обновляет серию при первом ответе за день. Возвращает, сколько 🧊 потрачено."""
    t, last, spent = today(), user.last_active_date, 0
    if last == t:
        return 0
    if last is None:
        user.current_streak = 1
    else:
        missed = (t - last).days - 1
        if missed <= 0:
            user.current_streak += 1
        elif user.freezes >= missed:          # Айсберг спасает серию
            user.freezes -= missed
            spent = missed
            user.current_streak += 1
        else:                                  # серия сгорела
            user.current_streak = 1
    user.longest_streak = max(user.longest_streak, user.current_streak)
    user.last_active_date = t
    return spent


# ── Ответы и награды ──────────────────────────────────────────────────
@dataclass
class AnswerResult:
    is_correct: bool
    repeat: bool = False
    points: int = 0
    freezes_used: int = 0
    achievements: list[str] = field(default_factory=list)
    invitee_bonus: int = 0                       # бонус приглашённому за первый ответ
    referrer_id: int | None = None               # кого нужно уведомить о бонусе
    referrer_points: int = 0
    referrer_achievements: list[str] = field(default_factory=list)


async def record_answer(session: AsyncSession, user: User, q: Question, idx: int, mode: str) -> AnswerResult:
    ok = idx == q.correct_answer
    exists = await session.scalar(
        select(UserProgress.id).where(UserProgress.user_id == user.id, UserProgress.question_id == q.id))
    if exists:
        return AnswerResult(is_correct=ok, repeat=True)

    session.add(UserProgress(user_id=user.id, question_id=q.id, is_correct=ok))
    res = AnswerResult(is_correct=ok)
    res.freezes_used = register_activity(user)
    mult = PLUS_MULTIPLIER if is_plus(user) else 1
    if ok:
        res.points += POINTS_CORRECT * mult
    if mode == "d":                            # ежедневное задание
        user.last_daily_date = today()
        if ok:
            res.points += DAILY_BONUS * mult
    user.points += res.points
    res.achievements = await check_achievements(session, user)
    if "first_step" in res.achievements:       # первый ответ = друг «засчитан»
        await _reward_referral(session, user, res)
    return res


async def _reward_referral(session: AsyncSession, user: User, res: AnswerResult) -> None:
    """Бонус обоим — один раз и только после первого ответа (а не за один /start)."""
    if not user.referrer_id or user.referral_rewarded:
        return
    user.referral_rewarded = True
    referrer = await session.get(User, user.referrer_id)
    if referrer is None:
        return
    user.points += REF_INVITEE_BONUS
    res.invitee_bonus = REF_INVITEE_BONUS
    referrer.points += REF_BONUS
    referrer.referrals_count += 1
    res.referrer_id, res.referrer_points = referrer.id, REF_BONUS
    res.referrer_achievements = await check_achievements(session, referrer)


async def check_achievements(session: AsyncSession, user: User) -> list[str]:
    earned = set(await session.scalars(select(UserAchievement.code).where(UserAchievement.user_id == user.id)))
    answered = await session.scalar(
        select(func.count()).select_from(UserProgress).where(UserProgress.user_id == user.id))
    dolphins = await session.scalar(
        select(func.count()).select_from(UserProgress)
        .join(Question, Question.id == UserProgress.question_id)
        .where(UserProgress.user_id == user.id, UserProgress.is_correct.is_(True),
               Question.category == "dolphins"))
    conditions = {
        "first_step": answered >= 1,
        "dolphin_expert": dolphins >= 10,
        "week_streak": user.longest_streak >= 7,
        "whale_patrol": user.longest_streak >= 30,
        "ambassador": user.referrals_count >= 5,
    }
    new = [code for code, ok in conditions.items() if ok and code not in earned]
    for code in new:
        session.add(UserAchievement(user_id=user.id, code=code))
    return new


# ── Выбор вопросов ────────────────────────────────────────────────────
def _unanswered(user_id: int):
    answered = select(UserProgress.question_id).where(UserProgress.user_id == user_id)
    return select(Question).where(Question.id.not_in(answered))


async def pick_quiz_question(session: AsyncSession, user_id: int, only_text: bool = False) -> Question | None:
    stmt = _unanswered(user_id)
    if only_text:                              # для send_poll медиа не нужно
        stmt = stmt.where(Question.media_type == "none")
    return await session.scalar(stmt.order_by(func.random()).limit(1))


async def pick_daily_question(session: AsyncSession, user_id: int) -> Question | None:
    qs = (await session.scalars(_unanswered(user_id).order_by(Question.id))).all()
    return qs[today().toordinal() % len(qs)] if qs else None


# ── Магазин ───────────────────────────────────────────────────────────
def buy_freeze(user: User) -> tuple[bool, str]:
    if user.freezes >= MAX_FREEZES:
        return False, f"У тебя уже максимум 🧊 ({MAX_FREEZES})."
    if user.points < FREEZE_PRICE:
        return False, f"Не хватает 🐚: нужно {FREEZE_PRICE}, у тебя {user.points}."
    user.points -= FREEZE_PRICE
    user.freezes += 1
    return True, "🧊 Айсберг куплен! Он сам спасёт серию при пропуске."


# ── Кит+ и покупки за Stars ────────────────────────────────────────────
def is_plus(user: User) -> bool:
    return bool(user.plus_until and user.plus_until >= today())


def apply_product(user: User, p: Product) -> str:
    """Выдаёт купленный товар и возвращает текст для пользователя."""
    if p.kind == "coins":
        user.points += p.amount
        return f"✅ Оплачено! +{p.amount} 🐚 (теперь у тебя {user.points})"
    if p.kind == "freeze":
        user.freezes += p.amount
        return f"✅ Оплачено! +{p.amount} 🧊 (теперь у тебя {user.freezes})"
    if p.kind == "plus":                       # повторная покупка продлевает срок
        start = max(user.plus_until or today(), today())
        user.plus_until = start + timedelta(days=p.amount)
        return f"✅ Оплачено! ⭐ Кит+ активен до {user.plus_until:%d.%m.%Y}. Теперь 🐚 за ответы ×{PLUS_MULTIPLIER}!"
    return "✅ Оплачено!"
