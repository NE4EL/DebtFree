import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { SaveScenario } from "../components/forms";
import { ErrorBox, Field, Loading } from "../components/ui";
import { usePlan } from "../context";
import { DEBT_TYPES, fmtMoney, fmtRate, parseAmount } from "../format";

export default function DebtsPage() {
  const navigate = useNavigate();
  const plan = usePlan();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [budgetError, setBudgetError] = useState(null);
  const [saved, setSaved] = useState(null);

  const load = useCallback(() => {
    api.debts().then(setData).catch(setError);
  }, []);
  useEffect(load, [load]);

  const remove = async (debt) => {
    if (!window.confirm(`Удалить долг «${debt.name}»?`)) return;
    try {
      await api.deleteDebt(debt.id);
      setError(null);
      load();
    } catch (err) {
      setError(err);
    }
  };

  // UC-9: бюджет не меньше суммы минимальных платежей
  const checkBudget = () => {
    const budget = Number(parseAmount(plan.budget));
    if (!budget) return "Укажите ежемесячный бюджет";
    if (budget < data.total_min_payments) return "Бюджет не может быть меньше суммы минимальных платежей";
    return null;
  };

  const calculate = (e) => {
    e.preventDefault();
    const err = checkBudget();
    setBudgetError(err);
    if (!err) navigate("/compare");
  };

  if (!data) return error ? <ErrorBox error={error} /> : <Loading />;
  const { debts } = data;

  return (
    <section>
      <div className="page-head">
        <h1>Мои долги</h1>
        <Link className="btn btn-primary" to="/debts/new">
          + Добавить долг
        </Link>
      </div>
      <ErrorBox error={error} />

      {debts.length === 0 ? (
        <div className="panel empty">
          <p>Долгов пока нет. Добавьте кредит, карту или рассрочку, чтобы рассчитать план погашения.</p>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="table debts-table">
              <thead>
                <tr>
                  <th>Название</th>
                  <th className="num">Остаток</th>
                  <th className="num hide-sm">Ставка</th>
                  <th className="num hide-sm">Мин. платёж</th>
                  <th className="num hide-sm">Срок</th>
                  <th aria-label="Действия" />
                </tr>
              </thead>
              <tbody>
                {debts.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <div>{d.name}</div>
                      <div className="muted small">
                        {DEBT_TYPES[d.debt_type]} · {d.payment_type === "annuity" ? "аннуитет" : "дифф."}
                      </div>
                      <div className="muted small show-sm">
                        {fmtRate(d.annual_rate)} · мин. {fmtMoney(d.min_payment)}
                      </div>
                    </td>
                    <td className="num">{fmtMoney(d.balance)}</td>
                    <td className="num hide-sm">{fmtRate(d.annual_rate)}</td>
                    <td className="num hide-sm">{fmtMoney(d.min_payment)}</td>
                    <td className="num hide-sm">{d.term_months} мес.</td>
                    <td className="actions">
                      <Link to={`/debts/${d.id}/schedule`} className="icon-btn" title="График платежей">
                        📈
                      </Link>
                      <Link to={`/debts/${d.id}/edit`} className="icon-btn" title="Изменить">
                        ✎
                      </Link>
                      <button className="icon-btn danger" title="Удалить" onClick={() => remove(d)}>
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="totals">
            <span>
              Итого долг: <b>{fmtMoney(data.total_balance)}</b>
            </span>
            <span>
              Сумма мин. платежей: <b>{fmtMoney(data.total_min_payments)}/мес</b>
            </span>
          </div>

          <form className="budget-row" onSubmit={calculate}>
            <Field label="Ежемесячный бюджет, ₽" error={budgetError}>
              <input
                inputMode="decimal"
                placeholder={String(Math.ceil(data.total_min_payments))}
                value={plan.budget}
                onChange={(e) => {
                  plan.update({ budget: e.target.value });
                  setBudgetError(null);
                }}
              />
            </Field>
            <button className="btn btn-primary">Рассчитать план</button>
            {!checkBudget() && (
              <SaveScenario
                request={() => ({ strategy: plan.strategy, budget: parseAmount(plan.budget) })}
                onSaved={(s) => setSaved(s)}
              />
            )}
          </form>
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
