"""Appendix C test 9 — the infinite demand-loaded cache (PLAN §5.2).

    9. Property: infinite demand-loaded >= every demand-fetch policy.

The definition under test (§5.2), restated: a set; a request is a hit iff the
same key was demanded earlier in the replayed range. So on any trace,
misses = number of distinct keys, and capacity plays no part.

Written from that definition, not from reading the implementation (hard
rule 8). Counting is full-sequence (no warmup) throughout: that is where the
inequality is a theorem. Every demand-fetch cache must miss on a key's first
request, and infinite misses on nothing else.

Belady joins the property test once it exists (Stage 2, §5.3).
"""

import random

from auspex.policies.infinite import Infinite
from auspex.policies.lfu import LFU
from auspex.policies.lru import LRU


DEMAND_FETCH = [LRU, LFU]
SIZES = (1, 2, 3, 5, 10, 25)


def hits(policy, keys: list[int]) -> int:
    """Drive the policy per the §4.3 contract (get; on a miss, put)."""
    n = 0
    for key in keys:
        if policy.get(key):
            n += 1
        else:
            policy.put(key)
    return n


def random_traces() -> list[list[int]]:
    """A few shapes: uniform, skewed (a hot set), and a scan-heavy cycle."""
    rng = random.Random(9)
    uniform = [rng.randint(0, 40) for _ in range(5000)]
    skewed = [
        rng.randint(0, 4) if rng.random() < 0.7 else rng.randint(5, 200)
        for _ in range(5000)
    ]
    cyclic = list(range(30)) * 100
    return [uniform, skewed, cyclic]


# --------------------------------------------------------------------------
# the definition
# --------------------------------------------------------------------------

def test_hand_trace_misses_equal_distinct_keys():
    """Ten requests over four keys: exactly four misses, one per first sight.

      keys     1 2 1 3 2 3 3 1 4 1
      outcome  M M H M H H H H M H     -> 6 hits, 4 misses
    """
    keys = [1, 2, 1, 3, 2, 3, 3, 1, 4, 1]
    assert hits(Infinite(2), keys) == 6


def test_capacity_is_ignored():
    """Same trace, any capacity -- including 1 -- gives the same answer."""
    keys = random_traces()[0]
    expected = len(keys) - len(set(keys))
    for size in (1, 10, 10_000):
        assert hits(Infinite(size), keys) == expected


def test_nothing_is_ever_forgotten():
    """A key seen once is a hit on every later request, however many
    other keys arrive in between."""
    policy = Infinite(1)
    policy.put(7)
    for key in range(1000):
        if not policy.get(key):
            policy.put(key)
    assert policy.get(7)


# --------------------------------------------------------------------------
# Appendix C test 9 — the property
# --------------------------------------------------------------------------

def test_infinite_beats_or_ties_every_demand_fetch_policy():
    """For every (trace, size, policy): hits(infinite) >= hits(policy)."""
    for keys in random_traces():
        ceiling = hits(Infinite(1), keys)
        for policy_class in DEMAND_FETCH:
            for size in SIZES:
                assert ceiling >= hits(policy_class(size), keys), (
                    f"{policy_class.name} at {size} beat infinite"
                )


def test_demand_fetch_equals_infinite_when_everything_fits():
    """Capacity >= distinct keys means no eviction ever happens, so every
    demand-fetch policy *is* the infinite cache on that trace.

    (This is the July result in miniature: 9,348 URLs < 10,000 slots.)
    """
    for keys in random_traces():
        distinct = len(set(keys))
        expected = hits(Infinite(1), keys)
        for policy_class in DEMAND_FETCH:
            assert hits(policy_class(distinct), keys) == expected
