from __future__ import annotations

import shutil
from dataclasses import dataclass

from hat.config import load_company_config, list_companies
from hat.common import load_common_tools
from hat.secrets import SecretResolver


@dataclass
class CheckResult:
    name: str
    level: str  # "ok", "warn", "error"
    message: str


def run_checks(company: str | None = None) -> list[CheckResult]:
    results = []
    companies = [company] if company else list_companies()

    for name in companies:
        results.extend(_check_company(name))

    results.extend(_check_tools())
    return results


def _check_company(name: str) -> list[CheckResult]:
    results = []

    # Config parseable
    try:
        config = load_company_config(name)
        results.append(CheckResult(f"{name}/config", "ok", "Config loaded"))
    except Exception as e:
        results.append(CheckResult(f"{name}/config", "error", str(e)))
        return results

    # Required fields
    if not config.get("name"):
        results.append(CheckResult(f"{name}/name", "warn", "Missing 'name' field"))

    # Secrets accessible
    resolver = SecretResolver()
    refs = resolver._find_refs(config)
    for ref in refs:
        try:
            resolver._resolve_one(ref)
            results.append(CheckResult(f"{name}/secret/{ref}", "ok", "Accessible"))
        except Exception as e:
            results.append(CheckResult(f"{name}/secret/{ref}", "error", str(e)))

    return results


def _check_tools() -> list[CheckResult]:
    results = []
    tools = load_common_tools()
    if not tools:
        results.append(CheckResult("tools/config", "warn", "No tools.yaml found"))
        return results

    for tool in tools.get("brew", []) + tools.get("pipx", []):
        if shutil.which(tool):
            results.append(CheckResult(f"tools/{tool}", "ok", "Installed"))
        else:
            results.append(CheckResult(f"tools/{tool}", "warn", f"Not installed"))

    return results
