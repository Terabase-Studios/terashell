import sys
import os
import pytest
from unittest import mock
import threading
import time # Added for sleep in debug

# We need to import the main function from TeraShell to test it.
# This relies on the pytest.ini configuration `pythonpath = src`.
from TeraShell import main
import config

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
def test_c_argument_success(monkeypatch):
    """Verifies '-c <command>' runs successfully and prints output."""
    def inner():
        test_command = 'echo "Terashell -c test successful"'
        monkeypatch.setattr(sys, "argv", ["TeraShell.py", "-c", test_command])

        # Pipe to capture stdout
        r, w = os.pipe()
        original_stdout_fd = os.dup(1)
        os.dup2(w, 1)

        try:
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 0

            # Close write end of pipe
            os.close(w)
            output = os.read(r, 1000).decode('utf-8')
            assert "Terashell -c test successful" in output
        finally:
            # Restore stdout
            os.dup2(original_stdout_fd, 1)
            os.close(original_stdout_fd)
            os.close(r)

    run_with_timeout(inner, timeout=2)


def test_c_argument_failure(monkeypatch):
    """Verifies '-c <command>' fails correctly with non-zero exit code and prints to stderr."""
    def inner():
        test_command = 'a-command-that-will-fail'
        monkeypatch.setattr(sys, "argv", ["TeraShell.py", "-c", test_command])

        # Pipe to capture stderr
        r, w = os.pipe()
        original_stderr_fd = os.dup(2)
        os.dup2(w, 2)

        try:
            with pytest.raises(SystemExit) as e:
                main()

            assert e.value.code != 0

            # Close write end of pipe
            os.close(w)
            error_output = os.read(r, 1000).decode('utf-8')
            assert len(error_output) > 0
        finally:
            # Restore stderr
            os.dup2(original_stderr_fd, 2)
            os.close(original_stderr_fd)
            os.close(r)

    run_with_timeout(inner, timeout=2)


def test_interactive_shell():
    """Test that TeraShell can be run interactively."""
    if sys.platform == "win32":
        import wexpect as pexpect
    else:
        import pexpect

    config.PATH_INDEXING = False
        
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

