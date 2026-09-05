"use client";
import { useApi } from "@/hooks/useApi";
import { useWebSocketContext } from "@/components/WebSocketProvider";

/**
 * The simulation clock.
 *
 * Audit rows are stamped with the virtual date, which runs ahead of wall-clock
 * time by one day per tick. Formatting those against `new Date()` produced
 * "-864000s ago" in the activity feed and overdue counts that disagreed with the
 * status ladder. Everything time-related must be computed against this.
 */
export function useVirtualDate() {
  const { virtualDate: wsDate } = useWebSocketContext();
  const { data, error, isLoading } = useApi<{ virtual_date: string }>("/api/simulation/state");

  // The socket is fresher than the 5s poll during an auto-run.
  const iso = wsDate ?? data?.virtual_date ?? null;
  const virtualNow = iso ? new Date(iso) : null;

  /** Days between the virtual clock and an ISO timestamp. Positive = in the past. */
  const daysSince = (isoDate: string | null | undefined): number | null => {
    if (!isoDate || !virtualNow) return null;
    const then = new Date(isoDate);
    return Math.floor((virtualNow.getTime() - then.getTime()) / 86_400_000);
  };

  /** Relative time against the virtual clock, e.g. "3d ago", "in 2d". */
  const timeAgo = (isoDate: string | null | undefined): string => {
    if (!isoDate || !virtualNow) return "—";
    const diffMs = virtualNow.getTime() - new Date(isoDate).getTime();
    const future = diffMs < 0;
    const abs = Math.abs(diffMs);
    const mins = Math.floor(abs / 60_000);
    const hours = Math.floor(abs / 3_600_000);
    const days = Math.floor(abs / 86_400_000);

    let label: string;
    if (days > 0) label = `${days}d`;
    else if (hours > 0) label = `${hours}h`;
    else if (mins > 0) label = `${mins}m`;
    else label = "just now";

    if (label === "just now") return label;
    return future ? `in ${label}` : `${label} ago`;
  };

  /** Days overdue relative to the virtual clock, never the real one. */
  const daysOverdue = (dueDate: string | null | undefined): number | null => {
    const d = daysSince(dueDate);
    return d === null ? null : Math.max(0, d);
  };

  return {
    virtualDate: virtualNow,
    virtualDateIso: iso,
    isLoading: isLoading && !iso,
    error,
    daysSince,
    daysOverdue,
    timeAgo,
    /** Formatted for display, e.g. "5 Oct 2026". */
    formatted: virtualNow
      ? virtualNow.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
      : null,
  };
}
