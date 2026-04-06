from unittest.mock import patch, call

from ctx.modules.ssh import SSHModule


def test_ssh_activate_adds_keys():
    mod = SSHModule()
    config = {"keys": ["~/.ssh/acme_ed25519", "~/.ssh/acme_bastion"]}
    with patch("ctx.modules.ssh.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    expected_calls = [
        call(["ssh-add", "~/.ssh/acme_ed25519"], capture_output=True, text=True),
        call(["ssh-add", "~/.ssh/acme_bastion"], capture_output=True, text=True),
    ]
    assert mock_run.call_args_list == expected_calls
    assert mod.status().active


def test_ssh_deactivate_removes_keys():
    mod = SSHModule()
    config = {"keys": ["~/.ssh/acme_ed25519"]}
    with patch("ctx.modules.ssh.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
        mod.deactivate()
    last_call = mock_run.call_args_list[-1]
    assert last_call == call(
        ["ssh-add", "-d", "~/.ssh/acme_ed25519"], capture_output=True, text=True
    )


def test_ssh_no_keys():
    mod = SSHModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
