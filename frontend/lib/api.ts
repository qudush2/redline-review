// Typed helpers for every backend endpoint.
// Types mirror backend/app/models.py. Requests go to /api/*, which Next.js
// forwards to FastAPI on port 8000 (see next.config.ts).

// --- Types ---------------------------------------------------------------------

export type FileType = "md" | "txt" | "docx";

export type DocumentSummary = {
  id: string;
  title: string;
  file_type: FileType;
  version: number;
  updated_at: string;
  size_chars: number;
};

export type DocumentFull = {
  id: string;
  title: string;
  file_type: FileType;
  version: number;
  text: string;
  created_at: string;
  updated_at: string;
};

// Which match to change: 1, 2, … or "all". null means "it must appear exactly once".
export type Occurrence = number | "all" | null;

// One edit, in the same shape the API expects.
// Example: { operation: "replace", target: { text: "Licensee", occurrence: "all" }, replacement: "Customer" }
export type ChangeRequest = {
  operation: "replace";
  target: { text: string; occurrence?: Occurrence; whole_word?: boolean };
  replacement: string;
  reason?: string | null;
  source?: "human" | "ai";
};

export type AppliedChange = {
  find: string;
  replace: string;
  occurrence: Occurrence;
  count: number;
  reason: string | null;
  source: "human" | "ai";
};

export type EditResponse = { id: string; version: number; text: string; applied: AppliedChange[] };

export type PreviewResponse = {
  id: string;
  version: number;
  text_after: string;
  redline_markdown: string | null; // null when the document is too large to diff
  applied: AppliedChange[];
};

export type SearchResult = {
  document_id: string;
  document_title: string;
  position: number;
  line: number;
  occurrence_in_document: number;
  snippet: string;
  match_start: number; // where the match sits inside `snippet`
  match_end: number;
};

export type SearchResponse = { query: string; total: number; limit: number; offset: number; results: SearchResult[] };

export type HistoryEntry = { version: number; timestamp: string; author: string; changes: AppliedChange[] };

// AI suggestions that passed the guardrail, plus the ones it threw out.
export type DroppedSuggestion = { find: string; why: string };
export type SuggestionsResponse = { suggestions: ChangeRequest[]; dropped: DroppedSuggestion[]; model: string };

// One match listed in an "ambiguous_match" error, so the user can pick it.
export type AmbiguousMatch = { occurrence: number; snippet: string; match_start: number; match_end: number };

// --- Errors --------------------------------------------------------------------

// Every API error arrives as { error, code, type, details }. We turn it into this
// class so components can check e.g. `error.type === "ambiguous_match"`.
export class ApiError extends Error {
  status: number;
  type: string;
  details: Record<string, unknown>;

  constructor(message: string, status: number, type: string, details: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.type = type;
    this.details = details;
  }
}

// --- The one place that calls fetch ---------------------------------------------

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, options);
  } catch {
    throw new ApiError("Can't reach the API. Is the backend running?", 0, "network_error");
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      body?.error ?? "Something went wrong. Please try again.",
      response.status,
      body?.type ?? "server_error",
      body?.details ?? {},
    );
  }
  return body as T;
}

function sendJson<T>(method: string, path: string, data: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// --- Endpoints -----------------------------------------------------------------

export const api = {
  listDocuments: () => request<DocumentSummary[]>("/documents"),

  getDocument: (id: string) => request<DocumentFull>(`/documents/${id}`),

  getHistory: (id: string) => request<HistoryEntry[]>(`/documents/${id}/history`),

  // Save changes as a new version (all-or-nothing).
  editDocument: (id: string, changes: ChangeRequest[], expectedVersion: number, author: string) =>
    sendJson<EditResponse>("PATCH", `/documents/${id}`, { changes, expected_version: expectedVersion, author }),

  // Same as editDocument, but nothing is saved. Returns the inline redline.
  previewChanges: (id: string, changes: ChangeRequest[], expectedVersion: number) =>
    sendJson<PreviewResponse>("POST", `/documents/${id}/preview`, { changes, expected_version: expectedVersion }),

  // Ask the AI for suggested edits. Nothing is saved.
  suggestEdits: (id: string, instruction: string) =>
    sendJson<SuggestionsResponse>("POST", `/documents/${id}/suggestions`, { instruction }),

  search: (query: string, limit = 20, offset = 0) =>
    request<SearchResponse>(`/documents/search?${new URLSearchParams({ q: query, limit: String(limit), offset: String(offset) })}`),

  uploadDocument: (file: File, author: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("author", author);
    // No Content-Type header: the browser sets the multipart boundary itself.
    return request<DocumentFull>("/documents/upload", { method: "POST", body: form });
  },
};
