import { useEffect, useState } from "react";

interface FilterSpec {
  index: number;
  label: string;
  options: string[];
}

interface Props {
  tableId: string;
  filters: FilterSpec[];
  total: number;
}

export default function BrowseFilter({ tableId, filters, total }: Props) {
  const [text, setText] = useState("");
  const [debouncedText, setDebouncedText] = useState("");
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [shown, setShown] = useState(total);

  // Debounce the free-text filter (~150ms) so fast typing doesn't force a full
  // table pass per keystroke; select filters below apply immediately.
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedText(text), 150);
    return () => window.clearTimeout(timer);
  }, [text]);

  useEffect(() => {
    const needle = debouncedText.trim().toLowerCase();
    const frame = requestAnimationFrame(() => {
      let count = 0;
      document.querySelectorAll<HTMLTableRowElement>(`#${tableId} tbody tr`).forEach((row) => {
        const matches =
          (!needle || (row.dataset.search ?? "").includes(needle)) &&
          Object.entries(selected).every(([index, value]) => !value || row.getAttribute(`data-f${index}`) === value);
        row.hidden = !matches;
        if (matches) count += 1;
      });
      setShown(count);
    });
    return () => cancelAnimationFrame(frame);
  }, [debouncedText, selected, tableId]);

  return (
    <div className="browse-filter" role="search">
      <input
        type="search"
        placeholder="Filter by name or key"
        aria-label="Filter by name or key"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      {filters.map((f) => (
        <label key={f.index}>
          {f.label}{" "}
          <select value={selected[f.index] ?? ""} onChange={(e) => setSelected({ ...selected, [f.index]: e.target.value })}>
            <option value="">All</option>
            {f.options.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </label>
      ))}
      <span className="muted">
        {shown} of {total}
      </span>
    </div>
  );
}
