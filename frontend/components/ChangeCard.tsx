import { Check, Sparkles, User, X } from "lucide-react";
import type { PendingChange } from "@/lib/mockData";

// One proposed edit: where it is, before → after, who proposed it and why.
export default function ChangeCard({ change }: { change: PendingChange }) {
  const isAi = change.source === "ai";

  return (
    <div className="rounded-xl border border-line bg-white p-3.5 shadow-[0_1px_2px_rgba(61,51,41,0.04)]">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-ink-muted">{change.section}</span>
        <SourceBadge isAi={isAi} />
      </div>

      <div className="mt-2.5 space-y-1.5 font-serif text-[13.5px] leading-snug">
        <p className="rounded-md bg-del-bg px-2 py-1 text-del line-through decoration-1">
          {change.find}
        </p>
        <p className="rounded-md bg-ins-bg px-2 py-1 text-ins">{change.replace}</p>
      </div>

      <p className="mt-2.5 text-xs leading-relaxed text-ink-muted">{change.reason}</p>

      <div className="mt-3 flex items-center justify-between">
        <span className="text-[11px] text-ink-faint">
          {change.author} · {change.created_at}
        </span>
        <div className="flex gap-1.5">
          <button className="flex items-center gap-1 rounded-md border border-line px-2.5 py-1 text-xs font-medium hover:bg-subtle">
            <X size={13} /> Reject
          </button>
          <button className="flex items-center gap-1 rounded-md bg-rust px-2.5 py-1 text-xs font-medium text-white hover:bg-rust-dark">
            <Check size={13} /> Accept
          </button>
        </div>
      </div>
    </div>
  );
}

function SourceBadge({ isAi }: { isAi: boolean }) {
  if (isAi) {
    return (
      <span className="flex items-center gap-1 rounded-full bg-sky px-2 py-0.5 text-[11px] font-semibold text-sky-ink">
        <Sparkles size={11} /> AI
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 rounded-full bg-clay px-2 py-0.5 text-[11px] font-semibold text-rust">
      <User size={11} /> You
    </span>
  );
}
