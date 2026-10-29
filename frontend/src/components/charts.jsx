import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";
import { STRATEGY_LABELS, fmtMoney, fmtWhole } from "../format";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend, Filler);

export const COLORS = {
  avalanche: "#16a34a",
  snowball: "#2563eb",
  minimum: "#dc2626",
  base: "#16a34a",
  extra: "#2563eb",
};

const shortMoney = (v) => (Math.abs(v) >= 1000 ? `${Math.round(v / 1000)} тыс.` : `${v}`);

/**
 * Линии остатка долга по месяцам.
 * series: [{ label, color, dashed, timeline: [{month, balance}], initial }]
 */
export function BalanceChart({ series, height = 300 }) {
  const months = Math.max(...series.map((s) => s.timeline.length), 0);
  const labels = Array.from({ length: months + 1 }, (_, i) => i);
  const data = {
    labels,
    datasets: series.map((s) => ({
      label: s.label,
      data: [s.initial, ...s.timeline.map((m) => m.balance)],
      borderColor: s.color,
      backgroundColor: s.color,
      borderDash: s.dashed ? [6, 4] : undefined,
      borderWidth: 2.5,
      pointRadius: 0,
      pointHitRadius: 8,
      tension: 0.15,
    })),
  };
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "bottom", labels: { usePointStyle: true, pointStyle: "line" } },
      tooltip: {
        callbacks: {
          title: (items) => `Месяц ${items[0].label}`,
          label: (ctx) => (ctx.raw === undefined ? null : `${ctx.dataset.label}: ${fmtMoney(ctx.raw)}`),
        },
      },
    },
    scales: {
      x: { title: { display: true, text: "Месяцы" }, ticks: { maxTicksLimit: 13 } },
      y: { beginAtZero: true, ticks: { callback: shortMoney } },
    },
  };
  return (
    <div className="chart" style={{ height }}>
      <Line data={data} options={options} />
    </div>
  );
}

/** Горизонтальные столбцы переплаты по стратегиям. */
export function OverpayChart({ results }) {
  const data = {
    labels: results.map((r) => STRATEGY_LABELS[r.strategy]),
    datasets: [
      {
        label: "Переплата",
        data: results.map((r) => r.total_interest),
        backgroundColor: results.map((r) => COLORS[r.strategy]),
        borderRadius: 4,
      },
    ],
  };
  const options = {
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => fmtMoney(ctx.raw) } },
    },
    scales: { x: { beginAtZero: true, ticks: { callback: shortMoney } } },
  };
  return (
    <div className="chart" style={{ height: 70 + results.length * 40 }}>
      <Bar data={data} options={options} aria-label={results.map((r) => `${r.strategy_name}: ${fmtWhole(r.total_interest)}`).join(", ")} />
    </div>
  );
}
