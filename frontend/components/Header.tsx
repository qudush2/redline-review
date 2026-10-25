"use client";

import { useState } from "react";
import { Clock, Download, FileText, Send, UserPen } from "lucide-react";
import { toast } from "sonner";
import type { DocumentFull } from "@/lib/api";
import { fileTypeLabel, timeAgo } from "@/lib/format";

const tabs = ["Document", "Details", "Activity", "Approvals"];

type HeaderProps = {
  document: DocumentFull;
  pendingCount: number;
  editorName: string;
  onEditorNameChange: (name: string) => void;
};

// Document header: title, version, who is editing, and page tabs.
// Only the "Document" tab is built; the others (and Export/Send) are placeholders.
export default function Header({ document, pendingCount, editorName, onEditorNameChange }: HeaderProps) {
  const [activeTab, setActiveTab] = useState("Document");

  return (
    <div className="shrink-0 border-b border-line bg-surface px-6 pt-5">
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="truncate font-serif text-[26px] font-normal leading-tight tracking-tight">
              {document.title}
            </h1>
            <span className="rounded-md border border-line bg-white px-2 py-0.5 text-xs font-semibold text-ink-muted">
              v{document.version}
            </span>
            <span className="rounded-full bg-clay px-2.5 py-0.5 text-xs font-medium text-rust">
              {pendingCount > 0 ? "In review" : "Draft"}
            </span>
          </div>

          <div className="mt-2 flex items-center gap-5 text-[13px] text-ink-muted">
            <span className="flex items-center gap-1.5">
              <FileText size={14} /> {fileTypeLabel(document.file_type)}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock size={14} /> Updated {timeAgo(document.updated_at)}
            </span>
            <label className="flex items-center gap-1.5" title="Recorded as the author of changes you accept">
              <UserPen size={14} /> Editing as
              <input
                value={editorName}
                onChange={(event) => onEditorNameChange(event.target.value)}
                className="w-24 rounded border border-transparent bg-transparent px-1 font-medium text-ink outline-none hover:border-line focus:border-terracotta focus:bg-white"
              />
            </label>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="mr-2 text-[13px] text-ink-muted">
            <span className="font-semibold text-rust">{pendingCount}</span> pending{" "}
            {pendingCount === 1 ? "change" : "changes"}
          </span>
          <button
            onClick={() => toast.info("Export to Word with tracked changes is next on the roadmap.")}
            className="flex items-center gap-1.5 rounded-lg border border-line bg-white px-3 py-1.5 text-sm font-medium hover:bg-subtle"
          >
            <Download size={15} /> Export .docx
          </button>
          <button
            onClick={() => toast.info("Sending to the counterparty isn't part of this demo.")}
            className="flex items-center gap-1.5 rounded-lg bg-rust px-3 py-1.5 text-sm font-medium text-white hover:bg-rust-dark"
          >
            <Send size={15} /> Send to counterparty
          </button>
        </div>
      </div>

      <div className="mt-4 flex gap-6 text-sm">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`border-b-2 pb-2.5 font-medium transition-colors ${
              tab === activeTab ? "border-rust text-ink" : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>
    </div>
  );
}
