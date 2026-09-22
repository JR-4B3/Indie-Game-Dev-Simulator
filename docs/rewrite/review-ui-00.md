# WP-UI-00 reviews and lab audit

## Initial correctness review — 2026-09-11

Worker: frontend-go `ses_f72f0334fffejF44u35bci35Cq`.
Sol: `ses_f7257e3e4ffewGS6glOSTFtleN`. Verdict: **REWRITE**.
No provider fallback; step-budget continuations completed initial work but did not
substitute for correctness review. Astra independently verified six-file scope,
protected-source/save hashes and full diff; acceptance passed 1251 assertions.
Diff/evidence: `/tmp/opencode/gamedev-ui-lab/wp-ui-00.diff`, `review-files.sha256`,
`astra-acceptance.log` and 13 screenshots. Sol inspected all 13 and ran probes.

Complete defect list:

1. **Major, `lab.js:362`** — phase, 60% baseline work, readiness and confidence
   rendered only as text; no progress/meter semantics or visible segmented bars.
   Add accessible graphical work/phase/categorical readiness/evidence indicators
   to all treatments without inventing precise quality/confidence numbers. Assert
   actual semantics and visible geometry.
2. **Major, `lab.js:1180`** — rerender destroys focused element and generally focuses
   first autofocus target; keyboard response selection jumped to Studio overview.
   Confirming clear feedback leaves focus on hidden clear-confirm-yes. Preserve or
   deliberately advance action context; restore Clear feedback focus on confirmation.
3. **Major, `browser-test.cjs:248`** — keyboard/focus acceptance falsely positive:
   no Tab/Enter/Space/arrow/input-Enter or active-focus assertions. Add real common
   workflow keyboard tests, Board Map arrows/activation, Timeline arrows, Command
   Board filtering/Enter, rerender focus, visible focus and clear confirmation restore.
4. **Major, `lab.js:868,1000`** — Board Map and Timeline subtitles permanently say
   decision pending after committed/deferred/rejected. Derive all status labels
   from shared state and check no contradictory pending/open status after transitions.

Sol evidence: all six hashes matched; syntax and 1251-check acceptance passed;
390×844 probe found zero progress-like elements, focus at open-overview after
keyboard response activation and hidden clear-confirm-yes after feedback clear.
All five lower Board Map nodes were pointer-reachable by scrolling. Only approved
localStorage key; no fetch/beacon/WebSocket/interval simulation/production wiring.
Five treatments genuinely distinct; separate right rail, fixture/economic effects,
storage/export, isolation and Board Map reachability sound.

## Astra correction order — cycle 1 of maximum 2

Send all four findings to same Go worker. Interpret progress as 60% of **baseline**
work; phase is Production, readiness categorical At risk, confidence uses existing
Supported/Tentative labels—not fabricated percentages. Work bars need nonzero
visible geometry and accessible name/value; categorical indicators need visible
shape/text state, not color alone. These are required behavior, not redesign.
Keyboard focus must follow the current action (response/preview/confirm/cancel/
navigation), never dump to unrelated overview or hidden controls; no new shortcuts
that hijack review text fields. Full evidence and screenshot self-inspection required.
Sol re-review and Ponytail remain pending.
