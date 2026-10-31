from datetime import date, datetime

from sqlalchemy import (JSON, BigInteger, Boolean, Date, DateTime, ForeignKey,
                        Integer, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)  # Telegram ID
    username: Mapped[str | None] = mapped_column(String(64))
    points: Mapped[int] = mapped_column(Integer, default=0)            # 🐚
    current_streak: Mapped[int] = mapped_column(Integer, default=0)    # 🔥
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    freezes: Mapped[int] = mapped_column(Integer, default=0)           # 🧊 Iceberg
    last_active_date: Mapped[date | None] = mapped_column(Date)
    last_daily_date: Mapped[date | None] = mapped_column(Date)         # когда выполнено ежедневное задание
    reminder_time: Mapped[str | None] = mapped_column(String(5), default="19:00")  # "HH:MM"
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))  # кто пригласил
    referrals_count: Mapped[int] = mapped_column(Integer, default=0)      # сколько друзей «засчитано»
    referral_rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
    plus_until: Mapped[date | None] = mapped_column(Date)                 # Кит+ действует до этой даты
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON)                  # ["вариант 1", "вариант 2", ...]
    correct_answer: Mapped[int] = mapped_column(Integer)         # индекс верного варианта (с 0)
    category: Mapped[str] = mapped_column(String(32), default="general")  # whales | dolphins | porpoises
    media_type: Mapped[str] = mapped_column(String(16), default="none")  # none | photo | photos | audio | voice | document
    media_url: Mapped[str | None] = mapped_column(Text)          # Telegram file_id (или https-ссылка); для photos — несколько id через «|»
    fact_text: Mapped[str | None] = mapped_column(Text)          # «Знаете ли вы?» после ответа


class UserProgress(Base):
    __tablename__ = "user_progress"
    __table_args__ = (UniqueConstraint("user_id", "question_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    is_correct: Mapped[bool] = mapped_column(Boolean)
    answered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    earned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Payment(Base):
    """Журнал платежей Stars: защита от двойного начисления и основа для возвратов."""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    product: Mapped[str] = mapped_column(String(32))
    stars: Mapped[int] = mapped_column(Integer)
    charge_id: Mapped[str] = mapped_column(String(128), unique=True)   # telegram_payment_charge_id
    refunded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
