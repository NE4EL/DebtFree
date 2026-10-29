const money = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const whole = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
const rate = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 1, maximumFractionDigits: 2 });

export const fmtMoney = (v) => `${money.format(v)} ₽`;
export const fmtWhole = (v) => `${whole.format(v)} ₽`;
export const fmtRate = (v) => `${rate.format(v)} %`;

export function fmtMonths(n) {
  const years = Math.floor(n / 12);
  const months = n % 12;
  const short = `${n} мес.`;
  if (years === 0) return short;
  return `${short} (${years} г.${months ? ` ${months} мес.` : ""})`;
}

export function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("ru-RU");
}

// «60 000,50» → "60000.50"; пустая строка → null
export function parseAmount(text) {
  const s = String(text ?? "").replace(/[\s ]/g, "").replace(",", ".");
  return s === "" ? null : s;
}

export const STRATEGY_LABELS = {
  avalanche: "Лавина",
  snowball: "Снежный ком",
  minimum: "Только мин. платежи",
};

export const DEBT_TYPES = {
  credit: "Кредит",
  card: "Кредитная карта",
  installment: "Рассрочка",
  mortgage: "Ипотека",
  other: "Другое",
};
