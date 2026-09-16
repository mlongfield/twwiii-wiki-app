export interface TreeNodeInput {
  id: string;
  row: number;
  column: number;
  label: string;
  icon: string | null;
  url: string | null;
  hidden: boolean;
  detailHtml: string;
}

export interface TreeLinkInput {
  parent: string;
  child: string;
}

export interface TreeCell {
  node: TreeNodeInput;
  rowIndex: number;
  column: number;
}

export interface TreeGroup {
  row: number;
  nodes: TreeNodeInput[];
}

export interface TreeLayout {
  rows: number[];
  columns: number;
  cells: TreeCell[];
  links: { from: string; to: string }[];
  groups: TreeGroup[];
}

/** Skill tree row used by the game for nodes it never shows. */
export const HIDDEN_ROW = 99;

export function layoutTree(nodes: TreeNodeInput[], links: TreeLinkInput[]): TreeLayout {
  const visible = nodes
    .filter((n) => !n.hidden && n.row !== HIDDEN_ROW)
    .sort((a, b) => a.row - b.row || a.column - b.column || a.id.localeCompare(b.id));
  const rows = [...new Set(visible.map((n) => n.row))];
  const rowIndex = new Map(rows.map((row, index) => [row, index]));

  const occupied = new Set<string>();
  const cells: TreeCell[] = visible.map((n) => {
    let column = n.column;
    while (occupied.has(`${n.row}:${column}`)) column += 1;
    occupied.add(`${n.row}:${column}`);
    return { node: n, rowIndex: rowIndex.get(n.row)!, column };
  });

  const ids = new Set(visible.map((n) => n.id));
  const seen = new Set<string>();
  const treeLinks: { from: string; to: string }[] = [];
  for (const link of links) {
    const id = `${link.parent}>${link.child}`;
    if (!ids.has(link.parent) || !ids.has(link.child) || seen.has(id)) continue;
    seen.add(id);
    treeLinks.push({ from: link.parent, to: link.child });
  }

  return {
    rows,
    columns: cells.length ? Math.max(...cells.map((c) => c.column)) + 1 : 0,
    cells,
    links: treeLinks,
    groups: rows.map((row) => ({ row, nodes: cells.filter((c) => c.node.row === row).map((c) => c.node) })),
  };
}
