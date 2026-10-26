"use client";

// The single app screen. This component owns the state and talks to the API;
// the components below it only display data and report clicks back up.
//
// The redline flow:
//   1. Proposed edits sit in `pendingByDoc` (browser only, nothing saved).
//   2. Whenever they change, we call POST /preview to get the inline redline.
//   3. Accept sends PATCH with that one change; Accept all sends them all.
//   4. Reject just removes it from the list.

import { useCallback, useEffect, useState } from "react";
import { toast, Toaster } from "sonner";

import AppNav from "@/components/AppNav";
import ChangesPanel from "@/components/ChangesPanel";
import DocumentSidebar from "@/components/DocumentSidebar";
import DocumentViewer from "@/components/DocumentViewer";
import Header from "@/components/Header";
import SuggestEditForm, { type EditMode } from "@/components/SuggestEditForm";
import TopBar from "@/components/TopBar";
import {
  api,
  ApiError,
  type ChangeRequest,
  type DocumentFull,
  type DocumentSummary,
  type HistoryEntry,
  type PreviewResponse,
  type SearchResponse,
  type SearchResult,
  type SuggestionsResponse,
} from "@/lib/api";
import { makePendingChange, type PendingChange, type PendingChangeView } from "@/lib/pending";

const EDITOR_NAME_KEY = "redline.editorName";

// One shared empty list. Writing `?? []` inline would create a NEW array on every
// render, and React would think the pending list changed each time (an endless preview loop).
const NO_PENDING: PendingChange[] = [];

const CONFLICT_TOAST_ID = "version-conflict";

export default function Home() {
  // --- State ---------------------------------------------------------------------
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentsLoaded, setDocumentsLoaded] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [document, setDocument] = useState<DocumentFull | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  // Pending edits per document id, so switching documents keeps each one's list.
  const [pendingByDoc, setPendingByDoc] = useState<Record<string, PendingChange[]>>({});
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewIds, setPreviewIds] = useState<string[]>([]); // which pending ids the preview includes
  const [changeErrors, setChangeErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false); // true while accepting
  const [aiBusy, setAiBusy] = useState(false); // true while waiting for AI suggestions
  const [aiResult, setAiResult] = useState<SuggestionsResponse | null>(null); // last AI answer, for the summary note

  const [editorName, setEditorName] = useState("Qudus");
  // The edit form in the side panel. `key` changes each time it opens, so a new
  // text selection starts a fresh form instead of keeping the old one's fields.
  const [editor, setEditor] = useState<{ mode: EditMode; find: string; key: number } | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [uploading, setUploading] = useState(false);

  const pending = (activeId && pendingByDoc[activeId]) || NO_PENDING;

  // --- Error handling --------------------------------------------------------------

  const reloadDocument = useCallback(async (id: string) => {
    const [fresh, freshHistory, list] = await Promise.all([api.getDocument(id), api.getHistory(id), api.listDocuments()]);
    setDocument(fresh);
    setHistory(freshHistory);
    setDocuments(list); // keeps the version numbers in the sidebar current
    toast.dismiss(CONFLICT_TOAST_ID); // we have the latest version now
  }, []);

  // Show an API error as a toast. A 409 gets a "Reload" button.
  const showError = useCallback(
    (error: unknown) => {
      if (error instanceof ApiError && error.type === "version_conflict" && activeId) {
        toast.error(error.message, {
          action: { label: "Reload", onClick: () => reloadDocument(activeId).catch(showError) },
          duration: Infinity, // stays until clicked or closed: the user needs to act on it
          id: CONFLICT_TOAST_ID, // a second conflict replaces this toast instead of stacking
        });
        return;
      }
      toast.error(error instanceof Error ? error.message : "Something went wrong.");
    },
    [activeId, reloadDocument],
  );

  // --- Loading -------------------------------------------------------------------------

  const refreshDocumentList = useCallback(async () => {
    const list = await api.listDocuments();
    setDocuments(list);
    return list;
  }, []);

  // On first load: remember the editor's name, and fetch the document list.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(EDITOR_NAME_KEY);
      if (saved) setEditorName(saved);
    } catch {
      // Storage can be blocked (e.g. private mode). The default name is fine.
    }

    refreshDocumentList()
      .then((list) => {
        // Open the MSA first (it has the demo scenarios), otherwise the first document.
        const first = list.find((d) => d.id === "master-services-agreement") ?? list[0];
        setActiveId(first?.id ?? null);
      })
      .catch(showError)
      .finally(() => setDocumentsLoaded(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!activeId) return;
    setDocument(null);
    setPreview(null);
    setAiResult(null);
    setEditor(null);
    reloadDocument(activeId).catch(showError);
  }, [activeId, reloadDocument, showError]);

  function changeEditorName(name: string) {
    setEditorName(name);
    try {
      localStorage.setItem(EDITOR_NAME_KEY, name);
    } catch {
      // Storage can be blocked; the name just won't be remembered.
    }
  }

  // --- Preview: re-run whenever the document or its pending list changes ---------------

  useEffect(() => {
    if (!document) return;
    const doc = document;

    async function runPreview() {
      // The preview is all-or-nothing, so if one change no longer applies we set it
      // aside (its card shows the error) and retry with the rest.
      let candidates = pending;
      const errors: Record<string, string> = {};

      for (let attempt = 0; attempt <= pending.length; attempt++) {
        if (candidates.length === 0) {
          setPreview(null);
          setPreviewIds([]);
          break;
        }
        try {
          const result = await api.previewChanges(doc.id, candidates.map((c) => c.request), doc.version);
          setPreview(result);
          setPreviewIds(candidates.map((c) => c.id));
          break;
        } catch (error) {
          const index = error instanceof ApiError ? error.details.change_index : undefined;
          if (typeof index !== "number") {
            showError(error);
            break;
          }
          const failing = candidates[index];
          errors[failing.id] = (error as ApiError).message.replace(/^Change \d+: /, "");
          candidates = candidates.filter((c) => c.id !== failing.id);
        }
      }
      setChangeErrors(errors);
    }

    runPreview();
  }, [document, pending, showError]);

  const pendingViews: PendingChangeView[] = pending.map((change) => {
    const previewIndex = previewIds.indexOf(change.id);
    return {
      change,
      count: previewIndex >= 0 ? preview?.applied[previewIndex]?.count : undefined,
      error: changeErrors[change.id],
    };
  });

  // --- Pending changes: add, accept, reject ---------------------------------------------

  function setPendingForActive(update: (current: PendingChange[]) => PendingChange[]) {
    if (!activeId) return;
    setPendingByDoc((all) => ({ ...all, [activeId]: update(all[activeId] ?? []) }));
  }

  function openEditor(mode: EditMode, find: string) {
    setEditor({ mode, find, key: Date.now() });
  }

  function closeEditor() {
    setEditor(null);
  }

  function addPendingChange(request: ChangeRequest) {
    setPendingForActive((current) => [...current, makePendingChange(request, editorName)]);
    closeEditor();
  }

  function rejectChange(id: string) {
    setPendingForActive((current) => current.filter((c) => c.id !== id));
  }

  // Save the given changes as a new version, then drop them from the pending list.
  async function acceptChanges(toAccept: PendingChange[]) {
    if (!document || toAccept.length === 0) return;
    setBusy(true);
    try {
      const result = await api.editDocument(
        document.id,
        toAccept.map((c) => c.request),
        document.version, // 409 if someone saved a newer version meanwhile
        editorName,
      );
      const acceptedIds = new Set(toAccept.map((c) => c.id));
      setPendingForActive((current) => current.filter((c) => !acceptedIds.has(c.id)));
      setDocument({ ...document, version: result.version, text: result.text });
      setHistory(await api.getHistory(document.id));
      refreshDocumentList().catch(() => {});
      toast.success(toAccept.length === 1 ? `Change accepted. Now v${result.version}.` : `${toAccept.length} changes accepted. Now v${result.version}.`);
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  function acceptOne(id: string) {
    const change = pending.find((c) => c.id === id);
    if (change) acceptChanges([change]);
  }

  function acceptAll() {
    // Skip changes that no longer apply; they'd make the whole batch fail.
    acceptChanges(pending.filter((c) => !changeErrors[c.id]));
  }

  // --- AI suggestions -----------------------------------------------------------------

  // Ask the AI for edits. They arrive as pending cards (badged "AI"); nothing is saved.
  async function askAi(instruction: string) {
    if (!document || !instruction.trim()) return;
    setAiBusy(true);
    try {
      const result = await api.suggestEdits(document.id, instruction);
      const newChanges = result.suggestions.map((request) => makePendingChange(request, "Redline AI"));
      setPendingForActive((current) => [...current, ...newChanges]);
      setAiResult(result);
    } catch (error) {
      showError(error);
    } finally {
      setAiBusy(false);
    }
  }

  // --- Search ---------------------------------------------------------------------------

  // Search as the user types, waiting 300ms after the last keystroke.
  useEffect(() => {
    const query = searchQuery.trim();
    if (!query) {
      setSearchResponse(null);
      return;
    }
    const timer = setTimeout(() => {
      api.search(query).then(setSearchResponse).catch(showError);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, showError]);

  function openSearchResult(result: SearchResult) {
    setActiveId(result.document_id);
  }

  // --- Upload ---------------------------------------------------------------------------

  async function uploadFile(file: File) {
    setUploading(true);
    try {
      const created = await api.uploadDocument(file, editorName);
      await refreshDocumentList();
      setActiveId(created.id);
      toast.success(`Uploaded "${created.title}".`);
    } catch (error) {
      showError(error);
    } finally {
      setUploading(false);
    }
  }

  // --- Layout ---------------------------------------------------------------------------

  const viewerMarkdown = preview?.redline_markdown ?? document?.text ?? "";
  const cleanMarkdown = preview?.text_after ?? document?.text ?? "";

  return (
    <div className="flex h-screen overflow-hidden">
      <Toaster position="bottom-right" richColors closeButton />
      <AppNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar documentTitle={document?.title ?? "Contracts"} />
        <div className="flex min-h-0 flex-1">
          <DocumentSidebar
            documents={documents}
            activeId={activeId}
            onSelect={setActiveId}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            searchResponse={searchResponse}
            onOpenResult={openSearchResult}
            onUpload={uploadFile}
            uploading={uploading}
          />

          {document ? (
            <main className="flex min-w-0 flex-1 flex-col">
              <Header
                document={document}
                pendingCount={pending.length}
                editorName={editorName}
                onEditorNameChange={changeEditorName}
              />
              <div className="flex min-h-0 flex-1">
                <DocumentViewer
                  documentKey={`${document.id}-v${document.version}`}
                  markdown={viewerMarkdown}
                  cleanMarkdown={cleanMarkdown}
                  redlineUnavailable={pending.length > 0 && preview !== null && preview.redline_markdown === null}
                  onSuggestEdit={(text) => openEditor("edit", text)}
                />
                <ChangesPanel
                  changes={pendingViews}
                  history={history}
                  busy={busy}
                  onAccept={acceptOne}
                  onReject={rejectChange}
                  onAcceptAll={acceptAll}
                  onSuggestEdit={() => openEditor("edit", "")}
                  onRenameTerm={() => openEditor("rename", "")}
                  editForm={
                    editor ? (
                      <SuggestEditForm
                        key={editor.key}
                        mode={editor.mode}
                        initialFind={editor.find}
                        document={document}
                        onAdd={addPendingChange}
                        onClose={closeEditor}
                      />
                    ) : null
                  }
                  onAskAi={askAi}
                  aiBusy={aiBusy}
                  aiResult={aiResult}
                  onDismissAiResult={() => setAiResult(null)}
                />
              </div>
            </main>
          ) : (
            <EmptyState loading={!documentsLoaded || activeId !== null} />
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ loading }: { loading: boolean }) {
  return (
    <main className="flex flex-1 items-center justify-center">
      {loading ? (
        <p className="text-sm text-ink-muted">Loading…</p>
      ) : (
        <div className="text-center">
          <p className="font-serif text-2xl">Upload a contract to get started</p>
          <p className="mt-2 text-sm text-ink-muted">Use the upload box on the left. Word, Markdown, or text files.</p>
        </div>
      )}
    </main>
  );
}
