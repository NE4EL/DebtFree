"""Моделирование стратегий погашения нескольких долгов (ТЗ 4.4).

Проценты начисляются без промежуточного округления; до копеек округляются
строки графика и итоговые суммы (NFR-2). Именно так получаются значения
контрольного примера 4.7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from .calculator import MAX_MONTHS, CalculationError, monthly_rate, to_money


class Strategy(StrEnum):
    AVALANCHE = "avalanche"
    SNOWBALL = "snowball"
    MINIMUM = "minimum"


STRATEGY_NAMES = {
    Strategy.AVALANCHE: "Лавина",
    Strategy.SNOWBALL: "Снежный ком",
    Strategy.MINIMUM: "Только минимальные платежи",
}


@dataclass(frozen=True)
class DebtInput:
    key: int | str
    name: str
    balance: Decimal
    annual_rate: Decimal
    min_payment: Decimal


@dataclass(frozen=True)
class PlanExtra:
    """Досрочный платёж в плане.

    С `debt_key` идёт на указанный долг, без него добавляется к свободной сумме
    и распределяется по правилу стратегии.
    """

    amount: Decimal
    month: int = 1
    regular: bool = False
    debt_key: int | str | None = None

    def applies_to(self, month: int) -> bool:
        return month >= self.month if self.regular else month == self.month


@dataclass(frozen=True)
class DebtMonth:
    month: int
    payment: Decimal
    interest: Decimal
    principal: Decimal
    balance: Decimal


@dataclass(frozen=True)
class PlanMonth:
    month: int
    payment: Decimal
    interest: Decimal
    principal: Decimal
    balance: Decimal


@dataclass
class DebtTrack:
    debt: DebtInput
    rows: list[DebtMonth] = field(default_factory=list)

    @property
    def payoff_month(self) -> int:
        return self.rows[-1].month if self.rows else 0


@dataclass
class PlanResult:
    strategy: Strategy
    budget: Decimal
    months: int
    total_paid: Decimal
    total_interest: Decimal
    timeline: list[PlanMonth]
    debts: list[DebtTrack]

    @property
    def payoff_order(self) -> list[int | str]:
        return [t.debt.key for t in sorted(self.debts, key=lambda t: t.payoff_month)]


def min_payments_total(debts: list[DebtInput]) -> Decimal:
    return sum((Decimal(d.min_payment) for d in debts), Decimal("0"))


def validate_debts(debts: list[DebtInput]) -> None:
    if not debts:
        raise CalculationError("Добавьте хотя бы один долг")
    for d in debts:
        if d.balance <= 0:
            raise CalculationError(f"«{d.name}»: остаток должен быть больше 0")
        if not 0 <= d.annual_rate <= 100:
            raise CalculationError(f"«{d.name}»: ставка должна быть от 0 до 100 %")
        if d.min_payment <= 0:
            raise CalculationError(f"«{d.name}»: минимальный платёж должен быть больше 0")
        if d.min_payment <= d.balance * monthly_rate(d.annual_rate):
            raise CalculationError(
                f"«{d.name}»: минимальный платёж не покрывает начисленные за месяц проценты — долг не погашается"
            )


def _priority(strategy: Strategy, debt: DebtInput, balance: Decimal) -> tuple:
    if strategy is Strategy.SNOWBALL:
        return (balance, -debt.annual_rate)
    # Лавина; для базовой стратегии так же распределяются только досрочные платежи
    return (-debt.annual_rate, balance)


def simulate(
    debts: list[DebtInput],
    budget: Decimal | None,
    strategy: Strategy,
    extras: list[PlanExtra] | tuple[PlanExtra, ...] = (),
) -> PlanResult:
    """Алгоритм 4.4. Для базовой стратегии бюджет не используется:
    освободившиеся платежи не перераспределяются."""
    strategy = Strategy(strategy)
    validate_debts(debts)
    mins = min_payments_total(debts)
    if strategy is Strategy.MINIMUM:
        budget = mins
    elif budget is None or Decimal(budget) < mins:
        raise CalculationError(
            f"Бюджет не может быть меньше суммы минимальных платежей ({to_money(mins)} ₽)"
        )
    budget = Decimal(budget)
    keys = {d.key for d in debts}
    for e in extras:
        if e.amount <= 0:
            raise CalculationError("Сумма досрочного платежа должна быть больше 0")
        if e.month < 1:
            raise CalculationError("Месяц досрочного платежа должен быть не меньше 1")
        if e.debt_key is not None and e.debt_key not in keys:
            raise CalculationError("Досрочный платёж указан для долга, которого нет в расчёте")

    balances = [Decimal(d.balance) for d in debts]
    rates = [monthly_rate(d.annual_rate) for d in debts]
    tracks = [DebtTrack(d) for d in debts]
    timeline: list[PlanMonth] = []
    total_paid = Decimal("0")
    month = 0

    while any(b > 0 for b in balances):
        if month >= MAX_MONTHS:
            raise CalculationError(f"Долги не погашаются за {MAX_MONTHS // 12} лет — увеличьте бюджет")
        month += 1
        active = [k for k, b in enumerate(balances) if b > 0]
        interest = {k: balances[k] * rates[k] for k in active}
        paid = {k: Decimal("0") for k in active}

        # 2.1 начислить проценты
        for k in active:
            balances[k] += interest[k]

        # 2.2–2.3 минимальные платежи
        free = budget
        for k in active:
            p = min(Decimal(debts[k].min_payment), balances[k])
            balances[k] -= p
            paid[k] += p
            free -= p
        if strategy is Strategy.MINIMUM:
            free = Decimal("0")

        # 2.4 досрочные платежи этого месяца
        for e in extras:
            if not e.applies_to(month):
                continue
            if e.debt_key is None:
                free += Decimal(e.amount)
                continue
            k = next(k for k, d in enumerate(debts) if d.key == e.debt_key)
            p = min(Decimal(e.amount), balances[k])
            if p < Decimal(e.amount) and not e.regular:
                raise CalculationError(
                    f"Досрочный платёж в месяце {month} больше остатка долга «{debts[k].name}»"
                )
            balances[k] -= p
            paid[k] = paid.get(k, Decimal("0")) + p

        # 2.5–2.6 свободная сумма — по порядку стратегии
        order = sorted(
            (k for k in active if balances[k] > 0),
            key=lambda k: _priority(strategy, debts[k], balances[k]),
        )
        for k in order:
            if free <= 0:
                break
            p = min(free, balances[k])
            balances[k] -= p
            paid[k] += p
            free -= p

        # 2.7 строка графика
        month_paid = Decimal("0")
        month_interest = Decimal("0")
        for k in active:
            tracks[k].rows.append(
                DebtMonth(
                    month=month,
                    payment=to_money(paid[k]),
                    interest=to_money(interest[k]),
                    principal=to_money(paid[k] - interest[k]),
                    balance=to_money(balances[k]),
                )
            )
            month_paid += paid[k]
            month_interest += interest[k]
        total_paid += month_paid
        timeline.append(
            PlanMonth(
                month=month,
                payment=to_money(month_paid),
                interest=to_money(month_interest),
                principal=to_money(month_paid - month_interest),
                balance=to_money(sum(balances, Decimal("0"))),
            )
        )

    initial = sum((Decimal(d.balance) for d in debts), Decimal("0"))
    return PlanResult(
        strategy=strategy,
        budget=to_money(budget),
        months=month,
        total_paid=to_money(total_paid),
        total_interest=to_money(total_paid - initial),
        timeline=timeline,
        debts=tracks,
    )


def compare(
    debts: list[DebtInput],
    budget: Decimal,
    extras: list[PlanExtra] | tuple[PlanExtra, ...] = (),
) -> dict[Strategy, PlanResult]:
    """Сравнение «Лавины», «Снежного кома» и базового варианта (FR-5, FR-6)."""
    return {s: simulate(debts, budget, s, extras) for s in Strategy}
