# M1 kernel implementation and review ledger

## Dispatch — 2026-09-20 continuation

Frozen design: M1-K1 in `m1-kernel-contract.md`; exact work packages in
`wp-m1-foundation.md`. User explicitly removed D7b as a mechanics prerequisite.
UI integration stopped/retained, no new lab expansion. Runtime remains standard
library only, old entrypoints and saves protected. No default agent/config changes.

| Package | Owner session | Dependency / status | Sol | Ponytail / final |
| --- | --- | --- | --- | --- |
| WP-01 clock/commands | frontend-go `ses_f3fa02d58ffeJ2BQ3vkfjpqfOf` | Correction1 delivered; Astra39 PASS | Re-reviewing | Pending |
| WP-03 save codec/safety | frontend-go `ses_f3f9fe1e1ffeSNatAbEiY93Wa4` | Incomplete initial tranche; same-owner verification continuation | Pending | Pending |
| WP-KV tiny vector/test | micro-go `ses_f3f9f9bf0ffeeyw1rTMi1dzDIi` | Accepted / hash frozen | PASS | LEAN → final Sol PASS |
| WP-02 finance | frontend-go queued | Starts after WP-01 final acceptance; spec authorized | Pending | Pending |

No shared writes: WP-01 owns package init files/domain/application/random adapter;
WP-03 owns saves.py and its fixture/test only; micro owns vector JSON and its test.
WP-02 extends service/commands/campaign/tick only after WP-01 is frozen/accepted.
Each package acceptance and rewrite return to its original worker, maximum two
correctness cycles and one justified simplicity rewrite, then final Sol and audit.

Evidence root `/tmp/opencode/gamedev-m1/`, subdirectories per package. Current
contract hash manifest `contracts-frozen.sha256` contains both authoritative docs.
On this continuation previous external `/tmp/opencode` M1 baseline was unavailable;
do **not** claim it was reverified. Re-captured current protected non-kernel baseline
of83 files and dirty tracked diff before package source deliveries. This includes
newly present `.coderabbit.yaml`/`CODERABBIT.md` as protected user work, as well as
all existing source/config/UI artifacts. Workers only create new kernel paths.
Observed runtime Python3.14.7; design uses Python3.10-compatible stdlib APIs, but
actual3.10 execution is not yet proven and must not be claimed.

Package delivery, exact diffs/test output, Sol findings, simplicity records and
cross-codec kernel audit will be appended here. Nothing accepted merely by dispatch.

Current preserved-game baseline: `python -m unittest test_simulation test_version10
test_browser` **PASS147** on Python3.14.7 (34.624s), `legacy-baseline.log`. This is
an actual current rerun, not reuse of missing earlier /tmp evidence.

WP-KV delivered exact two files. Astra independently ran the targeted unittest:
PASS1 test with three vector subtests, collected `wp-kv/astra.diff` and
`wp-kv/candidate.sha256`; no runtime import/change. Sol session
`ses_f3f9da06effeB0l7IoWJMXZW5Q` reviewing exact K2 literal agreement and test method.
No acceptance until Sol/Ponytail/final confirmation. WP-01 and WP-03 continue in
their disjoint production namespaces; WP-02 remains dependency-queued, not stalled
on UI selection.

### WP-KV accepted — 2026-09-20

Sol PASS with no findings: independently ran1 test/3 vector subtests, verified
literal hashes/u64 against K2 using independent digest/big-endian checks, candidate
hashes and exact two-file diff. Astra explicitly loaded Ponytail AFTER PASS and
read complete38-line test/20-line fixture: **LEAN**, straightforward stdlib witness,
no speculative machinery or worthwhile reduction. No edits ordered. Sol final
**PASS** verified unchanged two-file hashes and retained test evidence.
Accepted manifest `wp-kv/frozen.sha256`; no correction cycles or provider fallback.
This accepts the contract witness, not the concurrently developing runtime kernel.

### WP-01 initial delivery / correctness review

Original Go worker hit step limit after completing ten allowed files and removing
an unused import. Astra independently reran final-source acceptance rather than
claiming the earlier worker run covered that last edit: **37 tests PASS** (0.190s),
`compileall -q studio_sim` PASS. Collected ten-file `wp-01/astra.diff` and
`candidate.sha256`; all83 protected baseline files unchanged. Generated __pycache__
files are build artifacts, not additional authored implementation scope.

Sol `ses_f3f9a47a4ffeZK3Hc57Pxs54Xs` reviewing full K1/K2 API/state/clock/receipts/
copy ownership/RNG contract plus targeted gaps. WP-02 stays queued until final
gates, while WP-03 continues independently. Worker only syntax-parsed3.10; actual
runtime acceptance is Python3.14.7. No fallback/commit or UI work.

Sol initial **REWRITE**, three majors (complete defect list):
1. service.py57–60/115–116: no-op set_pause bypasses capacity and increments
   revision10^9 to1000000001. Check revision on every new accepted command,
   including no-ops; add boundary regression. Cached duplicates remain no-ops.
2. service.py29–37/169–180: tuple descendants accepted; cyclic containers raise
   RecursionError rather than invalid_command. Enforce exact JSON types, ancestor
   cycle/depth rejection, with tests for tuple/cycle/excess nesting.
3. tick.py78–85/114–135: premature K3 insolvency evaluation in WP-01 violates the
   package's initial-finance-only scope and would preempt same-day rescue. Delete
   solvency evaluation/event creation and its WP-01 test; WP-02 owns evaluation
   after mandatory settlements, preserving atomicity/end-before-decision order.

Sol independently37 tests/compile/candidate10 hashes/protected83 hashes passed,
then reproduced the first two failures by probes. Astra resolves scope explicitly:
WP-01 contains NO financial failure evaluation. K2 clarified command tree limit32
container levels/exact JSON types and no-op revision bound; no save schema change.
Same frontend-go ordered correction1; WP-02 remains gated, WP-03 still disjoint.

### WP-03 initial tranche incomplete

Worker reached step limit after codec/repository and K5 fixture implementation,
with only partial codec tests (~64) and three known test issues. No completed
acceptance claimed. Missing store/locking/recovery/fault/Ironman tests are mandatory,
not optional polish. Same Go session continued to finish actual temp-file fault
coverage, correct test expectations against the frozen contract, run full targeted
suite/py_compile and capture three-file diff/baseline checks. No domain imports,
UI edits, cross-package writes or fallback permitted. A functioning codec alone
does not prove save safety or clear this package's review gate.

WP-01 correction1 delivered: only service/tick/clock-test changed among ten allowed
files. No-op revision capacity enforced, exact JSON type/ancestor-cycle/depth32
validation added, premature financial closure code/tests removed. Astra independently
**39 tests PASS** (0.115s) plus compile; all ten cycle1 hashes matched. Evidence
`wp-01/astra-cycle1.log`, full `astra-cycle1.diff`, incremental `correction1.diff`,
`candidate-cycle1.sha256`. Sol same session re-reviewing; no acceptance yet.
Worker's broad discovery observed two failures in concurrently unfinished WP-03;
these are not an accepted full-kernel run or permission to edit sibling tests.
Targeted package evidence is authoritative until all dependencies are complete.
