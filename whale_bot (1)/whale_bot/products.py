"""Каталог товаров за Telegram Stars (XTR). Цены — примеры, меняйте под себя.
kind: coins — 🐚, freeze — 🧊, plus — дни подписки «Кит+». amount — количество (🐚 / 🧊 / дней)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    code: str          # попадает в invoice payload и callback_data (без «:»)
    title: str         # до 32 символов
    description: str   # до 255 символов
    stars: int
    kind: str
    amount: int


PRODUCTS: dict[str, Product] = {p.code: p for p in [
    Product("freeze1", "🧊 Айсберг", "Заморозка серии: пропущенный день не сожжёт твою 🔥.", 15, "freeze", 1),
    Product("freeze3", "🧊 3 Айсберга", "Три заморозки серии со скидкой.", 39, "freeze", 3),
    Product("coins200", "🐚 200 ракушек", "Пополни запас ракушек — хватит на 4 Айсберга.", 25, "coins", 200),
    Product("coins600", "🐚 600 ракушек", "Выгодный пак ракушек.", 69, "coins", 600),
    Product("plus30", "⭐ Кит+ на 30 дней", "Двойные 🐚 за верные ответы и ежедневное задание.", 99, "plus", 30),
]}
