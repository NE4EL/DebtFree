import { useState } from "react";
import { api } from "../api";
import { ErrorBox, Field } from "../components/ui";
import { useAuth } from "../context";

export default function AuthPage() {
  const { login } = useAuth();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const isRegister = mode === "register";

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (isRegister) await api.register(email, password);
      await login(email, password);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="panel auth-card" onSubmit={submit}>
        <h1 className="brand-lg">DebtFree</h1>
        <p className="muted">Планировщик погашения долгов</p>
        <div className="tabs">
          <button type="button" className={!isRegister ? "tab active" : "tab"} onClick={() => setMode("login")}>
            Вход
          </button>
          <button type="button" className={isRegister ? "tab active" : "tab"} onClick={() => setMode("register")}>
            Регистрация
          </button>
        </div>
        <Field label="Email" error={error?.fields?.email}>
          <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Пароль" error={error?.fields?.password} hint={isRegister ? "Не короче 8 символов" : undefined}>
          <input
            type="password"
            autoComplete={isRegister ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        {error && !Object.keys(error.fields || {}).length && <ErrorBox error={error} />}
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Подождите…" : isRegister ? "Зарегистрироваться" : "Войти"}
        </button>
      </form>
    </div>
  );
}
