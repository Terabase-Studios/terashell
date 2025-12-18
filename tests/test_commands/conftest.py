import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Add src to path to allow imports
sys.path.insert(0, './src')

from commands import ShellCommands
from input import ShellInput
from background import BackgroundTaskManager

@pytest.fixture
def shell_commands(tmp_path):
    """Fixture to create a ShellCommands instance with a mock shell."""
    # Mock for the shell object
    mock_shell = Mock()
    mock_shell.running = True
    
    # Set the initial working directory to a temporary path
    mock_shell.working_dir = str(tmp_path)
    
    # Add a mock btm
    mock_shell.btm = Mock(spec=BackgroundTaskManager)
    
    # Create the ShellCommands instance first
    commands = ShellCommands(mock_shell)
    # Add it to the mock_shell so ShellInput can use it
    mock_shell.command_handler = commands
    
    # Add a mock input_handler to the shell for history tests
    mock_shell.input_handler = Mock()
    
    # We need to mock os.chdir to not actually change the test runner's CWD
    with patch('os.chdir') as mock_chdir:
        # Yield all the objects that tests might need
        yield commands, mock_shell, mock_chdir
