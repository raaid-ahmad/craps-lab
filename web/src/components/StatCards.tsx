import type { SummaryStats } from "../lib/types";
import { STRATEGY_COLORS } from "../lib/chartTheme";

interface Props {
  results: SummaryStats[];
}

function fmt(n: number): string {
  return n >= 0 ? `+$${Math.round(n)}` : `-$${Math.round(Math.abs(n))}`;
}

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

interface CardDef {
  label: string;
  getValue: (s: SummaryStats) => string;
  subtext?: (s: SummaryStats) => string;
}

const CARDS: CardDef[] = [
  {
    label: "Chance of Profit",
    getValue: (s) => pct(s.win_rate),
    subtext: (s) => `${pct(s.bust_rate)} bust rate`,
  },
  {
    label: "Average Win",
    getValue: (s) => fmt(s.avg_win),
    subtext: () => `when you're up`,
  },
  {
    label: "Average Loss",
    getValue: (s) => fmt(s.avg_loss),
    subtext: () => `when you're down`,
  },
  {
    label: "Worst 10%",
    getValue: (s) => fmt(s.percentile_10),
    subtext: () => `10th percentile outcome`,
  },
  {
    label: "Best 10%",
    getValue: (s) => fmt(s.percentile_90),
    subtext: () => `90th percentile outcome`,
  },
  {
    label: "Typical Drawdown",
    getValue: (s) => `-$${Math.round(s.mean_drawdown)}`,
    subtext: () => `avg peak-to-trough drop`,
  },
];

export default function StatCards({ results }: Props) {
  const isCompare = results.length > 1;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
      {CARDS.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm"
        >
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
            {card.label}
          </p>
          {results.map((s, i) => (
            <div key={s.strategy_name} className={i > 0 ? "mt-2 pt-2 border-t border-slate-100" : ""}>
              <p className="text-xl font-semibold text-slate-900 tabular-nums">
                {isCompare && (
                  <span
                    className="inline-block w-2 h-2 rounded-full mr-2"
                    style={{ backgroundColor: STRATEGY_COLORS[i] }}
                  />
                )}
                {card.getValue(s)}
              </p>
              {card.subtext && (
                <p className="text-xs text-slate-400 mt-0.5">
                  {isCompare && <span className="font-medium text-slate-500">{s.strategy_name} — </span>}
                  {card.subtext(s)}
                </p>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
