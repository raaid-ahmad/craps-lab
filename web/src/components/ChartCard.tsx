import type { ReactNode } from "react";

interface Props {
  title: string;
  interp: string;
  children: ReactNode;
}

export default function ChartCard({ title, interp, children }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 pt-4 pb-2">
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      </div>
      {children}
      <p className="px-5 pb-4 text-xs text-slate-400 leading-relaxed">{interp}</p>
    </div>
  );
}
