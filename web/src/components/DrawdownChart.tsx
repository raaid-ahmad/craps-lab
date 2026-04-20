import Plot from "react-plotly.js";
import type { SimulateResponse } from "../lib/types";
import { BASE_LAYOUT, PLOTLY_CONFIG, STRATEGY_COLORS } from "../lib/chartTheme";
import ChartCard from "./ChartCard";

interface Props {
  results: SimulateResponse[];
}

export default function DrawdownChart({ results }: Props) {
  const traces = results.map((r, i) => ({
    x: r.charts.drawdown_values,
    type: "histogram" as const,
    nbinsx: 50,
    name: r.summary.strategy_name,
    marker: { color: STRATEGY_COLORS[i], opacity: results.length > 1 ? 0.55 : 0.7 },
    hovertemplate: "$%{x:,.0f} drawdown<br>%{y} sessions<extra></extra>",
  }));

  const layout = {
    ...BASE_LAYOUT,
    barmode: results.length > 1 ? ("overlay" as const) : undefined,
    xaxis: { ...BASE_LAYOUT.xaxis, title: { text: "Max Drawdown ($)" } },
    yaxis: { ...BASE_LAYOUT.yaxis, title: { text: "Sessions" } },
    showlegend: results.length > 1,
    legend: { x: 0.99, xanchor: "right" as const, y: 0.99, bgcolor: "rgba(255,255,255,0.8)" },
  };

  const s = results[0].summary;
  const bustPct = Math.round(s.bust_rate * 100);
  const interp =
    `Average peak-to-trough drop is $${Math.round(s.mean_drawdown)} per session, ` +
    `including the ${bustPct}% of sessions that busted (entire bankroll lost). ` +
    `Size your bankroll for the deep end of this distribution, not the mean.`;

  return (
    <ChartCard title="Drawdown Distribution" interp={interp}>
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
