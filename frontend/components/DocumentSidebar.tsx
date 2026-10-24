"use client";

import { useState } from "react";
import { FileText, FileType, Search, Upload } from "lucide-react";
import type { DocumentSummary, SearchHit } from "@/lib/mockData";

type DocumentSidebarProps = {
  documents: DocumentSummary[];
  activeId: string;
  searchHits: SearchHit[];
};

// Left column: search across contracts, the contract list, and upload.
export default function DocumentSidebar({ documents, activeId, searchHits }: DocumentSidebarProps) {
  const [query, setQuery] = useState("");
  const isSearching = query.trim().length > 0;

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-line bg-surface">
      <div className="p-4 pb-3">
        <div className="flex items-center gap-2 rounded-lg border border-line bg-white px-3 py-2 focus-within:border-terracotta">
          <Search size={15} className="text-ink-faint" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search all contracts"
            className="w-full bg-transparent text-sm outline-none placeholder:text-ink-faint"
          />
        </div>
      </div>

      <div className="thin-scroll flex-1 overflow-y-auto px-2">
        {isSearching ? (
          <SearchResults hits={searchHits} />
        ) : (
          <DocumentList documents={documents} activeId={activeId} />
        )}
      </div>

      <div className="p-4">
        <label className="flex cursor-pointer flex-col items-center gap-1 rounded-xl border border-dashed border-[#d6cbbd] bg-canvas/50 px-4 py-4 text-center hover:border-terracotta hover:bg-clay/40">
          <Upload size={18} className="text-rust" />
          <span className="text-sm font-medium">Upload a contract</span>
          <span className="text-xs text-ink-faint">.docx, .md, or .txt · up to 20MB</span>
          <input type="file" accept=".docx,.md,.txt" className="hidden" />
        </label>
      </div>
    </aside>
  );
}

function DocumentList({ documents, activeId }: { documents: DocumentSummary[]; activeId: string }) {
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
                className={`flex w-full items-start gap-3 rounded-lg px-2.5 py-2.5 text-left transition-colors ${
                  isActive ? "bg-clay" : "hover:bg-subtle"
                }`}
              >
                <Icon size={17} className={`mt-0.5 shrink-0 ${isActive ? "text-rust" : "text-ink-faint"}`} />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium">{doc.title}</span>
                  <span className="block truncate text-xs text-ink-muted">
                    {doc.counterparty} · v{doc.version} · {doc.updated_at}
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

function SearchResults({ hits }: { hits: SearchHit[] }) {
  return (
    <>
      <p className="px-2 pb-1.5 pt-1 text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
        {hits.length} matches
      </p>
      <ul className="flex flex-col gap-1">
        {hits.map((hit, index) => (
          <li key={index}>
            <button className="w-full rounded-lg px-2.5 py-2 text-left hover:bg-subtle">
              <span className="block text-xs font-medium text-ink-muted">
                {hit.document_title} · line {hit.line}
              </span>
              <span className="mt-0.5 block font-serif text-[13px] leading-snug">
                {hit.snippet.slice(0, hit.match_start)}
                <mark className="rounded bg-clay px-0.5 font-semibold text-rust">
                  {hit.snippet.slice(hit.match_start, hit.match_end)}
                </mark>
                {hit.snippet.slice(hit.match_end)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
