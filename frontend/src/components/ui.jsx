import { NavLink } from "react-router-dom";
import { useAuth } from "../context";

export function NavBar() {
  const { user, logout } = useAuth();
  const link = ({ isActive }) => (isActive ? "nav-link active" : "nav-link");
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <span className="brand">DebtFree</span>
        <nav className="nav-links">
          <NavLink to="/debts" className={link}>
            Долги
          </NavLink>
          <NavLink to="/compare" className={link}>
            Сравнение
          </NavLink>
          <NavLink to="/plan" className={link}>
            График
          </NavLink>
          <NavLink to="/scenarios" className={link}>
            Сценарии
          </NavLink>
        </nav>
        <div className="nav-user">
          <span className="nav-email" title={user?.email}>
            {user?.email}
          </span>
          <button className="btn-link light" onClick={logout}>
            Выйти
          </button>
        </div>
      </div>
    </header>
  );
}

export function Field({ label, error, hint, children }) {
  return (
    <label className={error ? "field has-error" : "field"}>
      <span className="field-label">{label}</span>
      {children}
      {error ? <span className="field-error">{error}</span> : hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return (
    <div className="alert alert-error" role="alert">
      {typeof error === "string" ? error : error.message}
    </div>
  );
}

export function Loading({ text = "Загрузка…" }) {
  return <p className="muted">{text}</p>;
}

export function Stat({ label, value, accent }) {
  return (
    <div className={accent ? "stat accent" : "stat"}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

export function RadioGroup({ name, value, onChange, options }) {
  return (
    <div className="radio-group" role="radiogroup">
      {options.map(([v, label]) => (
        <label key={v} className="radio">
          <input type="radio" name={name} value={v} checked={value === v} onChange={() => onChange(v)} />
          {label}
        </label>
      ))}
    </div>
  );
}
