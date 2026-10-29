"""Досрочное погашение для плана из нескольких долгов (ТЗ 4.5, FR-7)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .calculator import CENT, CalculationError, Effect
from .strategies import DebtInput, PlanExtra, PlanResult, Strategy, min_payments_total, simulate


@dataclass
class EarlyPaymentResult:
    effect: Effect
    base: PlanResult
    with_extra: PlanResult

    @property
    def months_saved(self) -> int:
        return self.base.months - self.with_extra.months

    @property
    def interest_saved(self) -> Decimal:
        return self.base.total_interest - self.with_extra.total_interest

    @property
    def budget_reduction(self) -> Decimal:
        return self.base.budget - self.with_extra.budget


def _lowest_budget_not_worse(
    debts: list[DebtInput],
    strategy: Strategy,
    extras: list[PlanExtra],
    base: PlanResult,
) -> PlanResult:
    """Минимальный ежемесячный бюджет (с точностью до копейки), при котором
    план с досрочными платежами не дольше и не дороже базового (критерий приёмки 4)."""

    def fits(plan: PlanResult) -> bool:
        return plan.months <= base.months and plan.total_interest <= base.total_interest

    lo = int(min_payments_total(debts) / CENT)
    lo_plan = simulate(debts, lo * CENT, strategy, extras)
    if fits(lo_plan):
        return lo_plan
    hi = int(base.budget / CENT)
    best = simulate(debts, base.budget, strategy, extras)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        plan = simulate(debts, mid * CENT, strategy, extras)
        if fits(plan):
            hi, best = mid, plan
        else:
            lo = mid
    return best


def early_payment(
    debts: list[DebtInput],
    budget: Decimal,
    strategy: Strategy,
    extras: list[PlanExtra],
    effect: Effect = Effect.TERM,
) -> EarlyPaymentResult:
    """Сравнить план без досрочных платежей с планом, где они есть.

    «Сократить срок» — бюджет прежний, лишние деньги ускоряют погашение.
    «Снизить платёж» — подбирается наименьший ежемесячный бюджет, при котором
    срок и переплата не больше, чем без досрочного платежа.
    """
    effect = Effect(effect)
    strategy = Strategy(strategy)
    if not extras:
        raise CalculationError("Укажите досрочный платёж")
    base = simulate(debts, budget, strategy)
    if effect is Effect.TERM:
        return EarlyPaymentResult(effect, base, simulate(debts, budget, strategy, extras))
    if strategy is Strategy.MINIMUM:
        raise CalculationError(
            "Для базовой стратегии ежемесячный платёж фиксирован — выберите «Сократить срок»"
        )
    return EarlyPaymentResult(effect, base, _lowest_budget_not_worse(debts, strategy, extras, base))
