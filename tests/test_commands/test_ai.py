from unittest.mock import Mock, patch


def test_ai_configure_uses_previous_values_and_saves(shell_commands, monkeypatch):
    commands, _, _ = shell_commands

    monkeypatch.setattr("config.AI_SERVER_IP", "http://localhost:11434")
    monkeypatch.setattr("config.AI_API_KEY", "old-key")
    monkeypatch.setattr("config.AI_MODEL", "old-model")

    inputs = iter(["", "", "", "new-model"])
    mock_interface = Mock()

    with patch("builtins.input", side_effect=lambda prompt: next(inputs)), \
            patch("ai.AIInterface", return_value=mock_interface) as MockAIInterface, \
            patch("config.save_settings") as save_settings:
        commands.handle_command("ai configure")

    MockAIInterface.assert_called_once_with("http://localhost:11434", "old-key")
    mock_interface.print_models.assert_called_once()
    save_settings.assert_called_once_with(
        AI_SERVER_IP="http://localhost:11434",
        AI_API_KEY="old-key",
        AI_MODEL="new-model",
    )


def test_ai_configure_saves_model_name_when_user_enters_index(shell_commands, monkeypatch):
    commands, _, _ = shell_commands

    monkeypatch.setattr("config.AI_SERVER_IP", "http://localhost:11434")
    monkeypatch.setattr("config.AI_API_KEY", "")
    monkeypatch.setattr("config.AI_MODEL", "old-model")

    model_0 = Mock(id="first-model")
    model_1 = Mock(id="second-model")
    mock_interface = Mock()
    mock_interface.get_models.return_value = [model_0, model_1]
    inputs = iter(["", "", "", "1"])

    with patch("builtins.input", side_effect=lambda prompt: next(inputs)), \
            patch("ai.AIInterface", return_value=mock_interface), \
            patch("config.save_settings") as save_settings:
        commands.handle_command("ai configure")

    save_settings.assert_called_once_with(
        AI_SERVER_IP="http://localhost:11434",
        AI_API_KEY="",
        AI_MODEL="second-model",
    )


def test_ai_configure_only_shows_in_full_help(shell_commands):
    commands, _, _ = shell_commands

    assert "ai configure" not in commands.help_simple
    assert "ai configure" in commands.help
    assert "ai configure" in commands.get_commands()


def test_ai_configure_accepts_new_connection_values(shell_commands, monkeypatch):
    commands, _, _ = shell_commands

    monkeypatch.setattr("config.AI_SERVER_IP", "")
    monkeypatch.setattr("config.AI_API_KEY", "")
    monkeypatch.setattr("config.AI_MODEL", "none")

    inputs = iter(["https://ai.local", "8080", "new-key", "model-a"])

    with patch("builtins.input", side_effect=lambda prompt: next(inputs)), \
            patch("ai.AIInterface") as MockAIInterface, \
            patch("config.save_settings") as save_settings:
        commands.handle_command("ai configure")

    MockAIInterface.assert_called_once_with("https://ai.local:8080", "new-key")
    save_settings.assert_called_once_with(
        AI_SERVER_IP="https://ai.local:8080",
        AI_API_KEY="new-key",
        AI_MODEL="model-a",
    )


def test_ai_command_tells_user_to_configure_when_missing_model(shell_commands, monkeypatch, capsys):
    commands, _, _ = shell_commands

    monkeypatch.setattr("config.AI_SERVER_IP", "http://localhost:11434")
    monkeypatch.setattr("config.AI_MODEL", "none")

    with patch("ai.init") as init:
        commands.handle_command("ai")

    init.assert_not_called()
    assert "Run: ai configure" in capsys.readouterr().out


def test_ai_command_tells_user_to_configure_when_connection_fails(shell_commands, monkeypatch, capsys):
    commands, _, _ = shell_commands

    monkeypatch.setattr("config.AI_SERVER_IP", "http://localhost:11434")
    monkeypatch.setattr("config.AI_MODEL", "model-a")
    monkeypatch.setattr("config.AI_ENABLED", False)

    with patch("ai.init") as init:
        commands.handle_command("ai")

    init.assert_called_once()
    assert "Run: ai configure" in capsys.readouterr().out
