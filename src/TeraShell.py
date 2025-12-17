import os
import signal
import subprocess
import sys
import time
import traceback

RED_BACKGROUND = "\033[41m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

times_critical = 0
warn = True

def start_shell(shell_script):
    global times_critical
    from config import SHELL_NAME, IS_UNIX
    # Handle instance safely if possible
    try:
        instance = shell_script.handle_instance()
    except Exception as ex:
        instance = None

    # Try to start the shell if we successfully imported it
    try:
        shell = shell_script.TeraShell(instance=instance, shell_file=__file__)
        shell.start()
    except Exception as ex:
        times_critical += 1
        if warn:
            print(f"{RED_BACKGROUND}{SHELL_NAME} unhandled error:{RESET}"
                f"\n{RED}"
            )

            traceback.print_exception(type(ex), ex, ex.__traceback__)
            print(f"\n\nPLEASE REPORT{RESET}")

        # If multiple critical errors, fallback
        if times_critical > 1 and IS_UNIX:
            if warn:
                print(f"{BOLD}Multiple critical errors!{RESET}\n")
            fallback()
            return
        else:
            time.sleep(1)
            print(f"Restarting {SHELL_NAME}...")
            start_shell(shell_script)
            return

def import_shell_script():
    # Try to import the main shell script
    try:
        import shell
        return shell
    except Exception as ex:
        try:
            import config
            shell_name = config.SHELL_NAME
        except:
            shell_name = "TeraShell"
        print(f"{RED_BACKGROUND}{shell_name} unhandled error:{RESET}"
              f"\n{RED}"
              )

        traceback.print_exception(type(ex), ex, ex.__traceback__)
        print(f"\n\nPLEASE REPORT{RESET}")
        return None

def fallback(cmd=None):
    print("Attempting to start; bash, zsh, or sh")
    for cand in ["/bin/bash", "/bin/zsh", "/bin/sh"]:
        if os.path.exists(cand):
            print(f"{cand} found, starting...\n")
            subprocess.run([cand])
            return
        else:
            print(f"{cand} not found")

    try:
        emergency_shell()
    except Exception as e:
        print("\nEmergency shell failed:", e)
        print("Try and boot with a live os to make repairs")
    sys.exit(1)

def emergency_shell():
    print("System shell could not be started.")
    print("Entering emergency shell. Extremely limited environment.\n")

    # Ignore Ctrl-C for the emergency shell itself
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    working_dir = os.getcwd()

    while True:
        try:
            try:
                cmd = input(f"emergency@{working_dir}> ").strip()
            except (KeyboardInterrupt, EOFError):
                cmd = ""
                continue

            if not cmd:
                continue

            if cmd == "exit":
                return

            if cmd.startswith("cd "):
                prev = working_dir
                path = cmd.removeprefix("cd ").strip()
                try:
                    new_dir = os.path.expanduser("~") if not path else os.path.join(working_dir, path)
                    if os.path.isdir(new_dir):
                        working_dir = os.path.abspath(new_dir)
                        os.chdir(working_dir)
                    else:
                        print(f"cd: no such directory: {path}")
                except Exception as e:
                    working_dir = prev
                    print(e)
                continue

            # Run external commands with their own Ctrl-C behavior
            try:
                subprocess.run(
                    cmd.split(),
                    preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL)
                )
            except Exception as e:
                print(f"Cannot execute: {e}")

        except Exception as loop_err:
            print(f"Unexpected emergency loop error: {loop_err}")


if __name__ == "__main__":
    # Non-interactive mode for scripts and tools like Cockpit/SSH
    # Executed via: terashell-shell -c "command"
    if len(sys.argv) > 2 and sys.argv[1] == '-c':
        command_to_run = sys.argv[2]
        # We run the command and let its stdout/stderr flow to the parent.
        # This makes it behave like a standard non-interactive shell.
        result = subprocess.run(command_to_run, shell=True, env=os.environ)
        sys.exit(result.returncode)

    # Interactive mode (default)
    shell_script = import_shell_script()
    if shell_script:
        start_shell(shell_script)
    else:
        is_unix = sys.platform.startswith("linux") or sys.platform.startswith("darwin")

        if is_unix:
            if warn:
                print(f"{BOLD}Failed to start shell!{RESET}\n")
            fallback()
            sys.exit(1)
        else:
            sys.exit(1)
