import pytest
from pydantic import ValidationError

from twwiki.model import schemas
from twwiki.model.context import opt, by_key, grouped
from tests.model.fixtures import make_context


def test_opt_turns_empty_strings_into_none():
    assert opt("") is None
    assert opt(None) is None
    assert opt("x") == "x"
    assert opt(0) == 0


def test_rows_returns_dicts():
    ctx = make_context({"things": [{"key": "a", "n": 1}, {"key": "b", "n": 2}]})
    assert ctx.rows("SELECT key, n FROM things ORDER BY key") == [{"key": "a", "n": 1}, {"key": "b", "n": 2}]
    assert ctx.rows("SELECT key FROM things WHERE n = ?", [2]) == [{"key": "b"}]


def test_require_records_missing_tables_as_partial():
    ctx = make_context({"things": [{"key": "a"}]})
    assert ctx.table_exists("things") and not ctx.table_exists("nope")
    assert ctx.require("unit", "things") is True
    assert ctx.require("unit", "things", "nope", "gone") is False
    assert ctx.partial == {"unit": ["nope", "gone"]}


def test_catalog_name_counts_missing_names():
    ctx = make_context({"things": [{"key": "a"}]}, loc={"name_a": "Alpha", "name_b": ""})
    assert ctx.catalog_name("unit", "name_a") == "Alpha"
    assert ctx.catalog_name("unit", "name_b") is None
    assert ctx.catalog_name("unit", "name_c") is None
    assert ctx.missing_names == {"unit": 2}


def test_link_model_rejects_extra_fields():
    schemas.Link(type="unit", key="k", name=None, missing=True)
    with pytest.raises(ValidationError):
        schemas.Link(type="unit", key="k", name=None, missing=False, extra=1)


def test_effect_application_optional_fields_default_to_none():
    link = {"type": "effect", "key": "e", "name": None, "missing": False}
    src = {"type": "skill", "key": "s", "name": None, "missing": False}
    app = schemas.EffectApplication(effect=link, scope="force_to_force_own", value=4.0, source=src)
    dumped = app.model_dump(mode="json")
    assert dumped["value_damaged"] is None and dumped["context_requirement"] is None


def test_entity_decorator_registers_model():
    @schemas.entity("test_only_type")
    class Thing(schemas.Strict):
        key: str

    assert schemas.ENTITY_MODELS["test_only_type"] is Thing
    del schemas.ENTITY_MODELS["test_only_type"]


def test_by_key_and_grouped_read_rows():
    ctx = make_context({"things": [{"key": "b", "grp": "x", "n": 2}, {"key": "a", "grp": "x", "n": 1}]})
    # by_key indexes rows by the key column
    by_key_result = by_key(ctx, "things", "key")
    assert by_key_result["a"]["n"] == 1
    assert by_key_result["b"]["n"] == 2
    # grouped groups rows by the key column and maintains order via ORDER BY
    grouped_result = grouped(ctx, "things", "grp", "n")
    assert list(grouped_result["x"]) == [{"key": "a", "grp": "x", "n": 1}, {"key": "b", "grp": "x", "n": 2}]


def test_by_key_and_grouped_return_empty_for_missing_table():
    ctx = make_context({"things": [{"key": "a"}]})
    assert by_key(ctx, "nope", "key") == {}
    assert dict(grouped(ctx, "nope", "key", "key")) == {}
    # Optional tables should not add to partial
    assert ctx.partial == {}
