import time
from decimal import Decimal as D

import pytest

from app.core.calculator import CalculationError, Effect
from app.core.simulator import early_payment
from app.core.strategies import DebtInput, PlanExtra, Strategy, compare, simulate

# Контрольный пример из п. 4.7 отчёта
DEBTS = [
    DebtInput("card", "Кредитная карта", D(60_000), D("29.9"), D(3_000)),
    DebtInput("loan", "Потребительский кредит", D(200_000), D(15), D(7_000)),
    DebtInput("phone", "Рассрочка на телефон", D(30_000), D(0), D(3_000)),
]


@pytest.mark.parametrize(
    "strategy, budget, extras, months, total_paid, overpay",
    [
        (Strategy.MINIMUM, D(13_000), [], 36, "363066.92", "73066.92"),
        (Strategy.SNOWBALL, D(20_000), [], 17, "325953.80", "35953.80"),
        (Strategy.AVALANCHE, D(20_000), [], 17, "323002.56", "33002.56"),
        (Strategy.AVALANCHE, D(20_000), [PlanExtra(D(5_000), 1, regular=True)], 13, "315287.07", "25287.07"),
        (Strategy.AVALANCHE, D(25_000), [], 13, "315287.07", "25287.07"),
    ],
)
def test_t5_control_example(strategy, budget, extras, months, total_paid, overpay):
    r = simulate(DEBTS, budget, strategy, extras)
    assert r.months == months
    assert r.total_paid == D(total_paid)
    assert r.total_interest == D(overpay)


def test_t5_conclusions():
    res = compare(DEBTS, D(20_000))
    av, sb, mn = res[Strategy.AVALANCHE], res[Strategy.SNOWBALL], res[Strategy.MINIMUM]
    assert sb.total_interest - av.total_interest == D("2951.24")
    assert mn.total_interest - av.total_interest == D("40064.36")


def test_t6_avalanche_not_worse_than_snowball():
    for budget in (D(13_000), D(15_000), D(20_000), D(40_000)):
        res = compare(DEBTS, budget)
        assert res[Strategy.AVALANCHE].total_interest <= res[Strategy.SNOWBALL].total_interest


def test_t7_budget_below_minimums_rejected():
    with pytest.raises(CalculationError, match="Бюджет не может быть меньше"):
        simulate(DEBTS, D(12_999), Strategy.AVALANCHE)


def test_t8_extra_payment_never_increases_term_or_overpay():
    for effect in Effect:
        r = early_payment(DEBTS, D(20_000), Strategy.AVALANCHE, [PlanExtra(D(5_000), 1, True)], effect)
        assert r.with_extra.months <= r.base.months
        assert r.with_extra.total_interest <= r.base.total_interest


def test_early_payment_term_matches_mockup():
    r = early_payment(DEBTS, D(20_000), Strategy.AVALANCHE, [PlanExtra(D(5_000), 1, True)], Effect.TERM)
    assert r.months_saved == 4
    assert r.interest_saved == D("7715.49")


def test_early_payment_reduce_payment_keeps_term_and_lowers_budget():
    r = early_payment(DEBTS, D(20_000), Strategy.AVALANCHE, [PlanExtra(D(30_000), 1)], Effect.PAYMENT)
    assert r.with_extra.months <= r.base.months
    assert r.budget_reduction > 0
    assert r.with_extra.total_interest <= r.base.total_interest
    # на копейку меньше — план уже дольше или дороже базового
    cheaper = simulate(DEBTS, r.with_extra.budget - D("0.01"), Strategy.AVALANCHE, [PlanExtra(D(30_000), 1)])
    assert cheaper.months > r.base.months or cheaper.total_interest > r.base.total_interest


def test_early_payment_reduce_payment_down_to_minimums():
    r = early_payment(DEBTS, D(13_500), Strategy.SNOWBALL, [PlanExtra(D(250_000), 1)], Effect.PAYMENT)
    assert r.with_extra.budget == D("13000.00")


def test_early_payment_validation():
    with pytest.raises(CalculationError):
        early_payment(DEBTS, D(20_000), Strategy.AVALANCHE, [])
    with pytest.raises(CalculationError, match="базовой стратегии"):
        early_payment(DEBTS, D(20_000), Strategy.MINIMUM, [PlanExtra(D(1_000))], Effect.PAYMENT)


def test_t9_min_payment_below_interest_is_reported():
    bad = [DebtInput(1, "Карта", D(100_000), D(36), D(3_000))]  # проценты 3000 ₽/мес
    with pytest.raises(CalculationError, match="не покрывает"):
        simulate(bad, D(10_000), Strategy.AVALANCHE)


def test_targeted_extra_goes_to_its_debt():
    r = simulate(DEBTS, D(13_000), Strategy.MINIMUM, [PlanExtra(D(27_000), 1, debt_key="phone")])
    phone = next(t for t in r.debts if t.debt.key == "phone")
    assert phone.payoff_month == 1


def test_targeted_extra_above_balance_rejected():
    with pytest.raises(CalculationError, match="больше остатка"):
        simulate(DEBTS, D(13_000), Strategy.MINIMUM, [PlanExtra(D(40_000), 1, debt_key="phone")])


def test_extra_for_unknown_debt_rejected():
    with pytest.raises(CalculationError, match="которого нет"):
        simulate(DEBTS, D(13_000), Strategy.MINIMUM, [PlanExtra(D(1_000), 1, debt_key="nope")])


@pytest.mark.parametrize("extra", [PlanExtra(D(0)), PlanExtra(D(100), month=0)])
def test_invalid_extra_rejected(extra):
    with pytest.raises(CalculationError):
        simulate(DEBTS, D(20_000), Strategy.AVALANCHE, [extra])


def test_snowball_closes_smallest_first_avalanche_highest_rate_first():
    sb = simulate(DEBTS, D(20_000), Strategy.SNOWBALL)
    av = simulate(DEBTS, D(20_000), Strategy.AVALANCHE)
    assert sb.payoff_order[0] == "phone"
    av_card = next(t for t in av.debts if t.debt.key == "card").payoff_month
    sb_card = next(t for t in sb.debts if t.debt.key == "card").payoff_month
    assert av_card < sb_card


def test_timeline_balances_end_at_zero_and_sum_up():
    r = simulate(DEBTS, D(20_000), Strategy.AVALANCHE)
    assert r.timeline[-1].balance == 0
    assert len(r.timeline) == r.months
    for m in r.timeline:
        assert m.payment <= D(20_000)


def test_not_paid_off_in_50_years():
    debts = [DebtInput(1, "Ипотека", D(5_000_000), D(10), D("41667"))]  # проценты ≈ 41 666,67
    with pytest.raises(CalculationError, match="не погашаются"):
        simulate(debts, D("41667"), Strategy.AVALANCHE)


@pytest.mark.parametrize(
    "debt",
    [
        DebtInput(1, "x", D(0), D(1), D(1)),
        DebtInput(1, "x", D(1), D(101), D(1)),
        DebtInput(1, "x", D(1), D(1), D(0)),
    ],
)
def test_invalid_debts(debt):
    with pytest.raises(CalculationError):
        simulate([debt], D(100), Strategy.AVALANCHE)


def test_empty_debts():
    with pytest.raises(CalculationError, match="хотя бы один"):
        simulate([], D(100), Strategy.AVALANCHE)


def test_nfr1_twenty_debts_fifty_years_under_two_seconds():
    debts = [DebtInput(k, f"Долг {k}", D(1_000_000), D(10) + k, D(1_000_000) * (D(10) + k) / 1200 + 500) for k in range(20)]
    start = time.perf_counter()
    res = compare(debts, sum(d.min_payment for d in debts) + 1)
    assert time.perf_counter() - start < 2
    assert res[Strategy.MINIMUM].months <= 600
