"""Search across documents. Pure logic, no web framework.

Approach: a linear scan of each document for every query. Scanning 10MB takes a
fraction of a second, and it always reflects the latest edits. An inverted index
would make repeated searches faster but costs memory and must be updated on every
edit (see the README for the trade-off).
"""

from app.errors import InvalidRequest
from app.matching import find_matches, make_snippet


def search_documents(
    documents: list[dict],
    query: str,
    limit: int = 10,
    offset: int = 0,
    document_ids: list[str] | None = None,
    whole_word: bool = False,
) -> dict:
    """Find every match of `query` (case-insensitive) and return one page of results.

    We first collect only match *positions* (cheap), so `total` is exact. Then we
    build snippets and line numbers just for the page being returned.

    Examples (documents = MSA with "Liability" twice, NDA with "LIABILITY" once):
        search_documents(documents, "liability")
            -> {"total": 3, "results": [MSA hit 1, MSA hit 2, NDA hit 1], ...}
               # case doesn't matter in search

        search_documents(documents, "liability", limit=1, offset=1)
            -> {"total": 3, "results": [MSA hit 2], ...}
               # page 2 when showing 1 per page; total is still the full count

        search_documents(documents, "liability", document_ids=["nda"])
            -> {"total": 1, "results": [NDA hit 1], ...}
               # search inside one document only

        search_documents(documents, "indemnification")
            -> {"total": 0, "results": [], ...}     # no results is not an error

        search_documents(documents, "   ")
            -> raises InvalidRequest

    Each result looks like (MSA text = "Intro line\\nLimitation of Liability applies.\\nliability again"):
        {"document_id": "msa", "document_title": "MSA",
         "position": 25,                  # "Liability" starts at character 25 of the document
         "line": 2,                       # it's on the 2nd line
         "occurrence_in_document": 1,     # 1st match in this document
         "snippet": "Intro line Limitation of Liability applies. liability again",
         "match_start": 25, "match_end": 34}   # snippet[25:34] == "Liability"
    """
    # 1. Ignore stray spaces; refuse an empty search.
    query = query.strip()
    if not query:
        raise InvalidRequest("Enter some text to search for.")

    # 2. Find every match position, document by document, in order.
    #    Each entry is (document, position, "this is the Nth match in this document").
    all_matches = []
    for document in documents:
        # If the caller asked for specific documents, skip the rest.
        if document_ids is not None and document["id"] not in document_ids:
            continue
        positions = find_matches(document["text"], query, whole_word=whole_word, case_sensitive=False)
        for number, position in enumerate(positions, start=1):
            all_matches.append((document, position, number))

    # 3. Keep only the requested page. With limit=10, offset=20 that's matches 21–30.
    page = all_matches[offset : offset + limit]

    # 4. Build the display details (snippet, line number) only for that page.
    #    Doing this for every match would waste time when there are thousands.
    results = []
    for document, position, number in page:
        text = document["text"]
        snippet = make_snippet(text, position, position + len(query))
        results.append(
            {
                "document_id": document["id"],
                "document_title": document["title"],
                "position": position,
                # Line number = how many newlines come before the match, plus 1.
                "line": text.count("\n", 0, position) + 1,
                "occurrence_in_document": number,
                **snippet,  # adds "snippet", "match_start", "match_end"
            }
        )

    # 5. Send back the page plus the info a UI needs for "Showing 1–10 of 42".
    return {
        "query": query,
        "total": len(all_matches),
        "limit": limit,
        "offset": offset,
        "results": results,
    }
