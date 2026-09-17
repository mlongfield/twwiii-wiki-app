import { useEffect, useState } from "react";
import { DEFAULT_CAMPAIGN, EVERY_CAMPAIGN, campaignMatches } from "../lib/campaignFilter";

interface FilterSpec {
  index: number;
  label: string;
  options: string[];
}

interface Props {
  tableId: string;
  filters: FilterSpec[];
  total: number;
  campaigns?: { key: string; name: string }[];
}

export default function BrowseFilter({ tableId, filters, total, campaigns = [] }: Props) {
  const [text, setText] = useState("");
  const [debouncedText, setDebouncedText] = useState("");
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [campaign, setCampaign] = useState(campaigns.some((c) => c.key === DEFAULT_CAMPAIGN) ? DEFAULT_CAMPAIGN : "");
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
          (!campaigns.length || campaignMatches(row.dataset.campaigns ?? EVERY_CAMPAIGN, campaign)) &&
          Object.entries(selected).every(([index, value]) => !value || row.getAttribute(`data-f${index}`) === value);
        row.hidden = !matches;
        if (matches) count += 1;
      });
      setShown(count);
    });
    return () => cancelAnimationFrame(frame);
  }, [debouncedText, selected, campaign, campaigns.length, tableId]);

  return (
    <div className="browse-filter" role="search">
      <input
        type="search"
        placeholder="Filter by name or key"
        aria-label="Filter by name or key"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      {campaigns.length > 0 && (
        <label>
          Campaign{" "}
          <select value={campaign} onChange={(e) => setCampaign(e.target.value)}>
            <option value="">All</option>
            {campaigns.map((c) => (
              <option key={c.key} value={c.key}>{c.name}</option>
            ))}
          </select>
        </label>
      )}
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
