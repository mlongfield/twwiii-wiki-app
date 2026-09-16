import MiniSearch from "minisearch";
import { type FocusEvent, type KeyboardEvent, useEffect, useMemo, useState } from "react";
import { type ResultGroup, SEARCH_OPTIONS, SEARCH_QUERY, type SearchDocument, groupResults } from "../lib/search";

interface Props {
  indexUrl: string;
}

let loadedIndex: Promise<MiniSearch<SearchDocument>> | null = null;

function loadIndex(url: string): Promise<MiniSearch<SearchDocument>> {
  loadedIndex ??= fetch(url)
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.text();
    })
    .then((text) => MiniSearch.loadJSON<SearchDocument>(text, SEARCH_OPTIONS));
  return loadedIndex;
}

export default function SearchBox({ indexUrl }: Props) {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState<MiniSearch<SearchDocument> | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  function ensureIndex() {
    if (status === "loading" || status === "ready") return;
    setStatus("loading");
    loadIndex(indexUrl).then(
      (loaded) => {
        setIndex(loaded);
        setStatus("ready");
      },
      () => {
        loadedIndex = null;
        setStatus("error");
      },
    );
  }

  const trimmed = query.trim();
  const groups: ResultGroup[] = useMemo(
    () => (index && trimmed.length >= 2 ? groupResults(index.search(trimmed, SEARCH_QUERY)) : []),
    [index, trimmed],
  );
  const hits = useMemo(() => groups.flatMap((g) => g.items), [groups]);
  useEffect(() => setActive(0), [trimmed]);

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((a) => Math.min(a + 1, hits.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (event.key === "Enter" && hits[active]) {
      event.preventDefault();
      window.location.href = hits[active].url;
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  function onBlur(event: FocusEvent<HTMLDivElement>) {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
  }

  let position = -1;
  return (
    <div className="site-search" onBlur={onBlur}>
      <input
        type="search"
        placeholder="Search units, skills, regions…"
        aria-label="Search the wiki"
        role="combobox"
        aria-expanded={open && hits.length > 0}
        aria-controls="search-results"
        autoComplete="off"
        value={query}
        onFocus={() => {
          ensureIndex();
          setOpen(true);
        }}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onKeyDown={onKeyDown}
      />
      {open && trimmed.length >= 2 && (
        <div id="search-results" className="search-results" role="listbox">
          {status === "loading" && <p className="muted">Loading search…</p>}
          {status === "error" && <p className="muted">Search is unavailable.</p>}
          {status === "ready" && hits.length === 0 && <p className="muted">No matches.</p>}
          {groups.map((group) => (
            <div key={group.type} className="search-group" role="group">
              <div className="search-group-label">{group.typeLabel}</div>
              {group.items.map((item) => {
                position += 1;
                const itemPosition = position;
                return (
                  <a
                    key={item.id}
                    href={item.url}
                    role="option"
                    aria-selected={itemPosition === active}
                    className={itemPosition === active ? "search-hit active" : "search-hit"}
                    onMouseEnter={() => setActive(itemPosition)}
                  >
                    {item.icon ? <img src={item.icon} alt="" width={20} height={20} /> : <span className="search-hit-blank" />}
                    <span>{item.name}</span>
                  </a>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
