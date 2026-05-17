def test_register_subcommand_handler(shell_commands):
    commands, _, _ = shell_commands
    calls = []

    commands.register("demo run", calls.append, help="Run demo.")

    assert "demo run" in commands.get_commands()
    assert commands.handle_command("demo run one two") is True
    assert calls == [["one", "two"]]


def test_parent_handler_receives_unknown_or_unhandled_subcommands(shell_commands):
    commands, _, _ = shell_commands
    calls = []

    commands.register("demo", calls.append, help="Demo command.")
    commands.register("demo known", help="Known demo subcommand.")

    assert commands.handle_command("demo known value") is True
    assert commands.handle_command("demo other value") is True
    assert calls == [["known", "value"], ["other", "value"]]
