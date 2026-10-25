// A proposed edit waiting for the user to accept or reject it.
// It lives only in the browser until accepted; then it's sent to the API.

import type { ChangeRequest } from "./api";

export type PendingChange = {
  id: string; // local id so React can track each card
  request: ChangeRequest; // exactly what we'll send to the API
  author: string; // who proposed it ("Redline AI" for AI suggestions)
  createdAt: string;
};

// What the changes panel shows for each pending change after the latest preview.
export type PendingChangeView = {
  change: PendingChange;
  count?: number; // how many places it will change (from the preview)
  error?: string; // set if this change no longer applies (e.g. its text is gone)
};

export function makePendingChange(request: ChangeRequest, author: string): PendingChange {
  return { id: crypto.randomUUID(), request, author, createdAt: new Date().toISOString() };
}
