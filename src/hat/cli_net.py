from __future__ import annotations

import click


@click.group("net")
def net_group():
    """Network diagnostic tools."""


@net_group.command("domain")
@click.argument("domain")
def domain_cmd(domain: str):
    """WHOIS/RDAP info for a domain."""
    from hat.net import domain_info
    info = domain_info(domain)
    click.echo(f"Domain:      {info['domain']}")
    if "registrar" in info:
        click.echo(f"Registrar:   {info['registrar']}")
    if "created" in info:
        click.echo(f"Created:     {info['created']}")
    if "expires" in info:
        click.echo(f"Expires:     {info['expires']}")
    for ns in info.get("nameservers", []):
        click.echo(f"Nameserver:  {ns}")


@net_group.command("cert")
@click.argument("host")
@click.option("-p", "--port", default=443, help="Port number")
def cert_cmd(host: str, port: int):
    """SSL certificate info."""
    from hat.net import cert_info
    info = cert_info(host, port)
    click.echo(f"Subject:     {info.get('subject', 'N/A')}")
    click.echo(f"Issuer:      {info.get('issuer', 'N/A')}")
    click.echo(f"Org:         {info.get('issuer_org', 'N/A')}")
    if info.get("self_signed"):
        click.echo(click.style("Self-signed: YES", fg="yellow"))
    click.echo(f"Valid from:  {info.get('not_before', 'N/A')}")
    click.echo(f"Valid until: {info.get('not_after', 'N/A')}")
    days = info.get("days_until_expiry")
    if days is not None:
        color = "red" if days < 30 else "yellow" if days < 90 else "green"
        click.echo(click.style(f"Expires in:  {days} days", fg=color))
    if info.get("expired"):
        click.echo(click.style("EXPIRED!", fg="red", bold=True))
    if info.get("chain_error"):
        click.echo(click.style(f"Chain error: {info['chain_error']}", fg="red"))
    sans = info.get("san", [])
    if sans:
        click.echo(f"SANs:        {', '.join(sans[:5])}")
        if len(sans) > 5:
            click.echo(f"             ... and {len(sans) - 5} more")


@net_group.command("ip")
@click.argument("address")
def ip_cmd(address: str):
    """IP address info — location, ISP, hosting."""
    from hat.net import ip_info
    info = ip_info(address)
    if "error" in info:
        click.echo(f"Error: {info['error']}")
        return
    click.echo(f"IP:       {info['ip']}")
    click.echo(f"Location: {info['city']}, {info['region']}, {info['country']}")
    click.echo(f"ISP:      {info['isp']}")
    click.echo(f"Org:      {info['org']}")
    click.echo(f"AS:       {info['as']}")
    click.echo(f"Lookup:   {info['lookup_url']}")


@net_group.command("dns")
@click.argument("domain")
def dns_cmd(domain: str):
    """DNS lookup — A, AAAA, MX, NS, CNAME, TXT records."""
    from hat.net import dns_lookup
    info = dns_lookup(domain)
    for rtype in ["A", "AAAA", "CNAME", "MX", "NS", "TXT"]:
        records = info.get(rtype, [])
        if records:
            click.echo(f"\n  {rtype}:")
            for r in records:
                click.echo(f"    {r}")
    if len(info) == 1:  # only domain key
        click.echo("No records found.")


@net_group.command("check")
@click.argument("host")
@click.option("-p", "--port", "ports", multiple=True, type=int, help="Ports to check (repeatable)")
def net_check_cmd(host: str, ports: tuple[int, ...]):
    """Ping + traceroute + port check."""
    from hat.net import net_check
    port_list = list(ports) if ports else [22, 80, 443]
    click.echo(f"Checking {host}...")
    info = net_check(host, port_list)

    # Ping
    ping = info["ping"]
    status = click.style("OK", fg="green") if ping["success"] else click.style("FAIL", fg="red")
    click.echo(f"\nPing: {status}")
    for line in ping["output"]:
        click.echo(f"  {line}")

    # Ports
    if "ports" in info:
        click.echo(f"\nPorts:")
        for port, state in info["ports"].items():
            color = "green" if state == "open" else "red"
            click.echo(f"  {port}: {click.style(state, fg=color)}")

    # Traceroute
    click.echo(f"\nTraceroute:")
    for line in info.get("traceroute", []):
        click.echo(f"  {line}")
