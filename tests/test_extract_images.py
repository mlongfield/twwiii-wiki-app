import asyncio
import json
from pathlib import Path

import pytest

from twwiki import extract_images as ei
from twwiki.extract import _image_paths_from_tables
from twwiki.extract_images import column_values, extract_images, image_containers, matches_entry
from twwiki.rpfm_client import RpfmError


class FakeClient:
    """Writes the files an ExtractPackedFiles call names, like rpfm_server does."""

    def __init__(self, files_by_folder: dict[str, list[str]] | None = None, failing: tuple[str, ...] = (),
                 failing_files: tuple[str, ...] = ()):
        self.files_by_folder = files_by_folder or {}
        self.failing = failing
        self.failing_files = failing_files
        self.calls: list[tuple[str, list]] = []

    async def call(self, command, args=None):
        self.calls.append((command, args))
        _, sources, dest, _ = args
        written = []
        for source in sources["GameFiles"]:
            if "Folder" in source:
                folder = source["Folder"]
                if folder in self.failing:
                    raise RpfmError(f"{command} failed: boom")
                paths = [f"{folder}/{name}" for name in self.files_by_folder.get(folder, [])]
            else:
                if source["File"] in self.failing_files:
                    raise RpfmError(f"{command} failed: bad file")
                paths = [source["File"]]
            for rel in paths:
                path = Path(dest) / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"png")
                written.append(str(path))
        return ["", written]


def game(*paths, container="ui.pack"):
    return [{"path": p, "container_name": container} for p in paths]


FLAGS = game("ui/flags/wh_main_emp_empire/mon_64.png", "ui/flags/wh_main_emp_empire/mon_256.png",
             "ui/flags/wh_main_dwf_dwarfs/mon_64.png", "ui/flags/wh_main_dwf_dwarfs/sub/mon_64.png")


def exported_files(client):
    return [s["File"] for _, args in client.calls for s in args[1]["GameFiles"] if "File" in s]


def test_exports_each_folder_with_game_files_source_and_counts_files(tmp_path):
    client = FakeClient({"ui/units/icons": ["a.png", "b.png"], "ui/skins": ["default/x.png"]})
    dest = tmp_path / "images"
    section = asyncio.run(extract_images(client, ["ui/units/icons", "ui/skins"], dest, []))
    assert client.calls == [
        ("ExtractPackedFiles", ["", {"GameFiles": [{"Folder": "ui/units/icons"}]}, str(dest.resolve()), False]),
        ("ExtractPackedFiles", ["", {"GameFiles": [{"Folder": "ui/skins"}]}, str(dest.resolve()), False]),
    ]
    assert section == {"folders": {"ui/units/icons": 2, "ui/skins": 1}, "failed_folders": []}
    assert (dest / "ui/skins/default/x.png").exists()


def test_failed_and_empty_folders_are_listed_and_others_still_run(tmp_path):
    client = FakeClient({"ui/units/icons": ["a.png"]}, failing=("ui/broken",))
    section = asyncio.run(extract_images(client, ["ui/broken", "ui/empty", "ui/units/icons"], tmp_path / "images", []))
    assert section["folders"] == {"ui/units/icons": 1}
    assert section["failed_folders"] == [
        {"folder": "ui/broken", "error": "ExtractPackedFiles failed: boom"},
        {"folder": "ui/empty", "error": "no files exported"},
    ]


def test_no_folders_exports_nothing(tmp_path):
    client = FakeClient()
    section = asyncio.run(extract_images(client, [], tmp_path / "images", []))
    assert section == {"folders": {}, "failed_folders": []}
    assert client.calls == [] and not (tmp_path / "images").exists()


def test_star_matches_exactly_one_path_segment_ignoring_case():
    assert matches_entry("UI/Flags/wh_main_emp_empire/mon_64.png", "ui/flags/*/mon_64.png")
    assert not matches_entry("ui/flags/wh_main_emp_empire/mon_256.png", "ui/flags/*/mon_64.png")
    assert not matches_entry("ui/flags/a/sub/mon_64.png", "ui/flags/*/mon_64.png")
    assert matches_entry("ui/skins/default/x.png", "ui/skins/default/*.png")
    assert not matches_entry("ui/skins/default/dlc/x.png", "ui/skins/default/*.png")


def test_plain_entries_match_everything_under_the_folder():
    assert matches_entry("UI/Units/Icons/a.png", "ui/units/icons")
    assert matches_entry("ui/units/icons/deeper/a.png", "ui/units/icons/")
    assert not matches_entry("ui/units/icons_old/a.png", "ui/units/icons")


def test_pattern_entries_export_only_matching_files(tmp_path):
    client = FakeClient()
    dest = tmp_path / "images"
    section = asyncio.run(extract_images(client, ["ui/flags/*/mon_64.png"], dest, FLAGS))
    assert sorted(exported_files(client)) == ["ui/flags/wh_main_dwf_dwarfs/mon_64.png",
                                              "ui/flags/wh_main_emp_empire/mon_64.png"]
    assert section == {"folders": {"ui/flags/*/mon_64.png": 2}, "failed_folders": []}
    assert (dest / "ui/flags/wh_main_emp_empire/mon_64.png").exists()


def test_pattern_files_are_exported_in_batches(tmp_path, monkeypatch):
    monkeypatch.setattr(ei, "FILE_BATCH", 2)
    files = game(*(f"ui/skins/default/{i}.png" for i in range(5)))
    client = FakeClient()
    section = asyncio.run(extract_images(client, ["ui/skins/default/*.png"], tmp_path / "images", files))
    assert [len(args[1]["GameFiles"]) for _, args in client.calls] == [2, 2, 1]
    assert section["folders"] == {"ui/skins/default/*.png": 5}


def test_pattern_with_no_match_or_failed_export_is_listed(tmp_path):
    client = FakeClient(failing_files=("ui/flags/wh_main_emp_empire/mon_256.png",))
    section = asyncio.run(extract_images(
        client, ["ui/nothing/*.png", "ui/flags/*/mon_256.png", "ui/flags/*/mon_64.png"], tmp_path / "images", FLAGS))
    assert section["folders"] == {"ui/flags/*/mon_64.png": 2}
    assert section["failed_folders"] == [
        {"folder": "ui/nothing/*.png", "error": "no files matched"},
        {"folder": "ui/flags/*/mon_256.png", "error": "ExtractPackedFiles failed: bad file"},
    ]


def test_table_paths_export_files_not_already_covered(tmp_path):
    files = FLAGS + game("ui/skins/warhammer2/icon.png", "ui/cursors/Attack.png")
    table_paths = ["UI\\Flags\\wh_main_emp_empire\\mon_64.png",  # covered by the pattern
              "ui/skins/warhammer2/icon.png", "ui//cursors/attack.png", "ui/cursors/attack.png",
              "ui/skins/missing.png", ""]
    client = FakeClient()
    dest = tmp_path / "images"
    section = asyncio.run(extract_images(client, ["ui/flags/*/mon_64.png"], dest, files, table_paths))
    assert section["from_tables"] == {"listed": 4, "not_in_game": 1, "already_covered": 1, "exported": 2}
    assert exported_files(client)[-2:] == ["ui/cursors/Attack.png", "ui/skins/warhammer2/icon.png"]
    assert (dest / "ui/skins/warhammer2/icon.png").exists()
    assert section["failed_folders"] == []


def test_table_paths_export_failure_is_listed(tmp_path):
    client = FakeClient(failing_files=("ui/cursors/a.png",))
    section = asyncio.run(extract_images(client, [], tmp_path / "images", game("ui/cursors/a.png"),
                                         ["ui/cursors/a.png"]))
    assert section["from_tables"]["exported"] == 0
    assert section["failed_folders"] == [{"folder": "path_columns", "error": "ExtractPackedFiles failed: bad file"}]


def test_column_values_read_the_staged_table(tmp_path):
    staged = tmp_path / "files/db/ui_tagged_images_tables/data__.jsonl"
    staged.parent.mkdir(parents=True)
    header = {"table": "ui_tagged_images_tables",
              "fields": [{"name": "key"}, {"name": "image_path"}]}
    staged.write_text("\n".join(json.dumps(x) for x in [header, ["a", "ui/x.png"], ["b", "UI\\Y.png"]]) + "\n",
                      encoding="utf-8")
    rel = ["files/db/ui_tagged_images_tables/data__.jsonl"]
    assert column_values(tmp_path, rel, "image_path") == ["ui/x.png", "UI\\Y.png"]
    assert column_values(tmp_path, [], "image_path") == []
    with pytest.raises(ValueError, match="no column nope"):
        column_values(tmp_path, rel, "nope")


def test_image_paths_from_tables_collects_columns_and_reports_problems(tmp_path):
    staged = tmp_path / "files/db/ancillary_types_tables/data__.jsonl"
    staged.parent.mkdir(parents=True)
    staged.write_text(json.dumps({"fields": [{"name": "type"}, {"name": "ui_icon"}]}) + "\n"
                      + json.dumps(["t", "ui/skins/default/sub/a.png"]) + "\n", encoding="utf-8")
    tables = {"ancillary_types_tables": ["files/db/ancillary_types_tables/data__.jsonl"]}

    assert _image_paths_from_tables(tmp_path, tables, None) == (None, [])
    paths, problems = _image_paths_from_tables(
        tmp_path, tables, ["ancillary_types.ui_icon", "ancillary_types.nope", "missing_table.path"])
    assert paths == ["ui/skins/default/sub/a.png"]
    assert [p["folder"] for p in problems] == ["ancillary_types.nope", "missing_table.path"]
    assert problems[1]["error"] == "table missing_table was not extracted"


def test_image_containers_follow_folders_and_patterns():
    files = [
        {"path": "ui/units/icons/a.png", "container_name": "ui.pack"},
        {"path": "UI/Skins/default/b.png", "container_name": "ui2.pack"},
        {"path": "ui/skins/default/sub/b.png", "container_name": "deep.pack"},
        {"path": "ui/units/icons_old/c.png", "container_name": "old.pack"},
        {"path": "db/main_units_tables/data__", "container_name": "db.pack"},
        {"path": "ui/units/icons/loose.png", "container_name": None},
    ]
    assert image_containers(files, ["ui/units/icons", "ui/skins/default/*.png"]) == {"ui.pack", "ui2.pack"}
