import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { TreeLayout } from "../lib/treeLayout";

interface Props {
  layout: TreeLayout;
  ariaLabel: string;
}

interface Line {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

function TreeGrid({ layout, selected, onSelect }: { layout: TreeLayout; selected: string | null; onSelect: (id: string) => void }) {
  const gridRef = useRef<HTMLDivElement>(null);
  const [lines, setLines] = useState<Line[]>([]);

  useLayoutEffect(() => {
    const grid = gridRef.current;
    if (!grid) return;
    const measure = () => {
      const box = grid.getBoundingClientRect();
      const rects = new Map<string, DOMRect>();
      grid.querySelectorAll<HTMLElement>("[data-node]").forEach((el) => rects.set(el.dataset.node!, el.getBoundingClientRect()));
      setLines(
        layout.links.flatMap((link) => {
          const a = rects.get(link.from);
          const b = rects.get(link.to);
          if (!a || !b) return [];
          return [{ x1: a.right - box.left, y1: a.top + a.height / 2 - box.top, x2: b.left - box.left, y2: b.top + b.height / 2 - box.top }];
        }),
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(grid);
    return () => observer.disconnect();
  }, [layout]);

  return (
    <div className="tree-grid-wrap">
      <div ref={gridRef} className="tree-grid" style={{ gridTemplateColumns: `repeat(${layout.columns}, minmax(8rem, 1fr))` }}>
        <svg className="tree-links" aria-hidden="true">
          {lines.map((l, i) => (
            <line key={i} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} />
          ))}
        </svg>
        {layout.cells.map((cell) => (
          <button
            key={cell.node.id}
            type="button"
            data-node={cell.node.id}
            className={cell.node.id === selected ? "tree-node selected" : "tree-node"}
            style={{ gridRow: cell.rowIndex + 1, gridColumn: cell.column + 1 }}
            aria-pressed={cell.node.id === selected}
            onClick={() => onSelect(cell.node.id)}
          >
            {cell.node.icon && <img src={cell.node.icon} alt="" width={24} height={24} />}
            <span>{cell.node.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function TreeLines({ layout }: { layout: TreeLayout }) {
  return (
    <div className="tree-lines">
      {layout.groups.map((group, index) => (
        <details key={group.row} open={index === 0}>
          <summary>Line {index + 1} ({group.nodes.length})</summary>
          <ul>
            {group.nodes.map((node) => (
              <li key={node.id}>
                <details>
                  <summary>
                    {node.icon && <img src={node.icon} alt="" width={20} height={20} />} {node.label}
                  </summary>
                  <div dangerouslySetInnerHTML={{ __html: node.detailHtml }} />
                  {node.url && <a href={node.url}>Open page</a>}
                </details>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  );
}

export default function TreeView({ layout, ariaLabel }: Props) {
  const [selected, setSelected] = useState<string | null>(layout.cells[0]?.node.id ?? null);
  const [narrow, setNarrow] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(max-width: 767px)");
    const update = () => setNarrow(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  const byId = useMemo(() => new Map(layout.cells.map((c) => [c.node.id, c.node])), [layout]);
  const current = selected ? byId.get(selected) ?? null : null;

  if (layout.cells.length === 0) return <p className="muted">No visible nodes.</p>;
  if (narrow) return <TreeLines layout={layout} />;
  return (
    <div className="tree" role="group" aria-label={ariaLabel}>
      <TreeGrid layout={layout} selected={selected} onSelect={setSelected} />
      <aside className="tree-panel" aria-live="polite">
        {current && (
          <>
            <h3>{current.label}</h3>
            <div dangerouslySetInnerHTML={{ __html: current.detailHtml }} />
            {current.url && <a href={current.url}>Open page</a>}
          </>
        )}
      </aside>
    </div>
  );
}
