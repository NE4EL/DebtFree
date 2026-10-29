"""Платежи по одному долгу: аннуитет, дифференцированный платёж, график (ТЗ 4.1, 4.2, 4.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

CENT = Decimal("0.01")
MAX_MONTHS = 600  # 50 лет (NFR-1)


class CalculationError(ValueError):
    """Ошибка входных данных расчёта; сообщение показывается пользователю."""


class PaymentType(StrEnum):
    ANNUITY = "annuity"
    DIFF = "diff"


class Effect(StrEnum):
    TERM = "term"  # сократить срок
    PAYMENT = "payment"  # снизить платёж


def to_money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_rate(annual_rate: Decimal) -> Decimal:
    """i = r / 12 / 100."""
    return Decimal(annual_rate) / Decimal(1200)


def monthly_interest(balance: Decimal, annual_rate: Decimal) -> Decimal:
    return to_money(Decimal(balance) * monthly_rate(annual_rate))


def annuity_payment(balance: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    """A = S · i / (1 − (1 + i)^(−n)); при i = 0: A = S / n."""
    if months <= 0:
        raise CalculationError("Срок должен быть не меньше 1 месяца")
    balance = Decimal(balance)
    i = monthly_rate(annual_rate)
    if i == 0:
        return to_money(balance / months)
    return to_money(balance * i / (1 - (1 + i) ** -months))


def diff_principal(balance: Decimal, months: int) -> Decimal:
    """D = S / n — постоянная часть основного долга."""
    if months <= 0:
        raise CalculationError("Срок должен быть не меньше 1 месяца")
    return to_money(Decimal(balance) / months)


@dataclass(frozen=True)
class ExtraPayment:
    """Досрочный платёж: разовый в месяце `month` или регулярный начиная с него."""

    amount: Decimal
    month: int = 1
    regular: bool = False

    def applies_to(self, month: int) -> bool:
        return month >= self.month if self.regular else month == self.month


@dataclass(frozen=True)
class ScheduleRow:
    month: int
    payment: Decimal  # плановый платёж (проценты + основной долг)
    interest: Decimal
    principal: Decimal
    extra: Decimal  # досрочный платёж сверх графика
    balance: Decimal  # остаток после платежа


@dataclass
class ScheduleResult:
    rows: list[ScheduleRow] = field(default_factory=list)

    @property
    def months(self) -> int:
        return len(self.rows)

    @property
    def total_paid(self) -> Decimal:
        return sum((r.payment + r.extra for r in self.rows), Decimal("0.00"))

    @property
    def total_interest(self) -> Decimal:
        return sum((r.interest for r in self.rows), Decimal("0.00"))

    @property
    def first_payment(self) -> Decimal:
        return self.rows[0].payment if self.rows else Decimal("0.00")


def build_schedule(
    balance: Decimal,
    annual_rate: Decimal,
    months: int,
    payment_type: PaymentType = PaymentType.ANNUITY,
    extra_payments: list[ExtraPayment] | tuple[ExtraPayment, ...] = (),
    effect: Effect = Effect.TERM,
) -> ScheduleResult:
    """Помесячный график погашения одного долга.

    Проценты и платежи округляются до копеек каждый месяц, последний платёж
    закрывает остаток полностью — сумма основного долга по графику равна
    исходному остатку (T3), остаток в последнем месяце равен 0 (T4).
    """
    balance = to_money(balance)
    if balance <= 0:
        raise CalculationError("Остаток долга должен быть больше 0")
    if not 0 <= Decimal(annual_rate) <= 100:
        raise CalculationError("Ставка должна быть от 0 до 100 %")
    if not 1 <= months <= MAX_MONTHS:
        raise CalculationError(f"Срок должен быть от 1 до {MAX_MONTHS} месяцев")

    payment_type = PaymentType(payment_type)
    effect = Effect(effect)
    annuity = annuity_payment(balance, annual_rate, months)
    principal_part = diff_principal(balance, months)

    result = ScheduleResult()
    month = 0
    while balance > 0:
        month += 1
        interest = monthly_interest(balance, annual_rate)
        if payment_type is PaymentType.ANNUITY:
            principal = annuity - interest
        else:
            principal = principal_part
        if month >= months or principal >= balance:
            principal = balance
        payment = principal + interest
        balance -= principal

        extra = Decimal("0.00")
        for ep in extra_payments:
            if not ep.applies_to(month) or balance == 0:
                continue
            amount = to_money(ep.amount)
            if amount > balance:
                if not ep.regular:
                    raise CalculationError(
                        f"Досрочный платёж в месяце {month} ({amount} ₽) больше остатка долга ({balance} ₽)"
                    )
                amount = balance  # регулярный платёж в последнем месяце закрывает остаток
            balance -= amount
            extra += amount

        if extra > 0 and balance > 0 and effect is Effect.PAYMENT:
            remaining = months - month
            annuity = annuity_payment(balance, annual_rate, remaining)
            principal_part = diff_principal(balance, remaining)

        result.rows.append(ScheduleRow(month, payment, interest, principal, extra, balance))
    return result
