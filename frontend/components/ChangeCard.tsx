import { CircleAlert, Check, Sparkles, User, X } from "lucide-react";
import { occurrenceLabel, timeAgo } from "@/lib/format";
import type { PendingChangeView } from "@/lib/pending";

type ChangeCardProps = {
  view: PendingChangeView;
  busy: boolean;
  onAccept: () => void;
  onReject: () => void;
};

// One proposed edit: before → after, which match, who proposed it and why.
export default function ChangeCard({ view, busy, onAccept, onReject }: ChangeCardProps) {
  const { change, count, error } = view;
  const { request } = change;
  const isAi = request.source === "ai";

  return (
    <div
      className={`rounded-xl border bg-white p-3.5 shadow-[0_1px_2px_rgba(61,51,41,0.04)] ${
        error ? "border-del/40" : "border-line"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-ink-muted">{occurrenceLabel(request.target.occurrence, count)}</span>
        <SourceBadge isAi={isAi} />
      </div>

      <div className="mt-2.5 space-y-1.5 font-serif text-[13.5px] leading-snug">
        <p className="rounded-md bg-del-bg px-2 py-1 text-del line-through decoration-1">{request.target.text}</p>
        {request.replacement ? (
          <p className="rounded-md bg-ins-bg px-2 py-1 text-ins">{request.replacement}</p>
        ) : (
          <p className="px-2 font-sans text-xs italic text-ink-muted">Delete this text</p>
        )}
      </div>

      {request.reason ? <p className="mt-2.5 text-xs leading-relaxed text-ink-muted">{request.reason}</p> : null}

      {error ? (
        <p className="mt-2.5 flex items-start gap-1.5 rounded-md bg-del-bg px-2 py-1.5 text-xs text-del">
          <CircleAlert size={13} className="mt-px shrink-0" /> {error}
        </p>
      ) : null}

      <div className="mt-3 flex items-center justify-between">
        <span className="text-[11px] text-ink-faint">
          {change.author} · {timeAgo(change.createdAt)}
        </span>
        <div className="flex gap-1.5">
          <button
            onClick={onReject}
            disabled={busy}
            className="flex items-center gap-1 rounded-md border border-line px-2.5 py-1 text-xs font-medium hover:bg-subtle disabled:opacity-50"
          >
            <X size={13} /> Reject
          </button>
          <button
            onClick={onAccept}
            disabled={busy || Boolean(error)}
            title={error ? "This change no longer applies" : undefined}
            className="flex items-center gap-1 rounded-md bg-rust px-2.5 py-1 text-xs font-medium text-white hover:bg-rust-dark disabled:opacity-40"
          >
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
