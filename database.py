from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from sqlalchemy import Date, Numeric, String, create_engine, extract, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'trades.db'}"


class Base(DeclarativeBase):
    pass


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create database tables when they do not already exist."""
    Base.metadata.create_all(bind=engine)


def add_trade(trade_date: date, amount: Decimal | float | int | str, note: str = "") -> Trade:
    """Persist a trade and return the saved row."""
    init_db()
    with SessionLocal() as session:
        trade = Trade(date=trade_date, amount=Decimal(str(amount)), note=note.strip())
        session.add(trade)
        session.commit()
        session.refresh(trade)
        return trade


def update_trade(
    trade_id: int,
    trade_date: date,
    amount: Decimal | float | int | str,
    note: str = "",
) -> Trade | None:
    """Update an existing trade. Returns None when the row is missing."""
    init_db()
    with SessionLocal() as session:
        trade = session.get(Trade, trade_id)
        if trade is None:
            return None

        trade.date = trade_date
        trade.amount = Decimal(str(amount))
        trade.note = note.strip()
        session.commit()
        session.refresh(trade)
        return trade


def delete_trade(trade_id: int) -> bool:
    """Delete a trade by id. Returns False when the row is missing."""
    init_db()
    with SessionLocal() as session:
        trade = session.get(Trade, trade_id)
        if trade is None:
            return False

        session.delete(trade)
        session.commit()
        return True


def get_monthly_totals(year: int, month: int) -> dict[date, Decimal]:
    """Return summed P&L by day for the selected month."""
    init_db()
    with SessionLocal() as session:
        rows: Iterable[tuple[date, Decimal | None]] = session.execute(
            select(Trade.date, func.coalesce(func.sum(Trade.amount), 0))
            .where(extract("year", Trade.date) == year)
            .where(extract("month", Trade.date) == month)
            .group_by(Trade.date)
            .order_by(Trade.date)
        ).all()
        return {trade_date: Decimal(total or 0) for trade_date, total in rows}


def get_monthly_earnings(year: int, month: int) -> Decimal:
    """Return the total P&L for a month, or zero when no rows exist."""
    init_db()
    with SessionLocal() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(Trade.amount), 0))
            .where(extract("year", Trade.date) == year)
            .where(extract("month", Trade.date) == month)
        )
        return Decimal(total or 0)


def get_total_between(start_date: date, end_date: date) -> Decimal:
    """Return total P&L between two dates, inclusive."""
    init_db()
    with SessionLocal() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(Trade.amount), 0))
            .where(Trade.date >= start_date)
            .where(Trade.date <= end_date)
        )
        return Decimal(total or 0)


def get_trades_for_day(trade_date: date) -> list[Trade]:
    """Return all trades recorded for a single day."""
    init_db()
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(Trade).where(Trade.date == trade_date).order_by(Trade.id.desc())
            ).all()
        )
