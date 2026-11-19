"""Chạy tác vụ nặng (viết content, đọc giọng, tìm ảnh, xuất video) ở nền."""
import threading
import time
import traceback

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def get(pid: str) -> dict:
    with _lock:
        j = _jobs.get(pid)
        return dict(j, log=list(j["log"][-200:])) if j else {"status": "idle", "log": []}


def running(pid: str) -> bool:
    with _lock:
        j = _jobs.get(pid)
        return bool(j and j["status"] == "running")


def start(pid: str, name: str, fn, *args, **kwargs) -> dict:
    with _lock:
        if pid in _jobs and _jobs[pid]["status"] == "running":
            raise RuntimeError("Đang có tác vụ khác chạy, đợi xong đã nhé.")
        job = {"name": name, "status": "running", "progress": 0.0, "log": [], "started": time.time(),
               "error": ""}
        _jobs[pid] = job

    def log(msg: str, progress: float | None = None):
        with _lock:
            job["log"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
            if progress is not None:
                job["progress"] = max(0.0, min(1.0, progress))
        print(f"[{pid}] {msg}", flush=True)

    def run():
        try:
            fn(pid, log, *args, **kwargs)
            with _lock:
                job["status"] = "done"
                job["progress"] = 1.0
            log("Xong ✅")
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            with _lock:
                job["status"] = "error"
                job["error"] = str(e)
            log(f"LỖI: {e}")

    threading.Thread(target=run, daemon=True).start()
    return get(pid)
