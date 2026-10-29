"""Понятные сообщения об ошибках на русском (FR-9)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..core.calculator import CalculationError
from ..services import ServiceError

FIELD_LABELS = {
    "email": "Email",
    "password": "Пароль",
    "name": "Название",
    "debt_type": "Вид долга",
    "balance": "Остаток",
    "annual_rate": "Ставка",
    "min_payment": "Мин. платёж",
    "term_months": "Срок",
    "start_date": "Дата начала",
    "payment_type": "Тип платежа",
    "budget": "Бюджет",
    "amount": "Сумма досрочного платежа",
    "month": "Месяц досрочного платежа",
    "extra_payments": "Досрочные платежи",
    "debt_ids": "Долги",
    "debt_id": "Долг",
    "strategy": "Стратегия",
    "effect": "Эффект платежа",
}


def _message(err: dict) -> str:
    ctx = err.get("ctx") or {}
    t = err["type"]
    field = str(err["loc"][-1]) if err["loc"] else ""
    if t == "missing":
        return "обязательное поле"
    if t == "greater_than":
        return f"должно быть больше {ctx['gt']}"
    if t == "greater_than_equal":
        return f"должно быть не меньше {ctx['ge']}"
    if t == "less_than":
        return f"должно быть меньше {ctx['lt']}"
    if t == "less_than_equal":
        return f"должно быть не больше {ctx['le']}"
    if t == "decimal_max_places":
        return f"не больше {ctx['decimal_places']} знаков после запятой"
    if t in ("decimal_max_digits", "decimal_whole_digits"):
        return "слишком большое число"
    if t in ("decimal_parsing", "decimal_type", "float_parsing", "float_type", "int_parsing", "int_type", "int_from_float"):
        return "введите число"
    if t == "string_too_short":
        return "заполните поле" if ctx.get("min_length") == 1 else f"не короче {ctx['min_length']} символов"
    if t == "string_too_long":
        return f"не длиннее {ctx['max_length']} символов"
    if t == "too_short":
        return "добавьте хотя бы один элемент"
    if t == "too_long":
        return "слишком много элементов"
    if t == "literal_error":
        return "недопустимое значение"
    if t in ("date_parsing", "date_from_datetime_parsing", "date_type"):
        return "некорректная дата"
    if t == "json_invalid":
        return "некорректный JSON"
    if field == "email" and t == "value_error":
        return "некорректный email"
    if t == "value_error":
        return str(ctx.get("error", err["msg"]))
    return err["msg"]


def _field(loc: tuple) -> str:
    names = [str(p) for p in loc if p not in ("body", "query", "path") and not isinstance(p, int)]
    return names[-1] if names else ""


def install(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            field = _field(err["loc"])
            # собственные сообщения валидаторов уже называют поле
            own_message = err["type"] == "value_error" and field != "email"
            label = None if own_message else FIELD_LABELS.get(field)
            msg = _message(err)
            errors.append({"field": field or None, "message": f"{label}: {msg}" if label else msg[:1].upper() + msg[1:]})
        return JSONResponse(status_code=422, content={"detail": errors[0]["message"], "errors": errors})

    @app.exception_handler(CalculationError)
    async def calculation_error(_: Request, exc: CalculationError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ServiceError)
    async def service_error(_: Request, exc: ServiceError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message}, headers=headers)
