"""Subprocess workers for benchmark / batch / OSM background jobs."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import traceback
from datetime import datetime

from app.api import state
from app.paths import repo_root


def run_benchmark_job(job_id: str, config_path: str, skip_llm: bool) -> None:
    _proj = repo_root()
    cmd = [
        sys.executable,
        "-m",
        "app.ai.experiment_runner",
        "--config",
        config_path,
    ]
    if skip_llm:
        cmd.append("--no-llm")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(_proj),
            capture_output=True,
            text=True,
            check=False,
        )
        output_tail = (proc.stdout or "")
        if proc.stderr:
            output_tail += "\n" + proc.stderr
        output_tail = output_tail[-6000:] if output_tail else ""

        if proc.returncode == 0:
            state.update_benchmark_job_state(
                status="success",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=proc.returncode,
                error=None,
                outputTail=output_tail,
            )
        else:
            state.update_benchmark_job_state(
                status="failed",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=proc.returncode,
                error=f"Benchmark process exited with code {proc.returncode}",
                outputTail=output_tail,
            )
    except Exception as exc:
        state.update_benchmark_job_state(
            status="failed",
            finishedAt=datetime.utcnow().isoformat() + "Z",
            exitCode=-1,
            error=f"{exc}\n{traceback.format_exc()}",
            outputTail=None,
        )


def run_batch_job(job_id: str, limit: int, method: str) -> None:
    _proj = repo_root()
    cmd = [
        sys.executable,
        "-m",
        "app.ai.production_pipeline",
        "--limit",
        str(limit),
    ]

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        proc = subprocess.Popen(
            cmd,
            cwd=str(_proj),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        output_tail = ""
        if proc.stdout is not None:
            for raw_line in proc.stdout:
                line = raw_line.rstrip("\n")
                if not line:
                    continue

                output_tail = (output_tail + "\n" + line).strip()[-6000:]

                progress_match = re.search(r"Progress:\s*(\d+)/(\d+)", line)
                if progress_match:
                    processed = int(progress_match.group(1))
                    total = int(progress_match.group(2))
                    start_time = datetime.fromisoformat(state.batch_job_state["startedAt"].replace("Z", ""))
                    elapsed = max(1, (datetime.utcnow() - start_time).total_seconds())
                    throughput = processed / elapsed
                    state.update_batch_job_state(
                        processedCount=processed,
                        totalCount=total,
                        throughput=throughput,
                        outputTail=output_tail,
                    )
                else:
                    state.update_batch_job_state(outputTail=output_tail)

        return_code = proc.wait()

        if return_code == 0:
            state.update_batch_job_state(
                status="success",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=return_code,
                processedCount=state.batch_job_state.get("totalCount", 0),
                error=None,
                outputTail=output_tail,
            )
        else:
            state.update_batch_job_state(
                status="failed",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=return_code,
                error=f"Batch process exited with code {return_code}",
                outputTail=output_tail,
            )
    except Exception as exc:
        state.update_batch_job_state(
            status="failed",
            finishedAt=datetime.utcnow().isoformat() + "Z",
            exitCode=-1,
            error=f"{exc}\n{traceback.format_exc()}",
            outputTail=None,
        )


def run_osm_job(job_id: str, limit_provinces: int, target_total: int) -> None:
    _proj = repo_root()
    cmd = [
        sys.executable,
        "-m",
        "app.main",
        "osm:fetch",
        "--limit",
        str(limit_provinces),
        "--target",
        str(target_total),
    ]

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        proc = subprocess.Popen(
            cmd,
            cwd=str(_proj),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        output_tail = ""
        if proc.stdout is not None:
            for raw_line in proc.stdout:
                line = raw_line.rstrip("\n")
                if not line:
                    continue

                output_tail = (output_tail + "\n" + line).strip()[-6000:]
                state.update_osm_job_state(outputTail=output_tail)

        return_code = proc.wait()

        if return_code == 0:
            state.update_osm_job_state(
                status="success",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=return_code,
                error=None,
                outputTail=output_tail,
            )
        else:
            state.update_osm_job_state(
                status="failed",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                exitCode=return_code,
                error=f"OSM process exited with code {return_code}",
                outputTail=output_tail,
            )
    except Exception as exc:
        state.update_osm_job_state(
            status="failed",
            finishedAt=datetime.utcnow().isoformat() + "Z",
            exitCode=-1,
            error=f"{exc}\n{traceback.format_exc()}",
            outputTail=None,
        )
