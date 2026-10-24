"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { Eye, EyeOff, Minus, Plus, ScanSearch } from "lucide-react";

type DocumentViewerProps = {
  markdown: string;
};

// Center column: the contract rendered on "paper", with redlines inline.
// rehype-raw lets our <del>/<ins> tags through; rehype-sanitize strips anything unsafe.
export default function DocumentViewer({ markdown }: DocumentViewerProps) {
  const [showRedline, setShowRedline] = useState(true);

  return (
    <section className="flex min-w-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-line bg-canvas px-5 py-2 text-[13px] text-ink-muted">
        <div className="flex items-center gap-1 rounded-lg border border-line bg-surface p-0.5">
          <ToolbarToggle active={showRedline} onClick={() => setShowRedline(true)}>
            <Eye size={14} /> Redline
          </ToolbarToggle>
          <ToolbarToggle active={!showRedline} onClick={() => setShowRedline(false)}>
            <EyeOff size={14} /> Clean
          </ToolbarToggle>
        </div>

        <div className="flex items-center gap-4">
          <button className="flex items-center gap-1.5 hover:text-ink">
            <ScanSearch size={14} /> Find in document
          </button>
          <div className="flex items-center gap-2">
            <button title="Zoom out" className="hover:text-ink"><Minus size={14} /></button>
            <span className="w-10 text-center">100%</span>
            <button title="Zoom in" className="hover:text-ink"><Plus size={14} /></button>
          </div>
        </div>
      </div>

      <div className="thin-scroll flex-1 overflow-y-auto px-8 py-8">
        <article className="paper mx-auto max-w-[816px] rounded-sm bg-white px-20 py-16 shadow-[0_1px_3px_rgba(61,51,41,0.08),0_8px_24px_rgba(61,51,41,0.06)]">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
            {showRedline ? markdown : cleanVersion(markdown)}
          </ReactMarkdown>
        </article>
      </div>
    </section>
  );
}

// "Clean" view: what the contract reads like if every pending change is accepted.
// Temporary; Phase 3 uses text_after from the preview endpoint instead.
function cleanVersion(markdown: string): string {
  return markdown.replace(/<del>.*?<\/del>/g, "").replace(/<\/?ins>/g, "");
}

function ToolbarToggle({
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
      className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-colors ${
        active ? "bg-white text-ink shadow-sm" : "hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
