"use client";
import { ReactNode } from "react";
import { ApiError } from "@/hooks/useApi";

interface QueryBoundaryProps {
  /** SWR's `isLoading`, or `!data && !error` for older call sites. */
  loading?: boolean;
  /** SWR's `error`. An ApiError renders with its status code and path. */
  error?: unknown;
  /** True when the request succeeded but returned nothing to show. */
  isEmpty?: boolean;
  /** Message for the empty state. */
  emptyMessage?: string;
  /** Retry handler — pass SWR's `mutate`. */
  onRetry?: () => void;
  /** Rendered as-is instead of the default skeleton while loading. */
  loadingFallback?: ReactNode;
  children: ReactNode;
}

function describe(error: unknown): { title: string; detail: string } {
  if (error instanceof ApiError) {
    return {
      title: `${error.status} — ${error.path}`,
      detail: error.body?.slice(0, 400) || "No response body.",
    };
  }
  if (error instanceof TypeError) {
    // fetch() rejects with TypeError when the backend is unreachable entirely.
    return {
      title: "Backend unreachable",
      detail: `${error.message}. Is the API running on ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}?`,
    };
  }
  if (error instanceof Error) return { title: error.name, detail: error.message };
  return { title: "Unknown error", detail: String(error) };
}

export default function QueryBoundary({
  loading,
  error,
  isEmpty,
  emptyMessage = "No data yet.",
  onRetry,
  loadingFallback,
  children,
}: QueryBoundaryProps) {
  // Error takes precedence over loading: SWR keeps revalidating on a failing key,
  // and a spinner would hide the failure indefinitely.
  if (error) {
    const { title, detail } = describe(error);
    return (
      <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-red-300">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="mono-label text-red-400">Request failed</p>
            <p className="mt-1 font-mono text-sm font-bold break-all">{title}</p>
            <pre className="mt-2 whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-red-300/70">
              {detail}
            </pre>
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="shrink-0 rounded-lg border border-red-500/40 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors hover:bg-red-500/20"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      loadingFallback ?? (
        <div className="space-y-2" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-4 animate-pulse rounded bg-white/5" style={{ animationDelay: `${i * 120}ms` }} />
          ))}
        </div>
      )
    );
  }

  if (isEmpty) {
    return (
      <div className="flex items-center justify-center p-6 text-center font-mono text-sm text-white/30">
        {emptyMessage}
      </div>
    );
  }

  return <>{children}</>;
}
