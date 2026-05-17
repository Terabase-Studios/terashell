from unittest.mock import patch


def test_reset_aborts_by_default(shell_commands, capsys):
    commands, _, _ = shell_commands

    with patch("builtins.input", return_value=""), \
            patch("config.reset_settings") as reset_settings:
        commands.handle_command("reset")

    reset_settings.assert_not_called()
    assert "Aborted." in capsys.readouterr().out


def test_reset_requires_yes(shell_commands, capsys):
    commands, _, _ = shell_commands

    with patch("builtins.input", return_value="y"), \
            patch("config.reset_settings") as reset_settings:
        commands.handle_command("reset")

    reset_settings.assert_called_once()
    assert "configuration reset" in capsys.readouterr().out
