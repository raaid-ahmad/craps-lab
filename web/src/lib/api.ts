import type {
  PresetInfo,
  SimulateRequest,
  SimulateResponse,
  CompareRequest,
  CompareResponse,
} from "./types";

const DEFAULT_TIMEOUT_MS = 30_000;

async function post<T>(
  url: string,
  body: unknown,
  signal?: AbortSignal
): Promise<T> {
  const ctrl = new AbortController();
  const timeoutId = window.setTimeout(
    () => ctrl.abort(new DOMException("Request timed out", "TimeoutError")),
    DEFAULT_TIMEOUT_MS
  );

  if (signal) {
    if (signal.aborted) {
      ctrl.abort(signal.reason);
    } else {
      signal.addEventListener("abort", () => ctrl.abort(signal.reason), {
        once: true,
      });
    }
  }

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(`API error ${res.status}: ${detail}`);
    }
    return res.json();
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function fetchPresets(): Promise<PresetInfo[]> {
  const res = await fetch("/api/presets");
  if (!res.ok) throw new Error("Failed to fetch presets");
  return res.json();
}

export async function simulate(
  req: SimulateRequest,
  signal?: AbortSignal
): Promise<SimulateResponse> {
  return post("/api/simulate", req, signal);
}

export async function compare(
  req: CompareRequest,
  signal?: AbortSignal
): Promise<CompareResponse> {
  return post("/api/compare", req, signal);
}
