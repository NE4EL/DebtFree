import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { BalanceChart, COLORS, OverpayChart } from "../components/charts";
import { SaveScenario } from "../components/forms";
import { PayoffTable } from "../components/tables";
import { ErrorBox, Field, Loading } from "../components/ui";
import { usePlan } from "../context";
import { fmtMoney, fmtMonths, fmtWhole, parseAmount } from "../format";

/** Экран 3: сравнение стратегий при заданном бюджете (UC-13, FR-5, FR-6). */
export default function ComparePage() {
  const plan = usePlan();
  const navigate = useNavigate();
  const [budgetText, setBudgetText] = useState(plan.budget);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(null);

  const run = useCallback(async (budget) => {
    if (!parseAmount(budget)) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.compare({ budget: parseAmount(budget) }));
    } catch (err) {
      setResult(null);
      setError(err);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    run(plan.budget);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = (e) => {
    e.preventDefault();
    plan.update({ budget: budgetText });
    run(budgetText);
  };

  const selected = result?.results.find((r) => r.strategy === plan.strategy) ?? result?.results[0];

  return (
    <section>
      <h1>Сравнение стратегий</h1>
      <form className="budget-row" onSubmit={submit}>
        <Field label="Ежемесячный бюджет, ₽">
          <input inputMode="decimal" placeholder="20 000" value={budgetText} onChange={(e) => setBudgetText(e.target.value)} required />
        </Field>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Считаю…" : "Рассчитать"}
        </button>
      </form>
      <ErrorBox error={error} />
      {error?.message === "Добавьте хотя бы один долг" && (
        <p>
          <Link to="/debts/new">Добавить долг →</Link>
        </p>
      )}
      {!result && !error && (busy ? <Loading text="Считаю…" /> : <p className="muted">Введите бюджет, чтобы сравнить стратегии.</p>)}

      {result && (
        <>
          <p className="muted">
            Бюджет: <b>{fmtWhole(result.budget)}/мес</b> · долг {fmtMoney(result.total_balance)} · сумма мин. платежей{" "}
            {fmtMoney(result.total_min_payments)}
          </p>
          <div className="cards">
            {result.results.map((r) => {
              const recommended = r.strategy === result.recommended;
              const active = r.strategy === selected.strategy;
              return (
                <button
                  key={r.strategy}
                  className={`card strategy-card${recommended ? " recommended" : ""}${active ? " active" : ""}`}
                  onClick={() => plan.update({ strategy: r.strategy })}
                  aria-pressed={active}
                >
                  <span className="card-title">{r.strategy_name}</span>
                  <span className="kv">
                    <span>Срок:</span>
                    <b>{fmtMonths(r.months)}</b>
                  </span>
                  <span className="kv">
                    <span>Переплата:</span>
                    <b>{fmtWhole(r.total_interest)}</b>
                  </span>
                  <span className="kv">
                    <span>Платёж:</span>
                    <b>{fmtWhole(r.budget)}/мес</b>
                  </span>
                  {recommended && <span className="badge">★ Рекомендуется</span>}
                </button>
              );
            })}
          </div>

          <div className="grid-2 wide-gap">
            <div className="panel">
              <h3>Переплата по стратегиям, ₽</h3>
              <OverpayChart results={result.results} />
            </div>
            <div className="panel">
              <h3>Остаток долга</h3>
              <BalanceChart
                height={240}
                series={result.results.map((r) => ({
                  label: r.strategy_name,
                  color: COLORS[r.strategy],
                  timeline: r.timeline,
                  initial: result.total_balance,
                  dashed: r.strategy === "minimum",
                }))}
              />
            </div>
          </div>

          <h2>Порядок погашения: {selected.strategy_name}</h2>
          <PayoffTable debts={selected.debts} />

          <div className="form-actions">
            <button className="btn btn-primary" onClick={() => navigate("/plan")}>
              Открыть график
            </button>
            <SaveScenario
              request={() => ({ strategy: selected.strategy, budget: parseAmount(plan.budget) })}
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
