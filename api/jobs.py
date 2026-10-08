import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class Job:
    id: str
    status: str
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class JobStore:
    """进程内异步任务表：一个后台线程跑一个任务，结果留在内存供轮询。

    小内存机器（1 vCPU / 1 GB）下只保留有界数量的在册任务，结束的任务按 TTL 清理。
    """

    def __init__(self, ttl: float = 3600.0, max_jobs: int = 20):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._ttl = ttl
        self._max_jobs = max(1, max_jobs)

    def _purge_locked(self) -> None:
        now = time.time()
        expired = [
            jid
            for jid, job in self._jobs.items()
            if job.finished_at is not None and now - job.finished_at > self._ttl
        ]
        for jid in expired:
            self._jobs.pop(jid, None)

    def active_count(self) -> int:
        with self._lock:
            return sum(
                1
                for job in self._jobs.values()
                if job.status in ("pending", "running")
            )

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            self._purge_locked()
            return self._jobs.get(job_id)

    def submit(
        self,
        target: Callable[[], Any],
        meta: Optional[Dict[str, Any]] = None,
    ) -> Job:
        with self._lock:
            self._purge_locked()
            active = sum(
                1
                for job in self._jobs.values()
                if job.status in ("pending", "running")
            )
            if active >= self._max_jobs:
                raise RuntimeError(
                    f"异步上传任务过多（上限 {self._max_jobs}），请稍后重试"
                )
            job = Job(
                id=uuid.uuid4().hex,
                status="pending",
                created_at=time.time(),
                meta=dict(meta or {}),
            )
            self._jobs[job.id] = job

        thread = threading.Thread(
            target=self._run,
            args=(job, target),
            name=f"upload-{job.id[:8]}",
            daemon=True,
        )
        thread.start()
        return job

    def _run(self, job: Job, target: Callable[[], Any]) -> None:
        with self._lock:
            job.status = "running"
            job.started_at = time.time()
        try:
            result = target()
        except Exception as exc:  # noqa: BLE001 - 结果原样回传给轮询方
            with self._lock:
                job.status = "failed"
                job.error = str(exc)
                job.error_type = type(exc).__name__
        else:
            with self._lock:
                job.status = "succeeded"
                job.result = result
        finally:
            with self._lock:
                job.finished_at = time.time()

    def snapshot(self, job: Job) -> Dict[str, Any]:
        return {
            "job_id": job.id,
            "status": job.status,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "elapsed": (
                (job.finished_at or time.time()) - job.started_at
                if job.started_at
                else None
            ),
            "result": job.result,
            "error": job.error,
            "error_type": job.error_type,
            "meta": job.meta,
        }
