"""Приведение вопросов из разных JSON-форматов к формату бота."""

# Тип медиа определяется по началу file_id (так Telegram кодирует тип файла).
PREFIX_TO_TYPE = {"AgAC": "photo", "AwAC": "voice", "CQAC": "audio", "BQAC": "document"}
QTYPE_TO_MEDIA = {"audio": "audio", "visual": "photo", "photo": "photo", "geography": "photo"}


def flatten(raw):
    for x in raw:
        if isinstance(x, list):
            yield from flatten(x)
        else:
            yield x


def _media(it: dict) -> tuple[str, str | None]:
    urls = it.get("media_urls")
    if urls:                                    # несколько картинок в одном вопросе
        return "photos", "|".join(urls)
    url = it.get("media_url")
    if not url or "ВСТАВЬТЕ" in url:
        return "none", None
    by_prefix = PREFIX_TO_TYPE.get(url[:4])
    declared = it.get("media_type") or QTYPE_TO_MEDIA.get(it.get("question_type"), "photo")
    return (by_prefix or declared), url


def normalize_one(it: dict) -> dict:
    text = it.get("text") or it.get("question_text")
    options = it.get("options")
    correct = it.get("correct_answer", it.get("correct_index"))
    if not text or not isinstance(options, list):
        raise ValueError("нет текста вопроса или списка options")
    if correct is None:
        raise ValueError("нет correct_answer / correct_index")
    correct = int(correct)
    if not (2 <= len(options) <= 10 and 0 <= correct < len(options)):
        raise ValueError("число вариантов 2–10, индекс верного ответа должен быть внутри списка")
    media_type, media_url = _media(it)
    return {
        "text": text, "options": options, "correct_answer": correct,
        "category": it.get("category") or "general",
        "media_type": media_type, "media_url": media_url,
        "fact_text": it.get("fact_text") or it.get("explanation"),
    }


def normalize(raw: list) -> tuple[list[dict], list[str]]:
    """Возвращает (готовые вопросы, список ошибок с номерами)."""
    items, errors = [], []
    for n, it in enumerate(flatten(raw), start=1):
        try:
            if not isinstance(it, dict):
                raise ValueError("элемент не является объектом")
            items.append(normalize_one(it))
        except (ValueError, TypeError) as e:
            errors.append(f"вопрос №{n}: {e}")
    return items, errors