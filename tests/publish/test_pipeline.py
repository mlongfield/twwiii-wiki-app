import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import PermissionDenied
from google.auth.exceptions import DefaultCredentialsError

from tests.publish.fakes import FakeEntityStore, FakePost, FakeSnapshotStore
from tests.publish.helpers import make_model
from twwiki.config import load_config
from twwiki.publish import PublishError, documents
from twwiki.publish import __main__ as cli
from twwiki.publish.pipeline import Services, Settings, deploy_only, publish, prune_build

UNIT = {"key": "u1", "name": "Unit One", "caste": "melee", "category": "inf", "unit_class": "inf_mel",
        "tier": 1, "is_naval": False, "abilities": [], "characters": [], "custom_battle_factions": [],
        "recruited_by_buildings": []}
NOW = "2026-09-16T12:00:00+00:00"


def settings_for(root: Path) -> Settings:
    return Settings(project_id="p", storage_bucket="bkt", repo="o/r", workflow="deploy.yml", ref="main",
                    model_root=root)


def make_services(token: str | None = "tok", post: FakePost | None = None,
                  snapshots: FakeSnapshotStore | None = None) -> Services:
    return Services(entities=FakeEntityStore(), snapshots=snapshots or FakeSnapshotStore(),
                    post=post or FakePost(), token=token, now=lambda: NOW)


def test_settings_from_the_repository_config():
    settings = Settings.from_config(load_config("config.yaml"))
    assert settings.project_id == "twwiii-wiki"
    assert settings.storage_bucket.startswith("twwiii-wiki.")
    assert (settings.repo, settings.workflow, settings.ref) == ("mlongfield/twwiii-wiki-app", "deploy.yml", "main")
    assert settings.model_root == Path("./model")


def test_settings_require_a_firebase_section():
    with pytest.raises(PublishError, match="no `firebase` section"):
        Settings.from_config(SimpleNamespace(paths=SimpleNamespace(model_dir="model")))


def test_publish_runs_every_step_and_switches_current_last(tmp_path):
    make_model(tmp_path, "b1", entities={"unit": [UNIT]})
    services = make_services()

    assert publish(settings_for(tmp_path), services) == "b1"

    assert "builds/b1/manifest.json" in services.snapshots.objects
    assert services.entities.docs["builds/b1/unit/u1"]["key"] == "u1"
    assert services.entities.docs["builds/b1"]["status"] == "ready"
    assert services.entities.docs["site/current"] == {
        "build_id": "b1", "previous_build_id": None, "model_version": 2, "published_at": NOW}
    calls = services.entities.calls
    last_count = max(i for i, call in enumerate(calls) if call[0] == "count")
    assert calls.index(("set", "site/current")) > last_count
    (url, _, body), = services.post.requests
    assert url.endswith("/repos/o/r/actions/workflows/deploy.yml/dispatches")
    assert json.loads(body) == {"ref": "main", "inputs": {"build_id": "b1"}}


def test_publish_without_deploy_needs_no_token(tmp_path):
    make_model(tmp_path, "b1")
    services = make_services(token=None)
    assert publish(settings_for(tmp_path), services, deploy=False) == "b1"
    assert services.post.requests == []
    assert services.entities.docs["site/current"]["build_id"] == "b1"


def test_publish_picks_the_newest_model_or_the_given_build(tmp_path):
    make_model(tmp_path, "b1", generated_at="2026-09-01T00:00:00+00:00")
    make_model(tmp_path, "b2", generated_at="2026-09-10T00:00:00+00:00")
    services = make_services()
    assert publish(settings_for(tmp_path), services, deploy=False) == "b2"
    assert publish(settings_for(tmp_path), services, build_id="b1", deploy=False) == "b1"
    assert services.entities.docs["site/current"]["previous_build_id"] == "b2"


def _preflight_failure(tmp_path, scenario):
    model_version = 1 if scenario == "version" else 2
    make_model(tmp_path, "b1", model_version=model_version)
    services = make_services(token=None if scenario == "token" else "tok",
                             snapshots=FakeSnapshotStore(exists=scenario != "bucket"))
    if scenario == "credentials":
        services.entities.fail_get = DefaultCredentialsError("no application default credentials")
    if scenario == "permission":
        services.entities.fail_get = PermissionDenied("denied")
    return services


@pytest.mark.parametrize("scenario, message", [
    ("version", "model_version 1, expected 2"),
    ("token", "TWWIKI_GITHUB_TOKEN is not set"),
    ("credentials", "gcloud auth application-default login"),
    ("permission", "gcloud auth application-default login"),
    ("bucket", "bucket bkt not found"),
])
def test_preflight_failures_write_nothing(tmp_path, scenario, message):
    services = _preflight_failure(tmp_path, scenario)
    with pytest.raises(PublishError, match=message):
        publish(settings_for(tmp_path), services)
    assert services.snapshots.objects == {}
    assert not [call for call in services.entities.calls if call[0] != "get"]
    assert services.post.requests == []


def test_derived_field_collision_stops_preflight(tmp_path, monkeypatch):
    make_model(tmp_path, "b1")
    monkeypatch.setitem(documents.INDEX_FIELDS, "unit", ["abilities_keys"])
    services = make_services()
    with pytest.raises(PublishError, match="clash"):
        publish(settings_for(tmp_path), services)
    assert services.snapshots.objects == {}


def test_count_mismatch_leaves_the_live_build_untouched(tmp_path):
    make_model(tmp_path, "b1", entities={"unit": [UNIT]})
    services = make_services()
    services.entities.docs["site/current"] = {"build_id": "b0", "previous_build_id": None}
    services.entities.count_override["builds/b1/unit"] = 5
    with pytest.raises(PublishError, match="unit 5 \\(expected 1\\)"):
        publish(settings_for(tmp_path), services)
    assert services.entities.docs["site/current"]["build_id"] == "b0"
    assert services.entities.docs["builds/b1"]["status"] == "loading"
    assert services.post.requests == []


def test_dispatch_failure_happens_after_go_live(tmp_path):
    make_model(tmp_path, "b1")
    services = make_services(post=FakePost(401))
    with pytest.raises(PublishError, match="--deploy-only"):
        publish(settings_for(tmp_path), services)
    assert services.entities.docs["site/current"]["build_id"] == "b1"


def test_deploy_only(tmp_path):
    services = make_services()
    with pytest.raises(PublishError, match="names no build"):
        deploy_only(settings_for(tmp_path), services)
    services.entities.docs["site/current"] = {"build_id": "b1"}
    services.entities.docs["builds/b1"] = {"status": "ready"}
    services.entities.docs["builds/b0"] = {"status": "loading"}
    assert deploy_only(settings_for(tmp_path), services).endswith("/actions/workflows/deploy.yml")
    assert json.loads(services.post.requests[0][2])["inputs"] == {"build_id": "b1"}
    with pytest.raises(PublishError, match="not ready \\(status: loading\\)"):
        deploy_only(settings_for(tmp_path), services, build_id="b0")
    with pytest.raises(PublishError, match="not ready \\(status: missing\\)"):
        deploy_only(settings_for(tmp_path), services, build_id="b9")
    with pytest.raises(PublishError, match="TWWIKI_GITHUB_TOKEN is not set"):
        deploy_only(settings_for(tmp_path), make_services(token=None))


def test_prune_build(tmp_path):
    services = make_services()
    services.entities.docs["site/current"] = {"build_id": "b2", "previous_build_id": "b1"}
    services.entities.docs["builds/b0"] = {"status": "ready"}
    prune_build(settings_for(tmp_path), services, "b0")
    assert "builds/b0" not in services.entities.docs


def test_cli_modes_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--no-deploy", "--deploy-only"])
    args = cli.build_parser().parse_args(["--prune", "b0"])
    assert args.prune == "b0" and not args.no_deploy


def test_cli_write_indexes():
    assert cli.main(["--write-indexes"]) == 0


def test_cli_reports_publish_errors_with_exit_code_1(tmp_path, monkeypatch, caplog):
    config = tmp_path / "config.yaml"
    config.write_text(
        "game: warhammer_3\n"
        f"paths:\n  model_dir: '{(tmp_path / 'no-models').as_posix()}'\n"
        "firebase:\n  project_id: p\n  storage_bucket: bkt\n"
        "  deploy_workflow: {repo: o/r, workflow: deploy.yml, ref: main}\n",
        encoding="utf-8")
    monkeypatch.setattr(cli, "real_services", lambda settings: make_services())
    assert cli.main(["--config", str(config), "--no-deploy"]) == 1
    assert "no model found" in caplog.text
