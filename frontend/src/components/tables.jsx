import { useState } from "react";
import { fmtMoney } from "../format";

const PREVIEW_ROWS = 12;

/** Помесячная таблица; длинные графики сворачиваются до первого года. */
export function MonthTable({ rows, withExtra = false }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? rows : rows.slice(0, PREVIEW_ROWS);
  return (
    <>
      <div className="table-wrap">
        <table className="table numeric">
          <thead>
            <tr>
              <th>Месяц</th>
              <th>Платёж</th>
              <th>Проценты</th>
              <th>Основной долг</th>
              {withExtra && <th>Досрочно</th>}
              <th>Остаток</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.month}>
                <td>{r.month}</td>
                <td>{fmtMoney(r.payment)}</td>
                <td>{fmtMoney(r.interest)}</td>
                <td>{fmtMoney(r.principal)}</td>
                {withExtra && <td>{r.extra ? fmtMoney(r.extra) : "—"}</td>}
                <td>{fmtMoney(r.balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > PREVIEW_ROWS && (
        <button className="btn-link" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Свернуть" : `Показать все ${rows.length} мес.`}
        </button>
      )}
    </>
  );
}

/** Когда закрывается каждый долг. */
export function PayoffTable({ debts }) {
  const sorted = [...debts].sort((a, b) => a.payoff_month - b.payoff_month);
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Долг</th>
            <th className="num">Закрыт в месяце</th>
            <th className="num hide-sm">Выплачено</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((d, i) => (
            <tr key={d.debt_id}>
              <td>{i + 1}</td>
              <td>{d.name}</td>
              <td className="num">{d.payoff_month}</td>
              <td className="num hide-sm">{fmtMoney(d.rows.reduce((s, r) => s + r.payment, 0))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
