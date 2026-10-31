from aiogram.filters.callback_data import CallbackData
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import Question
from products import PRODUCTS
from services import FREEZE_PRICE

MENU = {
    "daily": "📅 Ежедневное задание",
    "quiz": "🧠 Квиз",
    "progress": "📊 Мой прогресс",
    "ach": "🏆 Достижения",
    "settings": "⚙️ Настройки",
    "invite": "👥 Пригласить друзей",
    "shop": "🛒 Магазин",
    "feedback": "💬 Обратная связь",
}


class AnswerCb(CallbackData, prefix="ans"):
    qid: int
    idx: int
    mode: str          # q — квиз, d — ежедневное


class QuizCb(CallbackData, prefix="quiz"):
    action: str        # next | blitz


class ShopCb(CallbackData, prefix="shop"):
    item: str          # open | freeze


class BuyCb(CallbackData, prefix="buy"):
    code: str          # код товара из products.py (покупка за Stars)


class RemindCb(CallbackData, prefix="rem"):
    value: str         # "0900" или "off" (двоеточие нельзя: оно разделитель CallbackData)


def main_menu() -> ReplyKeyboardMarkup:
    m = MENU
    rows = [[m["daily"], m["quiz"]], [m["progress"], m["ach"]], [m["invite"], m["shop"]],
            [m["settings"], m["feedback"]]]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows],
        resize_keyboard=True, input_field_placeholder="🌊 Выбери действие")


def question_kb(q: Question, mode: str):
    b = InlineKeyboardBuilder()
    for i, opt in enumerate(q.options):
        b.button(text=opt, callback_data=AnswerCb(qid=q.id, idx=i, mode=mode))
    b.adjust(1)
    return b.as_markup()


def quiz_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🎯 Вопрос", callback_data=QuizCb(action="next"))
    b.button(text="⚡ Блиц-опрос", callback_data=QuizCb(action="blitz"))
    b.adjust(2)
    return b.as_markup()


def next_kb():
    b = InlineKeyboardBuilder()
    b.button(text="➡️ Следующий вопрос", callback_data=QuizCb(action="next"))
    return b.as_markup()


def shop_open_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🛒 Магазин", callback_data=ShopCb(item="open"))
    return b.as_markup()


def shop_kb():
    b = InlineKeyboardBuilder()
    b.button(text=f"🧊 Айсберг за {FREEZE_PRICE} 🐚", callback_data=ShopCb(item="freeze"))
    for p in PRODUCTS.values():                # платные товары за Telegram Stars
        b.button(text=f"{p.title} — {p.stars} ⭐", callback_data=BuyCb(code=p.code))
    b.adjust(1)
    return b.as_markup()


def reminder_kb():
    b = InlineKeyboardBuilder()
    for t in ("0900", "1200", "1800", "2100"):
        b.button(text=f"🕒 {t[:2]}:{t[2:]}", callback_data=RemindCb(value=t))
    b.button(text="🔕 Выключить", callback_data=RemindCb(value="off"))
    b.adjust(4, 1)
    return b.as_markup()
