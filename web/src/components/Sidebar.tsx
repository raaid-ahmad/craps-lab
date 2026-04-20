import { useEffect, useState } from "react";
import { fetchPresets } from "../lib/api";
import type { PresetInfo } from "../lib/types";

export interface SimConfig {
  strategy: string;
  strategyB: string | null;
  bankroll: number;
  hours: number;
  rollsPerHour: number;
  stopWin: number | null;
  stopLoss: number | null;
  sessions: number;
}

interface Props {
  onRun: (config: SimConfig) => void;
  loading: boolean;
}

export default function Sidebar({ onRun, loading }: Props) {
  const [presets, setPresets] = useState<PresetInfo[]>([]);
  const [presetError, setPresetError] = useState<string | null>(null);
  const [strategy, setStrategy] = useState("");
  const [compare, setCompare] = useState(false);
  const [strategyB, setStrategyB] = useState("");
  const [bankroll, setBankroll] = useState(500);
  const [hours, setHours] = useState(4);
  const [rollsPerHour, setRollsPerHour] = useState(60);
  const [sessions, setSessions] = useState(10000);
  const [useStopWin, setUseStopWin] = useState(false);
  const [stopWin, setStopWin] = useState(200);
  const [useStopLoss, setUseStopLoss] = useState(false);
  const [stopLoss, setStopLoss] = useState(300);

  useEffect(() => {
    fetchPresets()
      .then((p) => {
        setPresets(p);
        setPresetError(null);
        if (p.length > 0) {
          setStrategy(p[0].slug);
          if (p.length > 1) setStrategyB(p[1].slug);
        }
      })
      .catch(() => {
        setPresetError(
          "Could not reach the API. Start it in another terminal with: uvicorn api.main:app --reload"
        );
      });
  }, []);

  const handleRun = () => {
    onRun({
      strategy,
      strategyB: compare ? strategyB : null,
      bankroll,
      hours,
      rollsPerHour,
      stopWin: useStopWin ? stopWin : null,
      stopLoss: useStopLoss ? stopLoss : null,
      sessions,
    });
  };

  const selectedPreset = presets.find((p) => p.slug === strategy);

  return (
    <aside className="w-80 shrink-0 bg-slate-900 text-slate-200 flex flex-col h-screen overflow-y-auto">
      {/* Header */}
      <div className="px-5 pt-6 pb-4 border-b border-slate-700/50">
        <h1 className="text-lg font-semibold text-white tracking-tight">
          craps-lab
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Strategy simulator
        </p>
      </div>

      <div className="flex-1 px-5 py-5 space-y-5">
        {presetError && (
          <div
            role="alert"
            className="rounded-md border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-200 leading-relaxed"
          >
            {presetError}
          </div>
        )}

        {/* Strategy */}
        <fieldset>
          <Label>Strategy</Label>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="input-field"
            disabled={presets.length === 0}
          >
            {presets.map((p) => (
              <option key={p.slug} value={p.slug}>
                {p.name}
              </option>
            ))}
          </select>
          {selectedPreset && (
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              {selectedPreset.description}
            </p>
          )}
        </fieldset>

        {/* Compare toggle */}
        <label className="flex items-center gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={compare}
            onChange={(e) => setCompare(e.target.checked)}
            className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500
                       focus:ring-blue-500 focus:ring-offset-0 focus:ring-offset-slate-900"
          />
          <span className="text-sm text-slate-300">Compare strategies</span>
        </label>

        {compare && (
          <fieldset>
            <Label>Compare with</Label>
            <select
              value={strategyB}
              onChange={(e) => setStrategyB(e.target.value)}
              className="input-field"
            >
              {presets
                .filter((p) => p.slug !== strategy)
                .map((p) => (
                  <option key={p.slug} value={p.slug}>
                    {p.name}
                  </option>
                ))}
            </select>
          </fieldset>
        )}

        <hr className="border-slate-700/50" />

        {/* Session parameters */}
        <fieldset>
          <Label>Bankroll</Label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
              $
            </span>
            <input
              type="number"
              value={bankroll}
              onChange={(e) => setBankroll(Number(e.target.value))}
              min={1}
              className="input-field pl-7"
            />
          </div>
        </fieldset>

        <div className="grid grid-cols-2 gap-3">
          <fieldset>
            <Label>Hours</Label>
            <input
              type="number"
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
              min={0.5}
              step={0.5}
              className="input-field"
            />
          </fieldset>
          <fieldset>
            <Label>Rolls/hr</Label>
            <input
              type="number"
              value={rollsPerHour}
              onChange={(e) => setRollsPerHour(Number(e.target.value))}
              min={1}
              className="input-field"
            />
          </fieldset>
        </div>

        <fieldset>
          <Label>Sessions</Label>
          <input
            type="number"
            value={sessions}
            onChange={(e) => setSessions(Number(e.target.value))}
            min={100}
            max={100000}
            step={1000}
            className="input-field"
          />
        </fieldset>

        <hr className="border-slate-700/50" />

        {/* Stop conditions */}
        <fieldset>
          <label className="flex items-center gap-2.5 cursor-pointer select-none mb-2">
            <input
              type="checkbox"
              checked={useStopWin}
              onChange={(e) => setUseStopWin(e.target.checked)}
              className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500
                         focus:ring-blue-500 focus:ring-offset-0 focus:ring-offset-slate-900"
            />
            <span className="text-sm text-slate-300">Stop-win</span>
          </label>
          {useStopWin && (
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
                $
              </span>
              <input
                type="number"
                value={stopWin}
                onChange={(e) => setStopWin(Number(e.target.value))}
                min={1}
                className="input-field pl-7"
              />
            </div>
          )}
        </fieldset>

        <fieldset>
          <label className="flex items-center gap-2.5 cursor-pointer select-none mb-2">
            <input
              type="checkbox"
              checked={useStopLoss}
              onChange={(e) => setUseStopLoss(e.target.checked)}
              className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500
                         focus:ring-blue-500 focus:ring-offset-0 focus:ring-offset-slate-900"
            />
            <span className="text-sm text-slate-300">Stop-loss</span>
          </label>
          {useStopLoss && (
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
                $
              </span>
              <input
                type="number"
                value={stopLoss}
                onChange={(e) => setStopLoss(Number(e.target.value))}
                min={1}
                className="input-field pl-7"
              />
            </div>
          )}
        </fieldset>
      </div>

      {/* Run button */}
      <div className="px-5 pb-5 pt-2">
        <button
          onClick={handleRun}
          disabled={loading || presets.length === 0}
          className="w-full py-2.5 rounded-lg font-semibold text-sm transition-all
                     bg-blue-600 hover:bg-blue-500 text-white
                     disabled:opacity-50 disabled:cursor-not-allowed
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              Simulating...
            </span>
          ) : (
            "Run Simulation"
          )}
        </button>
      </div>
    </aside>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5">
      {children}
    </label>
  );
}
