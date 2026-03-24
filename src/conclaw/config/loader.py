import copy
import os
import json
from pathlib import Path

from conclaw.config.defaults import DEFAULT_CONFIG


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_toml(path: Path) -> dict:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_config() -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)

    global_config_path = Path.home() / ".conclaw" / "config.toml"
    if global_config_path.exists():
        config = _deep_merge(config, _load_toml(global_config_path))

    project_config_path = Path.cwd() / ".conclaw" / "project.json"
    if project_config_path.exists():
        with open(project_config_path, "r", encoding="utf-8") as f:
            config = _deep_merge(config, json.load(f))

    env_overrides = {
        "CONCLAW_MODEL": ("llm", "model"),
        "CONCLAW_LOG_LEVEL": ("logging", "level"),
    }
    for env_var, key_path in env_overrides.items():
        value = os.environ.get(env_var)
        if value:
            section, key = key_path
            config[section][key] = value

    return config
