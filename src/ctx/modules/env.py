from __future__ import annotations

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class EnvModule(Module):
    name = "env"
    order = 8

    def __init__(self):
        self._vars: dict[str, str] = {}

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return
        self._vars = dict(config)
        sm = StateManager()
        existing: dict[str, str] = {}
        env_file = sm._env_file
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("export "):
                    key, _, val = line[7:].partition("=")
                    existing[key] = val.strip('"')
        existing.update(self._vars)
        sm.write_env(existing)

    def deactivate(self) -> None:
        self._vars = {}
        sm = StateManager()
        sm.clear_env()

    def status(self) -> ModuleStatus:
        if not self._vars:
            return ModuleStatus(active=False)
        var_names = ", ".join(sorted(self._vars.keys()))
        return ModuleStatus(active=True, details=var_names)
