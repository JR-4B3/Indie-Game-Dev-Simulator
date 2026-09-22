// WP-UI-01V2 — Field Notes (variant 2), disposable prototype renderer.
//
// Visual direction: a readable editorial dossier on ruled paper. The studio
// decision is a numbered case file: exhibits (signals, findings) and the
// disposition register sit side by side on a wide sheet; the register folds
// open by default and footnote-style <details> carry sources and notes.
// All state arrives from the shared mount; this module only composes shared
// parts, styles its own root and never mutates fixtures or state.

import { F, el, part, planOf, statusText } from '../../shared.js';

export const metadata = {
  id: 2,
  name: 'Field Notes',
  description:
    'Editorial dossier on paper: numbered files, an evidence/disposition spread and footnote-style disclosure around the decision register.',
};

const NAV = [
  ['overview', 'open-overview', 'Studio'],
  ['project', 'open-project', 'Signal Drift'],
  ['person', 'open-person', 'Mina Rao'],
  ['product', 'open-product', 'Paper Harbor'],
  ['postmortem', 'open-postmortem', 'Postmortem'],
  ['capabilities', 'open-capabilities', 'Capabilities'],
];

const TITLES = {
  overview: 'Studio briefing',
  project: 'Signal Drift development',
  person: 'Mina Rao — production file',
  product: 'Paper Harbor — support obligation',
  postmortem: 'Paper Harbor — compact postmortem',
  capabilities: 'Capability graph — inspection file',
};

function navTab(state, view, testId, label) {
  const active = state.view === view;
  return el('button', {
    type: 'button',
    class: 'v2-index-tab' + (active ? ' is-active' : ''),
    'data-action': 'goto',
    'data-arg': view,
    'data-testid': testId,
    'data-focus-key': 'nav-' + view,
    'aria-current': active ? 'true' : null,
  }, label);
}

function readingKey() {
  return el('details', { class: 'v2-key' },
    el('summary', {}, 'Reading key & prototype note'),
    el('ul', { class: 'v2-key-list' },
      el('li', {}, '\u25A0 Phase segments — outlined segment is current; Production is current here.'),
      el('li', {}, '\u25CF Supported observation and \u25D0 tentative inference are shapes, never odds.'),
      el('li', {}, '\u25B2 Readiness stamp — “At risk — follow-up validation needed” survives any decision.'),
      el('li', {}, '\u25C6 Numeral / letter badges index files and exhibits.')
    ),
    el('p', {}, F.meta.pausedNote)
  );
}

function hudBar(state) {
  return el('div', { class: 'v2-hudbar' }, part(state, 'hud'));
}

function masthead(state) {
  return el('div', { class: 'v2-masthead' },
    el('div', { class: 'v2-masthead-top' },
      el('p', { class: 'v2-brand' },
        el('span', { class: 'v2-brand-mark', 'aria-hidden': 'true' }, '\u25C6'),
        el('span', { class: 'v2-brand-name' }, 'Northstar Works'),
        el('span', { class: 'v2-brand-sub' }, 'field notes · disposable prototype, not production')
      )
    ),
    el('p', { class: 'v2-folio' },
      'Status: ', el('strong', {}, statusText(state)),
      ' · Plan: ', el('strong', {}, planOf(state).label)
    ),
    el('nav', { class: 'v2-index', 'aria-label': 'Dossier index' },
      NAV.map((item) => navTab(state, item[0], item[1], item[2]))
    ),
    readingKey()
  );
}

function section(number, title, ...children) {
  return el('section', { class: 'v2-section' },
    el('div', { class: 'v2-section-head' },
      el('span', { class: 'v2-section-num', 'aria-hidden': 'true' }, number),
      el('h2', { class: 'v2-section-title' }, title)
    ),
    el('div', { class: 'v2-section-body' }, children)
  );
}

function footnote(summaryText, ...children) {
  return el('details', { class: 'v2-footnote' },
    el('summary', {}, summaryText),
    el('div', { class: 'v2-footnote-body' }, children)
  );
}

function refLink(view, label) {
  return el('button', {
    type: 'button',
    class: 'v2-ref',
    'data-action': 'goto',
    'data-arg': view,
  }, label);
}

function docShell(fileLabel, title, ...children) {
  return el('article', { class: 'v2-doc' },
    el('p', { class: 'v2-file' }, fileLabel),
    el('h1', { class: 'v2-title', 'data-focus-key': 'view-title', tabindex: '-1' }, title),
    el('div', { class: 'v2-rule', 'aria-hidden': 'true' }),
    children
  );
}

function overviewView(state) {
  return docShell('File 01 · Studio condition', TITLES.overview,
    section('01', 'Decision on the desk',
      part(state, 'summary'),
      el('p', { class: 'v2-question' }, F.project.decisionQuestion),
      el('p', { class: 'v2-refs-label' }, 'Continue reading'),
      el('div', { class: 'v2-refs' },
        refLink('project', 'Signal Drift case file'),
        refLink('person', 'Mina Rao'),
        refLink('product', 'Paper Harbor obligation'),
        refLink('postmortem', 'Compact postmortem'),
        refLink('capabilities', 'Capability graph')
      )
    ),
    section('02', 'Studio condition', part(state, 'studio')),
    footnote('About these field notes',
      el('p', {}, F.meta.pausedNote),
      el('p', {}, F.project.progressNote),
      el('p', {}, F.project.qualityNote)
    )
  );
}

function projectView(state) {
  const evidence = el('div', { class: 'v2-column v2-evidence' },
    section('A', 'Exhibit A — project signals', part(state, 'signals')),
    section('B', 'Exhibit B — findings on file', part(state, 'findings'))
  );
  const register = el('div', { class: 'v2-column v2-register' },
    el('details', { class: 'v2-fold', open: true },
      el('summary', { class: 'v2-fold-summary' },
        el('span', { class: 'v2-fold-mark', 'aria-hidden': 'true' }, '\u25C6'),
        'Disposition register — select, compare, commit'
      ),
      el('div', { class: 'v2-fold-body' },
        section('C', 'Responses on file', part(state, 'responses')),
        state.previewFor ? section('D', 'Comparison — baseline vs response', part(state, 'preview')) : null,
        section('E', 'Sign-off', part(state, 'actions')),
        section('F', 'Decision log', part(state, 'history'))
      )
    )
  );
  return docShell('File 02 · Signal Drift case file', TITLES.project,
    section('01', 'Decision brief',
      part(state, 'summary'),
      el('p', { class: 'v2-question' }, F.project.decisionQuestion)
    ),
    el('div', { class: 'v2-spread' }, evidence, register),
    footnote('Appendix — sources, limitations & reading notes',
      el('ul', { class: 'v2-appendix-list' }, F.findings.map((finding) => el('li', {},
        el('strong', {}, finding.id.toUpperCase() + ' · ' + finding.date + ' — '),
        finding.method + '. ' + finding.history))),
      el('p', {}, F.project.progressNote),
      el('p', {}, F.project.qualityNote)
    )
  );
}

function personView(state) {
  return docShell('File 03 · People', TITLES.person,
    section('01', 'Role & traits', part(state, 'person')),
    footnote('Capacity note', el('p', {}, F.person.note))
  );
}

function productView(state) {
  return docShell('File 04 · Obligations', TITLES.product,
    section('01', 'Support obligation', part(state, 'support')),
    footnote('Promise ledger note', el('p', {}, F.otherProduct.note))
  );
}

function postmortemView(state) {
  return docShell('File 05 · Outcomes', TITLES.postmortem,
    section('01', 'Outcome record', part(state, 'postmortem')),
    footnote('How to read outcomes',
      el('p', {}, 'Expected and observed values are recorded separately; contributing factors stay qualified.'),
      el('p', {}, F.postmortem.qualificationNote)
    )
  );
}

function capabilitiesView(state) {
  return docShell('File 06 · Capabilities', TITLES.capabilities,
    section('01', 'Inspection board',
      el('div', { class: 'v2-scroll-x' }, part(state, 'capabilities'))
    ),
    footnote('How to read the board',
      el('ul', { class: 'v2-key-list' },
        el('li', {}, 'Solid frame — owned capability.'),
        el('li', {}, 'Dashed frame — available or locked; the keyboard list states prerequisites.'),
        el('li', {}, 'Dashed connector — dependency direction; Safe release train needs both inputs.')
      )
    )
  );
}

export function render(state, dispatch) {
  const root = el('div', { class: 'variant-2', 'data-variant': '2' });
  root.append(hudBar(state));
  root.append(masthead(state));
  const view = state.view;
  const body = view === 'project' ? projectView(state)
    : view === 'person' ? personView(state)
      : view === 'product' ? productView(state)
        : view === 'postmortem' ? postmortemView(state)
          : view === 'capabilities' ? capabilitiesView(state)
            : overviewView(state);
  root.append(body);
  return root;
}
