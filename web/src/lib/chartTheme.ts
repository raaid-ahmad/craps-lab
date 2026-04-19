import type { Config, Layout } from "plotly.js-dist-min";

export const COLORS = {
  blue: "#2563eb",
  red: "#dc2626",
  green: "#16a34a",
  purple: "#9333ea",
  orange: "#ea580c",
} as const;

export const STRATEGY_COLORS = [COLORS.blue, COLORS.red, COLORS.green, COLORS.purple, COLORS.orange];

export const BASE_LAYOUT: Partial<Layout> = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "#ffffff",
  font: {
    family: "Inter, system-ui, sans-serif",
    color: "#334155",
    size: 13,
  },
  margin: { t: 32, r: 24, b: 48, l: 56 },
  xaxis: {
    gridcolor: "#f1f5f9",
    linecolor: "#e2e8f0",
    zerolinecolor: "#e2e8f0",
  },
  yaxis: {
    gridcolor: "#f1f5f9",
    linecolor: "#e2e8f0",
    zerolinecolor: "#e2e8f0",
  },
  hoverlabel: {
    bgcolor: "#1e293b",
    font: { color: "#f8fafc", size: 13 },
    bordercolor: "transparent",
  },
  modebar: {
    bgcolor: "transparent",
    color: "#94a3b8",
    activecolor: "#2563eb",
  },
};

export const PLOTLY_CONFIG: Partial<Config> = {
  displayModeBar: true,
  modeBarButtonsToRemove: [
    "select2d",
    "lasso2d",
    "autoScale2d",
    "hoverClosestCartesian",
    "hoverCompareCartesian",
    "toggleSpikelines",
  ],
  displaylogo: false,
  responsive: true,
};
