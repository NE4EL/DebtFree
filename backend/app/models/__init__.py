"""SQLAlchemy-модели по словарю данных (отчёт, п. 5.1)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

scenario_debts = Table(
    "scenario_debts",
    Base.metadata,
    Column("scenario_id", ForeignKey("scenarios.id", ondelete="CASCADE"), primary_key=True),
    Column("debt_id", ForeignKey("debts.id", ondelete="RESTRICT"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Debt(Base):
    __tablename__ = "debts"
    __table_args__ = (
        CheckConstraint("balance > 0", name="ck_debts_balance"),
        CheckConstraint("annual_rate BETWEEN 0 AND 100", name="ck_debts_rate"),
        CheckConstraint("min_payment > 0", name="ck_debts_min_payment"),
        CheckConstraint("term_months BETWEEN 1 AND 600", name="ck_debts_term"),
        CheckConstraint("payment_type IN ('annuity', 'diff')", name="ck_debts_payment_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    debt_type: Mapped[str] = mapped_column(String(20), default="credit")
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    min_payment: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    term_months: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    payment_type: Mapped[str] = mapped_column(String(10), default="annuity")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id"))
    name: Mapped[str] = mapped_column(String(100))
    monthly_budget: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_interest: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    months_to_payoff: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    strategy: Mapped[Strategy] = relationship(lazy="joined")
    debts: Mapped[list[Debt]] = relationship(secondary=scenario_debts, order_by=Debt.id)
    schedule: Mapped[list["PaymentSchedule"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="(PaymentSchedule.month_no, PaymentSchedule.debt_id)"
    )
    extra_payments: Mapped[list["ExtraPaymentRow"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="ExtraPaymentRow.id"
    )


class PaymentSchedule(Base):
    __tablename__ = "payment_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    debt_id: Mapped[int] = mapped_column(ForeignKey("debts.id", ondelete="RESTRICT"))
    month_no: Mapped[int] = mapped_column(Integer)
    payment: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    principal_part: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    interest_part: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class ExtraPaymentRow(Base):
    __tablename__ = "extra_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    debt_id: Mapped[int | None] = mapped_column(ForeignKey("debts.id", ondelete="RESTRICT"))
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    pay_month: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    effect: Mapped[str] = mapped_column(String(10), default="term")
    # не было в словаре данных: регулярный платёж повторяется каждый месяц начиная с pay_month
    is_regular: Mapped[bool] = mapped_column(Boolean, default=False)
