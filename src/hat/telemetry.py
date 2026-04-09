from __future__ import annotations

import os
import platform
from importlib.metadata import version
from pathlib import Path

from hat.config import get_config_dir

SENTRY_DSN = "https://99e49f6fd68f0a9ddfcfac4b0180287d@o4511188642824192.ingest.de.sentry.io/4511188654882896"

SENSITIVE_ENV_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "key",
        "dsn",
        "credential",
        "auth",
        "private",
        "api_key",
        "apikey",
    }
)


def _settings_file() -> Path:
    return get_config_dir() / "telemetry.json"


def is_enabled() -> bool:
    if os.environ.get("HAT_TELEMETRY", "").lower() in ("0", "false", "off", "no"):
        return False
    path = _settings_file()
    if not path.exists():
        return True
    try:
        import json

        data = json.loads(path.read_text())
    except (OSError, ValueError):
        # Corrupt or unreadable settings file — default to enabled
        # rather than crashing every hat invocation.
        return True
    return bool(data.get("enabled", True))


def set_enabled(enabled: bool) -> None:
    import json

    path = _settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"enabled": enabled}) + "\n")


def is_first_run() -> bool:
    return not _settings_file().exists()


_SECRETY_VALUE_HINTS = (
    "://",  # URLs (may contain hostnames / creds)
    "bearer ",
    "token=",
    "password=",
    "secret=",
)


def _scrub_value(value):
    """Scrub a leaf value if it looks like a secret.

    We're conservative: strings that look like URLs, JWTs, long hex/base64,
    or contain secret-ish keywords are replaced. Non-string values are
    returned as-is.
    """
    if not isinstance(value, str):
        return value
    v = value.lower()
    if any(hint in v for hint in _SECRETY_VALUE_HINTS):
        return "[scrubbed]"
    # Long opaque strings (likely tokens/keys): >= 32 chars, no whitespace
    if len(value) >= 32 and " " not in value and "\n" not in value:
        return "[scrubbed]"
    return value


def _scrub_mapping(mapping: dict) -> dict:
    """Scrub a dict by key name AND by value content."""
    out = {}
    for k, v in mapping.items():
        if any(s in k.lower() for s in SENSITIVE_ENV_KEYS):
            out[k] = "[scrubbed]"
        elif isinstance(v, dict):
            out[k] = _scrub_mapping(v)
        else:
            out[k] = _scrub_value(v)
    return out


def _before_send(event, hint):
    """Scrub PII and sensitive data before sending to Sentry."""
    # Hostname / user / machine info
    event.pop("server_name", None)
    event.pop("user", None)

    # Request context (URLs, headers, cookies, data)
    event.pop("request", None)

    # Breadcrumbs may contain command lines with tokens — drop entirely.
    event.pop("breadcrumbs", None)

    # Modules list can fingerprint env — not secrets but not needed.
    event.pop("modules", None)

    # Scrub exception chain (type + value + stacktrace vars and context)
    for exc in (event.get("exception") or {}).get("values", []) or []:
        # The exception message itself can contain secrets (e.g. a 403
        # from a URL with a token in it) — redact it lightly.
        if isinstance(exc.get("value"), str):
            exc["value"] = _scrub_value(exc["value"])
        for frame in (exc.get("stacktrace") or {}).get("frames", []) or []:
            if isinstance(frame.get("vars"), dict):
                frame["vars"] = _scrub_mapping(frame["vars"])
            # Source-code context lines can contain string literals with
            # secrets — drop them. Stack-trace filenames/functions are OK.
            frame.pop("pre_context", None)
            frame.pop("context_line", None)
            frame.pop("post_context", None)

    # Tags + extra contexts
    for key in ("extra", "tags"):
        if isinstance(event.get(key), dict):
            event[key] = _scrub_mapping(event[key])

    # Contexts may hold runtime/trace info — keep the runtime/os contexts
    # we set explicitly in init(), drop everything else.
    if isinstance(event.get("contexts"), dict):
        event["contexts"] = {
            k: v for k, v in event["contexts"].items() if k in ("runtime", "os")
        }

    return event


_initialized = False


def init() -> None:
    global _initialized
    if _initialized or not is_enabled():
        return

    try:
        hat_version = version("hatctl")
    except Exception:
        hat_version = "unknown"

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            release=f"hatctl@{hat_version}",
            send_default_pii=False,
            before_send=_before_send,
            traces_sample_rate=0,
            attach_stacktrace=True,
            server_name="redacted",
            shutdown_timeout=5,
        )
        sentry_sdk.set_context(
            "runtime",
            {
                "name": "python",
                "version": platform.python_version(),
            },
        )
        sentry_sdk.set_context(
            "os",
            {
                "name": platform.system(),
                "version": platform.mac_ver()[0] or platform.release(),
            },
        )
        sentry_sdk.set_tag("hat.version", hat_version)
        _initialized = True
    except Exception:
        pass


def capture_exception(exc: BaseException) -> None:
    if not is_enabled() or not _initialized:
        return
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
        sentry_sdk.flush(timeout=5)
    except Exception:
        pass
