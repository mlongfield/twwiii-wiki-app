import { useState } from "react";
import type { ChainGroup, CultureChoice } from "../lib/regionCultures";

interface Props {
  cultures: CultureChoice[];
  initialCulture: string;
  initialGroups: ChainGroup[];
  dataUrl: string;
}

let allChains: Promise<Record<string, ChainGroup[]>> | null = null;

function loadAllChains(url: string): Promise<Record<string, ChainGroup[]>> {
  allChains ??= fetch(url).then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  });
  return allChains;
}

export default function CulturePicker({ cultures, initialCulture, initialGroups, dataUrl }: Props) {
  const [culture, setCulture] = useState(initialCulture);
  const [groups, setGroups] = useState(initialGroups);
  const [status, setStatus] = useState<"ready" | "loading" | "error">("ready");

  async function choose(key: string) {
    setCulture(key);
    if (key === initialCulture) {
      setGroups(initialGroups);
      setStatus("ready");
      return;
    }
    setStatus("loading");
    try {
      const all = await loadAllChains(dataUrl);
      setGroups(all[key] ?? []);
      setStatus("ready");
    } catch {
      allChains = null;
      setStatus("error");
    }
  }

  const count = groups.reduce((n, g) => n + g.chains.length, 0);
  return (
    <div className="culture-picker">
      <label>
        Culture{" "}
        <select value={culture} onChange={(e) => void choose(e.target.value)}>
          {cultures.map((c) => (
            <option key={c.key} value={c.key}>{c.name}</option>
          ))}
        </select>
      </label>{" "}
      <span className="muted" aria-live="polite">
        {status === "loading" ? "Loading…" : status === "error" ? "Could not load building data." : `${count} building chains`}
      </span>
      {status === "ready" && count === 0 && <p className="muted">This culture has no building chains.</p>}
      {groups.map((group) => (
        <div key={group.category} className="chain-group">
          <h3>{group.category}</h3>
          <ul className="link-list">
            {group.chains.map((chain) => (
              <li key={chain.key}>
                {chain.url ? (
                  <a className="entity-link" href={chain.url}>
                    {chain.icon ? (
                      <img className="game-img game-img-icon" src={chain.icon} alt="" />
                    ) : (
                      <span className="game-img game-img-icon placeholder" data-placeholder-image="" aria-hidden="true" />
                    )}
                    <span>{chain.name}</span>
                  </a>
                ) : (
                  chain.name
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
