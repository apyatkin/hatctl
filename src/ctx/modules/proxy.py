from __future__ import annotations

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class ProxyModule(Module):
    name = "proxy"
    order = 10

    def __init__(self):
        self._active = False

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return

        env_vars: dict[str, str] = {}
        if "http" in config:
            env_vars["HTTP_PROXY"] = config["http"]
            env_vars["http_proxy"] = config["http"]
        if "https" in config:
            env_vars["HTTPS_PROXY"] = config["https"]
            env_vars["https_proxy"] = config["https"]
        if "no_proxy" in config:
            env_vars["NO_PROXY"] = config["no_proxy"]
            env_vars["no_proxy"] = config["no_proxy"]

        if env_vars:
            self._active = True
            StateManager().merge_env(env_vars)

    def deactivate(self) -> None:
        self._active = False

    def status(self) -> ModuleStatus:
        if not self._active:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details="proxy configured")
