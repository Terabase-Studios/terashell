def test_exit_command(shell_commands):
    """Test that the exit command sets the shell's running flag to False."""
    commands, shell, _ = shell_commands
    commands.handle_command("exit")
    assert shell.running is False
