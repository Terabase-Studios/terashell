from pathlib import Path

def test_cd_to_home(shell_commands):
    """Test 'cd' with no arguments, should change to home directory."""
    commands, shell, mock_chdir = shell_commands
    home_dir = str(Path.home())
    
    commands.handle_command("cd")
    
    # Assert that the shell's working directory is updated
    assert shell.working_dir == home_dir
    # Assert that os.chdir was called with the home directory
    mock_chdir.assert_called_with(home_dir)

def test_cd_to_specific_dir(shell_commands):
    """Test 'cd' to a specific existing directory."""
    commands, shell, mock_chdir = shell_commands
    
    # Create a subdirectory in the temp path
    specific_dir = Path(shell.working_dir) / "specific_dir"
    specific_dir.mkdir()
    
    commands.handle_command(f"cd {specific_dir}")
    
    # Assert that the shell's working directory is updated
    assert shell.working_dir == str(specific_dir)
    # Assert that os.chdir was called with the correct path
    mock_chdir.assert_called_with(str(specific_dir))

def test_cd_to_non_existent_dir(shell_commands, capsys):
    """Test 'cd' to a non-existent directory, should print an error."""
    commands, shell, mock_chdir = shell_commands
    initial_dir = shell.working_dir
    non_existent_dir = "non_existent_dir"
    
    commands.handle_command(f"cd {non_existent_dir}")
    
    # Assert that the working directory has NOT changed
    assert shell.working_dir == initial_dir
    # Assert that os.chdir was NOT called
    mock_chdir.assert_not_called()
    
    # Capture the output and check for the error message
    captured = capsys.readouterr()
    assert "no such directory" in captured.out

def test_cd_with_tilde_expansion(shell_commands):
    """Test 'cd' with '~' expansion."""
    commands, shell, mock_chdir = shell_commands
    home_dir = str(Path.home())
    
    commands.handle_command("cd ~")
    
    # Assert that the shell's working directory is updated to home
    assert shell.working_dir == home_dir
    # Assert that os.chdir was called with the home directory
    mock_chdir.assert_called_with(home_dir)
