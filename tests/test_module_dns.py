from unittest.mock import patch

from hat.modules.dns import DNSModule


def test_dns_activate():
    mod = DNSModule()
    config = {
        "resolvers": ["10.0.0.53", "10.0.0.54"],
        "search_domains": ["acme.internal"],
    }
    with (
        patch("hat.modules.dns.click.confirm"),
        patch("hat.platform.configure_dns") as mock_configure,
        patch("hat.platform.get_resolver_dir", return_value=None),
    ):
        mod.activate(config, secrets={})

    mock_configure.assert_called_once_with(
        ["10.0.0.53", "10.0.0.54"], ["acme.internal"]
    )


def test_dns_deactivate():
    mod = DNSModule()
    config = {
        "resolvers": ["10.0.0.53"],
        "search_domains": ["acme.internal", "acme.corp"],
    }
    with (
        patch("hat.modules.dns.click.confirm"),
        patch("hat.platform.configure_dns"),
        patch("hat.platform.get_resolver_dir", return_value=None),
        patch("hat.platform.unconfigure_dns") as mock_unconfigure,
    ):
        mod.activate(config, secrets={})
        mod.deactivate()

    mock_unconfigure.assert_called_once_with(["acme.internal", "acme.corp"])


def test_dns_no_config():
    mod = DNSModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
