"""Appendix C tests 7 and 8 — Belady / MIN (PLAN §5.3).

    7. Belady hand-verified on 3 crafted traces (OPT computed on paper).
    8. Property: Belady >= LRU and >= LFU for every (trace, size),
       under FULL-SEQUENCE counting.
    9. (Belady's half) infinite >= Belady.

The definition under test (§5.3), restated: on a miss with a full cache,
evict the cached key whose next request is furthest in the future (never
requested again counts as furthest). The whole key sequence is given at
construction; each get() is the next request in that sequence.

Written from that definition, not from reading the implementation (hard
rule 8). Every expected sequence is derived by hand in the comment beside it,
and a deliberately naive reference (a forward scan on every eviction) is
included below so the fast implementation can be compared request by request.

Why full-sequence counting (§5.3): MIN minimises misses over everything it
processes. If only a suffix is scored, it may trade a scored hit for an
unscored one, so "Belady >= LRU" is only a theorem with no warmup.
"""

import random

from auspex.policies.belady import Belady
from auspex.policies.infinite import Infinite
from auspex.policies.lfu import LFU
from auspex.policies.lru import LRU


SIZES = (1, 2, 3, 5, 10, 25)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def outcomes(policy, keys: list[int]) -> str:
    """Drive a policy per the §4.3 contract (get; on a miss, put)."""
    out = []
    for key in keys:
        if policy.get(key):
            out.append("H")
        else:
            out.append("M")
            policy.put(key)
    return "".join(out)


def belady(capacity: int, keys: list[int]) -> str:
    return outcomes(Belady(capacity, keys), keys)


def reference_min(capacity: int, keys: list[int]) -> str:
    """Belady by brute force: on each eviction, scan the future.

    O(n * capacity * n) -- only for small traces. No heap, no next-use
    array, no counter: nothing shared with the implementation under test.
    """
    cache: set[int] = set()
    out = []
    for i, key in enumerate(keys):
        if key in cache:
            out.append("H")
            continue
        out.append("M")
        if len(cache) >= capacity:
            def next_request(k: int) -> int:
                for j in range(i + 1, len(keys)):
                    if keys[j] == k:
                        return j
                return len(keys)            # never again: furthest of all
            cache.remove(max(cache, key=next_request))
        cache.add(key)
    return "".join(out)


def random_traces() -> list[list[int]]:
    """Uniform, skewed (a hot set), and a cycle -- LRU's worst case."""
    rng = random.Random(8)
    uniform = [rng.randint(0, 30) for _ in range(1500)]
    skewed = [
        rng.randint(0, 4) if rng.random() < 0.7 else rng.randint(5, 120)
        for _ in range(1500)
    ]
    cyclic = list(range(12)) * 60
    return [uniform, skewed, cyclic]


# --------------------------------------------------------------------------
# Appendix C test 7 — hand-verified traces
# --------------------------------------------------------------------------

def test_hand_trace_session_example():
    """The worked example from the session, capacity 2.

      position   0  1  2  3  4  5
      key        A  B  A  C  B  A        (A=0, B=1, C=2)
      next use   2  4  5  6  6  6        (6 = never)

      i=0 A  M  {A}
      i=1 B  M  {A, B}
      i=2 A  H  A's next use 2 -> 5
      i=3 C  M  full; A (5) is furthest vs B (4) -> evict A     {B, C}
      i=4 B  H
      i=5 A  M  full; B and C both never again -> evict either  {., A}

    4 misses. LRU on the same trace evicts B at i=3 and makes 5.
    """
    keys = [0, 1, 0, 2, 1, 0]
    assert belady(2, keys) == "MMHMHM"
    assert outcomes(LRU(2), keys) == "MMHMMM"


def test_hand_trace_textbook_string_three_frames():
    """The classic string 1 2 3 4 1 2 5 1 2 3 4 5, capacity 3: OPT = 7 misses.

      i   key  outcome  eviction (next uses of the cached keys)
      0-3 1234 M M M M  at 4: 1@4 2@5 3@9 -> evict 3        {1,2,4}
      4   1    H
      5   2    H
      6   5    M        1@7 2@8 4@10 -> evict 4           {1,2,5}
      7   1    H
      8   2    H
      9   3    M        1 never, 2 never, 5@11 -> evict 1 or 2
      10  4    M        a never-again key is still there -> evict it
      11  5    H
    """
    keys = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    assert belady(3, keys) == "MMMMHHMHHMMH"
    assert belady(3, keys).count("M") == 7


def test_hand_trace_textbook_string_four_frames():
    """Same string, capacity 4: OPT = 6 misses.

      0-3 1234 M M M M
      4-5 1 2  H H
      6   5    M   1@7 2@8 3@9 4@10 -> evict 4
      7-9 1 2 3 H H H
      10  4    M   1, 2, 3 never again; 5@11 -> evict one of 1/2/3
      11  5    H
    """
    keys = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    assert belady(4, keys) == "MMMMHHMHHHMH"


def test_hand_trace_cycle_where_lru_scores_zero():
    """ABCD ABCD, capacity 3. LRU: 0 hits (the cyclic pathology). OPT: 3.

      0-2 A B C  M M M
      3   D      M   A@4 B@5 C@6 -> evict C          {A,B,D}
      4   A      H
      5   B      H
      6   C      M   A never, B never, D@7 -> evict A or B
      7   D      H
    """
    keys = [0, 1, 2, 3, 0, 1, 2, 3]
    assert belady(3, keys) == "MMMMHHMH"
    assert outcomes(LRU(3), keys) == "MMMMMMMM"


def test_capacity_holds_everything_means_only_first_sight_misses():
    keys = [0, 1, 0, 2, 1, 0, 2, 2, 1]
    assert belady(3, keys) == "MMHMHHHHH"


# --------------------------------------------------------------------------
# fast implementation vs the brute-force reference
# --------------------------------------------------------------------------

def test_matches_brute_force_reference_request_by_request():
    """Same H/M string as the forward-scan reference, every trace and size.

    Ties only ever happen among never-again keys (two different keys can't
    both be next requested at the same position), and evicting one
    never-again key instead of another can't change any later outcome --
    so the full sequence must match, not just the totals.
    """
    for keys in random_traces():
        for size in SIZES:
            assert belady(size, keys) == reference_min(size, keys), (
                f"size {size}"
            )


# --------------------------------------------------------------------------
# Appendix C test 8 — the property, full-sequence counting
# --------------------------------------------------------------------------

def test_belady_beats_or_ties_lru_and_lfu():
    """misses(Belady) <= misses(LRU) and <= misses(LFU), every trace and size.

    Every request counted -- no warmup (see module docstring).
    """
    for keys in random_traces():
        for size in SIZES:
            opt = belady(size, keys).count("M")
            for policy_class in (LRU, LFU):
                other = outcomes(policy_class(size), keys).count("M")
                assert opt <= other, (
                    f"{policy_class.name} beat Belady at size {size}: "
                    f"{other} < {opt} misses"
                )


# --------------------------------------------------------------------------
# Appendix C test 9 — Belady's half
# --------------------------------------------------------------------------

def test_infinite_beats_or_ties_belady():
    for keys in random_traces():
        ceiling = outcomes(Infinite(1), keys).count("H")
        for size in SIZES:
            assert ceiling >= belady(size, keys).count("H")


def test_belady_equals_infinite_when_everything_fits():
    for keys in random_traces():
        distinct = len(set(keys))
        assert belady(distinct, keys) == outcomes(Infinite(1), keys)
