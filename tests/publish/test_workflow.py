from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy.yml"


def load() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def steps() -> list[dict]:
    return load()["jobs"]["deploy"]["steps"]


def test_triggers_and_concurrency():
    workflow = load()
    on = workflow.get("on", workflow.get(True))  # PyYAML reads a bare `on` key as True
    build_id = on["workflow_dispatch"]["inputs"]["build_id"]
    assert build_id["required"] is False and build_id["type"] == "string"
    assert on["push"]["branches"] == ["main"]
    assert set(on["push"]["paths"]) == {
        "web/**", "firebase.json", ".firebaserc", "firestore.rules", "firestore.indexes.json",
        "storage.rules", ".github/workflows/deploy.yml"}
    assert workflow["concurrency"] == {"group": "deploy", "cancel-in-progress": False}
    assert workflow["permissions"] == {"contents": "read"}


def test_steps_run_in_order_with_pinned_tools():
    runs = [step.get("run", "") for step in steps()]

    def index(fragment: str) -> int:
        return next(i for i, run in enumerate(runs) if fragment in run)

    assert (index("npm ci") < index("fetch-snapshot.ts") < index("npm run build") < index("npm test")
            < index("firebase-tools@15.30.1 deploy") < index("curl"))
    assert "--only hosting,firestore:rules,firestore:indexes,storage" in "\n".join(runs)
    assert [step["uses"] for step in steps() if "uses" in step] == ["actions/checkout@v7", "actions/setup-node@v7"]
    cleanup = steps()[-1]
    assert cleanup["if"] == "always()" and "rm -f" in cleanup["run"]


def test_secrets_and_inputs_reach_scripts_only_through_env():
    for step in steps():
        run = step.get("run", "")
        assert "secrets." not in run and "inputs." not in run and "steps." not in run
