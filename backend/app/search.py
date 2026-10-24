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
    """
    query = query.strip()
    if not query:
        raise InvalidRequest("Enter some text to search for.")

    # Step 1: every match position, in document order.
    all_matches = []  # (document, position, occurrence number within that document)
    for document in documents:
        if document_ids is not None and document["id"] not in document_ids:
            continue
        positions = find_matches(document["text"], query, whole_word=whole_word, case_sensitive=False)
        for number, position in enumerate(positions, start=1):
            all_matches.append((document, position, number))

    # Step 2: details only for the requested page.
    page = all_matches[offset : offset + limit]
    results = []
    for document, position, number in page:
        text = document["text"]
        snippet = make_snippet(text, position, position + len(query))
        results.append(
            {
                "document_id": document["id"],
                "document_title": document["title"],
                "position": position,
                "line": text.count("\n", 0, position) + 1,
                "occurrence_in_document": number,
                **snippet,
            }
        )

    return {
        "query": query,
        "total": len(all_matches),
        "limit": limit,
        "offset": offset,
        "results": results,
    }
