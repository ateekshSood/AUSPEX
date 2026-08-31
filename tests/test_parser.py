"""Appendix C test 12 — parser.

Fixture file with malformed lines -> correct kept/dropped counts.

Written from PLAN §3.2's stated requirements, not from reading the
implementation (hard rule 8 / D015). Every expected value below is derived
from the fixture by hand.
"""

import gzip

import pandas as pd
import pytest

from auspex.parser_nasa import parse_line, parse_file, write_parquet


# --- the fixture -----------------------------------------------------------
#
# 14 lines, deliberately interleaved so that a kept row's `seq` can never be
# confused with its index among the kept rows.
#
#  seq  what it is                                    outcome
#  ---  --------------------------------------------  ---------
#   0   plain GET 200                                 kept
#   1   GET 404                                       dropped
#   2   GET 200, size "-"                             kept
#   3   not a log line at all                         malformed
#   4   GET 200, URL carries a #fragment              kept
#   5   POST 200                                      dropped
#   6   GET 200, URL carries a query string           kept
#   7   request field has one part ("GET")            malformed
#   8   GET 200, mixed-case path                      kept
#   9   GET 304                                       dropped
#  10   GET 200, non-UTF-8 (latin-1) byte in URL      kept
#  11   HEAD 200                                      dropped
#  12   empty request field ("")                      malformed
#  13   status is "-" not three digits                malformed
#
# totals: 14 lines, 6 kept, 4 dropped-by-filter, 4 malformed.
#
# Line 13 is written WITHOUT a trailing newline, mirroring the real NASA
# files (D008/D019): the parser must still count it.

FIXTURE_LINES = [
    b'199.72.81.55 - - [01/Jul/1995:00:00:01 -0400] "GET /history/apollo/ HTTP/1.0" 200 6245',
    b'burger.letters.com - - [01/Jul/1995:00:00:01 -0400] "GET /shuttle/missing.html HTTP/1.0" 404 -',
    b'unicomp6.unicomp.net - - [01/Jul/1995:00:00:06 -0400] "GET /shuttle/countdown/ HTTP/1.0" 200 -',
    b'this is not a log line at all',
    b'199.120.110.21 - - [01/Jul/1995:00:00:12 -0400] "GET /shuttle/missions/sts-73/mission.html#launch HTTP/1.0" 200 4085',
    b'205.212.115.106 - - [01/Jul/1995:00:00:12 -0400] "POST /cgi-bin/submit HTTP/1.0" 200 512',
    b'd104.aa.net - - [01/Jul/1995:00:01:00 -0400] "GET /cgi-bin/imagemap/countdown?99,176 HTTP/1.0" 200 110',
    b'129.94.144.152 - - [01/Jul/1995:00:01:00 -0400] "GET" 200 1234',
    b'ppp-mia-30.shiva.com - - [01/Jul/1995:00:01:30 -0400] "GET /History/Apollo/INDEX.HTML HTTP/1.0" 200 512',
    b'net-1-141.eden.com - - [01/Jul/1995:00:01:30 -0400] "GET /images/ksclogo.gif HTTP/1.0" 304 0',
    # 0xE9 is "e-acute" in latin-1 and is NOT valid UTF-8 on its own.
    b'gw1.att.com - - [01/Jul/1995:01:00:00 -0400] "GET /history/apollo/caf\xe9.html HTTP/1.0" 200 777',
    b'slip1.slip.net - - [01/Jul/1995:01:00:00 -0400] "HEAD /index.html HTTP/1.0" 200 0',
    b'dial22.lloyd.com - - [01/Jul/1995:01:00:00 -0400] "" 200 0',
    b'link097.txdirect.net - - [01/Jul/1995:01:00:00 -0400] "GET /shuttle/ HTTP/1.0" - -',
]

EXPECTED_TOTAL = 14
EXPECTED_KEPT = 6
EXPECTED_DROPPED = 4
EXPECTED_MALFORMED = 4

# Hand-computed: 1995-07-01 00:00:01 -0400 is 1995-07-01 04:00:01 UTC.
TS_00_00_01 = 804571201
TS_00_00_06 = 804571206
TS_00_00_12 = 804571212
TS_00_01_00 = 804571260
TS_00_01_30 = 804571290
TS_01_00_00 = 804574800


@pytest.fixture
def fixture_log(tmp_path):
    """Write the fixture as a real gzipped log file and return its path."""
    path = tmp_path / "fixture_access_log.gz"
    body = b"\n".join(FIXTURE_LINES)  # no trailing newline: last line unterminated
    with gzip.open(path, "wb") as f:
        f.write(body)
    return path


# --- parse_line ------------------------------------------------------------

def test_parse_line_extracts_every_field():
    row = parse_line(
        '199.72.81.55 - - [01/Jul/1995:00:00:01 -0400] '
        '"GET /history/apollo/ HTTP/1.0" 200 6245'
    )
    assert row == {
        "host": "199.72.81.55",
        "ts": TS_00_00_01,
        "method": "GET",
        "url": "/history/apollo/",
        "status": 200,
        "size": 6245,
    }


def test_parse_line_absent_size_becomes_none():
    """CLF writes '-' when the response size is absent; it must not become 0."""
    row = parse_line(
        'unicomp6.unicomp.net - - [01/Jul/1995:00:00:06 -0400] '
        '"GET /shuttle/countdown/ HTTP/1.0" 200 -'
    )
    assert row["size"] is None


@pytest.mark.parametrize(
    "line",
    [
        "this is not a log line at all",
        # request field with fewer than two parts
        '129.94.144.152 - - [01/Jul/1995:00:01:00 -0400] "GET" 200 1234',
        'dial22.lloyd.com - - [01/Jul/1995:01:00:00 -0400] "" 200 0',
        # status is not three digits
        'link097.txdirect.net - - [01/Jul/1995:01:00:00 -0400] "GET /shuttle/ HTTP/1.0" - -',
        "",
    ],
)
def test_parse_line_returns_none_on_malformed(line):
    """§3.2: count and skip corrupt lines, never crash."""
    assert parse_line(line) is None


# --- §3.2's URL normalization rule (D026) ----------------------------------

def test_url_fragment_is_stripped():
    row = parse_line(
        '199.120.110.21 - - [01/Jul/1995:00:00:12 -0400] '
        '"GET /shuttle/missions/sts-73/mission.html#launch HTTP/1.0" 200 4085'
    )
    assert row["url"] == "/shuttle/missions/sts-73/mission.html"


def test_url_query_string_is_kept_byte_for_byte():
    row = parse_line(
        'd104.aa.net - - [01/Jul/1995:00:01:00 -0400] '
        '"GET /cgi-bin/imagemap/countdown?99,176 HTTP/1.0" 200 110'
    )
    assert row["url"] == "/cgi-bin/imagemap/countdown?99,176"


def test_url_case_is_preserved():
    """URLs are case-sensitive; lowercasing would merge distinct objects."""
    row = parse_line(
        'ppp-mia-30.shiva.com - - [01/Jul/1995:00:01:30 -0400] '
        '"GET /History/Apollo/INDEX.HTML HTTP/1.0" 200 512'
    )
    assert row["url"] == "/History/Apollo/INDEX.HTML"


# --- parse_file counts (the headline of test 12) ---------------------------

def test_counts_match_the_fixture(fixture_log):
    r = parse_file(fixture_log)
    assert r["total"] == EXPECTED_TOTAL
    assert r["kept"] == EXPECTED_KEPT
    assert r["dropped"] == EXPECTED_DROPPED
    assert r["malformed"] == EXPECTED_MALFORMED


def test_counts_are_exhaustive(fixture_log):
    """Every line lands in exactly one bucket."""
    r = parse_file(fixture_log)
    assert r["malformed"] + r["dropped"] + r["kept"] == r["total"]
    assert len(r["kept_rows"]) == r["kept"]


def test_unterminated_final_line_is_counted(fixture_log):
    """The real files' last line has no newline (D008); it must still count."""
    r = parse_file(fixture_log)
    assert r["total"] == len(FIXTURE_LINES)


def test_latin1_line_survives(fixture_log):
    """Opened as latin-1: a 0xE9 byte must parse, not raise UnicodeDecodeError."""
    r = parse_file(fixture_log)
    urls = [row["url"] for row in r["kept_rows"]]
    assert "/history/apollo/caf\xe9.html" in urls


# --- the keep rule (D027) --------------------------------------------------

def test_only_get_200_survives(fixture_log):
    """404, 304, POST and HEAD are all dropped by the filter, not kept."""
    r = parse_file(fixture_log)
    urls = [row["url"] for row in r["kept_rows"]]
    assert "/shuttle/missing.html" not in urls   # 404
    assert "/images/ksclogo.gif" not in urls     # 304
    assert "/cgi-bin/submit" not in urls         # POST
    assert "/index.html" not in urls             # HEAD


# --- seq (§3.2: "the raw-log row index, born HERE") ------------------------

def test_seq_is_the_raw_log_row_index(fixture_log):
    """Not the index among kept rows — the fixture interleaves so they differ."""
    r = parse_file(fixture_log)
    assert [row["seq"] for row in r["kept_rows"]] == [0, 2, 4, 6, 8, 10]


def test_seq_is_strictly_increasing(fixture_log):
    r = parse_file(fixture_log)
    seqs = [row["seq"] for row in r["kept_rows"]]
    assert all(b > a for a, b in zip(seqs, seqs[1:]))


# --- timestamps ------------------------------------------------------------

def test_timestamps_are_utc_epoch_seconds(fixture_log):
    """-0400 must be honoured, not silently treated as local or naive time."""
    r = parse_file(fixture_log)
    assert [row["ts"] for row in r["kept_rows"]] == [
        TS_00_00_01,
        TS_00_00_06,
        TS_00_00_12,
        TS_00_01_00,
        TS_00_01_30,
        TS_01_00_00,
    ]


# --- parquet output (§3.2) -------------------------------------------------

def test_write_parquet_roundtrips_with_nullable_int32_size(fixture_log, tmp_path):
    """`size` must be nullable Int32 — '-' stays null, never 0, never float."""
    r = parse_file(fixture_log)
    out = tmp_path / "out.parquet"
    write_parquet(r["kept_rows"], out)

    df = pd.read_parquet(out)
    assert len(df) == EXPECTED_KEPT
    assert str(df["size"].dtype) == "Int32"
    assert df["size"].isna().sum() == 1          # exactly the one '-' row
    assert (df["size"].dropna() != 0).all()

    # C006/D013 pinned the column set (method/status deliberately absent).
    # Order is not pinned by §3.2, so it is deliberately not asserted here.
    assert set(df.columns) == {"seq", "ts", "host", "url", "size"}
    # written with index=False: no stray index column
    assert not any(c.startswith("__index_level_") for c in df.columns)


def test_write_parquet_preserves_row_order(fixture_log, tmp_path):
    r = parse_file(fixture_log)
    out = tmp_path / "out.parquet"
    write_parquet(r["kept_rows"], out)

    df = pd.read_parquet(out)
    assert df["seq"].tolist() == [0, 2, 4, 6, 8, 10]
