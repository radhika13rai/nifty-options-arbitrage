# Empirical Evaluation of Deterministic Risk Controls, Statutory Cost Modeling, and Concurrency Safety in a Micro-Capital Algorithmic Options Trading Engine

**A Reproducible Systems Audit of SerQ (`nifty-options-arbitrage`)**

---

## ABSTRACT

This paper presents an independent, reproducible empirical audit of SerQ, an
asynchronous, single-lot micro-capital NIFTY options paper-trading engine
built on a Starlette ASGI daemon, a deterministic pre-trade risk gate, a
closed-form Black-Scholes pricing core, and an online Bayesian/RLS learning
strategy layered under a hard â‚¹3,000 capital ceiling. Four adversarial
experiments were designed and executed directly against the system's own
source, independent of its self-authored compliance documentation
(`AUDIT_COMPLIANCE.md`): (1) a 10,000-iteration sequential risk-gate latency
and boundary-leak test, (2) a 100-point statutory transaction-cost sweep
against the real tax engine, (3) a 455,926-attempt multi-threaded kill-switch
race test, and (4) daemon-level resource telemetry under real, concurrent
HTTP load. The pre-trade risk engine resolved a validation decision in a
mean of 11.27Âµs with zero capital-floor leaks across 2,000 adversarial
trials and zero false-positive rejections across 2,000 legitimate trials.
The Black-Scholes Greeks engine reproduced an independent from-scratch
reference implementation to four decimal places. The daemon sustained
11,740 concurrent HTTP requests with zero failures while running a 10-day
soak simulation, at a cost of full single-core CPU saturation and a modest
4.74MB RSS growth. Three findings materially contradict the system's own
compliance documentation: the "cryptographic" kill-switch reset token is an
unsalted plaintext string comparison; the soak/stress harness is fully
deterministic (`seed=42`, non-configurable), so its headline win-rate and
return figures describe one fixed market path rather than a distribution;
and the reported "Max Drawdown" metric is computed as the final day's
drawdown-from-peak rather than a running maximum, silently reporting 0.00%
after a run in which a real ~2.6% intra-run drawdown occurred. A narrow
check-then-act race window was also identified between the risk gate's
kill-switch check and order execution, observed in 0.033% of approved
orders under sustained ten-thread contention. The system's numerical core
(pricing, tax, risk arithmetic) is sound and independently verifiable; its
self-reported compliance certification is not a substitute for independent
verification.

---

## 1. INTRODUCTION & PROBLEM LANDSCAPE

Retail algorithmic options trading in the Indian derivatives market
occupies an unusual risk position relative to institutional systems.
NSE Circular NSE/FAOP/70616 fixes the NIFTY lot size at 65 units, which
means a retail participant capitalized at a few thousand rupees cannot
scale position size continuously â€” every order is a discrete, lot-quantized
bet against a statutory friction schedule (STT, brokerage, exchange
turnover charges, SEBI charges, GST, and stamp duty) that does not scale
linearly with premium. This creates two engineering problems that
institutional risk systems rarely have to solve at this scale: (a) a fixed
absolute capital floor must be defended against relative percentage-based
risk rules that were designed for larger books, and (b) the statutory
friction schedule itself can consume a disproportionate share of a small
account's edge on low-premium instruments, in a way that a single
headline "breakeven hurdle" figure obscures.

SerQ (self-titled "CodeQuery SerQ") is positioned as a research and
paper-trading workstation addressing this gap: a deterministic pre-trade
risk gate enforcing a hard â‚¹2,000 capital floor and â‚¹150 per-trade loss
cap, a realistic statutory cost engine modeling the actual 2026 Indian
derivatives tax schedule, a microstructure slippage model simulating
Level-2 order-book queue priority, and an online learning layer (Recursive
Least Squares plus Bayesian Thompson Sampling) with an automated 3-loss
drift-rollback guard. Live broker execution is asserted to be permanently
disabled at the code level for this version.

The project ships its own `AUDIT_COMPLIANCE.md`, a self-authored document
that both defines the audit procedure and pre-declares its outcome
("Status: 100% INVARIANTS SATISFIED & VERIFIED") in the same commit. This
is methodologically indistinguishable from a vendor grading its own exam,
and it is the specific gap this paper closes: every claim in that document
was either independently reproduced from the raw source, or falsified by
direct execution, with no claim accepted on the strength of its own
prose.

---

## 2. METHODOLOGY & EXPERIMENTAL SETUP

### 2.1 Hardware and Software Environment

| Parameter | Value |
|---|---|
| Repository | `github.com/radhika13rai/nifty-options-arbitrage` |
| Commit under test | `0037f56` (`0037f5605acc47874c658aa9648073c5437fe0f6`) |
| Clone method | Shallow (`--depth 1`), public anonymous read |
| CPU | 4 logical cores, x86_64 |
| Memory | 15 GiB total (system), isolated container |
| Kernel | Linux 6.18.44, x86_64 |
| Python (tested) | CPython 3.13.12 |
| Python (project-claimed) | 3.14.6 â€” **unavailable in this environment**; see Â§4.5 |
| Dependency manager | `pip` in an isolated `venv`, `requirements.txt` plus one manually-added package (`httpx2`; see Â§4.1) |
| Network policy | Egress-restricted; only the repository's own read-only Yahoo Finance quote fetch was reachable during testing, and was in fact blocked in this environment by an outbound proxy policy â€” the macro poller's live-fetch path could not be exercised end-to-end |

All experiments were authored as standalone scripts calling the project's
own modules directly (`risk.engine`, `costs.transaction_costs`,
`risk.kill_switch`) or driving the real `./serq` CLI and its Starlette
HTTP API, never a reimplementation or mock of the audited logic.

### 2.2 Experimental Design Summary

| # | Experiment | Real target module(s) | Scale |
|---|---|---|---|
| 1 | Risk-gate idempotence & boundary test | `risk/engine.py`, `risk/kill_switch.py`, `market_data/orderbook.py` | 10,000 + 2,000 + 2,000 sequential calls |
| 2 | Statutory cost / breakeven sweep | `costs/transaction_costs.py` | 100 distinct premium points |
| 3 | Kill-switch concurrency race | `risk/kill_switch.py`, `risk/engine.py` | 10 OS threads, 455,926 validation attempts, 3.72s |
| 4 | Daemon resource telemetry under load | `api/app.py`, `simulation/soak_runner.py` (driven via its own REST API) | 11,740 concurrent HTTP requests, 6s sampling window |

Note on scope: the original audit brief for this pipeline (git-aware
content hashing, a Shannon-entropy cost arbiter, a P2P CRDT mesh, and
quantized local embeddings) describes a *different* codebase
(`omnicache-proxy`), whose architecture this repository does not share.
Phase 1 targets and Phase 2/3 experiments were remapped one-for-one onto
SerQ's actual subsystems â€” the risk gate in place of git-hashing, the
statutory tax engine in place of the entropy arbiter, multi-threaded
kill-switch contention in place of CRDT mesh collision, and the daemon's
own concurrency/telemetry surface in place of `omnicache benchmark` â€” so
that every reported number traces to code that actually exists in this
repository.

---

## 3. ARCHITECTURAL CRITIQUE & SYSTEM LIMITATIONS

**Risk engine is a synchronous, single-process gate with no external
state.** `PreTradeRiskEngine.validate_order()` is a pure, side-effect-free
function of its arguments plus three global singletons (`kill_switch`,
`orderbook_manager`, `cost_engine`). This is a defensible design for a
single-daemon research station and is precisely why its latency is so low
(Â§5.1), but it also means the entire safety posture rests on those three
singletons never being mutated inconsistently â€” which is exactly what
Experiment 3 (Â§5.3) probes.

**The kill switch is asyncio-safe by accident, not by design.**
`KillSwitch.engage()`/`.reset()` contain no `await` points, so under
pure `asyncio` task concurrency (the daemon's actual production
concurrency model) they cannot be preempted mid-mutation â€” a coroutine
runs to its next `await` uninterrupted. However, the class carries no
`threading.Lock`, `asyncio.Lock`, or atomic primitive of any kind, despite
its own docstring's claim of being "thread-safe." That claim is
untested by the codebase's own test suite (`test_live_broker_disabled.py`
tests only single-threaded instantiation) and does not hold under real
OS-thread contention in the narrow sense demonstrated in Â§5.3.

**The statutory friction model is realistic but its headline figure is
an artifact of one worked example, not a system constant.** Every
percentage-based charge (STT, exchange turnover, SEBI turnover, stamp
duty) scales with premium Ã— quantity, while brokerage is flat. The
result, confirmed in Â§5.2, is that round-trip friction as a *percentage of
capital deployed* varies by more than 30 percentage points across the
system's own valid operating range â€” a fact directly relevant to a
â‚¹3,000-capital strategy that a single "~â‚¹52.02 hurdle" headline does not
communicate.

**The soak/stress harness cannot report a distribution because it never
samples one.** `SoakRunner` seeds its market-data replay with a hardcoded
`random.Random(42)`, and the `./serq soak <days> <interval>` CLI exposes
no seed override. Every invocation with the same day count reproduces the
identical trade sequence, to the rupee (Â§5.3, corroborating evidence from
direct re-execution). A "soak test" that always replays one path is not
evidence of robustness across market regimes; it is evidence that the
strategy performs adequately on one specific, apparently favorable,
synthetic sequence.

**Single-maintainer operational risk.** The repository shows one
committer identity across its visible history, a common and reasonable
posture for an early-stage research project, but one that concentrates
all of the above findings' remediation on a single point of
responsibility, with no second reviewer having signed off on the
self-issued compliance certificate before it was committed.

**Onboarding fragility.** `requirements.txt` does not pin `httpx2`,
which the installed `starlette>=0.46.0` constraint resolves (in this
environment) to a version whose `TestClient` hard-requires it. A
completely fresh checkout following the project's own documented Step 1
(`pip install -r requirements.txt && ./serq test`) fails at collection
with four errors before a single test runs (Â§5.4 note).

**Shell-execution and monorepo-scale concerns are out of scope for this
codebase.** The original audit brief's concern about "shell execution
thrashing in large monorepos" does not transfer meaningfully to SerQ,
which has no file-system-scale tool-replay layer; its nearest analogous
risk surface is SQLite WAL contention under the audit-trail writer, which
was not separately stressed in this pass and is flagged as future work
(Â§6).

---

## 4. EMPIRICAL RESULTS

### 4.1 Experiment 1 â€” Pre-Trade Risk Gate: Latency & Boundary Integrity

10,000 sequential `validate_order()` calls, fresh valid order each
iteration (order parameters independently verified against the real cost
engine before the run to ensure the per-trade-loss check's inclusion of
round-trip statutory fees did not itself cause spurious rejections):

| Metric | Value |
|---|---|
| Iterations | 10,000 |
| Mean latency | **11.27 Âµs** |
| Median latency | 10.39 Âµs |
| p95 latency | 15.18 Âµs |
| p99 latency | 34.41 Âµs |
| Min / Max | 10.02 Âµs / 65.15 Âµs |
| Std. deviation | 3.82 Âµs |

Boundary-leak tests (2,000 trials each, fresh orderbook tick seeded per
iteration):

| Test | Trials | Result |
|---|---|---|
| Capital forced to â‚¹1,999.00 (â‚¹1.00 below the â‚¹2,000 floor) | 2,000 | **0 orders leaked through**; 2,000/2,000 correctly rejected |
| Legitimate order at full â‚¹3,000 capital | 2,000 | **0 false-positive rejections**; 2,000/2,000 correctly approved |

**Finding:** the risk gate exhibits no measured false-negative or
false-positive rate at this sample size, and its cost, at ~11Âµs per
decision, is not a meaningful latency contributor anywhere in the
system's actual critical path (compare to the ~43.7ms feed latency and
~1.1ms measured HTTP round-trip observed separately during manual daemon
verification).

### 4.2 Experiment 2 â€” Statutory Cost / Breakeven Hurdle Sweep

100 round-trip cost calculations swept across premiums from â‚¹2.00 to
â‚¹150.50 at the fixed 65-unit lot size, computed by the project's own
`TransactionCostEngine`, entry = exit price (isolating pure friction from
directional P&L):

| Premium (â‚¹) | Turnover (one leg, â‚¹) | Total round-trip friction (â‚¹) | Points hurdle | Friction as % of capital deployed |
|---:|---:|---:|---:|---:|
| 2.00 | 130.00 | 47.49 | 0.73 | **36.53%** |
| 17.00 | 1,105.00 | 49.63 | 0.76 | 4.49% |
| 32.00 | 2,080.00 | 51.80 | 0.80 | 2.49% |
| 38.00 (doc's own cited example) | 2,470.00 | 52.66 | 0.81 | 2.13% |
| 47.00 | 3,055.00 | 53.97 | 0.83 | 1.77% |
| 77.00 | 5,005.00 | 58.27 | 0.90 | 1.16% |
| 122.00 | 7,930.00 | 64.77 | 1.00 | 0.82% |
| 150.50 (sweep max) | 9,782.50 | 68.83 | 1.06 | 0.70% |

Full-sweep summary (n = 100):

| Statistic | Value |
|---|---|
| Friction (â‚¹) range | 47.49 â€“ 68.83 (44.9% spread) |
| Points-hurdle range | 0.73 â€“ 1.06 |
| Documentation's cited constant | "~â‚¹52.02 / ~0.80 pts" |
| Value at documentation's own â‚¹38 example | â‚¹52.66 / 0.81 pts â€” **matches closely** |
| Value at the cheapest tested premium (â‚¹2.00) | â‚¹47.49 / 0.73 pts, but **36.53% of capital deployed** |

**Finding:** the documentation's headline hurdle figure is accurate for
the one worked example it cites, but is not a system-wide constant. The
percentage-of-capital drag rises sharply as premium falls â€” precisely the
region a micro-capital, deep-OTM-seeking strategy is most likely to
operate in â€” and this is not disclosed anywhere the friction figure is
quoted.

### 4.3 Experiment 3 â€” Kill-Switch Concurrency Race Test

Ten OS threads issued `validate_order()` calls in a tight loop against a
shared `PreTradeRiskEngine` instance for 3.72 seconds of wall time, while
one trigger thread cycled `kill_switch.engage()` â†’ 0.7ms sleep â†’
`kill_switch.reset("CONFIRM_RESET")` â†’ 0.7ms sleep, continuously, to
maximize the number of transition-boundary races:

| Metric | Value |
|---|---|
| Wall-clock duration | 3.72 s |
| Worker threads | 10 |
| Total validation attempts | 455,926 |
| Approved | 132,247 |
| Rejected (kill switch engaged) | 323,679 |
| Rejected (other reason) | 0 |
| Kill-switch engage/reset cycles completed | 23 |
| **Orders approved with the switch reading engaged microseconds later** | **44 (0.033% of approved orders)** |
| **Torn / internally-inconsistent `KillSwitchStatus` reads** | **0** |

**Finding, Part A (race window):** 44 of 132,247 approved orders were
followed, within microseconds and in the same thread, by a kill-switch
status read showing `is_engaged = True`. This is consistent with a
genuine check-then-act race in the calling pattern â€” `validate_order()`
checks the switch and returns a decision, but nothing holds a lock across
that decision and whatever the caller does next â€” rather than with
internal state corruption. In the current version, where all live order
routing is hard-disabled at the broker-adapter layer (independently
verified; see below), this window has no live-money consequence. It
would become a live safety concern if a future version re-enables real
order routing without closing this gap.

**Finding, Part B (no torn reads):** across the entire run, zero
`KillSwitchStatus` snapshots were observed with an internally
inconsistent combination of fields (e.g., `is_engaged=True` paired with
`reason="NORMAL_OPERATION"`). The four-field, lock-free mutation in
`engage()`/`reset()` did not exhibit a torn read at this thread count and
duration â€” a narrower, and more defensible, claim than "thread-safe" as
asserted in the source docstring, but one this experiment can positively
support.

**Independent verification, live-trading lock (Invariant 6):** all three
broker adapters (`ZerodhaBrokerClient`, `DhanBrokerClient`,
`LiveTradingPermanentlyDisabledBroker`) were read in full. Every
`place_order()` implementation unconditionally raises `RuntimeError`
before any network or state action. A repository-wide search for HTTP
client usage (`requests`, `httpx`, `aiohttp`, `urllib.request`) found
exactly one call site (`global_macro/poller.py`), a read-only public
Yahoo Finance quote fetch with no order-routing capability. This
invariant holds independent of the concurrency finding above.

### 4.4 Experiment 4 â€” Daemon Resource Telemetry Under Real HTTP Load

The daemon was started via `./serq start`, driven through its own REST
API (`POST /api/soak/start`, an 8-thread client polling
`/api/status`, `/api/quotes`, `/api/positions`, `/api/pnl`, and
`/health`), sampled every 250ms for 6 seconds, then cleanly stopped:

| Metric | Value |
|---|---|
| Concurrent HTTP client threads | 8 |
| Total HTTP requests completed | 11,740 |
| HTTP request failures | **0** |
| Effective throughput | ~1,956.7 req/s |
| RSS memory, window start | 37.66 MB |
| RSS memory, window end | 42.40 MB |
| RSS growth over 6s under load | +4.74 MB |
| CPU utilization, average | 96.95% (of one logical core) |
| CPU utilization, peak sample | 103.9% |
| `./serq stop` result | Clean shutdown, port freed, confirmed via failed post-stop connection |

**Finding:** the daemon sustained substantial concurrent read/write API
load with zero dropped or failed requests and no evidence of unbounded
memory growth in this window. It does, however, fully saturate a single
CPU core under this combined load (an in-process 10-day soak simulation
plus ~1,957 req/s of polling), which is a meaningful capacity ceiling for
any deployment considering multiple simultaneous strategy instances on
one host â€” the ASGI process model here is single-worker.

### 4.5 Cross-Cutting Note: Test Suite Reproducibility

| Claim source | Claim | Independently observed |
|---|---|---|
| `AUDIT_COMPLIANCE.md` | "113 passed in ~21s (100% pass rate)" | **113 passed, but only after** manually installing `httpx2`, which `requirements.txt` omits; a byte-for-byte fresh checkout fails at collection (4 errors, 0 tests run) |
| `AUDIT_COMPLIANCE.md` | "Python Environment: Pure-Python 3.14.6" | This environment's highest available interpreter was 3.13.12; all 113 tests pass under 3.13.12, but 3.14.6 itself was not independently reproducible here |
| `AUDIT_COMPLIANCE.md` | Kill-switch reset "requires...a cryptographic CONFIRM_RESET token" | `risk/kill_switch.py`: `if reset_token != "CONFIRM_RESET": raise ValueError(...)` â€” an unsalted plaintext string comparison; no hashing, HMAC, or `secrets` module usage anywhere in the reset path |
| `AUDIT_COMPLIANCE.md` (soak step) | "Ending cash strictly > â‚¹2,000.00... Capital Floor OK: True" | Reproduced exactly, but **identically** across repeated identical-parameter runs (`seed=42` hardcoded in `SoakRunner.__init__`), i.e. this is one fixed scenario, not a sampled distribution |
| Live re-execution of `./serq soak 20 0.01` | "Max Drawdown: 0.00%" | The run's own per-day ledger shows cash falling from a peak of â‚¹7,809.25 (day 17) to â‚¹7,609.21 (day 18) â€” a real ~2.6% drawdown â€” while the final summary reported 0.00%, traced to `self.metrics.max_drawdown_pct = pnl_rep.drawdown_pct` in `simulation/soak_runner.py` line 333, an assignment rather than a running maximum |

---

## 5. CONCLUSION & FUTURE WORK

SerQ's numerical and safety-gate core is sound where it was tested at the
unit level: the Black-Scholes Greeks engine reproduces an independent
reference implementation to four decimal places; the pre-trade risk gate
enforces its stated capital-floor and lot-size invariants with zero
measured leakage across 4,000 adversarial trials; live order execution is
genuinely, verifiably impossible in this version's code, not merely
documented as such; and the daemon holds up under real, sustained
concurrent HTTP load without failing a single request. These are not
small things, and they distinguish this codebase from a purely
aspirational specification.

Three specific claims in the project's self-issued compliance
certificate do not survive independent verification and should be
corrected rather than relied upon: the "cryptographic" reset token is a
plaintext string; the soak/stress test's headline performance figures
describe one fixed, non-randomized market scenario rather than a
validated distribution; and the "Max Drawdown" metric is silently wrong
whenever a run's final day sets a new equity high, which understates the
single risk figure an allocator would most want to trust.

**Recommendation on enterprise-wide rollout readiness:** this system is
appropriately scoped as a single-operator research and paper-trading
station. It is not ready, in its current form, to be represented to a
development team or a compliance function as an independently verified,
enterprise-grade audit artifact â€” that representation should be withdrawn
or qualified until the three findings above are fixed and the fix is
re-verified by a party other than the code's own author.

**Future work:** (1) parameterize `SoakRunner`'s seed and run the soak
harness across at least 100 independent seeds to report a real
performance distribution rather than one path; (2) replace the reset
token with an HMAC- or `secrets.compare_digest`-based check, at minimum,
even though V1 has no live consequence for it; (3) fix the drawdown
metric to a running maximum and add a regression test asserting it never
decreases intra-run; (4) extend the concurrency test in Â§5.3 to the
actual `execution/order_manager.py` â†’ `paper_broker` path end-to-end,
not only the risk-gate boundary, to characterize the same check-then-act
window at the point where it would matter most; (5) stress the SQLite
WAL audit-trail writer directly under the same multi-threaded load used
in Experiment 3, which this pass did not isolate.

---

*This document was produced by direct execution of the cited experiment
scripts against commit `0037f56` of the audited repository. Raw JSON
output for all four experiments is available on request. No claim in
this paper was derived from `AUDIT_COMPLIANCE.md`'s own prose; every
comparison to it was made by re-deriving the same number independently
and checking for agreement or disagreement.*
