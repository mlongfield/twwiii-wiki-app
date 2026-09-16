import duckdb
import pandas as pd

from twwiki.model.link_report import link_report
from tests.model.fixtures import make_context


def make_db(tables: dict[str, list[dict]], columns: list[tuple]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    for name, rows in tables.items():
        con.register("_fixture", pd.DataFrame(rows))
        con.execute(f'CREATE TABLE "{name}" AS SELECT * FROM _fixture')
        con.unregister("_fixture")
    con.execute("""CREATE TABLE _columns (table_name VARCHAR, position INTEGER, column_name VARCHAR,
                   rpfm_type VARCHAR, is_key BOOLEAN, ref_table VARCHAR, ref_column VARCHAR)""")
    con.executemany("INSERT INTO _columns VALUES (?, 0, ?, 'StringU8', false, ?, ?)", columns)
    return con


TABLES = {
    "unit_abilities": [{"key": "hold"}, {"key": "charge"}],
    "unit_ability_junctions": [{"ability": "hold"}, {"ability": "gone"}, {"ability": "gone"}, {"ability": ""}],
    "battle_contexts": [{"unit_ability": "charge"}],
    "unit_ability_types": [{"key": "spell"}],
    "unrelated": [{"a": "x"}, {"b": "y"}],
}
COLUMNS = [
    ("unit_ability_junctions", "ability", "unit_abilities", "key"),
    ("battle_contexts", "unit_ability", "unit_abilities", "key"),
    ("unit_abilities", "key", "unit_ability_types", "key"),
    ("unrelated", "a", "unrelated", "b"),
    ("unit_abilities", "key", None, None),
]


def by_source(report):
    return {(r["source_table"], r["source_column"]): r for r in report["references"]}


def test_references_are_labelled_by_which_tables_the_model_read():
    con = make_db(TABLES, COLUMNS)
    report = link_report(con, {"unit_abilities", "unit_ability_junctions"})
    refs = by_source(report)

    assert report["available"] is True
    assert set(refs) == {("unit_ability_junctions", "ability"), ("battle_contexts", "unit_ability"),
                         ("unit_abilities", "key")}
    assert refs[("unit_ability_junctions", "ability")]["status"] == "both_read"
    assert refs[("battle_contexts", "unit_ability")]["status"] == "source_not_read"
    assert refs[("unit_abilities", "key")]["status"] == "target_not_read"
    assert report["summary"] == {"tables_read": 2, "both_read": 1, "source_not_read": 1,
                                 "target_not_read": 1, "with_broken_values": 1}


def test_broken_values_are_counted_for_references_between_read_tables_only():
    con = make_db(TABLES, COLUMNS)
    refs = by_source(link_report(con, {"unit_abilities", "unit_ability_junctions"}))

    junction = refs[("unit_ability_junctions", "ability")]
    assert (junction["target_table"], junction["target_column"]) == ("unit_abilities", "key")
    # the empty value means "none" and is not counted
    assert junction["rows_with_value"] == 3
    assert junction["broken_rows"] == 2
    assert junction["broken_values"] == 1
    assert junction["examples"] == ["gone"]
    assert "broken_rows" not in refs[("battle_contexts", "unit_ability")]


def test_reference_to_a_table_that_was_not_loaded_is_skipped_for_counting():
    con = make_db(TABLES, COLUMNS + [("unit_ability_junctions", "ability", "never_loaded", "key")])
    refs = [r for r in link_report(con, {"unit_ability_junctions"})["references"]
            if r["target_table"] == "never_loaded"]
    assert refs == [{"source_table": "unit_ability_junctions", "source_column": "ability",
                     "target_table": "never_loaded", "target_column": "key", "status": "target_not_read"}]


def test_database_without_column_metadata_gives_an_unavailable_report():
    con = duckdb.connect(":memory:")
    assert link_report(con, {"anything"}) == {"available": False, "summary": {}, "references": []}


def test_context_records_tables_read_through_rows():
    ctx = make_context({"unit_abilities": [{"key": "hold"}], "unit_ability_junctions": [{"ability": "hold"}]})
    ctx.rows("SELECT * FROM unit_abilities a JOIN \"unit_ability_junctions\" j ON j.ability = a.key")
    ctx.rows("SELECT table_name FROM information_schema.tables")
    ctx.rows("WITH x AS (SELECT 1 AS k) SELECT * FROM x")
    assert ctx.tables_read == {"unit_abilities", "unit_ability_junctions"}
