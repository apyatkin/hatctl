from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import click

from hat.config import get_config_dir
from hat.modules import Module, ModuleStatus

THROTTLE_SECONDS = 86400


class ToolsModule(Module):
    name = "tools"
    order = 0

    def __init__(self):
        self._installed: list[str] = []
        self._updated: list[str] = []
        self._already_ok: list[str] = []

    def activate(self, config: dict, secrets: dict) -> None:
        brew_tools = config.get("brew", [])
        pipx_tools = config.get("pipx", [])
        if not brew_tools and not pipx_tools:
            return

        state = self._load_state()
        now = time.time()

        brew_outdated: set[str] | None = None
        tools_to_check = [t for t in brew_tools if shutil.which(t) and self._should_check(t, state, now)]
        if tools_to_check:
            result = subprocess.run(["brew", "outdated", "--quiet"], capture_output=True, text=True)
            brew_outdated = set(result.stdout.split())

        for tool in brew_tools:
            self._ensure_brew(tool, state, now, brew_outdated)

        for tool in pipx_tools:
            self._ensure_pipx(tool, state, now)

        self._save_state(state)

        parts = []
        if self._installed:
            parts.append(f"installed {len(self._installed)}")
        if self._updated:
            parts.append(f"updated {len(self._updated)}")
        if self._already_ok:
            parts.append(f"{len(self._already_ok)} up to date")
        if parts:
            click.echo(f"Tools: {', '.join(parts)}")

    def _ensure_brew(self, tool: str, state: dict, now: float, outdated: set[str] | None = None) -> None:
        if shutil.which(tool) is None:
            subprocess.run(["brew", "install", tool], capture_output=True, text=True)
            self._installed.append(tool)
            state[tool] = now
        elif self._should_check(tool, state, now) and outdated is not None:
            if tool in outdated:
                subprocess.run(["brew", "upgrade", tool], capture_output=True, text=True)
                self._updated.append(tool)
            else:
                self._already_ok.append(tool)
            state[tool] = now
        else:
            self._already_ok.append(tool)

    def _ensure_pipx(self, tool: str, state: dict, now: float) -> None:
        if shutil.which(tool) is None:
            subprocess.run(
                ["uv", "tool", "install", tool],
                capture_output=True, text=True,
            )
            self._installed.append(tool)
            state[tool] = now
        elif self._should_check(tool, state, now):
            result = subprocess.run(
                ["uv", "tool", "upgrade", tool],
                capture_output=True, text=True,
            )
            if "already" not in result.stdout.lower():
                self._updated.append(tool)
            else:
                self._already_ok.append(tool)
            state[tool] = now
        else:
            self._already_ok.append(tool)

    def _should_check(self, tool: str, state: dict, now: float) -> bool:
        last_check = state.get(tool, 0)
        return (now - last_check) > THROTTLE_SECONDS

    def _load_state(self) -> dict:
        state_file = get_config_dir() / "tools_state.json"
        if state_file.exists():
            return json.loads(state_file.read_text())
        return {}

    def _save_state(self, state: dict) -> None:
        state_file = get_config_dir() / "tools_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2) + "\n")

    def deactivate(self) -> None:
        pass  # no-op: don't uninstall tools

    def status(self) -> ModuleStatus:
        total = len(self._installed) + len(self._updated) + len(self._already_ok)
        if total == 0:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=f"{total} tools managed")
