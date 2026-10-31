"""Импорт вопросов: python seed.py [data/questions.json | questions.csv]
Повторный запуск обновляет вопросы с тем же text (дубликатов не будет).
CSV-колонки: text,options,correct_answer,category,media_type,media_url,fact_text  (options через « | »)."""
import asyncio
import csv
import json
import sys
from pathlib import Path

from sqlalchemy import select

from database import SessionMaker, init_db
from models import Question
from qnorm import normalize


def load(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            r["options"] = [o.strip() for o in r["options"].split("|")]
            r["correct_answer"] = int(r["correct_answer"])
        return rows
    return json.loads(path.read_text(encoding="utf-8"))   # дальше normalize() приведёт формат к нужному


async def seed(path: Path) -> None:
    items, errors = normalize(load(path))
    if errors:                                   # ничего не пишем в БД, пока файл не исправлен
        print("❌ В файле есть ошибки, импорт отменён:")
        print("\n".join(" • " + e for e in errors))
        raise SystemExit(1)
    await init_db()
    async with SessionMaker() as session:
        for it in items:
            q = await session.scalar(select(Question).where(Question.text == it["text"])) or Question()
            q.text, q.options, q.correct_answer = it["text"], it["options"], it["correct_answer"]
            q.category, q.media_type, q.media_url, q.fact_text = (
                it["category"], it["media_type"], it["media_url"], it["fact_text"])
            session.add(q)
        await session.commit()
    print(f"✅ Импортировано вопросов: {len(items)}")


if __name__ == "__main__":
    asyncio.run(seed(Path(sys.argv[1] if len(sys.argv) > 1 else "data/questions.json")))
