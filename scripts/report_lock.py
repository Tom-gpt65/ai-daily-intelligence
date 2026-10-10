"""OS-released lock for local report/index transactions; no stale PID files."""
from contextlib import contextmanager
import os
from pathlib import Path
import threading
import time

_thread_lock = threading.RLock()


@contextmanager
def lock(reports: Path):
    target = reports.parent.parent/".cache"/"reports-write.lock"
    target.parent.mkdir(parents=True, exist_ok=True)
    with _thread_lock, target.open("a+b") as stream:
        if not stream.tell():
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic()+20
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Report publication lock timed out")
                time.sleep(0.05)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
