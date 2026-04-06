from __future__ import annotations

from pathlib import Path

import click

from hat.modules import Module, ModuleStatus

MARKER_START = "# >>> ctx-managed >>>"
MARKER_END = "# <<< ctx-managed <<<"
DEFAULT_HOSTS_PATH = Path("/etc/hosts")


class HostsModule(Module):
    name = "hosts"
    order = 4

    def __init__(self, hosts_path: Path | None = None):
        self._hosts_path = hosts_path or DEFAULT_HOSTS_PATH
        self._entries: list[str] = []

    def activate(self, config: dict, secrets: dict) -> None:
        entries = config.get("entries", [])
        if not entries:
            return
        self._entries = entries

        block = f"{MARKER_START}\n" + "\n".join(entries) + f"\n{MARKER_END}\n"
        content = self._hosts_path.read_text()
        content = self._remove_block(content)

        if self._hosts_path == DEFAULT_HOSTS_PATH:
            click.confirm(
                f"Will add {len(entries)} entries to /etc/hosts\nProceed?",
                default=True,
                abort=True,
            )

        self._hosts_path.write_text(content.rstrip("\n") + "\n" + block)

    def deactivate(self) -> None:
        if not self._entries:
            return
        content = self._hosts_path.read_text()
        content = self._remove_block(content)
        self._hosts_path.write_text(content)
        self._entries = []

    def _remove_block(self, content: str) -> str:
        lines = content.splitlines(keepends=True)
        result = []
        in_block = False
        for line in lines:
            if line.strip() == MARKER_START:
                in_block = True
                continue
            if line.strip() == MARKER_END:
                in_block = False
                continue
            if not in_block:
                result.append(line)
        return "".join(result)

    def status(self) -> ModuleStatus:
        if not self._entries:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=f"{len(self._entries)} entries",
        )
