from __future__ import annotations

import click


@click.group("tools")
def tools_group():
    """Manage company tools."""


@tools_group.command("check")
def tools_check():
    """Check and install/update tools from ~/projects/common/tools.yaml."""
    from hat.common import load_common_tools
    tools_config = load_common_tools()
    if not tools_config:
        click.echo("No tools configured. Run 'hat tools init' first.")
        return
    from hat.modules.tools import ToolsModule
    mod = ToolsModule()
    mod.activate(tools_config, secrets={})


@tools_group.command("init")
def tools_init():
    """Generate ~/projects/common/tools.yaml with default tools."""
    from hat.common import generate_tools_config
    path = generate_tools_config()
    click.echo(f"Generated {path}")
    click.echo("Edit the file to customize your tools list.")


@click.group()
def aliases():
    """Manage shell aliases."""


@aliases.command("generate")
def aliases_generate():
    """Generate ~/projects/common/aliases.sh."""
    from hat.common import generate_aliases
    path = generate_aliases()
    click.echo(f"Generated {path}")


@click.group()
def completions():
    """Manage shell completions."""


@completions.command("generate")
def completions_generate():
    """Generate ~/projects/common/completions.sh."""
    from hat.common import generate_completions
    path = generate_completions()
    click.echo(f"Generated {path}")


@click.group()
def skills():
    """Manage Claude Code skills."""


@skills.command("deploy")
def skills_deploy():
    """Deploy skills to ~/projects/.claude/skills/ as symlinks."""
    from hat.skills import get_skills_source, deploy_skills
    source = get_skills_source()
    if not source.exists():
        click.echo(f"Skills source not found: {source}")
        return
    deployed = deploy_skills(source)
    if deployed:
        click.echo(f"Deployed {len(deployed)} skills: {', '.join(deployed)}")
    else:
        click.echo("All skills already deployed.")
