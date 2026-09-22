// WP-UI-01V5 — Variant 5, "Command Board".
// A searchable command workspace over the shared fixture/reducer seam: every command
// is a readable, pointer-equivalent button, the palette filters as you type, Enter
// runs the first matching command, and the board answers with structured evidence,
// comparison and commitment cards (not a terminal text dump).
//
// This renderer only reads the frozen state snapshot it is given and dispatches
// shared actions. No reducer/fixture duplication, no storage, no network, no
// listeners outside the returned root.

import { F, el, part, planOf, statusText } from '../../shared.js';

export const metadata = {
  id: 5,
  name: 'Command Board',
  description: 'Command-palette workspace: filter or click readable commands, run with Enter, and read structured evidence, comparison and commitment cards on the board.',
};

const VIEWS = [
  { view: 'overview', title: 'Studio overview', command: 'Open — Studio overview', nav: 'Studio', testid: 'open-overview' },
  { view: 'project', title: 'Signal Drift development', command: 'Open — Project: Signal Drift', nav: 'Signal Drift', testid: 'open-project' },
  { view: 'person', title: 'Mina Rao', command: 'Open — Person: Mina Rao', nav: 'Mina Rao', testid: 'open-person' },
  { view: 'product', title: 'Paper Harbor support obligation', command: 'Open — Obligation: Paper Harbor', nav: 'Paper Harbor', testid: 'open-product' },
  { view: 'postmortem', title: 'Paper Harbor postmortem', command: 'Open — Postmortem: Paper Harbor', nav: 'Postmortem', testid: 'open-postmortem' },
  { view: 'capabilities', title: 'Capability graph', command: 'Open — Capability graph', nav: 'Capabilities', testid: 'open-capabilities' },
];

// Narrow surfaces keep the catalogue collapsed by default so the game content
// starts near the top; the nav strip, input and Run/Clear stay visible.
const WIDE_CATALOGUE = 860;

// UI-local filter text only. It is never authoritative game/decision data; the
// command list is rebuilt from the shared state snapshot on every render.
let query = '';

function responseById(id) {
  return F.responses.find((response) => response.id === id) || null;
}

function viewMeta(view) {
  return VIEWS.find((entry) => entry.view === view) || VIEWS[0];
}

function panel(label, tone, ...children) {
  const node = el('section', { class: 'v5-panel v5-tone-' + tone },
    el('header', { class: 'v5-panel-head' },
      el('span', { class: 'v5-panel-led', 'aria-hidden': 'true' }),
      el('h3', { class: 'v5-panel-label' }, label)
    )
  );
  children.forEach((child) => { if (child) node.append(child); });
  return node;
}

function channelMap(state) {
  return panel('Channel map', 'green',
    el('div', { class: 'v5-channels' }, VIEWS.map((entry) => el('button', {
      type: 'button',
      class: 'v5-channel',
      'data-action': 'goto',
      'data-arg': entry.view,
      'data-testid': 'channel-' + entry.view,
      'data-focus-key': 'channel-' + entry.view,
      'aria-current': state.view === entry.view ? 'true' : null,
    },
      el('span', { class: 'v5-channel-name' }, entry.nav),
      el('span', { class: 'v5-channel-state' }, state.view === entry.view ? 'ACTIVE' : 'OPEN')
    )))
  );
}

function buildOutput(state) {
  const output = el('div', { class: 'v5-output' });
  switch (state.view) {
    case 'overview':
      output.append(panel('Studio condition', 'cyan', part(state, 'studio')));
      output.append(panel('Decision brief', 'hot', part(state, 'summary')));
      output.append(channelMap(state));
      break;
    case 'project':
      output.append(panel('Decision brief', 'hot', part(state, 'summary')));
      output.append(panel('Systems readout', 'cyan', part(state, 'signals')));
      output.append(panel('Evidence board', 'lav', part(state, 'findings')));
      output.append(panel('Decision deck', 'hot',
        part(state, 'responses'), part(state, 'preview'), part(state, 'actions')));
      output.append(panel('Decision ledger', 'green', part(state, 'history')));
      break;
    case 'person':
      output.append(panel('Person record', 'cyan', part(state, 'person')));
      break;
    case 'product':
      output.append(panel('Support obligation', 'lav', part(state, 'support')));
      break;
    case 'postmortem':
      output.append(panel('Postmortem archive', 'lav', part(state, 'postmortem')));
      break;
    case 'capabilities':
      output.append(panel('Capability inspection', 'green', part(state, 'capabilities')));
      break;
    default:
      break;
  }
  return output;
}

function buildCommands(state) {
  const open = state.decisionStatus === 'open';
  const hasSelection = Boolean(state.selectedResponseId);
  const previewOpen = state.previewFor !== null && state.previewFor === state.selectedResponseId;
  const reopens = state.decisionStatus === 'deferred' || state.decisionStatus === 'rejected';
  const lockedWhy = state.decisionStatus === 'committed'
    ? 'Already committed — reset the fixture to compare again'
    : 'Decision is ' + state.decisionStatus + ' — reopen it first';
  const list = [];

  VIEWS.forEach((entry) => list.push({
    group: 'Navigate',
    label: entry.command,
    keys: entry.view + ' ' + entry.title + ' open go view route page',
    action: 'goto',
    arg: entry.view,
    testid: 'command-view-' + entry.view,
    disabled: false,
    why: null,
  }));

  F.responses.forEach((response) => list.push({
    group: 'Response',
    label: 'Select response — ' + response.label,
    keys: response.id + ' ' + response.label + ' choose pick compare draft',
    action: 'select-response',
    arg: response.id,
    testid: 'command-select-' + response.id,
    disabled: !open,
    why: open ? null : lockedWhy,
  }));

  list.push({
    group: 'Decision',
    label: 'Preview selected response',
    keys: 'preview compare tradeoff evidence',
    action: 'preview',
    arg: null,
    testid: 'command-preview',
    disabled: !open || !hasSelection,
    why: !open ? lockedWhy : (!hasSelection ? 'Select a response first' : null),
  });
  list.push({
    group: 'Decision',
    label: 'Commit selected response',
    keys: 'confirm commit spend money',
    action: 'confirm',
    arg: null,
    testid: 'command-confirm',
    disabled: !open || !previewOpen,
    why: !open ? lockedWhy : (!previewOpen ? 'Preview the selected response first' : null),
  });
  list.push({
    group: 'Decision',
    label: 'Defer decision',
    keys: 'defer postpone later revisit',
    action: 'defer',
    arg: null,
    testid: 'command-defer',
    disabled: !open || !hasSelection,
    why: !open ? lockedWhy : (!hasSelection ? 'Select a response first' : null),
  });
  list.push({
    group: 'Decision',
    label: 'Reject response',
    keys: 'reject decline keep original risk',
    action: 'reject',
    arg: null,
    testid: 'command-reject',
    disabled: !open || !hasSelection,
    why: !open ? lockedWhy : (!hasSelection ? 'Select a response first' : null),
  });
  list.push({
    group: 'Decision',
    label: 'Reopen decision',
    keys: 'reopen review again',
    action: 'reopen',
    arg: null,
    testid: 'command-reopen',
    disabled: !reopens,
    why: reopens ? null : 'Only available after defer or reject',
  });

  F.capabilities.nodes.forEach((node) => list.push({
    group: 'Inspect',
    label: 'Inspect capability — ' + node.name,
    keys: node.id + ' ' + node.name + ' capability graph locked available owned',
    action: 'select-capability',
    arg: node.id,
    testid: 'command-cap-' + node.id,
    disabled: false,
    why: null,
  }));

  list.push({
    group: 'Fixture',
    label: 'Reset fixture state',
    keys: 'reset restart clear prototype',
    action: 'reset',
    arg: null,
    testid: 'command-reset',
    disabled: false,
    why: null,
  });

  return list;
}

function searchText(command) {
  return (command.label + ' ' + command.group + ' ' + command.keys).toLowerCase();
}

function chip(kind, label, value) {
  return el('span', { class: 'v5-chip is-' + kind },
    el('b', {}, label + ': '),
    el('span', { class: 'v5-chip-value' }, value)
  );
}

export function render(state, dispatch) {
  const root = el('div', { class: 'variant-5', 'data-variant': '5' });

  const hud = part(state, 'hud');
  if (hud) root.append(hud);

  const commands = buildCommands(state);
  const wideCatalogue = window.innerWidth >= WIDE_CATALOGUE;
  const selected = state.selectedResponseId ? responseById(state.selectedResponseId) : null;
  const preview = state.previewFor ? responseById(state.previewFor) : null;

  const input = el('input', {
    id: 'v5-command-input',
    class: 'v5-input',
    type: 'text',
    value: query,
    placeholder: 'Filter commands…',
    autocomplete: 'off',
    spellcheck: 'false',
    'aria-label': 'Command search',
    'data-focus-key': 'command-input',
  });
  const runButton = el('button', {
    type: 'button',
    class: 'v5-btn is-primary',
    'data-command-run': '',
    'data-testid': 'command-run',
    'data-focus-key': 'command-run',
    'aria-label': 'Run first matching command',
  }, 'Run');
  const clearButton = el('button', {
    type: 'button',
    class: 'v5-btn',
    'data-command-clear': '',
    'aria-label': 'Clear command filter',
  }, '✕');

  const count = el('span', { class: 'v5-count', 'data-testid': 'command-count' }, '');
  const empty = el('p', {
    class: 'v5-empty',
    hidden: true,
    'data-testid': 'command-empty',
  }, 'No command matches this filter. Clear it to restore every command.');

  const buttons = commands.map((command) => el('button', {
    type: 'button',
    class: 'v5-cmd',
    'data-action': command.action,
    'data-arg': command.arg,
    'data-search': searchText(command),
    'data-testid': command.testid,
    title: command.why,
    disabled: command.disabled || null,
  },
    el('span', { class: 'v5-cmd-glyph', 'aria-hidden': 'true' }, command.disabled ? '×' : '▸'),
    el('span', { class: 'v5-cmd-body' },
      el('span', { class: 'v5-cmd-label' }, command.label),
      command.why ? el('span', { class: 'v5-cmd-why' }, command.why) : null
    ),
    el('span', { class: 'v5-cmd-tag', 'aria-hidden': 'true' }, command.group)
  ));

  const total = buttons.length;

  function refreshFilter() {
    const needle = query.trim().toLowerCase();
    let shown = 0;
    buttons.forEach((button) => {
      const match = !needle || (button.getAttribute('data-search') || '').includes(needle);
      button.hidden = !match;
      if (match) shown += 1;
    });
    count.textContent = shown + '/' + total + ' commands';
    empty.hidden = !(needle && shown === 0);
    return shown;
  }

  function firstRunnable() {
    return buttons.find((button) => !button.hidden && !button.disabled) || null;
  }

  function runFirstCommand() {
    const target = firstRunnable();
    if (!target) {
      empty.hidden = false;
      return;
    }
    query = '';
    dispatch(target.getAttribute('data-action'), target.getAttribute('data-arg'));
  }

  const context = el('div', { class: 'v5-context', 'data-testid': 'command-context' },
    chip('view', 'View', viewMeta(state.view).title),
    chip('status', 'Status', statusText(state)),
    chip('selected', 'Selected', selected ? selected.label : 'none'),
    chip('preview', 'Preview', preview ? preview.label : 'off'),
    chip('cash', 'Cash', planOf(state).cashLabel)
  );

  const deck = el('section', { class: 'v5-deck', 'aria-label': 'Command deck' },
    el('p', { class: 'v5-deck-title' },
      el('span', {}, 'COMMAND DECK'),
      el('span', { class: 'v5-keyhint' }, 'type to filter · ↓ enter list · Tab/Shift+Tab move · Enter run · Esc clear')
    ),
    el('div', { class: 'v5-search' },
      el('span', { class: 'v5-prompt', 'aria-hidden': 'true' }, '⌘'),
      input,
      runButton,
      clearButton
    ),
    context,
    el('details', { class: 'v5-catalogue', open: wideCatalogue ? true : null },
      el('summary', { class: 'v5-catalogue-summary' },
        el('span', {}, 'Command catalogue'),
        count
      ),
      el('div', { class: 'v5-commands' }, buttons, empty)
    )
  );

  const meta = viewMeta(state.view);
  const nav = el('nav', { class: 'v5-nav', 'aria-label': 'Game views' },
    VIEWS.map((entry, index) => el('button', {
      type: 'button',
      class: 'v5-nav-btn',
      'data-action': 'goto',
      'data-arg': entry.view,
      'data-testid': entry.testid,
      'data-focus-key': 'nav-' + entry.view,
      'aria-current': state.view === entry.view ? 'true' : null,
      title: entry.title,
    },
      el('span', { class: 'v5-nav-index', 'aria-hidden': 'true' }, String(index + 1)),
      entry.nav
    ))
  );

  const title = el('h2', {
    class: 'v5-view-title',
    'data-focus-key': 'view-title',
    tabindex: '-1',
  }, meta.title);

  const board = el('section', { class: 'v5-board', 'aria-label': 'Command output board' },
    nav, title, buildOutput(state));

  root.append(el('div', { class: 'v5-console' }, deck, board));

  input.addEventListener('input', () => {
    query = input.value;
    const details = root.querySelector('.v5-catalogue');
    if (query && details && !details.open) details.open = true;
    refreshFilter();
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      runFirstCommand();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      query = '';
      input.value = '';
      refreshFilter();
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      const first = firstRunnable();
      if (first) first.focus();
    }
  });

  root.addEventListener('click', (event) => {
    if (!event.target || !event.target.closest) return;
    if (event.target.closest('[data-command-clear]')) {
      query = '';
      input.value = '';
      refreshFilter();
      input.focus();
      return;
    }
    if (event.target.closest('[data-command-run]')) {
      runFirstCommand();
      return;
    }
    const command = event.target.closest('.v5-cmd');
    if (command && !command.disabled) {
      // Clear the filter so every control is visible again before the shared
      // reducer re-renders the board.
      query = '';
      refreshFilter();
    }
  });

  refreshFilter();
  return root;
}
