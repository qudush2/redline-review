"use client";

import { useState } from "react";
import { FileText, FileType, LoaderCircle, Search, Upload, X } from "lucide-react";
import type { DocumentSummary, SearchResponse, SearchResult } from "@/lib/api";
import { fileTypeLabel, splitSnippet, timeAgo } from "@/lib/format";

type DocumentSidebarProps = {
  documents: DocumentSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  searchResponse: SearchResponse | null;
  onOpenResult: (result: SearchResult) => void;
  onUpload: (file: File) => void;
  uploading: boolean;
};

// Left column: search across contracts, the contract list, and upload.
export default function DocumentSidebar(props: DocumentSidebarProps) {
  const isSearching = props.searchQuery.trim().length > 0;

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-line bg-surface">
      <div className="p-4 pb-3">
        <div className="flex items-center gap-2 rounded-lg border border-line bg-white px-3 py-2 focus-within:border-terracotta">
          <Search size={15} className="text-ink-faint" />
          <input
            value={props.searchQuery}
            onChange={(event) => props.onSearchChange(event.target.value)}
            placeholder="Search all contracts"
            className="w-full bg-transparent text-sm outline-none placeholder:text-ink-faint"
          />
          {isSearching ? (
            <button title="Clear search" onClick={() => props.onSearchChange("")} className="text-ink-faint hover:text-ink">
              <X size={14} />
            </button>
          ) : null}
        </div>
      </div>

      <div className="thin-scroll flex-1 overflow-y-auto px-2">
        {isSearching ? (
          <SearchResults response={props.searchResponse} onOpen={props.onOpenResult} />
        ) : (
          <DocumentList documents={props.documents} activeId={props.activeId} onSelect={props.onSelect} />
        )}
      </div>

      <UploadZone onUpload={props.onUpload} uploading={props.uploading} />
    </aside>
  );
}

function DocumentList({
  documents,
  activeId,
  onSelect,
}: {
  documents: DocumentSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <>
      <p className="px-2 pb-1.5 pt-1 text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
        Contracts · {documents.length}
      </p>
      <ul className="flex flex-col gap-0.5">
        {documents.map((doc) => {
          const isActive = doc.id === activeId;
          const Icon = doc.file_type === "docx" ? FileType : FileText;
          return (
            <li key={doc.id}>
              <button
                onClick={() => onSelect(doc.id)}
                className={`flex w-full items-start gap-3 rounded-lg px-2.5 py-2.5 text-left transition-colors ${
                  isActive ? "bg-clay" : "hover:bg-subtle"
                }`}
              >
                <Icon size={17} className={`mt-0.5 shrink-0 ${isActive ? "text-rust" : "text-ink-faint"}`} />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium">{doc.title}</span>
                  <span className="block truncate text-xs text-ink-muted">
                    v{doc.version} · {fileTypeLabel(doc.file_type)} · {timeAgo(doc.updated_at)}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </>
  );
}

function SearchResults({
  response,
  onOpen,
}: {
  response: SearchResponse | null;
  onOpen: (result: SearchResult) => void;
}) {
  if (!response) {
    return <p className="px-2 pt-2 text-xs text-ink-faint">Searching…</p>;
  }
  if (response.total === 0) {
    return <p className="px-2 pt-2 text-sm text-ink-muted">No matches for “{response.query}”.</p>;
  }

  return (
    <>
      <p className="px-2 pb-1.5 pt-1 text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
        {response.total} {response.total === 1 ? "match" : "matches"}
        {response.total > response.results.length ? ` · showing ${response.results.length}` : ""}
      </p>
      <ul className="flex flex-col gap-1">
        {response.results.map((hit) => {
          // The API tells us where the match is inside the snippet, so we can bold it safely.
          const [before, match, after] = splitSnippet(hit.snippet, hit.match_start, hit.match_end);
          return (
            <li key={`${hit.document_id}-${hit.position}`}>
              <button onClick={() => onOpen(hit)} className="w-full rounded-lg px-2.5 py-2 text-left hover:bg-subtle">
                <span className="block truncate text-xs font-medium text-ink-muted">
                  {hit.document_title} · line {hit.line}
                </span>
                <span className="mt-0.5 block font-serif text-[13px] leading-snug">
                  {before}
                  <mark className="rounded bg-clay px-0.5 font-semibold text-rust">{match}</mark>
                  {after}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </>
  );
}

// Click to choose a file, or drag one onto the box.
function UploadZone({ onUpload, uploading }: { onUpload: (file: File) => void; uploading: boolean }) {
  const [dragging, setDragging] = useState(false);

  function handleDrop(event: React.DragEvent) {
    event.preventDefault(); // stop the browser from opening the file itself
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) onUpload(file);
  }

  return (
    <div className="p-4">
      <label
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center gap-1 rounded-xl border border-dashed px-4 py-4 text-center transition-colors ${
          dragging ? "border-terracotta bg-clay/60" : "border-[#d6cbbd] bg-canvas/50 hover:border-terracotta hover:bg-clay/40"
        }`}
      >
        {uploading ? (
          <LoaderCircle size={18} className="animate-spin text-rust" />
        ) : (
          <Upload size={18} className="text-rust" />
        )}
        <span className="text-sm font-medium">{uploading ? "Uploading…" : "Upload a contract"}</span>
        <span className="text-xs text-ink-faint">.docx, .md, or .txt · up to 10MB</span>
        <input
          type="file"
          accept=".docx,.md,.txt"
          className="hidden"
          disabled={uploading}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onUpload(file);
            event.target.value = ""; // allow picking the same file again
          }}
        />
      </label>
    </div>
  );
}
