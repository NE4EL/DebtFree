import { useState } from "react";
import { api } from "../api";
import { parseAmount } from "../format";
import { ErrorBox, Field, RadioGroup } from "./ui";

export const EMPTY_EXTRA = { amount: "", regular: false, month: "1", debtId: "", effect: "term" };

/** Превращает состояние формы досрочного платежа в тело запроса API. */
export function extraToApi(extra) {
  return {
    amount: parseAmount(extra.amount),
    month: Number(extra.month) || 1,
    regular: extra.regular,
    debt_id: extra.debtId ? Number(extra.debtId) : null,
  };
}

/** Панель «Досрочно» (экран 4 макета). debts — для выбора долга; без них платёж идёт по стратегии. */
export function ExtraPaymentForm({ value, onChange, onSubmit, debts, busy, submitLabel = "Пересчитать", allowPaymentEffect = true }) {
  const set = (patch) => onChange({ ...value, ...patch });
  return (
    <form
      className="panel extra-form"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <h3>Досрочно</h3>
      <Field label="Сумма, ₽">
        <input
          inputMode="decimal"
          placeholder="5 000"
          value={value.amount}
          onChange={(e) => set({ amount: e.target.value })}
          required
        />
      </Field>
      <RadioGroup
        name="extra-kind"
        value={value.regular ? "regular" : "once"}
        onChange={(v) => set({ regular: v === "regular" })}
        options={[
          ["once", "Разово"],
          ["regular", "Каждый месяц"],
        ]}
      />
      <Field label={value.regular ? "Начиная с месяца" : "В месяце"}>
        <input type="number" min="1" max="600" value={value.month} onChange={(e) => set({ month: e.target.value })} />
      </Field>
      {debts && (
        <Field label="На какой долг">
          <select value={value.debtId} onChange={(e) => set({ debtId: e.target.value })}>
            <option value="">По правилу стратегии</option>
            {debts.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </Field>
      )}
      <span className="field-label">Эффект:</span>
      <RadioGroup
        name="extra-effect"
        value={value.effect}
        onChange={(effect) => set({ effect })}
        options={[["term", "Сократить срок"], ...(allowPaymentEffect ? [["payment", "Снизить платёж"]] : [])]}
      />
      <button className="btn btn-primary" disabled={busy}>
        {busy ? "Считаю…" : submitLabel}
      </button>
    </form>
  );
}

/** Сохранение сценария (UC-16): название + параметры текущего расчёта. */
export function SaveScenario({ request, onSaved }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (!open) {
    return (
      <button className="btn btn-outline" type="button" onClick={() => setOpen(true)}>
        Сохранить сценарий
      </button>
    );
  }
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await api.createScenario({ ...request(), name });
      setOpen(false);
      setName("");
      onSaved?.(saved);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="save-scenario" onSubmit={save}>
      <input
        autoFocus
        placeholder="Название сценария"
        value={name}
        maxLength={100}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <button className="btn btn-primary" disabled={busy}>
        {busy ? "Сохраняю…" : "Сохранить"}
      </button>
      <button className="btn btn-outline" type="button" onClick={() => setOpen(false)}>
        Отмена
      </button>
      <ErrorBox error={error} />
    </form>
  );
}
