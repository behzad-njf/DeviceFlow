"""Plugin discovery and in-process registry (SDK v1)."""
from __future__ import annotations

import importlib.util
import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from django.conf import settings

logger = logging.getLogger(__name__)

PLUGIN_API_VERSION = "1.0"


class Plugin(Protocol):
    id: str
    version: str

    def on_load(self, app_context: dict) -> None: ...

    def on_event(self, event: "DomainEvent") -> None: ...


@dataclass
class DomainEvent:
    type: str
    tenant_id: str
    payload: dict = field(default_factory=dict)
    project_id: str | None = None


@dataclass
class PluginManifest:
    id: str
    name: str
    version: str
    hooks: list[str]
    config_schema: dict
    plugin_api: str
    path: Path
    module: Any | None = None
    py_module: Any | None = None


class PluginRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._plugins: dict[str, PluginManifest] = {}
        self._discovered = False

    def discover(self, force: bool = False) -> list[PluginManifest]:
        with self._lock:
            if self._discovered and not force:
                return list(self._plugins.values())
            self._plugins.clear()
            roots = self._roots()
            for root in roots:
                if not root.exists():
                    continue
                for child in sorted(root.iterdir()):
                    manifest_path = child / "plugin.json"
                    if not manifest_path.is_file():
                        continue
                    try:
                        manifest = self._load_manifest(child, manifest_path)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Skip plugin %s: %s", child, exc)
                        continue
                    self._plugins[manifest.id] = manifest
            self._discovered = True
            return list(self._plugins.values())

    def _roots(self) -> list[Path]:
        configured = getattr(settings, "DEVICEFLOW_PLUGINS_DIRS", None)
        if configured:
            return [Path(p) for p in configured]
        # Default: <repo>/backend/plugins and <repo>/plugins
        backend_root = Path(settings.BASE_DIR)
        return [backend_root / "plugins", backend_root.parent / "plugins"]

    def _load_manifest(self, folder: Path, manifest_path: Path) -> PluginManifest:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        plugin_api = str(data.get("plugin_api") or PLUGIN_API_VERSION)
        if plugin_api.split(".")[0] != PLUGIN_API_VERSION.split(".")[0]:
            raise ValueError(f"Incompatible plugin_api {plugin_api}")
        entry = data.get("entry") or "plugin.py"
        module_path = folder / entry
        if not module_path.is_file():
            raise ValueError(f"Missing entry {entry}")
        spec = importlib.util.spec_from_file_location(
            f"deviceflow_plugin_{data['id'].replace('-', '_')}", module_path
        )
        if spec is None or spec.loader is None:
            raise ValueError("Cannot load plugin module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugin = getattr(module, "plugin", None) or getattr(module, "PLUGIN", None)
        if plugin is None:
            raise ValueError("Plugin module must export `plugin` or `PLUGIN`")
        plugin.on_load(
            {
                "plugin_api_version": PLUGIN_API_VERSION,
                "plugin_id": data["id"],
            }
        )
        return PluginManifest(
            id=str(data["id"]),
            name=str(data.get("name") or data["id"]),
            version=str(data.get("version") or "0.0.0"),
            hooks=list(data.get("hooks") or []),
            config_schema=dict(data.get("config_schema") or {}),
            plugin_api=plugin_api,
            path=folder,
            module=plugin,
            py_module=module,
        )

    def list(self) -> list[PluginManifest]:
        self.discover()
        return list(self._plugins.values())

    def get(self, plugin_id: str) -> PluginManifest | None:
        self.discover()
        return self._plugins.get(plugin_id)

    def dispatch(self, event: DomainEvent, *, installed_ids: set[str] | None = None) -> None:
        """Fan-out event to loaded plugins (optionally filtered by tenant installs)."""
        self.discover()
        for manifest in self._plugins.values():
            if installed_ids is not None and manifest.id not in installed_ids:
                continue
            plugin = manifest.module
            if plugin is None:
                continue
            try:
                plugin.on_event(event)
            except Exception:  # noqa: BLE001
                logger.exception("Plugin %s failed on %s", manifest.id, event.type)


_REGISTRY: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = PluginRegistry()
    return _REGISTRY
