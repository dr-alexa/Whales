import html

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InputMediaPhoto

from keyboards import question_kb
from models import Question, User
from services import ACHIEVEMENTS, AnswerResult

# poll_id -> question_id. В памяти — для старта; в проде храните в БД/Redis.
POLLS: dict[str, int] = {}


def esc(s: str | None) -> str:
    return html.escape(s or "")


def _cut(s: str | None, n: int) -> str | None:
    """Лимит пояснения в Telegram-квизе — 200 символов; обрезаем аккуратно, с многоточием."""
    s = (s or "").strip()
    if not s:
        return None
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


async def send_question(bot: Bot, chat_id: int, q: Question, mode: str = "q") -> None:
    """Текст вопроса уходит в caption медиа — картинка и вопрос единое сообщение.
    Типы media_type: none | photo | photos (несколько id через «|») | audio | voice | document."""
    prefix = "📅 <b>Ежедневное задание</b>\n\n" if mode == "d" else ""
    caption = f"{prefix}❓ <b>{esc(q.text)}</b>"
    kb = question_kb(q, mode)
    mt, url = q.media_type, q.media_url
    try:
        if mt == "photos" and url:
            ids = [i for i in url.split("|") if i][:10]
            if len(ids) > 1:                    # у альбома не бывает кнопок — вопрос идёт следом отдельным сообщением
                await bot.send_media_group(chat_id, [InputMediaPhoto(media=i) for i in ids])
                await bot.send_message(chat_id, caption, reply_markup=kb)
            else:
                await bot.send_photo(chat_id, ids[0], caption=caption, reply_markup=kb)
        elif mt == "photo" and url:
            await bot.send_photo(chat_id, url, caption=caption, reply_markup=kb)
        elif mt == "audio" and url:
            await bot.send_audio(chat_id, url, caption=caption, reply_markup=kb, title="🐋 Голос океана")
        elif mt == "voice" and url:             # file_id голосовых сообщений нужно слать через send_voice
            await bot.send_voice(chat_id, url, caption=caption, reply_markup=kb)
        elif mt == "document" and url:
            await bot.send_document(chat_id, url, caption=caption, reply_markup=kb)
        else:
            await bot.send_message(chat_id, caption, reply_markup=kb)
    except TelegramBadRequest:  # битый file_id и т.п. — не роняем квиз
        await bot.send_message(chat_id, caption + "\n\n⚠️ <i>Медиа временно недоступно</i>", reply_markup=kb)


async def send_blitz(bot: Bot, chat_id: int, q: Question) -> None:
    """Блиц: нативный Telegram-квиз с таймером. is_anonymous=False нужен, чтобы приходил poll_answer."""
    msg = await bot.send_poll(
        chat_id,
        question=q.text[:300],
        options=[o[:100] for o in q.options],
        type="quiz",
        correct_option_id=q.correct_answer,
        is_anonymous=False,
        explanation=_cut(q.fact_text, 200),
        open_period=30,
    )
    POLLS[msg.poll.id] = q.id


def result_text(q: Question, res: AnswerResult, user: User) -> str:
    if res.repeat:
        head = "ℹ️ Ты уже отвечал на этот вопрос — очки не начисляются."
    elif res.is_correct:
        head = f"✅ <b>Верно!</b> +{res.points} 🐚"
    else:
        head = f"🌊 <b>Почти!</b> Правильный ответ: <b>{esc(q.options[q.correct_answer])}</b>"
    parts = [head]
    if q.fact_text:
        parts.append(f"\n💡 <i>{esc(q.fact_text)}</i>")
    if res.freezes_used:
        parts.append("\n🧊 Айсберг спас твою серию!")
    if res.invitee_bonus:
        parts.append(f"\n🎁 Бонус за приглашение: +{res.invitee_bonus} 🐚")
    for code in res.achievements:
        parts.append(f"\n🎉 Новое достижение: <b>{ACHIEVEMENTS[code][0]}</b>")
    parts.append(f"\n🔥 Серия: {user.current_streak} · 🐚 {user.points}")
    return "\n".join(parts)


async def notify_referrer(bot: Bot, res: AnswerResult) -> None:
    """Сообщает пригласившему, что друг начал играть, и о его бонусе."""
    if not res.referrer_id:
        return
    text = f"🎁 Твой друг начал играть в КитоКвиз! +{res.referrer_points} 🐚"
    for code in res.referrer_achievements:
        text += f"\n🎉 Новое достижение: <b>{ACHIEVEMENTS[code][0]}</b>"
    try:
        await bot.send_message(res.referrer_id, text)
    except TelegramAPIError:
        pass
