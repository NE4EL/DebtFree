"""Связка расчётного модуля с БД и API-схемами."""

from decimal import Decimal

from sqlalchemy.orm import Session

from ..core.calculator import CalculationError, Effect, ExtraPayment, PaymentType, build_schedule
from ..core.simulator import early_payment
from ..core.strategies import STRATEGY_NAMES, DebtInput, PlanExtra, PlanResult, Strategy, compare
from ..models import Debt, User
from ..schemas import (
    CompareOut,
    DebtTrackOut,
    EarlyPaymentIn,
    EarlyPaymentOut,
    ExtraIn,
    PlanIn,
    PlanMonthOut,
    PlanOut,
    ScheduleIn,
    ScheduleOut,
    ScheduleRowOut,
    ScheduleSummary,
)
from . import debt_service


def to_inputs(debts: list[Debt]) -> list[DebtInput]:
    return [DebtInput(d.id, d.name, d.balance, d.annual_rate, d.min_payment) for d in debts]


def to_plan_extras(extras: list[ExtraIn], debts: list[Debt]) -> list[PlanExtra]:
    ids = {d.id for d in debts}
    for e in extras:
        if e.debt_id is not None and e.debt_id not in ids:
            raise CalculationError("Досрочный платёж указан для долга, которого нет в расчёте")
    return [PlanExtra(e.amount, e.month, e.regular, e.debt_id) for e in extras]


def plan_out(result: PlanResult) -> PlanOut:
    return PlanOut(
        strategy=result.strategy.value,
        strategy_name=STRATEGY_NAMES[result.strategy],
        budget=result.budget,
        months=result.months,
        total_paid=result.total_paid,
        total_interest=result.total_interest,
        timeline=[PlanMonthOut(**vars(m)) for m in result.timeline],
        debts=[
            DebtTrackOut(
                debt_id=t.debt.key,
                name=t.debt.name,
                payoff_month=t.payoff_month,
                rows=[PlanMonthOut(**vars(r)) for r in t.rows],
            )
            for t in result.debts
        ],
    )


def schedule(db: Session, user: User, data: ScheduleIn) -> ScheduleOut:
    if data.debt_id is not None:
        debt = debt_service.get_debt(db, user, data.debt_id)
        balance, rate, months, ptype = debt.balance, debt.annual_rate, debt.term_months, debt.payment_type
    else:
        balance, rate, months, ptype = data.balance, data.annual_rate, data.term_months, data.payment_type
    extras = [ExtraPayment(e.amount, e.month, e.regular) for e in data.extra_payments]
    result = build_schedule(balance, rate, months, PaymentType(ptype), extras, Effect(data.effect))

    def summary(r) -> dict:
        return dict(
            months=r.months,
            monthly_payment=r.first_payment,
            total_paid=r.total_paid,
            total_interest=r.total_interest,
        )

    base = None
    if extras:
        base = ScheduleSummary(**summary(build_schedule(balance, rate, months, PaymentType(ptype))))
    return ScheduleOut(**summary(result), rows=[ScheduleRowOut(**vars(r)) for r in result.rows], base=base)


def compare_plans(db: Session, user: User, data: PlanIn) -> CompareOut:
    debts = debt_service.get_debts(db, user, data.debt_ids)
    inputs = to_inputs(debts)
    results = compare(inputs, data.budget, to_plan_extras(data.extra_payments, debts))
    best = min(
        (r for s, r in results.items() if s is not Strategy.MINIMUM),
        key=lambda r: (r.total_interest, r.months),
    )
    return CompareOut(
        budget=data.budget,
        total_balance=sum((d.balance for d in debts), Decimal("0")),
        total_min_payments=sum((d.min_payment for d in debts), Decimal("0")),
        results=[plan_out(r) for r in results.values()],
        recommended=best.strategy.value,
    )


def early(db: Session, user: User, data: EarlyPaymentIn) -> EarlyPaymentOut:
    debts = debt_service.get_debts(db, user, data.debt_ids)
    r = early_payment(
        to_inputs(debts),
        data.budget,
        Strategy(data.strategy),
        to_plan_extras(data.extra_payments, debts),
        Effect(data.effect),
    )
    return EarlyPaymentOut(
        effect=r.effect.value,
        base=plan_out(r.base),
        with_extra=plan_out(r.with_extra),
        months_saved=r.months_saved,
        interest_saved=r.interest_saved,
        budget_reduction=r.budget_reduction,
    )
