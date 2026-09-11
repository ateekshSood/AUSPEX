# AUSPEX

Asynchronous predictive prefetching over an LRU-managed cache, evaluated against
standard policies by trace replay on real request logs.

## CHECK DECISIONS.MD FOR PROJECT PROGRESS

## Data

The NASA-HTTP 1995 traces are **not committed to this repo** — they are 37 MB of
public archive data that anyone can re-fetch. Download them into `data/raw/`:

```commands to download dataset: 
mkdir -p data/raw && cd data/raw
curl -O https://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz
curl -O https://ita.ee.lbl.gov/traces/NASA_access_log_Aug95.gz
```

Source: the [Internet Traffic Archive](https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html)
at Lawrence Berkeley National Laboratory — the canonical origin of this dataset.

Verify what you downloaded:


### Known quirks of these files

Measured, not assumed — see `decisions.md` D008, C002, C003.

- **July covers Jul 1 – Jul 28 only**, not Jul 31. Jul 28 is a half-day, ending
  13:32. Do not hardcode a Jul 29–31 window.
- **July's last line is truncated** (`alyssa.p`, no newline). This is genuine in
  the archive, not a bad download; `wc -l` therefore reports 1,891,714 against a
  true 1,891,715 records. The truncated line is a real malformed record and is
  expected to appear in the parser's dropped count.
- **August starts Aug 1, not Aug 4**, and **Aug 2 is entirely missing** (a
  ~37.7-hour outage from Aug 1 14:52 to Aug 3 04:36).
