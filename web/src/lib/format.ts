export function fmtPnl(n: number): string {
  return n >= 0 ? `+$${Math.round(n)}` : `-$${Math.round(Math.abs(n))}`;
}
