from __future__ import annotations

import subprocess

from ctx.modules import Module, ModuleStatus


class SSHModule(Module):
    name = "ssh"
    order = 5

    def __init__(self):
        self._keys: list[str] = []
        self._config_snippet: str | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        self._keys = config.get("keys", [])
        self._config_snippet = config.get("config")

        for key in self._keys:
            subprocess.run(["ssh-add", key], capture_output=True, text=True)

    def deactivate(self) -> None:
        for key in self._keys:
            subprocess.run(["ssh-add", "-d", key], capture_output=True, text=True)
        self._keys = []
        self._config_snippet = None

    def status(self) -> ModuleStatus:
        if not self._keys:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=f"{len(self._keys)} key(s) loaded",
        )
