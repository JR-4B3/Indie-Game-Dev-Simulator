// WP-UI-01 shared foundation checker (immutable tooling for later variant workers).
//
//   NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
//     node prototypes/studio-lab/check.cjs --core
//   NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
//     node prototypes/studio-lab/check.cjs --variant N
//
// Starts/stops its own stdlib static server (core 18779, variant 18780+N), cwd repo
// root. Evidence (screenshots + check.log) under /tmp/opencode/gamedev-ui-parallel/.
// Visible controls drive the workflow; window.__labHarness is used only for invalid
// action paths, reset plumbing and the core setRenderer preservation probe.

const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

let core = false;
let variant = null;
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--core') core = true;
  else if (argv[i] === '--variant') variant = Number(argv[++i]);
  else if (argv[i].startsWith('--variant=')) variant = Number(argv[i].split('=')[1]);
}
if (!core && !(Number.isInteger(variant) && variant >= 1 && variant <= 5)) {
  console.error('usage: node check.cjs --core | --variant N (N 1..5)');
  process.exit(2);
}

const PORT = core ? 18779 : 18780 + variant;
const MODE = core ? 'core' : 'variant-' + variant;
const EVIDENCE = process.env.LAB_EVIDENCE_DIR || (core
  ? '/tmp/opencode/gamedev-ui-parallel/core'
  : '/tmp/opencode/gamedev-ui-parallel/variant-' + variant);
const HARNESS_URL = 'http://127.0.0.1:' + PORT + '/prototypes/studio-lab/harness.html?' + (core ? 'core=1' : 'variant=' + variant);
const HARNESS_ORIGIN = new URL(HARNESS_URL).origin;

const EXPECTED_PREVIEW = {
  simplify: {
    baselineCash: '$84,000 now',
    proposedCash: '$80,000 after · runway 6.7 months',
    baselineEstimate: '8–11 weeks now',
    proposedEstimate: '7–9 weeks after',
    baselineScope: '100% of baseline now',
    proposedScope: '92% of baseline after',
    spend: '$4,000',
    tradeoff: 'Some core fans may miss depth; onboarding improvement unverified',
  },
  onboarding: {
    baselineCash: '$84,000 now',
    proposedCash: '$72,000 after · runway 6.0 months',
    baselineEstimate: '8–11 weeks now',
    proposedEstimate: '10–13 weeks after',
    baselineScope: '100% of baseline now',
    proposedScope: '100% of baseline after',
    spend: '$12,000',
    tradeoff: 'Keeps depth, costs time/runway; integration untested',
  },
  hold: {
    baselineCash: '$84,000 now',
    proposedCash: '$84,000 after · runway 7.0 months',
    baselineEstimate: '8–11 weeks now',
    proposedEstimate: '8–11 weeks after',
    baselineScope: '100% of baseline now',
    proposedScope: '100% of baseline after',
    spend: '$0',
    tradeoff: 'Preserves schedule, newcomer friction unresolved',
  },
};

let checks = 0;
const logLines = [];
function ok(condition, message) {
  checks += 1;
  assert.ok(condition, message);
}
function eq(actual, expected, message) {
  checks += 1;
  assert.equal(actual, expected, message);
}
function log(message) {
  logLines.push(message);
  process.stdout.write('[lab-check] ' + message + '\n');
}
function norm(text) {
  return (text || '').replace(/\s+/g, ' ').trim();
}

async function waitForServer() {
  for (let attempt = 0; attempt < 120; attempt++) {
    try {
      const response = await fetch(HARNESS_URL);
      if (response.ok) return;
    } catch (error) { /* not ready yet */ }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('stdlib static server did not start on port ' + PORT);
}

async function textOf(page, testId, index = 0) {
  const locator = page.getByTestId(testId).nth(index);
  await locator.waitFor({ state: 'attached', timeout: 8000 });
  return norm(await locator.textContent());
}

async function assertText(page, testId, expected, label) {
  const actual = await textOf(page, testId);
  eq(actual, expected, `${label || testId}: expected "${expected}" got "${actual}"`);
}

async function assertContainsText(page, testId, needle, label) {
  const actual = await textOf(page, testId);
  ok(actual.includes(needle), `${label || testId}: expected to contain "${needle}" got "${actual}"`);
}

async function stateJson(page) {
  return page.evaluate(() => JSON.stringify(window.__labHarness.getState()));
}

async function assertNoStalePending(page, expected, label) {
  const surface = norm(await page.locator('#game-surface').innerText());
  ok(!/decision pending/i.test(surface), `${label}: no stale "decision pending"`);
  if (expected) ok(new RegExp(expected, 'i').test(surface), `${label}: shows ${expected}`);
}

async function activeFocus(page) {
  return page.evaluate(() => {
    const active = document.activeElement;
    if (!active) return null;
    const style = getComputedStyle(active);
    return {
      testid: active.getAttribute ? active.getAttribute('data-testid') : null,
      key: active.getAttribute ? active.getAttribute('data-focus-key') : null,
      id: active.id || null,
      aria: active.getAttribute ? active.getAttribute('aria-label') : null,
      tag: active.tagName,
      inSurface: Boolean(active.closest && active.closest('#game-surface')),
      focusVisible: active.matches(':focus-visible'),
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
    };
  });
}

async function tabTo(page, match, maxTabs = 160) {
  for (let index = 0; index <= maxTabs; index++) {
    const info = await activeFocus(page);
    if (info && match(info)) return info;
    await page.keyboard.press('Tab');
  }
  return null;
}

async function assertFocusKey(page, key, label) {
  const info = await activeFocus(page);
  ok(info && info.key === key, `${label}: expected focus key "${key}" got ${JSON.stringify(info)}`);
}

async function assertKeyboardFocus(page, key, label) {
  await assertFocusKey(page, key, label);
  const info = await activeFocus(page);
  ok(info.focusVisible, `${label}: focused element matches :focus-visible`);
  ok(info.outlineStyle !== 'none' && parseFloat(info.outlineWidth || '0') > 0, `${label}: visible focus outline (${info.outlineStyle} ${info.outlineWidth})`);
}

function rootSelector() {
  return core
    ? '#game-surface > .core-composition[data-variant="core"]'
    : '#game-surface > .variant-' + variant + '[data-variant="' + variant + '"]';
}

async function waitForRoot(page) {
  await page.locator(rootSelector()).waitFor({ state: 'visible', timeout: 10000 });
}

async function gotoView(page, view) {
  await page.getByTestId('open-' + view).first().click();
  await assertText(page, 'date', '18 May 2031', `date on ${view}`);
}

async function resetState(page) {
  if (core) {
    await page.getByTestId('reset-fixture').first().click();
  } else {
    await page.evaluate(() => window.__labHarness.reset());
  }
  await page.waitForTimeout(30);
}

async function assertGeometry(page, label, expectedRail) {
  const geometry = await page.evaluate(() => {
    const rail = document.getElementById('rail-placeholder').getBoundingClientRect();
    const surface = document.getElementById('game-surface').getBoundingClientRect();
    const root = document.querySelector('#game-surface > [data-variant]');
    return {
      rail: { left: rail.left, right: rail.right, width: rail.width },
      surface: { left: surface.left, right: surface.right, width: surface.width },
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      docScrollWidth: document.documentElement.scrollWidth,
      docScrollHeight: document.documentElement.scrollHeight,
      rootVisible: Boolean(root && root.getBoundingClientRect().width > 0 && root.getBoundingClientRect().height > 0),
    };
  });
  ok(geometry.rail.right <= geometry.innerWidth + 1, `${label}: rail must not exceed viewport`);
  ok(geometry.rail.left >= geometry.surface.right - 1, `${label}: surface must not sit under the rail`);
  ok(Math.abs(geometry.rail.width + geometry.surface.width - geometry.innerWidth) < 2, `${label}: rail + surface fill viewport`);
  eq(Math.round(geometry.rail.width), expectedRail, `${label}: reserved rail width`);
  ok(geometry.docScrollWidth <= geometry.innerWidth + 1, `${label}: no horizontal page overflow`);
  ok(geometry.rootVisible, `${label}: mounted root visible`);
}

async function assertIndicatorGraphics(page, label) {
  await assertText(page, 'work-progress', '60% of baseline scope', `${label}: baseline-relative work text`);
  const work = await page.evaluate(() => {
    const bar = document.querySelector('[data-testid="work-bar"]');
    const track = document.querySelector('[data-testid="work-bar-track"]');
    if (!bar || !track) return null;
    const b = bar.getBoundingClientRect();
    const t = track.getBoundingClientRect();
    return {
      role: bar.getAttribute('role'),
      name: bar.getAttribute('aria-label'),
      now: bar.getAttribute('aria-valuenow'),
      min: bar.getAttribute('aria-valuemin'),
      max: bar.getAttribute('aria-valuemax'),
      ratio: t.width ? b.width / t.width : 0,
      height: b.height,
    };
  });
  ok(work, `${label}: work bar present`);
  eq(work.role, 'progressbar', `${label}: work bar role`);
  eq(work.name, 'Baseline work completed', `${label}: work bar accessible name`);
  eq(work.now, '60', `${label}: work bar value 60`);
  eq(work.min, '0', `${label}: work bar min 0`);
  eq(work.max, '100', `${label}: work bar max 100`);
  ok(work.ratio > 0.5 && work.ratio < 0.7, `${label}: work bar fill near 60% (${work.ratio})`);
  ok(work.height > 0, `${label}: work bar visible geometry`);

  const phase = await page.evaluate(() => {
    const track = document.querySelector('[data-testid="phase-track"]');
    if (!track) return null;
    const current = track.querySelector('[aria-current="step"]');
    return {
      steps: track.querySelectorAll('li').length,
      aria: track.getAttribute('aria-label'),
      currentText: current ? current.textContent : '',
      currentBox: current ? current.getBoundingClientRect().width : 0,
    };
  });
  ok(phase, `${label}: phase track present`);
  ok(phase.steps >= 5, `${label}: phase track segmented`);
  ok(/Production/.test(phase.aria) && /Production/.test(phase.currentText), `${label}: Production labeled current`);
  ok(phase.currentBox > 0, `${label}: current phase segment visible`);

  const readiness = await page.evaluate(() => {
    const cue = document.querySelector('[data-testid="readiness"]');
    if (!cue) return null;
    const rect = cue.getBoundingClientRect();
    return { aria: cue.getAttribute('aria-label'), text: cue.textContent, width: rect.width, height: rect.height };
  });
  ok(readiness && /At risk/.test(readiness.aria) && /At risk/.test(readiness.text), `${label}: readiness categorical text`);
  ok(readiness.width > 0 && readiness.height > 0, `${label}: readiness shape visible`);
}

async function assertConfidence(page, label) {
  for (const [findingId, category] of [['f1', 'supported'], ['f2', 'tentative'], ['f3', 'tentative']]) {
    const cue = page.getByTestId('confidence-' + findingId).first();
    eq(await cue.getAttribute('data-confidence'), category, `${label}: confidence-${findingId} category`);
    const aria = await cue.getAttribute('aria-label');
    ok(new RegExp(category, 'i').test(aria), `${label}: confidence-${findingId} label (${aria})`);
    const box = await cue.boundingBox();
    ok(box && box.width > 0 && box.height > 0, `${label}: confidence-${findingId} visible shape`);
    ok(!/\d+\s*%/.test(await cue.innerText()), `${label}: confidence-${findingId} has no fabricated odds`);
    const findingText = await textOf(page, 'finding-' + findingId);
    ok(findingText.includes('Source:'), `${label}: finding-${findingId} source`);
    ok(findingText.includes('20') || findingText.includes('May 2031'), `${label}: finding-${findingId} date/history`);
  }
}

async function runWorkflow(page) {
  log('workflow: overview -> project -> compare -> transitions -> commit');
  await gotoView(page, 'overview');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'overview cash');
  await assertText(page, 'metric-runway', 'Runway 7.0 months', 'overview runway');
  await assertText(page, 'decision-flag', 'Unresolved onboarding decision', 'decision flag');
  await assertText(page, 'decision-status', 'Open — no response committed', 'initial status');
  const overviewText = norm(await page.locator('#game-surface').innerText());
  ok(overviewText.includes('Paper Harbor'), 'overview mentions Paper Harbor');
  await gotoView(page, 'project');
  await assertText(page, 'decision-flag', 'Unresolved onboarding decision', 'open flag wording on project');
  await assertText(page, 'project-name', 'Signal Drift', 'project name');
  eq(await page.getByTestId('pillar').count(), 3, 'three pillars');
  await assertIndicatorGraphics(page, 'project');
  await assertText(page, 'finish-estimate', '8–11 weeks', 'initial finish estimate');
  await assertText(page, 'scope-baseline', '100% of baseline', 'initial scope');
  await assertConfidence(page, 'project');
  eq(await page.getByTestId('history-entry').count(), 0, 'no history yet');

  for (const responseId of ['simplify', 'onboarding', 'hold']) {
    const expected = EXPECTED_PREVIEW[responseId];
    await page.getByTestId('response-' + responseId).first().click();
    eq(await page.getByTestId('response-' + responseId).getAttribute('aria-pressed'), 'true', `${responseId} selected`);
    await assertFocusKey(page, 'response-' + responseId, `${responseId} selection focus`);
    eq(await page.getByTestId('confirm-button').isDisabled(), true, `${responseId}: confirm needs preview`);
    await page.getByTestId('preview-button').first().click();
    await assertFocusKey(page, 'cancel-preview', `${responseId} preview focus`);
    await assertText(page, 'preview-baseline-cash', expected.baselineCash, `${responseId} baseline cash`);
    await assertText(page, 'preview-proposed-cash', expected.proposedCash, `${responseId} proposed cash`);
    await assertText(page, 'preview-baseline-estimate', expected.baselineEstimate, `${responseId} baseline estimate`);
    await assertText(page, 'preview-proposed-estimate', expected.proposedEstimate, `${responseId} proposed estimate`);
    await assertText(page, 'preview-baseline-scope', expected.baselineScope, `${responseId} baseline scope`);
    await assertText(page, 'preview-proposed-scope', expected.proposedScope, `${responseId} proposed scope`);
    await assertText(page, 'preview-spend', expected.spend, `${responseId} spend`);
    await assertText(page, 'preview-tradeoff', expected.tradeoff, `${responseId} tradeoff`);
    await assertText(page, 'metric-cash', 'Cash $84,000', `${responseId} preview does not spend`);
    await page.getByTestId('cancel-preview').first().click();
    eq(await page.getByTestId('preview-panel').count(), 0, `${responseId} cancel closes preview`);
    await assertFocusKey(page, 'preview-button', `${responseId} cancel focus`);
    eq(await page.getByTestId('history-entry').count(), 0, `${responseId} preview/cancel is not history`);
  }

  // Defer -> reopen -> reject -> reopen.
  await page.getByTestId('response-onboarding').first().click();
  await page.getByTestId('defer-button').first().click();
  await assertText(page, 'decision-status', 'Deferred — revisit before validation', 'deferred status');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'defer keeps cash');
  eq(await page.getByTestId('history-entry').count(), 1, 'defer recorded once');
  await assertFocusKey(page, 'reopen-button', 'defer focus advances to reopen');
  await assertNoStalePending(page, 'deferred', 'defer status labels');
  await assertText(page, 'decision-flag', 'Deferred: Build guided introduction — revisit before validation', 'defer flag wording on project');
  await gotoView(page, 'overview');
  await assertText(page, 'decision-flag', 'Deferred: Build guided introduction — revisit before validation', 'defer flag wording on overview');
  await gotoView(page, 'project');

  await page.getByTestId('reopen-button').first().click();
  await assertText(page, 'decision-status', 'Open — no response committed', 'reopened status');
  eq(await page.getByTestId('history-entry').count(), 2, 'reopen recorded');
  await assertFocusKey(page, 'decision-result', 'reopen focus advances to result');

  await page.getByTestId('response-simplify').first().click();
  await page.getByTestId('reject-button').first().click();
  await assertText(page, 'decision-status', 'Response rejected — original risk remains', 'rejected status');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'reject keeps cash');
  eq(await page.getByTestId('history-entry').count(), 3, 'reject recorded');
  await assertFocusKey(page, 'reopen-button', 'reject focus advances to reopen');
  await assertNoStalePending(page, 'rejected', 'reject status labels');
  await assertText(page, 'decision-flag', 'Rejected: Simplify branching — original risk remains', 'reject flag wording on project');
  await gotoView(page, 'overview');
  await assertText(page, 'decision-flag', 'Rejected: Simplify branching — original risk remains', 'reject flag wording on overview');
  await gotoView(page, 'project');

  await page.getByTestId('reopen-button').first().click();
  await page.getByTestId('response-simplify').first().click();
  await page.getByTestId('preview-button').first().click();
  await page.getByTestId('confirm-button').first().click();
  await assertText(page, 'decision-status', 'Committed', 'committed status');
  await assertText(page, 'metric-cash', 'Cash $80,000', 'committed cash');
  await assertText(page, 'metric-runway', 'Runway 6.7 months', 'committed runway');
  await assertText(page, 'finish-estimate', '7–9 weeks', 'committed estimate');
  await assertText(page, 'scope-baseline', '92% of baseline', 'committed scope');
  await assertText(page, 'readiness-text', 'At risk — follow-up validation needed', 'readiness stays at risk');
  await assertIndicatorGraphics(page, 'committed');
  await assertFocusKey(page, 'decision-result', 'confirm focus advances to result');
  await assertText(page, 'decision-flag', 'Committed: Simplify branching', 'commit flag wording on project');
  eq(await page.getByTestId('history-entry').count(), 5, 'commit recorded after earlier transitions');
  for (const responseId of ['simplify', 'onboarding', 'hold']) {
    eq(await page.getByTestId('response-' + responseId).isDisabled(), true, `${responseId} locked after commit`);
  }
  eq(await page.getByTestId('confirm-button').isDisabled(), true, 'confirm locked after commit');
  const cashBefore = await textOf(page, 'metric-cash');
  await page.evaluate(() => { window.__labHarness.dispatch('confirm'); });
  await assertContainsText(page, 'metric-cash', cashBefore, 'duplicate confirm cannot spend again');
  await assertNoStalePending(page, 'committed', 'committed status labels');

  // Overview reflects the committed decision.
  await gotoView(page, 'overview');
  await assertText(page, 'metric-cash', 'Cash $80,000', 'overview cash after commit');
  await assertText(page, 'decision-status', 'Committed', 'overview status after commit');
  await assertContainsText(page, 'committed-plan', 'Simplify branching', 'overview committed plan');
  await assertText(page, 'decision-flag', 'Committed: Simplify branching', 'commit flag wording on overview');

  // Other routes.
  await gotoView(page, 'person');
  await assertText(page, 'person-name', 'Mina Rao', 'person name');
  const traits = await textOf(page, 'person-traits');
  ok(traits.includes('Methodical') && traits.includes('Mentor'), 'person traits');
  await assertContainsText(page, 'person-commitment', 'Signal Drift integration', 'person commitment');
  await assertNoStalePending(page, null, 'person status labels');

  await gotoView(page, 'product');
  await assertContainsText(page, 'support-obligation', 'Compatibility fix promised by 2 June', 'support promise');
  await assertContainsText(page, 'support-obligation', 'One engineer-week reserved', 'support reservation');
  ok(norm(await page.locator('#game-surface').innerText()).includes('competes with ongoing Signal Drift production'), 'support opportunity cost');

  await gotoView(page, 'postmortem');
  await assertContainsText(page, 'pm-schedule', 'planned 20 weeks → actual 24 weeks', 'postmortem schedule');
  await assertContainsText(page, 'pm-budget', 'expected $60,000 → actual $68,000', 'postmortem budget');
  await assertContainsText(page, 'pm-receipts', 'expected $100,000 → observed $92,000', 'postmortem receipts');
  await assertContainsText(page, 'pm-net', '$70,000', 'postmortem net');
  await assertContainsText(page, 'pm-contribution', '$2,000 after $68,000 tracked cost', 'postmortem contribution');
  eq(await page.getByTestId('factor').count(), 3, 'three qualified factors');
  await assertNoStalePending(page, null, 'postmortem status labels');

  await gotoView(page, 'capabilities');
  eq(await page.getByTestId('capability-list').locator('button').count(), 5, 'capability list has five buttons');
  ok(await page.getByTestId('capability-graph').first().isVisible(), 'capability graph visible');
  const edges = await page.evaluate(() => {
    const svg = document.querySelector('[data-testid="capability-graph"]');
    return Array.from(svg.querySelectorAll('line')).map((line) => {
      const style = getComputedStyle(line);
      return {
        stroke: style.stroke,
        strokeWidth: style.strokeWidth,
        x1: Number(line.getAttribute('x1')),
        y1: Number(line.getAttribute('y1')),
        x2: Number(line.getAttribute('x2')),
        y2: Number(line.getAttribute('y2')),
      };
    });
  });
  eq(edges.length, 4, 'four capability edges present');
  edges.forEach((edge, index) => {
    ok(edge.stroke && edge.stroke !== 'none' && edge.stroke !== 'rgba(0, 0, 0, 0)', `edge ${index} has visible computed stroke (${edge.stroke})`);
    ok(parseFloat(edge.strokeWidth) > 0, `edge ${index} has nonzero stroke width`);
    ok(Math.hypot(edge.x2 - edge.x1, edge.y2 - edge.y1) > 10, `edge ${index} has nonzero geometry`);
  });
  eq(edges.filter((edge) => edge.x2 > 400).length, 2, 'two edges feed Safe release train');
  await page.getByTestId('cap-list-automated-tests').first().click();
  await assertFocusKey(page, 'cap-automated-tests', 'capability selection focus');
  await assertContainsText(page, 'cap-detail', 'Detects regressions, not design fun', 'automated tests detail');
  await assertContainsText(page, 'cap-detail', 'Reserve $6,000 and 2 engineer-weeks', 'automated tests cost');
  await assertContainsText(page, 'cap-note', 'Inspection only', 'inspection-only note');
  await page.getByTestId('cap-list-safe-release-train').first().click();
  await assertContainsText(page, 'cap-detail', 'Requires Automated tests AND Incident process', 'AND prerequisite');
  await assertContainsText(page, 'cap-detail', 'Locked', 'locked capability');
  await assertNoStalePending(page, null, 'capabilities status labels');

  // Exact committed effects for all three responses, on project and overview.
  for (const [responseId, expected] of [
    ['simplify', { label: 'Simplify branching', cash: 'Cash $80,000', runway: 'Runway 6.7 months', estimate: '7–9 weeks', scope: '92% of baseline' }],
    ['onboarding', { label: 'Build guided introduction', cash: 'Cash $72,000', runway: 'Runway 6.0 months', estimate: '10–13 weeks', scope: '100% of baseline' }],
    ['hold', { label: 'Keep current plan', cash: 'Cash $84,000', runway: 'Runway 7.0 months', estimate: '8–11 weeks', scope: '100% of baseline' }],
  ]) {
    await resetState(page);
    await gotoView(page, 'project');
    await page.getByTestId('response-' + responseId).first().click();
    await page.getByTestId('preview-button').first().click();
    await page.getByTestId('confirm-button').first().click();
    await assertText(page, 'metric-cash', expected.cash, responseId + ': committed cash');
    await assertText(page, 'metric-runway', expected.runway, responseId + ': committed runway');
    await assertText(page, 'finish-estimate', expected.estimate, responseId + ': committed estimate');
    await assertText(page, 'scope-baseline', expected.scope, responseId + ': committed scope');
    await assertText(page, 'decision-status', 'Committed', responseId + ': committed status');
    await assertText(page, 'decision-flag', 'Committed: ' + expected.label, responseId + ': flag on project');
    await gotoView(page, 'overview');
    await assertText(page, 'decision-flag', 'Committed: ' + expected.label, responseId + ': flag on overview');
    await assertText(page, 'metric-cash', expected.cash, responseId + ': overview cash');
  }
  await resetState(page);
}

async function runInvalidActions(page) {
  log('invalid actions do not mutate state');
  await resetState(page);
  const before = await page.evaluate(() => JSON.stringify(window.__labHarness.getState()));
  await page.evaluate(() => {
    window.__labHarness.dispatch('not-an-action');
    window.__labHarness.dispatch('goto', 'nonsense');
    window.__labHarness.dispatch('select-response', 'nope');
    window.__labHarness.dispatch('select-capability', 'nope');
    window.__labHarness.dispatch('confirm');
    window.__labHarness.dispatch('defer');
  });
  const after = await page.evaluate(() => JSON.stringify(window.__labHarness.getState()));
  eq(after, before, 'invalid actions leave shared state unchanged');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'invalid actions keep cash');
}

async function runKeyboard(page) {
  log('keyboard: Tab/Enter/Space workflow and focus ownership');
  await resetState(page);

  // Keyboard navigation to the project view.
  let info = await tabTo(page, (focus) => focus.testid === 'open-project');
  ok(info, 'keyboard: Tab reached open-project');
  await page.keyboard.press('Enter');
  await assertKeyboardFocus(page, 'view-title', 'keyboard: navigation focuses view heading');

  // Enter selects a response and keeps focus.
  info = await tabTo(page, (focus) => focus.testid === 'response-onboarding');
  ok(info, 'keyboard: Tab reached response-onboarding');
  await page.keyboard.press('Enter');
  eq(await page.getByTestId('response-onboarding').getAttribute('aria-pressed'), 'true', 'keyboard: Enter selected onboarding');
  await assertKeyboardFocus(page, 'response-onboarding', 'keyboard: selection focus retained');

  // Space selects the hold response.
  info = await tabTo(page, (focus) => focus.testid === 'response-hold');
  ok(info, 'keyboard: Tab reached response-hold');
  await page.keyboard.press('Space');
  eq(await page.getByTestId('response-hold').getAttribute('aria-pressed'), 'true', 'keyboard: Space selected hold');
  await assertKeyboardFocus(page, 'response-hold', 'keyboard: Space selection focus retained');

  // Preview then cancel with keyboard.
  info = await tabTo(page, (focus) => focus.testid === 'preview-button');
  ok(info, 'keyboard: Tab reached preview-button');
  await page.keyboard.press('Enter');
  ok(await page.getByTestId('preview-panel').first().isVisible(), 'keyboard: Enter opened preview');
  await assertKeyboardFocus(page, 'cancel-preview', 'keyboard: preview focuses cancel');
  info = await tabTo(page, (focus) => focus.testid === 'cancel-preview');
  await page.keyboard.press('Enter');
  eq(await page.getByTestId('preview-panel').count(), 0, 'keyboard: cancel closed preview');
  await assertKeyboardFocus(page, 'preview-button', 'keyboard: cancel returns focus to preview');

  // Preview and confirm with keyboard.
  await page.keyboard.press('Enter');
  info = await tabTo(page, (focus) => focus.testid === 'confirm-button');
  ok(info, 'keyboard: Tab reached confirm-button');
  await page.keyboard.press('Enter');
  await assertText(page, 'decision-status', 'Committed', 'keyboard: Enter committed');
  await assertKeyboardFocus(page, 'decision-result', 'keyboard: confirm focuses decision result');

  // Defer then reopen with keyboard.
  await resetState(page);
  await gotoView(page, 'project');
  info = await tabTo(page, (focus) => focus.testid === 'response-onboarding');
  await page.keyboard.press('Enter');
  info = await tabTo(page, (focus) => focus.testid === 'defer-button');
  ok(info, 'keyboard: Tab reached defer-button');
  await page.keyboard.press('Enter');
  await assertKeyboardFocus(page, 'reopen-button', 'keyboard: defer focuses reopen');
  await page.keyboard.press('Enter');
  await assertText(page, 'decision-status', 'Open — no response committed', 'keyboard: reopen returns to open');
  await assertKeyboardFocus(page, 'decision-result', 'keyboard: reopen focuses decision result');
}

async function runUnavailableProbe(page) {
  log('harness: invalid/absent variants are honestly unavailable');
  await page.goto('http://127.0.0.1:' + PORT + '/prototypes/studio-lab/harness.html?variant=9');
  const unavailable = page.getByTestId('variant-unavailable');
  await unavailable.waitFor({ state: 'visible', timeout: 5000 });
  ok((await unavailable.textContent()).includes('not one of'), 'invalid variant message is honest');
  eq(await page.locator('#game-surface > [data-variant]').count(), 0, 'invalid variant substitutes no design');

  await page.goto('http://127.0.0.1:' + PORT + '/prototypes/studio-lab/harness.html?variant=1');
  const absent = await page.getByTestId('variant-unavailable').waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false);
  const roots = await page.locator('#game-surface > [data-variant]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-variant')));
  ok(absent || (roots.length === 1 && roots[0] === '1'), 'variant 1 either mounts or reports honestly, never another design');
  if (roots.length) eq(roots[0], '1', 'variant 1 route only mounts variant 1');
}

async function runGuards(page) {
  log('guards: non-open decisions require explicit reopen');
  await resetState(page);
  await gotoView(page, 'project');

  // Deferred: all five decision actions disabled; dispatch is identity.
  await page.getByTestId('response-onboarding').first().click();
  await page.getByTestId('defer-button').first().click();
  for (const id of ['simplify', 'onboarding', 'hold']) {
    eq(await page.getByTestId('response-' + id).isDisabled(), true, `deferred: response-${id} disabled`);
  }
  for (const id of ['preview-button', 'confirm-button', 'defer-button', 'reject-button']) {
    eq(await page.getByTestId(id).isDisabled(), true, `deferred: ${id} disabled`);
  }
  eq(await page.getByTestId('reopen-button').isDisabled(), false, 'deferred: reopen enabled');
  const deferredState = await stateJson(page);
  const deferredCount = await page.getByTestId('history-entry').count();
  await page.evaluate(() => {
    const harness = window.__labHarness;
    harness.dispatch('select-response', 'simplify');
    harness.dispatch('preview');
    harness.dispatch('confirm');
    harness.dispatch('defer');
    harness.dispatch('reject');
    harness.dispatch('select-response', 'hold');
  });
  eq(await stateJson(page), deferredState, 'deferred: guarded actions cannot mutate state');
  eq(await page.getByTestId('history-entry').count(), deferredCount, 'deferred: no duplicate history');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'deferred: money unchanged');

  // Rejected: same guards until explicit reopen.
  await page.getByTestId('reopen-button').first().click();
  await page.getByTestId('response-simplify').first().click();
  await page.getByTestId('reject-button').first().click();
  for (const id of ['preview-button', 'confirm-button', 'defer-button', 'reject-button']) {
    eq(await page.getByTestId(id).isDisabled(), true, `rejected: ${id} disabled`);
  }
  const rejectedState = await stateJson(page);
  const rejectedCount = await page.getByTestId('history-entry').count();
  await page.evaluate(() => {
    const harness = window.__labHarness;
    harness.dispatch('select-response', 'simplify');
    harness.dispatch('preview');
    harness.dispatch('confirm');
    harness.dispatch('reject');
    harness.dispatch('defer');
  });
  eq(await stateJson(page), rejectedState, 'rejected: guarded actions cannot mutate state');
  eq(await page.getByTestId('history-entry').count(), rejectedCount, 'rejected: no duplicate history');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'rejected: money unchanged');

  // Committed: still locked; no reopen offered.
  await page.getByTestId('reopen-button').first().click();
  await page.getByTestId('response-simplify').first().click();
  await page.getByTestId('preview-button').first().click();
  await page.getByTestId('confirm-button').first().click();
  const committedState = await stateJson(page);
  const committedCount = await page.getByTestId('history-entry').count();
  await page.evaluate(() => {
    const harness = window.__labHarness;
    harness.dispatch('select-response', 'onboarding');
    harness.dispatch('preview');
    harness.dispatch('confirm');
    harness.dispatch('defer');
    harness.dispatch('reject');
  });
  eq(await stateJson(page), committedState, 'committed: guarded actions cannot mutate state');
  eq(await page.getByTestId('history-entry').count(), committedCount, 'committed: no duplicate history');
  await assertText(page, 'metric-cash', 'Cash $80,000', 'committed: money unchanged');
  eq(await page.getByTestId('reopen-button').count(), 0, 'committed: no reopen offered');
}

async function runImmutability(page) {
  log('fixtures and prior state immutability');
  const frozen = await page.evaluate(() => ({
    root: Object.isFrozen(globalThis.STUDIO_LAB_FIXTURES),
    response: Object.isFrozen(globalThis.STUDIO_LAB_FIXTURES.responses[0]),
    snapshot: JSON.stringify(globalThis.STUDIO_LAB_FIXTURES),
  }));
  ok(frozen.root && frozen.response, 'fixture data deeply frozen');
  await resetState(page);
  const before = await stateJson(page);
  await page.evaluate(() => {
    const harness = window.__labHarness;
    harness.dispatch('select-response', 'nope');
    harness.dispatch('goto', 'nowhere');
    harness.dispatch('confirm');
  });
  eq(await stateJson(page), before, 'invalid actions leave state unchanged');
  const after = await page.evaluate(() => JSON.stringify(globalThis.STUDIO_LAB_FIXTURES));
  eq(after, frozen.snapshot, 'fixture data unchanged by reducer usage');

  // Valid transitions retain every previous state/history snapshot and references.
  const transitions = await page.evaluate(() => {
    const harness = window.__labHarness;
    harness.reset();
    const states = [];
    const snapshots = [];
    const capture = () => { states.push(harness.getState()); snapshots.push(JSON.stringify(harness.getState())); };
    capture();
    harness.dispatch('goto', 'project');
    capture();
    harness.dispatch('select-response', 'simplify');
    capture();
    harness.dispatch('preview');
    capture();
    harness.dispatch('confirm');
    capture();
    harness.dispatch('confirm');
    harness.dispatch('defer');
    harness.dispatch('reject');
    return {
      distinct: states.every((state, index) => index === 0 || state !== states[index - 1]),
      snapshots,
      later: states.map((state) => JSON.stringify(state)),
      historyRefStable: states[2].history === states[3].history && states[3].history !== states[4].history,
      statesFrozen: states.every((state) => Object.isFrozen(state) && Object.isFrozen(state.history)),
      committedHistoryFrozen: Object.isFrozen(states[4].history) && Object.isFrozen(states[4].history[0]),
      nestedFrozen: Object.isFrozen(globalThis.STUDIO_LAB_FIXTURES.capabilities.nodes)
        && Object.isFrozen(globalThis.STUDIO_LAB_FIXTURES.capabilities.nodes[0])
        && Object.isFrozen(globalThis.STUDIO_LAB_FIXTURES.capabilities.edges)
        && Object.isFrozen(globalThis.STUDIO_LAB_FIXTURES.responses)
        && Object.isFrozen(globalThis.STUDIO_LAB_FIXTURES.responses[0])
        && Object.isFrozen(globalThis.STUDIO_LAB_FIXTURES.findings[0]),
    };
  });
  ok(transitions.distinct, 'each valid transition returns a new state object');
  eq(JSON.stringify(transitions.later), JSON.stringify(transitions.snapshots), 'previous valid state snapshots stay unchanged');
  ok(transitions.historyRefStable, 'preview keeps the history reference; confirm creates a new frozen history array');
  ok(transitions.statesFrozen && transitions.committedHistoryFrozen, 'states and history entries are frozen');
  ok(transitions.nestedFrozen, 'nested fixture branches (capabilities, responses, findings) are frozen');
}

async function runResetProbe(page) {
  log('reset(): fixture/state reset with focus inside and outside the surface');
  await page.goto(HARNESS_URL);
  await waitForRoot(page);
  await page.getByTestId('open-project').first().click();
  await page.getByTestId('response-onboarding').first().click();
  await page.getByTestId('preview-button').first().click();
  await page.getByTestId('confirm-button').first().click();
  await assertText(page, 'metric-cash', 'Cash $72,000', 'reset probe: committed fixture changed');

  await page.getByTestId('decision-result').focus();
  await page.evaluate(() => window.__labHarness.reset());
  eq(await stateJson(page), JSON.stringify({
    view: 'overview',
    selectedResponseId: null,
    previewFor: null,
    decisionStatus: 'open',
    committedResponseId: null,
    history: [],
    ack: '',
    selectedCapabilityId: 'automated-tests',
  }), 'reset restores the exact initial shared state');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'reset restores fixture cash');
  await assertText(page, 'decision-status', 'Open — no response committed', 'reset reopens the decision');
  eq(await page.getByTestId('history-entry').count(), 0, 'reset clears history');
  eq(await page.evaluate(() => document.activeElement.getAttribute('data-focus-key')), 'view-title', 'reset moves inside-surface focus to the visible view heading');

  await page.evaluate(() => {
    const button = document.createElement('button');
    button.id = 'rail-reset-probe';
    button.textContent = 'rail reset probe';
    document.getElementById('rail-placeholder').append(button);
    button.focus();
  });
  await page.evaluate(() => window.__labHarness.reset());
  eq(await page.evaluate(() => document.activeElement.id), 'rail-reset-probe', 'reset keeps focus outside the surface');
}

async function runFocusProbes(page) {
  log('focus: rail isolation, offscreen heading, unusable targets, renderer validation');
  await page.goto(HARNESS_URL);
  await waitForRoot(page);

  const buildProbe = `(state) => {
    const root = document.createElement('div');
    root.className = 'focus-probe';
    root.setAttribute('data-variant', 'focus-probe');
    const title = document.createElement('h2');
    title.setAttribute('data-focus-key', 'view-title');
    title.tabIndex = -1;
    title.textContent = 'Probe ' + state.view;
    root.append(title);
    for (let i = 0; i < 80; i++) {
      const spacer = document.createElement('p');
      spacer.textContent = 'spacer ' + i;
      root.append(spacer);
    }
    return root;
  }`;
  const installProbe = async () => page.evaluate((source) => {
    window.__labHarness.setRenderer(eval(source));
  }, buildProbe);

  // Keyed external rail control keeps focus through setRenderer.
  await page.evaluate(() => {
    const button = document.createElement('button');
    button.id = 'rail-keyed';
    button.setAttribute('data-focus-key', 'rail-keyed');
    button.textContent = 'rail keyed';
    document.getElementById('rail-placeholder').append(button);
    button.focus();
  });
  await installProbe();
  eq(await page.evaluate(() => document.activeElement.id), 'rail-keyed', 'keyed rail focus survives setRenderer');

  // Unkeyed external control keeps focus too.
  await page.evaluate(() => {
    const button = document.createElement('button');
    button.id = 'rail-plain';
    button.textContent = 'rail plain';
    document.getElementById('rail-placeholder').append(button);
    button.focus();
  });
  await installProbe();
  eq(await page.evaluate(() => document.activeElement.id), 'rail-plain', 'unkeyed rail focus survives setRenderer');

  // Offscreen intended heading is scrolled into the surface viewport.
  await page.evaluate(() => {
    const surface = document.getElementById('game-surface');
    surface.scrollTop = surface.scrollHeight;
  });
  await page.evaluate(() => window.__labHarness.dispatch('goto', 'person'));
  const headingVisible = await page.evaluate(() => {
    const surface = document.getElementById('game-surface').getBoundingClientRect();
    const title = document.querySelector('[data-focus-key="view-title"]').getBoundingClientRect();
    return title.top >= surface.top - 1 && title.bottom <= surface.bottom + 1;
  });
  ok(headingVisible, 'intended heading scrolled into the surface viewport');

  // Hidden/inert/disabled targets (including a hidden ancestor) are rejected.
  await page.evaluate(() => {
    window.__labHarness.setRenderer(() => {
      const root = document.createElement('div');
      root.className = 'focus-probe-hidden';
      root.setAttribute('data-variant', 'focus-probe-hidden');
      const hidden = document.createElement('p');
      hidden.setAttribute('data-focus-key', 'view-title');
      hidden.hidden = true;
      hidden.textContent = 'hidden title';
      const inert = document.createElement('p');
      inert.setAttribute('data-focus-key', 'decision-result');
      inert.setAttribute('inert', '');
      inert.textContent = 'inert result';
      const disabled = document.createElement('button');
      disabled.setAttribute('data-focus-key', 'reopen-button');
      disabled.setAttribute('disabled', '');
      disabled.textContent = 'disabled reopen';
      const hiddenWrap = document.createElement('div');
      hiddenWrap.hidden = true;
      const wrapped = document.createElement('button');
      wrapped.setAttribute('data-focus-key', 'preview-button');
      wrapped.textContent = 'hidden ancestor button';
      hiddenWrap.append(wrapped);
      root.append(hidden, inert, disabled, hiddenWrap);
      return root;
    });
  });
  await page.evaluate(() => window.__labHarness.dispatch('goto', 'project'));
  const fallback = await page.evaluate(() => {
    const active = document.activeElement;
    return { variant: active.getAttribute && active.getAttribute('data-variant'), tabindex: active.tabIndex };
  });
  eq(fallback.variant, 'focus-probe-hidden', 'unusable targets fall back to the focusable root');
  eq(fallback.tabindex, -1, 'fallback root is focusable at tabindex -1');
  await page.evaluate(() => {
    const harness = window.__labHarness;
    harness.dispatch('select-response', 'simplify');
    harness.dispatch('preview');
    harness.dispatch('cancel-preview');
  });
  const afterHiddenAncestor = await page.evaluate(() => document.activeElement.getAttribute && document.activeElement.getAttribute('data-variant'));
  eq(afterHiddenAncestor, 'focus-probe-hidden', 'target inside a hidden ancestor is rejected');

  // CSS-hidden and zero-geometry targets/ancestors are also rejected.
  await page.evaluate(() => {
    window.__labHarness.setRenderer(() => {
      const root = document.createElement('div');
      root.className = 'focus-probe-css';
      root.setAttribute('data-variant', 'focus-probe-css');
      const displayNoneWrap = document.createElement('div');
      displayNoneWrap.style.display = 'none';
      const titleInside = document.createElement('button');
      titleInside.setAttribute('data-focus-key', 'view-title');
      titleInside.textContent = 'display none title';
      displayNoneWrap.append(titleInside);
      const visibilityWrap = document.createElement('div');
      visibilityWrap.style.visibility = 'hidden';
      const hiddenButton = document.createElement('button');
      hiddenButton.setAttribute('data-focus-key', 'preview-button');
      hiddenButton.style.visibility = 'hidden';
      hiddenButton.textContent = 'invisible button';
      visibilityWrap.append(hiddenButton);
      const zeroSize = document.createElement('button');
      zeroSize.setAttribute('data-focus-key', 'cancel-preview');
      zeroSize.style.display = 'block';
      zeroSize.style.width = '0';
      zeroSize.style.height = '0';
      zeroSize.style.padding = '0';
      zeroSize.style.border = '0';
      zeroSize.style.overflow = 'hidden';
      root.append(displayNoneWrap, visibilityWrap, zeroSize);
      return root;
    });
  });
  await page.evaluate(() => window.__labHarness.dispatch('goto', 'project'));
  const cssFallback = await page.evaluate(() => {
    const active = document.activeElement;
    return { variant: active.getAttribute && active.getAttribute('data-variant'), tabindex: active.tabIndex };
  });
  eq(cssFallback.variant, 'focus-probe-css', 'display:none target falls back to the root');
  eq(cssFallback.tabindex, -1, 'CSS fallback root is focusable');
  await page.evaluate(() => {
    const harness = window.__labHarness;
    harness.dispatch('select-response', 'simplify');
    harness.dispatch('preview');
    harness.dispatch('cancel-preview');
  });
  const visibilityFallback = await page.evaluate(() => document.activeElement.getAttribute && document.activeElement.getAttribute('data-variant'));
  eq(visibilityFallback, 'focus-probe-css', 'visibility:hidden ancestor/target and zero-geometry target are rejected');

  // Renderer return validation.
  const invalid = await page.evaluate(() => {
    const harness = window.__labHarness;
    const attempts = {
      fragment: () => document.createDocumentFragment(),
      text: () => 'plain text',
      svg: () => document.createElementNS('http://www.w3.org/2000/svg', 'svg'),
      number: () => 7,
    };
    const results = {};
    Object.keys(attempts).forEach((name) => {
      try { harness.setRenderer(attempts[name]); results[name] = 'no-error'; }
      catch (error) { results[name] = String(error.message); }
    });
    return results;
  });
  Object.keys(invalid).forEach((name) => {
    ok(/HTMLElement/.test(invalid[name]), `renderer returning ${name} is rejected (${invalid[name]})`);
  });
  await page.evaluate(() => window.__labHarness.dispatch('goto', 'overview'));
  eq(await page.locator('.focus-probe-css').count(), 1, 'renderer stays unchanged after invalid setRenderer attempts');

  // setRenderer renders exactly once and invalid results preserve DOM/state.
  const renderOnce = await page.evaluate(() => {
    const harness = window.__labHarness;
    let calls = 0;
    harness.setRenderer(() => {
      calls += 1;
      const root = document.createElement('div');
      root.className = 'count-probe';
      root.setAttribute('data-variant', 'count-probe');
      return root;
    });
    return { calls, installed: document.querySelectorAll('#game-surface > .count-probe').length };
  });
  eq(renderOnce.calls, 1, 'setRenderer invokes the renderer exactly once');
  eq(renderOnce.installed, 1, 'setRenderer installs exactly one new root');

  const preserved = await page.evaluate(() => {
    const harness = window.__labHarness;
    const domBefore = document.querySelector('#game-surface > [data-variant]').outerHTML;
    const stateBefore = JSON.stringify(harness.getState());
    let threw = false;
    try { harness.setRenderer(() => document.createDocumentFragment()); } catch (error) { threw = /HTMLElement/.test(String(error.message)); }
    return {
      threw,
      domSame: document.querySelector('#game-surface > [data-variant]').outerHTML === domBefore,
      stateSame: JSON.stringify(harness.getState()) === stateBefore,
    };
  });
  ok(preserved.threw, 'invalid renderer result is rejected');
  ok(preserved.domSame, 'invalid renderer result keeps the existing DOM');
  ok(preserved.stateSame, 'invalid renderer result keeps the shared state');
}

async function captureScreenshots(page) {
  log('capturing evidence screenshots');
  fs.mkdirSync(EVIDENCE, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 900 });
  await resetState(page);
  await gotoView(page, 'overview');
  await page.screenshot({ path: path.join(EVIDENCE, 'overview-desktop.png') });

  await gotoView(page, 'project');
  await page.getByTestId('work-bar').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(EVIDENCE, 'project-desktop.png') });

  await page.getByTestId('response-onboarding').first().click();
  await page.getByTestId('preview-button').first().click();
  await page.getByTestId('preview-panel').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(EVIDENCE, 'preview-desktop.png') });

  await gotoView(page, 'capabilities');
  await page.getByTestId('cap-list-automated-tests').first().click();
  await page.getByTestId('capability-graph').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(EVIDENCE, 'graph-desktop.png') });

  await page.setViewportSize({ width: 390, height: 844 });
  await resetState(page);
  await gotoView(page, 'project');
  await page.evaluate(() => { document.getElementById('game-surface').scrollTop = 0; });
  await page.screenshot({ path: path.join(EVIDENCE, 'project-narrow.png') });
  await page.getByTestId('work-bar').first().scrollIntoViewIfNeeded();
  await page.getByTestId('phase-track').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(EVIDENCE, 'signals-narrow.png') });
  await page.getByTestId('response-onboarding').first().click();
  await page.getByTestId('preview-button').first().click();
  await page.getByTestId('preview-panel').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(EVIDENCE, 'preview-narrow.png') });
  await page.setViewportSize({ width: 1440, height: 900 });
}

async function runCoreSetRenderer(page) {
  log('core: setRenderer preserves state/draft/entity');
  await resetState(page);
  await page.getByTestId('open-project').first().click();
  await page.getByTestId('response-onboarding').first().click();
  await page.getByTestId('preview-button').first().click();
  const before = await page.evaluate(() => JSON.stringify(window.__labHarness.getState()));
  await page.evaluate(() => {
    window.__labHarness.setRenderer((state) => {
      const probe = document.createElement('div');
      probe.setAttribute('data-variant', 'probe');
      probe.className = 'probe-renderer';
      probe.textContent = [state.view, state.selectedResponseId, state.previewFor, state.decisionStatus].join('|');
      return probe;
    });
  });
  const probeText = await page.locator('.probe-renderer').textContent();
  eq(probeText, 'project|onboarding|onboarding|open', 'setRenderer keeps view/draft/preview/status');
  const after = await page.evaluate(() => JSON.stringify(window.__labHarness.getState()));
  eq(after, before, 'setRenderer does not mutate shared state');
}

(async () => {
  const server = spawn(process.env.PYTHON || 'python3', [
    '-m', 'http.server', String(PORT), '--bind', '127.0.0.1', '--directory', REPO_ROOT,
  ], { stdio: 'ignore' });

  let browser;
  try {
    await waitForServer();
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const pageErrors = [];
    const consoleErrors = [];
    const externalRequests = [];
    page.on('pageerror', (error) => pageErrors.push(error.message));
    page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    page.on('request', (request) => {
      const url = request.url();
      if (url.startsWith('data:') || url.startsWith('blob:')) return;
      let origin = null;
      try {
        origin = new URL(url).origin;
      } catch (error) {
        externalRequests.push(url + ' (unparseable)');
        return;
      }
      if (origin !== HARNESS_ORIGIN) externalRequests.push(url + ' (origin ' + origin + ')');
    });

    await page.goto(HARNESS_URL);
    await waitForRoot(page);
    log(`mounted ${MODE}`);

    await runWorkflow(page);
    await runGuards(page);
    await runImmutability(page);
    await runInvalidActions(page);
    await runKeyboard(page);

    for (const [width, height, railWidth] of [[1440, 900, 280], [1024, 768, 280], [390, 844, 112]]) {
      await page.setViewportSize({ width, height });
      await page.waitForTimeout(60);
      await assertGeometry(page, MODE + ' ' + width + 'x' + height, railWidth);
    }
    await page.setViewportSize({ width: 1440, height: 900 });

    await captureScreenshots(page);
    eq(externalRequests.length, 0, `no external requests: ${externalRequests.join(', ')}`);
    eq(pageErrors.length, 0, `no page errors: ${pageErrors.join('; ')}`);
    eq(consoleErrors.length, 0, `no console errors: ${consoleErrors.join('; ')}`);

    if (core) {
      await runCoreSetRenderer(page);
      await runResetProbe(page);
      await runFocusProbes(page);
    }
    await runUnavailableProbe(page);

    fs.mkdirSync(EVIDENCE, { recursive: true });
    fs.writeFileSync(path.join(EVIDENCE, 'check.log'), logLines.join('\n') + '\nPASS ' + checks + ' checks\n');
    log('PASS — ' + checks + ' checks, evidence in ' + EVIDENCE);
    await context.close();
  } catch (error) {
    console.error(error);
    fs.mkdirSync(EVIDENCE, { recursive: true });
    try { fs.writeFileSync(path.join(EVIDENCE, 'check.log'), logLines.join('\n') + '\nFAIL ' + error.message + '\n'); } catch (writeError) { /* ignore */ }
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close().catch(() => {});
    server.kill('SIGTERM');
  }
})();
