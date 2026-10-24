"use client";

import { useEffect, useState } from "react";
import { Bell, ChevronRight, Search } from "lucide-react";

type ApiStatus = "checking" | "connected" | "offline";

// Global top bar: breadcrumb, workspace search, API status, and the user.
export default function TopBar({ documentTitle }: { documentTitle: string }) {
  const apiStatus = useApiStatus();

  return (
    <header className="flex h-14 shrink-0 items-center gap-6 border-b border-line bg-surface px-5">
      <div className="flex min-w-0 items-center gap-1.5 text-sm">
        <span className="text-ink-muted">Contracts</span>
        <ChevronRight size={14} className="text-ink-faint" />
        <span className="truncate font-medium">{documentTitle}</span>
      </div>

      <div className="mx-auto flex w-full max-w-md items-center gap-2 rounded-lg border border-line bg-white px-3 py-1.5 text-sm text-ink-faint">
        <Search size={15} />
        <span className="flex-1">Search contracts, clauses, parties…</span>
        <kbd className="rounded border border-line px-1.5 text-[11px]">⌘K</kbd>
      </div>

      <div className="flex items-center gap-4">
        <ApiStatusPill status={apiStatus} />
        <button title="Notifications" className="relative text-ink-muted hover:text-ink">
          <Bell size={18} />
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-terracotta" />
        </button>
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-rust text-xs font-semibold text-white">
          QS
        </div>
      </div>
    </header>
  );
}

// Pings the backend once on load, so it's obvious when the API isn't running.
function useApiStatus(): ApiStatus {
  const [status, setStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => setStatus(response.ok ? "connected" : "offline"))
      .catch(() => setStatus("offline"));
  }, []);

  return status;
}

function ApiStatusPill({ status }: { status: ApiStatus }) {
  const styles = {
    checking: { dot: "bg-ink-faint", label: "Connecting…" },
    connected: { dot: "bg-ins", label: "API connected" },
    offline: { dot: "bg-del", label: "API offline" },
  }[status];

  return (
    <span className="flex items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-xs text-ink-muted">
      <span className={`h-1.5 w-1.5 rounded-full ${styles.dot}`} />
      {styles.label}
    </span>
  );
}
