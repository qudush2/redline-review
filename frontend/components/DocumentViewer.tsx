"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { Eye, EyeOff, Minus, PencilLine, Plus } from "lucide-react";
import { clearHighlight, highlightMatch } from "@/lib/highlight";

// "Highlight the 2nd match of 'liability'". `key` changes on every click, so
// clicking the same search result twice still scrolls to it again.
export type HighlightRequest = { query: string; occurrence: number; key: number };

type DocumentViewerProps = {
  documentKey: string; // changes when a different document or version is shown
  markdown: string; // the redline (or plain text when nothing is pending)
  cleanMarkdown: string; // the text as it reads with every pending change accepted
  redlineUnavailable: boolean; // true for very large documents
  highlight: HighlightRequest | null; // a search hit to scroll to and highlight
  onSuggestEdit: (selectedText: string) => void;
};

const ZOOM_STEPS = [80, 90, 100, 110, 125];

// Center column: the contract rendered on "paper", with redlines inline.
// rehype-raw lets our <del>/<ins> tags through; rehype-sanitize strips anything unsafe.
export default function DocumentViewer(props: DocumentViewerProps) {
  const [showRedline, setShowRedline] = useState(true);
  const [zoomIndex, setZoomIndex] = useState(2); // 100%
  const [popup, setPopup] = useState<{ text: string; top: number; left: number } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const articleRef = useRef<HTMLElement>(null);

  useEffect(() => setPopup(null), [props.documentKey]);

  // Once the document is on screen, scroll to the search hit and highlight it.
  useEffect(() => {
    if (!props.highlight || !articleRef.current) {
      clearHighlight();
      return;
    }
    highlightMatch(articleRef.current, props.highlight.query, props.highlight.occurrence);
  }, [props.highlight, props.documentKey]);

  useEffect(() => clearHighlight, []);

  // After the user selects text in the contract, show a small "Suggest edit" button above it.
  function handleMouseUp() {
    const selection = window.getSelection();
    const text = selection?.toString().replace(/\s+/g, " ").trim() ?? "";
    if (!selection || !text || !scrollRef.current) {
      setPopup(null);
      return;
    }

    // Position relative to the scrolling area, so the button stays next to the text while scrolling.
    const selectionBox = selection.getRangeAt(0).getBoundingClientRect();
    const areaBox = scrollRef.current.getBoundingClientRect();
    setPopup({
      text,
      top: selectionBox.top - areaBox.top + scrollRef.current.scrollTop - 42,
      left: selectionBox.left - areaBox.left + selectionBox.width / 2,
    });
  }

  const zoom = ZOOM_STEPS[zoomIndex];

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
          <span className="text-xs text-ink-faint">Select text to suggest an edit</span>
          <div className="flex items-center gap-2">
            <button title="Zoom out" disabled={zoomIndex === 0} onClick={() => setZoomIndex(zoomIndex - 1)} className="hover:text-ink disabled:opacity-40">
              <Minus size={14} />
            </button>
            <span className="w-10 text-center">{zoom}%</span>
            <button title="Zoom in" disabled={zoomIndex === ZOOM_STEPS.length - 1} onClick={() => setZoomIndex(zoomIndex + 1)} className="hover:text-ink disabled:opacity-40">
              <Plus size={14} />
            </button>
          </div>
        </div>
      </div>

      <div ref={scrollRef} onMouseUp={handleMouseUp} className="thin-scroll relative flex-1 overflow-y-auto px-8 py-8">
        {props.redlineUnavailable && showRedline ? (
          <p className="mx-auto mb-4 max-w-[816px] rounded-lg bg-clay px-4 py-2 text-[13px] text-rust">
            This document is too large to show changes inline. Review each change in the panel on the right.
          </p>
        ) : null}

        <article
          ref={articleRef}
          style={{ zoom: zoom / 100 }}
          className="paper mx-auto max-w-[816px] rounded-sm bg-white px-20 py-16 shadow-[0_1px_3px_rgba(61,51,41,0.08),0_8px_24px_rgba(61,51,41,0.06)]"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
            {showRedline ? props.markdown : props.cleanMarkdown}
          </ReactMarkdown>
        </article>

        {popup ? (
          <button
            // preventDefault on mousedown keeps the text selected while clicking.
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => {
              props.onSuggestEdit(popup.text);
              setPopup(null);
            }}
            style={{ top: popup.top, left: popup.left }}
            className="absolute z-10 flex -translate-x-1/2 items-center gap-1.5 rounded-lg bg-espresso px-3 py-1.5 text-xs font-medium text-white shadow-lg hover:bg-black"
          >
            <PencilLine size={13} /> Suggest edit
          </button>
        ) : null}
      </div>
    </section>
  );
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
