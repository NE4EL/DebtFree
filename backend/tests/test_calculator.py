from decimal import Decimal as D

import pytest

from app.core.calculator import (
    CalculationError,
    Effect,
    ExtraPayment,
    PaymentType,
    annuity_payment,
    build_schedule,
    diff_principal,
    to_money,
)


def test_t1_annuity_reference_value():
    assert annuity_payment(D(200_000), D(15), 36) == D("6933.07")


def test_t2_zero_rate_is_balance_over_months():
    assert annuity_payment(D(30_000), D(0), 10) == D("3000.00")
    assert annuity_payment(D(100), D(0), 3) == D("33.33")


@pytest.mark.parametrize("payment_type", list(PaymentType))
def test_t3_t4_principal_sums_to_balance_and_ends_at_zero(payment_type):
    s = build_schedule(D(200_000), D(15), 36, payment_type)
    assert s.months == 36
    assert sum(r.principal for r in s.rows) == D("200000.00")
    assert s.rows[-1].balance == D("0.00")
    assert s.total_paid == D("200000.00") + s.total_interest


def test_annuity_schedule_rows_are_consistent():
    s = build_schedule(D(200_000), D(15), 36)
    first = s.rows[0]
    assert first.interest == D("2500.00")
    assert first.payment == D("6933.07")
    assert first.principal == D("4433.07")
    for r in s.rows:
        assert r.payment == r.interest + r.principal


def test_diff_schedule_decreasing_payments():
    s = build_schedule(D(120_000), D(12), 12, PaymentType.DIFF)
    assert diff_principal(D(120_000), 12) == D("10000.00")
    assert s.rows[0].payment == D("11200.00")
    assert s.rows[-1].payment == D("10100.00")
    payments = [r.payment for r in s.rows]
    assert payments == sorted(payments, reverse=True)
    assert s.total_interest == D("7800.00")


def test_zero_rate_schedule_has_no_interest():
    s = build_schedule(D(30_000), D(0), 10)
    assert s.total_interest == D("0.00")
    assert s.total_paid == D("30000.00")


def test_one_time_extra_shortens_term():
    base = build_schedule(D(200_000), D(15), 36)
    s = build_schedule(D(200_000), D(15), 36, extra_payments=[ExtraPayment(D(50_000), month=6)])
    assert s.months < base.months
    assert s.total_interest < base.total_interest
    assert s.rows[0].payment == base.rows[0].payment  # платёж не меняется
    assert sum(r.principal + r.extra for r in s.rows) == D("200000.00")


def test_extra_with_reduce_payment_keeps_term():
    base = build_schedule(D(200_000), D(15), 36)
    s = build_schedule(
        D(200_000), D(15), 36, extra_payments=[ExtraPayment(D(50_000), month=6)], effect=Effect.PAYMENT
    )
    assert s.months == 36
    assert s.rows[6].payment < base.rows[6].payment
    assert s.total_interest < base.total_interest
    assert s.rows[-1].balance == 0


def test_regular_extra_reduce_payment_for_diff():
    s = build_schedule(
        D(120_000),
        D(12),
        12,
        PaymentType.DIFF,
        extra_payments=[ExtraPayment(D(1_000), month=1, regular=True)],
        effect=Effect.PAYMENT,
    )
    assert s.months == 12
    assert sum(r.principal + r.extra for r in s.rows) == D("120000.00")


def test_regular_extra_is_capped_by_balance():
    s = build_schedule(D(10_000), D(10), 12, extra_payments=[ExtraPayment(D(5_000), 1, regular=True)])
    assert s.rows[-1].balance == 0
    assert sum(r.principal + r.extra for r in s.rows) == D("10000.00")


def test_one_time_extra_above_balance_is_rejected():
    with pytest.raises(CalculationError, match="больше остатка"):
        build_schedule(D(10_000), D(10), 12, extra_payments=[ExtraPayment(D(20_000), month=2)])


@pytest.mark.parametrize(
    "balance, rate, months",
    [(D(0), D(10), 12), (D(100), D(-1), 12), (D(100), D(101), 12), (D(100), D(10), 0), (D(100), D(10), 601)],
)
def test_invalid_inputs(balance, rate, months):
    with pytest.raises(CalculationError):
        build_schedule(balance, rate, months)


def test_annuity_requires_positive_term():
    with pytest.raises(CalculationError):
        annuity_payment(D(100), D(10), 0)
    with pytest.raises(CalculationError):
        diff_principal(D(100), 0)


def test_to_money_rounds_half_up():
    assert to_money(D("1.005")) == D("1.01")
    assert to_money(D("1.004")) == D("1.00")
