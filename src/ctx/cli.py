import click


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Company context switcher."""


@main.command()
def status():
    """Show active company and module states."""
    click.echo("No active context.")
