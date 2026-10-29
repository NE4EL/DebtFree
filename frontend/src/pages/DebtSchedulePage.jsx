import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { BalanceChart, COLORS } from "../components/charts";
import { EMPTY_EXTRA, ExtraPaymentForm, extraToApi } from "../components/forms";
import { MonthTable } from "../components/tables";
import { ErrorBox, Loading, Stat } from "../components/ui";
import { fmtMoney, fmtMonths, fmtRate } from "../format";

/** График погашения одного долга по его сроку и типу платежа (FR-3, FR-4, п. 4.5). */
export default function DebtSchedulePage() {
  const { id } = useParams();
  const [debt, setDebt] = useState(null);
  const [base, setBase] = useState(null);
  const [withExtra, setWithExtra] = useState(null);
  const [extra, setExtra] = useState(EMPTY_EXTRA);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api.debt(id), api.schedule({ debt_id: Number(id) })])
      .then(([d, s]) => {
        setDebt(d);
        setBase(s);
      })
      .catch(setError);
  }, [id]);

  const recalc = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const { debt_id: _, ...payment } = extraToApi(extra);
      setWithExtra(await api.schedule({ debt_id: Number(id), extra_payments: [payment], effect: extra.effect }));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }, [extra, id]);

  if (!base) return error ? <ErrorBox error={error} /> : <Loading />;
  const shown = withExtra || base;
  // при «снизить платёж» — плановый платёж в месяце после первого досрочного
  const firstExtra = withExtra ? withExtra.rows.findIndex((r) => r.extra > 0) : -1;
  const newPayment = firstExtra >= 0 ? withExtra.rows[firstExtra + 1]?.payment : undefined;

  return (
    <section>
      <Link to="/debts" className="back">
        ← К списку долгов
      </Link>
      <h1>{debt.name}</h1>
      <p className="muted">
        {fmtMoney(debt.balance)} · {fmtRate(debt.annual_rate)} · {debt.term_months} мес. ·{" "}
        {debt.payment_type === "annuity" ? "аннуитетный платёж" : "дифференцированный платёж"}
      </p>

      <div className="stats">
        <Stat label={debt.payment_type === "annuity" ? "Ежемесячный платёж" : "Первый платёж"} value={fmtMoney(base.monthly_payment)} />
        <Stat label="Срок" value={fmtMonths(base.months)} />
        <Stat label="Всего выплат" value={fmtMoney(base.total_paid)} />
        <Stat label="Переплата" value={fmtMoney(base.total_interest)} />
      </div>

      <div className="chart-with-panel">
        <div className="panel">
          <BalanceChart
            series={[
              { label: "Без досрочных платежей", color: COLORS.base, timeline: base.rows, initial: debt.balance },
              ...(withExtra
                ? [{ label: "С досрочным платежом", color: COLORS.extra, dashed: true, timeline: withExtra.rows, initial: debt.balance }]
                : []),
            ]}
          />
        </div>
        <ExtraPaymentForm value={extra} onChange={setExtra} onSubmit={recalc} busy={busy} />
      </div>
      <ErrorBox error={error} />

      {withExtra && (
        <div className="alert alert-success">
          Экономия: <b>{fmtMoney(base.total_interest - withExtra.total_interest)}</b> переплаты
          {base.months > withExtra.months && <>, срок короче на <b>{base.months - withExtra.months} мес.</b></>}
          {extra.effect === "payment" && newPayment !== undefined && (
            <>; платёж после досрочного погашения — <b>{fmtMoney(newPayment)}</b></>
          )}
        </div>
      )}

      <h2>Помесячный график</h2>
      <MonthTable rows={shown.rows} withExtra={!!withExtra} />
    </section>
  );
}
