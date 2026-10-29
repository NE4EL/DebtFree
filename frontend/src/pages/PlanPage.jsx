import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { BalanceChart, COLORS } from "../components/charts";
import { EMPTY_EXTRA, ExtraPaymentForm, SaveScenario, extraToApi } from "../components/forms";
import { MonthTable, PayoffTable } from "../components/tables";
import { ErrorBox, Field, Loading, Stat } from "../components/ui";
import { usePlan } from "../context";
import { STRATEGY_LABELS, fmtMoney, fmtMonths, fmtWhole, parseAmount } from "../format";

/** Экран 4: график остатка и досрочное погашение (UC-11, UC-14, UC-15). */
export default function PlanPage() {
  const plan = usePlan();
  const [budgetText, setBudgetText] = useState(plan.budget);
  const [debts, setDebts] = useState([]);
  const [base, setBase] = useState(null);
  const [early, setEarly] = useState(null);
  const [extra, setExtra] = useState(EMPTY_EXTRA);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(null);

  const loadBase = useCallback(async (budget, strategy) => {
    if (!parseAmount(budget)) return;
    setError(null);
    setEarly(null);
    try {
      const res = await api.compare({ budget: parseAmount(budget) });
      setBase({ ...res.results.find((r) => r.strategy === strategy), total_balance: res.total_balance });
    } catch (err) {
      setBase(null);
      setError(err);
    }
  }, []);

  useEffect(() => {
    api.debts().then((d) => setDebts(d.debts)).catch(setError);
  }, []);

  useEffect(() => {
    loadBase(plan.budget, plan.strategy);
  }, [plan.budget, plan.strategy, loadBase]);

  const recalc = async () => {
    setBusy(true);
    setError(null);
    try {
      setEarly(
        await api.earlyPayment({
          budget: parseAmount(plan.budget),
          strategy: plan.strategy,
          extra_payments: [extraToApi(extra)],
          effect: extra.effect,
        }),
      );
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const shown = early?.with_extra ?? base;

  return (
    <section>
      <h1>График остатка и досрочное погашение</h1>
      <form
        className="budget-row"
        onSubmit={(e) => {
          e.preventDefault();
          plan.update({ budget: budgetText });
        }}
      >
        <Field label="Стратегия">
          <select
            value={plan.strategy}
            onChange={(e) => {
              plan.update({ strategy: e.target.value });
              if (e.target.value === "minimum") setExtra((x) => ({ ...x, effect: "term" }));
            }}
          >
            {Object.entries(STRATEGY_LABELS).map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Ежемесячный бюджет, ₽">
          <input inputMode="decimal" placeholder="20 000" value={budgetText} onChange={(e) => setBudgetText(e.target.value)} required />
        </Field>
        <button className="btn btn-outline">Применить</button>
      </form>

      {!base && !error && <Loading text={parseAmount(plan.budget) ? "Считаю…" : "Введите бюджет, чтобы построить график."} />}
      {!base && <ErrorBox error={error} />}

      {base && (
        <>
          <div className="stats">
            <Stat label="Срок" value={fmtMonths(shown.months)} />
            <Stat label="Бюджет (без досрочных)" value={`${fmtWhole(shown.budget)}/мес`} />
            <Stat label="Всего выплат" value={fmtMoney(shown.total_paid)} />
            <Stat label="Переплата" value={fmtMoney(shown.total_interest)} />
          </div>

          <div className="chart-with-panel">
            <div className="panel">
              <BalanceChart
                series={[
                  { label: "Базовый план", color: COLORS.base, timeline: base.timeline, initial: base.total_balance },
                  ...(early
                    ? [{ label: "С досрочным платежом", color: COLORS.extra, dashed: true, timeline: early.with_extra.timeline, initial: base.total_balance }]
                    : []),
                ]}
              />
            </div>
            <ExtraPaymentForm
              value={extra}
              onChange={setExtra}
              onSubmit={recalc}
              debts={debts}
              busy={busy}
              allowPaymentEffect={plan.strategy !== "minimum"}
            />
          </div>
          <ErrorBox error={error} />

          {early && (
            <div className="alert alert-success">
              {early.effect === "payment" && early.budget_reduction > 0 && (
                <>
                  Платёж ниже на <b>{fmtMoney(early.budget_reduction)}/мес</b> ({fmtWhole(early.with_extra.budget)} вместо{" "}
                  {fmtWhole(early.base.budget)}).{" "}
                </>
              )}
              Экономия: <b>{fmtWhole(early.interest_saved)}</b> переплаты
              {early.months_saved > 0 ? (
                <>
                  , срок короче на <b>{early.months_saved} мес.</b>
                </>
              ) : (
                ", срок прежний"
              )}
            </div>
          )}

          <h2>Порядок погашения</h2>
          <PayoffTable debts={shown.debts} />

          <h2>По месяцам (все долги)</h2>
          <MonthTable rows={shown.timeline} />

          <div className="form-actions">
            <SaveScenario
              request={() => ({
                strategy: plan.strategy,
                budget: parseAmount(plan.budget),
                ...(early ? { extra_payments: [extraToApi(extra)], effect: extra.effect } : {}),
              })}
              onSaved={setSaved}
            />
          </div>
          {saved && (
            <div className="alert alert-success">
              Сценарий «{saved.name}» сохранён. <Link to={`/scenarios/${saved.id}`}>Открыть</Link>
            </div>
          )}
        </>
      )}
    </section>
  );
}
