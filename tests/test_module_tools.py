import json
import time
from unittest.mock import patch, MagicMock

from ctx.modules.tools import ToolsModule


def test_tools_installs_missing_brew(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = ToolsModule()
    config = {"brew": ["kubectl", "helm"], "pipx": []}

    def fake_which(name):
        return None  # nothing installed

    with patch("ctx.modules.tools.shutil.which", side_effect=fake_which), \
         patch("ctx.modules.tools.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mod.activate(config, secrets={})

    brew_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][0] == "brew" and c.args[0][1] == "install"
    ]
    assert len(brew_calls) == 2


def test_tools_installs_missing_pipx(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = ToolsModule()
    config = {"brew": [], "pipx": ["ansible", "ruff"]}

    with patch("ctx.modules.tools.shutil.which", return_value=None), \
         patch("ctx.modules.tools.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mod.activate(config, secrets={})

    uv_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][:3] == ["uv", "tool", "install"]
    ]
    assert len(uv_calls) == 2


def test_tools_skips_installed(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    # Pre-populate tools_state.json with recent timestamps
    state_file = tmp_path / "tools_state.json"
    now = time.time()
    state_file.write_text(json.dumps({"kubectl": now, "helm": now}))

    mod = ToolsModule()
    config = {"brew": ["kubectl", "helm"], "pipx": []}

    with patch("ctx.modules.tools.shutil.which", return_value="/usr/local/bin/kubectl"), \
         patch("ctx.modules.tools.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mod.activate(config, secrets={})

    # No install or upgrade calls expected
    install_calls = [
        c for c in mock_run.call_args_list
        if len(c.args[0]) > 1 and c.args[0][1] in ("install", "upgrade")
    ]
    assert len(install_calls) == 0


def test_tools_no_config():
    mod = ToolsModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
