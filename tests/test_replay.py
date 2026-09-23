"""Appendix C tests 1-5 — LRU and the replay harness (PLAN §4.4).

    1. cyclic pathology: ABCD x 1000, cap 3 -> hit rate exactly 0.
    2. capacity invariant: never exceeded.
    3. hand-trace: 10 requests, cap 2, exact hit/miss sequence.
    4. warmup gating: counts differ, cache end-state identical.
    5. determinism: two runs, identical result payload (modulo run_id,
       wall_clock_s and timestamps).

Written from the PLAN's stated requirements, not from reading the
implementation (hard rule 8). Every expected number below is derived by hand
in the comment beside it.

§4.3, restated as the contract under test:
  - on_tick(ts) before get(key);
  - a demand miss always calls put(key) -- no admission policy;
  - observe() after serve, for every request, counted or not;
  - the counted mask gates *counting only*, never the cache mutation.
"""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from auspex.config import Cfg
from auspex.harness.protocols import counted_mask
from auspex.harness.replay import policy_loop
from auspex.policies.lru import LRU


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def make_trace(keys: list[int], sids: list[int] | None = None):
    """Turn a list of keys into the arrays the loop wants.

    Timestamps are one second apart so (ts, seq) order is trivially valid;
    sessions default to one session, since no Stage-1 policy reads them.
    """
    n = len(keys)
    ts = np.arange(n, dtype=np.int64)
    ids = np.asarray(keys, dtype=np.int64)
    sid = np.asarray(sids if sids is not None else [0] * n, dtype=np.int64)
    return ts, ids, sid


def all_counted(n: int) -> np.ndarray:
    """No warmup: every request is graded."""
    return np.ones(n, dtype=bool)


def cache_size(policy) -> int:
    """Number of keys resident, without assuming the attribute's name.

    §4.2 pins the structure (an OrderedDict); what it is *called* is the
    implementer's choice, so this test does not depend on it.
    """
    for value in vars(policy).values():
        if hasattr(value, "keys"):
            return len(value)
    raise AssertionError("policy exposes no mapping to measure")


def cache_keys(policy) -> list:
    for value in vars(policy).values():
        if hasattr(value, "keys"):
            return list(value.keys())
    raise AssertionError("policy exposes no mapping to measure")


# --------------------------------------------------------------------------
# Appendix C test 1 — the cyclic pathology (spec §1.4)
# --------------------------------------------------------------------------

def test_cyclic_pathology_is_exactly_zero():
    """ABCD repeated 1000x through a 3-slot LRU: every request misses.

    Hand derivation: with capacity 3 and a cycle of length 4, the key you
    are about to need is always the one just evicted -- A is evicted to make
    room for D, then requested immediately. 4000 requests, 0 hits.

    This is the test that fails if get() forgets to update recency, so the
    exact 0.0 matters: a FIFO-by-accident cache scores 0 here too, but a
    cache whose get() is a no-op peek would score differently.
    """
    keys = [1, 2, 3, 4] * 1000
    ts, ids, sid = make_trace(keys)
    counted = all_counted(len(keys))

    out = policy_loop(LRU(3), len(keys), ts, ids, sid, counted)

    assert out["hits"] == 0
    assert out["misses"] == 4000
    assert out["hits"] / (out["hits"] + out["misses"]) == 0.0


def test_cyclic_pathology_one_slot_larger_is_all_hits_after_warmup():
    """Capacity 4 holds the whole cycle: 4 compulsory misses, 3996 hits.

    The companion to the test above -- it shows the 0.0 came from the
    capacity/cycle relationship, not from a cache that never stores anything.
    """
    keys = [1, 2, 3, 4] * 1000
    ts, ids, sid = make_trace(keys)
    counted = all_counted(len(keys))

    out = policy_loop(LRU(4), len(keys), ts, ids, sid, counted)

    assert out["misses"] == 4          # first sight of each of the 4 keys
    assert out["hits"] == 3996         # 4000 - 4


# --------------------------------------------------------------------------
# Appendix C test 3 — hand-computed trace
# --------------------------------------------------------------------------

# Worked by hand, capacity 2, no warmup. Cache shown front (LRU) -> back (MRU).
#
#   i  key  outcome  action                      cache after
#   0   1   MISS     put 1                       [1]
#   1   2   MISS     put 2                       [1, 2]
#   2   1   HIT      move 1 to back              [2, 1]
#   3   3   MISS     evict 2 (front), put 3      [1, 3]
#   4   2   MISS     evict 1 (front), put 2      [3, 2]
#   5   3   HIT      move 3 to back              [2, 3]
#   6   3   HIT      already at back             [2, 3]
#   7   1   MISS     evict 2 (front), put 1      [3, 1]
#   8   4   MISS     evict 3 (front), put 4      [1, 4]
#   9   1   HIT      move 1 to back              [4, 1]
#
# sequence: M M H M M H H M M H  ->  4 hits, 6 misses, end state [4, 1]
HAND_KEYS = [1, 2, 1, 3, 2, 3, 3, 1, 4, 1]
HAND_HITS = 4
HAND_MISSES = 6
HAND_END_STATE = [4, 1]


def test_hand_trace_counts():
    ts, ids, sid = make_trace(HAND_KEYS)
    out = policy_loop(LRU(2), len(HAND_KEYS), ts, ids, sid,
                      all_counted(len(HAND_KEYS)))

    assert out["hits"] == HAND_HITS
    assert out["misses"] == HAND_MISSES


def test_hand_trace_exact_hit_miss_sequence():
    """Not just the totals -- the outcome of every individual request.

    Totals can match by coincidence (a cache off by one eviction often lands
    on the same hit count); the sequence cannot.
    """
    expected = ["M", "M", "H", "M", "M", "H", "H", "M", "M", "H"]

    lru = LRU(2)
    observed = []
    for key in HAND_KEYS:
        if lru.get(key):
            observed.append("H")
        else:
            observed.append("M")
            lru.put(key)

    assert observed == expected
    assert cache_keys(lru) == HAND_END_STATE


# --------------------------------------------------------------------------
# Appendix C test 2 — capacity invariant
# --------------------------------------------------------------------------

@pytest.mark.parametrize("capacity", [1, 2, 3, 7, 50])
def test_capacity_never_exceeded(capacity):
    """After every single operation, residency <= capacity.

    Checked per request rather than at the end, because an implementation
    that inserts before evicting is momentarily over capacity and would pass
    an end-of-run check.
    """
    rng = np.random.default_rng(0)
    keys = rng.integers(0, 20, size=500)

    lru = LRU(capacity)
    for key in keys:
        if not lru.get(int(key)):
            lru.put(int(key))
        assert cache_size(lru) <= capacity


def test_capacity_one_holds_only_the_last_key():
    """Degenerate capacity: a 1-slot cache always holds the most recent key."""
    lru = LRU(1)
    for key in [5, 6, 7]:
        if not lru.get(key):
            lru.put(key)
    assert cache_keys(lru) == [7]


# --------------------------------------------------------------------------
# Appendix C test 4 — warmup gating
# --------------------------------------------------------------------------

def test_warmup_changes_counts_but_not_cache_end_state():
    """warmup_frac 0.0 vs 0.2 on the same trace.

    The mask gates *counting*, never the cache: every request is served and
    every miss still inserts. So the two runs must end with byte-identical
    cache contents and differ only in the scoreboard.

    Hand derivation on HAND_KEYS (capacity 2), warmup = int(10 * 0.2) = 2:
    requests 0 and 1 are both MISSES and both uncounted, so
        hits    4 -> 4   (no hit falls inside the warmup)
        misses  6 -> 4
    """
    ts, ids, sid = make_trace(HAND_KEYS)
    frame = pd.DataFrame({"ts": ts})

    cfg_none = replace(Cfg(), warmup_frac=0.0)
    cfg_20 = replace(Cfg(), warmup_frac=0.2)

    lru_none = LRU(2)
    out_none = policy_loop(lru_none, len(HAND_KEYS), ts, ids, sid,
                           counted_mask(frame, "P1", cfg_none))

    lru_20 = LRU(2)
    out_20 = policy_loop(lru_20, len(HAND_KEYS), ts, ids, sid,
                         counted_mask(frame, "P1", cfg_20))

    # counts differ
    assert (out_none["hits"], out_none["misses"]) == (4, 6)
    assert (out_20["hits"], out_20["misses"]) == (4, 4)

    # end-state identical
    assert cache_keys(lru_none) == cache_keys(lru_20) == HAND_END_STATE


def test_counted_total_equals_mask_sum():
    """hits + misses must equal the number of counted requests, exactly.

    If this fails, the mask and the loop disagree about which requests are
    graded -- the failure mode that makes two policies incomparable.
    """
    ts, ids, sid = make_trace(HAND_KEYS)
    frame = pd.DataFrame({"ts": ts})
    mask = counted_mask(frame, "P1", Cfg())

    out = policy_loop(LRU(2), len(HAND_KEYS), ts, ids, sid, mask)

    assert out["hits"] + out["misses"] == int(mask.sum())


# --------------------------------------------------------------------------
# Appendix C test 5 — determinism
# --------------------------------------------------------------------------

VOLATILE = {"run_id", "generated_at", "wall_clock_s"}


def test_two_identical_runs_produce_identical_payloads(tmp_path, monkeypatch):
    """Same trace, same policy, same capacity -> same JSON.

    Everything except run_id, generated_at and wall_clock_s must match; those
    three are metadata about *when* the run happened, and a byte-identity
    test on them would fail for reasons that say nothing about correctness
    (Appendix C test 5 says so explicitly).
    """
    import json

    from auspex.harness import results as results_mod

    monkeypatch.setattr(results_mod, "RESULTS_DIR", tmp_path)

    ts, ids, sid = make_trace(HAND_KEYS)
    frame = pd.DataFrame({"ts": ts})
    mask = counted_mask(frame, "P1", Cfg())
    trace_path = results_mod.REPO_ROOT / "data/processed/vocab.parquet"

    payloads = []
    for _ in range(2):
        lru = LRU(2)
        out = policy_loop(lru, len(HAND_KEYS), ts, ids, sid, mask)
        written = results_mod.write_result(
            policy=lru.name,
            capacity=2,
            protocol="P1",
            trace_path=trace_path,
            cfg=Cfg(),
            hits=out["hits"],
            misses=out["misses"],
            counted_requests=int(mask.sum()),
            wall_clock_s=out["time_taken"],
            counted_window=(int(ts[mask][0]), int(ts[mask][-1])),
            policy_stats=lru.stats(),
        )
        payloads.append(json.loads(written.read_text()))

    first, second = payloads
    assert first.keys() == second.keys()
    for field in first:
        if field not in VOLATILE:
            assert first[field] == second[field], f"{field} differs between runs"


def test_writer_rejects_inconsistent_counts(tmp_path, monkeypatch):
    """hits + misses != counted_requests must not be writable.

    A result file that fails its own arithmetic is worse than no file: it
    looks authoritative and is wrong.
    """
    from auspex.harness import results as results_mod

    monkeypatch.setattr(results_mod, "RESULTS_DIR", tmp_path)

    with pytest.raises(ValueError):
        results_mod.write_result(
            policy="lru", capacity=2, protocol="P1",
            trace_path=results_mod.REPO_ROOT / "data/processed/vocab.parquet",
            cfg=Cfg(), hits=3, misses=3, counted_requests=99,
            wall_clock_s=0.1,
        )
