import { API_BASE } from "./env";
import type { ApiResponse } from "./types";

async function request<T>(path: string, init?: RequestInit, token?: string): Promise<ApiResponse<T>> {
  const headers = new Headers(init?.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);

  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });

  let parsed: ApiResponse<T> | null = null;
  try {
    parsed = (await res.json()) as ApiResponse<T>;
  } catch {
    parsed = null;
  }

  if (!res.ok) {
    return { data: null as T, error: parsed?.error || `HTTP ${res.status}` };
  }
  return parsed || ({ data: null as T, error: "Empty response" } as ApiResponse<T>);
}

export function apiGet<T>(path: string, token?: string) {
  return request<T>(path, { method: "GET" }, token);
}

export function apiPost<T>(path: string, body: unknown, token?: string) {
  const payload = body instanceof FormData ? body : JSON.stringify(body);
  return request<T>(path, { method: "POST", body: payload }, token);
}

export function apiPatch<T>(path: string, body: unknown, token?: string) {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(body) }, token);
}

export function apiDelete<T>(path: string, token?: string) {
  return request<T>(path, { method: "DELETE" }, token);
}
