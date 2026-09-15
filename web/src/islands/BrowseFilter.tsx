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
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [shown, setShown] = useState(total);

  useEffect(() => {
    const needle = text.trim().toLowerCase();
    let count = 0;
    document.querySelectorAll<HTMLTableRowElement>(`#${tableId} tbody tr`).forEach((row) => {
      const matches =
        (!needle || (row.dataset.search ?? "").includes(needle)) &&
        Object.entries(selected).every(([index, value]) => !value || row.getAttribute(`data-f${index}`) === value);
      row.hidden = !matches;
      if (matches) count += 1;
    });
    setShown(count);
  }, [text, selected, tableId]);

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
