import Plot from "react-plotly.js";
import type { Data } from "plotly.js-dist-min";
import type { SimulateResponse } from "../lib/types";
import { BASE_LAYOUT, PLOTLY_CONFIG, STRATEGY_COLORS } from "../lib/chartTheme";
import ChartCard from "./ChartCard";

interface Props {
  results: SimulateResponse[];
  bankroll: number;
}

export default function EquityChart({ results, bankroll }: Props) {
  const traces: Data[] = [];

  results.forEach((r, si) => {
    const color = STRATEGY_COLORS[si];
    const ep = r.charts.equity_percentiles;
    const label = results.length > 1 ? ` (${r.summary.strategy_name})` : "";

    // P5-P95 band — outer 90% of sessions
    traces.push({
      x: [...ep.rolls, ...ep.rolls.slice().reverse()],
      y: [...ep.p95, ...ep.p5.slice().reverse()],
      fill: "toself",
      fillcolor: hexToRgba(color, 0.08),
      line: { color: "transparent" },
      name: `90% of sessions (5th–95th pct)${label}`,
      showlegend: true,
      hoverinfo: "skip",
      type: "scatter",
    });

    // P25-P75 band — interquartile range
    traces.push({
      x: [...ep.rolls, ...ep.rolls.slice().reverse()],
      y: [...ep.p75, ...ep.p25.slice().reverse()],
      fill: "toself",
      fillcolor: hexToRgba(color, 0.15),
      line: { color: "transparent" },
      name: `Middle half (25th–75th pct)${label}`,
      showlegend: true,
      hoverinfo: "skip",
      type: "scatter",
    });

    // Median line
    traces.push({
      x: ep.rolls,
      y: ep.p50,
      mode: "lines",
      line: { color, width: 2 },
      name: `Median${label}`,
      hovertemplate: "Roll %{x}<br>Bankroll: $%{y:,.0f}<extra></extra>",
      type: "scatter",
    });

    // Sample paths
    r.charts.equity_sample.slice(0, 8).forEach((curve, ci) => {
      traces.push({
        x: Array.from({ length: curve.length }, (_, i) => i),
        y: curve,
        mode: "lines",
        line: { color: hexToRgba(color, 0.15), width: 0.8 },
        showlegend: false,
        hoverinfo: "skip",
        type: "scatter",
        name: `path-${si}-${ci}`,
      });
    });
  });

  const layout = {
    ...BASE_LAYOUT,
    xaxis: { ...BASE_LAYOUT.xaxis, title: { text: "Roll" } },
    yaxis: { ...BASE_LAYOUT.yaxis, title: { text: "Bankroll ($)" } },
    shapes: [
      {
        type: "line" as const,
        x0: 0, x1: 1,
        xref: "paper" as const,
        y0: bankroll, y1: bankroll,
        line: { color: "#94a3b8", width: 1, dash: "dash" as const },
      },
    ],
    showlegend: true,
    legend: { x: 0.01, y: 0.99, bgcolor: "rgba(255,255,255,0.8)" },
  };

  const s = results[0].summary;
  const interp =
    `Half of sessions end inside the darker band; 90% inside the lighter band. ` +
    `The dashed line is your starting bankroll. ` +
    `Typical peak-to-trough drawdown: $${Math.round(s.mean_drawdown)}.`;

  return (
    <ChartCard title="Bankroll Over Time" interp={interp}>
      <Plot
        data={traces}
        layout={layout}
        config={PLOTLY_CONFIG}
        className="w-full"
        useResizeHandler
        style={{ width: "100%", height: 360 }}
      />
    </ChartCard>
  );
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
