from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded."""


def _resolve_env(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_key = value[2:-1]
        return os.getenv(env_key, "")
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(item) for item in value]
    return value


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing configuration file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return _resolve_env(data)


@lru_cache(maxsize=4)
def load_app_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load the primary application config."""

    path = Path(config_path or "configs/app.yaml")
    return _load_yaml(path)


@lru_cache(maxsize=4)
def load_sources_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load the niche sources configuration."""

    path = Path(config_path or "configs/niche_sources.yaml")
    return _load_yaml(path)


def cache_directory() -> Path:
    """Ensure the cache directory exists and return its path."""

    config = load_app_config()
    cache_dir = Path(config.get("cache_dir", "./.cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
