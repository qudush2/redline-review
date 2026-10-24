"use client";

import { useState } from "react";
import { ArrowUp, CheckCheck, PencilLine, Replace, Sparkles } from "lucide-react";
import ChangeCard from "./ChangeCard";
import type { HistoryEntry, PendingChange } from "@/lib/mockData";

type ChangesPanelProps = {
  pendingChanges: PendingChange[];
  history: HistoryEntry[];
};

// Right column: pending redlines to accept/reject, version history, and the AI box.
export default function ChangesPanel({ pendingChanges, history }: ChangesPanelProps) {
  const [tab, setTab] = useState<"pending" | "history">("pending");

  return (
    <aside className="flex w-[380px] shrink-0 flex-col border-l border-line bg-surface">
      <div className="flex shrink-0 gap-1 border-b border-line px-4 pt-3">
        <PanelTab active={tab === "pending"} onClick={() => setTab("pending")}>
          Pending
          <span className="rounded-full bg-clay px-1.5 text-[11px] font-semibold text-rust">
            {pendingChanges.length}
          </span>
        </PanelTab>
        <PanelTab active={tab === "history"} onClick={() => setTab("history")}>
          History
        </PanelTab>
      </div>

      <div className="thin-scroll flex-1 overflow-y-auto p-4">
        {tab === "pending" ? (
          <PendingList changes={pendingChanges} />
        ) : (
          <HistoryList entries={history} />
        )}
      </div>

      <AskAiBox />
    </aside>
  );
}

function PendingList({ changes }: { changes: PendingChange[] }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2">
        <button className="flex items-center justify-center gap-1.5 rounded-lg border border-line bg-white py-2 text-[13px] font-medium hover:bg-subtle">
          <PencilLine size={14} /> Suggest edit
        </button>
        <button className="flex items-center justify-center gap-1.5 rounded-lg border border-line bg-white py-2 text-[13px] font-medium hover:bg-subtle">
          <Replace size={14} /> Rename term
        </button>
      </div>

      {changes.length === 0 ? (
        <p className="px-4 py-10 text-center text-sm text-ink-muted">
          No pending changes. Select text in the document or ask AI for suggestions.
        </p>
      ) : (
        <>
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-ink-muted">Review each change before it&apos;s saved.</span>
            <button className="flex items-center gap-1 text-xs font-semibold text-rust hover:text-rust-dark">
              <CheckCheck size={14} /> Accept all
            </button>
          </div>
          {changes.map((change) => (
            <ChangeCard key={change.id} change={change} />
          ))}
        </>
      )}
    </div>
  );
}

function HistoryList({ entries }: { entries: HistoryEntry[] }) {
  return (
    <ol className="relative ml-2 border-l border-line">
      {entries.map((entry) => (
        <li key={entry.version} className="mb-6 ml-5">
          <span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-terracotta" />
          <p className="text-sm">
            <span className="font-semibold">v{entry.version}</span>
            <span className="text-ink-muted"> · {entry.author} · {entry.timestamp}</span>
          </p>
          <p className="mt-1 text-[13px] leading-snug text-ink-muted">{entry.summary}</p>
          {entry.source === "ai" ? (
            <span className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-sky px-2 py-0.5 text-[11px] font-semibold text-sky-ink">
              <Sparkles size={11} /> AI suggestion
            </span>
          ) : null}
        </li>
      ))}
    </ol>
  );
}

const promptChips = ["Apply our playbook", "Tighten liability", "Check governing law"];

function AskAiBox() {
  const [instruction, setInstruction] = useState("");

  return (
    <div className="shrink-0 border-t border-line p-4">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-sky-ink">
        <Sparkles size={13} /> Ask AI for suggested edits
      </div>
      <div className="flex flex-wrap gap-1.5 pb-2.5">
        {promptChips.map((chip) => (
          <button
            key={chip}
            onClick={() => setInstruction(chip)}
            className="rounded-full border border-line bg-white px-2.5 py-1 text-xs text-ink-muted hover:border-sky-ink hover:text-sky-ink"
          >
            {chip}
          </button>
        ))}
      </div>
      <div className="flex items-end gap-2 rounded-xl border border-line bg-white p-2 focus-within:border-sky-ink">
        <textarea
          value={instruction}
          onChange={(event) => setInstruction(event.target.value)}
          rows={2}
          placeholder="Bring this in line with our playbook…"
          className="flex-1 resize-none bg-transparent px-1 text-sm outline-none placeholder:text-ink-faint"
        />
        <button
          title="Ask AI"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rust text-white hover:bg-rust-dark"
        >
          <ArrowUp size={16} />
        </button>
      </div>
      <p className="mt-1.5 text-[11px] text-ink-faint">
        AI only suggests. Nothing changes until you accept it.
      </p>
    </div>
  );
}

function PanelTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 border-b-2 px-2 pb-2.5 text-sm font-medium ${
        active ? "border-rust text-ink" : "border-transparent text-ink-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
