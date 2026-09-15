from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..config import load_config
from .build import run


def main() -> None:
    ap = argparse.ArgumentParser(description="Build model/<build_id>/ from twwiki.duckdb")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_config(args.config)
    run(Path(cfg.paths.db_path), Path(getattr(cfg.paths, "model_dir", "./model")))


if __name__ == "__main__":
    main()
