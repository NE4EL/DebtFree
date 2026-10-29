const TOKEN_KEY = "debtfree.token";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* хранилище недоступно — токен живёт до перезагрузки */
  }
}

export class ApiError extends Error {
  constructor(status, message, errors = []) {
    super(message);
    this.status = status;
    // ошибки по полям: { balance: "Остаток: должно быть больше 0", ... }
    this.fields = Object.fromEntries(errors.filter((e) => e.field).map((e) => [e.field, e.message]));
  }
}

let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

async function request(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError(0, "Сервер недоступен. Проверьте, что backend запущен.");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized();
    throw new ApiError(res.status, data.detail || `Ошибка ${res.status}`, data.errors);
  }
  return data;
}

export const api = {
  register: (email, password) => request("POST", "/auth/register", { email, password }),
  login: (email, password) => request("POST", "/auth/login", { email, password }),
  me: () => request("GET", "/auth/me"),

  debts: () => request("GET", "/debts"),
  debt: (id) => request("GET", `/debts/${id}`),
  createDebt: (data) => request("POST", "/debts", data),
  updateDebt: (id, data) => request("PUT", `/debts/${id}`, data),
  deleteDebt: (id) => request("DELETE", `/debts/${id}`),

  schedule: (data) => request("POST", "/schedule", data),
  compare: (data) => request("POST", "/compare", data),
  earlyPayment: (data) => request("POST", "/early-payment", data),

  scenarios: () => request("GET", "/scenarios"),
  scenario: (id) => request("GET", `/scenarios/${id}`),
  createScenario: (data) => request("POST", "/scenarios", data),
  deleteScenario: (id) => request("DELETE", `/scenarios/${id}`),
};
