# libCacheSim cross-check — Stage 2 evidence (PLAN §5.4)

**Result: exact match.** On NASA-HTTP July 1995 (1,671,535 kept requests),
our LRU and our LFU produce the **same miss count as libCacheSim at every
cache size** — not approximately, request-for-request in total.

| capacity (objects) | LRU — ours | LRU — libCacheSim | LFU — ours | LFU — libCacheSim |
|---:|---:|---:|---:|---:|
| 100    | 611,562 | 611,562 | 640,769 | 640,769 |
| 500    | 197,494 | 197,494 | 262,978 | 262,978 |
| 1,000  |  76,602 |  76,602 | 111,748 | 111,748 |
| 5,000  |   7,754 |   7,754 |   7,539 |   7,539 |
| 10,000 |   7,207 |   7,207 |   7,207 |   7,207 |

At 10,000 both policies make exactly 7,207 misses — the number of distinct
URLs in July — because the whole URL universe fits and only first
appearances miss.

These are **cross-check numbers, not the reported P1 results**: every request
is counted (no warmup), which removes the protocol as a variable and tests
only the eviction machinery. The P1 hit rates live in the per-run JSONs.

## Why this check exists

Every later claim in the project is "the prefetcher beats LRU by X". That is
only as good as the LRU it is compared against. An independent, widely used
simulator reproducing our baseline exactly rules out a crippled or subtly
wrong baseline. PLAN §5.4 sets the bar at *exact*: with identical order, zero
warmup, object-count capacity and admit-on-miss, there is no legitimate
source of a small difference.

## Setup

| | |
|---|---|
| Our code | commit `85a54ec` (`policies/lru.py`, `policies/lfu.py`, `harness/replay.py`) |
| libCacheSim | commit `93529a1`, built from source in `~/tools/libCacheSim` (outside this repo), plus the one-line print patch below |
| Trace | `data/processed/Jul95.csv`, written by `harness/export_libcachesim.py -j` |
| Order | the CSV is written from `trace_loading()` — the very arrays `policy_loop` replays — so the two simulators cannot see different orders |
| Warmup | none on either side; libCacheSim logs `num_warmup_req 0` |
| Capacity | number of objects (`--ignore-obj-size 1`), matching `LRU(n)` / `LFU(n)` |
| Admission | none on either side (every miss is inserted); libCacheSim's run log lists no admission algorithm |

### libCacheSim command

```bash
~/tools/libCacheSim/_build/bin/cachesim \
    data/processed/Jul95.csv csv lru 100,500,1000,5000,10000 \
    --ignore-obj-size 1 \
    -t "time-col=1, obj-id-col=2, obj-id-is-num=true, delimiter=,, has-header=true" \
    -o results/libcachesim/Jul95_lru_exact
```

(and the same with `lfu` → `results/libcachesim/Jul95_lfu_exact`).

### Our side

`policy_loop(Policy(size), …)` from `harness/replay.py`, with a counted mask
of all `True` (every request scored) instead of the P1 mask.

### The one change made to libCacheSim

`cachesim` computes the exact miss count but printed only `miss ratio %.4lf`.
On 1.67M requests one step in the 4th decimal is ~167 requests, too coarse to
call a match exact. `libCacheSim/bin/cachesim/main.c` was patched to also
print `result[i].n_miss`:

```diff
-  "%s %s cache size %8ld%s, %lld req, miss ratio %.4lf",
+  "%s %s cache size %8ld%s, %lld req, %lld miss, miss ratio %.4lf",
   ...
-  (long long)result[i].n_req, miss_ratio);
+  (long long)result[i].n_req, (long long)result[i].n_miss,
+  miss_ratio);
```

Print-only: no simulation code was touched. (Before the patch, all five LRU
ratios already agreed to 4 decimals: 0.3659 / 0.1182 / 0.0458 / 0.0046 /
0.0043; that first run is kept as `results/libcachesim/Jul95_lru.cachesim`.)

## LFU: why an exact match was possible

PLAN §5.4 expected LFU to match only if libCacheSim's variant is the one we
pinned (D056). Reading its `cache/eviction/LFU.c` confirms it is:

| | ours (D056) | libCacheSim `LFU.c` |
|---|---|---|
| count on insert | 1 | 1 |
| on eviction | count discarded | "do not keep an object's frequency after evicting" |
| structure | count → ordered bucket, plus `min_count` | freq → linked list, plus `min_freq` |
| on a hit | move to the **back** of the next bucket | `append_obj_to_tail` of the next bucket |
| victim | **front** of the min-count bucket | `first_obj` of the min-freq node |

libCacheSim calls its tie-break "FIFO within a frequency", but since every hit
re-appends the object at the tail of its new bucket, the order inside a bucket
is order of *last access* — the same least-recently-used tie-break as ours.

## Belady

Not cross-checked against libCacheSim. PLAN §5.3 allows either converting the
trace with libCacheSim's `traceConv` or relying on hand-verified tests;
we rely on `tests/test_belady.py`: four traces with OPT computed on paper, and
a brute-force forward-scan MIN that the implementation matches
request-by-request on three trace shapes at six sizes (D062).

## Reproduce

```bash
uv run python -m auspex.harness.export_libcachesim -j # writes data/processed/Jul95.csv
# then the cachesim command above, for lru and lfu
```

Our-side numbers were produced on 2026-09-30 by calling `policy_loop` with an
all-`True` counted mask from a one-off command, not yet from a committed
script or `make` target. **Open:** add one (e.g. a no-warmup mode in the
harness) so this side is reproducible with one command too.
