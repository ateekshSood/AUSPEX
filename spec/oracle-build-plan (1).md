# Project ORACLE — Detailed Build Plan (v1.3)

**Companion to:** *Project ORACLE — Team Specification v1* (August 2026)
**Purpose of this document:** The spec says *what and why*. This document says *do this, in this file, with this command, and here is the test that proves it's done*. It is written to be dropped into the repo and handed to Claude Code stage by stage.

**How to read it:** Section 0 is the analysis. Section 1 is the rules that never bend. Section 2 sets up the repo. Sections 3–11 are the stages (0 through 8), each ending in an acceptance checklist that gates the next stage. Section 12 is how to drive Claude Code with this plan. Appendices hold the exact day-one commands, the results schema, and the full test list.

**Changelog v1.1** — folds in the external spec review and the résumé-readiness notes: infinite-cache "ceiling" claim corrected (§5.2); two-segment parity claim weakened and a prefetch-fraction sweep added (§6.5–6.6); metrics widened to a demand-latency distribution, timely-prefetch rate, efficiency, and occupancy (§6.4); block-bootstrap 95% confidence intervals (new §6.7); "predictive prefetching, not learned eviction" naming rule (§1 rule 11, CLAUDE.md); millisecond timing claims now require the own/ms-synthetic trace (§8.1); backend-hardening menu + authorization boundary (§9.4, §8.3); learned eviction and byte capacity precisely defined as Stage 7 stretch goals (§10); claims/résumé staging discipline (§15 item 11).

**Changelog v1.2** — responds to the external review *of this plan* (not the spec). Three concessions, all breaking: **(1)** replay is now global-chronological with per-session model context — sessionizer output re-sorted by `(ts, seq)`, `seq` column added, `observe()` gains `session_id` (§3.3, §4.1, §4.3, tests 21–22); **(2)** a dedicated validation window (P2-dev) — every knob is tuned there and the final Jul 25–31 window is run once per configuration freeze (§6.2, §6.6, §1 rule 12); **(3)** full-vocabulary Laplace smoothing dropped for empirical probability + min-support — the v1 defaults produced a prefetcher that could never fire (§6.3). Also adopted: backend-load budget + Pareto view for τ selection (§6.6); Appendix C test 9 rescoped to demand-fetch and an optional perfect-next-prefetch oracle bound (§5.2); NASA realistic timing reframed as a bounded sensitivity scenario (§6.4); Stage 6 event-logging pinned against the unawaited-coroutine trap, Lua atomicity, `XAUTOCLAIM` recovery, prefetch concurrency cap (§9.1); timeline revised to ~15–23 focused days (§13); determinism test fixed, dataset hashing, pinned deps, formalized bot rule + unfiltered sensitivity, html-only elevated to a required attribution check (§2–3, §15, App. B–C).

**Changelog v1.3** — responds to the review of v1.2; all eight must-fixes conceded. Singleton sessions stay in the replay workload and leave only training (§3.3, test 23); the parser now actually emits `seq / method / status / size` with `'-'` handled (§3.2); the Stage 3/4 contradiction fixed — Stage 3 never touches the final window, one **sealed predeclared batch** at the end of Stage 4 replaces "once per freeze" (§6.2, §7, rule 12); the pending-prefetch race is a pinned state machine with a segment-exclusivity invariant (§6.4, tests 24–25); event publication fires on hits *and* misses, XACK + idempotency promoted from menu to core, cross-process coalescing via a Redis inflight claim (§9.1, §9.4); the worker-death claim corrected and heartbeat segment-reclaim added (§1 rule 2, §9.1); the oracle-prefetch bound promoted to required — built *before* the Markov model — and made the gate of last resort (§5.2, §5.5); Belady relabelled **whole-horizon MIN**, not counted-suffix optimal, with property tests pinned to full-sequence counting (§5.3, test 8). Refinements adopted: common random numbers for latency (§6.4), V_train vs global encoder (§6.1), exact libCacheSim match (§5.4), CLAUDE.md description fixed, two-tier definition of done (§15). Minors: Stage 6 duration, monotonic ZSET scores, frozen config in compose, consistent JSON example, window-edge censoring.

---

## 0. Analysis — what this project is, and where it lives or dies

**In one paragraph.** ORACLE replaces LRU's fixed heuristic ("recently used → will be used again") with a learned one ("about to be used → load it now"). The system has two loops: a plain synchronous cache on the serving path, and an asynchronous learner/prefetcher off to the side that reads the event stream, updates a Markov transition table, and pushes predicted-next entries into the cache before they are requested. The deliverable is not the model — it is one honestly measured number: hit-rate improvement over LRU on real production traces (NASA-HTTP first), at matched cache sizes, with LFU, Belady, and infinite-cache as reference points, and with the failure modes (pollution, prefetch latency, drift) measured and reported rather than hidden.

**Where the value concentrates.** Roughly 70% of the project's credibility lives in Stages 0–2 (data, harness, baselines, libCacheSim cross-check) — before any ML exists. The model is a plugin into the harness. This is the same shape as the pump-detector lesson: the evaluation methodology *is* the project, and every impressive-sounding result that skips it collapses on the first hard question.

**The four ways it dies (each has a gate in this plan):**

1. **Crippled baseline** — your LRU is subtly wrong, so anything beats it. Gate: exact-match cross-check against libCacheSim (Stage 2, §5.4).
2. **Dishonest prefetch timing** — you assume prefetches are instant; in reality many arrive after the request they were meant to serve. Gate: the latency-aware replay mode and the idealised-vs-realistic pair of numbers (Stage 3, §6.4).
3. **Cache pollution** — over-eager prefetching evicts things LRU would have kept, and your hit rate lands *below* baseline. Gate: two-segment cache, prefetch-precision metric, τ sweep (Stage 3, §6.5–6.6).
4. **Leakage / circularity** — random train/test splits, or a synthetic generator from the same model class you're fitting. Gate: time-based split protocol pinned in §6.2; generator rules in §9 and spec §7.4.

**Deployability — the direct answer to the question.** Your instinct is half right. The *evaluation* is offline by design — trace replay on production logs is how the entire caching literature works, and spec §14 gives you the exact sentence to say about it. But the *system* is absolutely deployable, and this plan makes it so: Stage 6 builds the live FastAPI + Redis + worker stack as real running services, Stage 8 packages it with Docker Compose and gives you three deployment paths (VPS, Fly.io/Railway, and the stretch option of mounting it in front of your actual DHIS2 OCR service's read endpoints). What you deploy is a *live demo of the system*, not a production rollout — and the plan tells you exactly how to phrase that distinction so it reads as rigor, not weakness.

**What's new for you vs. what's free.** FastAPI, Redis, Docker, async fire-and-forget — you already have all of this from the OCR service; Loop 2 here is structurally identical to your async OCR worker (events in → worker processes → state out). The genuinely new muscles are: writing a correct discrete-event simulator, implementing eviction algorithms (Belady especially), and the evaluation discipline (matched counted windows, warmup handling, external validation). Those are exactly the muscles worth building.

**The external review, mapped.** The spec later received an outside review (scorecard + eight fixes) and a résumé-readiness note. Checked against this plan: several points were already enforced here, several were genuine gaps — now patched. The map:

| Review point | Where it lands in v1.1 |
|---|---|
| 1 · Solo scope too large | Already structural: hard gates; Stages 0–4 = the complete project (§13); 5/6/8 tiered |
| 2 · Learned eviction never specified | Renamed *predictive prefetching* (§1 rule 11); a **defined** eviction score parked in Stage 7 (§10 item 3) |
| 3 · Hit rate alone insufficient | Was partial (extra-backend-load, coverage); now adds latency distribution, timely rate, efficiency, occupancy (§6.4, App. B) |
| 4 · Infinite cache mislabelled as ceiling | Conceded — v1's §5.2 was subtly wrong under protocol P2; corrected labels + reasoning (§5.2) |
| 5 · Segments ≠ free parity with LRU | v1's "worst case: waste f" phrasing was too strong; weakened to "pollution-bounded", f-sweep with f = 0 control added (§6.5–6.6) |
| 6 · NASA 1 s timing too coarse | ms-level timing headline now requires the own trace or ms-stamped synthetic (§8.1) |
| 7 · "Statistically meaningful" undefined | Block-bootstrap 95% CIs — new §6.7 |
| 8 · Entry-count capacity is a simplification | Assumption stated; `size` column now kept in parsing (§3.2); byte-capacity stretch (§10 item 2) |
| Backend-hardening checklist | Menu of 3–4 required, incl. coalescing + idempotency; authorization rule (§9.4, §8.3, §11.4) |
| Résumé wording & staging | §1 rule 11 + §15 item 11 (don't list until built; never invent numbers; name your track) |

**The second review — of this plan — mapped.** This one drew blood: one outright design bug and two methodology errors that survived v1.1.

| Plan-review point | Status in v1.2 |
|---|---|
| 1 · Session-concatenated replay | **Conceded — a real bug.** Worse: the libCacheSim export shared the wrong order, so the cross-check would have *matched while both were unrealistic*. Fixed: global `(ts, seq)` order, per-session context (§3.3, §4.1, §4.3) |
| 2 · τ (and every knob) tuned on the test window | **Conceded** — preached the pump-detector leakage lesson, then scheduled a milder form of it. P2-dev validation split; final window run once (§6.2) |
| 3 · Laplace α·V kills confidence | **Conceded** — the spec's formula, propagated without doing the arithmetic. Under it no row with support < V/3 can ever cross τ = 0.4. Empirical + min-support (§6.3) |
| 4 · Learned eviction undefined | Fixed in v1.1 (naming rule; defined Stage 7 variant) — review saw v1 |
| 5 · Infinite ceiling | §5.2 fixed in v1.1; residual caught here: App. C test 9 rescoped; oracle-prefetch bound added (§5.2) |
| 6 · NASA 1 s timing | v1.1 already required ms data for the claim; v1.2 adds the pessimistic/central bounds bracket (§6.4) |
| 7 · Redis/event semantics | Adopted: awaited/queued `XADD` (the unawaited-coroutine trap is real), Lua atomicity, `XAUTOCLAIM`, prefetch semaphore (§9.1) |
| Backend-load budget + Pareto | Adopted (§6.6, §15 item 1) |
| Confidence intervals | Already in v1.1 (§6.7); Δbackend-fetch CI added to the set |
| Timeline optimistic | Revised: ~15–23 focused days + wall-clock caveats (§13) |
| Deferral list | Mostly aligned; two mild dissents: online drift stays in Stage 4 (≈20 lines, spec objective 4), and no per-event object allocation in the hot loop despite the suggested dataclass (§4.1) |

**The third review — of v1.2 — mapped.** Four rounds in, still drawing blood: three protocol-level catches no test in Appendix C would have caught, plus a contradiction v1.2 itself introduced.

| v1.2-review point | Status in v1.3 |
|---|---|
| 1 · Singletons dropped from replay | **Conceded — same family as the ordering bug** (evaluating a doctored workload), and again the spec's own instruction, propagated. Kept in replay, excluded from training only (§3.3, tests 11/23) |
| 2 · Parser/schema mismatch | Conceded; snippet now emits `seq / method / status / size`, `'-'` → null (§3.2) |
| 3 · Stage 3/4 vs the final window | **Conceded — a contradiction v1.2 created** when the P2-dev patch was bolted onto the old stage order. Stage 3 = validation only; one sealed batch after Stage 4; the "once per freeze" loophole closed (rule 12, §6.2, §7) |
| 4 · Pending-race undefined | Conceded; seven-step state machine + at-most-one-segment invariant (§6.4, tests 24–25) |
| 5 · Live event contract | Conceded on all three: hits logged too; XACK + idempotency now core; `asyncio.Lock` scope narrowed, Redis `inflight:` claim for cross-process coalescing (§9.1, §9.4) |
| 6 · Worker death ≠ LRU at C | Conceded; rule 2 reworded, heartbeat-reclaim makes "full-capacity LRU" literally true (§1, §9.1) |
| 7 · Oracle bound in the gate | Adopted, one sequencing change: it needs the §6.4 machinery, so it is the *first task of Stage 3* — where it doubles as the integration test of the prefetch plumbing against a hand-verifiable policy. §5.5's no-go now waits for it |
| 8 · Belady ≠ suffix optimum | **Conceded — the subtlest catch of all four rounds**, and it made property test 8 flaky as written (a 5-request counterexample exists where LRU strictly beats whole-horizon MIN on the counted suffix). Relabelled; property tests pinned to full counting (§5.3, test 8) |
| Refinements (CRN, V_train, exact match, CLAUDE.md line, two-tier DoD) | All adopted — the CLAUDE.md first line contradicting its own rule 10 is the kind of leftover only fresh eyes find |
| Minor cleanup | All adopted, incl. monotonic ZSET scores (same-millisecond ties make Redis order "recency" lexicographically — a real footgun) |

---

## 1. Ground rules — non-negotiable, enforced at every stage gate

1. **Harness before model.** No model code exists until the five-curve baseline plot exists (end of Stage 2). The plot tells you whether there's headroom worth chasing.
2. **No model on the serving path.** Loop 1 never waits on inference. If the learner dies, the API keeps serving through the ordinary cache path — with heartbeat-reclaim (§9.1) it converges to *full-capacity* LRU; without it, to segmented LRU at (1−f)·C plus stale prefetch leftovers. Claim whichever one you actually built. This is architectural, not aspirational — the demo proves it by killing the worker live.
3. **Time splits only.** Train on earlier time, evaluate on later time. Never random. (Same leakage class that broke the pump-detector labels.)
4. **Headline numbers come from real traces.** Synthetic traces are for debugging and the demo only, and the README says so explicitly.
5. **Matched counted windows.** Every policy in any comparison table is measured over the *identical* set of counted requests, same warmup rule, same cache size. A number without its protocol attached is discarded.
6. **External validation before trusting yourself.** Your LRU must match libCacheSim's LRU on the same trace before any learned result is believed.
7. **Report the harm.** Prefetch precision, wasted fetches, extra backend load, and the realistic-latency number are first-class results, printed in the README next to the headline.
8. **Boring stack.** Python, FastAPI, Redis, matplotlib. No Kafka, no Rust, no gRPC, no microservice split. Any new dependency needs a one-line justification in `decisions.md`.
9. **Stage gates are hard.** Each stage's acceptance checklist must be green (tests passing, artifacts written to `results/`) before the next stage starts. Claude Code is instructed to enforce this (§12).
10. **Everything reproducible.** Every result JSON records the git SHA, trace file, protocol, and parameters that produced it (Appendix B). If you can't regenerate a number with one make target, it doesn't exist.
11. **Name it what it is.** The system is *predictive prefetching over LRU*. The phrase "learned eviction" appears nowhere in code, README, or claims unless the Stage 7 variant (§10 item 3) is implemented **and measured**. Working README title: *Project ORACLE — An Asynchronous Predictive Prefetching Layer for Redis-Backed APIs*.
12. **The final window opens once.** Every knob — τ, f, `min_support`, `alpha0`, model order, `top_k` — is chosen on the P2-dev validation window (§6.2). At the end of Stage 4 one immutable `frozen.json` is written, and Jul 25–31 is opened for **one sealed, predeclared batch** of runs (all baselines, the oracle bound, and both declared model orders — reporting both is fine; *selecting* after looking is not). A rerun is allowed only when a documented correctness bug invalidates the previous one — never because the number disappointed. The v1.2 phrase "once per configuration freeze" was a loophole — serial freezes are serial peeks — and this closes it.

---

## 2. Repository, environment, and conventions

### 2.1 Repository layout (create this skeleton on day one)

```
oracle/
├── README.md                  # claims + headline plot + protocol, kept honest
├── PLAN.md                    # this document
├── CLAUDE.md                  # Claude Code operating instructions (§12.2)
├── decisions.md               # running log: decision, options, why
├── spec/
│   └── oracle-spec-v1.pdf     # the team specification
├── Makefile
├── requirements.txt
├── pyproject.toml             # optional; `pip install -e .` for the src layout
├── data/
│   ├── raw/                   # .gz logs — gitignored
│   └── processed/             # parquet — gitignored
├── src/oracle/
│   ├── __init__.py
│   ├── config.py              # one dataclass: every knob, every default
│   ├── parse_nasa.py          # CLF → parquet
│   ├── sessionize.py          # per-host sessions, bot filter
│   ├── stats.py               # Stage 0 summary + gap histogram
│   ├── vocab.py               # url<->int id mapping
│   ├── policies/
│   │   ├── base.py            # the Policy contract (§4.1)
│   │   ├── lru.py
│   │   ├── lfu.py
│   │   ├── belady.py
│   │   ├── infinite.py
│   │   └── learned.py         # two-segment cache + prefetch policy
│   ├── model/
│   │   ├── markov.py          # 1st + 2nd order, smoothing, backoff, decay
│   │   └── templates.py       # Stage 5: URL templates + candidate IDs
│   ├── harness/
│   │   ├── replay.py          # the replay engine + CLI
│   │   ├── protocols.py       # P1 / P2-dev / P2 / P3 counted-window definitions (§6.2)
│   │   ├── sweep.py           # τ and latency sweeps
│   │   └── export_libcachesim.py
│   └── plots/
│       └── curves.py          # five-curve plot, τ curve, L-sensitivity
├── synth/
│   └── generator.py           # spec §7.4 program-shaped generator
├── service/                   # Stage 6 live system
│   ├── api.py                 # FastAPI hot path
│   ├── backend.py             # fake slow DB (sleep + sqlite/dict)
│   ├── cachemgr.py            # Redis two-segment cache manager
│   ├── worker.py              # learner/prefetcher (Redis Streams consumer)
│   ├── driver.py              # synthetic workload against the live API
│   └── static/
│       ├── index.html         # landing: links to /race and /live
│       ├── race.html          # split-screen replay
│       └── live.html          # live-stack dashboard
├── docker/
│   ├── Dockerfile             # one image, two commands (api / worker)
│   └── docker-compose.yml
├── tests/                     # pytest; Appendix C is the list
└── results/                   # JSON + PNG artifacts, committed
```

### 2.2 Environment (WSL Ubuntu)

```bash
# Python — 3.11+ (3.12 fine; nothing here has wheel problems)
sudo apt update && sudo apt install -y python3.12-venv build-essential cmake libglib2.0-dev
git clone <your-repo> oracle && cd oracle
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .            # so `python -m oracle.*` works from anywhere

# Redis — only needed from Stage 6; run it in Docker, don't apt-install
docker run -d --name oracle-redis -p 6379:6379 redis:7-alpine
```

`requirements.txt` (keep it this small; additions go through `decisions.md`):

```
pandas
pyarrow
numpy
matplotlib
tqdm
pytest
fastapi
uvicorn[standard]
redis
httpx
```

Pin what you actually installed on day one: `pip freeze > requirements.lock`, commit both files. The loose list states intent; the lock states the truth your results were produced under.

### 2.3 Makefile (the public API of the project)

```make
DATA=data/processed
R=results

.PHONY: setup data stats baselines validate-export markov sweep second plots test demo

setup: ; pip install -r requirements.txt && pip install -e .

data:
	python -m oracle.parse_nasa data/raw/NASA_access_log_Jul95.gz $(DATA)/jul95.parquet
	python -m oracle.parse_nasa data/raw/NASA_access_log_Aug95.gz $(DATA)/aug95.parquet
	python -m oracle.sessionize $(DATA)/jul95.parquet $(DATA)/jul95.sessions.parquet
	python -m oracle.sessionize $(DATA)/aug95.parquet $(DATA)/aug95.sessions.parquet

stats: ; python -m oracle.stats $(DATA)/jul95.sessions.parquet --out $(R)

baselines:
	python -m oracle.harness.replay --trace $(DATA)/jul95.sessions.parquet \
	  --protocol P1 --policies lru,lfu,belady,infinite \
	  --sizes 100,500,1000,5000,10000 --out $(R)

validate-export:
	python -m oracle.harness.export_libcachesim $(DATA)/jul95.sessions.parquet $(R)/jul95.libcs.csv

markov:
	python -m oracle.harness.replay --trace $(DATA)/jul95.sessions.parquet \
	  --protocol P2dev --policies lru,lfu,belady,infinite,oracle1 \
	  --sizes 100,500,1000,5000,10000 --tau 0.4 --latency-ms 0,200 --out $(R)

sweep: ; python -m oracle.harness.sweep --trace $(DATA)/jul95.sessions.parquet --out $(R)

final:
	python -m oracle.harness.replay --trace $(DATA)/jul95.sessions.parquet \
	  --protocol P2 --policies lru,lfu,belady,infinite,nextoracle,oracle1,oracle2 \
	  --sizes 100,500,1000,5000,10000 --frozen-config $(R)/frozen.json --out $(R)

plots: ; python -m oracle.plots.curves --results $(R) --out $(R)

test:  ; pytest -q

demo:  ; uvicorn service.api:app --host 0.0.0.0 --port 8000
```

### 2.4 Configuration — one source of truth

`src/oracle/config.py` holds a single frozen dataclass with every knob and its default. Nothing else hardcodes a number.

```python
@dataclass(frozen=True)
class Cfg:
    session_gap_s: int = 1800        # 30-min sessionization threshold
    warmup_frac: float = 0.20        # protocol P1
    alpha0: float = 0.0              # concentration prior; 0 = pure empirical count/total (§6.3)
    min_support: int = 5             # row count needed before predicting
    tau: float = 0.4                 # prefetch probability threshold
    top_k: int = 1                   # predictions considered per event
    prefetch_frac: float = 0.20      # prefetch segment share of capacity
    latency_ms: int = 200            # realistic prefetch completion latency
    decay: float = 0.99              # per-day count decay (online mode)
    bot_max_session_len: int = 500   # sessions longer than this get inspected/dropped
    hit_ms: float = 2.0              # simulated service time on a cache hit
    miss_ms_median: float = 200.0    # simulated backend latency: lognormal median
    miss_ms_sigma: float = 0.4       # lognormal sigma (spread makes percentiles meaningful)
    seed: int = 7                    # RNG seed for the latency draws
    load_budget: float = 0.10        # max extra backend fetches vs LRU when picking τ* (validation)
```

Every results JSON embeds the full Cfg used (Appendix B), so any figure can be traced to its exact parameters.

---

## 3. Stage 0 — Data (½–1 day)

**Goal:** two clean, sessionized parquet files (July, August 1995) plus a printed summary that tells you whether the trace has exploitable structure.

### 3.1 Get NASA-HTTP — exactly where and how

The canonical source is the Internet Traffic Archive page **`ita.ee.lbl.gov/html/contrib/NASA-HTTP.html`**, which lists two files:

- `NASA_access_log_Jul95.gz` — 01/Jul – 31/Jul 1995, ~20 MB gzipped, ~1.89 M lines
- `NASA_access_log_Aug95.gz` — 04/Aug – 31/Aug 1995, ~16 MB gzipped, ~1.57 M lines

The ITA FTP links are ancient and frequently down. **Do not fight the FTP server.** Mirrors are plentiful:

1. **Kaggle** — search “NASA access log 1995” / “NASA web server logs”; several mirrors host both monthly files. Download via browser or `kaggle datasets download` if you have the CLI configured.
2. **GitHub** — code-search the exact filename `NASA_access_log_Jul95.gz`; multiple repos vendor it (often under `data/` in caching or log-analysis projects). `wget` the raw file URL.
3. If a mirror only has the uncompressed `.log`, that's fine — adjust the reader to open plain text.

**Verify before parsing** (wrong/truncated mirrors are common):

```bash
zcat data/raw/NASA_access_log_Jul95.gz | wc -l        # expect ≈ 1,891,715
zcat data/raw/NASA_access_log_Jul95.gz | head -1
# expected first line:
# 199.72.81.55 - - [01/Jul/1995:00:00:01 -0400] "GET /history/apollo/ HTTP/1.0" 200 6245
zcat data/raw/NASA_access_log_Aug95.gz | wc -l        # expect ≈ 1.57M
```

If counts are wildly off, find another mirror. Known dataset quirk: the server was down at the start of August (Hurricane Erin), so the August file starts on the 4th — **don't hardcode calendar assumptions; read min/max timestamps from the data** and set the split dates in §6.2 from what you actually see.

### 3.2 Parse — `oracle/parse_nasa.py`

Format is Common Log Format, one request per line. Parse with a regex; the file has a small number of corrupt lines (bad bytes, malformed request fields) — count and skip them, never crash.

```python
import re, gzip, datetime as dt
LOG_RE = re.compile(
    r'^(?P<host>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) (?P<size>\S+)'
)

def parse_line(line):
    m = LOG_RE.match(line)
    if not m: return None
    parts = m['req'].split()
    if len(parts) < 2: return None            # e.g. garbled "GET" with no URL
    method, url = parts[0], parts[1]
    ts = dt.datetime.strptime(m['ts'], "%d/%b/%Y:%H:%M:%S %z")
    size = None if m['size'] == '-' else int(m['size'])   # CLF writes '-' for absent sizes
    return m['host'], method, url, int(m['status']), size, int(ts.timestamp())

# caller: for seq, line in enumerate(fh): row = (seq, *parse_line(line))
# `seq` — the raw-log row index — is born HERE and preserved through every later
# transformation; §3.3's global (ts, seq) sort depends on it existing.
```

Rules, pinned:

- Open with `encoding="latin-1"` (a few lines contain non-UTF-8 bytes).
- **Keep:** `method == "GET"` and `status == 200`. Drop everything else. (Optional later variant: also keep `304` — a 304 is evidence the client *asked* for the object, i.e. it's still a reference for cache purposes. Note it in `decisions.md`, run it as a sensitivity check in Stage 7 if curious, but the headline uses the 200-only rule so it matches the spec.)
- **URL normalization rule (pin it, write it down):** strip any `#fragment`; otherwise keep the path+query byte-for-byte. Do not lowercase paths (URLs are case-sensitive), do not collapse slashes. The key is the exact string.
- Print at the end: total lines, parsed, dropped-malformed, dropped-by-filter. Malformed should be well under 0.1% — if it isn't, your regex is wrong, not the file.
- Output parquet columns: `seq:int64, ts:int64, host, method, url, status:int16, size:int32 (nullable)`. `seq` is the raw-log row index (see snippet); `method`/`status` stay so the keep-304 variant re-filters from this file instead of re-parsing; `size` costs nothing now and enables the Stage 7 byte-capacity variant. Parquet, not CSV — 10× smaller, 10× faster to reload, and it has real nullable types for the `'-'` sizes.

### 3.3 Sessionize + bot filter — `oracle/sessionize.py`

Implements spec §7.3 exactly:

1. Stable-sort by `(host, ts, original_row_index)` — the third key keeps same-second order deterministic.
2. Within each host, split into sessions wherever the gap to the previous request exceeds `cfg.session_gap_s` (1800 s).
3. Assign `session_id` (running int), `pos_in_session`.
4. **Keep sessions of length 1 in the replay workload.** A singleton is a real request that occupies capacity and can hit or miss; dropping it conditions the whole evaluation on multi-request users, inflating both baseline locality and apparent model coverage — a quieter cousin of the ordering bug. Length-1 sessions are excluded only at *transition-extraction* time (`if session_length >= 2: extract_pairs(...)`); at replay the predictor simply has no context for them and abstains. Test 23 pins this.
5. **Bot heuristics** — apply, and *print how much each rule removed*:
   - any host that ever requests `/robots.txt` → drop the host entirely;
   - sessions longer than `cfg.bot_max_session_len` → dump the top 5 offenders to console, eyeball them once, then drop;
   - hosts with ≥ 100 requests whose inter-request gaps have a coefficient of variation < 0.1 (near-constant cadence = scripted client) → drop. The rule is exact on purpose, so the filter is reproducible rather than vibes.
   Keep the filter light. If more than ~10% of requests are being dropped, your heuristics are too aggressive — loosen and log. And Stage 7 runs the headline comparison once on the *unfiltered* trace as a sensitivity check: proof the win wasn't manufactured by filter choices.
6. Output: `sessions.parquet` with `ts, seq, host, url, session_id, pos_in_session` — `seq` is the original raw-log row index, preserved forever — **sorted globally by `(ts, seq)`, not by session.** This matters more than it looks (it was the biggest bug in v1.1): a shared server cache sees one interleaved chronological stream; replaying whole sessions back-to-back changes eviction competition and inter-request timing, inflates apparent locality, and makes timestamps run backwards between sessions, breaking `on_tick` and the latency model. Sessions exist as a *column* — for training-pair extraction and per-session model context — never as the replay order.

One honest wrinkle to note in `decisions.md` (don't fix it yet): 1995 pages pull embedded images, so a page view produces a burst of same-second requests (`.html` then five `.gif`s). This inflates zero-gap transitions. It's real traffic and stays in the headline run; an `--html-only` variant (keep `.html`/`/`-ending URLs only) is a legitimate Stage 7 sensitivity experiment showing the sequence structure more cleanly.

### 3.4 Summary stats — `oracle/stats.py`

Must print (and save to `results/stage0_summary.json` + PNGs):

- total requests, unique URLs, unique hosts;
- number of sessions; session length p50 / p90 / max; share of singleton sessions and of singleton *requests* (they stay in the replay — §3.3);
- **inter-request gap distribution within sessions**: p50/p90/p99, and — the number that decides whether prefetching can work at all — the fraction of gaps ≥ 1 s, ≥ 2 s, ≥ 5 s (a prefetch taking 200 ms can only beat gaps ≥ ~1 s at this trace's 1 s resolution);
- top-20 URLs by frequency (scan it for bot leftovers);
- histogram PNGs: session lengths (log-y), gaps (log-x).

### Acceptance — Stage 0

- [ ] Both raw files verified by line count and first line.
- [ ] `make data` runs end-to-end and is idempotent.
- [ ] `make stats` prints every item in §3.4; PNGs in `results/`.
- [ ] Malformed-line rate < 0.1%; bot-drop rate printed and < ~10%.
- [ ] `decisions.md` records: URL normalization rule, 200-only rule, bot heuristics, embedded-image note.

---

## 4. Stage 1 — Harness + LRU (1 day)

**Goal:** a replay engine and a provably-correct LRU. Deliberately boring; everything else plugs into this.

### 4.1 The Policy contract — `policies/base.py` (fix this on day one, never change it)

```python
class Policy:
    name: str = "base"
    def __init__(self, capacity: int): ...
    def get(self, key: int) -> bool:
        """True = hit. MUST also update recency/frequency state on hit."""
    def put(self, key: int) -> None:
        """Insert after a demand miss (evicting if full)."""
    def observe(self, ts: int, session_id: int, key: int) -> None:
        """Called for every request AFTER it is served. Hook for the learner.
        session_id is REQUIRED: replay order is global-chronological (§3.3),
        so Markov context must be tracked per session or transitions smear
        across users. Baselines: no-op. Learned policy: update per-session
        context, update model (online mode), predict, maybe prefetch."""
    def on_tick(self, ts: int) -> None:
        """Called when simulated time advances. Learned policy completes
        in-flight prefetches whose finish time <= ts. Baselines: no-op."""
    def stats(self) -> dict:
        """hits/misses are the harness's job; return policy-internal counters:
        prefetch_issued, prefetch_hits, prefetch_evicted_unused, coverage_events..."""
```

Keys are **int ids**, not strings — build the vocab once in `oracle/vocab.py` (`url -> int`, saved as parquet). This makes the replay ~5× faster and makes the libCacheSim export trivial.

The learned policy keeps a per-session context store — `dict[session_id -> (prev2, prev1, last_ts)]` — purged when idle longer than `cfg.session_gap_s` (mirroring the sessionizer's 30-min rule) so it can't grow unboundedly. Do **not** allocate an event object per request in the hot loop: columns in, plain args through. (The reviewer's frozen `RequestEvent` dataclass is fine at the edges; the replay loop itself stays allocation-free — 1.7M object constructions per run is real money in CPython.)

### 4.2 LRU — `policies/lru.py`

`collections.OrderedDict`. `get`: hit → `move_to_end(key)`, return True. `put`: if present, `move_to_end`; else if `len == capacity`, `popitem(last=False)`; insert. All O(1). ~25 lines. Resist any urge to be clever.

### 4.3 Replay engine — `harness/replay.py`

The core loop (protocol details in §6.2; for Stage 1 use **P1**: warmup = first 20% of requests populate but don't count):

```python
def replay(trace, policy, counted_mask):        # trace: arrays ts[], key[]
    hits = misses = 0
    for i in range(len(trace)):
        policy.on_tick(trace.ts[i])             # advance sim time first
        if policy.get(trace.key[i]):
            if counted_mask[i]: hits += 1
        else:
            if counted_mask[i]: misses += 1
            policy.put(trace.key[i])
        policy.observe(trace.ts[i], trace.sid[i], trace.key[i])
    return hits, misses
```

Pinned semantics — these exact orderings are what libCacheSim must agree with:

- `on_tick` before `get` (a prefetch completing at t is usable by a request at t only if it finished strictly earlier — see §6.4; at 1 s resolution, "completes at t" counts as *not yet available* for a request at t).
- A demand miss always inserts (`put`) — there is no bypass/admission policy in the baselines.
- `observe` runs after serve, for every request, counted or not — the learner sees warmup traffic too; only *counting* is gated.
- Replay input must be non-decreasing in `(ts, seq)` — assert it at load and abort on violation (App. C test 21); a backwards timestamp is a data bug, not something to sort away silently.
- Iterate NumPy arrays / plain lists, never pandas rows. Target: full July (~1.7 M kept requests) through LRU in **< 30 s** on your laptop. If it's minutes, you're touching pandas per-row.

CLI (`python -m oracle.harness.replay`): `--trace --protocol P1|P2 --policies a,b,c --sizes 100,500,... --tau --latency-ms --online --out results/`. Every run writes one JSON per (policy, size, protocol, params) per Appendix B, plus prints a table.

### 4.4 Tests to write *now* (subset of Appendix C)

1. **The cyclic pathology (from spec §1.4):** trace `ABCD×1000`, capacity 3, no warmup → LRU hit rate exactly **0.0**. This single test kills most off-by-one recency bugs.
2. Capacity never exceeded (assert inside a debug mode).
3. Hand-computed 10-request trace, capacity 2 → exact hit/miss sequence matches a worked-by-hand table committed as a comment.
4. Warmup: same trace with warmup 0 vs 0.2 → identical cache end-state, different counts.
5. Determinism: two runs, identical JSON (modulo timestamps).

### Acceptance — Stage 1

- [ ] `make baselines` (LRU only at this point) prints hit rates at sizes 100 / 500 / 1k / 5k / 10k and writes JSONs.
- [ ] All §4.4 tests green.
- [ ] Full-July LRU replay < 30 s.

---

## 5. Stage 2 — Baselines + external validation (1 day)

**Goal:** LFU, Belady, infinite-cache implemented; your LRU cross-checked against libCacheSim; the five-curve headroom plot that decides whether the project proceeds on this trace.

### 5.1 LFU — pin the definition before implementing

“LFU” is ambiguous; ambiguity here is how baselines get accidentally crippled. Pin this variant and write it in `decisions.md`:

- **In-cache LFU:** frequency counter starts at 1 on insert, incremented on each hit, **destroyed on eviction** (no ghost history). Evict the minimum-frequency entry; break ties by least-recently-used.
- Implementation: the classic O(1) structure (dict key→node + dict freq→ordered bucket) is nice; a heap with lazy invalidation is perfectly fine at this scale. Either way, the tie-break rule must be deterministic.

### 5.2 Infinite demand-loaded cache — `policies/infinite.py`

A set. Hit iff the key has been *demanded* before within the replayed range. Ten lines, and it anchors the top of the demand-fetch curves: hit rate = 1 − compulsory-miss rate.

Label it precisely — **it is a reference line, not a ceiling for the prefetcher.** Two ways ours can legitimately exceed it: (1) under P2 the replay starts at the pre-warm slice, but the model was trained on earlier traffic — so a key's *first demand inside the replayed window* can already be cached because its predecessor triggered a prefetch; (2) with Stage 5 candidate harvesting, prefetch keys come from ids inside response bodies that may never have been individually demanded at all, beating even a full-history demand cache on true first references. Use three labels everywhere (plots, README, talk track): **Belady — demand-fetch optimum**, **infinite demand-loaded cache — reference**, and, only if you compute one, **oracle-prefetch bound**. Exceeding the first two with prefetching on is the interesting result, not an error. And the **oracle-prefetch bound** is cheap enough to actually build (~20 lines in the harness): a prefetcher that always predicts the session's true next request, subject to the *same* latency model, segment sizes, and backend-load budget as ours. It is the relevant ceiling — ours-vs-oracle isolates model quality, oracle-vs-infinite isolates structural and timing limits. **Required, and built as the first task of Stage 3 — before any Markov code.** Two reasons: it is the gate of last resort in §5.5, and it integration-tests the entire §6.4 prefetch machinery (pending set, latency, segments, promotion) against a policy whose correct behavior you can verify by hand, before a learned model is around to blur the blame.

### 5.3 Belady (MIN) — `policies/belady.py`

Two-pass, standard construction:

1. **Precompute next-use:** iterate the trace *backwards* with `last_seen: dict[key,int]`; `next_use[i] = last_seen.get(key[i], INF)`; then `last_seen[key[i]] = i`. O(n).
2. **Simulate:** cache maps key → its current next-use index. On access to key at position i, update its stored next-use to `next_use[i]`. On a miss with a full cache, evict the cached key with the **largest** next-use (evict never-used-again, i.e. INF, first). Maintain a max-heap of `(next_use, key)` with lazy invalidation: pop until the top matches the key's current stored value. O(n log n); expect this to be your slowest policy — a couple of minutes on full July is fine.
3. Belady needs the whole replayed trace up front (it reads the future) — the harness passes it the full key array at construction. That's the point of the cheat.

Validate on paper first: 3–4 handcrafted traces where you compute OPT by hand, committed as tests. Also the property test: **Belady ≥ LRU and ≥ LFU on every (trace, size) pair — under full-sequence counting.** One violation = simulator bug, stop everything.

The counting qualifier is load-bearing. Whole-horizon MIN minimises misses over the *entire sequence it processes*; it is **not** necessarily optimal for a counted suffix. Near the prewarm boundary, MIN can preserve an uncounted prewarm hit at the cost of a counted one — and a 5-request, capacity-2 counterexample exists where plain LRU strictly beats whole-horizon MIN on the suffix. Consequences, pinned: (a) never label the P2 Belady number "counted-window optimum" — the label is **"Belady demand-fetch reference (whole-horizon MIN)"**; (b) the ≥-LRU/LFU property tests run with no warmup and full-trace counting, where the guarantee actually holds — under suffix counting they would be flaky by construction.

### 5.4 libCacheSim cross-check — the credibility purchase

Build:

```bash
git clone https://github.com/1a1a11a/libCacheSim && cd libCacheSim
bash scripts/install_dependency.sh      # cmake, glib, zstd on Ubuntu/WSL
mkdir _build && cd _build && cmake .. && make -j$(nproc)   # → bin/cachesim
```

Export your trace (`harness/export_libcachesim.py`): CSV with `ts,int_key` (int keys from vocab), one row per kept request, in replay order. Then run their LRU and yours **with identical semantics**:

- Run *both* with warmup = 0 and full-trace counting — remove warmup as a variable; you're validating the eviction machinery, not the protocol.
- Uniform object size: pass libCacheSim its ignore-object-size option so cache size means "N objects", matching yours.
- Exact CLI flag names for CSV column mapping (`time-col`, `obj-id-col`, delimiter) are in the libCacheSim README — read it rather than guessing; budget 30 minutes for format fiddling.

**Match criterion: exact.** With identical replay order, zero warmup, object-count capacity, and the same admit-on-miss behavior, there is no legitimate source of ±3 — a small unexplained LRU discrepancy is an unexplained bug, and "close enough" here defeats the entire purpose of the check. The only acceptable non-match is a *documented semantic difference* (e.g., their LFU variant vs your pinned one), written into `decisions.md`. If they differ:

- off-by-one in warmup/first-request handling;
- your `get` not updating recency on hit;
- duplicate same-key same-timestamp rows ordered differently — your stable sort (§3.3) exists precisely for this;
- their default admits objects on miss the same way you do — confirm no admission policy is enabled.

Do the same for LFU (expect approximate match only if their LFU variant matches your pinned definition — if not, note the variant difference in `decisions.md` rather than chasing ghosts). For **Belady**, libCacheSim's implementation typically wants an oracle-annotated trace produced by their `traceConv` tool; either do that conversion, or rely on your hand-verified tests from §5.3 — both are defensible, log the choice.

### 5.5 The headroom plot and the go/no-go gate

`plots/curves.py`: hit rate (y) vs cache size (x, log scale), curves for LRU, LFU, Belady, infinite. Protocol P1, July.

**Gate (spec §11), now two-step.** Step 1, here: at the sizes you care about (≤ 5k), check Belady − LRU and infinite − LRU. If they're comfortable (≥ ~5 pp), proceed. If both are thin, do **not** kill the project yet — these are *eviction*-headroom gates, and they can reject a workload where prefetching would shine (highly predictable first references miss under every demand-fetch policy, yet a trained prefetcher avoids them). Step 2, the verdict: the **oracle-prefetch bound** (§5.2), built as the first task of Stage 3, under the same latency, capacity, segment, and backend-load constraints as ours. If oracle − LRU is *also* thin, now switch workloads (`--html-only`, another month, ClarkNet/EPA). Demand gates are the cheap early warning; the oracle gate is the decision.

### Acceptance — Stage 2

- [ ] LFU, Belady, infinite implemented; Belady property test green on all traces/sizes.
- [ ] LRU hit counts match libCacheSim at all five sizes (evidence: `results/libcachesim_crosscheck.md` with both numbers side by side).
- [ ] Four-curve plot in `results/`; headroom numbers written into README.
- [ ] Go/no-go decision recorded in `decisions.md`.

---

## 6. Stage 3 — First-order Markov + prefetching (2–3 days)

**Goal:** the learned policy exists, measured under an honest protocol, with pollution and timing measured. You may not beat LRU on the first attempt — the acceptance criteria below are about producing the *right artifacts*, not a predetermined win.

### 6.1 Vocab + training artifact

`oracle/vocab.py` maps every URL in July+August to a stable int id (build once from the union, save `vocab.parquet`) — but split the roles: the **encoder** (url → int) may see all of July+August, since it's deterministic bookkeeping; any probability that touches V — the α₀ prior — uses **V_train**, counted from the training slice only, with a reserved OOV id for keys unseen at train time. Letting August inflate V would leak future vocabulary size into a hyperparameter. The model artifact is `results/markov1.pkl`: `counts: dict[int, dict[int,int]]` + `row_totals: dict[int,int]` + the Cfg it was built with.

### 6.2 Protocols — pinned dates, matched windows (the paragraph Claude Code must never violate)

- **P1 (single-trace, model-free):** warmup = first 20% of requests (populate, don't count); count the rest. Used in Stages 1–2.
- **P2-dev (validation — where *all* tuning happens):** train = Jul 1–14; pre-warm = Jul 15–16; validation-count = Jul 17–21. Every knob is chosen here — τ, f, `min_support`, `alpha0`, model order, `top_k` — and every sweep in §6.6 runs here, its figures labelled *validation*.
- **P2 (final — the headline protocol, run once per configuration freeze):**
  - **Train slice:** July 1 00:00 → July 21 23:59 — build the transition table here, offline.
  - **Pre-warm slice:** July 22 → July 24 — replayed through every policy, *uncounted*, so no policy starts cold.
  - **Counted slice:** July 25 → July 31 (end of file) — the only requests that produce numbers, and they are opened **once**, at the end of Stage 4, for one sealed, predeclared batch: retrain on Jul 1–21 with the frozen knobs, run every declared policy (both model orders included), report. Reruns only for documented correctness bugs — never for disappointing numbers. Going back to re-tune after seeing this window is test-set leakage — the same disease as tuning τ on it directly, in a nicer suit.
  - **Every** policy in the headline table (LRU, LFU, Belady, infinite, ours) is rerun under P2 with the identical counted mask. Belady's future-lookup spans the whole replayed range (Jul 22–31).
  - Adjust exact boundaries after reading real min/max timestamps in Stage 0; keep the ~70/10/20 shape.
- **P3 (drift, Stage 4):** train = all July; pre-warm = first 2 days present in August; count the rest of August. Run with the model frozen vs online-updating.
- Sessions that straddle a boundary: transitions are extracted per session from *train-slice requests only*; a session crossing into the counted slice contributes its train-side pairs to training and its counted-side requests to evaluation. Simple, time-respecting, no leakage.

### 6.3 The model — `model/markov.py`

- Build: for each session in the train slice, for each adjacent pair `(a → b)`, `counts[a][b] += 1`. No pairs across session boundaries, ever.
- Probability: **empirical**, `p(b|a) = counts[a][b] / total[a]`, gated by `min_support`. The spec's full-vocabulary Laplace form `(count+α)/(total+α·V)` is quietly fatal for thresholded prefetching, and v1 shipped it unchecked: with V ≈ 20k and α = 0.5, a row with 100 observations and an 80%-dominant successor scores p ≈ 80.5/10,100 ≈ 0.008 — and in general no row with support < V/3 can *ever* cross τ = 0.4, however deterministic the transition. The prefetcher would sit silently dead at its own defaults. Smoothing exists to give unseen events non-zero mass; we never prefetch unseen transitions, and `min_support` already handles thin rows. If you want shrinkage, use a concentration prior `p = (count + α₀/V) / (total + α₀)` with `α₀ = cfg.alpha0 ∈ [1, 5]` as a P2-dev ablation — never α·V in the denominator.
- **Eligibility to predict:** `total[a] ≥ cfg.min_support` (default 5). Below that, the model abstains and the cache behaves as pure LRU for that step — this *is* the cold-start fallback from spec §11. Track `coverage = eligible events / counted events` and report it.
- Prediction: argmax over the row (top-k with k = cfg.top_k = 1 to start).
- Decay (`counts *= cfg.decay` per simulated day, prune < 0.01) matters only in online mode (§7) — the offline P2 table is frozen.

### 6.4 Prefetch mechanics in simulation — the crux; get this exactly right

The learned policy (`policies/learned.py`) implements the whole client-worker dance inside `observe`/`on_tick`:

- **On `observe(ts, key)`:** if predictor eligible → `(pred, p) = top1(key)`. Schedule a prefetch iff **all** of: `p ≥ τ`; `pred` not in demand segment, not in prefetch segment, not already pending. Pending entry: `(pred, ready_at = ts + latency_ms/1000)`. Count `prefetch_issued`.
- **On `on_tick(ts)`:** move every pending prefetch with `ready_at < ts` (strict) into the **prefetch segment**. At NASA's 1 s resolution this means: with `latency_ms = 200`, a prediction made at t serves a request at t+1; a same-second follow-up (gap 0) is unservable — which is honest, and is why §3.4 measured the gap distribution.
- **Idealised mode:** `latency_ms = 0` inserts immediately in `observe`. Report **both** numbers, always, side by side (spec §6.3).
- **NASA-specific honesty:** 1 s truncation means a recorded 0 s gap may truly be 800 ms (servable at L = 200 ms) and a recorded 1 s gap may truly be 50 ms (not servable). So on NASA the realistic mode is a **bounded sensitivity scenario**, not a measurement: report a pessimistic rule (servable iff recorded gap ≥ 2 s) and the central rule (≥ 1 s, the default above) as a bracket. The precise number comes from millisecond data (§8.1).
- **The pending-race state machine — pin it; this is where simulators silently double-count.** Demand for key k arriving before its prefetch's `ready_at`: (1) it is a miss; (2) `pending_missed += 1`; (3) the demand fetch proceeds and inserts into the **demand** segment; (4) the pending prefetch is marked obsolete — its backend cost stays counted (`prefetch_issued` was already incremented), and when it completes its result is **discarded**, never inserted. Invariant, enforced by assertion: a key occupies at most one segment at any time (test 25). This models a system *without* cross-path coalescing; the coalesced variant — demand joins the in-flight prefetch, pays only the residual latency, one backend fetch, classified separately from a hit — is the live system's §9.4 upgrade, not the offline core. Tests 24–25 pin both the accounting and the invariant.
- **Common random numbers:** pre-draw `backend_latency[i]` once per request index and share it across every policy — otherwise one policy can look faster because it rolled luckier misses. This also tightens §6.7's paired Δ-latency blocks. The fixed prefetch-completion L stays a *labelled sensitivity control*; a variant drawing prefetch completions from the same distribution is one flag away.
- **Right-censoring at the window edge:** prefetches issued in the last `max(L, 30 s)` of the counted window can be pending or not-yet-used through no fault of the model — exclude them from the precision denominator (or report them as censored) rather than booking them as waste.
- **In-flight cap, offline too:** the ms-trace simulator caps concurrent prefetches (mirror the live semaphore, e.g. 8) with a start queue — assuming every issued prefetch starts instantly overestimates timely completion under bursts. Second-order on 1 s NASA data; not second-order on the ms trace.
- **A hit on a prefetched entry** (demand `get` finds the key in the prefetch segment): count `prefetch_hit`, **promote** the entry into the demand segment (normal LRU insert there, which may evict).
- **Backend-load accounting:** `total_backend_fetches = demand_misses + prefetch_issued`. Report `extra_backend_load = ours_fetches / lru_misses − 1` — the cost side of the ledger.
- **Demand-latency distribution (headline metric #2):** a hit costs `cfg.hit_ms`; a miss draws backend latency from a seeded lognormal (median `cfg.miss_ms_median`, σ `cfg.miss_ms_sigma`). Report mean / p50 / p95 per policy. Why a distribution rather than two constants: with fixed {2 ms, 200 ms}, p95 is a degenerate step function of hit rate (it equals 200 ms whenever hit rate < 95%) — percentiles only mean something over spread, so simulate spread.
- **Timely-prefetch rate:** among prefetches whose key was subsequently demanded, the share that completed in time = `prefetch_hit / (prefetch_hit + pending_missed)`. The idealised−realistic hit-rate gap is this number's shadow; report both.
- **Efficiency:** `(lru_total_latency − ours_total_latency) / (ours_backend_fetches − lru_backend_fetches)` — user-milliseconds bought per extra backend fetch. If the denominator is ≤ 0 (ours fetched *less* overall), report "strictly dominant" instead. One number, extremely interviewable.
- **Prefetch occupancy:** time-averaged fraction of total capacity holding not-yet-hit prefetched entries — "capacity consumed by speculation", measured.

### 6.5 Two-segment cache (spec §5.3) — pollution containment

Capacity C splits into demand segment (LRU, cap `⌈(1−f)·C⌉`) and prefetch segment (FIFO, cap `⌊f·C⌋`, f = cfg.prefetch_frac = 0.2). Prefetch inserts go only to the prefetch segment; when it's full, evict its oldest and count `prefetch_evicted_unused` (that's a wasted prefetch). Demand misses insert only to the demand segment. What this buys, stated precisely: the segments **bound pollution** — a wrong prefetch can only ever displace other prefetches, never a demand-loaded entry, which stays put until it ages out of its own LRU. What it does **not** buy is parity with full-capacity LRU: the reserved `f·C` is an opportunity cost, and a *useless* model degrades you to roughly LRU at `(1−f)·C` — strictly worse than LRU at `C`. Never claim "no worse than LRU"; claim "pollution-bounded", show the f-sweep, and let f = 0 be the control.

- **Prefetch precision** = `prefetch_hit / prefetch_issued`. Below ~30% → you're polluting; raise τ (spec §5.2). Print it on every run.
- Fair-comparison note for `decisions.md`: baselines use the full C as one LRU; ours effectively runs demand-LRU at 0.8 C plus a predicted set at 0.2 C. That handicap is part of the design being tested — if ours still wins, the win is real. The f-sweep in §6.6 quantifies this handicap directly.

### 6.6 The τ sweep and the sanity gate

- `harness/sweep.py`: **on P2-dev**, fix size = 5000, sweep τ ∈ {0.1 … 0.9 step 0.1}, both latency modes → three figures: (i) hit rate vs τ (expect an interior optimum: too low = pollution, too high = no prefetching); (ii) precision vs τ; (iii) the **Pareto view** — extra backend fetches (x) against hit-rate / latency gain (y), one point per τ. Selection rule, applied on validation only: **τ\* = argmax hit-rate subject to `extra_backend_load ≤ cfg.load_budget`** (default 10%). The Pareto plot is the pre-loaded answer to "didn't you just buy hits with backend traffic?"
- **Prefetch-fraction sweep:** at size 5000 and the chosen τ, sweep f ∈ {0, 0.05, 0.10, 0.20, 0.30}. f = 0 means prefetches insert straight into the demand LRU — the unsegmented, pollution-exposed ablation. Together with plain LRU this gives the three-way ablation the review asks for: LRU vs LRU+unsegmented-prefetch vs full segmented policy. Runs on P2-dev, like every tuning sweep.
- **Plumbing gate (upgraded from the spec's sanity check):** with prefetching disabled *and* f = 0, the "learned" policy has no mechanism left except LRU — so it must reproduce plain LRU's hit/miss sequence **exactly, request for request**. Equality is a far sharper check than an inequality. The Belady bound stays as the umbrella property test: *any* demand-fetch configuration (this one, and Stage 7's learned eviction if built) scores ≤ Belady at every size. Violations of either are simulator bugs, full stop. Automate both as tests.
- Latency sensitivity: at the best τ, sweep `latency_ms ∈ {0, 100, 200, 500, 1000}` → one more plot; the 0→200 drop is your honesty headline.

### 6.7 Statistics — earning the phrase "statistically meaningful"

With ~400k counted requests, *everything* looks significant if you pretend requests are independent — they aren't: sessions are internally correlated and cache state couples the whole stream. The class-level procedure that is honest without being heavy:

1. Run each policy once over the counted window (all policies are deterministic; there is no seed variance to average — variability comes from the workload).
2. Compute **paired, per-block differences**: block = one calendar day of the counted window (7 blocks; also compute the per-session variant as a finer view). For each block b: Δ_b = metric(ours, b) − metric(LRU, b) on the identical requests, for hit rate and mean demand latency.
3. **Block bootstrap:** resample the day-blocks with replacement 10,000×, recompute the mean paired Δ each time, report the 2.5th/97.5th percentiles as the 95% CI.
4. State the caveat in the README: cache state couples blocks, so this captures workload variability, not full system re-randomisation — the standard pragmatic choice for trace studies. Day-blocks are the primary CI (fewer, less coupled than sessions).
5. Headline format: "Δhit-rate = +X pp (95% CI [a, b])". A CI that straddles zero gets reported exactly as such — that *is* a result (see §15 item 1's reframed objective).

### Acceptance — Stage 3

- [ ] Oracle-prefetch bound implemented **first** (§5.2) — it integration-tests the prefetch machinery and settles §5.5's deferred go/no-go before any learned code exists.
- [ ] First-order knobs tuned on P2-dev (τ*, f*, `min_support`, `alpha0`, `top_k`) with the sweep plots — **P2 final untouched**: the freeze and the sealed batch belong to the end of Stage 4, after the model-order comparison. Stage 3 produces validation numbers only.
- [ ] Validation τ-sweep, precision, and Pareto plots; τ* chosen under the load budget.
- [ ] Coverage %, prefetch precision, extra-backend-load % printed in every run summary.
- [ ] Belady sanity gate automated and green.
- [ ] If not beating LRU yet: a written paragraph in `decisions.md` diagnosing why (low coverage? low precision? gaps too short?) — that paragraph is Stage 4's roadmap, and is itself a deliverable.
- [ ] f-sweep plot including the f = 0 unsegmented ablation; chosen f recorded in `decisions.md`.
- [ ] 95% block-bootstrap CI on Δhit-rate and Δmean-latency vs LRU reported per §6.7.

---

## 7. Stage 4 — Second-order context, online updating, drift (1–2 days)

**Goal:** the usual place real gains appear (spec §4.3), plus the "weeks not minutes" story.

### 7.1 Second-order with backoff — `model/markov.py` extension

- Context = `(prev2, prev1)` within a session; separate table `counts2[(a,b)][c]`.
- **Backoff rule (pin it):** if `total2[(a,b)] ≥ min_support` use the bigram row; elif `total1[b] ≥ min_support` fall back to first-order; else abstain. (Optional refinement: linear interpolation `λ·p2 + (1−λ)·p1`, λ ≈ 0.7 — try only if plain backoff already helps.)
- Memory: pairs are bounded by observed transitions, not V². Keys are int tuples; if RAM complains, pack as `a*V + b`. Measure and print table sizes.
- Report the same metric set as Stage 3, plus **backoff share**: what fraction of eligible predictions came from the bigram vs unigram vs abstain.

### 7.2 Online mode — legal, realistic, and it sets up the drift result

`--online` flag: during replay, `observe` also does `counts[prev][cur] += 1` (and decays daily). This uses only the past at every step — **no leakage** — and is exactly how the deployed worker behaves. Expect it to help most on P3.

### 7.3 The drift experiment (protocol P3)

Four runs, one chart: {frozen, online} × {first-order, second-order} on August, trained on July. The finding you're fishing for (spec §2, objective 4): frozen degrades across weeks; online tracks. Even a null result ("NASA '95 traffic barely drifts month-to-month") is a real finding — report whatever the data says.

### Acceptance — Stage 4

- [ ] Second-order beats first-order on **P2-dev**, **or** a written explanation of why not (e.g., bigram coverage too low on this trace) — spec Phase 4's exit criterion, moved off the final window.
- [ ] Backoff-share numbers reported.
- [ ] Drift chart (P3, four runs) in `results/` + two-sentence interpretation in README.
- [ ] Model order and every remaining knob selected on P2-dev; **one immutable `results/frozen.json`** written (its sha256 lands in every final-run JSON).
- [ ] The **sealed final batch** run once: LRU, LFU, Belady reference, infinite demand-loaded reference, oracle-prefetch bound, first-order, second-order — all predeclared. The headline table and multi-curve plot come from this batch and nowhere else.

---

## 8. Stage 5 — Template/parameter split + your own trace (2–3 days)

**Goal:** exercise the one piece NASA can't (parameterised routes), on a trace you own.

### 8.1 Instrument the OCR service (start this clock **early** — day one of the project, not day ten)

Add a FastAPI middleware to your DHIS2 OCR backend that appends one line per request to `requests.log` (or a sqlite table): `ts_ms, session_key, method, path, status, duration_ms`. Session key: authenticated user id if present, else a cookie you set. **Privacy note in `decisions.md`:** log paths and ids only — never request bodies, tokens, or OCR content — and tell the classmates you recruit exactly what is being logged; consent is part of the method, not paperwork. Collect ≥ 2 weeks; recruit a handful of classmates for realistic multi-user sessions. Small is fine — “production logs from a service I built” is the sentence you're buying (spec §7.5). One elevation adopted from the review: NASA's 1-second timestamps cannot support millisecond-level timing conclusions (a 50 ms gap and a 900 ms gap are indistinguishable there), so the realistic-latency **headline** must come from millisecond-resolution data — this trace first, the ms-stamped synthetic generator as fallback — with NASA's realistic-mode number demoted to coarse corroboration. That upgrades this stage from nice-to-have to required-for-the-timing-claim.

### 8.2 Template extraction — `model/templates.py`

- `template(path)`: split on `/`; replace any segment that is all-digits, a UUID, or matches your known id shapes (DHIS2 uids are 11-char alphanumeric — add that pattern) with `{id}`. `/order/456` → `/order/{id}`. Unit-test against a fixture list of your real routes.
- The model trains and predicts over **templates**; the cache stores **concrete keys**.

### 8.3 Candidate harvesting (spec §4.2 — “the single best idea in this project”)

When the API serves a response, the cache layer extracts the ids it contained (e.g., the id list in a collection response) and stores the last-N ids per session in a small ring buffer. On a template prediction `p(next=/order/{id}) ≥ τ`, instantiate with the session's candidate ids (top-1 or all, slots permitting) and prefetch those concrete keys. In the offline harness, emulate this by having the trace carry, for collection-type requests, the ids their real responses contained (your instrumentation can log those id lists for exactly this purpose — add that field now).

**Authorization boundary — non-negotiable the moment any endpoint is user-scoped:** the worker acts on ids observed in *somebody's* response, so cache keys must carry the principal (`user:{uid}:order:{id}`), and candidates harvested from user A's traffic must never materialise an entry user B can read. When in doubt, restrict prefetching to non-user-scoped endpoints and write that restriction down.

### Acceptance — Stage 5

- [ ] Template extractor unit-tested on your route fixtures.
- [ ] Full pipeline (parse → sessionize → P2-style split → replay) runs on the OCR trace; results table with the same metric set.
- [ ] README gains a second results section: “on production logs from my own service”.
- [ ] Millisecond-resolution realistic-latency analysis run on this trace (or the ms-synthetic), labelled as the timing headline; NASA's 1 s version relabelled "coarse corroboration".

---

## 9. Stage 6 — Live system + demo (3–4 days)

**Goal:** the number made visible. Two demo surfaces: `/race` (split-screen replay, the crowd-pleaser) and `/live` (the real running stack).

### 9.1 The live stack (spec §8 architecture, concretely)

One Docker image, two entrypoints; Redis for cache + stream; a fake slow backend.

**Redis key scheme (write it in `service/README`):**

```
val:{key}        response payload (string)
idx:demand       ZSET  key → access_seq   (score = INCR ctr:seq — LRU order)
idx:prefetch     ZSET  key → insert_seq   (score = INCR ctr:seq — FIFO order)
                 (why a counter, not ms timestamps: same-millisecond accesses
                  tie, and ZSET orders ties lexicographically — not by recency)
events           STREAM  {ts, session, key}   (XADD from API — awaited or queued, §9.1)
ctr:*            counters: hits, misses, prefetch_issued, prefetch_hit
recent_preds     LIST of last 50 prediction JSONs (for the dashboard)
```

- **`service/backend.py`** — the “database”: `async def fetch(key)` = `await asyncio.sleep(BACKEND_LATENCY_MS/1000)` + deterministic payload (and, for collection endpoints, a generated id list). Env-tunable latency.
- **`service/api.py`** — Loop 1 verbatim: `GET /orders`, `GET /order/{id}`, `GET /search`, `GET /profile`… Handler: check `val:{key}` → on hit, ZADD `idx:demand`, promote if key was in `idx:prefetch` (ZREM p / ZADD d / INCR prefetch_hit); on miss, `backend.fetch`, insert with demand-eviction (if `ZCARD idx:demand ≥ cap_d`: `ZPOPMIN` + `DEL val:*`), then log the event — and here sits a real async-Python footgun the spec's "never await" phrasing walks you into: calling `redis.xadd(...)` without awaiting it does **not** send the command (you get an unawaited-coroutine warning and silence). Pin one of two designs and write it down. **(A)** `await redis.xadd(...)` on the path — sub-millisecond against local Redis; the rule was never "zero logging latency", it was *no model inference* on the path; measure and report the Δp95 it costs. **(B)** `queue.put_nowait(event)` into a bounded `asyncio.Queue`, flushed to Redis by a background task; on a full queue, drop-oldest and increment a counter — which *is* backpressure, made visible. A is the default; B upgrades §9.4 item 5 from paper to code. Either way, publication lives in a common post-serve hook that fires on **hits and misses alike** — the learner needs the full request sequence, and a miss-only stream trains a model of a workload that doesn't exist. Also `GET /stats` aggregating the counters. Run uvicorn with `--workers 1` and say so in the README — but one process does **not** make the system race-free: the API and the worker mutate the same cache concurrently. Make the three mutation sequences atomic with small Redis Lua scripts (`EVALSHA`): demand insert-with-evict, prefetch insert-with-evict, and promote-on-hit. Each is 10–15 lines, they close the check-then-act windows entirely, and they're the difference between "demo" and "service" when someone reads the code.
- **`service/worker.py`** — Loop 2: the loop is **read → process → `XACK` only on success**, with `XAUTOCLAIM` of stale pending entries at startup and idempotent processing (dedupe by stream entry id) — core behavior, not a §9.4 menu pick, because a crash between count-update and ack guarantees redelivery. Per event: update counts (in-process dict, pickled every 60 s — a Redis-hash port is optional), predict, and if `p ≥ τ` and key absent everywhere → `backend.fetch` + insert into prefetch segment (FIFO eviction via `ZPOPMIN idx:prefetch`), `INCR prefetch_issued`, `LPUSH recent_preds`. Cap concurrent prefetch backend fetches with an `asyncio.Semaphore` (e.g. 8) so the prefetcher can never stampede the backend; on startup, reclaim stuck pending entries older than 60 s via `XAUTOCLAIM` before reading new ones. Crashing the worker must leave the API serving at plain-LRU behaviour — **that's a demo moment: kill the worker live, nothing breaks, restart it, hit rate climbs again.** Add the heartbeat-reclaim: the worker refreshes `hb:worker` (TTL 10 s); when the API finds it expired it stops honoring the prefetch reservation — effective f → 0, demand expands into the full capacity — which is what makes rule 2's "converges to full-capacity LRU" literally true rather than approximately polite.
- **`service/driver.py`** — the spec §7.4 generator pointed at `http://api:8000` with lognormal think-times and per-user personalities, fully seeded (`--seed`) so any synthetic trace — including the ms-timing fallback of §8.1 — is reproducible, with the seed travelling into every results JSON built from it. This is what makes `/live` move.

### 9.2 `/race` — split-screen replay (pure simulation, served by the same app)

Server side: a background task replays a trace slice through two in-process policy instances (LRU vs learned, imported straight from `oracle.policies` — the harness *is* the demo engine), advancing `speed` events per second, pushing one JSON per tick over a WebSocket:

```json
{"type":"tick","i":18452,
 "lru":{"hits":9120,"total":18452},
 "oracle":{"hits":12873,"total":18452,"precision":0.61},
 "pred":{"ctx":"/shuttle/countdown/","next":"/shuttle/countdown/count.gif","p":0.72,"outcome":"hit"}}
```

Client (`race.html`, vanilla JS + one Chart.js CDN line chart): two huge counters, rolling hit-rate lines, the live prediction ticker flashing green/red, a running precision figure. Controls POST `{"trace","size","tau","latency_ms","speed"}` to `/race/start`, which resets both policies and restarts the feed. The two money interactions (spec §10.2): drag **cache size** small → gap explodes; crank **τ to 0.1** → watch pollution eat your own hit rate on purpose. Rehearse both.

### 9.3 Demo script (the 3 minutes, in order)

1. `/race` at size 5000, τ 0.4 — press play, say nothing for ten seconds while the counters diverge.
2. Drag size to 500 — the thesis, visible.
3. τ → 0.1 — “here is our failure mode, on purpose, measured.”
4. Switch to `/live` — real services, driver running, `docker kill` the worker → still serving → restart → recovery. “The model is not on the request path.”
5. End on the static five-curve plot. That image is the README, the slide, and the interview answer (spec §10.3).

### 9.4 Backend-hardening menu — pick 3–4, document the rest

The offline harness alone could read as a data-science project; these are what make the live stack unmistakably backend work. With item 2 promoted to core (§9.1), implement at least **two of the rest** with evidence (a test or a log excerpt) and list the unimplemented ones in the README as known gaps:

1. **Request coalescing (singleflight):** a per-key `asyncio.Lock` in the API coalesces *concurrent API demands only* — it cannot see the worker's prefetch, which lives in another process. For cross-process coalescing, both paths claim `SET inflight:{key} NX PX 5000` in Redis before any backend fetch; or keep the local lock and state the narrower scope explicitly. Count `coalesced_fetches` either way.
2. **At-least-once + idempotent worker — promoted to core (§9.1)**; no longer counts toward the menu picks. The tests still live here: a redelivered event must not double-count or double-fetch, and prefetching an already-cached key is a no-op by design — assert both.
3. **Graceful Redis-down:** the API catches connection errors and serves straight from the backend — slower, never broken; increment an alarm counter. Pairs with the worker-kill demo moment.
4. **TTLs + lazy index cleanup:** `val:*` gets a TTL; `ZPOPMIN` on an eviction index tolerates already-expired keys.
5. *(document only)* **Backpressure:** worker pauses prefetching when backend in-flight > N. 6. *(document only)* **Obsolete-prefetch cancellation.** 7. *(document only)* **Poison-event dead-lettering.**

### Acceptance — Stage 6

- [ ] `docker compose up` brings up redis+api+worker+driver; `/stats` moves; `/race` and `/live` both work from a phone on the same network.
- [ ] Worker-kill test passes: request-*path* overhead unchanged, zero 5xx, availability continuous — hit rate is allowed to decay (that's the design, not a failure); with heartbeat-reclaim, demand visibly expands into the full capacity.
- [ ] Demo script rehearsed once end-to-end under 4 minutes.
- [ ] ≥2 remaining §9.4 items implemented with evidence (item 2 is core and mandatory); the rest listed as known gaps.

---

## 10. Stage 7 — Optional upside (only after 0–6 are green)

In strict order of value-per-day:

1. **Adaptive τ** from backend load (trivial: worker reads an in-flight gauge, scales τ).
2. **Sensitivity runs:** `--html-only`, keep-304, and the **byte-capacity variant** — the parser kept the `size` column for exactly this; state the fixed-size-entry assumption in the README either way.
3. **Learned eviction — now actually defined** (this is what earns the phrase, per §1 rule 11): for each demand-segment key k, `score(k) = λ·recency_rank(k) + (1−λ)·Σ p(k | c)` summed over the last r = 3 observed request contexts c; evict argmin; sweep λ. It is demand-fetch, so the Belady umbrella (§6.6) applies to it for real. Only after it is built and measured may "learned eviction" appear in any claim.
4. **Feature-based model** (time-of-day, session position) via gradient boosting — ~4 days.
5. **Small transformer** (spec rung 5) — last, and measure its inference latency against the gap distribution before believing anything it produces.
6. **WorldCup98 scale test** — binary format; budget the half-day for its parsing tooling.

---

## 11. Stage 8 — Deployment (the honest version)

### 11.1 What “deployed” means here — get the framing right first

Three different claims, keep them separate:

1. **“The evaluation ran on production traffic.”** True via trace replay (NASA, your OCR logs). This is the field-standard methodology — spec §14 is your script.
2. **“The system runs as real deployed services.”** True after this stage: the compose stack on a public VM, dashboard reachable by URL. Say “a deployed live demo of the system,” not “deployed to production.”
3. **“It served real production traffic live.”** Only claimable via §11.4. Optional, small-scale, still honest.

### 11.2 Containerise

`docker/Dockerfile` (one image): `python:3.12-slim`, copy `src/ service/ requirements.txt`, `pip install -r requirements.txt -e .`; default CMD is uvicorn, worker overrides the command.

`docker/docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    volumes: [redis-data:/data]
  api:
    build: {context: .., dockerfile: docker/Dockerfile}
    command: uvicorn service.api:app --host 0.0.0.0 --port 8000 --workers 1
    environment: [REDIS_URL=redis://redis:6379, CACHE_CAP=5000, TAU=${ORACLE_TAU}, BACKEND_LATENCY_MS=200]
    ports: ["8000:8000"]
    depends_on: [redis]
  worker:
    build: {context: .., dockerfile: docker/Dockerfile}
    command: python -m service.worker
    environment: [REDIS_URL=redis://redis:6379, TAU=${ORACLE_TAU}]
    depends_on: [redis]
  driver:
    build: {context: .., dockerfile: docker/Dockerfile}
    command: python -m service.driver --users 8
    profiles: [demo]
    depends_on: [api]
volumes: {redis-data: {}}
```

The demo runs the **frozen** configuration: a five-line `make demo-env` exports `ORACLE_TAU` (and friends) from `results/frozen.json`. Hardcoded folklore defaults in a compose file are how a demo quietly contradicts its own paper.

### 11.3 Where to put it (pick one)

- **Small VPS (recommended — least friction, fixed cost):** any ~$5 box (Hetzner CX/DigitalOcean/Lightsail). `apt install docker.io docker-compose-plugin`, clone, `docker compose --profile demo up -d`, open port 8000 (or put Caddy in front for TLS + basic-auth in ~10 lines). Done: a URL a recruiter can click.
- **Fly.io / Railway / Render:** fine too; you'll split api and worker into two services and use a managed Redis (e.g., Upstash) — more accounts, more YAML, same result. Choose this only if you don't want to own a VM.
- **Not** serverless: the worker is a long-lived stream consumer; Lambda-shaped platforms fight you for nothing.

### 11.4 Stretch — point it at something real (spec §10.4, upgraded)

Mount the cache layer in front of your DHIS2 OCR service's **read-only GET endpoints** (job-status, results-fetch), behind a feature flag, keys namespaced per user — and the §9.4 authorization rule applies with teeth here: ids harvested from one user's responses must never materialise cache entries another user can read; when unsure, prefetch only non-user-scoped endpoints. The Loop-1 design already guarantees the failure mode is “behaves like LRU,” so the risk is bounded; still: GETs only, flag-off by default, and the drift/precision counters you already built become live production metrics on *your* service. If you do this for even two weeks, claim 3 in §11.1 is yours — small-scale, precisely worded.

### Acceptance — Stage 8

- [ ] `docker compose up` cold-start works on a machine that isn't yours.
- [ ] Public URL serves `/race`, `/live`, `/stats`; basic-auth if the driver is left running.
- [ ] README “Deployment” section states exactly which of the three claims you're making.

---

## 12. Driving this with Claude Code

### 12.1 Repo prep before the first session

Commit the skeleton (§2.1), this `PLAN.md`, the spec PDF, and the `CLAUDE.md` below. Then work **one stage per session/branch** (`stage-0-data`, `stage-1-harness`, …), merging only when the stage's acceptance checklist is green.

### 12.2 `CLAUDE.md` — paste this in, adjust to taste

```markdown
# Project ORACLE — operating instructions

## What this is
An asynchronous predictive prefetching layer over an LRU-managed cache, evaluated against standard policies on real request traces.
Authority order: PLAN.md > spec/oracle-spec-v1.pdf > this file. Read the
current stage's PLAN section fully before writing code.

## Commands
make data | stats | baselines | markov | sweep | plots | test | demo
Run `make test` before claiming anything is done.

## Hard rules
1. Stage gates are hard: do not start stage N+1 tasks while stage N's
   acceptance checklist (in PLAN.md) has unchecked items.
2. Never modify the protocol definitions (PLAN §6.2) or the Policy
   interface (PLAN §4.1) without asking first.
3. Time-based splits only. If you find yourself writing a random split,
   stop and re-read PLAN §1.3.
4. No new dependencies or services without asking; if approved, log the
   reason in decisions.md.
5. Baselines are sacred: any change to lru.py/lfu.py/belady.py requires
   re-running the libCacheSim cross-check.
6. Replay loops iterate arrays, never pandas rows. Budget: LRU over full
   July < 30s.
7. Every result goes through the JSON writer (PLAN Appendix B) — no
   numbers that exist only in chat.
8. Write the stage's tests (PLAN Appendix C) before or with the feature,
   not after.
9. Append significant design choices to decisions.md as you go
   (one line: decision / alternatives / why).
10. Naming: this is "predictive prefetching over LRU". Never write
   "learned eviction" in code, README, or results unless PLAN §10
   item 3 is implemented and measured.
11. The P2 final window (Jul 25–31) is run once per configuration
   freeze. All sweeps and tuning happen on P2-dev. If you catch
   yourself re-running the final window to pick a knob, stop.

## Style
Plain Python, type hints, small modules. No cleverness in baselines.
```

### 12.3 Per-stage kickoff prompt (template)

> Read PLAN.md §<N> (Stage <N>) end to end. Restate the acceptance checklist as a TODO list, then implement the tasks in order. Write the tests listed for this stage first. Definition of done = every checklist item green with evidence (test output, files in results/). Do not touch anything belonging to later stages. Surface any ambiguity in the plan as a question before coding around it.

Two habits that keep long agentic sessions honest: make it **show you the acceptance evidence** (paste the test run, `ls results/`) rather than assert completion; and end each session by having it append the session's decisions to `decisions.md` and propose the commit message.

### 12.4 Collaboration mode — decide it explicitly

Your OCR project runs strict Socratic mode with Claude Code. For ORACLE, a reasonable split: **full-speed delegation** on Stages 0–2 and 6 (parsing, plumbing, dashboards — engineering you already own), **Socratic/attempt-first** on the parts that are the actual learning target: Belady's algorithm, the prefetch-timing semantics (§6.4), the backoff rule, and the τ/precision analysis. Write the chosen mode into `CLAUDE.md` so every session starts consistent.

---

## 13. Timeline

| Stage | Solo estimate | Notes / spec track |
|---|---|---|
| 0 — Data | 0.5–1 d | Track A. Start OCR instrumentation (§8.1) the same day. |
| 1 — Harness + LRU | 1–2 d | Track A |
| 2 — Baselines + libCacheSim | 1.5–2.5 d | Track A. Go/no-go gate. |
| 3 — Markov + prefetch | 3–4 d | Track B (builds synth generator while blocked on A); includes the P2-dev tuning pass |
| 4 — 2nd order + drift | 1.5–2.5 d | Track B; ends with the freeze + the sealed final batch |
| 5 — Templates + own trace | 2–3 d | Track B + C (needs §8.1 data matured) |
| 6 — Live system + demo | 3–4 d | Track C (can start early, independent); Lua + semantics work included |
| 8 — Deployment | 0.5–1 d | Track C |
| Docs, final runs, video | 2–3 d | README claims + full reproduction pass |
| **Total (solo)** | **~15–23 focused days** | Stages 0–4 alone = complete, defensible project (spec §9) |

The plan-review called v1's 11–15 days optimistic and estimated 18–29 focused days unassisted. The honest middle — given Claude Code and the fact that FastAPI/Redis/Docker are already in your hands — is ~15–23 focused days: the assistant compresses typing and boilerplate hard, and compresses *diagnosis* (why is the simulator wrong, why is precision low) barely at all. Two wall-clock facts no tooling changes: Stage 5's trace collection needs ~2 calendar weeks running from day one, and part-time alongside coursework this is a 5–8 week project. Plan for that, not the best case.

---

## 14. Master risk map (condensed from spec §11, mapped to gates)

| Risk | Symptom | Gate in this plan |
|---|---|---|
| No headroom | Belady ≈ LRU | §5.5 go/no-go before any model code |
| Crippled baseline | Suspiciously huge win | §5.4 libCacheSim exact match |
| Cache pollution | Ours < LRU | §6.5 segments + precision; §6.6 τ sweep |
| Prefetch too slow | Idealised ≫ realistic | §6.4 latency mode; §3.4 gap distribution |
| Leakage | Test > train, or magic numbers | §6.2 pinned time protocols |
| Circular eval | Great on synth, flat on real | Spec §7.4 generator rules; headline = real traces only |
| Cold start | Low coverage | min_support abstain + coverage metric (§6.3) |
| Scope creep | Week 3, still configuring infra | §1 rule 8; §10 ordering; CLAUDE.md rule 4 |
| Reserved-segment cost | Below LRU even at high precision | f-sweep with f = 0 control (§6.6) |
| Overclaimed significance | Tiny Δ sold as a result | Block-bootstrap CI (§6.7) |
| Mislabelled reference lines | "Beat the ceiling" confusion | Corrected labels (§5.2) |
| Session-concatenated replay | Indefensible numbers; ts runs backwards | Global `(ts, seq)` order + per-session context (§3.3, §4.1); tests 21–22 |
| Tuning on the test window | Inflated headline | P2-dev split; final window run once (§6.2, rule 12) |
| Dead prefetcher at defaults | Zero prefetches at every τ | Empirical probability + min-support (§6.3) |
| Lost or duplicated events | Model drifts from reality | Awaited/queued XADD, XACK + XAUTOCLAIM, Lua atomicity (§9.1) |
| Doctored workload | Singletons dropped from replay | Kept in replay, excluded from training only (§3.3, test 23) |
| Serial freezes = serial peeks | Multiple "final" runs | One sealed predeclared batch; rerun only on documented bug (rule 12) |
| Double-inserted prefetches | Backend traffic undercounted | Pending-race state machine + exclusivity invariant (§6.4, tests 24–25) |

---

## 15. Definition of Done — the whole project

Two completion tiers — stop points, not stretch-goals-you-failed. **Tier 1 · class-complete** = items 1–6, 8, 10–12 below, on NASA; a busy semester ending here is a *finished* project. **Tier 2 · portfolio-complete** = all twelve plus the own-trace results (7), the deployment URL (9), and a two-minute demo video.

The README contains, with nothing hidden:

1. **The question, answered.** The README frames the objective the review's way — *determine when predictive prefetching improves demand hit rate and user-visible latency over LRU at fixed total memory and bounded backend load* — and then fills the sentence: *“On the NASA-HTTP trace (protocol P2, counted Jul 25–31), at a 5,000-entry cache: LRU __%, LFU __%, predictive prefetch __% idealised / __% at 200 ms (Δ vs LRU = __ pp, 95% CI [__, __]), Belady demand-fetch reference (whole-horizon MIN) __%, infinite demand-loaded reference __%.”* All knobs frozen on P2-dev; these numbers come from a single post-freeze run, at ≤ 10% extra backend fetches (or whatever budget was actually used, stated).
2. The five-curve plot (log-x cache size).
3. τ-sweep + precision-vs-τ plots, chosen τ, and the pollution number stated plainly.
4. Latency-sensitivity plot (0→1000 ms).
5. Drift chart (July→August, frozen vs online).
6. Coverage %, extra-backend-load %, timely-prefetch rate, prefetch occupancy, and demand-latency mean/p50/p95 per policy.
7. Second results table on your own OCR-service trace.
8. The libCacheSim cross-check note.
9. A “Deployment” section stating exactly which §11.1 claim is being made, with the URL.
10. The spec §14 paragraph, adapted, as the FAQ answer to “did you deploy it?” — plus the pollution number and τ-curve ready for the follow-up question.
11. **Claims discipline** (from the résumé notes, adopted): described everywhere as *predictive prefetching* (§1 rule 11); it goes on a résumé only once the repo and real-trace results exist — “in progress” before that, and numbers never estimated or invented; if this runs as the 3-track team build, your own track is named explicitly in the README and the résumé bullet.
12. **Attribution checks** next to the headline: the `--html-only` variant and the unfiltered-bot run — did the win come from human navigation structure, or from asset bundles and filter choices? Report whichever answer the data gives.

---

## Appendix A — First commands, end to end

```bash
# day one
git init oracle && cd oracle            # …create skeleton per §2.1, commit
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# data in, verified
mkdir -p data/raw && cd data/raw
# fetch NASA_access_log_Jul95.gz + Aug95.gz from a mirror (§3.1), then:
zcat NASA_access_log_Jul95.gz | wc -l      # ≈ 1,891,715
zcat NASA_access_log_Jul95.gz | head -1    # the 199.72.81.55 apollo line
cd ../..

make data && make stats                    # Stage 0 gate
make baselines                             # Stage 1–2 (grow the policy list)
make validate-export                       # then run libCacheSim per §5.4
make markov && make sweep && make plots    # Stage 3
pytest -q                                  # always
```

## Appendix B — Results JSON schema (one file per run)

```json
{
  "run_id": "2026-08-30T14_lru_5000_P1",
  "git_sha": "abc1234",
  "trace": "data/processed/jul95.sessions.parquet",
  "trace_sha256": "…", "prep_version": "sessionize-v3-singletons-kept", "frozen_sha256": "…",
  "protocol": "P2",
  "counted_window": ["1995-07-25T00:00:00-04:00", "1995-07-31T23:59:59-04:00"],
  "policy": "oracle1",
  "capacity": 5000,
  "cfg": { "alpha0": 0.0, "load_budget": 0.10, "min_support": 5, "tau": 0.4, "top_k": 1,
            "prefetch_frac": 0.2, "latency_ms": 200, "online": false },
  "counted_requests": 412903,
  "hits": 231540, "misses": 181363, "hit_rate": 0.5608,
  "prefetch": { "issued": 88012, "hits": 53927, "evicted_unused": 30110,
                 "precision": 0.6127, "pending_missed": 3975 },
  "coverage": 0.71,
  "backend_fetches": 269375, "lru_misses_same_window": 233890,
  "extra_backend_load": 0.093,
  "demand_latency_ms": { "mean": 61.4, "p50": 2.1, "p95": 214.0 },
  "timely_rate": 0.93,
  "prefetch_occupancy": 0.11,
  "ci95_delta_hit_vs_lru_pp": [3.1, 5.8],
  "wall_clock_s": 41.2
}
```

## Appendix C — Test list (pytest; grows with the stages)

1. LRU cyclic pathology: `ABCD×1000`, cap 3 → hit rate exactly 0.
2. LRU hand-trace: 10 requests, cap 2, exact hit/miss sequence.
3. Capacity invariant for every policy (debug assertion mode).
4. Warmup gating: counts differ, end-state identical.
5. Determinism: result JSON identical across two runs on all *deterministic* fields (exclude `run_id`, `wall_clock_s`, and timestamps — a byte-identity test would fail on its own metadata).
6. LFU tie-break determinism on a crafted tie trace.
7. Belady hand-verified on 3 crafted traces (OPT computed on paper).
8. Property: Belady ≥ LRU and ≥ LFU for every (trace, size) in the test matrix, **under full-sequence counting** — under suffix-only counting the inequality is not guaranteed (§5.3), and a property test that can fail for protocol reasons is a flaky test.
9. Property: infinite demand-loaded ≥ every **demand-fetch** policy (prefetch-off configurations only; §5.2 explains why the prefetcher may legitimately exceed it).
10. **Plumbing gate:** learned policy, prefetch off, f = 0 → reproduces plain LRU's hit/miss sequence exactly, request for request.
11. Sessionizer: gap>30 min splits; length-1 sessions *retained* in output; same-second order stable via `(ts, seq)`.
12. Parser: fixture file with malformed lines → correct kept/dropped counts.
13. Markov: tiny corpus → exact empirical probabilities by hand (plus the α₀-prior variant when enabled).
14. Backoff: bigram-rich context uses table 2; sparse falls to table 1; else abstains.
15. Prefetch timing: gap 0 s with latency 200 ms → miss; gap 2 s → hit; idealised → hit.
16. Segment promotion: prefetched key hit → moves to demand seg, precision counters correct.
17. Template extractor: fixture routes → expected templates (incl. 11-char DHIS2 uids).
18. No-leakage guard: transition pairs only from train-slice timestamps (assert max train ts < min counted ts among training pairs).
19. Belady umbrella: every demand-fetch configuration (incl. Stage 7 learned eviction, prefetch off) ≤ Belady on all (trace, size) pairs.
20. Bootstrap sanity: the §6.7 CI of Δ between two identical LRU runs contains 0.
21. Replay-order guard: harness input is non-decreasing in `(ts, seq)`; a violation aborts the run.
22. Session-context isolation: a crafted global stream interleaving two sessions, built so cross-session context would predict differently → assert each prediction used only its own session's previous keys.
23. Singleton retention: length-1 sessions appear in the replay trace, contribute zero transition pairs, and the model abstains on them.
24. Pending race: crafted demand-before-`ready_at` ⇒ miss + `pending_missed` + demand fetch + obsolete prefetch discarded on completion — exactly one insert, exactly two backend fetches counted.
25. Segment exclusivity: under adversarial interleaving, no key ever occupies both segments (assertion mode).
26. Common random numbers: the same request index draws the same backend latency in every policy's run.

---

*End of build plan v1.3. When reality disagrees with this document, update the document — in `decisions.md` first, then here.*
