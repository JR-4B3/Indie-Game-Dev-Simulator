// WP-UI-01V4 — Timeline Table.
// Commitment-agenda treatment: one fixed-epoch lane table (schedule records,
// product/people/support lanes) plus an inspection-only record desk built from
// the frozen shared content pieces. No scrubbing, no time advancement, no new
// scheduling actions or economy: temporal information is inspection only.
// Shared reducer/fixtures remain authoritative; this module only composes DOM.

import { F, el, part, planOf, statusText } from '../../shared.js';

export const metadata = {
  id: 4,
  name: 'Timeline Table',
  description: 'Fixed-epoch commitment lanes with estimate ranges and a record desk. Time is paused inspection, never a scrubber.',
};

const VIEW_TITLES = {
  overview: 'Studio overview',
  project: 'Signal Drift — commitment agenda',
  person: 'Mina Rao — commitment record',
  product: 'Paper Harbor — support obligation',
  postmortem: 'Paper Harbor — postmortem ledger',
  capabilities: 'Capability ledger',
};

const VIEW_SUBS = {
  overview: 'Studio condition and the current decision record.',
  project: 'Findings, responses and the decision record for Signal Drift.',
  person: 'Who carries the work; capacity and traits are inspection only.',
  product: 'The promised compatibility fix and what it competes with.',
  postmortem: 'Historical outcome with qualified factors and full accounting.',
  capabilities: 'Owned, available and locked capabilities; no unlocking here.',
};

const LANES = [
  {
    key: 'studio',
    view: 'overview',
    testId: 'open-overview',
    label: 'Studio',
    meta: F.studio.name + ' · ' + F.studio.staff + ' staff',
  },
  {
    key: 'signal-drift',
    view: 'project',
    testId: 'open-project',
    label: F.project.name,
    meta: F.project.phase + ' · ' + F.project.genre,
  },
  {
    key: 'mina',
    view: 'person',
    testId: 'open-person',
    label: F.person.name,
    meta: F.person.role,
  },
  {
    key: 'paper-harbor',
    view: 'product',
    testId: 'open-product',
    label: F.otherProduct.name,
    meta: F.otherProduct.kind,
  },
  {
    key: 'postmortem',
    view: 'postmortem',
    testId: 'open-postmortem',
    label: 'Paper Harbor postmortem',
    meta: 'Historical record · fixed',
  },
  {
    key: 'capabilities',
    view: 'capabilities',
    testId: 'open-capabilities',
    label: 'Capability ledger',
    meta: F.capabilities.nodes.length + ' nodes · inspection only',
  },
];

const LANE_BY_VIEW = {};
LANES.forEach((lane) => { LANE_BY_VIEW[lane.view] = lane; });

// Categorical records only. The single proportional visual in the lane table is
// the fixture-owned baseline-relative work percentage, whose denominator is
// stated in its own label; no other lane gets a proportion or gauge.
function workBand() {
  return el('div', { class: 'v4-bandrow' },
    el('span', { class: 'v4-band is-work', 'aria-hidden': 'true' },
      el('span', { class: 'v4-band-fill', style: 'width:' + F.project.workPercent + '%' })),
    el('span', { class: 'v4-band-label' }, 'Baseline-relative work · ' + F.project.workLabel)
  );
}

function recordRow(label, text) {
  return el('p', { class: 'v4-record' },
    el('strong', { class: 'v4-record-label' }, label),
    el('span', { class: 'v4-record-text' }, text)
  );
}

function chips(...items) {
  return el('div', { class: 'v4-chips' }, items);
}

function chip(text, extraClass) {
  return el('span', { class: 'v4-chip' + (extraClass ? ' ' + extraClass : '') }, text);
}

// The header title is derived from the shared state, never fixed: the fixture
// wording ("Unresolved …") is only valid while the decision is open.
function agendaTitle(state) {
  if (state.decisionStatus === 'open') return F.project.decisionTitle;
  return planOf(state).label;
}

function laneTrack(lane, state) {
  switch (lane.key) {
    case 'studio': {
      const plan = planOf(state);
      const committed = state.decisionStatus === 'committed';
      return [
        recordRow('Cash', plan.cashLabel + ' · runway ' + plan.runwayLabel + ' (rough cash ÷ burn)'),
        recordRow('Plan', (committed ? 'committed · ' : 'baseline · ') + plan.label),
        chips(
          chip(F.studio.staff + ' staff'),
          chip(F.studio.fansLabel),
          chip(F.studio.stars)
        ),
      ];
    }
    case 'signal-drift': {
      const committed = state.decisionStatus === 'committed';
      const plan = planOf(state);
      return [
        chips(
          chip(F.project.phase, 'is-open'),
          chip(statusText(state), committed ? 'is-ok' : 'is-open')
        ),
        workBand(),
        recordRow('Finish window', plan.estimate + ' · ' + plan.scopeLabel + ' · ' + (committed ? 'committed plan' : 'baseline plan')),
        recordRow('Agenda', agendaTitle(state)),
      ];
    }
    case 'mina':
      return [
        recordRow('Commitment', F.person.commitment),
        chips(
          chip(F.person.experience),
          chip('Methodical'),
          chip('Mentor')
        ),
      ];
    case 'paper-harbor':
      return [
        recordRow('Promise', 'Compatibility fix by 2 June (recorded promise date)'),
        recordRow('Reservation', '1 engineer-week reserved for the fix'),
        recordRow('Opportunity cost', 'Competes with ongoing Signal Drift production'),
        chips(chip('inspection only')),
      ];
    case 'postmortem': {
      const schedule = F.postmortem.rows.find((row) => row.id === 'schedule');
      return [
        recordRow('Recorded schedule', schedule
          ? schedule.expectedLabel + ' → ' + schedule.observedLabel
          : 'planned/actual fixture'),
        recordRow('Scope', 'Historical record only; no counterfactual claims'),
      ];
    }
    case 'capabilities':
      return [
        recordRow('Ledger', F.capabilities.nodes.length + ' nodes · owned / available / locked'),
        recordRow('Effect', 'No schedule or cash change; inspection only'),
      ];
    default:
      return [];
  }
}

function laneRow(lane, state, index) {
  const current = state.view === lane.view;
  return el('div', {
    class: 'v4-trow v4-lane' + (current ? ' is-current' : ''),
    role: 'row',
    'data-lane': lane.key,
  },
    el('div', { class: 'v4-cell-lane', role: 'cell' },
      el('button', {
        type: 'button',
        class: 'v4-lane-btn',
        'data-action': 'goto',
        'data-arg': lane.view,
        'data-testid': lane.testId,
        'data-lane-nav': lane.view,
        'data-focus-key': 'lane-' + lane.view,
        'aria-current': current ? 'true' : null,
      },
        el('span', { class: 'v4-lane-index', 'aria-hidden': 'true' }, String(index + 1).padStart(2, '0')),
        el('span', { class: 'v4-lane-text' },
          el('span', { class: 'v4-lane-name' }, lane.label),
          el('span', { class: 'v4-lane-meta' }, lane.meta)
        ),
        el('span', { class: 'v4-lane-go', 'aria-hidden': 'true' }, '▸')
      )
    ),
    el('div', { class: 'v4-cell-track', role: 'cell' }, laneTrack(lane, state))
  );
}

function laneTable(state) {
  return el('div', { class: 'v4-table', role: 'table', 'aria-label': 'Commitment lanes — schedule records and estimate ranges' },
    el('div', { class: 'v4-trow v4-thead', role: 'row' },
      el('span', { role: 'columnheader' }, 'Lane'),
      el('span', { role: 'columnheader' }, 'Window / schedule record')
    ),
    LANES.map((lane, index) => laneRow(lane, state, index))
  );
}

function sheetHead(state) {
  return el('header', { class: 'v4-sheethead' },
    el('div', { class: 'v4-sheet-title' },
      el('p', { class: 'v4-sheet-kicker' }, 'Disposable prototype · fixture ledger'),
      el('h2', { class: 'v4-sheet-heading' }, 'Timeline Table'),
      el('p', { class: 'v4-sheet-note' }, F.meta.pausedNote)
    ),
    el('div', { class: 'v4-epoch' },
      el('span', { class: 'v4-epoch-label' }, 'Fixed epoch'),
      el('strong', { class: 'v4-epoch-date' }, F.meta.dateLabel),
      el('span', { class: 'v4-epoch-note' }, 'Future windows are estimate ranges, not dates.')
    ),
    el('p', { class: 'v4-agenda-line' },
      el('span', { class: 'v4-agenda-label' }, 'Decision agenda: '),
      el('strong', {}, agendaTitle(state)),
      el('span', { class: 'v4-agenda-status' }, ' · ' + statusText(state))
    )
  );
}

function dayOf(dateText) {
  const match = /^(\d{1,2})/.exec(dateText || '');
  return match ? Number(match[1]) : 0;
}

function windowStrip(state) {
  const orderedFindings = F.findings.slice().sort((a, b) => dayOf(a.date) - dayOf(b.date));
  const evidence = el('div', { class: 'v4-window-col' },
    el('h3', { class: 'v4-window-title' }, 'Evidence window · recorded'),
    el('ol', { class: 'v4-window-list' }, orderedFindings.map((finding) => {
      const tentative = /tentative/i.test(finding.confidence);
      return el('li', { class: 'v4-evidence' },
        el('span', { class: 'v4-evidence-date' }, finding.date),
        el('span', { class: 'v4-evidence-shape', 'aria-hidden': 'true' }, tentative ? '◐' : '●'),
        el('span', { class: 'v4-evidence-text' }, finding.title + ' · ' + finding.confidence)
      );
    }))
  );

  const forward = el('div', { class: 'v4-window-col' },
    el('h3', { class: 'v4-window-title' }, 'Option windows · estimate ranges'),
    el('p', { class: 'v4-window-note' }, 'Fixture ranges in weeks; no end dates are derived.'),
    el('ul', { class: 'v4-window-list' }, F.responses.map((response) => {
      const selected = state.selectedResponseId === response.id;
      const committed = state.committedResponseId === response.id;
      const classes = 'v4-option'
        + (selected ? ' is-selected' : '')
        + (committed ? ' is-committed' : '');
      return el('li', { class: classes },
        el('span', { class: 'v4-option-name' }, response.label),
        el('span', { class: 'v4-option-meta' }, response.estimate + ' · ' + response.spendLabel + ' · ' + response.scopeLabel)
      );
    }))
  );

  return el('section', { class: 'v4-window', 'aria-label': 'Decision window' },
    evidence,
    el('div', { class: 'v4-window-now' },
      el('strong', {}, F.meta.dateLabel),
      el('span', {}, 'TODAY · time paused')
    ),
    forward
  );
}

function deskBody(state) {
  const nodes = [];
  if (state.view === 'overview') {
    nodes.push(part(state, 'studio'), part(state, 'summary'));
  } else if (state.view === 'project') {
    nodes.push(
      windowStrip(state),
      part(state, 'summary'),
      part(state, 'signals'),
      part(state, 'findings'),
      part(state, 'responses'),
      part(state, 'preview'),
      part(state, 'actions'),
      part(state, 'history')
    );
  } else if (state.view === 'person') {
    nodes.push(part(state, 'person'));
  } else if (state.view === 'product') {
    nodes.push(part(state, 'support'));
  } else if (state.view === 'postmortem') {
    nodes.push(part(state, 'postmortem'));
  } else if (state.view === 'capabilities') {
    nodes.push(part(state, 'capabilities'));
  }
  return nodes;
}

function desk(state) {
  const lane = LANE_BY_VIEW[state.view];
  return el('section', { class: 'v4-desk', 'aria-label': 'Record desk' },
    el('header', { class: 'v4-desk-head' },
      el('p', { class: 'v4-desk-kicker' }, 'Record · ' + (lane ? lane.label : state.view)),
      el('h2', { class: 'v4-desk-title', 'data-focus-key': 'view-title', tabindex: '-1' }, VIEW_TITLES[state.view] || state.view),
      el('p', { class: 'v4-desk-sub' }, VIEW_SUBS[state.view] || '')
    ),
    el('div', { class: 'v4-desk-body' }, deskBody(state))
  );
}

// Root-local keyboard navigation: Up/Down (and Left/Right) walk the six lane
// headers; Home/End jump to the first/last lane. Enter/Space still activates a
// lane natively through the mount's [data-action] delegation.
function attachLaneKeys(root) {
  const buttons = Array.from(root.querySelectorAll('[data-lane-nav]'));
  if (!buttons.length) return;
  root.addEventListener('keydown', (event) => {
    const index = buttons.indexOf(document.activeElement);
    if (index === -1) return;
    let next = null;
    if (event.key === 'ArrowDown' || event.key === 'ArrowRight') next = buttons[(index + 1) % buttons.length];
    else if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') next = buttons[(index - 1 + buttons.length) % buttons.length];
    else if (event.key === 'Home') next = buttons[0];
    else if (event.key === 'End') next = buttons[buttons.length - 1];
    else return;
    event.preventDefault();
    next.focus();
  });
}

export function render(state, dispatch) {
  const root = el('div', { class: 'variant-4', 'data-variant': '4' },
    part(state, 'hud'),
    sheetHead(state),
    laneTable(state),
    desk(state)
  );
  attachLaneKeys(root);
  return root;
}
