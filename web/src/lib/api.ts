import type {
  PresetInfo,
  SimulateRequest,
  SimulateResponse,
  CompareRequest,
  CompareResponse,
} from "./types";

async function post<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json();
}

export async function fetchPresets(): Promise<PresetInfo[]> {
  const res = await fetch("/api/presets");
  if (!res.ok) throw new Error("Failed to fetch presets");
  return res.json();
}

export async function simulate(
  req: SimulateRequest
): Promise<SimulateResponse> {
  return post("/api/simulate", req);
}

export async function compare(
  req: CompareRequest
): Promise<CompareResponse> {
  return post("/api/compare", req);
}
