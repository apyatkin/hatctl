"""Consistent colored output helpers + shared rendering / humanize utilities."""

from __future__ import annotations

import json as _json
from typing import Any

import click


# ─── Legacy simple helpers (used by modules/*, cli_ssh, etc) ──────────────


def header(text: str):
    click.echo(click.style(f"\n  {text}", bold=True))


def item(name: str, value: str, width: int = 20):
    click.echo(f"    {name:<{width}} {value}")


def ok(text: str):
    click.echo(f"    {click.style('OK', fg='green')}  {text}")


def warn(text: str):
    click.echo(f"    {click.style('WARN', fg='yellow')}  {text}")


def fail(text: str):
    click.echo(f"    {click.style('FAIL', fg='red')}  {text}")


def status_badge(label: str, active: bool) -> str:
    color = "green" if active else "red"
    state = "active" if active else "inactive"
    return f"{label} [{click.style(state, fg=color)}]"


# ─── Rich table renderers (shared by cli_inspect and cli_whatsup) ─────────


def render_table(
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    json_mode: bool = False,
) -> None:
    """Render a table of rows. In JSON mode, emits a single JSON object."""
    if json_mode:
        out = {
            "title": title,
            "columns": columns,
            "rows": [{col: row[i] for i, col in enumerate(columns)} for row in rows],
        }
        click.echo(_json.dumps(out, indent=2, default=str))
        return

    from rich.console import Console
    from rich.table import Table

    table = Table(title=title, header_style="bold cyan", title_style="bold")
    for col in columns:
        table.add_column(col, overflow="fold")
    for row in rows:
        table.add_row(*[str(c) for c in row])
    Console().print(table)


def render_kv(
    title: str,
    pairs: list[tuple[str, Any]],
    json_mode: bool = False,
) -> None:
    """Render a key/value two-column table."""
    if json_mode:
        click.echo(
            _json.dumps({"title": title, "data": dict(pairs)}, indent=2, default=str)
        )
        return

    from rich.console import Console
    from rich.table import Table

    table = Table(title=title, header_style="bold cyan", title_style="bold")
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    for k, v in pairs:
        table.add_row(str(k), str(v))
    Console().print(table)


# ─── Humanize / parsing helpers ───────────────────────────────────────────


def human_bytes(n: float) -> str:
    """Format a byte count like 1536000 -> '1.5 MB'."""
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} EB"


def human_kib(value: str) -> str:
    """Convert a string of KiB (e.g. '131548412') to human-readable bytes."""
    try:
        kb = float(value)
    except (ValueError, TypeError):
        return value
    return human_bytes(kb * 1024)


def humanize_k8s_memory(value: str) -> str:
    """Convert a Kubernetes resource quantity like '131548412Ki' to '125.5 GB'."""
    if not value or value == "?":
        return value
    v = value.strip()
    binary = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4, "Pi": 1024**5}
    decimal = {"K": 1000, "M": 1000**2, "G": 1000**3, "T": 1000**4, "P": 1000**5}

    try:
        for suffix, mult in binary.items():
            if v.endswith(suffix):
                return human_bytes(float(v[: -len(suffix)]) * mult)
        for suffix, mult in decimal.items():
            if v.endswith(suffix):
                return human_bytes(float(v[: -len(suffix)]) * mult)
        return human_bytes(float(v))
    except ValueError:
        return value


def parse_sections(text: str) -> dict[str, str]:
    """Parse text blocks separated by '===NAME===' markers.

    Used by cli_inspect and cli_whatsup to bundle multiple remote commands
    in a single SSH round-trip and split the output server-side.
    """
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("===") and line.endswith("==="):
            if current is not None:
                sections[current] = "\n".join(buf)
            current = line.strip("=")
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


def parse_meminfo(text: str) -> dict[str, str]:
    """Parse /proc/meminfo output into a dict of human-readable values.

    Adds derived keys MemUsed and SwapUsed when MemTotal/MemAvailable
    and SwapTotal/SwapFree are present.
    """
    raw: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        parts = v.strip().split()
        if parts and parts[0].isdigit():
            raw[k.strip()] = int(parts[0])  # value is in kB

    out = {k: human_kib(str(v)) for k, v in raw.items()}
    if "MemTotal" in raw and "MemAvailable" in raw:
        out["MemUsed"] = human_kib(str(raw["MemTotal"] - raw["MemAvailable"]))
    if "SwapTotal" in raw and "SwapFree" in raw:
        out["SwapUsed"] = human_kib(str(raw["SwapTotal"] - raw["SwapFree"]))
    return out
