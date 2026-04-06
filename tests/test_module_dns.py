from unittest.mock import patch

from ctx.modules.dns import DNSModule


def test_dns_activate(tmp_path):
    mod = DNSModule()
    config = {
        "resolvers": ["10.0.0.53", "10.0.0.54"],
        "search_domains": ["acme.internal"],
    }
    with patch("ctx.modules.dns.RESOLVER_DIR", tmp_path), \
         patch("ctx.modules.dns.click.confirm"):
        mod.activate(config, secrets={})

    resolver_file = tmp_path / "acme.internal"
    assert resolver_file.exists()
    content = resolver_file.read_text()
    assert "nameserver 10.0.0.53" in content
    assert "nameserver 10.0.0.54" in content


def test_dns_deactivate(tmp_path):
    mod = DNSModule()
    config = {
        "resolvers": ["10.0.0.53"],
        "search_domains": ["acme.internal", "acme.corp"],
    }
    with patch("ctx.modules.dns.RESOLVER_DIR", tmp_path), \
         patch("ctx.modules.dns.click.confirm"):
        mod.activate(config, secrets={})
        mod.deactivate()

    assert not (tmp_path / "acme.internal").exists()
    assert not (tmp_path / "acme.corp").exists()


def test_dns_no_config():
    mod = DNSModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
