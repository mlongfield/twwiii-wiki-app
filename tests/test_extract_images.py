import asyncio
from pathlib import Path

from twwiki.extract_images import extract_images, image_containers
from twwiki.rpfm_client import RpfmError


class FakeClient:
    def __init__(self, files_by_folder: dict[str, list[str]], failing: tuple[str, ...] = ()):
        self.files_by_folder = files_by_folder
        self.failing = failing
        self.calls: list[tuple[str, list]] = []

    async def call(self, command, args=None):
        self.calls.append((command, args))
        _, sources, dest, _ = args
        folder = sources["GameFiles"][0]["Folder"]
        if folder in self.failing:
            raise RpfmError(f"{command} failed: boom")
        written = []
        for name in self.files_by_folder.get(folder, []):
            path = Path(dest) / folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"png")
            written.append(str(path))
        return ["", written]


def test_exports_each_folder_with_game_files_source_and_counts_files(tmp_path):
    client = FakeClient({"ui/units/icons": ["a.png", "b.png"], "ui/skins": ["default/x.png"]})
    dest = tmp_path / "images"
    section = asyncio.run(extract_images(client, ["ui/units/icons", "ui/skins"], dest))
    assert client.calls == [
        ("ExtractPackedFiles", ["", {"GameFiles": [{"Folder": "ui/units/icons"}]}, str(dest.resolve()), False]),
        ("ExtractPackedFiles", ["", {"GameFiles": [{"Folder": "ui/skins"}]}, str(dest.resolve()), False]),
    ]
    assert section == {"folders": {"ui/units/icons": 2, "ui/skins": 1}, "failed_folders": []}
    assert (dest / "ui/skins/default/x.png").exists()


def test_failed_and_empty_folders_are_listed_and_others_still_run(tmp_path):
    client = FakeClient({"ui/units/icons": ["a.png"]}, failing=("ui/broken",))
    section = asyncio.run(extract_images(client, ["ui/broken", "ui/empty", "ui/units/icons"], tmp_path / "images"))
    assert section["folders"] == {"ui/units/icons": 1}
    assert section["failed_folders"] == [
        {"folder": "ui/broken", "error": "ExtractPackedFiles failed: boom"},
        {"folder": "ui/empty", "error": "no files exported"},
    ]


def test_no_folders_exports_nothing(tmp_path):
    client = FakeClient({})
    section = asyncio.run(extract_images(client, [], tmp_path / "images"))
    assert section == {"folders": {}, "failed_folders": []}
    assert client.calls == [] and not (tmp_path / "images").exists()


def test_image_containers_match_folder_prefixes_only():
    files = [
        {"path": "ui/units/icons/a.png", "container_name": "ui.pack"},
        {"path": "UI/Skins/default/b.png", "container_name": "ui2.pack"},
        {"path": "ui/units/icons_old/c.png", "container_name": "old.pack"},
        {"path": "db/main_units_tables/data__", "container_name": "db.pack"},
    ]
    assert image_containers(files, ["ui/units/icons", "ui/skins"]) == {"ui.pack", "ui2.pack"}
