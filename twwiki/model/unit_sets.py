"""Which unit sets each unit belongs to.

A rule row matches a unit when every non-empty filter on the row matches.
A unit is a member when it matches any include row and no exclude row.
Evaluated once here so the stat engine never re-implements the rules.
"""

from __future__ import annotations

from collections import defaultdict

from .context import Context

FILTERS = (("unit_record", "unit"), ("unit_caste", "caste"),
           ("unit_category", "category"), ("unit_class", "class"))


def evaluate_membership(units: list[dict], rules: list[dict]) -> dict[str, set[str]]:
    index: dict[tuple[str, str], set[str]] = defaultdict(set)
    for u in units:
        for _, field in FILTERS:
            if u.get(field):
                index[(field, u[field])].add(u["unit"])

    include: dict[str, set[str]] = defaultdict(set)
    exclude: dict[str, set[str]] = defaultdict(set)
    for r in rules:
        matched: set[str] | None = None
        for rule_col, field in FILTERS:
            value = r.get(rule_col)
            if not value:
                continue
            hits = index.get((field, value), set())
            matched = set(hits) if matched is None else matched & hits
        target = exclude if r["exclude"] else include
        target[r["unit_set"]] |= matched or set()

    return {s: include.get(s, set()) - exclude.get(s, set())
            for s in set(include) | set(exclude)}


def resolve_unit_sets(ctx: Context) -> dict[str, list[dict]]:
    if not ctx.require("unit", "main_units", "land_units", "unit_sets", "unit_set_to_unit_junctions"):
        return {}
    units = ctx.rows("""
        SELECT mu.unit, mu.caste, lu.category, lu.class
        FROM main_units mu LEFT JOIN land_units lu ON lu.key = mu.land_unit
    """)
    rules = ctx.rows("""
        SELECT unit_set, exclude, unit_record, unit_caste, unit_category, unit_class
        FROM unit_set_to_unit_junctions
    """)
    sets = {r["key"]: r for r in ctx.rows("SELECT * FROM unit_sets")}

    by_unit: dict[str, list[dict]] = defaultdict(list)
    for set_key, members in evaluate_membership(units, rules).items():
        meta = sets.get(set_key)
        conditional = bool(meta and meta["use_unit_exp_level_range"])
        entry = {
            "key": set_key,
            "conditional": conditional,
            "min_exp_level": meta["min_unit_exp_level_inclusive"] if conditional else None,
            "max_exp_level": meta["max_unit_exp_level_inclusive"] if conditional else None,
        }
        for unit in members:
            by_unit[unit].append(entry)
    return {u: sorted(entries, key=lambda e: e["key"]) for u, entries in by_unit.items()}
