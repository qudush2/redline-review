"use client";

import { useState } from "react";
import { ArrowUp, CheckCheck, PencilLine, Replace, Sparkles } from "lucide-react";
import ChangeCard from "./ChangeCard";
import ComingSoon from "./ComingSoon";
import type { HistoryEntry } from "@/lib/api";
import { occurrenceLabel, timeAgo } from "@/lib/format";
import type { PendingChangeView } from "@/lib/pending";

type ChangesPanelProps = {
  changes: PendingChangeView[];
  history: HistoryEntry[];
  busy: boolean;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onAcceptAll: () => void;
  onSuggestEdit: () => void;
  onRenameTerm: () => void;
  onAskAi: (instruction: string) => void;
};

// Right column: pending redlines to accept/reject, version history, and the AI box.
export default function ChangesPanel(props: ChangesPanelProps) {
  const [tab, setTab] = useState<"pending" | "history">("pending");

  return (
    <aside className="flex w-[380px] shrink-0 flex-col border-l border-line bg-surface">
      <div className="flex shrink-0 gap-1 border-b border-line px-4 pt-3">
        <PanelTab active={tab === "pending"} onClick={() => setTab("pending")}>
          Pending
          <span className="rounded-full bg-clay px-1.5 text-[11px] font-semibold text-rust">{props.changes.length}</span>
        </PanelTab>
        <PanelTab active={tab === "history"} onClick={() => setTab("history")}>
          History
          <span className="rounded-full bg-subtle px-1.5 text-[11px] font-semibold text-ink-muted">{props.history.length}</span>
        </PanelTab>
      </div>

      <div className="thin-scroll flex-1 overflow-y-auto p-4">
        {tab === "pending" ? <PendingList {...props} /> : <HistoryList entries={props.history} />}
      </div>

      {/* Grayed out until AI suggestions are wired up (Phase 4). */}
      <ComingSoon side="top" label="AI suggestions are being added next" className="w-full">
        <AskAiBox onAskAi={props.onAskAi} />
      </ComingSoon>
    </aside>
  );
}

function PendingList({ changes, busy, onAccept, onReject, onAcceptAll, onSuggestEdit, onRenameTerm }: ChangesPanelProps) {
  const acceptableCount = changes.filter((view) => !view.error).length;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={onSuggestEdit}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-line bg-white py-2 text-[13px] font-medium hover:bg-subtle"
        >
          <PencilLine size={14} /> Suggest edit
        </button>
        <button
          onClick={onRenameTerm}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-line bg-white py-2 text-[13px] font-medium hover:bg-subtle"
        >
          <Replace size={14} /> Rename term
        </button>
      </div>

      {changes.length === 0 ? (
        <TryItGuide />
      ) : (
        <>
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-ink-muted">Review each change before it&apos;s saved.</span>
            <button
              onClick={onAcceptAll}
              disabled={busy || acceptableCount === 0}
              className="flex items-center gap-1 text-xs font-semibold text-rust hover:text-rust-dark disabled:opacity-40"
            >
              <CheckCheck size={14} /> Accept all
            </button>
          </div>
          {changes.map((view) => (
            <ChangeCard
              key={view.change.id}
              view={view}
              busy={busy}
              onAccept={() => onAccept(view.change.id)}
              onReject={() => onReject(view.change.id)}
            />
          ))}
        </>
      )}
    </div>
  );
}

// Shown when nothing is pending: a short list of things to try in the prototype.
const tryItSteps = [
  { title: "Search", detail: "Type “liability” in the search box on the left, then click a result." },
  { title: "Suggest an edit", detail: "Select text in the contract (try “thirty (30) days” in §9.2), then click Suggest edit." },
  { title: "Rename a term", detail: "Click Rename term above and change “Licensee” to “Customer”." },
  { title: "Accept or reject", detail: "Review the redline, accept a change, then open the History tab." },
];

function TryItGuide() {
  return (
    <div className="rounded-xl border border-dashed border-line px-4 py-4">
      <p className="text-sm font-medium">No pending changes yet. Try this:</p>
      <ol className="mt-3 flex flex-col gap-3">
        {tryItSteps.map((step, index) => (
          <li key={step.title} className="flex gap-2.5">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-clay text-[11px] font-semibold text-rust">
              {index + 1}
            </span>
            <span className="text-[13px] leading-snug">
              <span className="font-medium">{step.title}.</span> <span className="text-ink-muted">{step.detail}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

// Versions newest first. Each version lists its changes, marking AI suggestions.
function HistoryList({ entries }: { entries: HistoryEntry[] }) {
  return (
    <ol className="relative ml-2 border-l border-line">
      {entries.map((entry) => (
        <li key={entry.version} className="mb-6 ml-5">
          <span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-terracotta" />
          <p className="text-sm">
            <span className="font-semibold">v{entry.version}</span>
            <span className="text-ink-muted">
              {" "}
              · {entry.author} · {timeAgo(entry.timestamp)}
            </span>
          </p>

          {entry.changes.length === 0 ? (
            <p className="mt-1 text-[13px] text-ink-muted">Original document</p>
          ) : (
            <ul className="mt-1.5 flex flex-col gap-2">
              {entry.changes.map((change, index) => (
                <li key={index} className="text-[13px] leading-snug">
                  <span className="text-del line-through">{change.find}</span>
                  {" → "}
                  <span className="text-ins">{change.replace || "(deleted)"}</span>
                  <span className="text-ink-faint"> · {occurrenceLabel(change.occurrence, change.count)}</span>
                  {change.reason ? <p className="mt-0.5 text-xs text-ink-muted">{change.reason}</p> : null}
                  {change.source === "ai" ? (
                    <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-sky px-2 py-0.5 text-[11px] font-semibold text-sky-ink">
                      <Sparkles size={11} /> AI suggestion, accepted by {entry.author}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ol>
  );
}

const promptChips = ["Apply our playbook", "Tighten liability", "Check governing law"];

function AskAiBox({ onAskAi }: { onAskAi: (instruction: string) => void }) {
  const [instruction, setInstruction] = useState("");

  return (
    <div className="w-full shrink-0 border-t border-line p-4">
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
          onClick={() => onAskAi(instruction)}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rust text-white hover:bg-rust-dark"
        >
          <ArrowUp size={16} />
        </button>
      </div>
      <p className="mt-1.5 text-[11px] text-ink-faint">AI only suggests. Nothing changes until you accept it.</p>
    </div>
  );
}

function PanelTab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
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
