'''

JSON RESULT WRITER I DIDNT WRITE IT MYSELF CUZ YOU KNOW JSON OUTPUT 
BUT CMON I THINK THIS MUCH IS FINE 
ITS JUST WRITING THE JSON OUTPUT 
ITS FINE 
RIGHT 
:D

'''


import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from auspex.config import Cfg

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "results"

# NASA-HTTP timestamps are US Eastern Daylight Time (the "-0400" in the raw log).
LOG_TZ = timezone(timedelta(hours=-4))


def git_sha() -> str:
    """The commit the run was produced from (Appendix B: reproducibility)."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()


def file_sha256(path: Path) -> str:
    """Fingerprint of the trace file, so a regenerated trace is detectable."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(epoch_s: int) -> str:
    """Epoch seconds -> ISO string in the log's own timezone."""
    return datetime.fromtimestamp(int(epoch_s), LOG_TZ).isoformat()


def write_result(
    policy: str,
    capacity: int,
    protocol: str,
    trace_path: Path,
    cfg: Cfg,
    hits: int,
    misses: int,
    counted_requests: int,
    wall_clock_s: float,
    counted_window: tuple[int, int] | None = None,
    policy_stats: dict | None = None,
) -> Path:
    """Write one run's Appendix B JSON and return the path it was written to.

    counted_window is (first_counted_ts, last_counted_ts) in epoch seconds;
    it is stored as ISO strings because a bare epoch is unreadable in a report.
    """
    total = hits + misses
    if total != counted_requests:
        raise ValueError(
            f"hits + misses ({total}) != counted_requests ({counted_requests})"
        )

    run_id = f"{datetime.now(UTC):%Y-%m-%dT%H}_{policy}_{capacity}_{protocol}"

    payload = {
        "run_id": run_id,
        "git_sha": git_sha(),
        "generated_at": datetime.now(UTC).isoformat(),
        "trace": str(trace_path.relative_to(REPO_ROOT)),
        "trace_sha256": file_sha256(trace_path),
        "protocol": protocol,
        "counted_window": [iso(counted_window[0]), iso(counted_window[1])]
        if counted_window
        else None,
        "policy": policy,
        "capacity": capacity,
        "cfg": asdict(cfg),
        "counted_requests": counted_requests,
        "hits": hits,
        "misses": misses,
        "hit_rate": round(hits / counted_requests, 6) if counted_requests else None,
        "policy_stats": policy_stats or {},
        "wall_clock_s": round(wall_clock_s, 3),
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{run_id}.json"
    out.write_text(json.dumps(payload, indent=2))
    return out


def print_table(rows: list[dict]) -> None:
    """Print the per-size summary table the CLI shows after a sweep."""
    print(f"{'policy':<10}{'capacity':>10}{'hit_rate':>12}{'hits':>12}"
          f"{'misses':>12}{'seconds':>10}")
    for r in rows:
        print(f"{r['policy']:<10}{r['capacity']:>10}{r['hit_rate']:>12.4f}"
              f"{r['hits']:>12}{r['misses']:>12}{r['wall_clock_s']:>10.1f}")
