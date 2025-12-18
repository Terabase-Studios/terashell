from unittest.mock import patch, MagicMock
import pytest
import os
import json
from pathlib import Path

# Need to import CommandIndexer and HelpIndexer from src.indexer
from indexer import CommandIndexer, HelpIndexer

# Mock the HELP_FILE constant to use a temporary file for tests
@pytest.fixture(autouse=True)
def mock_help_file(tmp_path):
    temp_help_file = tmp_path / "test_help_index.json"
    with patch('indexer.HELP_FILE', new=str(temp_help_file)):
        yield

@pytest.fixture
def mock_command_indexer():
    with patch('indexer.CommandIndexer._get_all_commands', return_value=[]) :
        ci = CommandIndexer(index_path=False) # Don't index actual path in tests
        yield ci

@pytest.fixture
def help_indexer_instance():
    # Ensure a fresh HelpIndexer for each test
    hi = HelpIndexer()
    hi.data = {} # Clear any loaded data
    hi.json_path.unlink(missing_ok=True) # Ensure file doesn't exist
    yield hi
    hi.json_path.unlink(missing_ok=True) # Clean up after test


def test_map_tool_parses_simple_help_output(mock_command_indexer, help_indexer_instance):
    """
    Test that map_tool correctly parses a simple --help output and populates
    the help_indexer's data.
    """
    mock_help_output = """
Usage: test_command [OPTIONS] COMMAND [ARGS]...

  This is a test command.

Options:
  --help     Show this message and exit.
  -v, --verbose  Enable verbose output.
  --config <FILE>  Specify config file.

Commands:
  subcommand1  Description for subcommand1.
  subcommand2  Description for subcommand2.
"""
    
    # Patch _get_help to return our mock output
    with patch.object(help_indexer_instance, '_get_help', return_value=mock_help_output), \
         patch('indexer.yaspin') as mock_yaspin, \
         patch('indexer.subprocess.run'): # Patch subprocess.run that might be called if _get_help fails

        # Call map_tool
        help_indexer_instance.map_tool("test_command")

        # Assert that data has been populated correctly
        assert "test_command" in help_indexer_instance.data
        command_data = help_indexer_instance.data["test_command"]

        assert command_data["command"] == ["test_command"]
        assert "subcommand1" in command_data["subcommands"]
        assert "subcommand2" in command_data["subcommands"]

        # Check options parsing - should group [-v, --verbose] and [--config]
        expected_options = sorted([
            sorted(["-v", "--verbose"]),
            sorted(["--config"])
        ])
        actual_options = sorted([sorted(opt) for opt in command_data["options"]])
        assert actual_options == expected_options

        # Check that spinner was used
        mock_yaspin.assert_called_once()
        mock_yaspin.return_value.__enter__.return_value.text.__setitem__.assert_called()

def test_map_tool_handles_no_help_output(mock_command_indexer, help_indexer_instance):
    """
    Test that map_tool handles commands with no useful --help output.
    """
    # Patch _get_help to return empty string
    with patch.object(help_indexer_instance, '_get_help', return_value=""), \
         patch('indexer.yaspin'), \
         patch('indexer.subprocess.run'), \
         patch('builtins.print') as mock_print: # Mock print to check error message

        help_indexer_instance.map_tool("no_help_command")

        # Assert that no data was added for this command
        assert "no_help_command" not in help_indexer_instance.data
        mock_print.assert_any_call(
            """Unable to find help for "no_help_command"
The tool did not return any help text."""
        )

def test_map_tool_handles_recursive_subcommands(mock_command_indexer, help_indexer_instance):
    """
    Test that map_tool correctly handles recursive subcommand parsing.
    """
    # Define a dictionary of mock help outputs for different command combinations
    help_outputs = {
        "main_command": """
Usage: main_command [OPTIONS] COMMAND

Commands:
  sub_command1
  sub_command2
""",
        "main_command sub_command1": """
Usage: main_command sub_command1 [OPTIONS]

Options:
  --flag_sub1

Commands:
  sub_sub_command1
""",
        "main_command sub_command1 sub_sub_command1": """
Usage: main_command sub_command1 sub_sub_command1 [OPTIONS]

Options:
  --flag_sub_sub1
"""
    }

    # Custom _get_help implementation to return specific outputs based on base_cmd and flag
    def custom_get_help(base_cmd, flag):
        cmd_str = " ".join(base_cmd)
        if cmd_str in help_outputs:
            return help_outputs[cmd_str]
        return "" # Default for other combinations

    with patch.object(help_indexer_instance, '_get_help', side_effect=custom_get_help), \
         patch('indexer.yaspin'), \
         patch('indexer.subprocess.run'):
        
        help_indexer_instance.map_tool("main_command", recursive_depth=3)

        assert "main_command" in help_indexer_instance.data
        main_data = help_indexer_instance.data["main_command"]

        assert "sub_command1" in main_data["subcommands"]
        assert "sub_command2" in main_data["subcommands"]

        # Check sub_command1 branch
        assert "sub_command1" in main_data["branches"]
        sub1_data = main_data["branches"]["sub_command1"]
        assert ["--flag_sub1"] in sub1_data["options"] # Should be a list of lists

        # Check sub_sub_command1 branch
        assert "sub_sub_command1" in sub1_data["subcommands"]
        assert "sub_sub_command1" in sub1_data["branches"]
        sub_sub1_data = sub1_data["branches"]["sub_sub_command1"]
        assert ["--flag_sub_sub1"] in sub_sub1_data["options"]
