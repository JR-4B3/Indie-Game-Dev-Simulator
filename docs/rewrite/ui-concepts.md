# UI prototype selection lab — rendered approval required

Status: **workflow and decision-centered UX foundation approved; no rendered
visual direction selected; WP-UI-00 authorized.** This document supersedes the earlier five prose-only concepts.
Those descriptions were not the review artifact the user requested and must not
be treated as candidates, approval, or implementation direction.

## Ownership

- Astra owns one coherent product/UX plan: player goals, information requirements,
  representative workflows, constraints, accessibility, and evaluation criteria.
- DeepSeek (`frontend-go`) owns the visual and interaction exploration inside that
  brief. It implements exactly five small, meaningfully different prototypes.
- The user reviews the rendered prototypes and may select one, reject all, combine
  elements, or give feedback for another iteration.
- Astra turns the user's rendered choice into the production interaction contract.
  No production UI implementation starts before that explicit approval.

## Shared prototype brief

The user supports the recommended decision-centered workspace foundation: keep
studio condition, product identity, the affected commitment and its evidence close
to the action. Growth changes the unit of control from personal work to team/product
leadership. This is one product plan, not a mandate for five reskins of one layout.
DeepSeek chooses five visual/navigation/control treatments within it, including at
least one non-page-based alternative. Do not resurrect the superseded prose list
as a fixed set to implement. The exact shared fixture and behavior contract is
[WP-UI-00](wp-ui-00.md); it is frozen for disposable prototype work only.

All five variants must demonstrate the same representative vertical workflow so
the comparison is meaningful rather than five unrelated feature sets:

1. inspect studio condition and identify a development decision needing attention;
2. enter an active game's development context without losing time/runway state;
3. inspect delayed findings and their confidence/history;
4. compare a proposed response with the project's current commitment;
5. commit, defer, or reject the response and see immediate acknowledgement;
6. move to another project/person/obligation and return without losing context;
7. inspect a compact outcome/postmortem view showing causal evidence without
   revealing hidden formulas as perfect truth.

Use representative static fixture data. The lab exists to evaluate interaction and
visual hierarchy, not to implement the replacement simulation or API prematurely.

## Required comparison experience

DeepSeek must build one local browser comparison page that provides:

- one selected prototype occupying the full game surface at a time;
- a fixed review-control rail on the right with numbered buttons 1–5; clicking a
  number immediately replaces the visible prototype with that variant;
- fast switching while preserving the current review step and feedback context;
- no side-by-side, split-screen, thumbnail-grid, or simultaneous variant display;
- a focused single-variant presentation on desktop and narrow screens;
- a comment/rating area for every variant and one overall feedback area in the
  fixed right review rail;
- local-only persistence and/or export to readable text or JSON—no external service;
- clear labels that these are disposable prototypes, not production screens;
- a reset control for fixture state and feedback;
- keyboard and pointer access to the demonstrated flow.

The five variants must meaningfully differ in navigation, hierarchy, control model,
and visual treatment. At least one should challenge page/tab navigation entirely.
They must not merely change colors around the same DOM structure.

## Shared visual constraints

- Retain the useful dark navy/lavender, blue, yellow, and green identity as a common
  lineage, while allowing each prototype to interpret it differently.
- Explore a stronger pixel character through portraits, icons, borders, frames,
  product emblems, and segmented meters—not blurry scaling or unreadable body text.
- Preserve the useful idea of colored development/phase bars, but their placement
  and interaction may be reconsidered.
- Keep text and data readable. Provide visible focus, semantic controls, non-color
  status cues, reduced-motion behavior, and a usable narrow presentation.
- Do not add a walking avatar, office-decoration mechanic, external asset/CDN, new
  runtime dependency, or production backend merely to make a prototype impressive.

## DeepSeek self-review evidence

Before presenting the lab, DeepSeek must:

1. exercise all five variants with browser tools;
2. capture and inspect screenshots at representative desktop and narrow sizes;
3. fix clipping, overlap, illegible hierarchy, unreachable controls, broken state,
   and comparison-shell problems;
4. verify feedback remains local/exportable and switching does not lose it;
5. provide launch instructions, screenshots, and a concise description of the real
   interaction differences—without choosing a winner for the user.

## Selection gate

The full-page, switchable prototype lab is the UI approval artifact. Text descriptions and screenshots may
help explain it but cannot replace direct interaction. After review, record the user's
selected or combined direction in `decisions.md`. Astra then specifies desktop/narrow
layouts, navigation, time/hold behavior, focus/error states, capability-tree behavior,
and production screenshot acceptance scenarios from that choice.
