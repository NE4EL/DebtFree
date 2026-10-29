from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Debt, Scenario, User, scenario_debts
from ..schemas import DebtIn
from . import Conflict, NotFound


def list_debts(db: Session, user: User) -> list[Debt]:
    return list(db.scalars(select(Debt).where(Debt.user_id == user.id).order_by(Debt.id)))


def get_debt(db: Session, user: User, debt_id: int) -> Debt:
    debt = db.get(Debt, debt_id)
    if debt is None or debt.user_id != user.id:
        raise NotFound("Долг не найден")
    return debt


def get_debts(db: Session, user: User, debt_ids: list[int] | None) -> list[Debt]:
    """Долги пользователя для расчёта: все или выбранные."""
    if debt_ids is None:
        return list_debts(db, user)
    unique = list(dict.fromkeys(debt_ids))
    return [get_debt(db, user, i) for i in unique]


def create_debt(db: Session, user: User, data: DebtIn) -> Debt:
    debt = Debt(user_id=user.id, **data.model_dump())
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt


def update_debt(db: Session, user: User, debt_id: int, data: DebtIn) -> Debt:
    debt = get_debt(db, user, debt_id)
    for key, value in data.model_dump().items():
        setattr(debt, key, value)
    db.commit()
    db.refresh(debt)
    return debt


def delete_debt(db: Session, user: User, debt_id: int) -> None:
    debt = get_debt(db, user, debt_id)
    used_in = list(
        db.scalars(
            select(Scenario.name)
            .join(scenario_debts, scenario_debts.c.scenario_id == Scenario.id)
            .where(scenario_debts.c.debt_id == debt.id)
            .order_by(Scenario.id)
        )
    )
    if used_in:
        names = ", ".join(f"«{n}»" for n in used_in)
        raise Conflict(f"Долг используется в сохранённых сценариях: {names}. Сначала удалите их.")
    db.delete(debt)
    db.commit()
