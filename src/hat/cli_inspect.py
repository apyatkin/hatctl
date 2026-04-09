"""Remote host inspection commands — CPU, memory, disk, network, logs."""

from __future__ import annotations

import json as _json
import shlex
import subprocess
import sys
from dataclasses import dataclass

import click

from hat.config import load_company_config
from hat.output import (
    human_bytes as _human_bytes,
    human_kib as _human_kib,
    parse_meminfo as _parse_meminfo,
    parse_sections as _parse_sections,
    render_kv as _render_kv,
    render_table as _render_table,
)


# ─── SSH target resolution ─────────────────────────────────────────────────


@dataclass
class SSHTarget:
    host: str
    user: str | None = None
    port: int | None = None
    key: str | None = None
    jump: str | None = None

    def ssh_cmd(self) -> list[str]:
        cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=10",
        ]
        if self.jump:
            cmd.extend(["-J", self.jump])
        if self.key:
            cmd.extend(["-i", self.key, "-o", "IdentitiesOnly=yes"])
        if self.port:
            cmd.extend(["-p", str(self.port)])
        target = f"{self.user}@{self.host}" if self.user else self.host
        cmd.append(target)
        return cmd


def _resolve_target(
    remote: str,
    user_override: str | None,
    port_override: int | None,
    key_override: str | None,
) -> SSHTarget:
    """Resolve a remote spec.

    `remote` can be:
      - a raw IP/hostname (uses defaults)
      - a host alias from any company's ssh.hosts
      - 'company:host' for explicit lookup
    """
    from hat.config import list_companies

    # Explicit company:host form
    company = None
    host_name = remote
    if ":" in remote and "/" not in remote:
        company, host_name = remote.split(":", 1)

    candidates = [company] if company else list_companies()

    target: SSHTarget | None = None
    for cname in candidates:
        try:
            cfg = load_company_config(cname)
        except Exception:
            continue
        ssh_cfg = cfg.get("ssh", {}) or {}
        hosts = ssh_cfg.get("hosts", {}) or {}
        if host_name not in hosts:
            continue
        entry = hosts[host_name]
        target = SSHTarget(
            host=entry["address"],
            user=entry.get("user") or ssh_cfg.get("default_user"),
            port=entry.get("port"),
        )
        # Resolve key from keychain ref if any
        key_ref = entry.get("key_ref") or ssh_cfg.get("default_key_ref")
        if key_ref:
            target.key = _materialize_key(key_ref)
        # Jump host
        if ssh_cfg.get("jump_host"):
            jh = ssh_cfg["jump_host"]
            ju = ssh_cfg.get("jump_user")
            target.jump = f"{ju}@{jh}" if ju else jh
        break

    if target is None:
        # Treat as raw IP/hostname
        target = SSHTarget(host=remote)

    # Apply overrides
    if user_override:
        target.user = user_override
    if port_override:
        target.port = port_override
    if key_override:
        # User-supplied path takes precedence; no temp file
        target.key = key_override

    return target


_KEY_TEMP_PATHS: list[str] = []


def _materialize_key(key_ref: str) -> str | None:
    """Resolve a hat secret ref (e.g. 'keychain:foo') to a temp file path."""
    import os
    import tempfile
    import atexit

    from hat.secrets import SecretResolver

    try:
        data = SecretResolver()._resolve_one(key_ref)
    except Exception:
        return None

    fd, path = tempfile.mkstemp(prefix="hat-inspect-", suffix=".key")
    payload = data if data.endswith("\n") else data + "\n"
    os.write(fd, payload.encode())
    os.close(fd)
    os.chmod(path, 0o600)
    _KEY_TEMP_PATHS.append(path)
    if len(_KEY_TEMP_PATHS) == 1:
        atexit.register(_cleanup_keys)
    return path


def _cleanup_keys():
    import os

    for p in _KEY_TEMP_PATHS:
        try:
            os.unlink(p)
        except OSError:
            pass


# ─── Remote command execution ──────────────────────────────────────────────


def _run_remote(target: SSHTarget, remote_cmd: str) -> str:
    """Run a shell command on the remote host, return stdout."""
    cmd = target.ssh_cmd() + [remote_cmd]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
    except subprocess.TimeoutExpired:
        click.echo(f"Error: SSH timeout connecting to {target.host}", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo("Error: ssh binary not found", err=True)
        sys.exit(1)

    if result.returncode != 0:
        click.echo(f"Error: remote command failed (exit {result.returncode})", err=True)
        if result.stderr:
            click.echo(result.stderr.strip(), err=True)
        sys.exit(result.returncode)
    return result.stdout


# ─── Common option set ─────────────────────────────────────────────────────


def _remote_options(f):
    f = click.option(
        "-r",
        "--remote",
        required=True,
        help="Remote host (IP, hostname, or alias from any company's ssh.hosts; use 'company:host' for explicit lookup)",
    )(f)
    f = click.option("-u", "--user", default=None, help="SSH user override")(f)
    f = click.option("-p", "--port", type=int, default=None, help="SSH port override")(
        f
    )
    f = click.option(
        "-i",
        "--private-key",
        "private_key",
        type=click.Path(exists=True, dir_okay=False),
        default=None,
        help="Path to SSH private key",
    )(f)
    f = click.option("--json", "json_out", is_flag=True, help="Output as JSON")(f)
    return f


# ─── Inspect group ─────────────────────────────────────────────────────────


@click.group("inspect")
def inspect_group():
    """Remote host inspection — performance, services, logs, health.

    \b
    Performance:
      hat inspect cpu     -r bastion        # top CPU processes
      hat inspect mem     -r bastion        # memory + top RSS
      hat inspect disk    -r bastion        # df per filesystem
      hat inspect io      -r bastion        # disk I/O (1s sample)
      hat inspect net     -r bastion        # throughput + TCP states
      hat inspect load    -r bastion        # load / uptime
      hat inspect sys     -r bastion        # full overview
      hat inspect hw      -r bastion        # CPU/RAM/disks/temps

    \b
    State:
      hat inspect services   -r bastion     # systemd units + failed
      hat inspect listen     -r bastion     # listening ports
      hat inspect who        -r bastion     # sessions + logins
      hat inspect proc       -r bastion nginx
      hat inspect containers -r bastion     # docker + nomad
      hat inspect updates    -r bastion     # pending + reboot
      hat inspect security   -r bastion     # failed logins, fw
      hat inspect health     -r bastion     # aggregate, exits 2 on ALERT

    \b
    Logs:
      hat inspect logs  -r bastion --errors --last 1h
      hat inspect dmesg -r bastion --errors --last 1h

    \b
    Host resolution (-r):
      IP/hostname         raw connection
      <alias>             lookup in any company's ssh.hosts
      <company>:<alias>   explicit company lookup
    """


# ─── cpu ───────────────────────────────────────────────────────────────────


@inspect_group.command("cpu")
@_remote_options
def cpu_cmd(remote, user, port, private_key, json_out):
    """Top 10 processes by CPU usage."""
    target = _resolve_target(remote, user, port, private_key)
    cmd = (
        "ps -eo pid,user,pcpu,pmem,rss,comm --sort=-pcpu --no-headers 2>/dev/null "
        "| head -10"
    )
    out = _run_remote(target, cmd)
    rows = []
    for line in out.strip().splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        pid, user_, pcpu, pmem, rss, comm = parts
        rows.append([pid, user_, f"{pcpu}%", f"{pmem}%", _human_kib(rss), comm])
    _render_table(
        f"Top 10 processes by CPU on {target.host}",
        ["PID", "USER", "CPU", "MEM", "RSS", "COMMAND"],
        rows,
        json_out,
    )


# ─── mem ───────────────────────────────────────────────────────────────────


@inspect_group.command("mem")
@_remote_options
def mem_cmd(remote, user, port, private_key, json_out):
    """Top 10 processes by memory + memory totals."""
    target = _resolve_target(remote, user, port, private_key)

    # Top 10 processes by RSS
    proc_out = _run_remote(
        target,
        "ps -eo pid,user,pcpu,pmem,rss,comm --sort=-rss --no-headers 2>/dev/null | head -10",
    )
    rows = []
    for line in proc_out.strip().splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        pid, user_, pcpu, pmem, rss, comm = parts
        rows.append([pid, user_, f"{pcpu}%", f"{pmem}%", _human_kib(rss), comm])

    # Memory totals
    mem_info = _parse_meminfo(_run_remote(target, "cat /proc/meminfo 2>/dev/null"))

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "memory": mem_info,
                    "top_processes": [
                        dict(zip(["PID", "USER", "CPU", "MEM", "RSS", "COMMAND"], r))
                        for r in rows
                    ],
                },
                indent=2,
            )
        )
        return

    _render_kv(
        f"Memory on {target.host}",
        [
            ("Total", mem_info.get("MemTotal", "?")),
            ("Used", mem_info.get("MemUsed", "?")),
            ("Free", mem_info.get("MemFree", "?")),
            ("Available", mem_info.get("MemAvailable", "?")),
            ("Buffers", mem_info.get("Buffers", "?")),
            ("Cached", mem_info.get("Cached", "?")),
            ("Swap Total", mem_info.get("SwapTotal", "?")),
            ("Swap Used", mem_info.get("SwapUsed", "?")),
        ],
    )
    _render_table(
        "Top 10 processes by memory",
        ["PID", "USER", "CPU", "MEM", "RSS", "COMMAND"],
        rows,
    )


# ─── disk ──────────────────────────────────────────────────────────────────


@inspect_group.command("disk")
@_remote_options
def disk_cmd(remote, user, port, private_key, json_out):
    """Disk usage per filesystem."""
    target = _resolve_target(remote, user, port, private_key)
    out = _run_remote(
        target,
        "df -PT -x tmpfs -x devtmpfs -x squashfs -x overlay 2>/dev/null | tail -n +2",
    )
    rows = []
    for line in out.strip().splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        fs, fstype, size, used, avail, pct, mount = parts[:7]
        rows.append(
            [
                fs,
                fstype,
                _human_kib(size),
                _human_kib(used),
                _human_kib(avail),
                pct,
                mount,
            ]
        )
    _render_table(
        f"Disk usage on {target.host}",
        ["Filesystem", "Type", "Size", "Used", "Avail", "Use%", "Mount"],
        rows,
        json_out,
    )


# ─── io ────────────────────────────────────────────────────────────────────


@inspect_group.command("io")
@_remote_options
def io_cmd(remote, user, port, private_key, json_out):
    """Disk I/O activity (1-second sample of /proc/diskstats)."""
    target = _resolve_target(remote, user, port, private_key)
    # Two snapshots joined with a literal '|' so we can split reliably
    cmd = (
        "awk '{print}' /proc/diskstats; echo '---SPLIT---'; "
        "sleep 1; awk '{print}' /proc/diskstats"
    )
    out = _run_remote(target, cmd)
    if "---SPLIT---" not in out:
        click.echo("Error: could not collect diskstats", err=True)
        sys.exit(1)
    snap1, snap2 = out.split("---SPLIT---", 1)

    def parse(text: str) -> dict[str, tuple[int, int]]:
        result: dict[str, tuple[int, int]] = {}
        for line in text.strip().splitlines():
            cols = line.split()
            if len(cols) < 14:
                continue
            dev = cols[2]
            try:
                # Field offsets per Documentation/admin-guide/iostats.rst:
                #   cols[3..]  → reads_completed, reads_merged, sectors_read, ...
                #   cols[5]   = sectors read; cols[9] = sectors written
                sectors_read = int(cols[5])
                sectors_written = int(cols[9])
            except (ValueError, IndexError):
                continue
            result[dev] = (sectors_read, sectors_written)
        return result

    s1 = parse(snap1)
    s2 = parse(snap2)
    rows = []
    for dev in sorted(s2.keys()):
        if dev.startswith(("loop", "ram", "dm-")):
            continue
        if dev not in s1:
            continue
        # 512-byte sectors → KB/s
        rkb = (s2[dev][0] - s1[dev][0]) // 2
        wkb = (s2[dev][1] - s1[dev][1]) // 2
        if rkb == 0 and wkb == 0:
            continue
        rows.append([dev, f"{rkb} KB/s", f"{wkb} KB/s"])

    if not rows:
        rows = [["(idle)", "0 KB/s", "0 KB/s"]]
    _render_table(
        f"Disk I/O on {target.host} (1s sample)",
        ["Device", "Read", "Write"],
        rows,
        json_out,
    )


# ─── net ───────────────────────────────────────────────────────────────────


@inspect_group.command("net")
@_remote_options
def net_cmd(remote, user, port, private_key, json_out):
    """Network interfaces, connections, throughput (1s sample)."""
    target = _resolve_target(remote, user, port, private_key)

    # Interface throughput from /proc/net/dev
    cmd = "cat /proc/net/dev; echo '---SPLIT---'; sleep 1; cat /proc/net/dev"
    out = _run_remote(target, cmd)
    if "---SPLIT---" not in out:
        click.echo("Error: could not collect /proc/net/dev", err=True)
        sys.exit(1)
    snap1, snap2 = out.split("---SPLIT---", 1)

    def parse_netdev(text: str) -> dict[str, tuple[int, int]]:
        result: dict[str, tuple[int, int]] = {}
        for line in text.strip().splitlines():
            if ":" not in line:
                continue
            iface, _, stats = line.partition(":")
            iface = iface.strip()
            cols = stats.split()
            if len(cols) < 16:
                continue
            try:
                rx_bytes = int(cols[0])
                tx_bytes = int(cols[8])
            except ValueError:
                continue
            result[iface] = (rx_bytes, tx_bytes)
        return result

    s1 = parse_netdev(snap1)
    s2 = parse_netdev(snap2)
    rows = []
    for iface in sorted(s2.keys()):
        if iface == "lo":
            continue
        if iface not in s1:
            continue
        rx_diff = s2[iface][0] - s1[iface][0]
        tx_diff = s2[iface][1] - s1[iface][1]
        if rx_diff == 0 and tx_diff == 0:
            continue
        rows.append([iface, _human_bytes(rx_diff), _human_bytes(tx_diff)])

    # Established connection count
    conn_out = _run_remote(
        target, "ss -tan 2>/dev/null | awk 'NR>1 {print $1}' | sort | uniq -c"
    )
    conn_pairs = []
    for line in conn_out.strip().splitlines():
        parts = line.split()
        if len(parts) == 2:
            conn_pairs.append((parts[1], int(parts[0])))

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "interfaces": [
                        {"iface": r[0], "rx_per_sec": r[1], "tx_per_sec": r[2]}
                        for r in rows
                    ],
                    "connections": dict(conn_pairs),
                },
                indent=2,
            )
        )
        return

    _render_table(
        f"Network throughput on {target.host} (1s sample)",
        ["Interface", "RX/s", "TX/s"],
        rows or [["(none)", "-", "-"]],
    )
    if conn_pairs:
        _render_table(
            "TCP connections by state",
            ["State", "Count"],
            [[s, c] for s, c in conn_pairs],
        )


# ─── load ──────────────────────────────────────────────────────────────────


@inspect_group.command("load")
@_remote_options
def load_cmd(remote, user, port, private_key, json_out):
    """Load average, uptime, CPU count."""
    target = _resolve_target(remote, user, port, private_key)
    out = _run_remote(
        target,
        "uptime; nproc 2>/dev/null; cat /proc/loadavg 2>/dev/null",
    )
    lines = out.strip().splitlines()
    pairs = []
    if lines:
        pairs.append(("uptime", lines[0].strip()))
    if len(lines) >= 2:
        pairs.append(("CPU cores", lines[1].strip()))
    if len(lines) >= 3:
        la = lines[2].split()
        if len(la) >= 5:
            pairs.append(("load 1m", la[0]))
            pairs.append(("load 5m", la[1]))
            pairs.append(("load 15m", la[2]))
            pairs.append(("running/total tasks", la[3]))
            pairs.append(("last PID", la[4]))
    _render_kv(f"Load on {target.host}", pairs, json_out)


# ─── sys ───────────────────────────────────────────────────────────────────


@inspect_group.command("sys")
@_remote_options
def sys_cmd(remote, user, port, private_key, json_out):
    """Full system overview — load, mem, disk, network, top processes."""
    target = _resolve_target(remote, user, port, private_key)

    # Single round-trip for everything
    script = """
echo '===HOSTNAME==='; hostname
echo '===UPTIME==='; uptime
echo '===KERNEL==='; uname -sr
echo '===OS==='; (cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '"') || echo unknown
echo '===CPU==='; nproc 2>/dev/null
echo '===LOADAVG==='; cat /proc/loadavg 2>/dev/null
echo '===MEMINFO==='; cat /proc/meminfo 2>/dev/null
echo '===DISK==='; df -PT -x tmpfs -x devtmpfs -x squashfs -x overlay 2>/dev/null | tail -n +2
echo '===TOPCPU==='; ps -eo pid,user,pcpu,pmem,comm --sort=-pcpu --no-headers 2>/dev/null | head -5
echo '===TOPMEM==='; ps -eo pid,user,pcpu,pmem,rss,comm --sort=-rss --no-headers 2>/dev/null | head -5
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    mem_info = _parse_meminfo(sections.get("MEMINFO", ""))

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "hostname": sections.get("HOSTNAME", "").strip(),
                    "os": sections.get("OS", "").strip(),
                    "kernel": sections.get("KERNEL", "").strip(),
                    "uptime": sections.get("UPTIME", "").strip(),
                    "cpu_cores": sections.get("CPU", "").strip(),
                    "loadavg": sections.get("LOADAVG", "").strip(),
                    "memory": mem_info,
                    "disk": sections.get("DISK", "").strip(),
                    "top_cpu": sections.get("TOPCPU", "").strip(),
                    "top_mem": sections.get("TOPMEM", "").strip(),
                },
                indent=2,
            )
        )
        return

    _render_kv(
        f"System overview — {target.host}",
        [
            ("hostname", sections.get("HOSTNAME", "?").strip()),
            ("OS", sections.get("OS", "?").strip()),
            ("kernel", sections.get("KERNEL", "?").strip()),
            ("uptime", sections.get("UPTIME", "?").strip()),
            ("CPU cores", sections.get("CPU", "?").strip()),
            ("load avg", sections.get("LOADAVG", "?").strip()),
            ("memory total", mem_info.get("MemTotal", "?")),
            ("memory used", mem_info.get("MemUsed", "?")),
            ("memory available", mem_info.get("MemAvailable", "?")),
        ],
    )

    # Disk
    disk_rows = []
    for line in sections.get("DISK", "").strip().splitlines():
        parts = line.split()
        if len(parts) >= 7:
            fs, fstype, size, used, avail, pct, mount = parts[:7]
            disk_rows.append(
                [fs, fstype, _human_kib(size), _human_kib(used), pct, mount]
            )
    if disk_rows:
        _render_table(
            "Disk usage",
            ["Filesystem", "Type", "Size", "Used", "Use%", "Mount"],
            disk_rows,
        )

    # Top CPU
    top_cpu_rows = []
    for line in sections.get("TOPCPU", "").strip().splitlines():
        parts = line.split(None, 4)
        if len(parts) == 5:
            top_cpu_rows.append(
                [parts[0], parts[1], f"{parts[2]}%", f"{parts[3]}%", parts[4]]
            )
    if top_cpu_rows:
        _render_table(
            "Top 5 by CPU",
            ["PID", "USER", "CPU", "MEM", "COMMAND"],
            top_cpu_rows,
        )

    # Top mem
    top_mem_rows = []
    for line in sections.get("TOPMEM", "").strip().splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6:
            top_mem_rows.append(
                [
                    parts[0],
                    parts[1],
                    f"{parts[2]}%",
                    f"{parts[3]}%",
                    _human_kib(parts[4]),
                    parts[5],
                ]
            )
    if top_mem_rows:
        _render_table(
            "Top 5 by memory",
            ["PID", "USER", "CPU", "MEM", "RSS", "COMMAND"],
            top_mem_rows,
        )


# ─── logs ──────────────────────────────────────────────────────────────────


@inspect_group.command("logs")
@_remote_options
@click.option("-n", "--lines", default=50, help="Number of log lines (default: 50)")
@click.option(
    "-s",
    "--service",
    default=None,
    help="Filter by systemd unit (e.g. 'sshd', 'nginx')",
)
@click.option(
    "--last",
    "last",
    default=None,
    help="Time window — e.g. '1h', '30m', '2d', '1w'",
)
@click.option(
    "--since",
    default=None,
    help="Raw systemd time spec, e.g. '1 hour ago', 'today', '2026-04-09 10:00'",
)
@click.option(
    "-l",
    "--level",
    type=click.Choice(["emerg", "alert", "crit", "err", "warning", "notice", "info"]),
    default=None,
    help="Min priority (includes this level and above)",
)
@click.option("--errors", "errors_only", is_flag=True, help="Shortcut for --level err")
@click.option(
    "--warnings",
    "warnings_only",
    is_flag=True,
    help="Shortcut for --level warning (warnings + errors)",
)
def logs_cmd(
    remote,
    user,
    port,
    private_key,
    json_out,
    lines,
    service,
    last,
    since,
    level,
    errors_only,
    warnings_only,
):
    """Recent system logs (journalctl, fallback to /var/log/syslog).

    \b
    Examples:
      hat inspect logs -r web1                       # last 50 lines
      hat inspect logs -r web1 -n 200                # last 200 lines
      hat inspect logs -r web1 --errors              # errors only
      hat inspect logs -r web1 --warnings            # warnings + errors
      hat inspect logs -r web1 --last 1h             # last hour
      hat inspect logs -r web1 --last 30m --errors   # last 30 min errors
      hat inspect logs -r web1 -s sshd --last 1d     # sshd unit, last day
    """
    target = _resolve_target(remote, user, port, private_key)
    level = _apply_level_shortcut(level, errors_only, warnings_only)
    since = _apply_time_window(since, last)

    parts = ["journalctl", "--no-pager", "-o", "short-iso", "-n", str(lines)]
    if since:
        parts.extend(["--since", shlex.quote(since)])
    if level:
        parts.extend(["-p", level])

    # Service filter — match either unit or syslog identifier.
    # journalctl ORs raw matches separated by '+'.
    if service:
        q = shlex.quote(service)
        if "." in service:
            # Full unit name (e.g. 'docker.service', 'nginx.socket') — use as-is
            parts.extend([f"_SYSTEMD_UNIT={q}"])
        else:
            # Bare name — try both '<name>.service' unit and syslog identifier
            q_svc = shlex.quote(f"{service}.service")
            parts.extend(
                [
                    f"_SYSTEMD_UNIT={q_svc}",
                    "+",
                    f"_SYSTEMD_UNIT={q}",
                    "+",
                    f"SYSLOG_IDENTIFIER={q}",
                ]
            )

    journal_cmd = " ".join(parts)
    fallback = f"tail -n {lines} /var/log/syslog 2>/dev/null || tail -n {lines} /var/log/messages 2>/dev/null"
    cmd = f"{journal_cmd} 2>/dev/null || {fallback}"

    out = _run_remote(target, cmd)
    log_lines = out.strip().splitlines()

    rows = [_parse_journal_line(line) for line in log_lines]

    title = f"Logs on {target.host}"
    if service:
        title += f" — unit: {service}"
    if level:
        title += f" — level: {level}+"
    if since:
        title += f" — since: {since}"
    _render_table(title, ["Timestamp", "Host", "Unit", "Message"], rows, json_out)


# ─── services ──────────────────────────────────────────────────────────────


@inspect_group.command("services")
@_remote_options
def services_cmd(remote, user, port, private_key, json_out):
    """Systemd units summary — totals + failed units.

    \b
    Examples:
      hat inspect services -r web1
      hat inspect services -r web1 --json
    """
    target = _resolve_target(remote, user, port, private_key)
    script = """
echo '===FAILED==='
systemctl list-units --state=failed --no-legend --plain --no-pager 2>/dev/null
echo '===RUNNING==='
systemctl list-units --type=service --state=running --no-legend --plain --no-pager 2>/dev/null | wc -l
echo '===TOTAL==='
systemctl list-units --type=service --no-legend --plain --no-pager 2>/dev/null | wc -l
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    running = sections.get("RUNNING", "0").strip() or "0"
    total = sections.get("TOTAL", "0").strip() or "0"
    failed_lines = [
        line for line in sections.get("FAILED", "").splitlines() if line.strip()
    ]

    failed_rows = []
    for line in failed_lines:
        cols = line.split(None, 4)
        if len(cols) >= 4:
            unit, load, active, sub = cols[:4]
            desc = cols[4] if len(cols) > 4 else ""
            failed_rows.append([unit, load, active, sub, desc])

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "total_services": int(total) if total.isdigit() else total,
                    "running_services": int(running) if running.isdigit() else running,
                    "failed_count": len(failed_rows),
                    "failed": [
                        dict(zip(["unit", "load", "active", "sub", "desc"], r))
                        for r in failed_rows
                    ],
                },
                indent=2,
            )
        )
        return

    _render_kv(
        f"Services on {target.host}",
        [
            ("Total services", total),
            ("Running", running),
            ("Failed", str(len(failed_rows))),
        ],
    )
    if failed_rows:
        _render_table(
            "Failed units",
            ["Unit", "Load", "Active", "Sub", "Description"],
            failed_rows,
        )
    else:
        from rich.console import Console

        Console().print("  [green]No failed units[/green]")


# ─── listen ────────────────────────────────────────────────────────────────


@inspect_group.command("listen")
@_remote_options
@click.option("--tcp", "tcp_only", is_flag=True, help="TCP sockets only")
@click.option("--udp", "udp_only", is_flag=True, help="UDP sockets only")
@click.option("-4", "ipv4_only", is_flag=True, help="IPv4 only")
@click.option("-6", "ipv6_only", is_flag=True, help="IPv6 only")
def listen_cmd(
    remote, user, port, private_key, json_out, tcp_only, udp_only, ipv4_only, ipv6_only
):
    """Listening TCP/UDP ports with process.

    \b
    Examples:
      hat inspect listen -r web1
      hat inspect listen -r web1 --tcp
      hat inspect listen -r web1 --udp -4
    """
    target = _resolve_target(remote, user, port, private_key)

    if tcp_only and udp_only:
        click.echo("Error: --tcp and --udp are mutually exclusive", err=True)
        sys.exit(2)
    if ipv4_only and ipv6_only:
        click.echo("Error: -4 and -6 are mutually exclusive", err=True)
        sys.exit(2)

    # Always include both -t and -u so the output consistently has a Netid
    # column; filter client-side instead.
    ss_flags = "-tulnpH"
    if ipv4_only:
        ss_flags += " -4"
    elif ipv6_only:
        ss_flags += " -6"

    # ss -p needs root to show processes owned by other users.
    # Try passwordless sudo first, fall back to unprivileged ss.
    cmd = f"sudo -n ss {ss_flags} 2>/dev/null || ss {ss_flags} 2>/dev/null"
    out = _run_remote(target, cmd)

    import re

    rows = []
    for line in out.strip().splitlines():
        cols = line.split()
        # With -H (no header) and -tu, each line has:
        #   Netid State Recv-Q Send-Q LocalAddress:Port PeerAddress:Port [Process]
        if len(cols) < 6:
            continue
        proto = cols[0]  # tcp / udp
        if tcp_only and proto != "tcp":
            continue
        if udp_only and proto != "udp":
            continue

        local = cols[4]
        process = cols[6] if len(cols) > 6 else ""

        # Split on last ':' to handle IPv6 addresses ("[::]:22" or "*:22")
        if ":" in local:
            addr, _, prt = local.rpartition(":")
            addr = addr.strip("[]") or "*"
        else:
            addr, prt = local, ""

        # Parse process: users:(("name",pid=123,fd=4))
        proc_m = re.search(r'users:\(\("([^"]+)",pid=(\d+)', process)
        proc_str = (
            f"{proc_m.group(1)}[{proc_m.group(2)}]" if proc_m else (process or "-")
        )
        rows.append([proto, addr, prt, proc_str])

    rows.sort(key=lambda r: (r[0], int(r[2]) if r[2].isdigit() else 0))
    _render_table(
        f"Listening sockets on {target.host}",
        ["Proto", "Address", "Port", "Process"],
        rows,
        json_out,
    )


# ─── who ───────────────────────────────────────────────────────────────────


@inspect_group.command("who")
@_remote_options
def who_cmd(remote, user, port, private_key, json_out):
    """Active sessions + recent logins.

    \b
    Examples:
      hat inspect who -r web1
    """
    target = _resolve_target(remote, user, port, private_key)
    script = """
echo '===ACTIVE==='
who 2>/dev/null
echo '===LAST==='
last -n 10 -F 2>/dev/null | head -n 10
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    active_rows = []
    for line in sections.get("ACTIVE", "").strip().splitlines():
        cols = line.split(None, 4)
        if len(cols) >= 4:
            who_user, tty, date, time_ = cols[:4]
            from_ = cols[4].strip("()") if len(cols) > 4 else ""
            active_rows.append([who_user, tty, from_, f"{date} {time_}"])

    last_rows = []
    for line in sections.get("LAST", "").strip().splitlines():
        if not line or line.startswith("wtmp") or "system boot" in line:
            continue
        # last -F format: user tty from Mon Apr  9 07:21:16 2026 - Mon Apr  9 07:22:02 2026 (00:00)
        cols = line.split()
        if len(cols) < 4:
            continue
        last_rows.append([line.strip()])

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "active": [
                        dict(zip(["user", "tty", "from", "login"], r))
                        for r in active_rows
                    ],
                    "recent": [r[0] for r in last_rows],
                },
                indent=2,
            )
        )
        return

    _render_table(
        f"Active sessions on {target.host}",
        ["User", "TTY", "From", "Login"],
        active_rows or [["(none)", "-", "-", "-"]],
    )
    if last_rows:
        _render_table("Recent logins (last 10)", ["Entry"], last_rows)


# ─── dmesg ─────────────────────────────────────────────────────────────────


@inspect_group.command("dmesg")
@_remote_options
@click.option("-n", "--lines", default=50, help="Number of lines (default: 50)")
@click.option(
    "--last",
    default=None,
    help="Time window — e.g. '1h', '30m', '2d', '1w' (requires dmesg with -T)",
)
@click.option(
    "-l",
    "--level",
    type=click.Choice(
        ["emerg", "alert", "crit", "err", "warn", "notice", "info", "debug"]
    ),
    default=None,
    help="Min priority",
)
@click.option("--errors", "errors_only", is_flag=True, help="Shortcut for --level err")
@click.option(
    "--warnings",
    "warnings_only",
    is_flag=True,
    help="Shortcut for --level warn",
)
def dmesg_cmd(
    remote,
    user,
    port,
    private_key,
    json_out,
    lines,
    last,
    level,
    errors_only,
    warnings_only,
):
    """Kernel ring buffer tail (dmesg).

    \b
    Examples:
      hat inspect dmesg -r web1
      hat inspect dmesg -r web1 --errors
      hat inspect dmesg -r web1 --last 1h --warnings
      hat inspect dmesg -r web1 -n 200
    """
    target = _resolve_target(remote, user, port, private_key)

    # Reuse shortcut helpers — but dmesg uses 'warn' not 'warning'
    if errors_only and warnings_only:
        click.echo("Error: --errors and --warnings are mutually exclusive", err=True)
        sys.exit(2)
    if errors_only:
        level = "err"
    elif warnings_only:
        level = "warn"

    parts = ["dmesg", "-T"]
    if level:
        parts.extend(["--level", level])
    cmd_primary = " ".join(parts) + f" 2>/dev/null | tail -n {lines}"
    # Fallback without -T (older kernels / non-linux)
    fallback = f"dmesg 2>/dev/null | tail -n {lines}"
    cmd = f"({cmd_primary}) || ({fallback})"

    out = _run_remote(target, cmd)
    dmesg_lines = out.strip().splitlines()

    # Optional time filter (client-side) when --last given
    if last:
        import re as _re
        from datetime import datetime, timedelta

        spec = _parse_last_spec(last)
        if spec is None:
            click.echo(
                f"Error: invalid --last value '{last}' (expected '30m', '1h', '2d', '1w')",
                err=True,
            )
            sys.exit(2)
        # Extract integer quantity + unit from spec
        m = _re.match(r"(\d+)\s+(\w+)s?\s+ago", spec)
        if m:
            n = int(m.group(1))
            unit = m.group(2).rstrip("s")
            mapping = {
                "second": "seconds",
                "minute": "minutes",
                "hour": "hours",
                "day": "days",
                "week": "weeks",
            }
            if unit in mapping:
                delta = timedelta(**{mapping[unit]: n})
                cutoff = datetime.now().astimezone() - delta
                dmesg_lines = [
                    line for line in dmesg_lines if _dmesg_line_after(line, cutoff)
                ]

    rows = []
    for line in dmesg_lines:
        # dmesg -T format: "[Thu Apr  9 07:24:05 2026] message..."
        if line.startswith("["):
            try:
                ts, rest = line[1:].split("] ", 1)
            except ValueError:
                ts, rest = "", line
        else:
            ts, rest = "", line
        rows.append([ts, rest])

    title = f"dmesg on {target.host}"
    if level:
        title += f" — level: {level}+"
    if last:
        title += f" — last: {last}"
    _render_table(title, ["Time", "Message"], rows, json_out)


def _dmesg_line_after(line: str, cutoff) -> bool:
    """Return True if a dmesg -T line's timestamp is >= cutoff."""
    from datetime import datetime

    if not line.startswith("["):
        return True  # keep undated lines (safer than dropping)
    try:
        ts_str, _ = line[1:].split("] ", 1)
        # dmesg -T format example: "Thu Apr  9 07:24:05 2026"
        ts = datetime.strptime(ts_str.strip(), "%a %b %d %H:%M:%S %Y")
        return ts.timestamp() >= cutoff.timestamp()
    except (ValueError, IndexError):
        return True


# ─── containers ────────────────────────────────────────────────────────────


@inspect_group.command("containers")
@_remote_options
def containers_cmd(remote, user, port, private_key, json_out):
    """Docker containers and Nomad workloads.

    \b
    Examples:
      hat inspect containers -r web1
    """
    target = _resolve_target(remote, user, port, private_key)
    script = r"""
echo '===DOCKER==='
if command -v docker >/dev/null 2>&1; then
  docker ps --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null
fi
echo '===NOMAD==='
if command -v nomad >/dev/null 2>&1; then
  # 'nomad status' lists jobs when it can connect to the agent.
  # Filter to only lines matching a plausible job row (space-separated cols).
  nomad status 2>/dev/null | awk 'NR==1 && /^ID/ || NR>1 && NF>=4 && $1 !~ /^-/'
fi
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    docker_rows = []
    for line in sections.get("DOCKER", "").strip().splitlines():
        cols = line.split("\t")
        if len(cols) >= 4:
            container_id, name, image, status = cols[:4]
            ports = cols[4] if len(cols) > 4 else ""
            docker_rows.append([container_id[:12], name, image, status, ports])

    nomad_rows = []
    for line in sections.get("NOMAD", "").strip().splitlines():
        cols = line.split()
        if cols:
            nomad_rows.append(cols)

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "docker": [
                        dict(zip(["id", "name", "image", "status", "ports"], r))
                        for r in docker_rows
                    ],
                    "nomad": nomad_rows,
                },
                indent=2,
            )
        )
        return

    if docker_rows:
        _render_table(
            f"Docker containers on {target.host}",
            ["ID", "Name", "Image", "Status", "Ports"],
            docker_rows,
        )
    else:
        from rich.console import Console

        Console().print(f"  [dim]No Docker containers on {target.host}[/dim]")

    if nomad_rows:
        # First row is header if still present
        cols_n = ["ID", "Type", "Priority", "Status", "Submit Date"][
            : len(nomad_rows[0])
        ]
        _render_table(f"Nomad jobs on {target.host}", cols_n, nomad_rows)


# ─── hw ────────────────────────────────────────────────────────────────────


@inspect_group.command("hw")
@_remote_options
def hw_cmd(remote, user, port, private_key, json_out):
    """Hardware summary — CPU, RAM, disks, temperature.

    \b
    Examples:
      hat inspect hw -r web1
    """
    target = _resolve_target(remote, user, port, private_key)
    script = r"""
echo '===LSCPU==='
lscpu 2>/dev/null | grep -E '^(Model name|Architecture|CPU\(s\)|Thread|Socket|CPU max MHz|CPU min MHz|Vendor ID)' || true
echo '===MEM==='
grep -E '^(MemTotal|MemAvailable|SwapTotal)' /proc/meminfo 2>/dev/null || true
echo '===DISKS==='
lsblk -dno NAME,SIZE,MODEL,ROTA 2>/dev/null || true
echo '===SENSORS==='
(command -v sensors >/dev/null && sensors 2>/dev/null | grep -E '\S+:\s+[+-]?[0-9]+\.[0-9]+°[CF]' | head -20) || true
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    cpu_info = {}
    for line in sections.get("LSCPU", "").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            cpu_info[k.strip()] = v.strip()

    mem_info = _parse_meminfo(sections.get("MEM", ""))

    disk_rows = []
    for line in sections.get("DISKS", "").strip().splitlines():
        cols = line.split(None, 3)
        if len(cols) >= 2:
            name = cols[0]
            size = cols[1]
            model = cols[2] if len(cols) > 2 else ""
            rota = cols[3] if len(cols) > 3 else ""
            kind = "HDD" if rota == "1" else "SSD" if rota == "0" else "?"
            disk_rows.append([name, size, model, kind])

    temp_rows = []
    for line in sections.get("SENSORS", "").strip().splitlines():
        if ":" in line:
            sensor, value = line.split(":", 1)
            temp_rows.append([sensor.strip(), value.strip()])

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "cpu": cpu_info,
                    "memory": mem_info,
                    "disks": [
                        dict(zip(["name", "size", "model", "type"], r))
                        for r in disk_rows
                    ],
                    "temperatures": [
                        dict(zip(["sensor", "value"], r)) for r in temp_rows
                    ],
                },
                indent=2,
            )
        )
        return

    _render_kv(
        f"Hardware — {target.host}",
        [
            ("CPU model", cpu_info.get("Model name", "?")),
            ("Vendor", cpu_info.get("Vendor ID", "?")),
            ("Architecture", cpu_info.get("Architecture", "?")),
            ("CPU(s)", cpu_info.get("CPU(s)", "?")),
            (
                "Threads/core",
                cpu_info.get("Thread(s) per core", "?"),
            ),
            ("Sockets", cpu_info.get("Socket(s)", "?")),
            ("Max MHz", cpu_info.get("CPU max MHz", "?")),
            ("Memory total", mem_info.get("MemTotal", "?")),
            ("Swap total", mem_info.get("SwapTotal", "?")),
        ],
    )
    if disk_rows:
        _render_table("Block devices", ["Device", "Size", "Model", "Type"], disk_rows)
    if temp_rows:
        _render_table("Temperature sensors", ["Sensor", "Reading"], temp_rows)


# ─── updates ───────────────────────────────────────────────────────────────


@inspect_group.command("updates")
@_remote_options
def updates_cmd(remote, user, port, private_key, json_out):
    """Pending package updates + reboot-required check.

    \b
    Examples:
      hat inspect updates -r web1
    """
    target = _resolve_target(remote, user, port, private_key)
    script = r"""
echo '===PM==='
if command -v apt >/dev/null 2>&1; then echo apt
elif command -v dnf >/dev/null 2>&1; then echo dnf
elif command -v yum >/dev/null 2>&1; then echo yum
elif command -v zypper >/dev/null 2>&1; then echo zypper
elif command -v pacman >/dev/null 2>&1; then echo pacman
else echo unknown
fi
echo '===PENDING==='
if command -v apt >/dev/null 2>&1; then
  apt list --upgradable 2>/dev/null | tail -n +2
elif command -v dnf >/dev/null 2>&1; then
  # Only lines that look like "package.arch  version  repo"
  dnf -q check-update 2>/dev/null | awk 'NF>=3 && $1 ~ /^[a-zA-Z0-9._+-]+\.[a-zA-Z0-9_]+$/ {print $1, $2, $3}'
elif command -v yum >/dev/null 2>&1; then
  yum -q check-update 2>/dev/null | awk 'NF>=3 && $1 ~ /^[a-zA-Z0-9._+-]+\.[a-zA-Z0-9_]+$/ {print $1, $2, $3}'
elif command -v zypper >/dev/null 2>&1; then
  zypper -q -n list-updates 2>/dev/null | awk -F'|' 'NR>2 && NF>=5 {gsub(/^ +| +$/, "", $3); gsub(/^ +| +$/, "", $5); print $3, $5}'
elif command -v pacman >/dev/null 2>&1; then
  pacman -Qu 2>/dev/null
fi
echo '===REBOOT==='
if [ -f /var/run/reboot-required ]; then
  echo YES
elif command -v needs-restarting >/dev/null 2>&1; then
  if needs-restarting -r >/dev/null 2>&1; then echo NO; else echo YES; fi
elif command -v dnf >/dev/null 2>&1; then
  if dnf needs-restarting -r >/dev/null 2>&1; then echo NO; else echo YES; fi
else
  echo UNKNOWN
fi
echo '===KERNEL==='
uname -r 2>/dev/null
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    pm = sections.get("PM", "").strip() or "unknown"
    reboot = sections.get("REBOOT", "").strip() or "UNKNOWN"
    kernel = sections.get("KERNEL", "").strip()

    pending_lines = [
        line for line in sections.get("PENDING", "").splitlines() if line.strip()
    ]

    rows = []
    for line in pending_lines[:20]:
        cols = line.split()
        if pm == "apt" and len(cols) >= 2:
            name = cols[0].split("/")[0]
            version = cols[1]
            rows.append([name, version])
        elif pm in ("dnf", "yum") and len(cols) >= 3:
            rows.append([cols[0], cols[1]])
        elif len(cols) >= 2:
            rows.append([cols[0], cols[1]])
        else:
            rows.append([line.strip(), ""])

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "package_manager": pm,
                    "pending_count": len(pending_lines),
                    "reboot_required": reboot,
                    "kernel": kernel,
                    "pending": [dict(zip(["package", "version"], r)) for r in rows],
                },
                indent=2,
            )
        )
        return

    _render_kv(
        f"Updates on {target.host}",
        [
            ("Package manager", pm),
            ("Pending updates", str(len(pending_lines))),
            ("Reboot required", reboot),
            ("Running kernel", kernel),
        ],
    )
    if rows:
        _render_table(
            f"Pending packages (first {len(rows)})",
            ["Package", "Version"],
            rows,
        )


# ─── proc ──────────────────────────────────────────────────────────────────


@inspect_group.command("proc")
@_remote_options
@click.argument("target_proc", metavar="PID_OR_NAME")
def proc_cmd(remote, user, port, private_key, json_out, target_proc):
    """Detailed process info by PID or name.

    \b
    Examples:
      hat inspect proc -r web1 1234
      hat inspect proc -r web1 nginx
    """
    target = _resolve_target(remote, user, port, private_key)

    # Resolve name → pid server-side.
    # All $PID expansions are double-quoted to prevent empty-resolution
    # from matching /proc itself (pgrep-returns-empty edge case).
    script = f"""
PID={shlex.quote(target_proc)}
if ! echo "$PID" | grep -qE '^[0-9]+$'; then
  RESOLVED=$(pgrep -x "$PID" 2>/dev/null | head -1)
  if [ -z "$RESOLVED" ]; then
    RESOLVED=$(pgrep "$PID" 2>/dev/null | head -1)
  fi
  PID="$RESOLVED"
fi
if [ -z "$PID" ] || ! [ -d /proc/"$PID" ]; then
  echo '===NOTFOUND==='
  echo "No process matching: {shlex.quote(target_proc)}"
  exit 0
fi
echo '===PID==='
echo "$PID"
echo '===PS==='
ps -p "$PID" -o pid,ppid,user,pcpu,pmem,rss,vsz,nlwp,stat,lstart,comm --no-headers 2>/dev/null
echo '===CMDLINE==='
tr '\\0' ' ' < /proc/"$PID"/cmdline 2>/dev/null; echo
echo '===STATUS==='
grep -E '^(VmPeak|VmSize|VmRSS|Threads|voluntary_ctxt_switches|nonvoluntary_ctxt_switches|State):' /proc/"$PID"/status 2>/dev/null
echo '===FDS==='
ls /proc/"$PID"/fd 2>/dev/null | wc -l
echo '===CONNS==='
ss -tanp state established 2>/dev/null | grep "pid=$PID," || true
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    if "NOTFOUND" in sections:
        click.echo(sections["NOTFOUND"].strip(), err=True)
        sys.exit(1)

    pid = sections.get("PID", "").strip()
    ps_line = sections.get("PS", "").strip()
    cmdline = sections.get("CMDLINE", "").strip()
    status_raw = sections.get("STATUS", "").strip()
    fd_count = sections.get("FDS", "").strip()
    conn_lines = [
        line for line in sections.get("CONNS", "").splitlines() if line.strip()
    ]

    # Parse ps fields: pid ppid user pcpu pmem rss vsz nlwp stat lstart(5 words) comm
    ps_cols = ps_line.split(None, 14)
    ps_info = {}
    if len(ps_cols) >= 15:
        ps_info = {
            "pid": ps_cols[0],
            "ppid": ps_cols[1],
            "user": ps_cols[2],
            "cpu%": ps_cols[3],
            "mem%": ps_cols[4],
            "rss": _human_kib(ps_cols[5]),
            "vsz": _human_kib(ps_cols[6]),
            "threads": ps_cols[7],
            "state": ps_cols[8],
            "start": " ".join(ps_cols[9:14]),
            "comm": ps_cols[14],
        }

    status = {}
    for line in status_raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            status[k.strip()] = v.strip()

    conn_rows = []
    for line in conn_lines:
        cols = line.split()
        if len(cols) >= 5:
            state_, recvq, sendq, local, peer = cols[:5]
            conn_rows.append([state_, local, peer])

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "pid": pid,
                    "ps": ps_info,
                    "cmdline": cmdline,
                    "status": status,
                    "open_fds": fd_count,
                    "connections": [
                        dict(zip(["state", "local", "peer"], r)) for r in conn_rows
                    ],
                },
                indent=2,
            )
        )
        return

    _render_kv(
        f"Process {pid} on {target.host}",
        [
            ("PID", ps_info.get("pid", pid)),
            ("PPID", ps_info.get("ppid", "?")),
            ("User", ps_info.get("user", "?")),
            ("Command", ps_info.get("comm", "?")),
            ("State", ps_info.get("state", status.get("State", "?"))),
            ("CPU %", ps_info.get("cpu%", "?")),
            ("Mem %", ps_info.get("mem%", "?")),
            ("RSS", ps_info.get("rss", "?")),
            ("VSZ", ps_info.get("vsz", "?")),
            ("Threads", ps_info.get("threads", status.get("Threads", "?"))),
            ("Open FDs", fd_count or "?"),
            (
                "Ctx switches (vol)",
                status.get("voluntary_ctxt_switches", "?"),
            ),
            ("Start", ps_info.get("start", "?")),
            ("Cmdline", cmdline or "?"),
        ],
    )
    if conn_rows:
        _render_table(
            "Established TCP connections",
            ["State", "Local", "Peer"],
            conn_rows,
        )


# ─── security ──────────────────────────────────────────────────────────────


@inspect_group.command("security")
@_remote_options
def security_cmd(remote, user, port, private_key, json_out):
    """Security posture snapshot — failed logins, users, firewall.

    \b
    Examples:
      hat inspect security -r web1
    """
    target = _resolve_target(remote, user, port, private_key)
    script = r"""
echo '===FAILED==='
if command -v lastb >/dev/null 2>&1; then
  lastb -n 10 -F 2>/dev/null | head -n 10
else
  journalctl _COMM=sshd -p warning --since='-1 day' 2>/dev/null | grep -i 'failed password' | tail -10
fi
echo '===WHO==='
who 2>/dev/null
echo '===FIREWALL==='
if command -v ufw >/dev/null 2>&1; then
  ufw status 2>/dev/null | head -20
elif command -v firewall-cmd >/dev/null 2>&1; then
  firewall-cmd --list-all 2>/dev/null | head -30
elif command -v iptables >/dev/null 2>&1; then
  echo "iptables rules (count):"
  iptables -L INPUT -n 2>/dev/null | wc -l
  iptables -L INPUT -n 2>/dev/null | head -20
fi
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    failed_rows = []
    for line in sections.get("FAILED", "").strip().splitlines():
        if line and not line.startswith("btmp"):
            failed_rows.append([line.strip()])

    who_rows = []
    for line in sections.get("WHO", "").strip().splitlines():
        cols = line.split(None, 4)
        if len(cols) >= 4:
            who_rows.append(
                [
                    cols[0],
                    cols[1],
                    cols[4].strip("()") if len(cols) > 4 else "",
                    f"{cols[2]} {cols[3]}",
                ]
            )

    firewall_raw = sections.get("FIREWALL", "").strip()

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "failed_logins": [r[0] for r in failed_rows],
                    "active_users": [
                        dict(zip(["user", "tty", "from", "login"], r)) for r in who_rows
                    ],
                    "firewall": firewall_raw,
                },
                indent=2,
            )
        )
        return

    _render_table(
        f"Recent failed logins on {target.host}",
        ["Entry"],
        failed_rows or [["(none)"]],
    )
    _render_table(
        "Active sessions",
        ["User", "TTY", "From", "Login"],
        who_rows or [["(none)", "-", "-", "-"]],
    )
    from rich.console import Console
    from rich.panel import Panel

    Console().print(
        Panel(firewall_raw or "(no firewall info)", title="Firewall", style="dim")
    )


# ─── health ────────────────────────────────────────────────────────────────


@inspect_group.command("health")
@_remote_options
def health_cmd(remote, user, port, private_key, json_out):
    """Aggregate health dashboard — exits 2 if any ALERT.

    \b
    Checks: load, memory, disk, failed services, zombies,
    reboot required, pending updates, dmesg errors.

    \b
    Examples:
      hat inspect health -r web1
      hat inspect health -r web1 --json
      hat inspect health -r web1 && echo OK  # scriptable
    """
    target = _resolve_target(remote, user, port, private_key)
    script = r"""
echo '===UPTIME==='
uptime
echo '===CORES==='
nproc 2>/dev/null
echo '===LOADAVG==='
cat /proc/loadavg 2>/dev/null
echo '===MEMINFO==='
grep -E '^(MemTotal|MemAvailable|MemFree|Buffers|Cached)' /proc/meminfo 2>/dev/null
echo '===DISK==='
df -P -x tmpfs -x devtmpfs -x squashfs -x overlay 2>/dev/null | tail -n +2
echo '===FAILED_UNITS==='
systemctl list-units --state=failed --no-legend --plain --no-pager 2>/dev/null | wc -l
echo '===ZOMBIES==='
ps -eo stat --no-headers 2>/dev/null | awk '$1 ~ /^Z/' | wc -l
echo '===REBOOT==='
if [ -f /var/run/reboot-required ]; then echo YES
elif command -v needs-restarting >/dev/null 2>&1; then
  if needs-restarting -r >/dev/null 2>&1; then echo NO; else echo YES; fi
elif command -v dnf >/dev/null 2>&1; then
  if dnf needs-restarting -r >/dev/null 2>&1; then echo NO; else echo YES; fi
else echo UNKNOWN
fi
echo '===UPDATES==='
if command -v apt >/dev/null 2>&1; then
  apt list --upgradable 2>/dev/null | tail -n +2 | wc -l
elif command -v dnf >/dev/null 2>&1; then
  dnf -q check-update 2>/dev/null | awk 'NF>=3 && $1 ~ /^[a-zA-Z0-9._+-]+\.[a-zA-Z0-9_]+$/' | wc -l
elif command -v pacman >/dev/null 2>&1; then
  pacman -Qu 2>/dev/null | wc -l
else
  echo 0
fi
echo '===DMESG_ERRORS==='
dmesg --level=err 2>/dev/null | wc -l
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    uptime = sections.get("UPTIME", "").strip()
    cores_str = sections.get("CORES", "").strip() or "1"
    cores = int(cores_str) if cores_str.isdigit() else 1
    loadavg = sections.get("LOADAVG", "").strip().split()
    load_1m = float(loadavg[0]) if loadavg else 0.0

    mem_info = _parse_meminfo(sections.get("MEMINFO", ""))
    raw_mem_total = 0
    raw_mem_avail = 0
    for line in sections.get("MEMINFO", "").splitlines():
        if line.startswith("MemTotal:"):
            raw_mem_total = int(line.split()[1])
        elif line.startswith("MemAvailable:"):
            raw_mem_avail = int(line.split()[1])
    mem_pct = (
        int(100 * (raw_mem_total - raw_mem_avail) / raw_mem_total)
        if raw_mem_total
        else 0
    )

    disk_max_pct = 0
    disk_max_mount = ""
    for line in sections.get("DISK", "").strip().splitlines():
        cols = line.split()
        if len(cols) >= 6:
            pct_str = cols[4].rstrip("%")
            mount = cols[5]
            if pct_str.isdigit():
                pct = int(pct_str)
                if pct > disk_max_pct:
                    disk_max_pct = pct
                    disk_max_mount = mount

    failed_units = int(sections.get("FAILED_UNITS", "0").strip() or "0")
    zombies = int(sections.get("ZOMBIES", "0").strip() or "0")
    reboot = sections.get("REBOOT", "UNKNOWN").strip()
    updates = int(sections.get("UPDATES", "0").strip() or "0")
    dmesg_errors = int(sections.get("DMESG_ERRORS", "0").strip() or "0")

    # Classify each check: "OK" / "WARN" / "ALERT"
    checks: list[tuple[str, str, str]] = []  # (name, status, value)

    # Load — ALERT if > 2x cores, WARN if > cores
    if load_1m > 2 * cores:
        checks.append(("Load (1m)", "ALERT", f"{load_1m:.2f} / {cores} cores"))
    elif load_1m > cores:
        checks.append(("Load (1m)", "WARN", f"{load_1m:.2f} / {cores} cores"))
    else:
        checks.append(("Load (1m)", "OK", f"{load_1m:.2f} / {cores} cores"))

    # Memory — ALERT > 95%, WARN > 80%
    if mem_pct > 95:
        checks.append(
            (
                "Memory",
                "ALERT",
                f"{mem_pct}% used ({mem_info.get('MemAvailable', '?')} free)",
            )
        )
    elif mem_pct > 80:
        checks.append(
            (
                "Memory",
                "WARN",
                f"{mem_pct}% used ({mem_info.get('MemAvailable', '?')} free)",
            )
        )
    else:
        checks.append(
            (
                "Memory",
                "OK",
                f"{mem_pct}% used ({mem_info.get('MemAvailable', '?')} free)",
            )
        )

    # Disk — ALERT > 95%, WARN > 80%
    if disk_max_pct > 95:
        checks.append(("Disk", "ALERT", f"{disk_max_pct}% on {disk_max_mount}"))
    elif disk_max_pct > 80:
        checks.append(("Disk", "WARN", f"{disk_max_pct}% on {disk_max_mount}"))
    else:
        checks.append(("Disk", "OK", f"{disk_max_pct}% on {disk_max_mount}"))

    # Failed systemd units — ALERT if any
    if failed_units > 0:
        checks.append(("Failed services", "ALERT", f"{failed_units} failed"))
    else:
        checks.append(("Failed services", "OK", "0"))

    # Zombies — ALERT if any
    if zombies > 0:
        checks.append(("Zombie processes", "ALERT", str(zombies)))
    else:
        checks.append(("Zombie processes", "OK", "0"))

    # Reboot required — ALERT if YES
    if reboot == "YES":
        checks.append(("Reboot required", "ALERT", "YES"))
    elif reboot == "NO":
        checks.append(("Reboot required", "OK", "NO"))
    else:
        checks.append(("Reboot required", "OK", "UNKNOWN"))

    # Updates — WARN if any
    if updates > 0:
        checks.append(("Pending updates", "WARN", str(updates)))
    else:
        checks.append(("Pending updates", "OK", "0"))

    # dmesg errors — ALERT if > 0
    if dmesg_errors > 0:
        checks.append(("dmesg errors", "ALERT", str(dmesg_errors)))
    else:
        checks.append(("dmesg errors", "OK", "0"))

    has_alert = any(c[1] == "ALERT" for c in checks)
    has_warn = any(c[1] == "WARN" for c in checks)
    overall = "ALERT" if has_alert else "WARN" if has_warn else "OK"

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "uptime": uptime,
                    "overall": overall,
                    "checks": [
                        {"name": c[0], "status": c[1], "value": c[2]} for c in checks
                    ],
                },
                indent=2,
            )
        )
        sys.exit(2 if has_alert else 0)

    from rich.console import Console
    from rich.table import Table

    style_map = {"OK": "green", "WARN": "yellow", "ALERT": "red bold"}
    table = Table(
        title=f"Health — {target.host}  [{style_map[overall]}]{overall}[/{style_map[overall]}]",
        header_style="bold cyan",
        title_style="bold",
    )
    table.add_column("Check", style="dim")
    table.add_column("Status")
    table.add_column("Value")
    for name, status, value in checks:
        table.add_row(
            name, f"[{style_map[status]}]{status}[/{style_map[status]}]", value
        )
    Console().print(table)
    Console().print(f"  [dim]uptime:[/dim] {uptime}")
    sys.exit(2 if has_alert else 0)


def _parse_last_spec(spec: str) -> str | None:
    """Parse '1h', '30m', '2d', '1w' into a journalctl --since spec."""
    import re

    m = re.fullmatch(r"(\d+)\s*([smhdw])", spec.strip().lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    names = {
        "s": "second",
        "m": "minute",
        "h": "hour",
        "d": "day",
        "w": "week",
    }
    plural = "" if n == 1 else "s"
    return f"{n} {names[unit]}{plural} ago"


def _apply_level_shortcut(
    level: str | None, errors_only: bool, warnings_only: bool
) -> str | None:
    """Resolve --errors/--warnings to a journalctl level string."""
    if errors_only and warnings_only:
        click.echo("Error: --errors and --warnings are mutually exclusive", err=True)
        sys.exit(2)
    if errors_only:
        return "err"
    if warnings_only:
        return "warning"
    return level


def _apply_time_window(since: str | None, last: str | None) -> str | None:
    """Resolve --last shortcut into a --since spec; error on conflict."""
    if last and since:
        click.echo("Error: --last and --since are mutually exclusive", err=True)
        sys.exit(2)
    if last:
        resolved = _parse_last_spec(last)
        if resolved is None:
            click.echo(
                f"Error: invalid --last value '{last}' (expected e.g. '30m', '1h', '2d', '1w')",
                err=True,
            )
            sys.exit(2)
        return resolved
    return since


def _parse_journal_line(line: str) -> list[str]:
    """Parse a journalctl short-iso line into [timestamp, host, unit, message]."""
    parts = line.split(None, 3)
    if len(parts) == 4 and "T" in parts[0]:
        return [parts[0], parts[1], parts[2].rstrip(":"), parts[3]]
    return ["", "", "", line]


# All rendering + humanize helpers live in hat.output (imported above).
