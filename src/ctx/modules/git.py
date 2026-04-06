from __future__ import annotations

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class GitModule(Module):
    name = "git"
    order = 6

    def __init__(self):
        self._identity: dict[str, str] | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        identity = config.get("identity")
        if not identity:
            return
        self._identity = identity
        env_vars = {
            "GIT_AUTHOR_NAME": identity["name"],
            "GIT_AUTHOR_EMAIL": identity["email"],
            "GIT_COMMITTER_NAME": identity["name"],
            "GIT_COMMITTER_EMAIL": identity["email"],
        }
        StateManager().merge_env(env_vars)

    def deactivate(self) -> None:
        self._identity = None

    def status(self) -> ModuleStatus:
        if not self._identity:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=f"{self._identity['name']} <{self._identity['email']}>",
        )
