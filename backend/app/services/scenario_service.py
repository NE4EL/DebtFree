from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..core.calculator import Effect
from ..core.simulator import early_payment
from ..core.strategies import STRATEGY_NAMES, Strategy, simulate
from ..models import ExtraPaymentRow, PaymentSchedule, Scenario, User
from ..models import Strategy as StrategyRow
from ..schemas import DebtTrackOut, ExtraOut, PlanMonthOut, PlanOut, ScenarioDetail, ScenarioIn, ScenarioOut
from . import NotFound, debt_service
from .plan_service import to_inputs, to_plan_extras


def create_scenario(db: Session, user: User, data: ScenarioIn) -> ScenarioDetail:
    debts = debt_service.get_debts(db, user, data.debt_ids)
    inputs = to_inputs(debts)
    extras = to_plan_extras(data.extra_payments, debts)
    strategy = Strategy(data.strategy)
    if extras:
        result = early_payment(inputs, data.budget, strategy, extras, Effect(data.effect)).with_extra
    else:
        result = simulate(inputs, data.budget, strategy)

    strategy_row = db.scalar(select(StrategyRow).where(StrategyRow.code == strategy.value))
    scenario = Scenario(
        user_id=user.id,
        strategy=strategy_row,
        name=data.name,
        monthly_budget=result.budget,
        total_paid=result.total_paid,
        total_interest=result.total_interest,
        months_to_payoff=result.months,
        debts=debts,
        schedule=[
            PaymentSchedule(
                debt_id=track.debt.key,
                month_no=row.month,
                payment=row.payment,
                principal_part=row.principal,
                interest_part=row.interest,
                balance_after=row.balance,
            )
            for track in result.debts
            for row in track.rows
        ],
        extra_payments=[
            ExtraPaymentRow(
                debt_id=e.debt_id, pay_month=e.month, amount=e.amount, effect=data.effect, is_regular=e.regular
            )
            for e in data.extra_payments
        ],
    )
    db.add(scenario)
    db.commit()
    return get_scenario(db, user, scenario.id)


def _summary(s: Scenario) -> dict:
    return dict(
        id=s.id,
        name=s.name,
        strategy=s.strategy.code,
        strategy_name=s.strategy.name,
        monthly_budget=s.monthly_budget,
        total_paid=s.total_paid,
        total_interest=s.total_interest,
        months_to_payoff=s.months_to_payoff,
        created_at=s.created_at,
        debt_names=[d.name for d in s.debts],
    )


def list_scenarios(db: Session, user: User) -> list[ScenarioOut]:
    rows = db.scalars(
        select(Scenario)
        .where(Scenario.user_id == user.id)
        .options(selectinload(Scenario.debts))
        .order_by(Scenario.created_at.desc(), Scenario.id.desc())
    )
    return [ScenarioOut(**_summary(s)) for s in rows]


def _get(db: Session, user: User, scenario_id: int) -> Scenario:
    scenario = db.get(Scenario, scenario_id)
    if scenario is None or scenario.user_id != user.id:
        raise NotFound("Сценарий не найден")
    return scenario


def get_scenario(db: Session, user: User, scenario_id: int) -> ScenarioDetail:
    s = _get(db, user, scenario_id)
    names = {d.id: d.name for d in s.debts}
    per_debt: dict[int, list[PlanMonthOut]] = defaultdict(list)
    months: dict[int, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for row in s.schedule:
        per_debt[row.debt_id].append(
            PlanMonthOut(
                month=row.month_no,
                payment=row.payment,
                interest=row.interest_part,
                principal=row.principal_part,
                balance=row.balance_after,
            )
        )
        m = months[row.month_no]
        m["payment"] += row.payment
        m["interest"] += row.interest_part
        m["principal"] += row.principal_part
        m["balance"] += row.balance_after
    plan = PlanOut(
        strategy=s.strategy.code,
        strategy_name=STRATEGY_NAMES[Strategy(s.strategy.code)],
        budget=s.monthly_budget,
        months=s.months_to_payoff,
        total_paid=s.total_paid,
        total_interest=s.total_interest,
        timeline=[PlanMonthOut(month=k, **v) for k, v in sorted(months.items())],
        debts=[
            DebtTrackOut(debt_id=d_id, name=names[d_id], payoff_month=rows[-1].month, rows=rows)
            for d_id, rows in per_debt.items()
        ],
    )
    extras = [
        ExtraOut(amount=e.amount, month=e.pay_month, regular=e.is_regular, debt_id=e.debt_id, effect=e.effect)
        for e in s.extra_payments
    ]
    return ScenarioDetail(**_summary(s), extra_payments=extras, plan=plan)


def delete_scenario(db: Session, user: User, scenario_id: int) -> None:
    db.delete(_get(db, user, scenario_id))
    db.commit()
