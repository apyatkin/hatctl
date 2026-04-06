import yaml
from click.testing import CliRunner

from hat.cli import main
from hat.config import set_nested


def _setup_company(tmp_path, name="acme"):
    company_dir = tmp_path / "companies" / name
    company_dir.mkdir(parents=True)
    config = {"name": name, "ssh": {"keys": []}, "cloud": {}}
    (company_dir / "config.yaml").write_text(yaml.dump(config))


def test_set_nested_simple():
    config = {}
    set_nested(config, "cloud.nomad.addr", "https://nomad.acme.com")
    assert config["cloud"]["nomad"]["addr"] == "https://nomad.acme.com"


def test_set_nested_append():
    config = {"ssh": {"keys": ["~/.ssh/old"]}}
    set_nested(config, "ssh.keys[+]", "~/.ssh/new")
    assert config["ssh"]["keys"] == ["~/.ssh/old", "~/.ssh/new"]


def test_set_nested_append_creates_list():
    config = {"ssh": {}}
    set_nested(config, "ssh.keys[+]", "~/.ssh/key")
    assert config["ssh"]["keys"] == ["~/.ssh/key"]


def test_config_set_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["config", "set", "acme", "cloud.nomad.addr", "https://nomad.acme.com"])
    assert result.exit_code == 0

    config = yaml.safe_load((tmp_path / "companies" / "acme" / "config.yaml").read_text())
    assert config["cloud"]["nomad"]["addr"] == "https://nomad.acme.com"


def test_config_add_ssh_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["config", "add-ssh", "acme", "~/.ssh/acme_ed25519"])
    assert result.exit_code == 0

    config = yaml.safe_load((tmp_path / "companies" / "acme" / "config.yaml").read_text())
    assert "~/.ssh/acme_ed25519" in config["ssh"]["keys"]


def test_config_add_ssh_appends(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path)
    runner = CliRunner()
    runner.invoke(main, ["config", "add-ssh", "acme", "~/.ssh/key1"])
    runner.invoke(main, ["config", "add-ssh", "acme", "~/.ssh/key2"])

    config = yaml.safe_load((tmp_path / "companies" / "acme" / "config.yaml").read_text())
    assert config["ssh"]["keys"] == ["~/.ssh/key1", "~/.ssh/key2"]
