"""Shared mutable state for background jobs and visit tracking."""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class VisitorStats:
    def __init__(self):
        self.total_visits = 0
        self.unique_ips = set()
        self.online_users: Dict[str, float] = {}

    def track(self, ip: str):
        self.total_visits += 1
        self.unique_ips.add(ip)
        self.online_users[ip] = time.time()

    def get_online_count(self):
        threshold = time.time() - 300
        self.online_users = {ip: t for ip, t in self.online_users.items() if t > threshold}
        return len(self.online_users)


stats_tracker = VisitorStats()

benchmark_job_lock = threading.Lock()
benchmark_job_state: Dict[str, Any] = {
    "jobId": None,
    "status": "idle",
    "startedAt": None,
    "finishedAt": None,
    "configPath": None,
    "skipLLM": False,
    "exitCode": None,
    "error": None,
    "outputTail": None,
}

osm_job_lock = threading.Lock()
osm_job_state: Dict[str, Any] = {
    "jobId": None,
    "status": "idle",
    "startedAt": None,
    "finishedAt": None,
    "limitProvinces": 63,
    "targetTotal": 5000000,
    "normalizedTargetTotal": 5000000,
    "exitCode": None,
    "error": None,
    "outputTail": None,
}

batch_job_lock = threading.Lock()
batch_job_state: Dict[str, Any] = {
    "jobId": None,
    "status": "idle",
    "startedAt": None,
    "finishedAt": None,
    "processedCount": 0,
    "totalCount": 0,
    "throughput": 0,
    "exitCode": None,
    "error": None,
    "outputTail": None,
}


def update_benchmark_job_state(**kwargs: Any) -> None:
    with benchmark_job_lock:
        benchmark_job_state.update(kwargs)


def update_osm_job_state(**kwargs: Any) -> None:
    with osm_job_lock:
        osm_job_state.update(kwargs)


def update_batch_job_state(**kwargs: Any) -> None:
    with batch_job_lock:
        batch_job_state.update(kwargs)
