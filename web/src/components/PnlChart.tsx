import Plot from "react-plotly.js";
import type { SimulateResponse } from "../lib/types";
import { BASE_LAYOUT, PLOTLY_CONFIG, STRATEGY_COLORS } from "../lib/chartTheme";
import { fmtPnl } from "../lib/format";
import ChartCard from "./ChartCard";

interface Props {
  results: SimulateResponse[];
}

export default function PnlChart({ results }: Props) {
  const traces = results.map((r, i) => ({
    x: r.charts.pnl_values,
    type: "histogram" as const,
    nbinsx: 50,
    name: r.summary.strategy_name,
    marker: { color: STRATEGY_COLORS[i], opacity: results.length > 1 ? 0.55 : 0.7 },
    hovertemplate: "%{x:$,.0f}<br>%{y} sessions<extra></extra>",
  }));

  const layout = {
    ...BASE_LAYOUT,
    barmode: results.length > 1 ? ("overlay" as const) : undefined,
    xaxis: { ...BASE_LAYOUT.xaxis, title: { text: "Net P&L ($)" } },
    yaxis: { ...BASE_LAYOUT.yaxis, title: { text: "Sessions" } },
    shapes: [
      {
        type: "line" as const,
        x0: 0, x1: 0,
        y0: 0, y1: 1,
        yref: "paper" as const,
        line: { color: "#94a3b8", width: 1.5, dash: "dash" as const },
      },
    ],
    showlegend: results.length > 1,
    legend: { x: 0.01, y: 0.99, bgcolor: "rgba(255,255,255,0.8)" },
  };

  // Build interpretation text — one sentence per strategy in compare mode
  const interp =
    results.length > 1
      ? results
          .map((r) => {
            const s = r.summary;
            return (
              `${s.strategy_name}: median ${fmtPnl(s.median_pnl)}, ` +
              `90% between ${fmtPnl(s.percentile_5)} and ${fmtPnl(s.percentile_95)}.`
            );
          })
          .join(" ")
      : (() => {
          const s = results[0].summary;
          return (
            `Most likely outcome: around ${fmtPnl(s.median_pnl)}. ` +
            `Results range from about ${fmtPnl(s.percentile_5)} to ${fmtPnl(s.percentile_95)} ` +
            `in 90% of sessions.`
          );
        })();

  return (
    <ChartCard title="P&L Distribution" interp={interp}>
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

