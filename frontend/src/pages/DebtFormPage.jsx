import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, Field, Loading, RadioGroup } from "../components/ui";
import { DEBT_TYPES, parseAmount } from "../format";

const EMPTY = {
  name: "",
  debt_type: "credit",
  balance: "",
  annual_rate: "",
  min_payment: "",
  term_months: "",
  start_date: "",
  payment_type: "annuity",
};

const toForm = (d) => ({
  ...d,
  balance: String(d.balance),
  annual_rate: String(d.annual_rate),
  min_payment: String(d.min_payment),
  term_months: String(d.term_months),
  start_date: d.start_date || "",
});

// Проверки UC-8 на клиенте; сервер проверяет то же самое
function validate(f) {
  const errors = {};
  const num = (v) => Number(parseAmount(v));
  if (!f.name.trim()) errors.name = "Заполните название";
  if (!(num(f.balance) > 0)) errors.balance = "Остаток должен быть больше 0";
  const rate = num(f.annual_rate);
  if (parseAmount(f.annual_rate) === null || Number.isNaN(rate) || rate < 0 || rate > 100)
    errors.annual_rate = "Ставка должна быть от 0 до 100 %";
  if (!(num(f.min_payment) > 0)) errors.min_payment = "Минимальный платёж должен быть больше 0";
  else if (!errors.balance && !errors.annual_rate) {
    const interest = Math.round(num(f.balance) * rate * 100 / 1200) / 100;
    if (num(f.min_payment) <= interest)
      errors.min_payment = `Должен быть больше процентов за месяц (${interest.toLocaleString("ru-RU")} ₽), иначе долг не погашается`;
  }
  const term = Number(f.term_months);
  if (!Number.isInteger(term) || term < 1 || term > 600) errors.term_months = "Срок — от 1 до 600 месяцев";
  return errors;
}

export default function DebtFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState(id ? null : EMPTY);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (id) api.debt(id).then((d) => setForm(toForm(d))).catch(setError);
  }, [id]);

  if (!form) return error ? <ErrorBox error={error} /> : <Loading />;

  const set = (key) => (e) => {
    setForm({ ...form, [key]: e.target.value });
    setErrors({ ...errors, [key]: undefined });
  };

  const submit = async (e) => {
    e.preventDefault();
    const clientErrors = validate(form);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length) return;
    const body = {
      name: form.name.trim(),
      debt_type: form.debt_type,
      balance: parseAmount(form.balance),
      annual_rate: parseAmount(form.annual_rate),
      min_payment: parseAmount(form.min_payment),
      term_months: Number(form.term_months),
      start_date: form.start_date || null,
      payment_type: form.payment_type,
    };
    setBusy(true);
    setError(null);
    try {
      if (id) await api.updateDebt(id, body);
      else await api.createDebt(body);
      navigate("/debts");
    } catch (err) {
      setErrors(err.fields || {});
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h1>{id ? "Изменение долга" : "Добавление долга"}</h1>
      <form className="panel form-card" onSubmit={submit} noValidate>
        <Field label="Название" error={errors.name}>
          <input placeholder="Например: Кредитная карта" maxLength={100} value={form.name} onChange={set("name")} />
        </Field>
        <Field label="Вид долга">
          <select value={form.debt_type} onChange={set("debt_type")}>
            {Object.entries(DEBT_TYPES).map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <div className="grid-2">
          <Field label="Остаток долга, ₽" error={errors.balance}>
            <input inputMode="decimal" placeholder="60 000" value={form.balance} onChange={set("balance")} />
          </Field>
          <Field label="Годовая ставка, %" error={errors.annual_rate}>
            <input inputMode="decimal" placeholder="29,9" value={form.annual_rate} onChange={set("annual_rate")} />
          </Field>
          <Field label="Мин. платёж, ₽" error={errors.min_payment}>
            <input inputMode="decimal" placeholder="3 000" value={form.min_payment} onChange={set("min_payment")} />
          </Field>
          <Field label="Срок, мес." error={errors.term_months}>
            <input type="number" min="1" max="600" placeholder="24" value={form.term_months} onChange={set("term_months")} />
          </Field>
          <Field label="Дата начала (необязательно)" error={errors.start_date}>
            <input type="date" value={form.start_date} onChange={set("start_date")} />
          </Field>
        </div>
        <span className="field-label">Тип платежа:</span>
        <RadioGroup
          name="payment_type"
          value={form.payment_type}
          onChange={(v) => setForm({ ...form, payment_type: v })}
          options={[
            ["annuity", "Аннуитетный"],
            ["diff", "Дифференцированный"],
          ]}
        />
        {error && !Object.keys(error.fields || {}).length && <ErrorBox error={error} />}
        <div className="form-actions">
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Сохраняю…" : "Сохранить"}
          </button>
          <button type="button" className="btn btn-outline" onClick={() => navigate("/debts")}>
            Отмена
          </button>
        </div>
      </form>
    </section>
  );
}
