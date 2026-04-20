import type {
  PresetInfo,
  SimulateRequest,
  SimulateResponse,
  CompareRequest,
  CompareResponse,
} from "./types";

const DEFAULT_TIMEOUT_MS = 30_000;

interface FastApiValidationError {
  loc?: unknown[];
  msg?: string;
}

async function readErrorMessage(res: Response): Promise<string> {
  let raw = "";
  try {
    raw = await res.text();
  } catch {
    return `Request failed (HTTP ${res.status}).`;
  }

  try {
    const data = JSON.parse(raw) as { detail?: unknown };
    const detail = data.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return (detail as FastApiValidationError[])
        .map((d) => {
          const loc = Array.isArray(d.loc) ? d.loc.slice(1).join(".") : "";
          const msg = d.msg ?? "invalid";
          return loc ? `${loc}: ${msg}` : msg;
        })
        .join("; ");
    }
  } catch {
    // body wasn't JSON — fall through to the raw text
  }

  return raw || `Request failed (HTTP ${res.status}).`;
}

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
      throw new Error(await readErrorMessage(res));
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
