import type { Corridor, CorridorRequest, Place, Plan, PlanRequest } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {}

export const planTrip = (request: PlanRequest, signal?: AbortSignal) => send<Plan>("/api/plan", post(request, signal));

export const fetchCorridor = (request: CorridorRequest, signal?: AbortSignal) =>
  send<Corridor>("/api/corridor", post(request, signal));

export const searchPlaces = (query: string, signal?: AbortSignal) =>
  send<Place[]>(`/api/geocode?q=${encodeURIComponent(query)}`, { signal });

function post(body: unknown, signal?: AbortSignal): RequestInit {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal };
}

async function send<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(BASE_URL + path, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Could not reach the server. Check your connection and try again.");
  }
  if (!response.ok) throw new ApiError(await errorMessage(response));
  return response.json();
}

async function errorMessage(response: Response): Promise<string> {
  const body = await response.json().catch(() => null);
  if (typeof body?.error === "string") return body.error;
  if (response.status === 502) return "The weather or routing service did not answer. Try again in a moment.";
  return `The server returned an error (${response.status}).`;
}
