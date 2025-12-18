def test_history_print(shell_commands):
    """Test that 'history' command calls the input_handler's print_history."""
    commands, shell, _ = shell_commands
    
    commands.handle_command("history")
    
    # Assert that the print_history method was called
    shell.input_handler.print_history.assert_called_once()

def test_history_clear(shell_commands):
    """Test that 'history clear' command calls the input_handler's clear_history."""
    commands, shell, _ = shell_commands
    
    commands.handle_command("history clear")
    
    # Assert that the clear_history method was called
    shell.input_handler.clear_history.assert_called_once()
