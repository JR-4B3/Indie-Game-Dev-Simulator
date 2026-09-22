// WP-UI-01S harness boot.
// ?variant=N imports ./variants/N/variant.js + variant.css and mounts its renderer.
// ?core=1 (or no parameter) mounts a plain contract-test composition that is
// explicitly not a sixth candidate design. Invalid/missing variants show an honest
// unavailable message and never substitute another design.

import { part, el, mount } from './shared.js';

const surface = document.getElementById('game-surface');
const railMode = document.getElementById('rail-mode');

const VIEW_TITLES = {
  overview: 'Studio overview',
  project: 'Signal Drift development',
  person: 'Mina Rao',
  product: 'Paper Harbor support obligation',
  postmortem: 'Paper Harbor postmortem',
  capabilities: 'Capability graph',
};

const NAV = [
  ['overview', 'open-overview', 'Studio'],
  ['project', 'open-project', 'Signal Drift'],
  ['person', 'open-person', 'Mina Rao'],
  ['product', 'open-product', 'Paper Harbor'],
  ['postmortem', 'open-postmortem', 'Postmortem'],
  ['capabilities', 'open-capabilities', 'Capabilities'],
];

function unavailable(message) {
  surface.textContent = '';
  surface.append(el('div', { class: 'lab-unavailable', 'data-testid': 'variant-unavailable' }, message));
  if (railMode) railMode.textContent = 'Unavailable';
  globalThis.__labHarness = { mode: 'unavailable', message };
}

function coreNav(state) {
  return el('nav', { class: 'lab-nav', 'aria-label': 'Contract-test navigation' },
    NAV.map(([view, testId, label]) => el('button', {
      type: 'button',
      'data-action': 'goto',
      'data-arg': view,
      'data-testid': testId,
      'data-focus-key': 'nav-' + view,
      'aria-current': state.view === view ? 'true' : null,
    }, label))
  );
}

function viewTitle(view) {
  return el('h2', { class: 'lab-view-title', 'data-focus-key': 'view-title', tabindex: '-1' }, VIEW_TITLES[view] || view);
}

function coreRenderer(state) {
  const root = el('div', { class: 'core-composition', 'data-variant': 'core' });
  root.append(el('header', { class: 'core-banner' },
    el('strong', {}, 'Contract-test composition'),
    el('span', {}, 'shared foundation check — not a sixth candidate design'),
    el('button', { type: 'button', class: 'lab-button', 'data-action': 'reset', 'data-testid': 'reset-fixture', 'data-focus-key': 'reset-fixture' }, 'Reset fixture')
  ));
  root.append(part(state, 'hud'));
  root.append(coreNav(state));

  const main = el('div', { class: 'core-view' });
  main.append(viewTitle(state.view));
  switch (state.view) {
    case 'overview':
      main.append(part(state, 'studio'), part(state, 'summary'));
      break;
    case 'project':
      main.append(part(state, 'summary'), part(state, 'signals'), part(state, 'findings'), part(state, 'responses'), part(state, 'preview'), part(state, 'actions'), part(state, 'history'));
      break;
    case 'person':
      main.append(part(state, 'person'));
      break;
    case 'product':
      main.append(part(state, 'support'));
      break;
    case 'postmortem':
      main.append(part(state, 'postmortem'));
      break;
    case 'capabilities':
      main.append(part(state, 'capabilities'));
      break;
    default:
      break;
  }
  root.append(main);
  return root;
}

async function boot() {
  const params = new URLSearchParams(window.location.search);
  const variantParam = params.get('variant');

  if (variantParam !== null) {
    const variantId = Number(variantParam);
    if (!Number.isInteger(variantId) || variantId < 1 || variantId > 5) {
      unavailable('Variant "' + variantParam + '" is not one of 1–5.');
      return;
    }
    try {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = './variants/' + variantId + '/variant.css';
      document.head.append(link);
      const module = await import('./variants/' + variantId + '/variant.js');
      if (!module || typeof module.render !== 'function') {
        unavailable('Variant ' + variantId + ' does not export render(state, dispatch).');
        return;
      }
      const name = module.metadata && module.metadata.name ? module.metadata.name : 'Variant ' + variantId;
      if (railMode) railMode.textContent = 'Variant ' + variantId + ' — ' + name;
      const api = mount(surface, module.render);
      globalThis.__labHarness = {
        mode: 'variant-' + variantId,
        getState: api.getState,
        dispatch: api.dispatch,
        reset: api.reset,
        setRenderer: api.setRenderer,
      };
    } catch (error) {
      unavailable('Variant ' + variantId + ' is unavailable: ' + (error && error.message ? error.message : String(error)));
    }
    return;
  }

  if (railMode) railMode.textContent = 'Contract-test composition (not a candidate design)';
  const api = mount(surface, coreRenderer);
  globalThis.__labHarness = {
    mode: 'core',
    getState: api.getState,
    dispatch: api.dispatch,
    reset: api.reset,
    setRenderer: api.setRenderer,
  };
}

boot();
