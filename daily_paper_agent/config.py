from __future__ import annotations

import os
from pathlib import Path

import yaml


def load_config(path: str | Path) -> dict:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    required = ["schedule", "research", "quality", "llm", "feishu", "state"]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing config sections: {', '.join(missing)}")

    config["llm"]["api_key"] = os.getenv(config["llm"]["api_key_env"], "")
    config["feishu"]["webhook_url"] = os.getenv(config["feishu"]["webhook_env"], "")
    config["_root"] = str(config_path.resolve().parent)
    return config

