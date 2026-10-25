"use client";

import { Clock, Download, FileText, Send, UserPen } from "lucide-react";
import ComingSoon from "./ComingSoon";
import type { DocumentFull } from "@/lib/api";
import { fileTypeLabel, timeAgo } from "@/lib/format";

// Only "Document" is built; the other tabs are placeholders.
const placeholderTabs = ["Details", "Activity", "Approvals"];

type HeaderProps = {
  document: DocumentFull;
  pendingCount: number;
  editorName: string;
  onEditorNameChange: (name: string) => void;
};

// Document header: title, version, who is editing, and page tabs.
// Placeholders (other tabs, Export, Send) are grayed out with ComingSoon.
export default function Header({ document, pendingCount, editorName, onEditorNameChange }: HeaderProps) {
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
          <ComingSoon label="Next on the roadmap: export to Word with tracked changes">
            <span className="flex items-center gap-1.5 rounded-lg border border-line bg-white px-3 py-1.5 text-sm font-medium">
              <Download size={15} /> Export .docx
            </span>
          </ComingSoon>
          <ComingSoon>
            <span className="flex items-center gap-1.5 rounded-lg bg-rust px-3 py-1.5 text-sm font-medium text-white">
              <Send size={15} /> Send to counterparty
            </span>
          </ComingSoon>
        </div>
      </div>

      <div className="mt-4 flex gap-6 text-sm">
        <span className="border-b-2 border-rust pb-2.5 font-medium text-ink">Document</span>
        {placeholderTabs.map((tab) => (
          <ComingSoon key={tab}>
            <span className="border-b-2 border-transparent pb-2.5 font-medium text-ink-muted">{tab}</span>
          </ComingSoon>
        ))}
      </div>
    </div>
  );
}
