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
    if path.exists():
        import json

        data = json.loads(path.read_text())
        return data.get("enabled", True)
    return True


def set_enabled(enabled: bool) -> None:
    import json

    path = _settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"enabled": enabled}) + "\n")


def is_first_run() -> bool:
    return not _settings_file().exists()


def _before_send(event, hint):
    """Scrub PII and sensitive data before sending to Sentry."""
    # Remove server_name (hostname)
    event.pop("server_name", None)

    # Scrub user info
    event.pop("user", None)

    # Scrub breadcrumbs that may contain commands/args with secrets
    if "breadcrumbs" in event:
        event["breadcrumbs"] = {"values": []}

    # Scrub exception frames for local variables
    if "exception" in event:
        for exc in event["exception"].get("values", []):
            for frame in (exc.get("stacktrace") or {}).get("frames", []):
                if "vars" in frame:
                    frame["vars"] = {
                        k: "[scrubbed]"
                        if any(s in k.lower() for s in SENSITIVE_ENV_KEYS)
                        else v
                        for k, v in frame["vars"].items()
                    }

    # Scrub extra context
    if "extra" in event:
        event["extra"] = {
            k: "[scrubbed]" if any(s in k.lower() for s in SENSITIVE_ENV_KEYS) else v
            for k, v in event["extra"].items()
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
