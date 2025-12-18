def test_bg_tasks_calls_task_table(shell_commands):
    """Test that 'bg tasks' command calls btm.task_table."""
    commands, shell, _ = shell_commands
    
    commands.handle_command("bg tasks")
    
    shell.btm.task_table.assert_called_once()

def test_bg_output_calls_show_output(shell_commands):
    """Test that 'bg output <id>' command calls btm.show_output with correct id."""
    commands, shell, _ = shell_commands
    task_id = 123
    
    commands.handle_command(f"bg output {task_id}")
    
    shell.btm.show_output.assert_called_once_with(task_id)

def test_bg_kill_calls_kill(shell_commands):
    """Test that 'bg kill <id>' command calls btm.kill with correct id."""
    commands, shell, _ = shell_commands
    task_id = 456
    
    commands.handle_command(f"bg kill {task_id}")
    
    shell.btm.kill.assert_called_once_with(task_id)

def test_bg_invalid_subcommand_prints_usage(shell_commands, capsys):
    """Test that 'bg invalid' prints usage."""
    commands, shell, _ = shell_commands
    
    commands.handle_command("bg invalid")
    
    captured = capsys.readouterr()
    assert "Usage: bg <command>" in captured.out
    shell.btm.task_table.assert_not_called()
    shell.btm.show_output.assert_not_called()
    shell.btm.kill.assert_not_called()

def test_bg_no_subcommand_prints_usage(shell_commands, capsys):
    """Test that 'bg' with no subcommand prints usage."""
    commands, shell, _ = shell_commands
    
    commands.handle_command("bg")
    
    captured = capsys.readouterr()
    assert "Usage: bg <command>" in captured.out
    shell.btm.task_table.assert_not_called()
    shell.btm.show_output.assert_not_called()
    shell.btm.kill.assert_not_called()

def test_bg_output_missing_id_prints_usage(shell_commands, capsys):
    """Test that 'bg output' without id prints usage."""
    commands, shell, _ = shell_commands
    
    commands.handle_command("bg output")
    
    captured = capsys.readouterr()
    assert "Usage: bg output <id>" in captured.out
    shell.btm.show_output.assert_not_called()

def test_bg_kill_missing_id_prints_usage(shell_commands, capsys):
    """Test that 'bg kill' without id prints usage."""
    commands, shell, _ = shell_commands
    
    commands.handle_command("bg kill")
    
    captured = capsys.readouterr()
    assert "Usage: kill <id>" in captured.out
    shell.btm.kill.assert_not_called()
