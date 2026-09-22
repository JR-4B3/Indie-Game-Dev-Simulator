// WP-UI-01S shared foundation (C-UI-S1 / C-UI-S2).
// Disposable prototype core: fixture access, pure reducer, content pieces and the
// renderer seam. No storage, feedback, timers, network or game rules.
// Renderers read state, never mutate it.

function deepFreeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value);
    Object.getOwnPropertyNames(value).forEach((key) => deepFreeze(value[key]));
  }
  return value;
}

const SOURCE = globalThis.STUDIO_LAB_FIXTURES;
if (!SOURCE) throw new Error('shared.js requires fixtures.js to be loaded first');

export const F = deepFreeze(SOURCE);

const VIEWS = ['overview', 'project', 'person', 'product', 'postmortem', 'capabilities'];

function responseById(id) {
  return F.responses.find((response) => response.id === id) || null;
}

function capabilityById(id) {
  return F.capabilities.nodes.find((node) => node.id === id) || null;
}

function freezeState(state) {
  state.history.forEach((entry) => Object.freeze(entry));
  Object.freeze(state.history);
  return Object.freeze(state);
}

export function createState() {
  return freezeState({
    view: 'overview',
    selectedResponseId: null,
    previewFor: null,
    decisionStatus: 'open',
    committedResponseId: null,
    history: [],
    ack: '',
    selectedCapabilityId: 'automated-tests',
  });
}

export function planOf(state) {
  if (state.committedResponseId) {
    const committed = responseById(state.committedResponseId);
    if (committed) return committed;
  }
  return F.baselinePlan;
}

export function statusText(state) {
  if (state.decisionStatus === 'committed') return 'Committed';
  if (state.decisionStatus === 'deferred') return 'Deferred — revisit before validation';
  if (state.decisionStatus === 'rejected') return 'Response rejected — original risk remains';
  return 'Open — no response committed';
}

export function reduce(state, action, arg) {
  switch (action) {
    case 'goto':
      if (!VIEWS.includes(arg)) return state;
      return freezeState({ ...state, view: arg, ack: '' });

    case 'select-response': {
      if (state.decisionStatus !== 'open') return state;
      const response = responseById(arg);
      if (!response || state.selectedResponseId === response.id) return state;
      return freezeState({ ...state, selectedResponseId: response.id, previewFor: null, ack: '' });
    }

    case 'preview': {
      if (state.decisionStatus !== 'open' || !state.selectedResponseId) return state;
      if (state.previewFor === state.selectedResponseId) return state;
      return freezeState({ ...state, previewFor: state.selectedResponseId });
    }

    case 'cancel-preview':
      if (state.previewFor === null) return state;
      return freezeState({ ...state, previewFor: null });

    case 'confirm': {
      if (state.decisionStatus !== 'open') return state;
      if (!state.selectedResponseId || state.previewFor !== state.selectedResponseId) return state;
      const chosen = responseById(state.selectedResponseId);
      if (!chosen) return state;
      return freezeState({
        ...state,
        decisionStatus: 'committed',
        committedResponseId: chosen.id,
        previewFor: null,
        history: [...state.history, {
          kind: 'Committed',
          text: 'Committed “' + chosen.label + '”. Cash ' + chosen.cashLabel + '; runway ' + chosen.runwayLabel + '; finish ' + chosen.estimate + '; scope ' + chosen.scopeLabel + '.',
        }],
        ack: 'Decision committed: ' + chosen.label + '. Cash is now ' + chosen.cashLabel + ', runway ' + chosen.runwayLabel + '. Readiness remains At risk — follow-up validation needed.',
      });
    }

    case 'defer': {
      if (state.decisionStatus !== 'open' || !state.selectedResponseId) return state;
      const deferred = responseById(state.selectedResponseId);
      if (!deferred) return state;
      return freezeState({
        ...state,
        decisionStatus: 'deferred',
        previewFor: null,
        history: [...state.history, {
          kind: 'Deferred',
          text: 'Deferred “' + deferred.label + '” — revisit before validation. No cash or plan change.',
        }],
        ack: 'Decision deferred: revisit before validation. No cash or plan change; the original risk remains.',
      });
    }

    case 'reject': {
      if (state.decisionStatus !== 'open' || !state.selectedResponseId) return state;
      const rejected = responseById(state.selectedResponseId);
      if (!rejected) return state;
      return freezeState({
        ...state,
        decisionStatus: 'rejected',
        previewFor: null,
        history: [...state.history, {
          kind: 'Rejected',
          text: 'Rejected “' + rejected.label + '” — original risk remains. No cash or plan change.',
        }],
        ack: 'Response rejected: original risk remains. No cash or plan change.',
      });
    }

    case 'reopen': {
      if (state.decisionStatus !== 'deferred' && state.decisionStatus !== 'rejected') return state;
      return freezeState({
        ...state,
        decisionStatus: 'open',
        selectedResponseId: null,
        previewFor: null,
        history: [...state.history, {
          kind: 'Reopened',
          text: 'Reopened the ' + state.decisionStatus + ' decision for further review. No cash or plan change.',
        }],
        ack: 'Decision reopened for review. No cash or plan change; the earlier acknowledgement stays in history.',
      });
    }

    case 'select-capability': {
      const capability = capabilityById(arg);
      if (!capability) return state;
      return freezeState({ ...state, selectedCapabilityId: capability.id, view: 'capabilities', ack: '' });
    }

    case 'reset':
      return createState();

    default:
      return state;
  }
}

// ------------------------------------------------------------------- DOM helper

function appendAll(node, children) {
  children.forEach((child) => {
    if (child === null || child === undefined || child === false) return;
    if (Array.isArray(child)) { appendAll(node, child); return; }
    node.append(child && child.nodeType ? child : document.createTextNode(String(child)));
  });
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  const attributes = attrs || {};
  Object.keys(attributes).forEach((key) => {
    const value = attributes[key];
    if (value === null || value === undefined || value === false) return;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else node.setAttribute(key, value === true ? '' : String(value));
  });
  appendAll(node, children);
  return node;
}

function svgEl(tag, attrs) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.keys(attrs || {}).forEach((key) => node.setAttribute(key, String(attrs[key])));
  return node;
}

// ------------------------------------------------------------- content pieces

function phaseTrack() {
  const stages = ['Opportunity', 'Discovery', 'Preproduction', 'Production', 'Validation', 'Launch', 'Operation'];
  const currentIndex = stages.indexOf(F.project.phase);
  return el('div', { class: 'lab-phase', 'data-testid': 'phase-track', role: 'img', 'aria-label': 'Phase: ' + F.project.phase },
    el('span', { class: 'lab-phase-label' }, F.project.phase),
    el('ol', { class: 'lab-phase-steps' }, stages.map((stage, index) => el('li', {
      class: 'lab-phase-step' + (index === currentIndex ? ' is-current' : '') + (index < currentIndex ? ' is-done' : ''),
      'aria-current': index === currentIndex ? 'step' : null,
      'data-current': index === currentIndex ? 'true' : null,
    },
      el('span', { class: 'lab-phase-dot', 'aria-hidden': 'true' }, '■'),
      el('span', { class: 'lab-sr-only' }, stage)
    )))
  );
}

function workBar() {
  return el('div', { class: 'lab-workbar' },
    el('div', { class: 'lab-workbar-track', 'data-testid': 'work-bar-track' },
      el('div', {
        class: 'lab-workbar-fill',
        style: 'width:' + F.project.workPercent + '%',
        role: 'progressbar',
        'aria-label': 'Baseline work completed',
        'aria-valuemin': '0',
        'aria-valuemax': '100',
        'aria-valuenow': String(F.project.workPercent),
        'aria-valuetext': F.project.workLabel + ' completed',
        'data-testid': 'work-bar',
      })
    )
  );
}

function readinessCue() {
  return el('span', { class: 'lab-readiness', 'data-testid': 'readiness', role: 'img', 'aria-label': 'Readiness: ' + F.project.readiness },
    el('span', { class: 'lab-readiness-shape', 'aria-hidden': 'true' }, '▲'),
    el('span', { class: 'lab-readiness-text', 'data-testid': 'readiness-text' }, F.project.readinessNote)
  );
}

function confidenceCue(finding) {
  const category = /tentative/i.test(finding.confidence) ? 'tentative' : 'supported';
  return el('span', {
    class: 'lab-confidence',
    role: 'img',
    'data-confidence': category,
    'aria-label': 'Confidence: ' + finding.confidence,
    'data-testid': 'confidence-' + finding.id,
  },
    el('span', { class: 'lab-confidence-shape', 'aria-hidden': 'true' }, category === 'tentative' ? '◐' : '●'),
    el('span', { class: 'lab-confidence-text' }, finding.confidence)
  );
}

function hudPart(state) {
  const plan = planOf(state);
  return el('header', { class: 'lab-hud' },
    el('span', { class: 'lab-hud-paused' }, F.meta.pausedLabel),
    el('span', { class: 'lab-hud-item', 'data-testid': 'date' }, F.meta.dateLabel),
    el('span', { class: 'lab-hud-item', 'data-testid': 'metric-cash' }, 'Cash ' + plan.cashLabel),
    el('span', { class: 'lab-hud-item', 'data-testid': 'metric-runway' }, 'Runway ' + plan.runwayLabel)
  );
}

function studioPart() {
  const studio = F.studio;
  return el('section', { class: 'lab-studio' },
    el('h3', {}, 'Studio condition'),
    el('p', { class: 'lab-studio-name' }, studio.name + ' · ' + studio.stars + ' · ' + studio.staff + ' staff'),
    el('p', {}, studio.identity),
    el('p', { class: 'lab-note' }, studio.shipped + ' shipped releases · ' + studio.fansLabel + '. ' + studio.runwayNote),
    el('ul', { class: 'lab-audiences' }, studio.audiences.map((audience) => el('li', {},
      el('strong', {}, audience.label + ' — ' + audience.strength + ': '), audience.note))),
    el('p', { class: 'lab-note' }, studio.ipNote),
    el('h4', {}, 'People'),
    el('ul', { class: 'lab-people' },
      el('li', {},
        el('strong', {}, F.person.name + ' — ' + F.person.role + '. '),
        F.person.experience + '. ' + F.person.commitment),
      F.roster.map((member) => el('li', {}, el('strong', {}, member.name + ' — ' + member.role + '. '), member.traits))
    )
  );
}

function summaryPart(state) {
  const plan = planOf(state);
  const response = state.committedResponseId
    ? responseById(state.committedResponseId)
    : (state.selectedResponseId ? responseById(state.selectedResponseId) : null);
  let flag = F.project.decisionTitle;
  if (state.decisionStatus === 'committed') flag = 'Committed: ' + (response ? response.label : plan.label);
  else if (state.decisionStatus === 'deferred') flag = 'Deferred: ' + (response ? response.label : plan.label) + ' — revisit before validation';
  else if (state.decisionStatus === 'rejected') flag = 'Rejected: ' + (response ? response.label : plan.label) + ' — original risk remains';
  return el('section', { class: 'lab-summary' },
    el('p', { class: 'lab-kicker', 'data-testid': 'decision-flag' }, flag),
    el('p', { class: 'lab-status' },
      el('span', {}, 'Decision status: '),
      el('strong', { 'data-testid': 'decision-status' }, statusText(state))
    ),
    el('p', { class: 'lab-committed', 'data-testid': 'committed-plan' },
      'Committed plan: ' + plan.label + ' · cash ' + plan.cashLabel + ' · finish ' + plan.estimate + ' · scope ' + plan.scopeLabel)
  );
}

function signalsPart(state) {
  const progress = F.project;
  const plan = planOf(state);
  return el('section', { class: 'lab-signals' },
    el('h3', {}, 'Project signals'),
    el('p', { class: 'lab-project-name', 'data-testid': 'project-name' }, progress.name),
    el('p', { class: 'lab-note' }, progress.phase + ' · ' + progress.genre + ' · ' + progress.release),
    el('ul', { class: 'lab-pillars' }, progress.pillars.map((pillar) => el('li', { 'data-testid': 'pillar' }, pillar))),
    el('p', { class: 'lab-work-label', 'data-testid': 'work-progress' }, progress.workLabel),
    workBar(),
    phaseTrack(),
    el('p', { class: 'lab-readiness-line' }, readinessCue()),
    el('dl', { class: 'lab-stats' },
      el('div', { class: 'lab-stat' }, el('dt', {}, 'Finish estimate'), el('dd', { 'data-testid': 'finish-estimate' }, plan.estimate)),
      el('div', { class: 'lab-stat' }, el('dt', {}, 'Scope baseline'), el('dd', { 'data-testid': 'scope-baseline' }, plan.scopeLabel))
    ),
    el('p', { class: 'lab-note' }, progress.progressNote),
    el('p', { class: 'lab-note' }, progress.qualityNote)
  );
}

function findingsPart() {
  return el('section', { class: 'lab-findings' },
    el('h3', {}, 'Findings'),
    el('p', { class: 'lab-note' }, 'Confidence is categorical; no precise odds are claimed.'),
    F.findings.map((finding) => el('article', { class: 'lab-finding', 'data-testid': 'finding-' + finding.id },
      el('header', { class: 'lab-finding-head' },
        el('span', { class: 'lab-finding-date' }, finding.date),
        confidenceCue(finding)
      ),
      el('h4', { class: 'lab-finding-title' }, finding.title),
      el('p', { class: 'lab-finding-line' }, 'Source: ' + finding.source + ' · ' + finding.method),
      el('p', { class: 'lab-finding-line' }, finding.implies),
      el('p', { class: 'lab-finding-history' }, finding.history)
    ))
  );
}

function responsesPart(state) {
  const locked = state.decisionStatus !== 'open';
  return el('section', { class: 'lab-responses' },
    el('h3', {}, 'Responses'),
    F.responses.map((response) => {
      const selected = state.selectedResponseId === response.id;
      return el('button', {
        type: 'button',
        class: 'lab-response' + (selected ? ' is-selected' : ''),
        'data-action': 'select-response',
        'data-arg': response.id,
        'data-testid': 'response-' + response.id,
        'data-focus-key': 'response-' + response.id,
        'aria-pressed': selected ? 'true' : 'false',
        disabled: locked || null,
      },
        el('span', { class: 'lab-response-label' }, response.label),
        el('span', { class: 'lab-response-line' }, 'Immediate ' + response.spendLabel + ' · cash ' + response.cashLabel + ' · runway ' + response.runwayLabel),
        el('span', { class: 'lab-response-line' }, 'Finish ' + response.estimate + ' · scope ' + response.scopeLabel),
        el('span', { class: 'lab-response-tradeoff' }, 'Tradeoff: ' + response.tradeoff)
      );
    })
  );
}

function previewPart(state) {
  const response = state.previewFor ? responseById(state.previewFor) : null;
  if (!response) return null;
  const base = planOf(state);
  return el('section', { class: 'lab-preview', 'data-testid': 'preview-panel', 'aria-label': 'Response preview' },
    el('div', { class: 'lab-preview-head' },
      el('h3', { class: 'lab-preview-title' }, 'Preview — ' + response.label),
      el('button', { type: 'button', class: 'lab-button', 'data-action': 'cancel-preview', 'data-testid': 'cancel-preview', 'data-focus-key': 'cancel-preview' }, 'Cancel preview')
    ),
    el('p', { class: 'lab-note' }, 'Previewing or closing this panel does not change committed data.'),
    el('dl', { class: 'lab-compare' },
      el('div', { class: 'lab-compare-row' }, el('dt', {}, 'Cash'),
        el('dd', { 'data-testid': 'preview-baseline-cash' }, base.cashLabel + ' now'),
        el('dd', { 'data-testid': 'preview-proposed-cash' }, response.cashLabel + ' after · runway ' + response.runwayLabel)),
      el('div', { class: 'lab-compare-row' }, el('dt', {}, 'Finish estimate'),
        el('dd', { 'data-testid': 'preview-baseline-estimate' }, base.estimate + ' now'),
        el('dd', { 'data-testid': 'preview-proposed-estimate' }, response.estimate + ' after')),
      el('div', { class: 'lab-compare-row' }, el('dt', {}, 'Scope'),
        el('dd', { 'data-testid': 'preview-baseline-scope' }, base.scopeLabel + ' now'),
        el('dd', { 'data-testid': 'preview-proposed-scope' }, response.scopeLabel + ' after')),
      el('div', { class: 'lab-compare-row' }, el('dt', {}, 'Immediate spend'),
        el('dd', { 'data-testid': 'preview-spend' }, response.spendLabel)),
      el('div', { class: 'lab-compare-row' }, el('dt', {}, 'Residual tradeoff'),
        el('dd', { 'data-testid': 'preview-tradeoff' }, response.tradeoff))
    )
  );
}

function actionsPart(state) {
  const locked = state.decisionStatus !== 'open';
  const hasSelection = Boolean(state.selectedResponseId);
  const previewOpen = Boolean(state.previewFor) && state.previewFor === state.selectedResponseId;
  const reopens = state.decisionStatus === 'deferred' || state.decisionStatus === 'rejected';
  return el('section', { class: 'lab-actions', role: 'group', 'aria-label': 'Decision actions' },
    el('button', { type: 'button', class: 'lab-button', 'data-action': 'preview', 'data-testid': 'preview-button', 'data-focus-key': 'preview-button', disabled: locked || !hasSelection || null }, 'Preview response'),
    el('button', { type: 'button', class: 'lab-button is-primary', 'data-action': 'confirm', 'data-testid': 'confirm-button', 'data-focus-key': 'confirm-button', disabled: locked || !previewOpen || null }, 'Confirm'),
    el('button', { type: 'button', class: 'lab-button', 'data-action': 'defer', 'data-testid': 'defer-button', 'data-focus-key': 'defer-button', disabled: locked || !hasSelection || null }, 'Defer'),
    el('button', { type: 'button', class: 'lab-button', 'data-action': 'reject', 'data-testid': 'reject-button', 'data-focus-key': 'reject-button', disabled: locked || !hasSelection || null }, 'Reject'),
    reopens ? el('button', { type: 'button', class: 'lab-button is-warn', 'data-action': 'reopen', 'data-testid': 'reopen-button', 'data-focus-key': 'reopen-button' }, 'Reopen decision') : null,
    el('p', {
      class: 'lab-result',
      'data-testid': 'decision-result',
      role: 'status',
      'aria-live': 'polite',
      tabindex: '-1',
      'data-focus-key': 'decision-result',
    }, state.ack || '')
  );
}

function historyPart(state) {
  return el('section', { class: 'lab-history', 'aria-label': 'Decision history' },
    el('h3', {}, 'Decision history'),
    state.history.length
      ? el('ol', { class: 'lab-history-list' }, state.history.map((entry) => el('li', { 'data-testid': 'history-entry' },
        el('strong', {}, entry.kind), el('span', {}, ' ' + entry.text))))
      : el('p', { class: 'lab-history-empty', 'data-testid': 'history-empty' }, 'No decisions recorded yet.')
  );
}

function personPart() {
  return el('section', { class: 'lab-person' },
    el('h3', { 'data-testid': 'person-name' }, F.person.name),
    el('p', { class: 'lab-note' }, F.person.role + ' · ' + F.person.experience),
    el('ul', { class: 'lab-traits', 'data-testid': 'person-traits' }, F.person.traits.map((trait) => el('li', {},
      el('strong', {}, trait.name + ' — '), trait.text))),
    el('p', { 'data-testid': 'person-commitment' }, 'Current commitment: ' + F.person.commitment),
    el('p', { class: 'lab-note' }, F.person.note)
  );
}

function supportPart() {
  const product = F.otherProduct;
  return el('section', { class: 'lab-support' },
    el('h3', {}, product.name + ' — ' + product.kind),
    el('p', { 'data-testid': 'support-obligation' }, product.obligationTitle + '. ' + product.obligation),
    el('p', {}, 'Opportunity cost: ' + product.opportunityCost),
    el('p', { class: 'lab-note' }, product.note)
  );
}

function postmortemPart() {
  const postmortem = F.postmortem;
  return el('section', { class: 'lab-postmortem', 'data-testid': 'postmortem' },
    el('h3', {}, postmortem.heading),
    el('p', { class: 'lab-note' }, postmortem.note),
    el('ul', { class: 'lab-pm-rows' }, postmortem.rows.map((row) => el('li', { 'data-testid': 'pm-' + row.id },
      el('strong', {}, row.label + ': '), row.expectedLabel + ' → ' + row.observedLabel))),
    el('ul', { class: 'lab-pm-rows' }, postmortem.accounting.map((row) => el('li', { 'data-testid': 'pm-' + row.id },
      el('strong', {}, row.label + ': '), row.value))),
    el('h4', {}, 'Qualified contributing factors'),
    el('ul', { class: 'lab-factors' }, postmortem.factors.map((factor) => el('li', { 'data-testid': 'factor' },
      factor.text + ' (' + factor.qualification + ')'))),
    el('p', { class: 'lab-note' }, postmortem.qualificationNote)
  );
}

function capabilityGraph() {
  const positions = {
    'repeatable-builds': { x: 20, y: 30 },
    'automated-tests': { x: 250, y: 30 },
    'safe-release-train': { x: 480, y: 30 },
    'community-practice': { x: 20, y: 150 },
    'incident-process': { x: 250, y: 150 },
  };
  const width = 180;
  const height = 70;
  const graph = svgEl('svg', {
    viewBox: '0 0 720 240',
    class: 'lab-cap-svg',
    role: 'img',
    'aria-label': 'Capability connections: Repeatable builds to Automated tests to Safe release train; Community practice to Incident process to Safe release train.',
    'data-testid': 'capability-graph',
  });
  F.capabilities.edges.forEach((edge) => {
    const from = positions[edge[0]];
    const to = positions[edge[1]];
    if (!from || !to) return;
    graph.append(svgEl('line', {
      x1: from.x + width, y1: from.y + height / 2,
      x2: to.x, y2: to.y + height / 2,
      stroke: 'currentColor',
      'stroke-width': '2', 'stroke-dasharray': '5 4',
    }));
  });
  F.capabilities.nodes.forEach((node) => {
    const position = positions[node.id];
    if (!position) return;
    const group = svgEl('g', {});
    group.append(svgEl('rect', { x: position.x, y: position.y, width: width, height: height, rx: 4 }));
    const label = svgEl('text', { x: position.x + 10, y: position.y + 28 });
    label.textContent = node.name;
    const state = svgEl('text', { x: position.x + 10, y: position.y + 50, class: 'lab-cap-svg-state' });
    state.textContent = node.state + (node.id === 'safe-release-train' ? ' — needs both' : '');
    group.append(label, state);
    graph.append(group);
  });
  return graph;
}

function capabilitiesPart(state) {
  const selected = capabilityById(state.selectedCapabilityId) || F.capabilities.nodes[0];
  return el('section', { class: 'lab-capabilities' },
    el('h3', {}, 'Capability inspection'),
    el('p', { class: 'lab-note' }, F.capabilities.note),
    capabilityGraph(),
    el('div', { class: 'lab-cap-columns' },
      el('div', {},
        el('h4', {}, 'Keyboard-readable list'),
        el('ul', { class: 'lab-cap-list', 'data-testid': 'capability-list' }, F.capabilities.nodes.map((node) => el('li', {},
          el('button', {
            type: 'button',
            class: 'lab-cap-item' + (node.id === selected.id ? ' is-selected' : ''),
            'data-action': 'select-capability',
            'data-arg': node.id,
            'data-testid': 'cap-list-' + node.id,
            'data-focus-key': 'cap-' + node.id,
            'aria-pressed': node.id === selected.id ? 'true' : 'false',
          },
            el('strong', {}, node.name), el('span', {}, ' — ' + node.state),
            el('span', { class: 'lab-cap-prereq' }, node.prereqs.length ? ' · requires ' + node.prereqs.join(' AND ') : ' · no prerequisites')
          ))
        ))
      ),
      el('div', { class: 'lab-cap-detail', 'data-testid': 'cap-detail' },
        el('h4', {}, selected.name + ' — ' + selected.state),
        el('p', {}, selected.detail),
        selected.cost ? el('p', { 'data-testid': 'cap-cost' }, selected.cost) : null,
        selected.state === 'Locked' ? el('p', { 'data-testid': 'cap-and' }, 'Requires ' + selected.prereqs.join(' AND ') + '.') : null,
        el('p', { class: 'lab-note' }, selected.tradeoff),
        el('p', { class: 'lab-note', 'data-testid': 'cap-note' }, F.capabilities.note)
      )
    )
  );
}

export function part(state, name) {
  switch (name) {
    case 'hud': return hudPart(state);
    case 'studio': return studioPart();
    case 'summary': return summaryPart(state);
    case 'signals': return signalsPart(state);
    case 'findings': return findingsPart();
    case 'responses': return responsesPart(state);
    case 'preview': return previewPart(state);
    case 'actions': return actionsPart(state);
    case 'history': return historyPart(state);
    case 'person': return personPart();
    case 'support': return supportPart();
    case 'postmortem': return postmortemPart();
    case 'capabilities': return capabilitiesPart(state);
    default: throw new Error('Unknown part: ' + name);
  }
}

// -------------------------------------------------------------------- mounting

// Focus is owned by mount; keys are only meaningful inside the mounted surface.

function focusIntent(action, state) {
  switch (action) {
    case 'select-response': return state.selectedResponseId ? 'response-' + state.selectedResponseId : null;
    case 'preview': return 'cancel-preview';
    case 'cancel-preview': return 'preview-button';
    case 'confirm': return 'decision-result';
    case 'defer':
    case 'reject': return 'reopen-button';
    case 'reopen': return 'decision-result';
    case 'goto':
    case 'reset': return 'view-title';
    case 'select-capability': return 'cap-' + state.selectedCapabilityId;
    default: return null;
  }
}

export function mount(surface, renderer) {
  if (!surface || typeof renderer !== 'function') {
    throw new Error('mount(surface, renderer) requires a surface element and a renderer function');
  }

  let current = createState();
  let render = renderer;
  let destroyed = false;

  function surfaceFocusKey() {
    const active = document.activeElement;
    if (!active || !active.closest || !surface.contains(active)) return null;
    const holder = active.closest('[data-focus-key]');
    return holder ? holder.getAttribute('data-focus-key') : null;
  }

  function isUsableTarget(node, root) {
    let element = node;
    const boundary = root.parentElement || surface;
    while (element && element !== boundary) {
      if (element.hidden) return false;
      if (element.hasAttribute) {
        if (element.hasAttribute('inert') || element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true') return false;
      }
      const style = window.getComputedStyle(element);
      if (style.display === 'none' || style.visibility === 'hidden' || style.visibility === 'collapse') return false;
      element = element.parentElement;
    }
    const rect = node.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    return true;
  }

  function usableTarget(root, key) {
    if (!key) return null;
    const node = root.querySelector('[data-focus-key="' + key + '"]');
    return node && isUsableTarget(node, root) ? node : null;
  }

  function renderNow(intent, previousKey, preparedRoot) {
    const hadFocus = surface.contains(document.activeElement);
    surface.textContent = '';
    const root = preparedRoot || render(current, api.dispatch);
    if (!(root instanceof HTMLElement)) throw new Error('renderer must return one HTMLElement');
    if (!root.hasAttribute('tabindex')) root.setAttribute('tabindex', '-1');
    surface.append(root);
    if (!intent && !previousKey && !hadFocus) return root;
    let target = usableTarget(root, intent)
      || usableTarget(root, previousKey)
      || usableTarget(root, 'view-title')
      || root;
    try { target.focus({ preventScroll: true }); } catch (err) { /* focus is best-effort */ }
    if (document.activeElement !== target) {
      const fallback = usableTarget(root, 'view-title') || root;
      try { fallback.focus({ preventScroll: true }); } catch (err) { /* focus is best-effort */ }
      target = fallback;
    }
    if (typeof target.scrollIntoView === 'function') {
      try { target.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch (err) { /* scroll is best-effort */ }
    }
    return root;
  }

  function onClick(event) {
    if (destroyed) return;
    const target = event.target.closest ? event.target.closest('[data-action]') : null;
    if (!target || !surface.contains(target) || target.hasAttribute('disabled')) return;
    api.dispatch(target.getAttribute('data-action'), target.getAttribute('data-arg'));
  }

  const api = {
    getState() { return current; },
    dispatch(action, arg) {
      const previousKey = surfaceFocusKey();
      const next = reduce(current, action, arg);
      if (next === current) return current;
      current = next;
      renderNow(focusIntent(action, current), previousKey);
      return current;
    },
    setRenderer(nextRenderer) {
      if (typeof nextRenderer !== 'function') throw new Error('setRenderer requires a renderer function');
      const root = nextRenderer(current, api.dispatch);
      if (!(root instanceof HTMLElement)) throw new Error('renderer must return one HTMLElement');
      render = nextRenderer;
      renderNow(null, surfaceFocusKey(), root);
      return api;
    },
    reset() {
      current = createState();
      renderNow(null, surfaceFocusKey());
      return api;
    },
    destroy() {
      destroyed = true;
      surface.removeEventListener('click', onClick);
      surface.textContent = '';
    },
  };

  surface.addEventListener('click', onClick);
  renderNow(null, null);
  return api;
}
