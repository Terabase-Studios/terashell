from unittest.mock import patch, MagicMock
from pathlib import Path
from config import INSTR_FILE

def test_instr_add_calls_add(shell_commands):
    """Test that 'instr add <text>' command calls instr_helper.add with correct text."""
    commands, shell, _ = shell_commands
    
    with patch('commands.InstructionHelper') as MockInstructionHelper, \
         patch('shell.instance_file', return_value="/tmp/test_instr_file.json") as mock_instance_file:
        
        commands.handle_command("instr add some instruction text")
        
        mock_instance_file.assert_called_once_with(shell.instance, INSTR_FILE)
        MockInstructionHelper.assert_called_once_with("/tmp/test_instr_file.json")
        MockInstructionHelper.return_value.add.assert_called_once_with("some instruction text")

def test_instr_remove_calls_remove(shell_commands):
    """Test that 'instr remove' command calls instr_helper.remove."""
    commands, shell, _ = shell_commands
    
    with patch('commands.InstructionHelper') as MockInstructionHelper, \
         patch('shell.instance_file', return_value="/tmp/test_instr_file.json") as mock_instance_file:
        
        commands.handle_command("instr remove")
        
        mock_instance_file.assert_called_once_with(shell.instance, INSTR_FILE)
        MockInstructionHelper.assert_called_once_with("/tmp/test_instr_file.json")
        MockInstructionHelper.return_value.remove.assert_called_once()

def test_instr_list_calls_list_and_prints(shell_commands, capsys):
    """Test that 'instr list' command calls instr_helper.list and prints its output."""
    commands, shell, _ = shell_commands
    
    with patch('commands.InstructionHelper') as MockInstructionHelper, \
         patch('shell.instance_file', return_value="/tmp/test_instr_file.json") as mock_instance_file:
        
        MockInstructionHelper.return_value.list.return_value = "1. test instruction"
        
        commands.handle_command("instr list")
        
        mock_instance_file.assert_called_once_with(shell.instance, INSTR_FILE)
        MockInstructionHelper.assert_called_once_with("/tmp/test_instr_file.json")
        MockInstructionHelper.return_value.list.assert_called_once()
        captured = capsys.readouterr()
        assert "1. test instruction" in captured.out

def test_instr_save_calls_save_markdown(shell_commands):
    """Test that 'instr save <filename>' command calls instr_helper.save_markdown with correct filename."""
    commands, shell, _ = shell_commands
    
    with patch('commands.InstructionHelper') as MockInstructionHelper, \
         patch('shell.instance_file', return_value="/tmp/test_instr_file.json") as mock_instance_file:
        
        filename = "test_instructions.md"
        shell.working_dir = "/tmp" # Set a mock working directory
        
        commands.handle_command(f"instr save {filename}")
        
        expected_filepath = str(Path("/tmp") / filename)
        mock_instance_file.assert_called_once_with(shell.instance, INSTR_FILE)
        MockInstructionHelper.assert_called_once_with("/tmp/test_instr_file.json")
        MockInstructionHelper.return_value.save_markdown.assert_called_once_with(expected_filepath)

def test_instr_clear_calls_clear(shell_commands):
    """Test that 'instr clear' command calls instr_helper.clear."""
    commands, shell, _ = shell_commands
    
    with patch('commands.InstructionHelper') as MockInstructionHelper, \
         patch('shell.instance_file', return_value="/tmp/test_instr_file.json") as mock_instance_file:
        
        commands.handle_command("instr clear")
        
        mock_instance_file.assert_called_once_with(shell.instance, INSTR_FILE)
        MockInstructionHelper.assert_called_once_with("/tmp/test_instr_file.json")
        MockInstructionHelper.return_value.clear.assert_called_once()
