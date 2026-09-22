# Studio rewrite — Astra source of truth

Status: **M1-K1 kernel contracts frozen; WP-01/03 parallel, WP-02 after WP-01.
UI-lab work paused; rendered D7b gates production UI only, not core mechanics.**
Initiated 2026-09-10. Owner: Astra. User owns game-concept approval and rendered
UI direction approval. A disposable UI prototype lab is the required UI selection
artifact; recommendations below are not approved production decisions.

## Charter

Replace the prototype with a difficult, reactive studio simulation: formulate a
distinctive game, commit scarce time and money, learn from imperfect evidence,
adapt, release, and carry the commercial and human consequences into the next
decision. Growth changes how the player works, not just the size of the numbers.
Preserve useful visual identity and proven invariants, not accidental rules or
the existing architecture.

The core resources are cash/runway, skilled time, technical/product foundations,
audience relationships, and organizational attention. Information is a capability,
not a second currency. Every proposed system must change an available decision,
its opportunity cost, or the evidence used to make it.

## Documents

1. [Inventory and baseline](inventory.md): observed prototype, tests, preservation.
2. [Game-design direction](game-design.md): approved principles, proposed detail and exclusions.
3. [UI prototype selection lab](ui-concepts.md): DeepSeek builds five rendered
   variants from one Astra plan; user selection is required.
4. [Architecture proposal](architecture.md): boundaries and migration options.
5. [Contracts](contracts.md): frozen kernel overrides and remaining candidates.
6. [Roadmap and packages](roadmap.md): staged implementation and acceptance gates.
7. [Decision and review register](decisions.md): approval ledger and discovery audit.
8. [WP-UI-00](wp-ui-00.md): frozen disposable lab fixtures, interaction contract,
   scope, acceptance checks and cleanup plan.
9. [Controlled parallel lab packages](ui-parallel.md): shared foundation first,
   five concurrent isolated Go variant workers, then integration. Supersedes the
    original single-writer lab scope, retaining its behavior and user feedback.
10. [M1-K1 kernel contract](m1-kernel-contract.md): frozen clock/commands, cash,
    obligations, complete save schema and safe normal/Ironman continuation.
11. [M1 foundation packages](wp-m1-foundation.md): exact ownership, parallel
    scheduling, acceptance and reviews for WP-01/02/03 and tiny WP-KV.

## Protection and non-goals

- Existing tracked and untracked work is protected. No reset, checkout-overwrite,
  cleanup, deletion, configuration/default-agent change, or automatic commit.
- Existing terminal, browser, and v11 save behavior remain available until an
  approved replacement/retirement boundary. D3/D4 remove legacy-save compatibility
  and new CLI work from the rewrite; they do not authorize deleting existing work.
  D5 permits campaign-scoped save destruction only in explicitly chosen Ironman.
- Keep runtime Python standard-library-only plus local browser HTML/CSS/JS and
  assets, unless the user explicitly approves a dependency. Existing Windows
  curses exception is documented in the prototype README; do not expand it silently.
- No multiplayer, cloud/account service, external AI runtime, real-world market
  feeds, enterprise framework, engine plugin system, or per-consumer simulation.
- Production runtime, test, and frontend implementation must wait for their relevant
   frozen contracts. M1-K1 now authorizes core implementation; lab remains paused.

## Approval gates

The user has resolved D1–D6 as recorded in `decisions.md`: multiple identities with
strong soft specialization, active-play-only time, no legacy-save compatibility,
browser only, normal reloadable autosaves plus opt-in destructive Ironman, and the
local staged architecture. M1-K1 freezes the kernel schema and technical scenarios;
full project/market balance remains a later explicit specification.
A rendered/interactive UI prototype direction must be approved before production UI.
Core schemas/scenarios are frozen independently of that rendered decision, per
the user's kernel-first instruction; implementers still cannot invent mechanics.
This does not block a bounded, isolated, disposable prototype-lab package. Astra
defines one UX brief; DeepSeek implements exactly five interactive variants behind
a local 1–5 comparison and feedback interface. Approval of a rendered direction
does not approve future departures from it.

Implementation reviews: Go worker first; matching OpenRouter only for actual
provider/auth/quota/transport failure, recorded here. Scope/diff and acceptance
checks → Sol → explicitly load `ponytail-review` for Astra's separate simplicity
gate → corrections by the same worker → acceptance and Sol recheck. Maximum two
correctness correction cycles and one justified simplicity rewrite per package.
Sol and Ponytail never edit. Astra audits every milestone as a whole.
