import pytest

CONTROL_DEBTS = [
    {"name": "Кредитная карта", "debt_type": "card", "balance": 60000, "annual_rate": 29.9, "min_payment": 3000, "term_months": 24},
    {"name": "Потребительский кредит", "balance": 200000, "annual_rate": 15, "min_payment": 7000, "term_months": 36},
    {"name": "Рассрочка на телефон", "debt_type": "installment", "balance": 30000, "annual_rate": 0, "min_payment": 3000, "term_months": 10},
]


@pytest.fixture
def user_with_debts(client, auth):
    headers = auth()
    ids = [client.post("/api/debts", json=d, headers=headers).json()["id"] for d in CONTROL_DEBTS]
    return headers, ids


# --- auth ---


def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"email": "A@Example.com", "password": "secret123"})
    assert r.status_code == 201
    assert r.json()["email"] == "a@example.com"
    assert "password" not in r.text

    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "secret123"})
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "a@example.com"


def test_password_is_stored_hashed(client, auth):
    from sqlalchemy import text

    from app.db import engine

    auth()
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT password_hash FROM users")).scalar_one()
    assert stored != "secret123" and stored.startswith("$2")


def test_duplicate_email_rejected(client):
    body = {"email": "a@example.com", "password": "secret123"}
    client.post("/api/auth/register", json=body)
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 409
    assert "уже зарегистрирован" in r.json()["detail"]


def test_wrong_password(client, auth):
    auth()
    r = client.post("/api/auth/login", json={"email": "user@example.com", "password": "wrongpass"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Неверный email или пароль"


@pytest.mark.parametrize(
    "body, message",
    [
        ({"email": "bad", "password": "secret123"}, "Email: некорректный email"),
        ({"email": "a@example.com", "password": "short"}, "Пароль: не короче 8 символов"),
    ],
)
def test_register_validation(client, body, message):
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 422
    assert r.json()["detail"] == message


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer garbage"}])
def test_protected_routes_require_token(client, headers):
    assert client.get("/api/debts", headers=headers).status_code == 401


# --- debts ---


def test_debt_crud_and_totals(client, user_with_debts):
    headers, ids = user_with_debts
    r = client.get("/api/debts", headers=headers).json()
    assert [d["name"] for d in r["debts"]] == [d["name"] for d in CONTROL_DEBTS]
    assert r["total_balance"] == 290000
    assert r["total_min_payments"] == 13000

    upd = dict(CONTROL_DEBTS[0], balance=55000.5)
    r = client.put(f"/api/debts/{ids[0]}", json=upd, headers=headers)
    assert r.status_code == 200 and r.json()["balance"] == 55000.5

    assert client.delete(f"/api/debts/{ids[2]}", headers=headers).status_code == 204
    assert len(client.get("/api/debts", headers=headers).json()["debts"]) == 2


def test_debts_are_private(client, auth, user_with_debts):
    _, ids = user_with_debts
    other = auth("other@example.com")
    assert client.get("/api/debts", headers=other).json()["debts"] == []
    assert client.get(f"/api/debts/{ids[0]}", headers=other).status_code == 404
    assert client.delete(f"/api/debts/{ids[0]}", headers=other).status_code == 404


@pytest.mark.parametrize(
    "patch, message",
    [
        ({"balance": 0}, "Остаток: должно быть больше 0"),
        ({"annual_rate": 120}, "Ставка: должно быть не больше 100"),
        ({"min_payment": -5}, "Мин. платёж: должно быть больше 0"),
        ({"min_payment": 1000}, "Минимальный платёж должен быть больше процентов за месяц (1495.00 ₽)"),
        ({"name": "   "}, "Заполните название"),
        ({"balance": "abc"}, "Остаток: введите число"),
        ({"balance": 10.555}, "Остаток: не больше 2 знаков после запятой"),
        ({"payment_type": "x"}, "Тип платежа: недопустимое значение"),
    ],
)
def test_t9_debt_validation_messages(client, auth, patch, message):
    r = client.post("/api/debts", json=dict(CONTROL_DEBTS[0], **patch), headers=auth())
    assert r.status_code == 422
    assert r.json()["detail"].startswith(message)


# --- calculations ---


def test_schedule_by_debt_id_and_params(client, user_with_debts):
    headers, ids = user_with_debts
    r = client.post("/api/schedule", json={"debt_id": ids[1]}, headers=headers).json()
    assert r["monthly_payment"] == 6933.07
    assert r["months"] == 36
    assert r["rows"][-1]["balance"] == 0
    assert r["base"] is None

    r = client.post(
        "/api/schedule",
        json={"balance": 120000, "annual_rate": 12, "term_months": 12, "payment_type": "diff"},
        headers=headers,
    ).json()
    assert r["monthly_payment"] == 11200
    assert r["total_interest"] == 7800


def test_schedule_with_extra_returns_base(client, user_with_debts):
    headers, ids = user_with_debts
    r = client.post(
        "/api/schedule",
        json={"debt_id": ids[1], "extra_payments": [{"amount": 50000, "month": 6}], "effect": "payment"},
        headers=headers,
    ).json()
    assert r["months"] == 36
    assert r["total_interest"] < r["base"]["total_interest"]


def test_schedule_requires_debt_or_params(client, auth):
    r = client.post("/api/schedule", json={"balance": 1000}, headers=auth())
    assert r.status_code == 422
    assert r.json()["detail"] == "Укажите долг или остаток, ставку и срок"


def test_t5_compare_control_example(client, user_with_debts):
    headers, _ = user_with_debts
    r = client.post("/api/compare", json={"budget": 20000}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    res = {p["strategy"]: p for p in body["results"]}
    assert (res["avalanche"]["months"], res["avalanche"]["total_interest"]) == (17, 33002.56)
    assert (res["snowball"]["months"], res["snowball"]["total_interest"]) == (17, 35953.80)
    assert (res["minimum"]["months"], res["minimum"]["total_interest"]) == (36, 73066.92)
    assert body["recommended"] == "avalanche"
    assert body["total_min_payments"] == 13000
    assert res["avalanche"]["timeline"][0]["balance"] > res["avalanche"]["timeline"][1]["balance"]
    assert {d["name"] for d in res["avalanche"]["debts"]} == {d["name"] for d in CONTROL_DEBTS}


def test_t7_compare_budget_below_minimums(client, user_with_debts):
    headers, _ = user_with_debts
    r = client.post("/api/compare", json={"budget": 12000}, headers=headers)
    assert r.status_code == 422
    assert r.json()["detail"] == "Бюджет не может быть меньше суммы минимальных платежей (13000.00 ₽)"


def test_compare_selected_debts(client, user_with_debts):
    headers, ids = user_with_debts
    r = client.post("/api/compare", json={"budget": 10000, "debt_ids": [ids[1]]}, headers=headers).json()
    assert r["total_balance"] == 200000


def test_compare_without_debts(client, auth):
    r = client.post("/api/compare", json={"budget": 10000}, headers=auth())
    assert r.status_code == 422
    assert r.json()["detail"] == "Добавьте хотя бы один долг"


def test_early_payment_matches_mockup(client, user_with_debts):
    headers, _ = user_with_debts
    r = client.post(
        "/api/early-payment",
        json={"budget": 20000, "strategy": "avalanche", "extra_payments": [{"amount": 5000, "regular": True}]},
        headers=headers,
    ).json()
    assert r["months_saved"] == 4
    assert r["interest_saved"] == 7715.49
    assert r["with_extra"]["total_paid"] == 315287.07


def test_early_payment_reduce_payment(client, user_with_debts):
    headers, _ = user_with_debts
    r = client.post(
        "/api/early-payment",
        json={"budget": 20000, "extra_payments": [{"amount": 30000, "month": 1}], "effect": "payment"},
        headers=headers,
    ).json()
    assert r["budget_reduction"] > 0
    assert r["with_extra"]["months"] <= r["base"]["months"]


def test_early_payment_extra_for_foreign_debt(client, auth, user_with_debts):
    headers, _ = user_with_debts
    other = auth("other@example.com")
    foreign = client.post("/api/debts", json=CONTROL_DEBTS[0], headers=other).json()["id"]
    r = client.post(
        "/api/early-payment",
        json={"budget": 20000, "extra_payments": [{"amount": 5000, "debt_id": foreign}]},
        headers=headers,
    )
    assert r.status_code == 422


# --- scenarios ---


def test_scenario_lifecycle(client, user_with_debts):
    headers, ids = user_with_debts
    r = client.post(
        "/api/scenarios",
        json={
            "name": "Лавина +5000",
            "strategy": "avalanche",
            "budget": 20000,
            "extra_payments": [{"amount": 5000, "regular": True}],
        },
        headers=headers,
    )
    assert r.status_code == 201
    created = r.json()
    assert created["months_to_payoff"] == 13
    assert created["total_interest"] == 25287.07
    assert created["strategy_name"] == "Лавина"
    assert created["extra_payments"] == [{"amount": 5000, "month": 1, "regular": True, "debt_id": None, "effect": "term"}]
    assert len(created["plan"]["timeline"]) == 13
    assert created["plan"]["timeline"][-1]["balance"] == 0

    listed = client.get("/api/scenarios", headers=headers).json()
    assert [s["name"] for s in listed] == ["Лавина +5000"]
    assert len(listed[0]["debt_names"]) == 3

    detail = client.get(f"/api/scenarios/{created['id']}", headers=headers).json()
    assert detail["plan"] == created["plan"]

    # долг из сценария удалить нельзя, пока сценарий существует
    r = client.delete(f"/api/debts/{ids[0]}", headers=headers)
    assert r.status_code == 409
    assert "«Лавина +5000»" in r.json()["detail"]

    assert client.delete(f"/api/scenarios/{created['id']}", headers=headers).status_code == 204
    assert client.get("/api/scenarios", headers=headers).json() == []
    assert client.delete(f"/api/debts/{ids[0]}", headers=headers).status_code == 204


def test_scenario_minimum_strategy_uses_min_payments(client, user_with_debts):
    headers, _ = user_with_debts
    r = client.post(
        "/api/scenarios", json={"name": "База", "strategy": "minimum", "budget": 20000}, headers=headers
    ).json()
    assert r["monthly_budget"] == 13000
    assert r["months_to_payoff"] == 36


def test_scenario_is_private(client, auth, user_with_debts):
    headers, _ = user_with_debts
    sid = client.post("/api/scenarios", json={"name": "S", "budget": 20000}, headers=headers).json()["id"]
    other = auth("other@example.com")
    assert client.get(f"/api/scenarios/{sid}", headers=other).status_code == 404
    assert client.delete(f"/api/scenarios/{sid}", headers=other).status_code == 404


def test_health(client):
    assert client.get("/api/health").status_code == 200
