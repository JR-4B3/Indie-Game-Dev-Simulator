# Game-design direction G0.1

**D1–D6 direction approved with the recorded qualifications.** Detailed mechanisms
and numerical ranges below remain proposals, not frozen balance. No worker may
choose missing rules or constants. [M1-K1](m1-kernel-contract.md) now freezes daily
clock/commands, finance arithmetic/grace and safe continuation for the kernel;
opening wealth/living cost remain explicit config, not a final gameplay-balance choice.
WP-UI-00 fixtures remain illustrative only, never kernel balance inputs.

## G1 — Player fantasy and core loop

Run a studio whose products, people and audience relationships acquire a history.
Survival is a constraint; informed commitment is the central skill. A lasting
boutique, a risky hit-driven studio, a service specialist, and a global publisher
must be distinct viable ambitions. Five stars is exceptional influence, not the
only victory condition. A good decision can lose; repeated sound judgment should
improve survival over many seeds. No invisible difficulty scaling to punish wealth.

Recommended setting: a fictional contemporary industry with plausible relationships,
not an exact reconstruction of named companies or future real-world history.
Active-play-only time is approved. Proposed engine quantum remains a day, but
there are no weekly turns, mandatory weekly planning screens or allocation resets.
Inspect and decide anytime; weekly/monthly summaries are reporting intervals only.
Pauseable time and optional advance-to-next-decision require an active visible
controlling browser session. Hidden/disconnected/closed games do not advance or
accumulate offline progression, and reconnect never fast-forwards absence.
First small release target: roughly 15–25 minutes of active play, not calendar
waiting. Long-form multi-session campaigns, adjustable speed, no forced five-star grind.

Loop: choose an opportunity → state a product thesis and budget → investigate the
important uncertainty → commit a team/plan → observe production and adapt → choose
when/how to launch → interpret audience/commercial results → support, expand,
pivot or retire → reinvest in people/capabilities/new work. Contract and study
choices compete with original development throughout, especially while solo.

### Strong, nonabsolute specialization (approved D1)

Studio identity emerges from practiced expertise, employee experience/interests,
trusted audience promises, reusable IP/technology and chosen capabilities. These
create meaningful advantages in familiar work and risk/opportunity costs in new
territory. No permanent class, arbitrary genre ban or universal global expertise
multiplier. Adjacent diversification can reuse some foundations; distant changes
need experiments, training/hiring, positioning and time to build a new audience.
Existing fans do not automatically transfer, employees can learn or disagree, and
IPs carry expectations rather than guaranteed sales. A studio can change identity
without a reset, but cannot become equally expert everywhere for free.

### Consequence and feedback map

```
Thesis / audience promise / business model / scope
     ↓                         ↓
Work needs + technical risks   Expected value, discoverability, price acceptance
     ↓                         ↓
Skills + allocations + tools   Research / prototype / audience sample
     ↓                         ↓
Throughput, debt, quality      Findings with confidence, bias, date and provenance
     └────────── decision to persist / cut / delay / pivot ───────────┘
                          ↓
             Actual product + promises + launch context
                          ↓
      Reach → purchase → play experience → refund / retain / recommend
                          ↓
         Cash / obligations / trust / employee response / prestige
                          ↓
       Support capacity and future audience, hiring, funding opportunities
```

Every numeric property must have an owner, update rule, observable evidence and
decision consumer. Remove anything without these four. Distinguish facts (cash,
contract terms), estimates (finish window), and unknowns (unreached audience fit).

## G2 — Projects and development pipeline

### Product identity

A project has a target player experience, primary audience, one or two optional
secondary audiences, 2–3 design pillars, genre/mechanical demands, presentation,
platform constraints and commercial promises. Genre is a demand profile, not a
secret correct theme pair. Curated feature packages change what the player is
building: e.g. handcrafted puzzles versus systemic simulation create different
work, QA and replayability demands. No individually simulated asset tickets.

Quality is multidimensional: core experience, usability/onboarding, expression
(art/audio/narrative as relevant), depth/content, and technical reliability.
Audience weights differ. Maintainability, adaptability, scope and debt are
production properties, not additional interchangeable review-score bonuses.
Reviews summarize experiences of different groups; no universal quality score
determines all sales or retention.

### Stage model

| Stage | Player commitment | Work/evidence | Exit/adaptation |
| --- | --- | --- | --- |
| Opportunity | Choose self-authored structured pitch, suggested idea, jam or commission | Rough audience signals, feasibility and runway | Shelve freely except time already spent; no need to wait for random idea |
| Discovery | Prioritize up to three consequential assumptions, choose studies/prototypes | Cheap biased observations; focused playable/technical experiments cost skilled time | Stop early, persist or revise; untested assumptions remain visibly uncertain |
| Preproduction | Commit pillars, feature packages, audience promise, work plan and budget envelope | Vertical slice, dependency and cost forecasts, initial playtests | Greenlight, scale down, fund more proof, or cancel |
| Production | Allocate team capacity and choose delivery order | Playable increments, team observations, integration failures and discoveries | Cut, resequence, refactor, change promise or request a pivot review |
| Validation | Decide coverage, launch readiness and release window | QA, accessibility/performance checks, external playtests, store/certification readiness | Fix, delay, accept disclosed risk, or return affected work to production |
| Launch | Commit price, stores, message, support reserve | Reviews, observed sales/refunds, onboarding failures, audience mix | Staged learning; launch is not a single random score roll |
| Operation / archive | Policies and time-bounded initiatives | Cohort retention, incidents, trust, contribution margin | Maintain, grow, pivot, hand off, sunset or archive |

Small projects compress stage work, not causal meaning. Jams can have a one-screen
brief and one key finding; do not impose a corporate approval ceremony on a solo dev.
Several projects become possible through real team allocation, not a prestige
permission toggle. Phases are explicit states; work completion does not silently
ship a game with unresolved release requirements.

### Progress, change and evidence

- Separate scope completed, quality evidence, and readiness. A green full work bar
  does not mean a good game. Denominator changes are annotated after scope changes;
  completed work is not secretly erased. Color always has a label/icon counterpart.
- Deterministic hidden reality plus seeded uncertain outcomes; evidence is sampled
  from actual product/team/audience conditions. Discovery does not reroll the game.
- An observation records subject/claim, method, sample/coverage, source bias,
  confidence category, timestamp, contradictions and actions it can inform.
  Early labels: unknown/tentative/supported/strong, not counterfeit precise odds.
- Repeating the same sample is correlated and has diminishing information value.
  Better tools expand coverage/precision; they do not buy positive findings.
- Important findings have actionable context: the symptom, suspected drivers,
  options with approximate cost/risk, and a link to the affected commitment.
  Quiet findings go to a digest; material deadline/survival decisions escalate.
- Change cost follows affected completed work, dependencies, team adaptability,
  debt and public promises. A pivot creates a revised plan, preserves history and
  explicitly writes off unusable work. Later changes are often costlier, not always wrong.
- Condition-driven event candidates, cooldowns, varied presentation and competing
  pressures replace a repeating random popup sequence. Rare external shocks have
  bounded, context-sensitive exposure and recorded causes, not universal ruin rolls.
- Postmortem: expected vs actual schedule/cost/audience/outcome, major turning points,
  supported contributing factors, conflicting evidence, unresolved uncertainty and
  reusable lessons. Never claim exact counterfactual causation from correlation.

Example: competitive multiplayer raises matchmaking/network/operations needs. A
prototype may expose weak onboarding, while testers praise cooperative sessions.
Cutting competitive mode can save future work but waste sunk network features and
break announced promises. Launching unchanged might attract initial interest yet
produce refunds and poor match availability. A cooperative pivot needs fresh
validation, not an automatic commercial bonus.

## G3 — People, solo work and organization

- Employees have separate skills (design, engineering, visual craft, audio,
  production, research/analysis, commercial/community, leadership), relevant
  experience domains, interests, work habits, ambitions and adaptability.
  Specialties refine an exercised skill; do not simulate hundreds of unused stats.
- Traits are a list with zero or more entries, never a forced positive/negative pair.
  All traits and their situational effects are visible. No hidden trait gotchas.
  Example: perfectionist notices integration issues but resists late scope cuts;
  it is not a universal quality multiplier plus a universal speed penalty.
- Compatibility arises from working relationships, role coverage and conflicting
  habits/incentives. Use relationships within teams/leads, not an all-company N²
  interpersonal matrix. Demographics never determine competence or traits.
- Work allocation is exclusive capacity accounting. Context switches, coordination,
  mentoring and support consume time. Overtime can help a short deadline but raises
  defects/exhaustion and eventually turnover; sustained crunch is not a best build.
- Learning needs suitable challenge and reflection. Training reserves learner and
  mentor time and may require money, facilities or access. Self-study is cheap and
  broad but slower; courses focus skills; mentorship transfers relevant expertise;
  applied rotations sacrifice current throughput for experience. No instant +all.
- Hiring exposes skills/traits and terms; uncertainty can concern relevant experience
  evidence and future team outcomes, not concealed punitive personality modifiers.
- Solo path: free jams (no entry fee, but living time), experiments, portfolio pieces,
  self-study, bounded contracts and small paid/free releases. Founder living costs
  are distinct from company payroll. Do not force free releases before selling.
- Scaling unit: own work time → named assignments in a small team → teams/leads
  with outcomes and capacity envelopes → departments/products with budgets and
  escalation policies. The founder can remain a specialist or become a leader.
  Facilities provide actual capacity/training/tool access, not office decoration buffs.

## G4 — Economy, market and audiences

Cash is the survival truth; contribution margin and full-cost profit answer
different questions. Account for setup, payroll/living draw, contractors, store
fees, refunds, marketing, hosting, licensing, financing, and simplified taxes.
Track cash timing separately from revenue and allocated product labor cost.
Never deduct attributed labor twice. Debt principal is financing, not an expense.

Work-for-hire trades time/IP freedom for bounded cash opportunities, with delivery,
client trust and opportunity costs. Debt buys runway under explicit obligations.
Publishing deals exchange financing/distribution for recoup, revenue share,
milestones and sometimes creative control. No free bailout or unlimited debt loop.

Market units: product, platform build, store listing, purchase/license, audience
owner, active player and payer are distinct. Cohort shopping money and attention
are finite; rivals face the same demand constraints, even if their production is
abstracted. Store purchases are not automatically distinct human players. Specify
cross-buy and repeat/platform purchases per policy, never accidentally duplicate owners.

Cohorts combine play motivations, time/budget constraints, platform access,
genre/mechanical preferences and tolerance for monetization/friction. Regional
economics, localization and device access affect reach. Avoid a giant demographic
cross-product; age/gender reporting is optional aggregate evidence only where
meaningful, never a deterministic taste or skill stereotype.

Acquisition follows awareness, promise/fit, price, store access, competition and
trust. Play then reveals product suitability: refunds, retention, recommendation,
reviews and willingness to buy again. Separate current sentiment, accumulated
studio/product trust and franchise expectations. Different cohorts can react in
opposite directions. Marketing amplifies promises; deception can buy launch
revenue and destroy future conversion. Good games can fail at positioning/reach.

Bounded seeded shocks represent uncertain competitors, timing and cultural response.
The same seed/date/rules/commands replay identically; the player does not see hidden
future shocks or exact utility formulas. Balance uses fixed-seed ensembles and
strategy comparisons, not arbitrary escalating costs proportional to player wealth.

## G5 — Analytics and mastery

Baseline: exact own cash/known costs and contractual store reports; rough personal
audience impressions. Never paywall basic accounting or existing employee traits.
Progression: storefront breakdowns → tagged playtests/surveys → segmentation and
localization research → consent-based telemetry/cohort analysis → analysts and
forecast comparison. Tool cost, analyst time, coverage, lag and sample bias matter.

Each analysis must answer a decision: which port to fund, what to fix, whether a
discount helps, which cohort churns, whether ads acquire profitable customers,
whether a sequel can carry promises, or whether support is affordable.
Metric views carry units, time window, product/store/platform scope, coverage,
source, lag, estimate status and uncertainty. Unknown is not zero. Missing old
telemetry does not become measured history after an upgrade; retrospective
estimates are labeled. Reconcile filters with totals or show excluded/unknown shares.

## G6 — Capabilities, research and prestige

Connected capability graph, not a universal XP shop. Nodes represent methods,
infrastructure, learned expertise or access; acquisition needs an appropriate mix
of demonstrated experience, paid work, staff time, equipment/partners and upkeep.
Edges state a real prerequisite; alternatives permit different strategies.
Cash cannot substitute for every prerequisite. Losing a mentor/tool can reduce
operating ability without deleting institutional knowledge. Do not make genre
choice a research license; research develops competence and production techniques.

Branches: craft/development, technology, production/QA, audience intelligence,
people/learning, commercial/publishing/marketing, finance, live operations,
leadership/organization. Example causal paths:

- Repeatable builds → automated tests → safe release train → delegated patch policy.
- Structured playtests → cohort sampling → retention instrumentation → live experiments.
- Mentoring practice → supported team leads → departmental budgets → portfolio governance.
- Reliable small releases → distribution relationships → co-publishing → platform partnerships.
- Community moderation + incident process + reliable online foundations → sustainable service operations.

Content expansion follows demonstrated decision variety, not a promised node count.
Show the long-term connected graph, emphasize reachable clusters, label AND/OR
dependencies and operational requirements. Include compact-studio paths with
deep craft/outsourcing, not only branches leading to larger headcount.

Prestige is a visible slowly moving 0.0–5.0 standing, reviewed quarterly with a
trend and dimension explanations; material scandals can act sooner. Money is not
a direct star purchase. Track demonstrated craft/catalogue, audience trust,
reliable delivery/organization, technological capability and industry reach.
Top ranges require breadth of influence, not endless grinding one score. Avoid
unlock flicker: earned access persists unless a stated contract/operating condition
is lost; prestige decline mainly changes new offers, expectations and terms.

| Stars (proposed ranges) | Narrative / opportunities | New pressures |
| --- | --- | --- |
| 0–0.9 | Unknown solo/micro studio; jams, small jobs, open storefronts | Living runway, limited reach, skill gaps |
| 1–1.9 | Credible independent; niche followers, better clients/collaborators | Consistency, support alongside next release |
| 2–2.9 | Established specialist/boutique; valuable catalogue, selected publisher/platform deals | Audience expectations, senior retention, multi-product capacity |
| 3–3.9 | Major developer/publisher; international releases, departments, financing | Coordination, simultaneous commitments, reputation exposure |
| 4–4.9 | Global portfolio company; major partnerships, ecosystem influence | Governance, brand contagion, anticompetitive/consumer scrutiny, operational exposure |
| 5.0 | Exceptional industry-shaping institution comparable in influence to platform holders | Stewardship of an ecosystem; dominance is neither permanent nor invulnerable |

A brilliant tiny studio can excel in craft and trust without global market power.
Show these dimensions so 2.5 stars does not mean mediocre games. Whether five
stars includes playable hardware/store operation is a user decision; recommendation:
strategic influence first, full platform-holder simulation postponed.

## G7 — Released products, live games and delegation

Every product has a lifecycle: launch learning, stabilization, sustained operation,
growth/renewal, decline and archive/sunset. Not every game needs all stages or
endless retention. A finite narrative game's healthy completion differs from a
competitive service losing its players. Catalogue sales can continue without servers.

Support is a policy (security/critical fixes, response targets, compatibility,
community commitments, budget ceiling), not a repeated generic update button.
Nonroutine initiatives have goals: improve onboarding, refactor matchmaking,
expand a campaign, create mod support, change business model, port, or run a season.
Each consumes capacity and targets diagnosed constraints with uncertain results.

Long life needs a renewable reason to return, accessible onboarding, adequate
population, maintainability, trust, sustainable monetization and operational skill.
Network effects have congestion/toxicity/content/competition counterpressures.
No evergreen flag, guaranteed sales floor or repeated-update immortality.
Unexpected cohort/mode traction can invite a costly prototype and pivot; related
versions share IP/history but explicitly manage audiences, promises and sunk work.

Leads receive a goal, staff/time allocation, spending authority, guardrails and
escalation thresholds. Their skill, habits and ambitions affect choices *within*
authority. Decisions and deviations have an audit trail. Uncertainty can cause a
bad call; delegation cannot secretly violate hard spend limits. Oversight consumes
leader/founder time, while overly narrow rules cause delay and missed opportunity.
Routine incidents aggregate; material incidents escalate with deadlines and fallback
policies. Critical survival/irreversible actions stop time by default.
Sunsetting is an explicit plan with contractual/community costs, not silent deletion.

## G8 — Difficulty, failure and deliberate postponement

Approved D5: normal play has reloadable rolling autosaves; manual saves remain a
proposed convenience. Explicit creation-time Ironman/permadeath is also a supported
direction, not quietly postponed. Normal bankruptcy preserves saves and offers a
separate new campaign. Ironman may irreversibly delete/invalidate only its own
campaign saves on definitive failure, under a separately frozen safety contract.
No retroactive mode conversion, cross-campaign cleanup, deletion on I/O failure,
or surprise restart. Crash recovery before legitimate failure must remain possible;
offline copies cannot be made tamper-proof by a local game. Liquidity trouble gives
dated obligations and costly restructuring choices before definitive failure.
Calibrate founder runway, contract alternatives and first-release scope jointly.
Do not keep the prototype's $100,000 start merely by inheritance.

First vertical slice deliberately includes few contrasting genres/features/cohorts,
one store/platform, solo work and small releases. Add breadth after causal depth
is proven. Planned later: multiple teams/stores/regions, specialists, connected
capabilities, live operations and portfolio leadership. Explicitly postponed pending
further approval: hardware manufacture, owned global storefronts, acquisitions,
public equity markets, detailed labor law/regulators, age/gender micro-segmentation,
procedural interpersonal drama, mod API and historical eras. These are not secretly
locked into the delivery roadmap.
