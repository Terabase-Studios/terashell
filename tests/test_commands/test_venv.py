import os
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

# No global sys.path.insert or config mock, these are handled by conftest.py

import os
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

# No global sys.path.insert or config mock, these are handled by conftest.py

def test_activate_venv(shell_commands, monkeypatch):
    """Test that 'activate <venv_path>' correctly sets environment variables."""
    commands, shell, _ = shell_commands
    
    # Platform-aware setup
    is_windows = os.name == 'nt'
    bindir_name = "Scripts" if is_windows else "bin"
    python_exe_name = "python.exe" if is_windows else "python"
    
    # Let the test use the actual value from the config module
    monkeypatch.setattr('config.IS_WINDOWS', is_windows)
    
    # Create a mock venv structure that matches the OS
    venv_path = Path(shell.working_dir) / "my_test_venv"
    bindir = venv_path / bindir_name
    bindir.mkdir(parents=True)
    (bindir / python_exe_name).touch()
    
    original_path = os.environ.get("PATH", "")
    
    with patch('subprocess.run') as mock_subprocess_run:
        mock_subprocess_run.return_value.stdout = "Python 3.9.7"
        mock_subprocess_run.return_value.stderr = ""
        mock_subprocess_run.return_value.returncode = 0

        commands.handle_command(f"activate {venv_path}")
        
        assert os.environ["VIRTUAL_ENV"] == str(venv_path)
        
        assert str(bindir) in os.environ["PATH"]
        assert os.environ["PATH"].startswith(str(bindir))
        
        assert shell.active_venv == venv_path.name
        assert shell.active_venv_version == "3.9.7"
        
        mock_subprocess_run.assert_called_once_with(
            [str(bindir / python_exe_name), "--version"],
            capture_output=True, text=True
        )

def test_deactivate_venv(shell_commands, monkeypatch):
    """Test that 'deactivate' correctly restores environment variables."""
    commands, shell, _ = shell_commands
    
    # Platform-aware setup
    is_windows = os.name == 'nt'
    bindir_name = "Scripts" if is_windows else "bin"
    
    monkeypatch.setattr('config.IS_WINDOWS', is_windows)
    
    # --- First, activate a mock venv ---
    venv_path = Path(shell.working_dir) / "my_test_venv_deact"
    bindir = venv_path / bindir_name
    bindir.mkdir(parents=True)
    
    original_path = os.environ.get("PATH", "")
    monkeypatch.setitem(os.environ, "VIRTUAL_ENV", str(venv_path))
    monkeypatch.setitem(os.environ, "PATH", str(bindir) + os.pathsep + original_path)
    shell.active_venv = venv_path.name
    shell.active_venv_version = "3.9.7"
    # --- Mock venv activated ---

    commands.handle_command("deactivate")
    
    assert "VIRTUAL_ENV" not in os.environ
    
    assert str(bindir) not in os.environ["PATH"]
    assert os.environ["PATH"] == original_path
    
    assert shell.active_venv is None
    assert shell.active_venv_version is None


def test_activate_non_existent_venv(shell_commands, capsys, monkeypatch):
    """Test 'activate' with a non-existent venv path."""
    commands, shell, _ = shell_commands
    
    # Platform-aware setup
    is_windows = os.name == 'nt'
    monkeypatch.setattr('config.IS_WINDOWS', is_windows)
    
    initial_environ = os.environ.copy()
    
    shell.active_venv = None
    shell.active_venv_version = None
    
    commands.handle_command("activate /non/existent/venv")
    
    assert os.environ.get("VIRTUAL_ENV") == initial_environ.get("VIRTUAL_ENV")
    assert os.environ.get("PATH") == initial_environ.get("PATH")
    
    assert shell.active_venv is None
    assert shell.active_venv_version is None
    
    captured = capsys.readouterr()
    assert "Did not find a valid virtual environment" in captured.out
    assert "Could not find python in" in captured.out
