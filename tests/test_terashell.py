import sys
import os
import pytest
from unittest import mock
import threading
import time # Added for sleep in debug

# We need to import the main function from TeraShell to test it.
# This relies on the pytest.ini configuration `pythonpath = src`.
from TeraShell import main

@pytest.fixture
def mock_subprocess_run():
    """Fixture to mock subprocess.run."""
    with mock.patch("subprocess.run") as mock_run:
        yield mock_run

def run_with_timeout(func, timeout=5):
    """Run func in a thread, fail if it doesn't finish within timeout seconds."""
    result = {}
    def target():
        try:
            func()
            result["finished"] = True
        except Exception as e:
            result["exception"] = e

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        print(f"\nTest timed out after {timeout}s ---")
        pytest.fail(f"Test timed out after {timeout}s")
    if "exception" in result:
        raise result["exception"]


# --- Tests for -c argument with timeout ---
def test_c_argument_success(monkeypatch, mock_subprocess_run):
    """Verifies '-c <command>' runs successfully."""
    def inner():
        test_command = 'echo "Terashell -c test successful"'
        print(f"\n[test_c_argument_success] --- Running Test ---")
        print(f"[test_c_argument_success] Test command: {test_command}")

        monkeypatch.setattr(sys, "argv", ["TeraShell.py", "-c", test_command])
        print(f"[test_c_argument_success] sys.argv set to: {sys.argv}")

        mock_subprocess_run.return_value.returncode = 0

        with pytest.raises(SystemExit) as e:
            main()

        mock_subprocess_run.assert_called_once_with(test_command, shell=True, env=os.environ)
        print(f"[test_c_argument_success] mock_subprocess_run called with: {mock_subprocess_run.call_args}")

        assert e.value.code == 0
        print(f"[test_c_argument_success] Exit code: {e.value.code}")
        print(f"[test_c_argument_success] --- Test Finished ---")

    run_with_timeout(inner, timeout=1)

def test_c_argument_failure(monkeypatch, mock_subprocess_run):
    """Verifies '-c <command>' fails correctly with non-zero exit code."""
    def inner():
        test_command = 'a-command-that-will-fail'
        print(f"\n[test_c_argument_failure] --- Running Test ---")
        print(f"[test_c_argument_failure] Test command: {test_command}")

        monkeypatch.setattr(sys, "argv", ["TeraShell.py", "-c", test_command])
        print(f"[test_c_argument_failure] sys.argv set to: {sys.argv}")

        mock_subprocess_run.return_value.returncode = 127

        with pytest.raises(SystemExit) as e:
            main()

        mock_subprocess_run.assert_called_once_with(test_command, shell=True, env=os.environ)
        print(f"[test_c_argument_failure] mock_subprocess_run called with: {mock_subprocess_run.call_args}")

        assert e.value.code == 127
        print(f"[test_c_argument_failure] Exit code: {e.value.code}")
        print(f"[test_c_argument_failure] --- Test Finished ---")

    run_with_timeout(inner, timeout=1)


def test_interactive_shell():
    """Test that TeraShell can be run interactively."""
    if sys.platform == "win32":
        import wexpect as pexpect
    else:
        import pexpect
        
    print(f"\n[test_interactive_shell] --- Running Test ---")

    # Locate the TeraShell.py script
    terashell_path = os.path.abspath("src/TeraShell.py")
    if not os.path.exists(terashell_path):
        terashell_path = os.path.abspath("../src/TeraShell.py")
        if not os.path.exists(terashell_path):
            pytest.fail("Could not find TeraShell.py")
    print(f"[test_interactive_shell] TeraShell script path: {terashell_path}")

    # Spawn the shell using pexpect
    command = f"{sys.executable} {terashell_path}"
    print(f"[test_interactive_shell] Spawning command: {command}")
    child = pexpect.spawn(command, encoding='utf-8')

    try:
        # Wait for the initial prompt
        print(f"[test_interactive_shell] Expecting prompt '└> '")
        child.expect("└> ", timeout=10)
        print(f"[test_interactive_shell] > BEFORE expect: {repr(child.before)}")
        print(f"[test_interactive_shell] > AFTER expect: {repr(child.after)}")

        # Send a command
        send_cmd = 'echo "hello from pexpect"'
        print(f"[test_interactive_shell] Sending command: '{send_cmd}'")
        child.sendline(send_cmd)

        # Expect the output of the command
        print(f"[test_interactive_shell] Expecting output 'hello from pexpect'")
        child.expect("hello from pexpect", timeout=2)
        print(f"[test_interactive_shell] > BEFORE expect: {repr(child.before)}")
        print(f"[test_interactive_shell] > AFTER expect: {repr(child.after)}")

        # Expect the next prompt
        print(f"[test_interactive_shell] Expecting next prompt '└> '")
        child.expect("└> ", timeout=2)
        print(f"[test_interactive_shell] > BEFORE expect: {repr(child.before)}")
        print(f"[test_interactive_shell] > AFTER expect: {repr(child.after)}")

        # Send the exit command
        print(f"[test_interactive_shell] Sending 'exit' command")
        child.sendline("exit")
        
        # Wait for the shell to exit
        print(f"[test_interactive_shell] Expecting EOF")
        child.expect(pexpect.EOF, timeout=2)
        print(f"[test_interactive_shell] Received EOF. child.before: {repr(child.before)}")

    finally:
        # Ensure the child process is terminated
        if child.isalive():
            print(f"[test_interactive_shell] Child process still alive, closing.")
            child.close()
        else:
            print(f"[test_interactive_shell] Child process terminated. Exit: {child.exitstatus}")
            
    print(f"[test_interactive_shell] --- Test Finished ---")

