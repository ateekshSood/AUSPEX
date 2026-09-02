"""Appendix C test 11 — sessionizer.

    "gap>30 min splits; length-1 sessions *retained* in output;
     same-second order stable via (ts, seq)."

Written from PLAN §3.3's stated requirements, not from reading the
implementation (hard rule 8 / D015). Every expected count below is derived by
hand from the fixture frame it sits next to.

§3.3, restated as the contract under test:
  1. stable-sort by (host, ts, seq) -- the third key makes same-second order
     deterministic;
  2. split a host's stream wherever the gap to the previous request *exceeds*
     cfg.session_gap_s;
  3. assign session_id (running int) and pos_in_session;
  4. length-1 sessions are RETAINED in the output;
  5. bot rules: robots.txt host / over-long session / near-constant cadence,
     each reporting how much it removed;
  6. output sorted globally by (ts, seq) -- never by session.
"""

import pandas as pd
import pytest

from auspex.config import Cfg
from auspex.sessionize import (
    label_sessions,
    drop_robots_hosts,
    drop_long_sessions,
    drop_metronome_hosts,
)


CFG = Cfg()

# Parser output columns (PLAN §3.2) that §3.3 consumes.
COLUMNS = ["host", "ts", "url", "size", "seq"]


def frame(rows: list[tuple[str, int, str, int]]) -> pd.DataFrame:
    """rows are (host, ts, url, seq); `size` is along for the ride."""
    return pd.DataFrame(
        [(h, ts, url, 100, seq) for h, ts, url, seq in rows], columns=COLUMNS
    )


def sid_of(df: pd.DataFrame, seq: int) -> int:
    """The session_id of the row carrying this raw-log seq."""
    return int(df.loc[df["seq"] == seq, "session_id"].iloc[0])


# --- step 2: where sessions split ------------------------------------------
#
# One host, four requests. GAP is cfg.session_gap_s (1800).
#
#  seq   ts             gap to previous   splits?
#  ---   ------------   ---------------   -------
#   0    1_000          --                (first)
#   1    1_000 + 1800   exactly 1800      no  -- "exceeds", not "reaches"
#   2    2_800 + 1801   1801              yes
#   3    4_601 + 1      1                 no


def test_gap_strictly_greater_than_threshold_splits():
    g = CFG.session_gap_s
    df = frame(
        [
            ("h", 1_000, "/a", 0),
            ("h", 1_000 + g, "/b", 1),
            ("h", 1_000 + g + g + 1, "/c", 2),
            ("h", 1_000 + g + g + 2, "/d", 3),
        ]
    )
    out = label_sessions(df, CFG)

    assert out["session_id"].nunique() == 2
    assert sid_of(out, 0) == sid_of(out, 1), "a gap of exactly session_gap_s must not split"
    assert sid_of(out, 1) != sid_of(out, 2), "a gap of session_gap_s + 1 must split"
    assert sid_of(out, 2) == sid_of(out, 3)


def test_a_different_host_never_shares_a_session():
    df = frame(
        [
            ("alice", 1_000, "/a", 0),
            ("bob", 1_000, "/a", 1),
            ("alice", 1_001, "/b", 2),
        ]
    )
    out = label_sessions(df, CFG)

    # Sessionization happens in sort-1 space (host, ts, seq), so alice's two
    # requests are adjacent there and share a session -- bob's interleaved
    # request does NOT cut them apart. Two sessions, not three.
    assert out["session_id"].nunique() == 2
    assert sid_of(out, 0) == sid_of(out, 2), "same host, 1 s apart -> one session"
    assert sid_of(out, 1) != sid_of(out, 0), "bob is never in alice's session"


def test_no_session_ever_spans_two_hosts():
    df = frame(
        [
            ("alice", 1_000, "/a", 0),
            ("bob", 1_001, "/b", 1),
            ("alice", 1_002, "/c", 2),
            ("carol", 1_003, "/d", 3),
            ("bob", 1_004, "/e", 4),
        ]
    )
    out = label_sessions(df, CFG)

    assert (out.groupby("session_id")["host"].nunique() == 1).all()


def test_in_session_gaps_are_non_negative_and_within_the_threshold():
    df = frame(
        [
            ("alice", 1_000, "/a", 0),
            ("alice", 1_500, "/b", 1),
            ("alice", 9_000, "/c", 2),
            ("bob", 1_200, "/a", 3),
            ("bob", 1_200, "/b", 4),
        ]
    )
    out = label_sessions(df, CFG)

    gaps = out.groupby("session_id")["ts"].diff().dropna()
    assert (gaps >= 0).all(), "ts must never run backwards inside a session"
    assert (gaps <= CFG.session_gap_s).all()


# --- step 3: pos_in_session -------------------------------------------------


def test_pos_in_session_starts_at_zero_and_is_contiguous():
    df = frame(
        [
            ("alice", 1_000, "/a", 0),
            ("alice", 1_001, "/b", 1),
            ("alice", 1_002, "/c", 2),
            ("bob", 1_003, "/a", 3),
            ("alice", 90_000, "/d", 4),
        ]
    )
    out = label_sessions(df, CFG)

    for _, g in out.groupby("session_id"):
        pos = sorted(g["pos_in_session"].tolist())
        assert pos == list(range(len(g))), "0..n-1, no gaps, no repeats"


def test_pos_in_session_ascends_with_ts():
    df = frame(
        [
            ("alice", 1_000, "/a", 0),
            ("alice", 1_005, "/b", 1),
            ("alice", 1_009, "/c", 2),
        ]
    )
    out = label_sessions(df, CFG).sort_values("pos_in_session")

    assert out["ts"].is_monotonic_increasing


# --- step 1: same-second order is stable via seq ----------------------------
#
# Four requests, one host, ALL at ts 1_000, presented out of seq order.
# §3.3 step 1 says the tie is broken by the raw-log row index, so the session
# must read seq 2, 5, 7, 9 -- and pos_in_session must agree.


def test_same_second_order_is_broken_by_seq():
    df = frame(
        [
            ("alice", 1_000, "/d", 9),
            ("alice", 1_000, "/b", 5),
            ("alice", 1_000, "/a", 2),
            ("alice", 1_000, "/c", 7),
        ]
    )
    out = label_sessions(df, CFG).sort_values("pos_in_session")

    assert out["seq"].tolist() == [2, 5, 7, 9]
    assert out["url"].tolist() == ["/a", "/b", "/c", "/d"]


def test_labelling_never_drops_or_duplicates_a_row():
    df = frame(
        [
            ("alice", 1_000, "/a", 0),
            ("bob", 1_000, "/a", 1),
            ("alice", 99_000, "/b", 2),
        ]
    )
    out = label_sessions(df, CFG)

    assert len(out) == len(df)
    assert sorted(out["seq"].tolist()) == [0, 1, 2]


# --- step 4: singletons are RETAINED ---------------------------------------


def test_length_one_sessions_are_retained():
    """PLAN §3.3 step 4: a singleton is a real request; it stays in the
    workload and is excluded only at transition-extraction time."""
    df = frame(
        [
            ("alice", 1_000, "/a", 0),
            ("alice", 1_100, "/b", 1),
            ("loner", 1_050, "/x", 2),        # one request, ever
            ("alice", 500_000, "/c", 3),      # far future -> its own singleton
        ]
    )
    out = label_sessions(df, CFG)

    sizes = out.groupby("session_id").size()
    assert sorted(sizes.tolist()) == [1, 1, 2]
    assert 2 in out["seq"].tolist(), "the lone host survives labelling"
    assert 3 in out["seq"].tolist(), "a host's trailing singleton survives too"


def test_singletons_survive_every_bot_rule():
    df = frame(
        [
            ("loner", 1_000, "/x", 0),
            ("alice", 1_001, "/a", 1),
            ("alice", 1_002, "/b", 2),
        ]
    )
    out = label_sessions(df, CFG)
    out, _ = drop_robots_hosts(out)
    out, _ = drop_long_sessions(out, CFG)
    out, _ = drop_metronome_hosts(out, CFG)

    assert 0 in out["seq"].tolist()


# --- step 5, rule 1: any host that ever requests /robots.txt ---------------


def test_robots_rule_drops_the_whole_host_not_just_the_row():
    df = frame(
        [
            ("crawler", 1_000, "/a", 0),
            ("crawler", 1_001, "/robots.txt", 1),
            ("crawler", 1_002, "/b", 2),
            ("alice", 1_003, "/a", 3),
        ]
    )
    labelled = label_sessions(df, CFG)
    out, dropped = drop_robots_hosts(labelled)

    assert dropped == 3, "all three crawler rows, not just the /robots.txt one"
    assert out["host"].tolist() == ["alice"]
    assert len(out) == len(labelled) - dropped


def test_robots_rule_is_a_no_op_when_nobody_asks_for_it():
    df = frame([("alice", 1_000, "/a", 0), ("bob", 1_001, "/b", 1)])
    out, dropped = drop_robots_hosts(label_sessions(df, CFG))

    assert dropped == 0
    assert len(out) == 2


# --- step 5, rule 2: sessions longer than cfg.bot_max_session_len ----------


def long_session(host: str, n: int, start_seq: int) -> list[tuple[str, int, str, int]]:
    """n requests, 10 s apart -- one session, since 10 << session_gap_s."""
    return [(host, 1_000 + 10 * i, f"/p{i}", start_seq + i) for i in range(n)]


def test_long_session_rule_uses_a_strict_greater_than():
    n = CFG.bot_max_session_len
    df = frame(long_session("exact", n, 0) + long_session("over", n + 1, 10_000))
    labelled = label_sessions(df, CFG)
    out, dropped = drop_long_sessions(labelled, CFG)

    assert dropped == n + 1, "only the over-length session goes"
    assert set(out["host"]) == {"exact"}
    assert len(out) == n


def test_long_session_rule_drops_the_session_not_the_host():
    """A host with one runaway session keeps its other, human-sized sessions."""
    n = CFG.bot_max_session_len + 1
    rows = long_session("mixed", n, 0)
    # far enough after the runaway to start a fresh session
    tail_start = 1_000 + 10 * n + CFG.session_gap_s + 1
    rows += [("mixed", tail_start + i, f"/q{i}", 10_000 + i) for i in range(3)]

    labelled = label_sessions(frame(rows), CFG)
    out, dropped = drop_long_sessions(labelled, CFG)

    assert dropped == n
    assert len(out) == 3
    assert set(out["host"]) == {"mixed"}


# --- step 5, rule 3: >=100 requests with gap CV < 0.1 ----------------------


def metronome(host: str, n: int, period: int, start_seq: int):
    return [(host, 1_000 + period * i, f"/p{i}", start_seq + i) for i in range(n)]


def jittery(host: str, n: int, start_seq: int):
    # gaps alternate 10 s and 200 s -> mean 105, std ~95, CV ~0.9
    ts, rows = 1_000, []
    for i in range(n):
        rows.append((host, ts, f"/p{i}", start_seq + i))
        ts += 10 if i % 2 == 0 else 200
    return rows


def test_metronome_rule_drops_a_constant_cadence_host():
    n = CFG.bot_cv_min_request
    df = frame(metronome("clock", n, 100, 0) + jittery("human", n, 10_000))
    labelled = label_sessions(df, CFG)
    out, dropped = drop_metronome_hosts(labelled, CFG)

    assert dropped == n, "CV of a perfectly constant cadence is 0"
    assert set(out["host"]) == {"human"}


def test_metronome_rule_min_requests_is_a_sample_size_gate():
    """PLAN §3.3: '>= 100 requests'. A short constant-cadence host is not
    enough evidence and must survive."""
    df = frame(metronome("shy", CFG.bot_cv_min_request - 1, 100, 0))
    out, dropped = drop_metronome_hosts(label_sessions(df, CFG), CFG)

    assert dropped == 0
    assert len(out) == CFG.bot_cv_min_request - 1


def test_metronome_rule_spares_a_busy_but_irregular_host():
    df = frame(jittery("human", CFG.bot_cv_min_request * 2, 0))
    out, dropped = drop_metronome_hosts(label_sessions(df, CFG), CFG)

    assert dropped == 0


def test_metronome_rule_leaves_no_working_columns_behind():
    df = frame(jittery("human", 10, 0))
    labelled = label_sessions(df, CFG)
    out, _ = drop_metronome_hosts(labelled, CFG)

    assert list(out.columns) == list(labelled.columns)


# --- the bot rules must not disturb the survivors --------------------------


def test_bot_rules_never_renumber_or_split_a_surviving_session():
    """Dropping rows is a filter, not a re-labelling: a session that survives
    must come out with the same session_id and the same pos_in_session it
    went in with."""
    rows = (
        [("crawler", 1_000, "/robots.txt", 0)]
        + long_session("runaway", CFG.bot_max_session_len + 1, 1)
        + metronome("clock", CFG.bot_cv_min_request, 100, 10_000)
        + [
            ("alice", 1_000, "/a", 20_000),
            ("alice", 1_060, "/b", 20_001),
            ("alice", 1_120, "/c", 20_002),
            ("loner", 1_030, "/x", 20_003),
        ]
    )
    labelled = label_sessions(frame(rows), CFG)
    before = labelled.set_index("seq")[["session_id", "pos_in_session"]]

    out, d1 = drop_robots_hosts(labelled)
    out, d2 = drop_long_sessions(out, CFG)
    out, d3 = drop_metronome_hosts(out, CFG)

    assert d1 + d2 + d3 == len(labelled) - len(out), "the printed counts must add up"
    assert set(out["host"]) == {"alice", "loner"}

    after = out.set_index("seq")[["session_id", "pos_in_session"]]
    pd.testing.assert_frame_equal(after, before.loc[after.index])

    # and alice's session is still whole and contiguous
    alice = out[out["host"] == "alice"]
    assert alice["session_id"].nunique() == 1
    assert sorted(alice["pos_in_session"].tolist()) == [0, 1, 2]


# --- step 6: the output contract -------------------------------------------
#
# THE SORT-2 REGRESSION TEST. §3.3 step 6: the written file is sorted globally
# by (ts, seq), NOT by session and NOT by host -- re-introducing `host` as a
# sort key here is the v1.1 bug the plan calls its biggest.
#
# `write()` derives its own output path from __file__, so these run against
# the real artifact rather than a tmp_path fixture. They skip when `make data`
# has not been run.

CLEANED = {
    "Jul95": "data/processed/NASA_access_log_cleaned_Jul95.parquet",
    "Aug95": "data/processed/NASA_access_log_cleaned_Aug95.parquet",
}

REQUIRED_COLUMNS = {"ts", "seq", "host", "url", "session_id", "pos_in_session"}


@pytest.fixture(scope="module")
def cleaned(request):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / CLEANED[request.param]
    if not path.exists():
        pytest.skip(f"{path.name} not built; run `make data` first")
    return pd.read_parquet(path)


@pytest.mark.parametrize("cleaned", ["Jul95", "Aug95"], indirect=True)
def test_output_is_sorted_globally_by_ts_seq(cleaned):
    assert cleaned["ts"].is_monotonic_increasing, "sorted by ts, not by session/host"
    keys = list(zip(cleaned["ts"], cleaned["seq"]))
    assert keys == sorted(keys), "(ts, seq) must be non-decreasing"


@pytest.mark.parametrize("cleaned", ["Jul95", "Aug95"], indirect=True)
def test_output_seq_is_unique_so_the_order_is_total(cleaned):
    assert cleaned["seq"].is_unique


@pytest.mark.parametrize("cleaned", ["Jul95", "Aug95"], indirect=True)
def test_output_carries_the_required_columns(cleaned):
    assert REQUIRED_COLUMNS <= set(cleaned.columns)


@pytest.mark.parametrize("cleaned", ["Jul95", "Aug95"], indirect=True)
def test_output_holds_the_session_invariants(cleaned):
    assert (cleaned.groupby("session_id")["host"].nunique() == 1).all()
    gaps = cleaned.sort_values(["session_id", "ts", "seq"]).groupby("session_id")["ts"].diff().dropna()
    assert (gaps >= 0).all()
    assert (gaps <= CFG.session_gap_s).all()


@pytest.mark.parametrize("cleaned", ["Jul95", "Aug95"], indirect=True)
def test_output_still_contains_singleton_sessions(cleaned):
    """§3.3 step 4 again, at the artifact level: if this ever reads 0, some
    'cleanup' has started dropping singletons from the replay workload."""
    sizes = cleaned.groupby("session_id").size()
    assert (sizes == 1).sum() > 0
