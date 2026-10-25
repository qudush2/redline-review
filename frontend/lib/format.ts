// Small display helpers.

import type { FileType, Occurrence } from "./api";

// "2026-10-25T14:00:00Z" -> "just now", "5 min ago", "3h ago", "Yesterday", "Oct 19"
export function timeAgo(isoTimestamp: string): string {
  const seconds = (Date.now() - new Date(isoTimestamp).getTime()) / 1000;
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 2 * 86400) return "Yesterday";
  return new Date(isoTimestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// "docx" -> "Word"
export function fileTypeLabel(fileType: FileType): string {
  return { md: "Markdown", txt: "Text", docx: "Word" }[fileType] ?? fileType;
}

// Hide Markdown symbols in short text previews (search results, match lists).
// Example: '(**"Provider"**), and ## 8. Limits' -> '("Provider"), and 8. Limits'
export function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*|__|`/g, "") // bold and code markers
    .replace(/#{1,6} /g, ""); // heading markers like "## "
}

// Split a snippet into [before, match, after] for display, with Markdown symbols hidden.
// Each part is cleaned separately, so the highlighted part still lines up.
export function splitSnippet(snippet: string, matchStart: number, matchEnd: number): [string, string, string] {
  return [
    stripMarkdown(snippet.slice(0, matchStart)),
    stripMarkdown(snippet.slice(matchStart, matchEnd)),
    stripMarkdown(snippet.slice(matchEnd)),
  ];
}

// Describe which match an edit targets.
// Examples: ("all", 24) -> "All 24 occurrences", (2, 1) -> "Occurrence 2", (null, 1) -> "1 match"
export function occurrenceLabel(occurrence: Occurrence | undefined, count?: number): string {
  if (occurrence === "all") return count === undefined ? "All occurrences" : `All ${count} occurrences`;
  if (typeof occurrence === "number") return `Occurrence ${occurrence}`;
  return "1 match";
}
