// Placeholder data so the UI can be designed before the API exists.
// Shapes mirror the planned API responses; Phase 3 replaces this file with real calls.

export type DocumentSummary = {
  id: string;
  title: string;
  counterparty: string;
  file_type: "md" | "txt" | "docx";
  version: number;
  updated_at: string;
  status: "In negotiation" | "Internal review" | "Executed";
};

export type PendingChange = {
  id: string;
  find: string;
  replace: string;
  section: string;
  reason: string;
  source: "human" | "ai";
  author: string;
  created_at: string;
};

export type HistoryEntry = {
  version: number;
  author: string;
  timestamp: string;
  summary: string;
  source: "human" | "ai" | "system";
};

export type SearchHit = {
  document_title: string;
  line: number;
  snippet: string;
  match_start: number;
  match_end: number;
};

export const documents: DocumentSummary[] = [
  {
    id: "master-services-agreement",
    title: "Master Services Agreement",
    counterparty: "Acme Analytics LLC",
    file_type: "md",
    version: 3,
    updated_at: "2h ago",
    status: "In negotiation",
  },
  {
    id: "mutual-nda",
    title: "Mutual NDA",
    counterparty: "Harbor & Pine Co.",
    file_type: "docx",
    version: 1,
    updated_at: "Yesterday",
    status: "Internal review",
  },
  {
    id: "employment-agreement",
    title: "Employment Agreement",
    counterparty: "J. Rivera",
    file_type: "md",
    version: 2,
    updated_at: "Oct 19",
    status: "Executed",
  },
];

export const pendingChanges: PendingChange[] = [
  {
    id: "c1",
    find: "shall be unlimited",
    replace: "shall not exceed two times (2x) the fees paid in the twelve (12) months preceding the claim",
    section: "§ 8.1 Limitation of Liability",
    reason: "Playbook: cap liability at 2x annual fees. Never unlimited.",
    source: "ai",
    author: "Redline AI",
    created_at: "4 min ago",
  },
  {
    id: "c2",
    find: "State of California",
    replace: "State of Delaware",
    section: "§ 11.2 Governing Law",
    reason: "Playbook: governing law is Delaware.",
    source: "ai",
    author: "Redline AI",
    created_at: "4 min ago",
  },
  {
    id: "c3",
    find: "thirty (30) days",
    replace: "sixty (60) days",
    section: "§ 9.2 Termination for Convenience",
    reason: "Match our standard 60-day notice period.",
    source: "human",
    author: "Qudus",
    created_at: "12 min ago",
  },
];

export const history: HistoryEntry[] = [
  {
    version: 3,
    author: "Qudus",
    timestamp: "2h ago",
    summary: "Renamed “Licensee” → “Customer” (15 occurrences)",
    source: "human",
  },
  {
    version: 2,
    author: "Qudus",
    timestamp: "Yesterday",
    summary: "Payment terms changed to Net 30 (AI suggestion, accepted)",
    source: "ai",
  },
  {
    version: 1,
    author: "System",
    timestamp: "Oct 21",
    summary: "Uploaded from master-services-agreement.docx",
    source: "system",
  },
];

export const searchHits: SearchHit[] = [
  {
    document_title: "Master Services Agreement",
    line: 41,
    snippet: "…8.1 Limitation of Liability. Each party’s aggregate liability under this Agreement…",
    match_start: 5,
    match_end: 28,
  },
  {
    document_title: "Mutual NDA",
    line: 58,
    snippet: "…no limitation of liability shall apply to a breach of Section 3 (Confidentiality)…",
    match_start: 4,
    match_end: 27,
  },
];

// The contract shown in the viewer, with pending changes already marked up
// as <del>/<ins>. In Phase 3 this comes from POST /documents/{id}/preview.
export const redlineMarkdown = `# MASTER SERVICES AGREEMENT

This Master Services Agreement (the **"Agreement"**) is entered into as of October 1, 2026 (the **"Effective Date"**) by and between **Northwind Labs, Inc.**, a Delaware corporation (**"Provider"**), and **Acme Analytics LLC**, a California limited liability company (**"Customer"**).

## 1. Services

1.1 Provider shall provide the software and related services described in each order form executed by the parties (the **"Services"**). Each order form is incorporated into this Agreement by reference.

1.2 Customer may permit its Affiliates to use the Services, provided that Customer remains responsible for each Affiliate's compliance with this Agreement.

## 4. Fees and Payment

4.1 Customer shall pay all fees within thirty (30) days of the invoice date. Late amounts accrue interest at one percent (1%) per month or the maximum rate permitted by law, whichever is lower.

## 8. Limitation of Liability

8.1 Except for a party's indemnification obligations, each party's aggregate liability arising out of or related to this Agreement <del>shall be unlimited</del><ins>shall not exceed two times (2x) the fees paid in the twelve (12) months preceding the claim</ins>.

8.2 In no event shall either party be liable for any indirect, incidental, special, or consequential damages, including lost profits, even if advised of their possibility.

## 9. Term and Termination

9.1 This Agreement begins on the Effective Date and continues until all order forms have expired or been terminated.

9.2 Either party may terminate this Agreement for convenience upon <del>thirty (30)</del><ins>sixty (60)</ins> days' prior written notice to the other party.

## 11. General

11.2 This Agreement is governed by the laws of the <del>State of California</del><ins>State of Delaware</ins>, without regard to its conflict of laws principles.
`;
