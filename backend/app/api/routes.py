from decimal import Decimal

from fastapi import APIRouter, status

from ..schemas import (
    CompareOut,
    Credentials,
    DebtIn,
    DebtOut,
    DebtsSummary,
    EarlyPaymentIn,
    EarlyPaymentOut,
    PlanIn,
    ScenarioDetail,
    ScenarioIn,
    ScenarioOut,
    ScheduleIn,
    ScheduleOut,
    TokenOut,
    UserOut,
)
from ..services import auth_service, debt_service, plan_service, scenario_service
from .deps import DB, CurrentUser

router = APIRouter(prefix="/api")


# --- Аккаунт (UC-1, UC-2) --------------------------------------------------


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(data: Credentials, db: DB):
    return auth_service.register(db, data.email, data.password)


@router.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(data: Credentials, db: DB):
    user = auth_service.authenticate(db, data.email, data.password)
    return TokenOut(access_token=auth_service.create_token(user))


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: CurrentUser):
    return user


# --- Долги (UC-4 … UC-8) ---------------------------------------------------


@router.get("/debts", response_model=DebtsSummary, tags=["debts"])
def list_debts(db: DB, user: CurrentUser):
    debts = debt_service.list_debts(db, user)
    return DebtsSummary(
        debts=debts,
        total_balance=sum((d.balance for d in debts), Decimal("0")),
        total_min_payments=sum((d.min_payment for d in debts), Decimal("0")),
    )


@router.post("/debts", response_model=DebtOut, status_code=status.HTTP_201_CREATED, tags=["debts"])
def create_debt(data: DebtIn, db: DB, user: CurrentUser):
    return debt_service.create_debt(db, user, data)


@router.get("/debts/{debt_id}", response_model=DebtOut, tags=["debts"])
def get_debt(debt_id: int, db: DB, user: CurrentUser):
    return debt_service.get_debt(db, user, debt_id)


@router.put("/debts/{debt_id}", response_model=DebtOut, tags=["debts"])
def update_debt(debt_id: int, data: DebtIn, db: DB, user: CurrentUser):
    return debt_service.update_debt(db, user, debt_id, data)


@router.delete("/debts/{debt_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["debts"])
def delete_debt(debt_id: int, db: DB, user: CurrentUser):
    debt_service.delete_debt(db, user, debt_id)


# --- Расчёты (UC-9 … UC-15) ------------------------------------------------


@router.post("/schedule", response_model=ScheduleOut, tags=["calculations"])
def schedule(data: ScheduleIn, db: DB, user: CurrentUser):
    return plan_service.schedule(db, user, data)


@router.post("/compare", response_model=CompareOut, tags=["calculations"])
def compare(data: PlanIn, db: DB, user: CurrentUser):
    return plan_service.compare_plans(db, user, data)


@router.post("/early-payment", response_model=EarlyPaymentOut, tags=["calculations"])
def early_payment(data: EarlyPaymentIn, db: DB, user: CurrentUser):
    return plan_service.early(db, user, data)


# --- Сценарии (UC-16 … UC-18) ----------------------------------------------


@router.get("/scenarios", response_model=list[ScenarioOut], tags=["scenarios"])
def list_scenarios(db: DB, user: CurrentUser):
    return scenario_service.list_scenarios(db, user)


@router.post("/scenarios", response_model=ScenarioDetail, status_code=status.HTTP_201_CREATED, tags=["scenarios"])
def create_scenario(data: ScenarioIn, db: DB, user: CurrentUser):
    return scenario_service.create_scenario(db, user, data)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetail, tags=["scenarios"])
def get_scenario(scenario_id: int, db: DB, user: CurrentUser):
    return scenario_service.get_scenario(db, user, scenario_id)


@router.delete("/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["scenarios"])
def delete_scenario(scenario_id: int, db: DB, user: CurrentUser):
    scenario_service.delete_scenario(db, user, scenario_id)
