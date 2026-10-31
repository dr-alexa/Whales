import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from keyboards import BuyCb
from models import Payment
from products import PRODUCTS
from services import MAX_FREEZES, apply_product, get_or_create_user

log = logging.getLogger(__name__)
router = Router()


# 1) Нажали «купить» → отправляем счёт в Stars (currency="XTR", provider_token не нужен).
@router.callback_query(BuyCb.filter())
async def buy(cb: CallbackQuery, callback_data: BuyCb, session: AsyncSession, bot: Bot):
    product = PRODUCTS.get(callback_data.code)
    if product is None:
        await cb.answer("Товар не найден", show_alert=True)
        return
    user = await get_or_create_user(session, cb.from_user)
    if product.kind == "freeze" and user.freezes + product.amount > MAX_FREEZES:
        await cb.answer(f"Максимум 🧊 — {MAX_FREEZES}. Сначала потрать имеющиеся.", show_alert=True)
        return
    await cb.answer()
    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=product.title,
        description=product.description,
        payload=product.code,                       # вернётся в pre_checkout и successful_payment
        currency="XTR",
        prices=[LabeledPrice(label=product.title, amount=product.stars)],
    )


# 2) Telegram спрашивает «можно списывать?» — нужно ответить в течение 10 секунд.
@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    product = PRODUCTS.get(query.invoice_payload)
    ok = product is not None and query.currency == "XTR" and query.total_amount == product.stars
    await query.answer(ok=ok, error_message=None if ok else "Товар недоступен, попробуй ещё раз")


# 3) Деньги списаны → выдаём товар. charge_id уникален: повторное сообщение не начислит дважды.
@router.message(F.successful_payment)
async def paid(message: Message, session: AsyncSession):
    sp = message.successful_payment
    if await session.scalar(select(Payment.id).where(Payment.charge_id == sp.telegram_payment_charge_id)):
        return
    user = await get_or_create_user(session, message.from_user)
    session.add(Payment(user_id=user.id, product=sp.invoice_payload, stars=sp.total_amount,
                        charge_id=sp.telegram_payment_charge_id, refunded=False))
    product = PRODUCTS.get(sp.invoice_payload)
    if product is None:
        log.error("Paid unknown product %s (charge %s)", sp.invoice_payload, sp.telegram_payment_charge_id)
        await message.answer("Платёж получен, но товар не найден 🙈 Напиши в /paysupport")
        return
    await message.answer(apply_product(user, product))


# Telegram требует, чтобы бот с платежами отвечал на /paysupport.
@router.message(Command("paysupport"))
async def paysupport(message: Message):
    await message.answer("💳 Вопросы по оплате: нажми «💬 Обратная связь» (или /feedback) и опиши проблему. "
                         "Если платёж не сработал, приложи скриншот — мы разберёмся и вернём ⭐.")


# Возврат (только админ): /refund <user_id> <charge_id>. charge_id есть в таблице payments.
@router.message(Command("refund"), F.from_user.id == settings.admin_id)
async def refund(message: Message, command: CommandObject, session: AsyncSession, bot: Bot):
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit():
        await message.answer("Формат: <code>/refund user_id charge_id</code>")
        return
    try:
        await bot.refund_star_payment(user_id=int(parts[0]), telegram_payment_charge_id=parts[1])
    except TelegramBadRequest as e:
        await message.answer(f"Ошибка возврата: {e.message}")
        return
    pay = await session.scalar(select(Payment).where(Payment.charge_id == parts[1]))
    if pay:
        pay.refunded = True
    await message.answer("↩️ ⭐ возвращены. Выданный товар автоматически не отзывается.")
