// Highlight a search hit inside the rendered document and scroll to it.
//
// We use the browser's CSS Custom Highlight API: it paints a highlight over a
// text range WITHOUT changing the page's HTML. That matters because React owns
// that HTML; editing it by hand (e.g. wrapping text in <mark>) can confuse React.
// The color comes from the ::highlight(search-hit) rule in globals.css.

const HIGHLIGHT_NAME = "search-hit";

// Find the Nth case-insensitive match of `query` in `container` and highlight it.
// Example: highlightMatch(article, "liability", 2) highlights the 2nd "liability".
// Returns false if it couldn't find it (e.g. the match spans bold and plain text).
export function highlightMatch(container: HTMLElement, query: string, occurrence: number): boolean {
  clearHighlight();
  const needle = query.toLowerCase();
  let seen = 0;

  // 1. Walk through every piece of text in the document, in reading order.
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    // 2. Look for the query inside this piece of text, possibly more than once.
    const text = (node.textContent ?? "").toLowerCase();
    let index = text.indexOf(needle);
    while (index !== -1) {
      seen += 1;
      // 3. Is this the one we want? Highlight it and scroll it into view.
      if (seen === occurrence) {
        const range = new Range();
        range.setStart(node, index);
        range.setEnd(node, index + needle.length);
        if ("highlights" in CSS) {
          CSS.highlights.set(HIGHLIGHT_NAME, new Highlight(range));
        }
        node.parentElement?.scrollIntoView({ block: "center", behavior: "smooth" });
        return true;
      }
      index = text.indexOf(needle, index + needle.length);
    }
    node = walker.nextNode();
  }
  return false;
}

export function clearHighlight(): void {
  if (typeof CSS !== "undefined" && "highlights" in CSS) {
    CSS.highlights.delete(HIGHLIGHT_NAME);
  }
}
