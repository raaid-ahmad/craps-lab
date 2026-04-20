import { useEffect, useRef, useState } from "react";
import Sidebar, { type SimConfig } from "./components/Sidebar";
import StatCards from "./components/StatCards";
import PnlChart from "./components/PnlChart";
import EquityChart from "./components/EquityChart";
import DrawdownChart from "./components/DrawdownChart";
import { simulate, compare } from "./lib/api";
import type { SimulateResponse } from "./lib/types";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SimulateResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [configLabel, setConfigLabel] = useState("");
  const [bankroll, setBankroll] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!loading) return;
    const start = Date.now();
    setElapsed(0);
    const id = window.setInterval(
      () => setElapsed((Date.now() - start) / 1000),
      200
    );
    return () => window.clearInterval(id);
  }, [loading]);

  const handleCancel = () => {
    abortRef.current?.abort(new DOMException("Cancelled", "AbortError"));
  };

  const handleRun = async (config: SimConfig) => {
    setLoading(true);
    setError(null);

    const label = `$${config.bankroll} bankroll | ${config.hours}h (${Math.round(config.hours * config.rollsPerHour)} rolls) | ${config.sessions.toLocaleString()} sessions`;
    setConfigLabel(label);
    setBankroll(config.bankroll);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      if (config.strategyB) {
        const res = await compare(
          {
            strategies: [config.strategy, config.strategyB],
            bankroll: config.bankroll,
            hours: config.hours,
            rolls_per_hour: config.rollsPerHour,
            stop_win: config.stopWin,
            stop_loss: config.stopLoss,
            sessions: config.sessions,
          },
          ctrl.signal
        );
        setResults(res.results);
      } else {
        const res = await simulate(
          {
            strategy: config.strategy,
            bankroll: config.bankroll,
            hours: config.hours,
            rolls_per_hour: config.rollsPerHour,
            stop_win: config.stopWin,
            stop_loss: config.stopLoss,
            sessions: config.sessions,
          },
          ctrl.signal
        );
        setResults([res]);
      }
    } catch (e) {
      if (ctrl.signal.aborted) {
        const reason = ctrl.signal.reason;
        if (reason instanceof DOMException && reason.name === "TimeoutError") {
          setError("Run timed out after 30s. Try fewer sessions or shorter hours.");
        } else {
          setError("Run cancelled.");
        }
      } else {
        setError(e instanceof Error ? e.message : "Simulation failed");
      }
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar onRun={handleRun} loading={loading} />

      <main className="flex-1 overflow-y-auto">
        {!results && !loading && <EmptyState />}

        {error && (
          <div className="m-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading && <LoadingSkeleton elapsed={elapsed} onCancel={handleCancel} />}

        {results && !loading && (
          <div className="p-6 space-y-6 max-w-7xl">
            {/* Config banner */}
            <div className="flex items-baseline gap-3">
              <h2 className="text-lg font-semibold text-slate-800">
                {results.map((r) => r.summary.strategy_name).join(" vs ")}
              </h2>
              <span className="text-sm text-slate-400">{configLabel}</span>
            </div>

            {/* Practical summary sentence */}
            <PracticalSummary results={results} />

            <StatCards results={results.map((r) => r.summary)} />

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <PnlChart results={results} />
              <EquityChart results={results} bankroll={bankroll} />
            </div>

            <DrawdownChart results={results} />
          </div>
        )}
      </main>
    </div>
  );
}

function PracticalSummary({ results }: { results: SimulateResponse[] }) {
  return (
    <div className="space-y-2">
      {results.map((r) => {
        const s = r.summary;
        const winPct = (s.win_rate * 100).toFixed(0);
        const avgWin = Math.round(s.avg_win);
        const avgLoss = Math.round(Math.abs(s.avg_loss));
        const worst10 = Math.round(Math.abs(s.percentile_10));
        const best10 = Math.round(s.percentile_90);

        return (
          <p key={s.strategy_name} className="text-sm text-slate-600 leading-relaxed">
            <span className="font-semibold text-slate-800">{s.strategy_name}:</span>{" "}
            In a given session your chance of profit is{" "}
            <span className="font-semibold text-slate-800">{winPct}%</span>.
            Average win is{" "}
            <span className="font-semibold text-green-700">+${avgWin}</span>{" "}
            and average loss is{" "}
            <span className="font-semibold text-red-600">-${avgLoss}</span>.
            10% of the time you'll lose more than{" "}
            <span className="font-semibold text-red-600">${worst10}</span>{" "}
            and 10% of the time you'll make more than{" "}
            <span className="font-semibold text-green-700">${best10}</span>.
          </p>
        );
      })}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center max-w-md">
        <div className="text-5xl mb-4 opacity-40">
          <svg className="w-16 h-16 mx-auto text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold text-slate-500">
          Pick a strategy and run
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Configure your session in the sidebar and hit Run Simulation
        </p>
      </div>
    </div>
  );
}

function LoadingSkeleton({ elapsed, onCancel }: { elapsed: number; onCancel: () => void }) {
  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3">
        <span className="text-sm text-slate-600">
          Simulating… <span className="font-mono text-slate-800">{elapsed.toFixed(1)}s</span>
        </span>
        <button
          type="button"
          onClick={onCancel}
          className="text-xs font-semibold text-red-600 hover:text-red-700 px-3 py-1.5 rounded-md border border-red-200 hover:bg-red-50"
        >
          Cancel
        </button>
      </div>
      <div className="animate-pulse space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 h-24" />
          ))}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-slate-200 h-96" />
          <div className="bg-white rounded-xl border border-slate-200 h-96" />
        </div>
        <div className="bg-white rounded-xl border border-slate-200 h-96" />
      </div>
    </div>
  );
}
