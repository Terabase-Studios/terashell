import asyncio
import os
import subprocess
import time
from collections import deque
from datetime import datetime
from threading import Thread

import psutil
from prettytable import PrettyTable


class BackgroundTask:
    def __init__(self, task_id, command, process):
        self.id = task_id
        self.command = command
        self.process = process
        self.stdout = deque()
        self.stderr = deque()
        self.output = deque()
        self.running = True
        self.exit_code = None
        self.killed = False
        self.started = datetime.now()
        self._start_reading()

    def _read_stream(self, stream, store, prefix):
        for line in iter(stream.readline, ''):
            store.append(line)
            self.output.append(line)
        stream.close()

    def _start_reading(self):
        Thread(target=self._read_stream, args=(self.process.stdout, self.stdout, "STDOUT"), daemon=True).start()
        Thread(target=self._read_stream, args=(self.process.stderr, self.stderr, "STDERR"), daemon=True).start()

    def status(self):
        if self.running:
            return "RUNNING"
        if self.killed:
            return "KILLED"
        if self.exit_code is None:
            return "UNKNOWN"
        if self.exit_code == 0:
            return "DONE"
        return "FAILED"

    def __repr__(self):
        return f"[{self.id}] {self.status():<7}  {self.command}"


class BackgroundTaskManager:
    def __init__(self):
        self.tasks = {}
        self.next_id = 1
        self._shutdown = False

    async def run_bg(self, cmd):
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "FORCE_COLOR": "1"},
            text=True,
            bufsize=1
        )
        task_id = self.next_id
        self.next_id += 1
        t = BackgroundTask(task_id, cmd, proc)
        self.tasks[task_id] = t
        Thread(target=self._wait_for_exit, args=(t,), daemon=True).start()
        print(f"[Task {task_id} started]")
        return task_id

    def _wait_for_exit(self, task):
        task.process.wait()
        task.running = False
        task.exit_code = task.process.returncode

    def list_jobs(self):
        for t in self.tasks.values():
            print(t)

    def show_output(self, task_id):
        t = self.tasks.get(task_id)
        if not t:
            print("No such task")
            return
        print(f"--- Output of Task {task_id} ---")
        for line in t.output:
            print(line, end="")
        print("\n--- End ---")

    def kill(self, task_id, timeout=3.0):
        t = self.tasks.get(task_id)
        if not t:
            print("No such task")
            return
        if not t.running:
            print("Task is not running.")
            return

        t.killed = True
        try:
            parent = psutil.Process(t.process.pid)
            # Kill all children first
            children = parent.children(recursive=True)
            for child in children:
                child.kill()
            parent.kill()

            # Wait until process actually exits
            start = time.time()
            while t.running and (time.time() - start) < timeout:
                if not parent.is_running():
                    t.running = False
                    t.exit_code = parent.returncode
                    break
                time.sleep(0.05)

            if t.running:
                print(f"[Task {task_id}] failed to terminate within {timeout}s")
            else:
                print(f"[Task {task_id}] terminated successfully")
        except psutil.NoSuchProcess:
            t.running = False
            print(f"[Task {task_id}] already exited")

    def task_table(self):
        """
        Print a table of tasks with ID, PID, status, exit code, CPU %, memory usage, and command.
        """
        table = PrettyTable()
        table.field_names = ["ID", "PID", "Status", "Exit Code", "CPU %", "Memory MB", "Command"]

        for t in self.tasks.values():
            pid = t.process.pid
            cpu = 0.0
            mem = 0.0
            status = t.status()

            try:
                proc = psutil.Process(pid)
                # Non-blocking: returns % since last call (you should have called this at least once before)
                cpu = proc.cpu_percent(interval=None)
                mem = proc.memory_info().rss / (1024 * 1024)
                # Optionally update status from psutil
                status = proc.status()
            except psutil.NoSuchProcess:
                status = "terminated"
            except psutil.AccessDenied:
                status = "access denied"

            table.add_row([
                t.id,
                pid,
                status,
                t.exit_code,
                f"{cpu:.1f}",
                f"{mem:.1f}",
                t.command
            ])

        print(table)

    async def shutdown(self):
        self._shutdown = True
        running = [t for t in self.tasks.values() if t.running]
        for t in running:
            try:
                parent = psutil.Process(t.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except Exception:
                pass
        await asyncio.sleep(0.1)


def create_btm() -> BackgroundTaskManager:
    """
    Create a BackgroundTaskManager with guaranteed cleanup on exit.
    """
    import signal, atexit

    btm = BackgroundTaskManager()

    # Safe shutdown on normal exit
    atexit.register(lambda: asyncio.run(btm.shutdown()))

    # Safe shutdown on signals
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    def handle_signal(signum, frame):
        # print(f"\nReceived signal {signum}, shutting down…")
        # loop.create_task(btm.shutdown())
        # Do not exit immediately, give shutdown a chance
        pass

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    return btm
