"""Platform abstraction for macOS, Ubuntu, and Rocky Linux."""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path


SYSTEM = platform.system()  # "Darwin", "Linux"


def get_default_config_dir() -> Path:
    if SYSTEM == "Darwin":
        return Path.home() / "Library" / "hat"
    return Path.home() / ".config" / "hat"


def open_url(url: str) -> None:
    if SYSTEM == "Darwin":
        subprocess.Popen(["open", url])
    else:
        subprocess.Popen(["xdg-open", url])


def open_browser_with_profile(app: str, profile: str) -> None:
    if SYSTEM == "Darwin":
        APP_MAP = {
            "google-chrome": "Google Chrome",
            "firefox": "Firefox",
            "arc": "Arc",
        }
        app_name = APP_MAP.get(app, app)
        subprocess.Popen(
            ["open", "-a", app_name, "--args", f"--profile-directory={profile}"],
        )
    else:
        # Linux: launch browser directly
        LINUX_BINS = {
            "google-chrome": "google-chrome",
            "firefox": "firefox",
            "arc": "arc",
        }
        binary = LINUX_BINS.get(app, app)
        if "chrome" in binary.lower():
            subprocess.Popen([binary, f"--profile-directory={profile}"])
        else:
            subprocess.Popen([binary])


def send_notification(title: str, message: str) -> None:
    if SYSTEM == "Darwin":
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.Popen(
            [
                "osascript",
                "-e",
                f'display notification "{safe_message}" with title "{safe_title}"',
            ]
        )
    else:
        # Linux: notify-send
        subprocess.Popen(["notify-send", title, message])


def store_secret(name: str, value_base64: str) -> bool:
    """Store a base64-encoded secret in the platform's credential store."""
    if SYSTEM == "Darwin":
        result = subprocess.run(
            [
                "security",
                "add-generic-password",
                "-s",
                name,
                "-a",
                name,
                "-w",
                value_base64,
                "-U",
            ],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    else:
        # Linux: use keyring library
        import keyring

        keyring.set_password("hat", name, value_base64)
        return True


def get_secret(name: str) -> str | None:
    """Get a base64-encoded secret from the platform's credential store."""
    if SYSTEM == "Darwin":
        result = subprocess.run(
            ["security", "find-generic-password", "-s", name, "-w"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    else:
        import keyring

        return keyring.get_password("hat", name)


def delete_secret(name: str) -> bool:
    """Delete a secret from the platform's credential store."""
    if SYSTEM == "Darwin":
        result = subprocess.run(
            ["security", "delete-generic-password", "-s", name],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    else:
        import keyring

        try:
            keyring.delete_password("hat", name)
            return True
        except keyring.errors.PasswordDeleteError:
            return False


def get_resolver_dir() -> Path | None:
    """Get DNS resolver directory. macOS only."""
    if SYSTEM == "Darwin":
        return Path("/etc/resolver")
    return None


def configure_dns(resolvers: list[str], domains: list[str]) -> None:
    """Configure DNS resolvers."""
    if SYSTEM == "Darwin":
        resolver_dir = Path("/etc/resolver")
        resolver_dir.mkdir(parents=True, exist_ok=True)
        content = "\n".join(f"nameserver {r}" for r in resolvers) + "\n"
        for domain in domains:
            (resolver_dir / domain).write_text(content)
    else:
        # Linux: use systemd-resolved if available
        if shutil.which("resolvectl"):
            for r in resolvers:
                subprocess.run(
                    ["sudo", "resolvectl", "dns", "hat0", r],
                    capture_output=True,
                )
            for d in domains:
                subprocess.run(
                    ["sudo", "resolvectl", "domain", "hat0", d],
                    capture_output=True,
                )
        # Fallback: not supported on basic Linux setups


def unconfigure_dns(domains: list[str]) -> None:
    """Remove DNS resolver config."""
    if SYSTEM == "Darwin":
        for domain in domains:
            path = Path("/etc/resolver") / domain
            if path.exists():
                path.unlink()


def find_binary_paths() -> list[str]:
    """Additional paths to search for binaries."""
    if SYSTEM == "Darwin":
        return ["/opt/homebrew/bin", "/usr/local/bin"]
    else:
        return ["/home/linuxbrew/.linuxbrew/bin", "/usr/local/bin", "/snap/bin"]


def get_package_manager() -> str:
    """Detect the system package manager for Linux."""
    if SYSTEM == "Darwin":
        return "brew"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("apt"):
        return "apt"
    if shutil.which("brew"):
        return "brew"
    return "unknown"
