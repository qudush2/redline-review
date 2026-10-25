#!/usr/bin/env bash
# Sample requests for every endpoint, using the seeded sample contracts.
#
# Start the API first (npm run dev), then either:
#   - run everything:      bash samples/requests.sh
#   - or copy one curl command at a time into your terminal.
#
# Note: the edits below really change the in-memory documents. Restart the
# server to get the original sample contracts back.

BASE="${BASE:-http://localhost:8000}"
MSA="master-services-agreement"

section() { printf '\n\n=== %s ===\n' "$1"; }

# --- Reads -------------------------------------------------------------------

section "Health check"
curl -s "$BASE/health"

section "List documents (no full text)"
curl -s "$BASE/documents"

section "Get one document (full text + version)"
curl -s "$BASE/documents/$MSA"

section "404: unknown document"
curl -s "$BASE/documents/does-not-exist"

# --- Search ------------------------------------------------------------------

section "Search all documents (case-insensitive), first page of 5"
curl -s "$BASE/documents/search?q=liability&limit=5&offset=0"

section "Search inside one document"
curl -s "$BASE/documents/$MSA/search?q=thirty%20(30)%20days"

section "400: empty search"
curl -s "$BASE/documents/search?q="

# --- Preview (nothing is saved) ----------------------------------------------

section "Preview an edit: returns the would-be text and an inline redline"
curl -s -X POST "$BASE/documents/$MSA/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "changes": [
      { "operation": "replace",
        "target": { "text": "State of California" },
        "replacement": "State of Delaware",
        "reason": "Playbook: Delaware law" }
    ]
  }'

section "422: ambiguous. \"thirty (30) days\" appears twice, so the API lists both and asks which"
curl -s -X POST "$BASE/documents/$MSA/preview" \
  -H "Content-Type: application/json" \
  -d '{ "changes": [ { "target": { "text": "thirty (30) days" }, "replacement": "sixty (60) days" } ] }'

section "422: text not found"
curl -s -X POST "$BASE/documents/$MSA/preview" \
  -H "Content-Type: application/json" \
  -d '{ "changes": [ { "target": { "text": "State of Nevada" }, "replacement": "State of Delaware" } ] }'

section "400: invalid payload (no changes)"
curl -s -X POST "$BASE/documents/$MSA/preview" \
  -H "Content-Type: application/json" \
  -d '{ "changes": [] }'

# --- Edits (saved as new versions) --------------------------------------------

section "Edit: pick the 2nd \"thirty (30) days\" (Termination), saved as version 2"
curl -s -X PATCH "$BASE/documents/$MSA" \
  -H "Content-Type: application/json" \
  -d '{
    "expected_version": 1,
    "author": "Qudus",
    "changes": [
      { "operation": "replace",
        "target": { "text": "thirty (30) days", "occurrence": 2 },
        "replacement": "sixty (60) days",
        "reason": "Playbook: 60 days notice for termination" }
    ]
  }'

section "Bulk edit, all-or-nothing: rename a defined term everywhere + change governing law (version 3)"
curl -s -X PATCH "$BASE/documents/$MSA" \
  -H "Content-Type: application/json" \
  -d '{
    "expected_version": 2,
    "author": "Qudus",
    "changes": [
      { "target": { "text": "Licensee", "occurrence": "all" },
        "replacement": "Customer",
        "reason": "Align with the order form" },
      { "target": { "text": "State of California" },
        "replacement": "State of Delaware",
        "reason": "Playbook: Delaware law",
        "source": "ai" }
    ]
  }'

section "409: stale expected_version (someone else saved first)"
curl -s -X PATCH "$BASE/documents/$MSA" \
  -H "Content-Type: application/json" \
  -d '{ "expected_version": 1, "changes": [ { "target": { "text": "Net" }, "replacement": "Gross" } ] }'

section "History: newest first, with author, reason, and human/AI source"
curl -s "$BASE/documents/$MSA/history"

# --- Create and upload --------------------------------------------------------

section "Create a document from JSON"
curl -s -X POST "$BASE/documents" \
  -H "Content-Type: application/json" \
  -d '{ "title": "Vendor Terms", "text": "# Vendor Terms\n\n1. Payment is due Net 45.", "author": "Qudus" }'

section "Upload a .docx (converted to Markdown)"
curl -s -X POST "$BASE/documents/upload" \
  -F "file=@samples/sample-vendor-agreement.docx" \
  -F "author=Qudus"

section "415: unsupported file type"
printf '%%PDF-1.4 fake' > /tmp/redline-sample.pdf
curl -s -X POST "$BASE/documents/upload" -F "file=@/tmp/redline-sample.pdf"

echo
