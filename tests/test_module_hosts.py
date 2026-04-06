from hat.modules.hosts import HostsModule, MARKER_START, MARKER_END


def test_hosts_activate(tmp_path):
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text("127.0.0.1 localhost\n")
    mod = HostsModule(hosts_path=hosts_file)
    config = {
        "entries": [
            "10.0.1.10 grafana.acme.internal",
            "10.0.1.11 vault.acme.internal",
        ]
    }
    mod.activate(config, secrets={})
    content = hosts_file.read_text()
    assert "127.0.0.1 localhost" in content
    assert MARKER_START in content
    assert "10.0.1.10 grafana.acme.internal" in content
    assert MARKER_END in content


def test_hosts_deactivate(tmp_path):
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text("127.0.0.1 localhost\n")
    mod = HostsModule(hosts_path=hosts_file)
    config = {"entries": ["10.0.1.10 grafana.acme.internal"]}
    mod.activate(config, secrets={})
    mod.deactivate()
    content = hosts_file.read_text()
    assert "127.0.0.1 localhost" in content
    assert MARKER_START not in content
    assert "grafana.acme.internal" not in content


def test_hosts_replaces_existing_block(tmp_path):
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text(
        f"127.0.0.1 localhost\n{MARKER_START}\nold entry\n{MARKER_END}\n"
    )
    mod = HostsModule(hosts_path=hosts_file)
    config = {"entries": ["10.0.1.10 new.acme.internal"]}
    mod.activate(config, secrets={})
    content = hosts_file.read_text()
    assert "old entry" not in content
    assert "10.0.1.10 new.acme.internal" in content


def test_hosts_no_config(tmp_path):
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text("127.0.0.1 localhost\n")
    mod = HostsModule(hosts_path=hosts_file)
    mod.activate({}, secrets={})
    assert not mod.status().active
