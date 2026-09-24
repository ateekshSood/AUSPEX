"""Appendix C tests for LFU (PLAN §5.1, pinned in decisions.md D056).

    6. tie-break determinism on crafted tie traces.
    3. capacity invariant, LFU edition.
    plus a hand-traced sequence (the LFU counterpart of the LRU hand-trace).

The definition under test (D056 / PLAN §5.1), restated:
  - in-cache LFU: a key's count is 1 when it is inserted, +1 on every hit;
  - the count is destroyed on eviction -- a returning key starts again at 1;
  - evict the minimum-count key; among equal counts, the least recently
    *used* one (last access, not first insertion).

Written from that definition, not from reading the implementation (hard
rule 8). Every expected sequence is derived by hand in the comment beside it.
All tests are black-box: they only call get/put and look at hit/miss
outcomes, so they do not depend on how the structure is named or built.
"""

import random

from auspex.policies.lfu import LFU


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def outcomes(capacity: int, keys: list[int]) -> str:
    """Drive the policy per the §4.3 contract (get; on a miss, put).

    Returns one letter per request: 'H' hit, 'M' miss.
    """
    policy = LFU(capacity)
    out = []
    for key in keys:
        if policy.get(key):
            out.append("H")
        else:
            out.append("M")
            policy.put(key)
    return "".join(out)


def resident_count(policy) -> int:
    """Number of keys resident, without assuming the attribute's name.

    Same convention as test_replay.cache_size: the first mapping attribute
    set in __init__ is the key -> state map, whose length is the occupancy.
    """
    for value in vars(policy).values():
        if hasattr(value, "keys"):
            return len(value)
    raise AssertionError("policy exposes no mapping to measure")


# --------------------------------------------------------------------------
# Appendix C test 6 — tie-break determinism
# --------------------------------------------------------------------------

def test_tie_among_count_one_evicts_least_recently_used():
    """Three keys at count 1; the oldest of them goes first.

    Capacity 3. Buckets shown as count: [least recent ... most recent].

      i  key  outcome  action                         state after
      0   1   M        insert                         1:[1]
      1   2   M        insert                         1:[1,2]
      2   3   M        insert                         1:[1,2,3]
      3   4   M        evict 1 (front of min=1)       1:[2,3,4]
      4   1   M        evict 2                        1:[3,4,1]
      5   3   H        3 -> count 2                   1:[4,1]  2:[3]
      6   2   M        evict 4 (front of min=1)       1:[1,2]  2:[3]
      7   4   M        evict 1                        1:[2,4]  2:[3]
      8   3   H        3 -> count 3                   1:[2,4]  3:[3]
    """
    assert outcomes(3, [1, 2, 3, 4, 1, 3, 2, 4, 3]) == "MMMMMHMMH"


def test_tie_break_uses_last_use_not_first_insertion():
    """All three keys at count 2; the one *used* longest ago is evicted.

    Key 1 was inserted first, but key 2 was last used earliest -- so a
    tie-break on insertion order evicts 1, and the pinned rule evicts 2.

    Capacity 3.

      i  key  outcome  action                         state after
      0   1   M        insert                         1:[1]
      1   2   M        insert                         1:[1,2]
      2   2   H        2 -> count 2                   1:[1]    2:[2]
      3   1   H        1 -> count 2                   2:[2,1]
      4   3   M        insert                         1:[3]    2:[2,1]
      5   3   H        3 -> count 2                   2:[2,1,3]  (min 2)
      6   4   M        evict 2 (front of min=2)       1:[4]    2:[1,3]
      7   2   M        2 was evicted; evict 4         1:[2]    2:[1,3]
      8   1   H        1 still resident               ...
      9   3   H        3 still resident               ...

    Under insertion-order tie-break, i6 evicts 1 and i7/i8 come out H/M.
    """
    assert outcomes(3, [1, 2, 2, 1, 3, 3, 4, 2, 1, 3]) == "MMHHMHMMHH"


def test_tie_break_is_deterministic_across_runs():
    """Same tie-heavy trace, two fresh policies, identical outcome string.

    A small key universe and small capacity make ties the common case, so a
    tie-break that depended on anything but the request history (hash order,
    set iteration) would show up here.
    """
    rng = random.Random(6)
    keys = [rng.randint(0, 12) for _ in range(5000)]
    for capacity in (1, 2, 3, 5, 8):
        assert outcomes(capacity, keys) == outcomes(capacity, keys)


# --------------------------------------------------------------------------
# the definition's other two clauses
# --------------------------------------------------------------------------

def test_min_count_beats_recency():
    """A frequent key survives even when it is the least recently used.

    Capacity 2.

      i  key  outcome  action                         state after
      0   1   M        insert                         1:[1]
      1   1   H        count 2                        2:[1]
      2   1   H        count 3                        3:[1]
      3   2   M        insert                         1:[2]    3:[1]
      4   3   M        evict 2 (count 1), NOT 1       1:[3]    3:[1]
      5   1   H        1 survived                     1:[3]    4:[1]
      6   2   M        2 was evicted; evict 3         1:[2]    4:[1]

    LRU would evict 1 at i4 (it is least recent) and miss at i5.
    """
    assert outcomes(2, [1, 1, 1, 2, 3, 1, 2]) == "MHHMMHM"


def test_count_is_destroyed_on_eviction():
    """No ghost history: an evicted key comes back at count 1.

    Capacity 2.

      i   key  outcome  action                        counts after
      0    1   M        insert                        1:1
      1-3  1   H H H    -> count 4                    1:4
      4    2   M        insert                        1:4 2:1
      5-8  2   H H H H  -> count 5                    1:4 2:5
      9    3   M        evict 1 (count 4 < 5)         2:5 3:1
      10   1   M        evict 3; 1 re-enters at 1     2:5 1:1
      11   4   M        evict 1 (count 1 < 5)         2:5 4:1
      12   1   M        1 was evicted                 ...

    With ghost history 1 would re-enter at i10 with count 5, tie with 2,
    and i11 would evict 2 (least recent) instead -- making i12 a hit.
    """
    keys = [1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 1, 4, 1]
    assert outcomes(2, keys) == "MHHHMHHHHMMMM"


# --------------------------------------------------------------------------
# Hand-traced sequence (the LFU counterpart of the LRU hand-trace)
# --------------------------------------------------------------------------

def test_hand_trace_and_divergence_from_lru():
    """Ten requests, capacity 2, exact hit/miss sequence.

    Same keys as the LRU hand-trace in test_replay.py, which gives
    M M H M M H H M M H there.

      i  key  outcome  action                         state after
      0   1   M        insert                         1:[1]
      1   2   M        insert                         1:[1,2]
      2   1   H        1 -> count 2                   1:[2]    2:[1]
      3   3   M        evict 2 (min=1)                1:[3]    2:[1]
      4   2   M        evict 3                        1:[2]    2:[1]
      5   3   M        evict 2                        1:[3]    2:[1]
      6   3   H        3 -> count 2                   2:[1,3]  (min 2)
      7   1   H        1 -> count 3                   2:[3]    3:[1]
      8   4   M        evict 3 (min=2)                1:[4]    3:[1]
      9   1   H        1 -> count 4                   1:[4]    4:[1]

    4 hits, 6 misses -- same totals as LRU, different positions (i5, i7).
    """
    keys = [1, 2, 1, 3, 2, 3, 3, 1, 4, 1]
    assert outcomes(2, keys) == "MMHMMMHHMH"


# --------------------------------------------------------------------------
# Appendix C test 3 — capacity invariant, LFU edition
# --------------------------------------------------------------------------

def test_capacity_is_never_exceeded():
    """Occupancy stays <= capacity after every request, at several sizes."""
    rng = random.Random(3)
    keys = [rng.randint(0, 40) for _ in range(20000)]
    for capacity in (1, 2, 3, 5, 10, 25):
        policy = LFU(capacity)
        for key in keys:
            if not policy.get(key):
                policy.put(key)
            assert resident_count(policy) <= capacity


def test_capacity_is_reached():
    """The cache does fill up -- the invariant above isn't met by storing nothing."""
    policy = LFU(5)
    for key in range(20):
        if not policy.get(key):
            policy.put(key)
    assert resident_count(policy) == 5
