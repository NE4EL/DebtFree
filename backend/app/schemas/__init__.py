"""Pydantic-схемы запросов и ответов API."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PlainSerializer,
    ValidationInfo,
    field_validator,
    model_validator,
)

from ..core.calculator import monthly_interest

# Деньги в ответах — числом, чтобы фронтенду не нужно было парсить строки
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
MoneyIn = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
StrategyCode = Literal["avalanche", "snowball", "minimum"]
EffectCode = Literal["term", "payment"]
PaymentTypeCode = Literal["annuity", "diff"]
DebtTypeCode = Literal["credit", "card", "installment", "mortgage", "other"]


# --- Аутентификация ---------------------------------------------------------


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, v: str) -> str:
        # bcrypt учитывает только первые 72 байта (кириллица — 2 байта на символ)
        if len(v.encode()) > 72:
            raise ValueError("Пароль слишком длинный (максимум 72 байта: около 36 русских или 72 латинских символов)")
        return v


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


# --- Долги -----------------------------------------------------------------


class DebtIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    debt_type: DebtTypeCode = "credit"
    balance: MoneyIn
    annual_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    min_payment: MoneyIn
    term_months: int = Field(ge=1, le=600)
    start_date: date | None = None
    payment_type: PaymentTypeCode = "annuity"

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Заполните название")
        return v

    @field_validator("min_payment")
    @classmethod
    def covers_interest(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        balance, rate = info.data.get("balance"), info.data.get("annual_rate")
        if balance is not None and rate is not None:
            interest = monthly_interest(balance, rate)
            if v <= interest:
                raise ValueError(
                    f"Минимальный платёж должен быть больше процентов за месяц ({interest} ₽), иначе долг не погашается"
                )
        return v


class DebtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    debt_type: str
    balance: Money
    annual_rate: Money
    min_payment: Money
    term_months: int
    start_date: date | None
    payment_type: str


class DebtsSummary(BaseModel):
    debts: list[DebtOut]
    total_balance: Money
    total_min_payments: Money


# --- Расчёты ---------------------------------------------------------------


class ExtraIn(BaseModel):
    amount: MoneyIn
    month: int = Field(default=1, ge=1, le=600)
    regular: bool = False
    debt_id: int | None = None


class ScheduleIn(BaseModel):
    """График одного долга: либо `debt_id` сохранённого долга, либо параметры вручную."""

    debt_id: int | None = None
    balance: MoneyIn | None = None
    annual_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    term_months: int | None = Field(default=None, ge=1, le=600)
    payment_type: PaymentTypeCode = "annuity"
    extra_payments: list[ExtraIn] = Field(default_factory=list, max_length=50)
    effect: EffectCode = "term"

    @model_validator(mode="after")
    def debt_or_params(self) -> "ScheduleIn":
        if self.debt_id is None and None in (self.balance, self.annual_rate, self.term_months):
            raise ValueError("Укажите долг или остаток, ставку и срок")
        return self


class ScheduleRowOut(BaseModel):
    month: int
    payment: Money
    interest: Money
    principal: Money
    extra: Money
    balance: Money


class ScheduleSummary(BaseModel):
    months: int
    monthly_payment: Money
    total_paid: Money
    total_interest: Money


class ScheduleOut(ScheduleSummary):
    rows: list[ScheduleRowOut]
    base: ScheduleSummary | None = None  # тот же долг без досрочных платежей


class PlanIn(BaseModel):
    budget: MoneyIn
    debt_ids: list[int] | None = Field(default=None, description="По умолчанию — все долги пользователя")
    extra_payments: list[ExtraIn] = Field(default_factory=list, max_length=50)


class EarlyPaymentIn(PlanIn):
    strategy: StrategyCode = "avalanche"
    extra_payments: list[ExtraIn] = Field(min_length=1, max_length=50)
    effect: EffectCode = "term"


class PlanMonthOut(BaseModel):
    month: int
    payment: Money
    interest: Money
    principal: Money
    balance: Money


class DebtTrackOut(BaseModel):
    debt_id: int
    name: str
    payoff_month: int
    rows: list[PlanMonthOut]


class PlanOut(BaseModel):
    strategy: StrategyCode
    strategy_name: str
    budget: Money
    months: int
    total_paid: Money
    total_interest: Money
    timeline: list[PlanMonthOut]
    debts: list[DebtTrackOut]


class CompareOut(BaseModel):
    budget: Money
    total_balance: Money
    total_min_payments: Money
    results: list[PlanOut]
    recommended: StrategyCode


class EarlyPaymentOut(BaseModel):
    effect: EffectCode
    base: PlanOut
    with_extra: PlanOut
    months_saved: int
    interest_saved: Money
    budget_reduction: Money


# --- Сценарии --------------------------------------------------------------


class ScenarioIn(PlanIn):
    name: str = Field(min_length=1, max_length=100)
    strategy: StrategyCode = "avalanche"
    effect: EffectCode = "term"

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Заполните название")
        return v


class ExtraOut(BaseModel):
    amount: Money
    month: int
    regular: bool
    debt_id: int | None
    effect: EffectCode


class ScenarioOut(BaseModel):
    id: int
    name: str
    strategy: StrategyCode
    strategy_name: str
    monthly_budget: Money
    total_paid: Money
    total_interest: Money
    months_to_payoff: int
    created_at: datetime
    debt_names: list[str]


class ScenarioDetail(ScenarioOut):
    extra_payments: list[ExtraOut]
    plan: PlanOut
