"use client";
import useSWR, { SWRConfiguration } from "swr";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

/** Error thrown by the fetcher on any non-2xx response. Carries enough to render a diagnostic. */
export class ApiError extends Error {
  readonly status: number;
  readonly path: string;
  readonly body: string;

  constructor(status: number, path: string, body: string) {
    super(`API ${status} on ${path}`);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
    this.body = body;
  }
}

const fetcher = async (path: string) => {
  const cleanPath = path.startsWith("/") ? path : "/" + path;
  const res = await fetch(`${API_BASE}${cleanPath}`);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, cleanPath, body);
  }
  return res.json();
};

export function useApi<T>(path: string | null, config?: SWRConfiguration) {
  return useSWR<T>(path, fetcher, { refreshInterval: 5000, ...config });
}
