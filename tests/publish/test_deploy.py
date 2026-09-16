import json

import pytest

from tests.publish.fakes import FakePost
from twwiki.publish import PublishError
from twwiki.publish.deploy import dispatch_deploy

ARGS = dict(repo="mlongfield/twwiii-wiki-app", workflow="deploy.yml", ref="main", build_id="b1", token="tok")


def test_dispatch_sends_the_workflow_dispatch_request():
    post = FakePost(204)
    url = dispatch_deploy(post, **ARGS)
    assert url == "https://github.com/mlongfield/twwiii-wiki-app/actions/workflows/deploy.yml"
    (request_url, headers, body), = post.requests
    assert request_url == ("https://api.github.com/repos/mlongfield/twwiii-wiki-app"
                           "/actions/workflows/deploy.yml/dispatches")
    assert headers["Authorization"] == "Bearer tok"
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert headers["Content-Type"] == "application/json"
    assert json.loads(body) == {"ref": "main", "inputs": {"build_id": "b1"}}


def test_dispatch_accepts_200():
    assert dispatch_deploy(FakePost(200), **ARGS).endswith("deploy.yml")


@pytest.mark.parametrize("status, hint", [
    (401, "token"), (403, "token"), (404, "deploy.yml"), (422, "HTTP 422")])
def test_dispatch_failures_explain_and_name_deploy_only(status, hint):
    with pytest.raises(PublishError) as excinfo:
        dispatch_deploy(FakePost(status), **ARGS)
    message = str(excinfo.value)
    assert hint in message
    assert "--deploy-only" in message
    assert "previous pages" in message


def test_dispatch_network_error():
    with pytest.raises(PublishError, match="could not reach GitHub"):
        dispatch_deploy(FakePost(error=OSError("offline")), **ARGS)
