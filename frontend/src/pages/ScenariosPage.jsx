import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { BalanceChart, COLORS } from "../components/charts";
import { MonthTable, PayoffTable } from "../components/tables";
import { ErrorBox, Loading, Stat } from "../components/ui";
import { fmtDate, fmtMoney, fmtMonths, fmtWhole } from "../format";

/** UC-17, UC-18: список сохранённых сценариев. */
export function ScenariosPage() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api.scenarios().then(setItems).catch(setError);
  }, []);
  useEffect(load, [load]);

  const remove = async (s) => {
    if (!window.confirm(`Удалить сценарий «${s.name}»?`)) return;
    try {
      await api.deleteScenario(s.id);
      load();
    } catch (err) {
      setError(err);
    }
  };

  if (!items) return error ? <ErrorBox error={error} /> : <Loading />;

  return (
    <section>
      <h1>Сохранённые сценарии</h1>
      <ErrorBox error={error} />
      {items.length === 0 ? (
        <div className="panel empty">
          <p>
            Сценариев пока нет. Рассчитайте план на экране <Link to="/compare">«Сравнение»</Link> или{" "}
            <Link to="/plan">«График»</Link> и нажмите «Сохранить сценарий».
          </p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Название</th>
                <th className="hide-sm">Стратегия</th>
                <th className="num">Платёж</th>
                <th className="num">Срок</th>
                <th className="num">Переплата</th>
                <th className="hide-sm">Создан</th>
                <th aria-label="Действия" />
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td>
                    <Link to={`/scenarios/${s.id}`}>{s.name}</Link>
                    <div className="muted small">{s.debt_names.join(", ")}</div>
                  </td>
                  <td className="hide-sm">{s.strategy_name}</td>
                  <td className="num">{fmtWhole(s.monthly_budget)}</td>
                  <td className="num">{s.months_to_payoff} мес.</td>
                  <td className="num">{fmtWhole(s.total_interest)}</td>
                  <td className="hide-sm">{fmtDate(s.created_at)}</td>
                  <td className="actions">
                    <button className="icon-btn danger" title="Удалить" onClick={() => remove(s)}>
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function ScenarioPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [s, setS] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.scenario(id).then(setS).catch(setError);
  }, [id]);

  if (!s) return error ? <ErrorBox error={error} /> : <Loading />;
  const initial = s.plan.timeline.length ? s.plan.timeline[0].balance + s.plan.timeline[0].principal : 0;

  const remove = async () => {
    if (!window.confirm(`Удалить сценарий «${s.name}»?`)) return;
    try {
      await api.deleteScenario(s.id);
      navigate("/scenarios");
    } catch (err) {
      setError(err);
    }
  };

  return (
    <section>
      <Link to="/scenarios" className="back">
        ← К сценариям
      </Link>
      <div className="page-head">
        <h1>{s.name}</h1>
        <button className="btn btn-outline danger" onClick={remove}>
          Удалить
        </button>
      </div>
      <p className="muted">
        {s.strategy_name} · создан {fmtDate(s.created_at)} · долги: {s.debt_names.join(", ")}
      </p>
      {s.extra_payments.length > 0 && (
        <p className="muted">
          Досрочно:{" "}
          {s.extra_payments
            .map(
              (e) =>
                `${fmtWhole(e.amount)} ${e.regular ? `ежемесячно с ${e.month}-го месяца` : `в ${e.month}-м месяце`}, ${
                  e.effect === "term" ? "сократить срок" : "снизить платёж"
                }`,
            )
            .join("; ")}
        </p>
      )}
      <ErrorBox error={error} />

      <div className="stats">
        <Stat label="Срок" value={fmtMonths(s.months_to_payoff)} />
        <Stat label="Платёж" value={`${fmtWhole(s.monthly_budget)}/мес`} />
        <Stat label="Всего выплат" value={fmtMoney(s.total_paid)} />
        <Stat label="Переплата" value={fmtMoney(s.total_interest)} />
      </div>

      <div className="panel">
        <BalanceChart series={[{ label: "Остаток долга", color: COLORS[s.strategy], timeline: s.plan.timeline, initial }]} />
      </div>

      <h2>Порядок погашения</h2>
      <PayoffTable debts={s.plan.debts} />
      <h2>По месяцам</h2>
      <MonthTable rows={s.plan.timeline} />
    </section>
  );
}
