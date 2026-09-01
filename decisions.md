# decisions.md

The running log for Project AUSPEX. Per PLAN §1 rule 8 and CLAUDE.md rule 9:
one entry for every design choice, correction, plan change, dependency, and
discussion that a future reader could reasonably have resolved differently.

**Maintenance:** Claude appends to this file continuously and unprompted —
after decisions, after mistakes and their corrections, after any discussion
that changes the plan. Ateeksh does not have to ask. Newest entries at the
bottom. Format: **decision / alternatives / why**, plus **status** where a
question is still open.

Legend: `D###` = decision. `C###` = correction (something we got wrong and
fixed). `Q###` = open question, awaiting an answer.

---

## Session 1 — 2026-08-25 · project setup

**C001 — Claude built the repo skeleton; it was reverted.**
What happened: the session opened by creating the full PLAN §2.1 skeleton
(`src/oracle/`, `service/`, `docker/`, `synth/`, `tests/`, `Makefile`,
`requirements.txt`, `pyproject.toml`, `.gitignore`, `README.md`), then started
a `python3 -m venv .venv` + `pip install` that Ateeksh rejected mid-run.
Correction: everything created after the last commit was deleted, including
the partially-built `.venv`. Only `CLAUDE.md` was kept.
Why it was wrong: Ateeksh owns the scaffolding and toolchain and is setting it
up himself with **uv**. The lesson generalises — **do not create project
scaffolding, virtualenvs, or dependency installs unprompted.** Ask, or wait.

**D001 — The project is renamed ORACLE → AUSPEX.**
Repo and remote were already `auspex` / `github.com/ateekshSood/AUSPEX`; the
plan document still says ORACLE throughout. Applied to `CLAUDE.md` (title,
`src/auspex/` paths, `spec/auspex-spec-v1.pdf`). Python package becomes
`src/auspex/`, invoked as `python -m auspex.*`.

**D002 — The word "oracle" is overloaded in PLAN.md and must be renamed
selectively, never with a global find-and-replace.** Three distinct senses:
1. *Project name* → becomes AUSPEX (package, module paths, Makefile targets).
2. *`oracle-prefetch bound`* (PLAN §5.2, §5.5) → **stays "oracle"**. It is
   standard caching/ML vocabulary for the ceiling policy that always predicts
   the session's true next request. "auspex-prefetch bound" would be
   unreadable to anyone in the field and would damage the README's credibility.
3. *`oracle1` / `oracle2`* — the `--policies` CLI values and the `"policy"`
   field in results JSON, meaning "our learned policy, 1st / 2nd order".
Alternatives: rename everything; rename nothing. Why selective: sense 2 is a
technical term of art, sense 1 is branding, and they sit adjacent in the same
CLI flag (`--policies ...,nextoracle,oracle1,oracle2`) where conflating them
would confuse the reader of every results file.

**Q001 — Rename inside `spec/PLAN.md` itself? — OPEN.**
PLAN.md is the committed authority document; a selective rename is a large
diff to it. Alternative: leave PLAN.md as historical text and let CLAUDE.md
carry the ORACLE→AUSPEX mapping. Awaiting Ateeksh's call.

**Q002 — Policy names `auspex1` / `auspex2`? — OPEN.**
Proposed: rename `oracle1`/`oracle2` → `auspex1`/`auspex2`, leaving
`nextoracle` and "oracle-prefetch bound" untouched, so "our policy" and "the
oracle bound" stay visibly distinct. Awaiting confirmation. These strings land
in every results JSON, so the choice should be made before Stage 3 writes any.

**D003 — `PLAN.md` lives at `spec/PLAN.md`, not the repo root.**
PLAN §2.1 shows it at the root; it arrived in `spec/`. Left as-is — it is
already committed there and `spec/` is the natural home for authority
documents. CLAUDE.md's authority line points at `spec/PLAN.md`.
Note: `spec/auspex-spec-v1.pdf` (the team specification) is **not** in the
repo. The authority chain currently terminates at PLAN.md.

**D004 — CLAUDE.md rule 11 follows PLAN v1.3 §1 rule 12, not the §12.2
template.** The §12.2 CLAUDE.md template still says the final window "is run
once per configuration freeze" — the exact loophole v1.3's rule 12 closes
("serial freezes are serial peeks"). CLAUDE.md instead states the sealed,
predeclared, single-batch rule. Alternatives: copy §12.2 byte-for-byte and let
the two documents contradict each other. Why: CLAUDE.md is read at the start of
every session, and a rule that licenses repeated peeks at the Jul 25–31 window
is the most expensive thing in this project to get wrong. Also corrected the
dangling "PLAN §1.3" pointer in rule 3 to "PLAN §1 rule 3". Everything else in
§12.2 is verbatim. **Status:** flagged to Ateeksh; revert on request.

**D005 — Toolchain is `uv`, not `python -m venv` + `pip`.**
Deviates from PLAN §2.2's setup block and the `setup:` Makefile target.
Why: Ateeksh's choice; uv is faster and lockfile-native, and PLAN §2.2's real
requirement is *pinned, reproducible deps* ("the lock states the truth your
results were produced under"), which `uv.lock` satisfies at least as well as
`requirements.lock`. Consequence to remember: the §2.2 commands and the
`setup:` target in the Makefile need updating to match whatever uv layout
Ateeksh lands on.

**D006 — Dependency set stays exactly PLAN §2.2's ten** (pandas, pyarrow,
numpy, matplotlib, tqdm, pytest, fastapi, uvicorn[standard], redis, httpx).
Any addition needs a one-line justification here first (PLAN §1 rule 8).

### Still to record before Stage 0 can be marked done (PLAN §3 acceptance)
- URL normalization rule (strip `#fragment`, otherwise byte-for-byte; no
  lowercasing, no slash collapsing) — §3.2
- The GET + status 200 only rule, and the keep-304 variant deferred to Stage 7
- Bot heuristics as actually applied, with the drop rate each rule produced
- The embedded-image note: 1995 pages pull `.gif` bursts in the same second,
  inflating zero-gap transitions; stays in the headline, `--html-only` is a
  Stage 7 sensitivity run — §3.3

---

## Session 2 — (next) · Stage 0

_Stage 0 has not started. Repo currently contains `CLAUDE.md` and
`spec/PLAN.md` only; Ateeksh is creating the skeleton and uv environment._

---

## Session 2 — 2026-08-25 · Stage 0 (Data)

**D007 — NASA-HTTP obtained from the canonical ITA source over HTTPS.**
`https://ita.ee.lbl.gov/traces/NASA_access_log_{Jul,Aug}95.gz`. PLAN §3.1 warns
the ITA links are "ancient and frequently down" and steers toward Kaggle/GitHub
mirrors; the canonical host answered `200` on the first try, so no mirror was
needed. Why this matters: mirrors are of unknown provenance and PLAN §3.1 warns
"wrong/truncated mirrors are common" — the canonical file needs no trust
argument. sha256 recorded for the results-JSON provenance field:
- `Jul95` `199109ed0f273e095da6ccd5fc9dc4cd8bb58daa06d62135e62090fea9d27488` (20,676,672 B)
- `Aug95` `14995aed0ba4558ab832613ebea9a3ef2d87cb4297fc67f5694e0032bbb6b788` (16,633,316 B)

**D008 — Verification passed; the July line-count "mismatch" is not one.**
`wc -l` reports 1,891,714 vs PLAN §3.1's expected 1,891,715. Cause: the July
file's final line is **truncated** (`alyssa.p`, no newline), so `wc -l` counts
newlines and undercounts the unterminated last line by exactly one.
1,891,714 + 1 = 1,891,715 — reconciled, file is canonical. Consequence: that
truncated line is a genuine malformed record and must show up in the parser's
dropped-malformed count (PLAN §3.2). Expected malformed count is therefore
≥ 1 and the rate stays far below the 0.1% gate. First line matches PLAN §3.1's
expected apollo line byte-for-byte. Aug95: 1,569,898 lines, ≈1.57M as expected.

**C002 — PLAN is wrong about the July file's end date: it stops on Jul 28,
not Jul 31.** Measured coverage: `01/Jul/1995:00:00:01 -0400` →
`28/Jul/1995:13:32:25 -0400`. There is **no Jul 29/30/31 data at all**, and
Jul 28 is a **partial day** ending 13:32 (27,121 requests vs a ~60k full day).
PLAN §6.2 pins the P2 counted slice as "July 25 → July 31 (end of file)", and
§1 rule 12, §15 item 1, and CLAUDE.md rule 11 all repeat "Jul 25–31". That
window cannot exist. PLAN §6.2 anticipated this — "Adjust exact boundaries
after reading real min/max timestamps in Stage 0; keep the ~70/10/20 shape" —
so this is the plan working as designed, not a surprise. Actual per-day counts
give the *current* P2 shape as train 81.5% / pre-warm 7.3% / counted 11.1%,
which is not ~70/10/20. See Q003.

**C003 — PLAN is also wrong about August's start date.** §3.1 says "the server
was down at the start of August (Hurricane Erin), so the August file starts on
the 4th". It starts `01/Aug/1995:00:00:01`. The real shape: Aug 1 runs to
14:52:01, then a ~37.7-hour outage with **Aug 2 entirely absent**, resuming
`03/Aug/1995:04:36:13`. File ends `31/Aug/1995:23:59:53` (a full day).
No action needed: P3 (§6.2) is already written robustly as "pre-warm = first
2 days *present* in August", which handles a missing calendar day correctly.
Recorded because §3.1's factual claim is wrong and the next reader will trip on
it.

**Q003 — P2 / P2-dev window boundaries need re-pinning. — OPEN, blocks Stage 3,
not Stage 0.** CLAUDE.md rule 2 forbids changing §6.2 protocol definitions
without asking, so this is a question, not a decision. Candidate that preserves
the ~70/10/20 shape on real request counts:
- train Jul 1–18 (1,338,680 req, 70.8%)
- pre-warm Jul 19–21 (203,960 req, 10.8%)
- counted Jul 22–28 (349,074 req, 18.5%)
This also yields **exactly 7 calendar day-blocks** in the counted window, which
is what §6.7's block bootstrap assumes ("7 blocks"). Caveats to settle at the
same time: (a) the final block, Jul 28, is a half-day — either accept an
unequal block or drop it and count Jul 22–27 (6 blocks); (b) P2-dev currently
counts Jul 17–21, which under this proposal falls inside the final *pre-warm*
slice and partly inside train — P2-dev needs its own re-pinning so that all
tuning stays strictly earlier than the final counted window.
Deferred deliberately: this is Stage 3 territory and Stage 0 must not touch it.

**Q004 — `uv add` for PLAN §2.2's dependencies? — OPEN, blocks Stage 0 code.**
Stage 0 needs `pandas pyarrow numpy matplotlib tqdm pytest`. Not run
unprompted, per [[no-unprompted-scaffolding]] / C001.

**Q005 — `.gitignore` currently contains only `CLAUDE.md`.** `data/raw/` holds
37 MB of `.gz` that PLAN §2.1 marks gitignored. Flagged before any commit puts
it in git history permanently.

**Session 2 end — 2026-08-25.** Stopped mid-Stage-0 at Ateeksh's request.
State: NASA Jul95 + Aug95 downloaded and verified (§3.1 acceptance item ✅);
no parser code written; blocked on **Q004** (deps) and **Q005** (`.gitignore`).
Q001/Q002/Q003 remain open but block later stages, not Stage 0.
The verbatim resume message is stored in memory as `auspex-resume-point`; on
"lets continue" it gets re-sent before any other work.

Stage 0 remaining, in order: `src/auspex/config.py` (§2.4) → `parse_nasa.py`
(§3.2) → `sessionize.py` (§3.3) → `stats.py` (§3.4) → Appendix C tests 11 + 12
→ `make data` idempotency check → the four §3 acceptance records listed above
→ stage-gate explain-back.

---

## Session 3 — 2026-08-27 · Stage 0 continues

**D009 — Q004 resolved: the six Stage 0 deps are installed via `uv`.**
Ateeksh ran `uv add` himself. `pyproject.toml` now pins matplotlib, numpy,
pandas, pyarrow, pytest, tqdm; `uv.lock` (112 KB) is written; `.venv` exists.
Exactly PLAN §2.2's Stage 0 six, no additions. The four Stage 6 deps (fastapi,
uvicorn, redis, httpx) are deliberately not installed yet. Q004 is **CLOSED**.
Note `requires-python = ">=3.13"` vs PLAN §2.2's "3.11+ (3.12 fine)" — newer,
not a conflict, but pandas 3.0 / numpy 2.5 are majors ahead of what the plan
was written against; watch for API drift in §3.2's parser.

**D010 — Q005 resolved: the NASA `.gz` files are removed from git history and
the repo; README carries the download links instead. — LOCAL DONE, PUSH PENDING.**
Alternatives: (a) leave 37 MB in history; (b) `git rm --cached` + gitignore,
which untracks going forward but leaves the blobs in every clone; (c) remove
from history properly. Chose (c). Why it was cheap: the data lived in exactly
one commit, `ba60bf2`, which was the tip — so `git reset --mixed HEAD~1` drops
it with no `filter-repo` and no rewriting of any other commit. Why at all: the
files are public archive data with a canonical URL and recorded sha256s, so the
repo gains nothing by carrying them and every clone pays 37 MB. Also expanded
`.gitignore` (was just `CLAUDE.md`) to cover `data/`, `results/`, `figures/`,
`*.parquet`, `.venv/`, `__pycache__/`, `.pytest_cache/`. README.md now holds the
ITA URLs, both sha256s with byte counts, and the three measured file quirks
(C002/C003/D008) so the next reader does not re-derive them.
**Incomplete:** `main` was already pushed and `origin/main` still points at
`ba60bf2`, which keeps the blobs reachable — `.git` is still 36 MB and will stay
so until a `--force-with-lease` push rewrites the remote. Backup bundle of the
pre-rewrite state is in the session scratchpad. Awaiting Ateeksh's go-ahead on
the force-push.

**C004 — correction to Q003's caveat (b): the P2-dev/P2 overlap is
pre-existing, not something the candidate re-pin introduces.**
Q003 caveat (b) said P2-dev's counted slice "falls inside the final pre-warm
slice and partly inside train", implying the candidate creates a problem.
Re-checked against §6.2 as written: P2 train is Jul 1–21 and P2-dev's
validation-count is Jul 17–21, so P2-dev's validation window **already** sits
entirely inside P2's training data in the plan as written. The candidate re-pin
does not create the overlap; it only changes which part is train (17–18) vs
pre-warm (19–21). Consequence: **Q003 does not block Stage 3.** Every P2-dev
day exists in the file, so the whole §6.6 tuning pass runs exactly as specified.
Q003 comes due at the end of Stage 4, before the sealed batch. The earlier
"OPEN, blocks Stage 3" label was wrong. The real (milder) issue underneath is
validation-inside-train, not test leakage — the counted window is untouched
either way — but it should be decided deliberately rather than inherited.

**D011 — the strongest argument for re-pinning P2 is §6.7, not the 70/10/20
shape.** §6.7 pins the block bootstrap at "block = one calendar day of the
counted window (**7 blocks**)", resampled 10,000×. Under §6.2 as written the
counted window resolves to Jul 25–28 = **4 blocks, one of them a half-day**,
because Jul 29–31 do not exist. A 4-block bootstrap produces a CI too wide to
separate any plausible result from zero, which disables the §15 item 1 headline
claim entirely. The candidate (counted Jul 22–28) restores exactly 7 day-blocks,
so §6.7 needs no edit at all. Recorded because the shape argument (81.5/7.3/11.1
vs ~70/10/20) is cosmetic by comparison and should not be the one that carries
the decision.

**Measured per-day July request counts** (source of every % above; `grep -oE
'\[[0-9]{2}/Jul/1995' | cut -c2-3 | sort | uniq -c`, total 1,891,714):
1:64714 2:60265 3:89584 4:70452 5:94575 6:100960 7:87233 8:38867 9:35272
10:72860 11:80407 12:92536 13:134203 14:84103 15:45532 16:47854 17:74981
18:64282 19:72738 20:66593 21:64629 22:35267 23:39199 24:64259 25:62699
26:58849 27:61680 28:27121
Slices: P2 as written = train Jul 1–21 1,542,640 (81.5%) / pre-warm Jul 22–24
138,725 (7.3%) / counted Jul 25–28 210,349 (11.1%). Candidate = train Jul 1–18
1,338,680 (70.8%) / pre-warm Jul 19–21 203,960 (10.8%) / counted Jul 22–28
349,074 (18.5%). P2-dev as written = 1,106,031 / 93,386 / 343,223.

**C005 — Claude wrote Stage 0 implementation code; it was deleted. Rule
widened: Claude never writes implementation code for this project, any file,
any stage.**
What happened: Claude created `src/auspex/__init__.py`, `config.py` (§2.4) and
`parse_nasa.py` (§3.2), added a `[build-system]` block to `pyproject.toml`, ran
the parser over both logs and wrote `data/processed/*.parquet`. Ateeksh stopped
it: *"your job is to teach me dont build it yourself ever i will build i am
doing this to learn... i wanna be an engineer."* All of it removed;
`pyproject.toml` reverted to his version. Only `tests/test_parser.py` kept, and
only because CLAUDE.md explicitly allows Claude to write Appendix C tests in
full — subject to his confirmation.
Why it happened (not an excuse, a cause worth recording): CLAUDE.md's LEARNING
MODE splits files into ATTEMPT-FIRST and DELEGATE, and lists "parsing,
sessionization, stats, vocab, plotting, CLI/JSON plumbing" under DELEGATE —
"build at full speed". Stage 0 is entirely DELEGATE files, so the section read
as authorisation. It is not what Ateeksh wants.
**Consequence — CLAUDE.md's DELEGATE list is now wrong and must be amended.**
Every file is ATTEMPT-FIRST. Claude teaches, asks for the approach in words,
probes holes with questions, escalates hints one level at a time, reviews
diffs, and writes Appendix C tests. It does not produce implementation code
without a literal "override: show me", and then the minimum fragment.
Related: C001, same failure one layer down (scaffolding rather than app code).
Recorded in memory as `never-write-implementation-code`.

**D012 — measurements taken during C005's deleted run, kept because they are
facts about the data, not code.** Re-derivable by Ateeksh's own parser and
useful as expected values to check it against (§3.2 prints exactly these):
- Jul95: total 1,891,715 · kept (GET+200) 1,697,501 (89.73%) · dropped by
  filter 194,194 · **malformed 20 (0.0011%)** — far under the §3.2 0.1% gate.
- Aug95: total 1,569,898 · kept 1,394,951 (88.86%) · dropped by filter 174,923 ·
  malformed 24 (0.0015%).
- Jul95 kept rows: 7,225 unique URLs, 80,982 unique hosts, 83 NULL sizes.
- **Note the total: 1,891,715, matching PLAN §3.1 exactly** — iterating the file
  yields the unterminated final line, which `wc -l` cannot count (D008).
- All 20 July malformed lines are genuinely corrupt *and* every one carries
  status 400/403/404, so none would have survived the GET+200 filter anyway —
  zero data loss. The dominant pattern is a stray `"` inside the URL
  (`"GET /images/" HTTP/1.0" 404 -`), which breaks CLF quoting; two are binary
  garbage from a broken client; the last is `alyssa.p` at seq 1,891,714, the
  truncated final line predicted by D008.

---

## Session 3 (cont.) — 2026-08-28 · Stage 0 design calls

**C006 — §3.2 contradicts itself on the `method`/`status` parquet columns;
Ateeksh found it. Resolution: drop both columns.**
§3.2's keep rule deletes every non-GET and non-200 row *in the parser*, then the
same section says to keep `method`/`status` "so the keep-304 variant re-filters
from this file instead of re-parsing". Both cannot hold: the 304 **rows** are
gone before the parquet is written, so preserving the `status` **column** cannot
recover them — it records a constant (`200`) that the filter rule already
guarantees. Ateeksh's reading, which is almost certainly right: the sentence is
a leftover from an earlier draft in which the parser wrote *all* GET rows and
the 200-filter happened downstream. In that design the sentence is correct.
Decision: **Option A — narrow file.** Parser keeps GET + 200; `method` and
`status` are not written. Alternative considered (Option B — wide file): parser
writes all GET rows, reader applies `status == 200`, making the plan's sentence
true and the Stage 7 304-variant a one-line filter. Why A: B relocates the
headline filter to "whoever loads the file", and forgetting to apply it silently
counts 304s as cache references while the README says otherwise — a wrong number
that looks right. A makes that error impossible; the cost is re-parsing the
`.gz` (~40 s, once) if the 304 variant is ever run in Stage 7.
Cost of keeping them was measured, not assumed: two constant columns over
1,697,501 rows add **11 KB** to the parquet (0.056%) because columnar RLE
collapses a constant. So this was decided on semantics, not size.

**D013 — parquet columns are therefore `seq, ts, host, url` (+ `size`, pending).**
Deviation from §3.2's seven-column list, following C006. `size` is retained-or-
not per Ateeksh's "add fields when we need them" rule (D014) — its only known
consumer is the Stage 7 byte-capacity variant.

**D014 — knobs and columns are added when a stage needs them, not up front.**
Ateeksh's call, and Claude agreed it is the better one. `config.py` starts with
the two knobs Stage 0 uses (`session_gap_s`, `bot_max_session_len`) and grows a
field per stage, rather than transcribing §2.4's fifteen at once. Why: writing
knobs he cannot yet use is transcription, not learning; each one lands when the
problem it solves is in front of him. Alternative: copy §2.4 verbatim now.
**Hard deadline on this:** the set must equal §2.4 by the end of Stage 4, because
that is when `results/frozen.json` is written and a knob outside the freeze is a
knob that could have been changed unrecorded (§1 rule 12). Diff `Cfg` against
§2.4 before the freeze. Corollary that still binds: §2.4's "nothing else
hardcodes a number" — a needed number goes into `Cfg` first, then gets used.

**D015 — test order reversed: implementation first, tests after.**
Ateeksh's call, 2026-08-28. Contradicts CLAUDE.md hard rule 8 and LEARNING MODE
item 1 ("write the failing test first"), both amended to match. Why: Claude had
already written `tests/test_parser.py` before any parser existed, and that test
pinned the module's API — function names, return shapes, whether stats was an
object or a dict. Designing the interface is the part Ateeksh is here to learn,
so a pre-written test hands him the answer to the wrong question. That test was
deleted. Known cost, and the mitigation: tests written after an implementation
can be unconsciously shaped to pass whatever the code already does. Mitigation
pinned — Claude derives tests from §3.2's stated requirements and D012's
measured counts, not by reading his implementation back to him. Appendix C's
list is the checklist either way.

**D016 — `size` is kept in the parquet.** Ateeksh's call: its only consumer is
the Stage 7 byte-capacity variant, and re-adding it later would mean re-parsing
the `.gz`, so the cheap move is to write it once now. Slight tension with D014
(add fields when a stage needs them), accepted knowingly — the honest framing is
"Stage 7 is a stretch goal that may never happen, and we're paying a near-zero
cost to keep the option open", not "we will need it". Nullable `Int32`: CLF's
`-` becomes NULL, never 0, so a missing size can never be confused with a
zero-byte response.

**D017 — build backend is `hatchling`; package installed editable from
`src/auspex`.** Added `[build-system]` (requires `hatchling`,
build-backend `hatchling.build`) and `[tool.hatch.build.targets.wheel]`
(`packages = ["src/auspex"]`) to `pyproject.toml`. Alternatives: `setuptools`
(the old default, works identically, more config), or no build system at all
plus `sys.path` manipulation. Why hatchling: modern default, minimal config,
what `uv` itself uses. Why a build system at all rather than `from src.auspex…`
or a `sys.path.append`: those work only from the repo root and break
`python -m auspex.*`, which §2.1/D001 pins as the invocation style for every
Makefile target; an editable install puts a `.pth` pointer in site-packages so
`auspex` resolves from any directory with no environment variables.
hatchling is a **build-time** tool, not a runtime dependency, so it is correctly
absent from `[project] dependencies` — logged per CLAUDE.md rule 4.

**D018 — `Cfg` currently holds four knobs:** `session_gap_s` (1800),
`bot_max_session_len` (500), `prefetch_frac` (0.20), `warmup_frac` (0.20).
Stage 0 needs only the first two; the other two were added because Ateeksh had
just understood them, which is consistent with D014's intent (a knob lands when
its idea does). Eleven of §2.4's fifteen remain; the deadline for parity is the
end of Stage 4 (`frozen.json`).

**D019 — parser works; §3.2 acceptance numbers reproduced by Ateeksh's own
implementation.** `python -m auspex.parse_nasa -j` on Jul95, 25 s:
total 1,891,715 · kept 1,697,501 · dropped-by-filter 194,194 · malformed 20
(0.0011%). Matches D012's independently measured values exactly, including the
1,891,715 total — the parser reads the unterminated final line that `wc -l`
cannot count (D008). Parquet: 23.5 MB, 1,697,501 rows, `seq` monotonic,
`size` dtype `Int32` with 83 nulls preserved (not float64, not zeros).

**D020 — parser API, as Ateeksh designed it.** Recorded because the tests are
written against it (D015). `parse_line(line)` → a dict
`{host, ts, method, url, status, size}` or `None` when malformed (no regex
match, or a request field with fewer than 2 parts). `parse_file(path)` → a dict
`{filtered_lines, malformed, dropped, kept, total}`, where `filtered_lines`
holds the **kept** rows as flat dicts with `seq` added and `method`/`status`
popped (C006/D013). `write_parquet(rows, output_path)` builds the DataFrame,
casts `size` to `Int32`, writes with `index=False`. `main()` takes `-j`/`-a`
boolean flags — both may be passed to process both files — prints help when
neither is given, and resolves paths from
`Path(__file__).resolve().parents[2] / "data"` so behaviour never depends on
the shell's working directory.

**D021 — CLI is `-j`/`-a` flags, not `--input`/`--output` paths.**
Ateeksh's call: the project has exactly two datasets forever, so typing full
paths on every invocation is friction for no flexibility. Deviates from §2.1's
implied `--input/--output` style. Why it costs nothing: `parse_file` and
`write_parquet` still take explicit paths, so tests and any future one-off feed
them directly and never touch `main()`. `--input/--output` can be added later
without breaking the flags. Path resolution anchors on `__file__` rather than
`Path.cwd()` — a `cwd`-derived path makes behaviour depend on which directory
the user happens to be standing in, which is the same class of fragility as
importing via `src.auspex` (D017).

**Session 3 end — 2026-08-28.** Stage 0 ~40%. `config.py` and the parser are
Ateeksh's own code and both work; the parser reproduces every §3.2 acceptance
number. Left mid-cleanup with six known touch-ups (two of them live bugs: the
`assert` references `filtered` where the local is `dropped`, and the malformed
gate is `0.01` where §3.2 says `0.001`). Remaining for the stage: Appendix C
tests 11 + 12, `sessionize.py`, `stats.py`, `make data` idempotency, the four
§3 acceptance records, and the stage-gate explain-back. Resume notes are in
memory as `auspex-resume-point`.

**D022 — filename stays `parser_nasa.py`; PLAN §3.2 says `parse_nasa.py`.**
Ateeksh's call: the two names carry the same meaning and the rename buys
nothing. Alternatives: rename to match §3.2, or rename and leave a shim.
Why it's safe: nothing imports it by name yet. **Consequence to honour** — the
Makefile's `data` target must read `python -m auspex.parser_nasa`, not
`parse_nasa`; §3.2's filename is now a known, deliberate deviation rather than
a typo to be "corrected" later.

**D023 — the two per-file blocks in `main()` collapsed into one function,**
`make_dir_fetch_details_write_parquet(name)`, parameterised by the dataset stem
("Jul95" / "Aug95"); `main()` keeps the `-j`/`-a` flags (D021) and just
dispatches. Alternatives: leave the duplication, or pass explicit paths.
Why: the two blocks differed only in two filenames, so the duplication was
pure drift risk — and the Aug95 path had in fact never been run until the
dedupe forced it through the same code.

**D024 — correction to D020: `parse_file` returns `kept_rows`, not
`filtered_lines`.** D020 recorded the key under its older name. The rows are
the *kept* ones, so `kept_rows` is the accurate name; Appendix C test 12 is to
be written against `kept_rows` (D015).

**D025 — Aug95 parsed for the first time, 2026-08-29:** total 1,569,898 ·
kept 1,394,951 · dropped-by-filter 174,923 · malformed 24 (0.0015%), 19.6 s,
parquet 19.4 MB. Jul95 re-verified unchanged after the dedupe
(1,891,715 / 1,697,501 / 194,194 / 20, 24.3 s). §3.2 pins acceptance numbers
for July only; the August figures are recorded here as the baseline any future
change to the parser must reproduce.

**D026 — §3 acceptance record 1/4: URL normalization rule (final).**
Strip any `#fragment`; otherwise keep path+query byte-for-byte. No lowercasing
(URLs are case-sensitive), no slash collapsing, no query-string reordering or
stripping. The cache key **is** the exact remaining string. Alternatives
considered and rejected: lowercasing (would merge `/HISTORY/` and `/history/`,
which the 1995 server treated as distinct objects), dropping query strings
(would merge distinct dynamic responses into one key and fabricate hits).
Implemented at `parser_nasa.py:25` as `url.split('#', 1)[0]`.

**D027 — §3 acceptance record 2/4: the GET+200 keep rule (final).**
Keep a row iff `method == "GET"` **and** `status == 200`; drop everything else,
counted as `dropped`. Jul95: 194,194 dropped (10.3%); Aug95: 174,923 (11.1%).
Alternative explicitly deferred: also keeping `304`, on the argument that a 304
proves the client *asked* for the object and so is a genuine cache reference.
Why 200-only for the headline: it matches the spec, and mixing 304s changes the
hit/miss denominator, so it belongs in Stage 7 as a sensitivity check, not in
the headline. Per C006 the 304 rows are gone from the parquet, so that variant
means re-parsing, not re-filtering.

**D028 — Appendix C test 12 (parser) written by Claude, after Ateeksh's
implementation, per hard rule 8 / D015.** `tests/test_parser.py`, 20 tests,
all passing in 0.5 s. Fixture: a 14-line gzipped log built in `tmp_path` —
6 kept, 4 dropped-by-filter (404 / 304 / POST / HEAD), 4 malformed (non-log
garbage, one-part request field, empty request field, non-numeric status).
Three deliberate design choices, recorded because they are what makes the test
worth having:
- **The fixture interleaves** good and bad lines, so kept rows land on seqs
  `[0, 2, 4, 6, 8, 10]`. A fixture with the good lines first would pass even if
  `seq` were the index among *kept* rows rather than the raw-log row index;
  this one cannot.
- **The final line is written without a trailing newline**, mirroring the real
  files (D008/D019), pinning the 1,891,715-vs-`wc -l` discrepancy as intended
  behaviour rather than an accident.
- **Column *order* is deliberately not asserted** — §3.2 pins the column set,
  not its order, so asserting order would be reverse-engineering the dict's
  insertion order from the implementation, which D015 forbids. The test asserts
  set equality `{seq, ts, host, url, size}` (method/status absent per C006/D013)
  plus the absence of any `__index_level_*` column from `index=False`.
Also pinned as executable rules: D026 (fragment stripped, query byte-for-byte,
case preserved) and D027 (GET+200 only), plus `size` nullable `Int32` with the
`'-'` row null and never 0, and timestamps as UTC epoch seconds with `-0400`
honoured.

**Session 4 end — 2026-08-29.** Stage 0 ~60%. The parser is finished and
locked down by tests. Discussion this session (recorded because the
explain-back at the stage gate draws on it): §3.3 was explained to Ateeksh in
parts — part 1, what sessionization is and why the model cannot learn
transitions from an interleaved multi-user log; part 2, the two-sorts idea
(`(host, ts, seq)` to *build* sessions, then a global re-sort by `(ts, seq)` to
*replay* them) and why replaying session-by-session deletes the eviction
contest, inflates every policy's hit rate, and makes the clock run backwards
through `on_tick`. Part 3 — singleton retention and the three bot rules — was
not reached. No code was written for `sessionize.py`; per LEARNING MODE he
states his approach in words first.

**Session 5 end — 2026-08-31.** Stage 0 still ~60%; no code written. Discussion
only, recorded for the stage-gate explain-back: §3.3 finished being explained.
Part 3 delivered — singletons stay in the replay workload and are excluded only
at transition-extraction time (`session_length >= 2`), because dropping them
would inflate both baseline locality and apparent model coverage; and the three
bot rules (`/robots.txt` host, session length > `bot_max_session_len`, host gap
CV < 0.1 with >=100 requests), each printing its own drop count, total kept
under ~10%. Then a simplified rebuild pinned two things Ateeksh had wrong:
(a) a new session starts when **the host changed OR the gap exceeds
`session_gap_s`** — the host test is not optional, since the "gap" across a host
boundary is negative and would silently weld two people into one session;
(b) bot filtering cannot run *before* sessionizing, because the session-length
rule needs `session_id` to exist — so all three rules run after labelling, while
the frame is still in host-grouped order. Also corrected: Markov here is plain
conditional-probability counting (maximum likelihood), not Bayes' theorem;
`seq` in the sort key, not `kind="stable"`, is what actually guarantees
deterministic same-second order (pandas' default kind is `quicksort`, unstable).

**Open, awaiting his answer before `sessionize.py` is written:** are the three
bot-rule drop counts measured **in sequence** (each rule sees only what earlier
rules spared; counts sum to the total) or **independently** against the original
frame (more informative per rule; counts overlap and will not sum)?

**D029 — bot-rule drop counts are measured *in sequence*, not independently.**
Closes the question left open at the end of session 5. Rule 1 (`/robots.txt`
host) runs first, rule 2 (session length > `bot_max_session_len`) sees only what
rule 1 spared, rule 3 (host gap CV < 0.1, >=100 requests) sees only what rules
1-2 spared. Alternatives: score each rule independently against the original
frame, which says more about each rule in isolation but produces overlapping
counts that do not sum. Why: the three printed counts then add up to the total
dropped, which is exactly the arithmetic the <=10% safety rail in PLAN §3.3
needs; a crawler that trips both rule 1 and rule 3 is attributed to rule 1 only,
which is honest as long as the ordering is recorded — it is, here. Consequence
to remember when reading the numbers: a later rule's count is a count of *extra*
rows it caught, not a measure of how much traffic that rule could catch alone.

**D030 — §3 acceptance record 3a/4: bot rule 1 (`/robots.txt`) is a structural
no-op on NASA-95, and the function stays anyway.** Discovered 2026-09-01 while
implementing `drop_robots_hosts`. The raw July log contains 59 `/robots.txt`
requests; **all 59 returned 404**, because the server had no such file. D027
keeps GET+200 only, so every one of them is removed by the parser before
`sessionize.py` runs: the parsed frame contains zero rows whose URL mentions
"robots", and the rule can therefore never fire. Two correct decisions collide;
neither is wrong. Alternatives considered: (b) have `parser_nasa.py` collect the
set of robots.txt hosts *before* the status filter and hand it to sessionize,
recovering the signal at the cost of a cross-module dependency and an edit to a
locked file; (c) delete the rule from the project. Chosen: **(a) keep the
function, let it report 0, and document why.** Why: the rule is correct code and
stays correct on any trace where `/robots.txt` returns 200 — the no-op is a
property of this dataset, not of the implementation — and (b) buys a filter that
D027 has already made unnecessary for the replay workload. Consequence: the
per-rule drop counts printed by §3.3 will always show rule 1 = 0 rows on
NASA-95; that zero is expected output, not a bug, and must be read as "this
dataset has no confessed crawlers", never as "this dataset has no crawlers" —
rules 2 and 3 are what actually catch them here.

**D031 — §3 acceptance record 3b/4: bot rule 2 (session length > 500) keeps the
threshold, and what it actually catches.** Inspected 2026-09-01, per PLAN §3.3's
requirement to eyeball the top 5 offenders before dropping. July has **27
sessions over 500 requests, 25,966 rows (1.53%)**. All five of the largest are
the same phenomenon and **none of them are crawlers**: they are the shuttle
countdown-clock page (`/htbin/cdt_main.pl`, `cdtclock.gif`, `countclock.gif`,
plus the site logos) left open in a browser under a ~100 s meta-refresh. The
worst, `siltb10.orl.mmc.com`, is **2,760 requests across 3 unique URLs spanning
280,107 s (3.2 days)**. Two consequences worth recording:
- **`session_gap_s` behaved correctly and still produced a 3-day "session".**
  A ~100 s refresh never reaches the 1800 s gap, so the session never closes.
  The 30-minute rule segments *human idle time*; it has nothing to say about a
  client that is never idle. Not a bug — a stated limit of the definition.
- **Measured, not assumed:** in-sample first-order next-URL predictability is
  **60.9%** inside these sessions vs **46.2%** everywhere else. At 1.53% of rows
  that is roughly **+0.2 pp** on a headline number — real, but far smaller than
  first claimed in discussion. The claim was corrected after measuring.
Decision: **drop them, and keep the threshold at 500.** Why: the justification
is *not* headline inflation (0.2 pp would not be worth a filter). It is that a
browser reloading itself on a timer is not a person navigating a website, and
the workload is meant to be the latter — the same argument would hold if the
number had moved the other way, which is what makes this a principled filter
rather than tuning. Alternatives: keep them and note the bias (rejected — harder
to defend than removing them); raise/lower the threshold (rejected — no evidence
for a different number, and Stage 7 can sweep it). Naming note for the write-up:
call these **degenerate self-refreshing clients**, not "bots".

**D032 — §3 acceptance record 3c/4: bot rule 3 (gap CV < 0.1) is the second
structural no-op, and the function stays.** Measured 2026-09-01 on July, three
ways, all zero:
- **per host, raw requests** — 1,842 hosts have >=100 requests; their CV runs
  min **0.738**, median 5.99, max 44.3. Nothing within 7x of the 0.1 threshold.
- **per host, page-views only** (same-second bursts collapsed to one event per
  `(host, ts)`) — 1,534 eligible hosts, lowest CV **0.726**. Still zero.
- **per session** (>=100 requests) — 3 of 550 eligible sessions fall below 0.1.
Two causes, both structural, neither a code defect:
1. **Embedded images make every gap distribution bimodal.** A 1995 page view is
   an `.html` plus five or ten `.gif`s arriving in the same second, so a host's
   gaps read `0, 0, 100, 0, 0, 100, ...` rather than `100, 100, 100`. Perfectly
   regular traffic, but standard deviation punishes bimodality hard.
   `siltb10.orl.mmc.com` — the countdown-clock host, a true ~100 s metronome —
   has **median gap 1 s, mean 100.5 s, std 373.3, CV 3.715**.
2. **A month of gaps is never homogeneous.** Even a browser on a refresh timer
   gets closed overnight, so between-sitting gaps are orders of magnitude larger
   than within-sitting ones and dominate the std. CV < 0.1 can only hold inside
   one uninterrupted sitting — which is why collapsing bursts (cause 1) still
   did not rescue the rule.
Decision: **(a) keep the rule, keep the function, let it report 0, document the
zero in a code comment.** Alternatives: (b) redefine CV per *session* rather than
per host — rejected, a spec change yielding 3 extra sessions; (c) loosen
`bot_cv_threshold` until something is caught — rejected outright, that is tuning
a filter until it agrees with you, exactly what PLAN §3.3's "cleaning, not
curating" warning forbids. Why keep it: the implementation is correct and fires
as intended on a trace whose crawlers do not sleep; the printed 0 is a measured
result the acceptance record needs; and Stage 7 cannot sweep `bot_cv_threshold`
on a deleted function. Note the redundancy: **rule 2 already removed every
metronome found here** — the countdown-clock sessions went via session length —
so rule 3 is inert rather than merely unlucky.

**D033 — §3 acceptance record 4/4: the embedded-image note.** 1995 pages pull
their images inline, so one page view produces a same-second burst (`.html`
then five or ten `.gif`s). Consequences, now measured rather than asserted:
zero-gap transitions are inflated; every host's inter-request gap distribution
is bimodal, which is cause 1 of D032; and the Markov model will learn
image-follows-page pairs alongside genuine navigation. **This is real traffic
and stays in the headline run** — the cache served those requests and a
prefetcher would have to handle them. An `--html-only` variant (keep `.html` and
`/`-ending URLs only) is a legitimate **Stage 7** sensitivity experiment showing
the navigation structure more cleanly; it is not the headline. Do not "fix" this
in Stage 0.

**D034 — `sessionize.py` (§3.3) complete, 2026-09-01, written by Ateeksh.**
Pipeline: `load` -> `label_sessions` -> `drop_robots_hosts` ->
`drop_long_sessions` -> `drop_metronome_hosts` -> `write`, driven by
`process_month(name)` behind the same `-j`/`-a` CLI as the parser (D021).
Verified output for July: **1,671,535 rows** (1,697,501 − 25,966), globally
sorted by `(ts, seq)` with `ignore_index=True`, index clean `0..n-1`, no
`__index_level_*` column. Drop counts sum exactly to rows removed, confirming
D029's sequential arithmetic. Totals: July 25,966 = **1.53%**, August 2,210 =
**0.16%** — both far under the ~10% rail, which `process_month` now checks and
warns to stderr about, matching `parser_nasa.py`'s existing warning pattern.
Notable during the build, worth keeping for the stage gate:
- The first `write()` re-sorted by `(host, ts, seq)` — sort 1 again, i.e. the
  exact v1.1 bug PLAN §3.3 warns about. Caught in review before it shipped.
  Sort 2 is `(ts, seq)`; **host is deliberately absent from it.**
- `session_id` is non-monotonic in the output (30553, 146528, 29458, ...) and
  that is correct: ids are labels, every downstream use is `groupby`, and
  nothing depends on their order or contiguity.
- Every bot rule drops whole hosts or whole sessions, never part of one, so
  `session_id` / `pos_in_session` stay valid after filtering and no re-labelling
  pass is needed.
- **August drops 10x less than July** (0.16% vs 1.53%): the countdown-clock
  traffic that dominates rule 2 is a July phenomenon (STS-70 launched Jul 13).
  Filter behaviour is month-dependent — remember this before comparing months.
**Still open on this file:** whether `size` stays in the output (PLAN §3.3 lists
six columns and omits it; decide by reading what the latency model needs), the
D030/D032 code comments marking rules 1 and 3 as structural zeros, and an
August run.
