import { describe, expect, it } from "vitest";
import { HIDDEN_ROW, type TreeNodeInput, layoutTree } from "../../src/lib/treeLayout";

const node = (id: string, row: number, column: number, hidden = false): TreeNodeInput => ({
  id, row, column, label: id.toUpperCase(), icon: null, url: null, hidden, detailHtml: `<p>${id}</p>`,
});

describe("layoutTree", () => {
  it("removes hidden nodes and the hidden row, compacting row indexes", () => {
    const layout = layoutTree(
      [node("a", 0, 0), node("b", 2, 1), node("c", 2, 0), node("h", 1, 0, true), node("x", HIDDEN_ROW, 0)],
      [],
    );
    expect(layout.rows).toEqual([0, 2]);
    expect(layout.cells.map((c) => [c.node.id, c.rowIndex, c.column])).toEqual([
      ["a", 0, 0],
      ["c", 1, 0],
      ["b", 1, 1],
    ]);
    expect(layout.columns).toBe(2);
    expect(layout.groups.map((g) => [g.row, g.nodes.map((n) => n.id)])).toEqual([
      [0, ["a"]],
      [2, ["c", "b"]],
    ]);
  });

  it("keeps links between visible nodes only, without duplicates", () => {
    const layout = layoutTree(
      [node("a", 0, 0), node("b", 0, 1), node("h", 0, 2, true)],
      [
        { parent: "a", child: "b" },
        { parent: "a", child: "b" },
        { parent: "b", child: "h" },
        { parent: "missing", child: "a" },
      ],
    );
    expect(layout.links).toEqual([{ from: "a", to: "b" }]);
  });

  it("moves a node that shares a row and column to the next free column", () => {
    const layout = layoutTree([node("a", 0, 1), node("b", 0, 1)], []);
    expect(layout.cells.map((c) => [c.node.id, c.column])).toEqual([
      ["a", 1],
      ["b", 2],
    ]);
    expect(layout.columns).toBe(3);
  });

  it("handles an empty tree", () => {
    expect(layoutTree([], [])).toEqual({ rows: [], columns: 0, cells: [], links: [], groups: [] });
  });
});
