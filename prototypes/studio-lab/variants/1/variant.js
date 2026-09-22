// WP-UI-01V1 — Variant 1 "Ops Deck".
// Persistent operations workspace: entity spine (left), focus deck (centre) and a
// live ops readout (right) that keeps decision status, plan lineage, project pulse
// and confidence visible on every view.
//
// Reads the shared frozen state through the C-UI-S1 exports only. It never mutates
// state or fixtures, never writes storage and never registers global listeners:
// the one keydown listener is attached to the returned root, which mount replaces
// on every render.

import { F, el, part, planOf, statusText } from '../../shared.js';

export const metadata = {
  id: 1,
  name: 'Ops Deck',
  description: 'Persistent three-pane operations deck: entity spine, focus workspace, evidence watch and decision lineage readout.',
};

const SVG_NS = 'http://www.w3.org/2000/svg';

const PHASES = ['Opportunity', 'Discovery', 'Preproduction', 'Production', 'Validation', 'Launch', 'Operation'];

const VIEW_META = {
  overview: { title: 'Studio overview', crumb: 'DECK 00 · ROOT' },
  project: { title: 'Signal Drift — development', crumb: 'DECK 01 · ACTIVE PROJECT' },
  person: { title: 'Mina Rao', crumb: 'DECK 02 · PERSONNEL' },
  product: { title: 'Paper Harbor — support', crumb: 'DECK 03 · OBLIGATION' },
  postmortem: { title: 'Paper Harbor postmortem', crumb: 'DECK 04 · HISTORICAL' },
  capabilities: { title: 'Capability graph', crumb: 'DECK 05 · INSPECTION' },
};

const NAV_ITEMS = [
  { view: 'overview', label: 'Studio', testid: 'open-overview' },
  { view: 'project', label: 'Signal Drift', testid: 'open-project' },
  { view: 'person', label: 'Mina Rao', testid: 'open-person' },
  { view: 'product', label: 'Paper Harbor', testid: 'open-product' },
  { view: 'postmortem', label: 'Postmortem', testid: 'open-postmortem' },
  { view: 'capabilities', label: 'Capabilities', testid: 'open-capabilities' },
];

// Module-local pure visual data: chunky pixel marks, no assets and no fixture truth.
const PIXEL = {
  brand: {
    label: 'Northstar Works pixel emblem',
    palette: { Y: '#ffd166', L: '#b9a7ff' },
    rows: [
      '.....Y.....',
      '....YYY....',
      '.....L.....',
      '..Y..L..Y..',
      '...YLLLY...',
      'YYYYL.LYYYY',
      '...YLLLY...',
      '..Y..L..Y..',
      '.....L.....',
      '....YYY....',
      '.....Y.....',
    ],
  },
  person: {
    label: 'Pixel portrait mark',
    palette: { H: '#8f7dff', S: '#f2c9a0', E: '#0a0f1e', C: '#5b8cff' },
    rows: [
      '...HHHHHH...',
      '..HHHHHHHH..',
      '.HHSSSSSSHH.',
      '.HSSSSSSSSH.',
      '.HSESSSSESH.',
      '.HSSSSSSSSH.',
      '.HHSSSSSSHH.',
      '..HHSSSSHH..',
      '...CCCCCC...',
      '..CCCCCCCC..',
      '.CCC.CC.CCC.',
      'CC........CC',
    ],
  },
  product: {
    label: 'Pixel paper boat mark',
    palette: { M: '#b9a7ff', W: '#dbe4f5', B: '#5b8cff' },
    rows: [
      '.....M......',
      '....MW......',
      '...MWW......',
      '..MWWW......',
      '..MWWWW.....',
      '.MWWWWW.....',
      'BBBBBBBBBBBB',
      '.BBBBBBBBBB.',
    ],
  },
  postmortem: {
    label: 'Pixel outcome chart mark',
    palette: { B: '#5b8cff', G: '#5be3a5', Y: '#ffd166' },
    rows: [
      '............',
      '.......G....',
      '....B..G....',
      '....B..G....',
      '..Y.B..G....',
      '..Y.B..G....',
      '..Y.B..G..Y.',
      '..Y.B..G..Y.',
      '..Y.B..G..Y.',
      '............',
    ],
  },
  capabilities: {
    label: 'Pixel node grid mark',
    palette: { N: '#b9a7ff', B: '#5b8cff' },
    rows: [
      '............',
      '.NN..BB..NN.',
      '.NN..BB..NN.',
      '............',
      '.BB..NN..BB.',
      '.BB..NN..BB.',
      '............',
      '.NN..BB..NN.',
      '.NN..BB..NN.',
      '............',
    ],
  },
};

function pixelIcon(icon) {
  const rows = icon.rows;
  const width = rows.reduce((max, row) => Math.max(max, row.length), 0);
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'v1-pix');
  svg.setAttribute('viewBox', '0 0 ' + width + ' ' + rows.length);
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', icon.label);
  svg.setAttribute('shape-rendering', 'crispEdges');
  svg.setAttribute('focusable', 'false');
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length; x += 1) {
      const color = icon.palette[row[x]];
      if (!color) continue;
      const cell = document.createElementNS(SVG_NS, 'rect');
      cell.setAttribute('x', String(x));
      cell.setAttribute('y', String(y));
      cell.setAttribute('width', '1');
      cell.setAttribute('height', '1');
      cell.setAttribute('fill', color);
      svg.append(cell);
    }
  });
  return svg;
}

// ------------------------------------------------------------- state helpers

function responseById(id) {
  return id ? F.responses.find((response) => response.id === id) || null : null;
}

function statusTone(state) {
  if (state.decisionStatus === 'committed') return 'ok';
  if (state.decisionStatus === 'deferred') return 'warn';
  if (state.decisionStatus === 'rejected') return 'bad';
  if (state.previewFor) return 'go';
  return 'idle';
}

function shortStatus(state) {
  if (state.decisionStatus === 'committed') return 'Committed';
  if (state.decisionStatus === 'deferred') return 'Deferred';
  if (state.decisionStatus === 'rejected') return 'Rejected';
  return 'Open';
}

function navMeta(view, state) {
  switch (view) {
    case 'overview': return 'deck root';
    case 'project':
      if (state.decisionStatus === 'committed') return 'plan committed';
      if (state.decisionStatus === 'deferred') return 'deferred · reopen';
      if (state.decisionStatus === 'rejected') return 'risk remains';
      if (state.previewFor) return 'comparing';
      return state.selectedResponseId ? 'draft selected' : 'decision open';
    case 'person': return 'traits';
    case 'product': return 'promise 2 Jun';
    case 'postmortem': return 'outcomes';
    case 'capabilities': return 'inspect only';
    default: return '';
  }
}

function focusNote(state) {
  if (state.view === 'project') {
    if (state.decisionStatus === 'committed') return 'Committed: ' + planOf(state).label + '. The committed tradeoff and residual risk stay visible below.';
    if (state.decisionStatus === 'deferred') return 'Deferred — no plan change. Reopen the decision before another review.';
    if (state.decisionStatus === 'rejected') return 'Rejected — original risk remains. Reopen before weighing another response.';
    return F.project.decisionQuestion;
  }
  if (state.view !== 'overview') return '';
  if (state.decisionStatus === 'committed') return 'Decision committed: ' + planOf(state).label + '. The project deck shows the committed tradeoff.';
  if (state.decisionStatus === 'deferred') return 'Decision deferred — revisit before validation. The original risk remains.';
  if (state.decisionStatus === 'rejected') return 'Response rejected — original risk remains. Reopen the decision to weigh another response.';
  return 'One development decision is open on Signal Drift — inspect the evidence before committing.';
}

// -------------------------------------------------------------- composition

function plateBar(step, kicker) {
  return el('div', { class: 'v1-plate-bar' },
    step ? el('span', { class: 'v1-plate-num' }, step) : el('span', { class: 'v1-plate-dot', 'aria-hidden': 'true' }),
    el('span', { class: 'v1-plate-kicker' }, kicker)
  );
}

function plate(state, name, step, kicker) {
  const piece = part(state, name);
  if (!piece) return null;
  return el('div', { class: 'v1-plate v1-plate-' + name },
    plateBar(step, kicker),
    piece
  );
}

function crossLink(view, label) {
  return el('button', { type: 'button', class: 'v1-crosslink', 'data-action': 'goto', 'data-arg': view },
    el('span', { class: 'v1-crosslink-arrow', 'aria-hidden': 'true' }, '▶'),
    el('span', {}, label)
  );
}

function miniPhase() {
  const current = F.project.phase;
  const currentIndex = PHASES.indexOf(current);
  return el('div', { class: 'v1-mini', role: 'img', 'aria-label': 'Phase: ' + current },
    el('div', { class: 'v1-mini-head' }, el('span', {}, 'Phase'), el('strong', {}, current)),
    el('div', { class: 'v1-mini-cells' }, PHASES.map((phase, index) => el('span', {
      class: 'v1-mini-cell' + (index < currentIndex ? ' is-done' : '') + (index === currentIndex ? ' is-current' : ''),
      'aria-hidden': 'true',
    })))
  );
}

function miniWork() {
  const percent = F.project.workPercent;
  const filled = Math.round(percent / 10);
  return el('div', { class: 'v1-mini', role: 'img', 'aria-label': 'Baseline work completed: ' + percent + '%' },
    el('div', { class: 'v1-mini-head' }, el('span', {}, 'Baseline work'), el('strong', {}, percent + '%')),
    el('div', { class: 'v1-mini-cells' }, Array.from({ length: 10 }, (_, index) => el('span', {
      class: 'v1-mini-cell' + (index < filled ? ' is-done' : ''),
      'aria-hidden': 'true',
    })))
  );
}

function readinessChip() {
  return el('p', { class: 'v1-ready' },
    el('span', { class: 'v1-ready-shape', 'aria-hidden': 'true' }, '▲'),
    el('span', {}, F.project.readinessNote)
  );
}

function confidenceKey() {
  const supported = F.findings.filter((finding) => /supported/i.test(finding.confidence)).length;
  const tentative = F.findings.length - supported;
  return el('div', { class: 'v1-legend' },
    el('span', { class: 'v1-legend-item is-supported' }, el('i', { 'aria-hidden': 'true' }, '●'), supported + ' supported'),
    el('span', { class: 'v1-legend-item is-tentative' }, el('i', { 'aria-hidden': 'true' }, '◐'), tentative + ' tentative'),
    el('span', { class: 'v1-legend-note' }, 'categorical · no odds')
  );
}

function pipeline(state) {
  const selected = responseById(state.selectedResponseId);
  const committed = responseById(state.committedResponseId);
  const preview = responseById(state.previewFor);
  const committedLabel = committed ? committed.label : (selected ? selected.label : planOf(state).label);
  let compareMeta = 'No response selected · preview needs a selection';
  let compareTone = '';
  let decideMeta = 'Preview before deciding';
  let decideTone = '';
  if (state.decisionStatus === 'committed') {
    compareMeta = 'Committed: ' + committedLabel;
    compareTone = ' is-ok';
    decideMeta = 'Locked · recorded in the ledger';
    decideTone = ' is-ok';
  } else if (state.decisionStatus === 'deferred') {
    compareMeta = selected ? 'Deferred: ' + selected.label + ' · review paused' : 'Deferred — no response retained';
    compareTone = ' is-warn';
    decideMeta = 'Reopen before another review';
    decideTone = ' is-warn';
  } else if (state.decisionStatus === 'rejected') {
    compareMeta = selected ? 'Rejected: ' + selected.label + ' · review paused' : 'Rejected — no response retained';
    compareTone = ' is-bad';
    decideMeta = 'Reopen before another review';
    decideTone = ' is-bad';
  } else if (preview) {
    compareMeta = preview.label + ' · preview open';
    compareTone = ' is-active';
    decideMeta = 'Confirm, defer or reject';
    decideTone = ' is-active';
  } else if (selected) {
    compareMeta = selected.label + ' · selected, preview available';
    compareTone = ' is-ready';
  }
  const steps = [
    { num: 'E', title: 'Evidence', meta: F.findings.length + ' findings recorded', tone: ' is-ok' },
    { num: 'C', title: 'Compare', meta: compareMeta, tone: compareTone },
    { num: 'D', title: 'Decide', meta: decideMeta, tone: decideTone },
  ];
  return el('ol', { class: 'v1-pipe', 'aria-label': 'Decision pipeline' },
    steps.map((step) => el('li', { class: 'v1-pipe-step' + step.tone },
      el('span', { class: 'v1-pipe-num', 'aria-hidden': 'true' }, step.num),
      el('span', { class: 'v1-pipe-text' },
        el('strong', {}, step.title),
        el('small', {}, step.meta)
      )
    ))
  );
}

function lineage(state) {
  const base = F.baselinePlan;
  const preview = state.previewFor ? responseById(state.previewFor) : null;
  const selected = responseById(state.selectedResponseId);
  const target = preview || planOf(state);
  const rows = [
    ['Cash', base.cashLabel, target.cashLabel],
    ['Finish', base.estimate, target.estimate],
    ['Scope', base.scopeLabel, target.scopeLabel],
    ['Runway', base.runwayLabel, target.runwayLabel],
  ];
  let note = 'Baseline is unchanged. Select a response to weigh a tradeoff.';
  if (state.decisionStatus === 'committed') note = 'Committed plan is locked; the original baseline stays on the left.';
  else if (state.decisionStatus === 'deferred') note = 'Deferred — no plan change. Reopen the decision before a new comparison.';
  else if (state.decisionStatus === 'rejected') note = 'Rejected — original risk remains, no plan change. Reopen before a new comparison.';
  else if (preview) note = 'Preview only — committed data changes only after Confirm.';
  else if (selected) note = 'Draft selected: ' + selected.label + '. Preview before committing.';
  return el('div', { class: 'v1-lineage' },
    rows.map(([label, from, to]) => {
      const changed = from !== to;
      return el('div', { class: 'v1-lineage-row' + (changed ? ' is-changed' : '') },
        el('span', { class: 'v1-lineage-label' }, label),
        el('span', { class: 'v1-lineage-from' }, from),
        el('span', { class: 'v1-lineage-arrow', 'aria-hidden': 'true' }, changed ? '▶' : '='),
        el('span', { class: 'v1-lineage-to' }, to)
      );
    }),
    el('p', { class: 'v1-lineage-note' }, note)
  );
}

function reviewRow(state) {
  const selected = responseById(state.selectedResponseId);
  if (state.decisionStatus === 'committed') {
    const committed = responseById(state.committedResponseId);
    return ['Committed', (committed || selected || planOf(state)).label];
  }
  if (state.decisionStatus === 'deferred') return ['Deferred', selected ? selected.label : '— none retained'];
  if (state.decisionStatus === 'rejected') return ['Rejected', selected ? selected.label : '— none retained'];
  return ['Draft', selected ? selected.label : '— none selected'];
}

function committedReadout(state) {
  const plan = planOf(state);
  const rows = [
    ['Plan', plan.label],
    ['Cash', plan.cashLabel],
    ['Runway', plan.runwayLabel],
    ['Finish', plan.estimate],
    ['Scope', plan.scopeLabel],
    reviewRow(state),
  ];
  return el('dl', { class: 'v1-readout' }, rows.map(([label, value]) => el('div', { class: 'v1-readout-row' },
    el('dt', {}, label), el('dd', {}, value))));
}

function logReadout(state) {
  const last = state.history.length ? state.history[state.history.length - 1] : null;
  return el('div', { class: 'v1-block' },
    el('p', { class: 'v1-block-title' }, 'Decision log'),
    el('p', { class: 'v1-log-line' },
      el('strong', {}, String(state.history.length)),
      state.history.length === 1 ? ' entry · ' : ' entries · ',
      last ? last.kind : 'none yet'
    ),
    last ? el('p', { class: 'v1-log-last' }, last.text) : el('p', { class: 'v1-log-last' }, 'Preview and cancel are not logged; only confirm, defer and reject.')
  );
}

function spine(state) {
  return el('nav', { class: 'v1-spine', 'aria-label': 'Studio entities' },
    el('p', { class: 'v1-spine-title' }, 'Entity spine'),
    NAV_ITEMS.map((item) => el('button', {
      type: 'button',
      class: 'v1-spine-btn'
        + (state.view === item.view ? ' is-active' : '')
        + (item.view === 'project' ? ' v1-tone-' + statusTone(state) : ''),
      'data-action': 'goto',
      'data-arg': item.view,
      'data-testid': item.testid,
      'data-focus-key': 'nav-' + item.view,
      'aria-current': state.view === item.view ? 'true' : null,
    },
      el('span', { class: 'v1-spine-led', 'aria-hidden': 'true' }),
      el('span', { class: 'v1-spine-body' },
        el('span', { class: 'v1-spine-label' }, item.label),
        el('span', { class: 'v1-spine-meta' }, navMeta(item.view, state))
      )
    ))
  );
}

function viewHead(state) {
  const meta = VIEW_META[state.view] || VIEW_META.overview;
  const note = focusNote(state);
  return el('header', { class: 'v1-focus-head' },
    el('p', { class: 'v1-crumb' }, 'OPS DECK / ', meta.crumb),
    el('div', { class: 'v1-focus-title-row' },
      el('h2', { class: 'v1-view-title', tabindex: '-1', 'data-focus-key': 'view-title' }, meta.title),
      el('span', { class: 'v1-chip v1-tone-' + statusTone(state) },
        el('span', { class: 'v1-chip-led', 'aria-hidden': 'true' }),
        shortStatus(state)
      )
    ),
    note ? el('p', { class: 'v1-focus-note' }, note) : null
  );
}

function inspector(state) {
  return el('aside', { class: 'v1-inspector', 'aria-label': 'Ops readout' },
    el('div', { class: 'v1-panel' },
      plateBar(null, 'Ops readout'),
      el('div', { class: 'v1-lamp v1-tone-' + statusTone(state) },
        el('span', { class: 'v1-lamp-led', 'aria-hidden': 'true' }),
        el('span', { class: 'v1-lamp-text' }, statusText(state))
      ),
      pipeline(state),
      el('div', { class: 'v1-block' },
        el('p', { class: 'v1-block-title' }, 'Plan lineage'),
        lineage(state)
      ),
      el('div', { class: 'v1-block' },
        el('p', { class: 'v1-block-title' }, 'Committed readout'),
        committedReadout(state)
      ),
      el('div', { class: 'v1-block' },
        el('p', { class: 'v1-block-title' }, 'Project pulse'),
        miniPhase(),
        miniWork()
      ),
      el('div', { class: 'v1-block' },
        el('p', { class: 'v1-block-title' }, 'Confidence key'),
        confidenceKey()
      ),
      logReadout(state)
    )
  );
}

// ---------------------------------------------------------------- the views

function telemetryPlate() {
  return el('div', { class: 'v1-plate v1-plate-telemetry' },
    plateBar(null, 'Project telemetry'),
    el('p', { class: 'v1-tel-name' },
      el('strong', {}, F.project.name),
      el('span', {}, F.project.phase + ' · ' + F.project.release)
    ),
    miniPhase(),
    miniWork(),
    readinessChip(),
    el('p', { class: 'v1-note' }, F.project.progressNote),
    crossLink('project', 'Open development deck')
  );
}

function evidencePlate() {
  return el('div', { class: 'v1-plate v1-plate-evidence' },
    plateBar(null, 'Evidence watch'),
    el('ul', { class: 'v1-evidence' }, F.findings.map((finding) => {
      const supported = /supported/i.test(finding.confidence);
      return el('li', { class: 'v1-evidence-row' },
        el('span', { class: 'v1-evidence-glyph' + (supported ? ' is-supported' : ' is-tentative'), 'aria-hidden': 'true' }, supported ? '●' : '◐'),
        el('span', { class: 'v1-evidence-body' },
          el('strong', {}, finding.title),
          el('span', { class: 'v1-evidence-meta' }, finding.confidence + ' · ' + finding.date + ' · ' + finding.source)
        )
      );
    })),
    el('p', { class: 'v1-note' }, 'Confidence is categorical; no precise odds are claimed.'),
    crossLink('project', 'Open findings and responses')
  );
}

function obligationPlate() {
  return el('div', { class: 'v1-plate v1-plate-obligation' },
    plateBar(null, 'Obligations'),
    el('p', { class: 'v1-obligation-title' }, F.otherProduct.name + ' — ' + F.otherProduct.kind),
    el('p', { class: 'v1-obligation-line' }, F.otherProduct.obligationTitle + '. ' + F.otherProduct.obligation),
    el('p', { class: 'v1-note' }, F.otherProduct.opportunityCost),
    crossLink('product', 'Open support obligation')
  );
}

function entityHead(icon, kicker, title) {
  return el('div', { class: 'v1-entity-head' },
    el('span', { class: 'v1-entity-emblem' }, pixelIcon(icon)),
    el('span', { class: 'v1-entity-text' },
      el('p', { class: 'v1-kicker' }, kicker),
      el('strong', { class: 'v1-entity-title' }, title)
    )
  );
}

function overviewView(state) {
  return el('div', { class: 'v1-view v1-view-overview' },
    el('div', { class: 'v1-grid-2' },
      el('div', { class: 'v1-stack' },
        plate(state, 'summary', '01', 'Decision desk'),
        plate(state, 'studio', '02', 'Identity & people')
      ),
      el('div', { class: 'v1-stack' },
        telemetryPlate(),
        evidencePlate(),
        obligationPlate()
      )
    )
  );
}

function projectView(state) {
  return el('div', { class: 'v1-view v1-view-project' },
    plate(state, 'summary', '01', 'Decision desk'),
    el('div', { class: 'v1-grid-2 v1-project-grid' },
      el('div', { class: 'v1-stack' },
        plate(state, 'signals', '02', 'Telemetry'),
        plate(state, 'findings', '03', 'Evidence')
      ),
      el('div', { class: 'v1-stack' },
        plate(state, 'responses', '04', 'Response options'),
        plate(state, 'preview', null, 'Comparison slate'),
        plate(state, 'actions', '05', 'Commit controls')
      )
    ),
    plate(state, 'history', '06', 'Decision ledger')
  );
}

function personView(state) {
  return el('div', { class: 'v1-view v1-view-person' },
    entityHead(PIXEL.person, 'PERSONNEL FILE', F.person.role),
    plate(state, 'person', null, 'Traits and commitment'),
    crossLink('project', 'Return to Signal Drift development')
  );
}

function productView(state) {
  return el('div', { class: 'v1-view v1-view-product' },
    entityHead(PIXEL.product, 'SUPPORT OBLIGATION', F.otherProduct.name + ' — ' + F.otherProduct.kind),
    plate(state, 'support', null, 'Promise register'),
    crossLink('project', 'Return to production deck')
  );
}

function postmortemView(state) {
  return el('div', { class: 'v1-view v1-view-postmortem' },
    entityHead(PIXEL.postmortem, 'HISTORICAL RECORD', 'Outcomes are not the Signal Drift decision'),
    plate(state, 'postmortem', null, 'Outcome ledger')
  );
}

function capabilitiesView(state) {
  return el('div', { class: 'v1-view v1-view-capabilities' },
    entityHead(PIXEL.capabilities, 'INSPECTION ONLY', 'No unlocking or spending in this lab'),
    plate(state, 'capabilities', null, 'Graph, list & detail')
  );
}

function viewContent(state) {
  switch (state.view) {
    case 'project': return projectView(state);
    case 'person': return personView(state);
    case 'product': return productView(state);
    case 'postmortem': return postmortemView(state);
    case 'capabilities': return capabilitiesView(state);
    default: return overviewView(state);
  }
}

function topBar(state) {
  return el('div', { class: 'v1-top' },
    el('div', { class: 'v1-brand' },
      el('span', { class: 'v1-brand-mark' }, pixelIcon(PIXEL.brand)),
      el('span', { class: 'v1-brand-text' },
        el('strong', {}, F.studio.name),
        el('small', {}, 'OPS DECK · ' + F.studio.stars + ' · ' + F.studio.fansLabel)
      )
    ),
    part(state, 'hud')
  );
}

// ------------------------------------------------- keyboard control (root-local)

const SHORTCUTS = {
  '1': ['select-response', 'simplify'],
  '2': ['select-response', 'onboarding'],
  '3': ['select-response', 'hold'],
  p: ['preview'],
  c: ['confirm'],
  d: ['defer'],
  r: ['reject'],
  o: ['reopen'],
};

// Decision keys never hijack a focused control: native Enter/Space and any
// control-specific key behaviour stay untouched. Spine arrows are handled before
// this check because spine items are controls themselves.
const INTERACTIVE_SELECTOR = [
  'button', 'input', 'textarea', 'select', 'a[href]', 'summary',
  '[contenteditable="true"]',
  '[role="button"]', '[role="link"]', '[role="tab"]', '[role="menuitem"]',
  '[role="menuitemcheckbox"]', '[role="menuitemradio"]', '[role="radio"]',
  '[role="checkbox"]', '[role="switch"]', '[role="option"]', '[role="slider"]',
  '[role="spinbutton"]', '[role="combobox"]', '[role="textbox"]', '[role="searchbox"]',
].join(',');

function onKeyDown(event, root, dispatch) {
  if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
  const target = event.target;
  const element = target && target.closest ? target : null;
  const key = event.key;

  if (key === 'ArrowDown' || key === 'ArrowRight' || key === 'ArrowUp' || key === 'ArrowLeft' || key === 'Home' || key === 'End') {
    const button = element ? element.closest('.v1-spine-btn') : null;
    if (!button || !root.contains(button)) return;
    const buttons = Array.from(root.querySelectorAll('.v1-spine-btn'));
    const index = buttons.indexOf(button);
    if (index < 0 || buttons.length === 0) return;
    let nextIndex = index;
    if (key === 'Home') nextIndex = 0;
    else if (key === 'End') nextIndex = buttons.length - 1;
    else if (key === 'ArrowDown' || key === 'ArrowRight') nextIndex = (index + 1) % buttons.length;
    else nextIndex = (index - 1 + buttons.length) % buttons.length;
    event.preventDefault();
    buttons[nextIndex].focus();
    return;
  }

  // Suppress decision shortcuts and Escape from inside any interactive control.
  if (element && element.closest(INTERACTIVE_SELECTOR)) return;

  if (key === 'Escape') {
    if (root.querySelector('[data-testid="preview-panel"]')) {
      event.preventDefault();
      dispatch('cancel-preview');
    }
    return;
  }

  const shortcut = SHORTCUTS[key];
  if (shortcut) {
    event.preventDefault();
    dispatch(shortcut[0], shortcut[1]);
  }
}

// -------------------------------------------------------------------- render

export function render(state, dispatch) {
  const root = el('div', {
    class: 'variant-1',
    'data-variant': '1',
  },
    topBar(state),
    el('div', { class: 'v1-scroller' },
      el('div', { class: 'v1-deck' },
        spine(state),
        el('main', { class: 'v1-focus', 'aria-label': 'Focus deck' },
          viewHead(state),
          viewContent(state)
        ),
        inspector(state)
      )
    )
  );
  root.addEventListener('keydown', (event) => onKeyDown(event, root, dispatch));
  return root;
}
