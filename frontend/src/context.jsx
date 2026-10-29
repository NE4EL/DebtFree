import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "./api";

const AuthContext = createContext(null);
const PlanContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!getToken());

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (getToken()) {
      api
        .me()
        .then(setUser)
        .catch(logout)
        .finally(() => setReady(true));
    }
  }, [logout]);

  const login = useCallback(async (email, password) => {
    const { access_token } = await api.login(email, password);
    setToken(access_token);
    setUser(await api.me());
  }, []);

  const value = useMemo(() => ({ user, ready, login, logout }), [user, ready, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

const PLAN_KEY = "debtfree.plan";

function loadPlan() {
  try {
    return { budget: "", strategy: "avalanche", ...JSON.parse(localStorage.getItem(PLAN_KEY) || "{}") };
  } catch {
    return { budget: "", strategy: "avalanche" };
  }
}

// Бюджет и выбранная стратегия общие для экранов «Долги», «Сравнение», «График»
export function PlanProvider({ children }) {
  const [plan, setPlan] = useState(loadPlan);
  const update = useCallback((patch) => {
    setPlan((prev) => {
      const next = { ...prev, ...patch };
      try {
        localStorage.setItem(PLAN_KEY, JSON.stringify(next));
      } catch {
        /* не критично */
      }
      return next;
    });
  }, []);
  const value = useMemo(() => ({ ...plan, update }), [plan, update]);
  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}

export const usePlan = () => useContext(PlanContext);
