"""uv run python -m twwiki.publish [--build-id ID] [--no-deploy | --deploy-only | --prune ID | --write-indexes]"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError

from ..config import load_config
from . import PublishError
from .indexes import write_indexes
from .pipeline import Services, Settings, deploy_only, prune_build, publish


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m twwiki.publish",
        description="Publish a built model to Firebase and start the site deploy.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--build-id", help="model/<BUILD_ID> to publish, or the build to deploy "
                                           "(default: newest model / current build)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--no-deploy", action="store_true", help="publish without starting the deploy workflow")
    mode.add_argument("--deploy-only", action="store_true", help="only start the deploy workflow")
    mode.add_argument("--prune", metavar="BUILD_ID", help="delete one build's Firestore documents")
    mode.add_argument("--write-indexes", action="store_true", help="regenerate firestore.indexes.json and exit")
    return parser


def real_services(settings: Settings) -> Services:
    from .cloud import FirestoreEntityStore, GcsSnapshotStore, urllib_post

    return Services(
        entities=FirestoreEntityStore(settings.project_id),
        snapshots=GcsSnapshotStore(settings.project_id, settings.storage_bucket),
        post=urllib_post,
        token=os.environ.get("TWWIKI_GITHUB_TOKEN") or None,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("twwiki.publish")
    if args.write_indexes:
        log.info("wrote %s", write_indexes())
        return 0
    try:
        settings = Settings.from_config(load_config(args.config))
        services = real_services(settings)
        if args.prune:
            prune_build(settings, services, args.prune)
        elif args.deploy_only:
            log.info("deploy started: %s", deploy_only(settings, services, build_id=args.build_id))
        else:
            publish(settings, services, build_id=args.build_id, deploy=not args.no_deploy)
    except (PublishError, GoogleAPIError, GoogleAuthError) as e:
        log.error("%s", e)
        return 1
    except Exception as e:
        log.error("unexpected error: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
