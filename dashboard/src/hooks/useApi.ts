"use client";
import useSWR, { SWRConfiguration } from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const fetcher = (path: string) => fetch(`${API_BASE}${path}`).then(r => r.json());

export function useApi<T>(path: string | null, config?: SWRConfiguration) {
  return useSWR<T>(path, fetcher, { refreshInterval: 5000, ...config });
}
