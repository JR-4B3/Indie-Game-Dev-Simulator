// WP-UI-01V3 — Board Map (variant 3).
//
// A radical non-page navigation: the surface is one spatial relationship board.
// Entity and evidence nodes are the only navigation; edges show influence,
// evidence and obligation links. A persistent "focus lens" beside the board
// inspects the current node's shared content pieces (same fixtures, same reducer
// effects, same HUD). There are no pages, tabs or route list.
//
// Keyboard: map nodes are native buttons (Enter/Space activate). Arrow keys move
// focus between map nodes using their actual geometry; the listener is attached
// to the map canvas element only (never window/document), so it cannot hijack
// text fields elsewhere. On narrow screens the board becomes a compact auto-fit
// grid with no canvas and no required panning; the "Jump to focus lens" button
// moves focus straight to the view heading and the critical actions.

import { F, el, part, planOf, statusText } from '../../shared.js';

export const metadata = {
  id: 3,
  name: 'Board Map',
  description: 'Spatial relationship board: entity, evidence and systems nodes linked by edges around a persistent focus lens. Arrow keys move between map nodes, Enter opens, and a compact no-pan narrow grid keeps the whole workflow reachable.',
};

const SVG_NS = 'http://www.w3.org/2000/svg';

const VIEW_TITLES = {
  overview: 'Studio overview',
  project: 'Signal Drift development',
  person: 'Mina Rao',
  product: 'Paper Harbor support obligation',
  postmortem: 'Paper Harbor postmortem',
  capabilities: 'Capability graph',
};

function confidenceWord(finding) {
  return finding.confidence.split(' ')[0].toUpperCase();
}

// Board layout in percent of the canvas. Coordinates are visual data only.
const NODES = [
  {
    id: 'overview', kind: 'STUDIO', view: 'overview',
    testid: 'open-overview', focus: 'map-overview',
    x: 3, y: 3, w: 40, h: 13,
    label: F.studio.name,
    sub: (state) => F.studio.stars + ' · ' + F.studio.staff + ' staff · cash ' + planOf(state).cashLabel,
  },
  {
    id: 'product', kind: 'SUPPORT', view: 'product',
    testid: 'open-product', focus: 'map-product',
    x: 57, y: 3, w: 40, h: 13,
    label: F.otherProduct.name,
    sub: () => F.otherProduct.obligationTitle,
  },
  {
    id: 'project', kind: 'ACTIVE PROJECT', view: 'project',
    testid: 'open-project', focus: 'map-project',
    x: 10, y: 24, w: 55, h: 20, primary: true,
    label: F.project.name,
    sub: () => F.project.phase + ' · ' + F.project.workLabel,
  },
  {
    id: 'person', kind: 'PEOPLE', view: 'person',
    testid: 'open-person', focus: 'map-person',
    x: 57, y: 50, w: 40, h: 11,
    label: F.person.name,
    sub: () => F.person.role,
  },
  {
    id: 'postmortem', kind: 'OUTCOME', view: 'postmortem',
    testid: 'open-postmortem', focus: 'map-postmortem',
    x: 57, y: 63, w: 40, h: 11,
    label: 'Paper Harbor postmortem',
    sub: () => 'planned vs actual · qualified factors',
  },
  {
    id: 'capabilities', kind: 'SYSTEMS', view: 'capabilities',
    testid: 'open-capabilities', focus: 'map-capabilities',
    x: 57, y: 76, w: 40, h: 11,
    label: 'Capabilities',
    sub: () => '2 owned · 2 available · 1 locked',
  },
  {
    id: 'evidence-f1', kind: 'EVIDENCE · ' + confidenceWord(F.findings[0]), view: 'project',
    focus: 'map-evidence-f1', evidence: true,
    x: 3, y: 50, w: 40, h: 10,
    label: 'Newcomer stall signal',
    sub: () => F.findings[0].date + ' · newcomer sample',
  },
  {
    id: 'evidence-f2', kind: 'EVIDENCE · ' + confidenceWord(F.findings[1]), view: 'project',
    focus: 'map-evidence-f2', evidence: true,
    x: 3, y: 62, w: 40, h: 10,
    label: 'Fan depth signal',
    sub: () => F.findings[1].date + ' · fan sample',
  },
  {
    id: 'evidence-f3', kind: 'EVIDENCE · ' + confidenceWord(F.findings[2]), view: 'project',
    focus: 'map-evidence-f3', evidence: true,
    x: 3, y: 74, w: 40, h: 10,
    label: 'Integration estimate',
    sub: () => F.findings[2].date + ' · unverified integration',
  },
];

const EDGES = [
  { from: 'overview', to: 'project', label: 'decision' },
  { from: 'product', to: 'project', label: 'competes' },
  { from: 'overview', to: 'product' },
  { from: 'project', to: 'person', label: 'lead' },
  { from: 'project', to: 'evidence-f1', label: 'evidence' },
  { from: 'project', to: 'evidence-f2' },
  { from: 'project', to: 'evidence-f3' },
  { from: 'product', to: 'postmortem', label: 'outcome' },
  { from: 'overview', to: 'capabilities' },
];

function nodeById(id) {
  for (let index = 0; index < NODES.length; index++) {
    if (NODES[index].id === id) return NODES[index];
  }
  return null;
}

function centerOf(node) {
  return { x: node.x + node.w / 2, y: node.y + node.h / 2 };
}

function svgNode(tag, attrs) {
  const node = document.createElementNS(SVG_NS, tag);
  Object.keys(attrs).forEach((key) => {
    if (attrs[key] === null || attrs[key] === undefined || attrs[key] === false) return;
    node.setAttribute(key, String(attrs[key]));
  });
  return node;
}

// ------------------------------------------------------------------- board

function buildEdgeLayer() {
  const layer = el('div', { class: 'v3-edge-layer', 'aria-hidden': 'true' });
  const svg = svgNode('svg', {
    class: 'v3-edges',
    viewBox: '0 0 100 100',
    preserveAspectRatio: 'none',
    focusable: 'false',
  });
  EDGES.forEach((edge) => {
    const from = centerOf(nodeById(edge.from));
    const to = centerOf(nodeById(edge.to));
    svg.append(svgNode('line', {
      class: 'v3-edge',
      x1: from.x, y1: from.y, x2: to.x, y2: to.y,
      'vector-effect': 'non-scaling-stroke',
    }));
  });
  layer.append(svg);
  EDGES.filter((edge) => edge.label).forEach((edge) => {
    const from = centerOf(nodeById(edge.from));
    const to = centerOf(nodeById(edge.to));
    layer.append(el('span', {
      class: 'v3-edge-label',
      style: 'left:' + ((from.x + to.x) / 2) + '%;top:' + ((from.y + to.y) / 2) + '%',
    }, edge.label));
  });
  return layer;
}

function buildNode(node, state) {
  const current = state.view === node.view && !node.evidence;
  const classes = ['v3-node'];
  if (node.primary) classes.push('is-primary');
  if (node.evidence) classes.push('is-evidence');
  if (current) classes.push('is-current');
  const attrs = {
    type: 'button',
    class: classes.join(' '),
    style: '--v3-x:' + node.x + ';--v3-y:' + node.y + ';--v3-w:' + node.w + ';--v3-h:' + node.h,
    'data-action': 'goto',
    'data-arg': node.view,
    'data-focus-key': node.focus,
    'aria-current': current ? 'true' : null,
  };
  if (node.testid) attrs['data-testid'] = node.testid;
  if (node.evidence) {
    attrs['aria-label'] = 'Open ' + node.label + ' (' + node.kind + ') in ' + F.project.name + ' context';
  }
  const children = [
    el('span', { class: 'v3-node-kind' }, node.kind),
    el('span', { class: 'v3-node-label' }, node.label),
    el('span', { class: 'v3-node-sub' }, node.sub(state)),
  ];
  if (node.primary) {
    children.push(el('span', { class: 'v3-node-status' }, statusText(state)));
    children.push(el('span', { class: 'v3-node-meter', 'aria-hidden': 'true' },
      el('span', { class: 'v3-node-meter-fill', style: 'width:' + F.project.workPercent + '%' })
    ));
  }
  return el('button', attrs, children);
}

function attachArrowKeys(canvas) {
  canvas.addEventListener('keydown', (event) => {
    const key = event.key;
    if (key !== 'ArrowUp' && key !== 'ArrowDown' && key !== 'ArrowLeft' && key !== 'ArrowRight') return;
    const nodes = Array.prototype.slice.call(canvas.querySelectorAll('button.v3-node'));
    const active = document.activeElement;
    if (nodes.indexOf(active) === -1) return;
    // While a map node holds focus, arrows belong to the board, not the page.
    event.preventDefault();
    const box = active.getBoundingClientRect();
    const cx = box.left + box.width / 2;
    const cy = box.top + box.height / 2;
    let best = null;
    let bestScore = Infinity;
    nodes.forEach((node) => {
      if (node === active) return;
      const rect = node.getBoundingClientRect();
      const dx = rect.left + rect.width / 2 - cx;
      const dy = rect.top + rect.height / 2 - cy;
      const forward = key === 'ArrowRight' ? dx : key === 'ArrowLeft' ? -dx : key === 'ArrowDown' ? dy : -dy;
      if (forward <= 12) return;
      const lateral = (key === 'ArrowRight' || key === 'ArrowLeft') ? Math.abs(dy) : Math.abs(dx);
      const score = forward + lateral * 2;
      if (score < bestScore) {
        bestScore = score;
        best = node;
      }
    });
    if (best) best.focus();
  });
}

function buildMap(state) {
  const map = el('section', { class: 'v3-map', role: 'group', 'aria-label': 'Studio relationship board' });
  map.append(el('div', { class: 'v3-map-tools' },
    el('span', { class: 'v3-map-title' }, 'Relation board'),
    el('span', { class: 'v3-map-hint' }, 'Arrow keys move · Enter opens'),
    el('button', {
      type: 'button',
      class: 'v3-jump',
      'data-action': 'goto',
      'data-arg': state.view,
      'data-testid': 'jump-lens',
      'data-focus-key': 'jump-lens',
    }, 'Jump to focus lens ↓')
  ));
  const canvas = el('div', { class: 'v3-map-canvas', 'data-testid': 'studio-map' });
  canvas.append(buildEdgeLayer());
  NODES.forEach((node) => canvas.append(buildNode(node, state)));
  attachArrowKeys(canvas);
  map.append(canvas);
  return map;
}

// -------------------------------------------------------------------- lens

function lensPieces(state) {
  switch (state.view) {
    case 'overview':
      return [
        part(state, 'summary'),
        part(state, 'studio'),
        el('p', { class: 'v3-board-note' },
          'Board link: ' + F.otherProduct.name + ' — ' + F.otherProduct.obligationTitle + '. ' + F.otherProduct.opportunityCost),
      ];
    case 'project':
      return [
        part(state, 'summary'),
        part(state, 'signals'),
        part(state, 'findings'),
        part(state, 'responses'),
        part(state, 'preview'),
        part(state, 'actions'),
        part(state, 'history'),
      ];
    case 'person':
      return [part(state, 'summary'), part(state, 'person')];
    case 'product':
      return [part(state, 'summary'), part(state, 'support')];
    case 'postmortem':
      return [part(state, 'summary'), part(state, 'postmortem')];
    case 'capabilities':
      return [part(state, 'summary'), part(state, 'capabilities')];
    default:
      return [part(state, 'summary')];
  }
}

function buildLens(state) {
  const lens = el('section', { class: 'v3-lens', 'aria-label': 'Focus lens' });
  lens.append(el('p', { class: 'v3-lens-kicker' }, 'Focus lens'));
  lens.append(el('h2', {
    class: 'v3-lens-title',
    'data-focus-key': 'view-title',
    tabindex: '-1',
  }, VIEW_TITLES[state.view] || state.view));
  lens.append(el('p', { class: 'v3-lens-status' }, statusText(state)));
  lens.append(el('div', { class: 'v3-lens-body' }, ...lensPieces(state)));
  return lens;
}

// ------------------------------------------------------------------ render

// dispatch is intentionally delegated to mount's [data-action] handling; it is
// accepted here to match the C-UI-S1 renderer seam exactly.
export function render(state, dispatch) {
  void dispatch;
  const root = el('div', {
    class: 'variant-3',
    'data-variant': '3',
    'data-view': state.view,
  });
  root.append(el('div', { class: 'v3-hud' }, part(state, 'hud')));
  const stage = el('div', { class: 'v3-stage' });
  stage.append(buildMap(state));
  stage.append(buildLens(state));
  root.append(stage);
  root.append(el('p', { class: 'v3-footnote' },
    'Board Map prototype · fixture state paused · nodes are navigation; edges show influence, evidence and obligations. No pages or tabs.'));
  return root;
}
