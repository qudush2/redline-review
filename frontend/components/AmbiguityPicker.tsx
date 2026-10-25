import type { AmbiguousMatch } from "@/lib/api";
import { splitSnippet } from "@/lib/format";

type AmbiguityPickerProps = {
  find: string;
  count: number; // total matches (the list may show only the first 20)
  matches: AmbiguousMatch[];
  onPick: (occurrence: number) => void;
  onPickAll: () => void;
};

// Shown when the text to change appears more than once. Instead of guessing,
// we list each match in context and let the user choose.
export default function AmbiguityPicker({ find, count, matches, onPick, onPickAll }: AmbiguityPickerProps) {
  return (
    <div className="rounded-xl border border-terracotta/50 bg-clay/40 p-3">
      <p className="text-sm font-medium">
        “{find}” appears {count} times. Which one did you mean?
      </p>
      <ul className="thin-scroll mt-2 flex max-h-56 flex-col gap-1.5 overflow-y-auto">
        {matches.map((match) => {
          const [before, text, after] = splitSnippet(match.snippet, match.match_start, match.match_end);
          return (
            <li key={match.occurrence}>
              <button
                type="button"
                onClick={() => onPick(match.occurrence)}
                className="w-full rounded-lg border border-line bg-white px-3 py-2 text-left hover:border-terracotta"
              >
                <span className="text-[11px] font-semibold text-ink-muted">Match {match.occurrence}</span>
                <span className="mt-0.5 block font-serif text-[13px] leading-snug">
                  {before}
                  <mark className="rounded bg-clay px-0.5 font-semibold text-rust">{text}</mark>
                  {after}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <button type="button" onClick={onPickAll} className="mt-2 text-xs font-semibold text-rust hover:text-rust-dark">
        Change all {count}
      </button>
    </div>
  );
}
