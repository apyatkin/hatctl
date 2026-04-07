from __future__ import annotations

from hat.modules import Module, ModuleStatus
from hat.state import StateManager


class GitModule(Module):
    name = "git"
    order = 6

    def __init__(self):
        self._identity: dict[str, str] | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        env_vars: dict[str, str] = {}

        identity = config.get("identity")
        if identity and identity.get("name"):
            self._identity = identity
            env_vars["GIT_AUTHOR_NAME"] = identity["name"]
            env_vars["GIT_AUTHOR_EMAIL"] = identity["email"]
            env_vars["GIT_COMMITTER_NAME"] = identity["name"]
            env_vars["GIT_COMMITTER_EMAIL"] = identity["email"]

        # Export git source URLs and tokens as env vars
        for i, source in enumerate(config.get("sources", [])):
            provider = source.get("provider", "")
            if provider == "gitlab":
                host = source.get("host", "")
                if host:
                    env_vars["GITLAB_URL"] = f"https://{host}"
                    env_vars["GITLAB_HOST"] = host
                token_ref = source.get("token_ref")
                if token_ref and token_ref in secrets:
                    env_vars["GITLAB_TOKEN"] = secrets[token_ref]
            elif provider == "github":
                org = source.get("org", "")
                if org:
                    env_vars["GITHUB_ORG"] = org
                token_ref = source.get("token_ref")
                if token_ref and token_ref in secrets:
                    env_vars["GITHUB_TOKEN"] = secrets[token_ref]

        if env_vars:
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
