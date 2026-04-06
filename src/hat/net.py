from __future__ import annotations

import json
import socket
import ssl
import subprocess
from datetime import datetime, timezone


def domain_info(domain: str) -> dict:
    """Get WHOIS/RDAP info for a domain."""
    result = subprocess.run(
        ["whois", domain], capture_output=True, text=True
    )
    info = {"domain": domain, "whois_raw": result.stdout}

    # Parse key fields from whois output
    for line in result.stdout.splitlines():
        line = line.strip()
        lower = line.lower()
        if "registrar:" in lower:
            info["registrar"] = line.split(":", 1)[1].strip()
        elif "creation date:" in lower or "created:" in lower:
            info["created"] = line.split(":", 1)[1].strip()
        elif "expir" in lower and "date" in lower:
            info["expires"] = line.split(":", 1)[1].strip()
        elif "name server:" in lower or "nserver:" in lower:
            info.setdefault("nameservers", []).append(line.split(":", 1)[1].strip())

    return info


def cert_info(host: str, port: int = 443) -> dict:
    """Get SSL certificate info."""
    ctx = ssl.create_default_context()
    try:
        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(10)
            s.connect((host, port))
            cert = s.getpeercert()
            der = s.getpeercert(binary_form=True)
    except ssl.SSLCertVerificationError as e:
        # Try without verification to still get cert details
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(10)
            s.connect((host, port))
            cert = s.getpeercert()
            der = s.getpeercert(binary_form=True)
        return _parse_cert(cert, der, chain_error=str(e))

    return _parse_cert(cert, der)


def _parse_cert(cert: dict, der: bytes, chain_error: str | None = None) -> dict:
    info = {}
    if cert:
        # Subject
        subject = dict(x[0] for x in cert.get("subject", ()))
        info["subject"] = subject.get("commonName", "")
        info["organization"] = subject.get("organizationName", "")

        # Issuer
        issuer = dict(x[0] for x in cert.get("issuer", ()))
        info["issuer"] = issuer.get("commonName", "")
        info["issuer_org"] = issuer.get("organizationName", "")

        # Self-signed check
        info["self_signed"] = info["subject"] == info["issuer"]

        # Dates
        not_before = cert.get("notBefore", "")
        not_after = cert.get("notAfter", "")
        info["not_before"] = not_before
        info["not_after"] = not_after

        # Check expiry
        if not_after:
            try:
                expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                info["days_until_expiry"] = (expiry - datetime.now()).days
                info["expired"] = info["days_until_expiry"] < 0
            except ValueError:
                pass

        # SANs
        sans = cert.get("subjectAltName", ())
        info["san"] = [v for _, v in sans]

    if chain_error:
        info["chain_error"] = chain_error

    return info


def ip_info(address: str) -> dict:
    """Get IP address info using ip-api.com."""
    import httpx
    try:
        resp = httpx.get(f"http://ip-api.com/json/{address}", timeout=10)
        data = resp.json()
        return {
            "ip": address,
            "country": data.get("country", ""),
            "region": data.get("regionName", ""),
            "city": data.get("city", ""),
            "isp": data.get("isp", ""),
            "org": data.get("org", ""),
            "as": data.get("as", ""),
            "lookup_url": f"https://ipinfo.io/{address}",
        }
    except Exception as e:
        return {"ip": address, "error": str(e)}


def dns_lookup(domain: str) -> dict:
    """Simplified DNS lookup — A, AAAA, MX, NS, CNAME, TXT."""
    results = {"domain": domain}
    for rtype in ["A", "AAAA", "MX", "NS", "CNAME", "TXT"]:
        result = subprocess.run(
            ["dig", "+short", domain, rtype],
            capture_output=True, text=True,
        )
        records = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
        if records:
            results[rtype] = records
    return results


def net_check(host: str, ports: list[int] | None = None) -> dict:
    """Combined ping + traceroute + port check."""
    results = {"host": host}

    # Ping
    ping_result = subprocess.run(
        ["ping", "-c", "3", "-W", "2", host],
        capture_output=True, text=True,
    )
    results["ping"] = {
        "success": ping_result.returncode == 0,
        "output": ping_result.stdout.strip().splitlines()[-2:] if ping_result.stdout else [],
    }

    # Traceroute (quick, max 15 hops)
    trace_result = subprocess.run(
        ["traceroute", "-m", "15", "-w", "2", host],
        capture_output=True, text=True,
        timeout=30,
    )
    results["traceroute"] = trace_result.stdout.strip().splitlines()[:15]

    # Port check
    if ports:
        port_results = {}
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                port_results[port] = "open" if result == 0 else "closed"
                sock.close()
            except Exception:
                port_results[port] = "error"
        results["ports"] = port_results

    return results
