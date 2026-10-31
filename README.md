# 🐋 Whales
Project "Whales" in Telegram is about quiz bot for learning smth new about our ocean creatures.

## Запуск
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env .env        # впишите BOT_TOKEN и ADMIN_ID
python seed.py              # импорт data/questions.json
python main.py
```

## Как хранить медиа без сторонних серверов (file_id)
Telegram хранит загруженные файлы у себя и выдаёт каждому уникальный `file_id`.
1. Запустите бота, откройте чат с ним под аккаунтом из `ADMIN_ID`.
2. Отправьте боту картинку (как фото) или аудио — бот ответит `file_id` (хендлер `handlers/admin.py`).
3. Вставьте его в `media_url` вопроса, `media_type` — `photo` или `audio`, затем `python seed.py`.

Важно: `file_id` привязан к токену бота — при смене бота файлы нужно загрузить заново.
Для `send_photo`/`send_audio` в `media_url` можно передать и обычную https-ссылку.

## Структура
`models.py` · `database.py` · `services.py` (серии, очки, достижения, магазин) · `senders.py` (вопросы с медиа и send_poll) ·
`handlers/` (menu, daily, quiz, prefs, feedback, admin) · `scheduler.py` · `seed.py`

## Рефералы и Stars
- Реферальная ссылка: `https://t.me/<бот>?start=ref_<user_id>` (команда `/invite`). Бонус обоим (+50 / +25 🐚) выдаётся
  один раз, после первого ответа нового пользователя. Самоприглашение и повторная привязка заблокированы.
- Магазин (`/shop`) продаёт за Telegram Stars (валюта `XTR`): 🧊, 🐚 и «Кит+» на 30 дней (×2 🐚). Каталог и цены — в `products.py`.
- `/paysupport` обязателен для ботов с платежами; `/refund user_id charge_id` — возврат (только админ).
- Схема БД изменилась: при первом запуске удалите старый `whale_bot.db` (или добавьте колонки миграцией).
