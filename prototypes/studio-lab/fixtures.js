// WP-UI-00 disposable fixture data.
// Illustrative, frozen fixture values from the work package. Not a simulation,
// not balanced game rules, not production data. No network and no code here.
(function () {
  'use strict';

  const meta = {
    dateLabel: '18 May 2031',
    pausedLabel: 'Prototype · fixture data · time paused',
    pausedNote: 'Fixture time is paused. This lab has no running clock, no autosave and no simulation.',
    feedbackNote: 'Fixture state resets on reload. Feedback and the selected variant are stored on this device only.',
  };

  const studio = {
    name: 'Northstar Works',
    stars: '1.5 stars',
    staff: 4,
    cash: 84000,
    cashLabel: '$84,000',
    monthlyBurn: 12000,
    monthlyBurnLabel: '$12,000',
    runwayLabel: '7.0 months',
    identity: 'Compact systems games — tactics, automation and readable rules.',
    shipped: 2,
    fans: 8400,
    fansLabel: '8,400 fans',
    runwayNote: 'Rough runway is cash ÷ burn, not a revenue forecast.',
    audiences: [
      { label: 'Systems players', strength: 'Supported', note: 'Current releases and playtest evidence support this audience.' },
      { label: 'Newcomers', strength: 'Tentative', note: 'Early evidence suggests friction; this audience is not yet supported.' },
    ],
    ipNote: 'Reusing an existing IP improves familiarity, but does not guarantee fit for a new audience.',
  };

  const baselinePlan = {
    id: 'hold',
    label: 'Keep current plan',
    spend: 0,
    spendLabel: '$0',
    cash: 84000,
    cashLabel: '$84,000',
    runwayLabel: '7.0 months',
    estimate: '8–11 weeks',
    scopePercent: 100,
    scopeLabel: '100% of baseline',
    tradeoff: 'Preserves schedule, newcomer friction unresolved',
  };

  const responses = [
    {
      id: 'simplify',
      label: 'Simplify branching',
      spend: 4000,
      spendLabel: '$4,000',
      cash: 80000,
      cashLabel: '$80,000',
      runwayLabel: '6.7 months',
      estimate: '7–9 weeks',
      scopePercent: 92,
      scopeLabel: '92% of baseline',
      tradeoff: 'Some core fans may miss depth; onboarding improvement unverified',
    },
    {
      id: 'onboarding',
      label: 'Build guided introduction',
      spend: 12000,
      spendLabel: '$12,000',
      cash: 72000,
      cashLabel: '$72,000',
      runwayLabel: '6.0 months',
      estimate: '10–13 weeks',
      scopePercent: 100,
      scopeLabel: '100% of baseline',
      tradeoff: 'Keeps depth, costs time/runway; integration untested',
    },
    baselinePlan,
  ];

  const project = {
    id: 'signal-drift',
    name: 'Signal Drift',
    genre: 'Tactics / automation',
    release: 'Small paid PC release',
    phase: 'Production',
    pillars: ['Readable systems', 'Short thoughtful sessions', 'Emergent solutions'],
    workPercent: 60,
    workLabel: '60% of baseline scope',
    readiness: 'At risk',
    readinessNote: 'At risk — follow-up validation needed',
    baselineEstimate: '8–11 weeks',
    baselineScopeLabel: '100% baseline',
    progressNote: 'Progress is baseline-relative even after a scope change, so cuts do not imply unexplained completed work.',
    qualityNote: 'Quality is not a new precise number in this fixture.',
    decisionTitle: 'Unresolved onboarding decision',
    decisionQuestion: 'Newcomer playtest findings conflict with a pillar that returning fans value. Compare a response before committing.',
  };

  const findings = [
    {
      id: 'f1',
      date: '15 May 2031',
      title: '8 of 12 new playtesters stalled at the first branching system.',
      confidence: 'Supported observation',
      method: 'Moderated playtest · small newcomer sample',
      source: 'Northstar playtest lab',
      implies: 'Implies an onboarding concern. It does not show that 67% of the whole market would fail.',
      history: 'Recorded 15 May 2031 · no revisions',
    },
    {
      id: 'f2',
      date: '12 May 2031',
      title: '5 of 6 returning fans enjoyed the branching depth.',
      confidence: 'Tentative audience inference',
      method: 'Existing-fan sample · biased toward current studio identity',
      source: 'Northstar community survey',
      implies: 'Cutting branches risks weakening a pillar for established fans.',
      history: 'Recorded 12 May 2031 · no revisions',
    },
    {
      id: 'f3',
      date: '17 May 2031',
      title: 'A guided introduction looks feasible, but integration is untested.',
      confidence: 'Tentative technical estimate',
      method: 'Employee review · requires validation',
      source: 'Mina Rao, production/engineering lead',
      implies: 'Feasibility is not evidence that integration will hold; plan validation work.',
      history: 'Recorded 17 May 2031 · no revisions',
    },
  ];

  const person = {
    id: 'mina',
    name: 'Mina Rao',
    role: 'Production / engineering lead',
    experience: '6 years systems experience',
    traits: [
      { name: 'Methodical', text: 'Catches integration risks; needs validation time' },
      { name: 'Mentor', text: 'Develops colleagues; coaching consumes delivery capacity' },
    ],
    commitment: 'Signal Drift integration — not idle or free extra capacity.',
    note: 'Traits are visible and shape work; this lab does not simulate hiring or training.',
  };

  const roster = [
    { name: 'Founder', role: 'Generalist', traits: 'No visible traits in this fixture' },
    { name: 'Artist', role: 'Art / direction', traits: 'Inventive — offers unusual directions; exploration needs time' },
    { name: 'Community specialist', role: 'Community', traits: 'No visible traits in this fixture' },
  ];

  const otherProduct = {
    id: 'paper-harbor',
    name: 'Paper Harbor',
    kind: 'Shipped finite puzzle game',
    obligationTitle: 'Compatibility fix promised by 2 June',
    obligation: 'One engineer-week reserved for the promised compatibility fix.',
    opportunityCost: 'That engineer-week competes with ongoing Signal Drift production.',
    note: 'No emergency modal and no budget change in this fixture; the promise is an inspection-only obligation.',
  };

  const postmortem = {
    heading: 'Paper Harbor — compact postmortem',
    note: 'Historical fixture. This is not the outcome of the Signal Drift decision.',
    rows: [
      { id: 'schedule', label: 'Planned / actual schedule', expected: '20 weeks', observed: '24 weeks', expectedLabel: 'planned 20 weeks', observedLabel: 'actual 24 weeks' },
      { id: 'budget', label: 'Planned / actual budget', expected: '$60,000', observed: '$68,000', expectedLabel: 'expected $60,000', observedLabel: 'actual $68,000' },
      { id: 'receipts', label: '90-day gross receipts', expected: '$100,000', observed: '$92,000', expectedLabel: 'expected $100,000', observedLabel: 'observed $92,000' },
    ],
    accounting: [
      { id: 'fees', label: 'Fees and refunds', value: '$22,000' },
      { id: 'net', label: 'Net receipts', value: '$70,000' },
      { id: 'contribution', label: 'Tracked contribution', value: '$2,000 after $68,000 tracked cost (not studio lifetime profit)' },
    ],
    factors: [
      { text: 'Playtests suggest simpler onboarding helped completion; small sample.', qualification: 'Suggestive, small sample' },
      { text: 'Late integration work contributed to schedule overrun (recorded work history).', qualification: 'Recorded work history' },
      { text: 'Store reach may explain weaker acquisition; evidence incomplete.', qualification: 'Evidence incomplete' },
    ],
    qualificationNote: 'Observed outcomes and qualified contributing factors only — no exact counterfactual causation.',
  };

  const capabilities = {
    note: 'Inspection only. No unlocking, no spending and no simulation effect in this lab.',
    nodes: [
      {
        id: 'repeatable-builds',
        name: 'Repeatable builds',
        state: 'Owned',
        detail: 'Studio already produces repeatable builds; this capability is available today.',
        cost: null,
        prereqs: [],
        tradeoff: 'No change here; it is the foundation for further tooling.',
      },
      {
        id: 'automated-tests',
        name: 'Automated tests',
        state: 'Available',
        detail: 'Detects regressions, not design fun.',
        cost: 'Reserve $6,000 and 2 engineer-weeks',
        prereqs: ['Repeatable builds'],
        tradeoff: 'Would compete for production capacity; inspection only in this lab.',
      },
      {
        id: 'safe-release-train',
        name: 'Safe release train',
        state: 'Locked',
        detail: 'Locked until its prerequisites are in place. Needs Automated tests AND Incident process.',
        cost: null,
        prereqs: ['Automated tests', 'Incident process'],
        tradeoff: 'Releasing more safely later may cost current production time now.',
      },
      {
        id: 'community-practice',
        name: 'Community practice',
        state: 'Owned',
        detail: 'Studio already has a practiced community relationship.',
        cost: null,
        prereqs: [],
        tradeoff: 'Foundation for incident response; no change in this lab.',
      },
      {
        id: 'incident-process',
        name: 'Incident process',
        state: 'Available',
        detail: 'Response preparation competes with current production.',
        cost: 'Reserve $3,000 and 1 lead-week',
        prereqs: ['Community practice'],
        tradeoff: 'Would compete for lead time; inspection only in this lab.',
      },
    ],
    edges: [
      ['repeatable-builds', 'automated-tests'],
      ['automated-tests', 'safe-release-train'],
      ['incident-process', 'safe-release-train'],
      ['community-practice', 'incident-process'],
    ],
  };

  const variants = [
    { id: 1, name: 'Ops Deck', summary: 'Persistent three-pane workspace: entity spine, focus pane, context inspector.' },
    { id: 2, name: 'Field Notes', summary: 'Editorial document with chapters, footnotes and inline disclosure.' },
    { id: 3, name: 'Board Map', summary: 'Spatial node board with a focus lens; no pages or tabs.' },
    { id: 4, name: 'Timeline Table', summary: 'Week ribbon and entity lanes with a detail desk.' },
    { id: 5, name: 'Command Board', summary: 'Command-first stream: type or click a command, read the output.' },
  ];

  globalThis.STUDIO_LAB_FIXTURES = {
    meta: meta,
    studio: studio,
    project: project,
    findings: findings,
    responses: responses,
    baselinePlan: baselinePlan,
    person: person,
    roster: roster,
    otherProduct: otherProduct,
    postmortem: postmortem,
    capabilities: capabilities,
    variants: variants,
  };
})();
