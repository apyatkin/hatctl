from __future__ import annotations

import click


@click.group("secret")
def secret_group():
    """Manage secrets."""


@secret_group.command("set")
@click.argument("ref")
@click.option("--file", "-f", "file_path", type=click.Path(exists=True), help="Read value from file")
def secret_set(ref: str, file_path: str | None):
    """Store a secret. Use -f for multiline values (SSH keys, certs)."""
    from hat.secrets import parse_secret_ref
    import base64
    import subprocess
    backend, path = parse_secret_ref(ref)

    if file_path:
        value = open(file_path).read()
    else:
        click.echo("Enter secret value (paste multiline, then Ctrl-D when done):")
        import sys
        value = sys.stdin.read()

    if backend == "keychain":
        encoded = base64.b64encode(value.encode()).decode()
        subprocess.run(
            ["security", "add-generic-password", "-s", path, "-a", path,
             "-w", encoded, "-U"],
            check=True,
        )
        click.echo(f"Stored in keychain: {path}")
    elif backend == "bitwarden":
        click.echo("Bitwarden secrets must be stored via the bw CLI or web vault.")


@secret_group.command("get")
@click.argument("ref")
def secret_get(ref: str):
    """Display a secret value."""
    from hat.secrets import SecretResolver
    from hat.activity_log import log_event
    resolver = SecretResolver()
    value = resolver._resolve_one(ref)
    log_event("secret-get", "keychain" if ref.startswith("keychain:") else "bitwarden", [ref])
    click.echo(value)
