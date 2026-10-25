"use client";

import { useState } from "react";
import { CircleAlert, LoaderCircle, X } from "lucide-react";
import AmbiguityPicker from "./AmbiguityPicker";
import { api, ApiError, type AmbiguousMatch, type ChangeRequest, type DocumentFull, type Occurrence } from "@/lib/api";

// "edit": a normal find-and-replace. "rename": change a defined term everywhere.
export type DialogMode = "edit" | "rename";

type SuggestEditDialogProps = {
  mode: DialogMode;
  initialFind: string;
  document: DocumentFull;
  onAdd: (request: ChangeRequest) => void;
  onClose: () => void;
};

// What the dry run told us about the edit the user is about to add.
type Check =
  | { kind: "ambiguous"; count: number; matches: AmbiguousMatch[] }
  | { kind: "confirm-all"; count: number }
  | { kind: "error"; message: string };

// A dialog to propose one edit. Before adding it to the pending list, we do a dry
// run against the API (POST /preview) so problems show up here, not later:
//   - text not found      -> show the error
//   - text appears twice+ -> show the "Which one?" picker
//   - "all"               -> show how many places will change, and ask to confirm
export default function SuggestEditDialog({ mode, initialFind, document, onAdd, onClose }: SuggestEditDialogProps) {
  const isRename = mode === "rename";

  const [find, setFind] = useState(initialFind);
  const [replacement, setReplacement] = useState("");
  const [occurrenceMode, setOccurrenceMode] = useState<"auto" | "specific" | "all">(isRename ? "all" : "auto");
  const [occurrenceNumber, setOccurrenceNumber] = useState(1);
  const [wholeWord, setWholeWord] = useState(true);
  const [reason, setReason] = useState("");
  const [check, setCheck] = useState<Check | null>(null);
  const [checking, setChecking] = useState(false);

  // Editing any field makes the last check out of date.
  function edit<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setCheck(null);
    };
  }

  function buildRequest(occurrence: Occurrence): ChangeRequest {
    return {
      operation: "replace",
      target: { text: find, occurrence, whole_word: wholeWord },
      replacement,
      reason: reason.trim() || null,
      source: "human",
    };
  }

  function chosenOccurrence(): Occurrence {
    if (occurrenceMode === "all") return "all";
    if (occurrenceMode === "specific") return occurrenceNumber;
    return null; // "auto": must appear exactly once
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const request = buildRequest(chosenOccurrence());

    // Second click after "This will change 24 places": the user confirmed.
    if (check?.kind === "confirm-all") {
      onAdd(request);
      return;
    }

    // 1. Dry run: would this edit apply to the current document?
    setChecking(true);
    try {
      const result = await api.previewChanges(document.id, [request], document.version);
      const count = result.applied[0].count;

      // 2. Changing every match? Show the count first, so nothing surprising happens.
      if (request.target.occurrence === "all") {
        setCheck({ kind: "confirm-all", count });
        return;
      }
      // 3. Otherwise it applies cleanly: add it to the pending list.
      onAdd(request);
    } catch (error) {
      // 4. Ambiguous: offer the picker. Anything else: show the message.
      if (error instanceof ApiError && error.type === "ambiguous_match") {
        setCheck({
          kind: "ambiguous",
          count: error.details.count as number,
          matches: error.details.matches as AmbiguousMatch[],
        });
      } else {
        setCheck({ kind: "error", message: error instanceof Error ? error.message : "Something went wrong." });
      }
    } finally {
      setChecking(false);
    }
  }

  const submitLabel = check?.kind === "confirm-all" ? `Add change (${check.count} places)` : isRename ? "Preview rename" : "Add change";

  return (
    // Dark backdrop; clicking it closes the dialog.
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-espresso/40 p-4" onMouseDown={onClose}>
      <form
        onSubmit={handleSubmit}
        onMouseDown={(event) => event.stopPropagation()} // clicks inside shouldn't close it
        className="w-full max-w-lg rounded-2xl bg-surface p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 className="font-serif text-xl">{isRename ? "Rename a defined term" : "Suggest an edit"}</h2>
            <p className="mt-1 text-[13px] text-ink-muted">
              {isRename
                ? "Changes every whole-word match. You'll see the count before anything is added."
                : "It's added as a pending change. Nothing is saved until you accept it."}
            </p>
          </div>
          <button type="button" title="Close" onClick={onClose} className="text-ink-faint hover:text-ink">
            <X size={18} />
          </button>
        </div>

        <div className="mt-5 flex flex-col gap-4">
          <Field label={isRename ? "Current term" : "Find (exact text)"}>
            <textarea
              value={find}
              onChange={(event) => edit(setFind)(event.target.value)}
              rows={2}
              required
              autoFocus={!initialFind}
              placeholder={isRename ? "Licensee" : "thirty (30) days"}
              className={inputClass}
            />
          </Field>

          <Field label={isRename ? "New term" : "Replace with"} hint="Leave empty to delete the text.">
            <textarea
              value={replacement}
              onChange={(event) => edit(setReplacement)(event.target.value)}
              rows={2}
              autoFocus={Boolean(initialFind)}
              placeholder={isRename ? "Customer" : "sixty (60) days"}
              className={inputClass}
            />
          </Field>

          {!isRename ? (
            <Field label="Which occurrence">
              <div className="flex items-center gap-2">
                {(["auto", "specific", "all"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => edit(setOccurrenceMode)(option)}
                    className={`rounded-lg border px-3 py-1.5 text-[13px] font-medium ${
                      occurrenceMode === option ? "border-rust bg-clay text-rust" : "border-line bg-white hover:bg-subtle"
                    }`}
                  >
                    {{ auto: "Auto", specific: "Specific", all: "All" }[option]}
                  </button>
                ))}
                {occurrenceMode === "specific" ? (
                  <input
                    type="number"
                    min={1}
                    value={occurrenceNumber}
                    onChange={(event) => edit(setOccurrenceNumber)(Math.max(1, Number(event.target.value)))}
                    className={`${inputClass} w-20`}
                  />
                ) : null}
              </div>
            </Field>
          ) : null}

          <label className="flex items-center gap-2 text-[13px]">
            <input type="checkbox" checked={wholeWord} onChange={(event) => edit(setWholeWord)(event.target.checked)} className="accent-rust" />
            Whole words only <span className="text-ink-faint">(“Term” won’t match “Termination”)</span>
          </label>

          <Field label="Reason (optional)" hint="Shown in the history, e.g. “Playbook: 60 days' notice”.">
            <input value={reason} onChange={(event) => setReason(event.target.value)} className={inputClass} />
          </Field>

          {/* Result of the dry run */}
          {check?.kind === "ambiguous" ? (
            <AmbiguityPicker
              find={find}
              count={check.count}
              matches={check.matches}
              onPick={(occurrence) => onAdd(buildRequest(occurrence))}
              onPickAll={() => onAdd(buildRequest("all"))}
            />
          ) : null}
          {check?.kind === "confirm-all" ? (
            <p className="rounded-lg bg-ins-bg px-3 py-2 text-[13px] text-ins">
              Will change {check.count} {check.count === 1 ? "occurrence" : "occurrences"} of “{find}”.
            </p>
          ) : null}
          {check?.kind === "error" ? (
            <p className="flex items-start gap-1.5 rounded-lg bg-del-bg px-3 py-2 text-[13px] text-del">
              <CircleAlert size={15} className="mt-px shrink-0" /> {check.message}
            </p>
          ) : null}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-medium hover:bg-subtle">
            Cancel
          </button>
          <button
            type="submit"
            disabled={checking || !find.trim() || check?.kind === "ambiguous"}
            className="flex items-center gap-1.5 rounded-lg bg-rust px-4 py-2 text-sm font-medium text-white hover:bg-rust-dark disabled:opacity-40"
          >
            {checking ? <LoaderCircle size={15} className="animate-spin" /> : null}
            {submitLabel}
          </button>
        </div>
      </form>
    </div>
  );
}

const inputClass =
  "w-full rounded-lg border border-line bg-white px-3 py-2 font-serif text-[14px] outline-none focus:border-terracotta";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold text-ink-muted">{label}</span>
      {children}
      {hint ? <span className="text-[11px] text-ink-faint">{hint}</span> : null}
    </label>
  );
}
