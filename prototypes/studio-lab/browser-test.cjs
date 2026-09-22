// WP-UI-01I integration acceptance browser test.
// Self-contained: starts/stops its own stdlib static server on port 18771.
//
//   node --check prototypes/studio-lab/lab.js
//   node --check prototypes/studio-lab/fixtures.js
//   NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
//     SCREENSHOT_DIR=/tmp/opencode/gamedev-ui-lab \
//     node prototypes/studio-lab/browser-test.cjs
//
// Exercises the visible integrated lab: five preloaded candidates through one
// shared mount, fixed right rail with feedback storage/export/reset, state
// retention across synchronous switches, real keyboard operation, storage failure
// handling, CSS isolation, geometry/overflow and focus clearance at
// 1440x900 / 1024x768 / 390x844. Playwright is dev-only and lives outside the repo.

const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const PORT = Number(process.env.LAB_PORT || 18771);
const BASE = `http://127.0.0.1:${PORT}/prototypes/studio-lab/`;
const SHOT_DIR = process.env.SCREENSHOT_DIR || '/tmp/opencode/gamedev-ui-lab';
const STORAGE_KEY = 'studio-rewrite-ui-lab-v1';

const RESPONSES = {
  simplify: {
    label: 'Simplify branching',
    baselineCash: '$84,000 now',
    proposedCash: '$80,000 after · runway 6.7 months',
    baselineEstimate: '8–11 weeks now',
    proposedEstimate: '7–9 weeks after',
    baselineScope: '100% of baseline now',
    proposedScope: '92% of baseline after',
    spend: '$4,000',
    tradeoff: 'Some core fans may miss depth; onboarding improvement unverified',
    commitCash: 'Cash $80,000',
    commitRunway: 'Runway 6.7 months',
    commitEstimate: '7–9 weeks',
    commitScope: '92% of baseline',
  },
  onboarding: {
    label: 'Build guided introduction',
    baselineCash: '$84,000 now',
    proposedCash: '$72,000 after · runway 6.0 months',
    baselineEstimate: '8–11 weeks now',
    proposedEstimate: '10–13 weeks after',
    baselineScope: '100% of baseline now',
    proposedScope: '100% of baseline after',
    spend: '$12,000',
    tradeoff: 'Keeps depth, costs time/runway; integration untested',
    commitCash: 'Cash $72,000',
    commitRunway: 'Runway 6.0 months',
    commitEstimate: '10–13 weeks',
    commitScope: '100% of baseline',
  },
  hold: {
    label: 'Keep current plan',
    baselineCash: '$84,000 now',
    proposedCash: '$84,000 after · runway 7.0 months',
    baselineEstimate: '8–11 weeks now',
    proposedEstimate: '8–11 weeks after',
    baselineScope: '100% of baseline now',
    proposedScope: '100% of baseline after',
    spend: '$0',
    tradeoff: 'Preserves schedule, newcomer friction unresolved',
    commitCash: 'Cash $84,000',
    commitRunway: 'Runway 7.0 months',
    commitEstimate: '8–11 weeks',
    commitScope: '100% of baseline',
  },
};

const VARIANT_NAMES = ['Ops Deck', 'Field Notes', 'Board Map', 'Timeline Table', 'Command Board'];

let checks = 0;
function ok(condition, message) {
  checks += 1;
  assert.ok(condition, message);
}
function eq(actual, expected, message) {
  checks += 1;
  assert.equal(actual, expected, message);
}
function log(message) {
  process.stdout.write(`[integration-test] ${message}\n`);
}
function norm(text) {
  return (text || '').replace(/\s+/g, ' ').trim();
}

async function waitForServer() {
  for (let i = 0; i < 120; i++) {
    try {
      const res = await fetch(BASE);
      if (res.ok) return;
    } catch (error) { /* not up yet */ }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('stdlib static server did not start on port ' + PORT);
}

// ------------------------------------------------------------------ DOM helpers

async function textOf(page, testid, index = 0) {
  const locator = page.getByTestId(testid).nth(index);
  await locator.waitFor({ state: 'attached', timeout: 8000 });
  return norm(await locator.textContent());
}
async function assertText(page, testid, expected, label) {
  const actual = await textOf(page, testid);
  eq(actual, expected, `${label || testid}: expected "${expected}" got "${actual}"`);
}
async function assertContainsText(page, testid, needle, label) {
  const actual = await textOf(page, testid);
  ok(actual.includes(needle), `${label || testid}: expected to contain "${needle}" got "${actual}"`);
}
async function waitForBoot(page) {
  await page.locator('#game-surface > [data-variant]').first().waitFor({ state: 'attached', timeout: 10000 });
  await page.getByTestId('selected-variant').waitFor({ state: 'attached', timeout: 10000 });
}
async function assertNoStalePending(page, expected, label) {
  const surface = norm(await page.locator('#game-surface').innerText());
  ok(!/decision pending/i.test(surface), `${label}: no stale "decision pending" text`);
  if (expected) ok(new RegExp(expected, 'i').test(surface), `${label}: surface shows ${expected}`);
}

async function assertOnlyVariant(page, n) {
  const info = await page.evaluate(() => {
    const surface = document.getElementById('game-surface');
    const roots = Array.from(surface.querySelectorAll(':scope > [data-variant]'));
    return {
      roots: roots.map((node) => {
        const rect = node.getBoundingClientRect();
        return {
          variant: node.getAttribute('data-variant'),
          width: rect.width,
          height: rect.height,
          visible: getComputedStyle(node).display !== 'none' && rect.width > 0 && rect.height > 0,
        };
      }),
      allVariantNodes: document.querySelectorAll('[data-variant]').length,
    };
  });
  eq(info.roots.length, 1, `variant ${n}: expected exactly one root in #game-surface`);
  eq(info.roots[0].variant, String(n), `variant ${n}: wrong root rendered`);
  ok(info.roots[0].visible, `variant ${n}: root is not visible`);
  eq(info.allVariantNodes, 1, `variant ${n}: no hidden duplicate candidate roots anywhere`);
}

async function activeInfo(page) {
  return page.evaluate(() => {
    const active = document.activeElement;
    if (!active) return null;
    const style = getComputedStyle(active);
    return {
      tag: active.tagName,
      id: active.id || null,
      testid: active.getAttribute ? active.getAttribute('data-testid') : null,
      key: active.getAttribute ? active.getAttribute('data-focus-key') : null,
      variantBtn: active.getAttribute ? active.getAttribute('data-variant-btn') : null,
      inSurface: Boolean(active.closest && active.closest('#game-surface')),
      focusVisible: active.matches(':focus-visible'),
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
    };
  });
}

async function tabTo(page, match, maxTabs = 200) {
  for (let index = 0; index <= maxTabs; index++) {
    const info = await activeInfo(page);
    if (info && match(info)) return info;
    await page.keyboard.press('Tab');
  }
  return null;
}

async function assertKeyboardFocus(page, expected, label) {
  const info = await activeInfo(page);
  const matches = info && (
    (expected.key !== undefined && info.key === expected.key)
    || (expected.testid !== undefined && info.testid === expected.testid)
    || (expected.id !== undefined && info.id === expected.id)
    || (expected.variantBtn !== undefined && info.variantBtn === expected.variantBtn)
  );
  ok(matches, `${label}: expected focus ${JSON.stringify(expected)} got ${JSON.stringify(info)}`);
  ok(info && info.focusVisible, `${label}: focused element matches :focus-visible`);
  ok(info && info.outlineStyle !== 'none' && parseFloat(info.outlineWidth || '0') > 0,
    `${label}: visible focus outline (${info && info.outlineStyle} ${info && info.outlineWidth})`);
}

async function switchVariant(page, n) {
  await page.getByRole('button', { name: `Variant ${n}`, exact: true }).click();
  await assertOnlyVariant(page, n);
  const selectedLabel = await textOf(page, 'selected-variant');
  ok(selectedLabel.includes(`Variant ${n}`), `rail identifies selected variant ${n} (got "${selectedLabel}")`);
  ok(selectedLabel.includes(VARIANT_NAMES[n - 1]), `rail names variant ${n} "${VARIANT_NAMES[n - 1]}" (got "${selectedLabel}")`);
  const focused = await page.evaluate(() => (document.activeElement && document.activeElement.getAttribute
    ? document.activeElement.getAttribute('data-variant-btn') : null));
  eq(focused, String(n), `rail focus stays on the variant ${n} button after switching`);
}

async function resetFixture(page) {
  await page.locator('#reset-fixture').click();
}
async function openOverview(page) {
  await page.getByTestId('open-overview').first().click();
  await page.getByTestId('decision-flag').first().waitFor({ state: 'attached', timeout: 8000 });
}
async function openProject(page) {
  await page.getByTestId('open-project').first().click();
  await page.getByTestId('project-name').first().waitFor({ state: 'attached', timeout: 8000 });
}
async function selectResponse(page, id) {
  await page.getByTestId(`response-${id}`).first().click();
}
async function openPreview(page) {
  await page.getByTestId('preview-button').first().click();
  await page.getByTestId('preview-panel').first().waitFor({ state: 'attached', timeout: 8000 });
}
async function cancelPreview(page) {
  await page.getByTestId('cancel-preview').first().click();
  eq(await page.getByTestId('preview-panel').count(), 0, 'cancel preview closes the panel');
}

async function assertPreview(page, id) {
  const expected = RESPONSES[id];
  await assertText(page, 'preview-baseline-cash', expected.baselineCash, `${id} baseline cash`);
  await assertText(page, 'preview-proposed-cash', expected.proposedCash, `${id} proposed cash/runway`);
  await assertText(page, 'preview-baseline-estimate', expected.baselineEstimate, `${id} baseline estimate`);
  await assertText(page, 'preview-proposed-estimate', expected.proposedEstimate, `${id} proposed estimate`);
  await assertText(page, 'preview-baseline-scope', expected.baselineScope, `${id} baseline scope`);
  await assertText(page, 'preview-proposed-scope', expected.proposedScope, `${id} proposed scope`);
  await assertText(page, 'preview-spend', expected.spend, `${id} immediate spend`);
  await assertText(page, 'preview-tradeoff', expected.tradeoff, `${id} residual tradeoff`);
  await assertText(page, 'metric-cash', 'Cash $84,000', `${id}: preview does not spend`);
  await assertText(page, 'metric-runway', 'Runway 7.0 months', `${id}: preview keeps committed runway`);
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
      currentWidth: current ? current.getBoundingClientRect().width : 0,
    };
  });
  ok(phase, `${label}: phase track present`);
  ok(phase.steps >= 5, `${label}: phase track segmented`);
  ok(/Production/.test(phase.aria) && /Production/.test(phase.currentText), `${label}: Production labeled current`);
  ok(phase.currentWidth > 0, `${label}: current phase segment visible`);

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
    const cue = page.getByTestId(`confidence-${findingId}`).first();
    eq(await cue.getAttribute('data-confidence'), category, `${label}: confidence-${findingId} category`);
    const aria = await cue.getAttribute('aria-label');
    ok(new RegExp(category, 'i').test(aria), `${label}: confidence-${findingId} label (${aria})`);
    const box = await cue.boundingBox();
    ok(box && box.width > 0 && box.height > 0, `${label}: confidence-${findingId} visible shape`);
    ok(!/\d+\s*%/.test(await cue.innerText()), `${label}: confidence-${findingId} has no fabricated odds`);
    const findingText = await textOf(page, `finding-${findingId}`);
    ok(findingText.includes('Source:'), `${label}: finding-${findingId} shows its source`);
    ok(/May 2031/.test(findingText), `${label}: finding-${findingId} shows date/history`);
  }
}

// Cross-cutting geometry: rail reservation, page/surface/scroller overflow and
// focus-outline clearance below any sticky/fixed HUD wrapper.
async function assertRailGeometry(page, label, expectedRail) {
  const g = await page.evaluate(() => {
    const rail = document.getElementById('review-rail');
    const surface = document.getElementById('game-surface');
    const railRect = rail.getBoundingClientRect();
    const gameRect = surface.getBoundingClientRect();
    const root = surface.querySelector(':scope > [data-variant]');
    const rootRect = root ? root.getBoundingClientRect() : null;
    const buttons = Array.from(document.querySelectorAll('[data-variant-btn]')).map((button) => {
      const rect = button.getBoundingClientRect();
      return { width: rect.width, height: rect.height };
    });
    const scrollers = [];
    surface.querySelectorAll('*').forEach((node) => {
      const style = getComputedStyle(node);
      if (style.overflowX !== 'auto' && style.overflowX !== 'scroll') return;
      const rect = node.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;
      scrollers.push({
        cls: String(node.className).slice(0, 60),
        left: rect.left,
        right: rect.right,
        clientWidth: node.clientWidth,
      });
    });
    return {
      rail: { left: railRect.left, right: railRect.right, width: railRect.width, clientWidth: rail.clientWidth, scrollWidth: rail.scrollWidth },
      game: { left: gameRect.left, right: gameRect.right, width: gameRect.width },
      surfaceClientWidth: surface.clientWidth,
      surfaceScrollWidth: surface.scrollWidth,
      root: rootRect ? { left: rootRect.left, right: rootRect.right } : null,
      buttons,
      scrollers,
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      docScrollWidth: document.documentElement.scrollWidth,
      docScrollHeight: document.documentElement.scrollHeight,
    };
  });
  ok(g.rail.right <= g.innerWidth + 1, `${label}: rail must not extend past viewport`);
  ok(g.game.right <= g.rail.left + 1, `${label}: game surface must not sit under the rail`);
  ok(Math.abs(g.rail.width + g.game.width - g.innerWidth) < 2, `${label}: rail + game consume viewport width`);
  eq(Math.round(g.rail.width), expectedRail, `${label}: reserved rail width`);
  ok(g.docScrollWidth <= g.innerWidth + 1, `${label}: no horizontal page overflow (${g.docScrollWidth} > ${g.innerWidth})`);
  ok(g.docScrollHeight <= g.innerHeight + 1, `${label}: page itself must not scroll`);
  ok(g.rail.scrollWidth <= g.rail.clientWidth + 1, `${label}: rail controls cannot spill horizontally`);
  ok(g.surfaceScrollWidth <= g.surfaceClientWidth + 1,
    `${label}: game surface horizontal overflow (${g.surfaceScrollWidth} > ${g.surfaceClientWidth})`);
  ok(g.root && g.root.left >= g.game.left - 1 && g.root.right <= g.game.right + 1,
    `${label}: candidate root fits inside the game surface (${JSON.stringify(g.root)})`);
  g.scrollers.forEach((scroller) => {
    ok(scroller.clientWidth <= g.surfaceClientWidth + 1,
      `${label}: internal scroller ${scroller.cls} is not wider than the surface`);
    ok(scroller.left >= g.game.left - 1 && scroller.right <= g.game.right + 1,
      `${label}: internal scroller ${scroller.cls} stays inside the surface`);
  });
  g.buttons.forEach((button, index) => {
    ok(button.width >= 39.5 && button.height >= 39.5,
      `${label}: variant button ${index + 1} target ${button.width}x${button.height} < 40x40`);
  });
}

async function assertFocusClearance(page, label) {
  const info = await page.evaluate(() => {
    const active = document.activeElement;
    const surface = document.getElementById('game-surface');
    if (!active || !surface || !surface.contains(active)) return { error: 'focus not inside game surface' };
    const rect = active.getBoundingClientRect();
    const style = getComputedStyle(active);
    const outlineWidth = parseFloat(style.outlineWidth) || 0;
    const outlineOffset = parseFloat(style.outlineOffset) || 0;
    const focusVisible = active.matches(':focus-visible');
    const pad = (focusVisible ? outlineWidth + outlineOffset : 0) + 1;
    const box = { top: rect.top - pad, bottom: rect.bottom + pad, left: rect.left - pad, right: rect.right + pad };
    const blockers = [];
    surface.querySelectorAll('*').forEach((node) => {
      const cs = getComputedStyle(node);
      if (cs.position !== 'sticky' && cs.position !== 'fixed') return;
      if (!node.querySelector('[data-testid="date"]') && node.getAttribute('data-testid') !== 'date') return;
      const r = node.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) return;
      const overlaps = r.left < box.right && r.right > box.left && r.top < box.bottom && r.bottom > box.top;
      if (overlaps) {
        blockers.push({ cls: String(node.className).slice(0, 60), top: Math.round(r.top), bottom: Math.round(r.bottom), activeTop: Math.round(rect.top) });
      }
    });
    return {
      key: active.getAttribute('data-focus-key'),
      testid: active.getAttribute('data-testid'),
      focusVisible,
      outlineStyle: style.outlineStyle,
      outlineWidth,
      blockers,
    };
  });
  ok(!info.error, `${label}: ${info.error || 'focus inside the game surface'}`);
  if (info.error) return;
  eq(info.blockers.length, 0,
    `${label}: focused ${info.key || info.testid} is clear of sticky HUD (${JSON.stringify(info.blockers)})`);
  ok(!info.focusVisible || (info.outlineStyle !== 'none' && info.outlineWidth > 0),
    `${label}: focus outline visible (${info.outlineStyle} ${info.outlineWidth})`);
}

// ------------------------------------------------------------ variant workflows

async function runVariantWorkflow(page, n) {
  log(`variant ${n}: full visible workflow`);
  await page.setViewportSize({ width: 1440, height: 900 });
  await resetFixture(page);
  await switchVariant(page, n);
  await openOverview(page);

  await assertText(page, 'date', '18 May 2031', `v${n}: paused date`);
  await assertText(page, 'metric-cash', 'Cash $84,000', `v${n}: overview cash`);
  await assertText(page, 'metric-runway', 'Runway 7.0 months', `v${n}: overview runway`);
  await assertText(page, 'decision-flag', 'Unresolved onboarding decision', `v${n}: unresolved decision`);
  await assertText(page, 'decision-status', 'Open — no response committed', `v${n}: initial status`);
  const overviewText = norm(await page.locator('#game-surface').innerText());
  ok(overviewText.includes('Northstar Works'), `v${n}: overview shows studio identity`);
  ok(overviewText.includes('Paper Harbor'), `v${n}: overview mentions Paper Harbor`);
  ok(await page.getByTestId('open-capabilities').first().isVisible(), `v${n}: capability navigation visible on overview`);

  await openProject(page);
  await assertText(page, 'project-name', 'Signal Drift', `v${n}: project name`);
  await assertText(page, 'decision-flag', 'Unresolved onboarding decision', `v${n}: open flag wording on project`);
  eq(await page.getByTestId('pillar').count(), 3, `v${n}: three pillars`);
  await assertIndicatorGraphics(page, `v${n} project`);
  await assertText(page, 'finish-estimate', '8–11 weeks', `v${n}: initial finish estimate`);
  await assertText(page, 'scope-baseline', '100% of baseline', `v${n}: initial scope baseline`);
  await assertConfidence(page, `v${n} project`);
  eq(await page.getByTestId('history-entry').count(), 0, `v${n}: no history before decisions`);

  // Compare every response; cancel each preview without spending.
  for (const id of ['simplify', 'onboarding', 'hold']) {
    await selectResponse(page, id);
    eq(await page.getByTestId(`response-${id}`).getAttribute('aria-pressed'), 'true', `v${n}: ${id} selected`);
    eq(await page.getByTestId('confirm-button').isDisabled(), true, `v${n}: ${id} confirm disabled until preview`);
    await openPreview(page);
    eq(await page.getByTestId('confirm-button').isDisabled(), false, `v${n}: ${id} confirm enabled after preview`);
    await assertPreview(page, id);
    await cancelPreview(page);
    await assertText(page, 'decision-status', 'Open — no response committed', `v${n}: ${id} cancel keeps decision open`);
    eq(await page.getByTestId('history-entry').count(), 0, `v${n}: ${id} preview/cancel is not a history event`);
  }

  // Defer -> reopen -> reject -> reopen.
  await selectResponse(page, 'onboarding');
  await page.getByTestId('defer-button').first().click();
  await assertText(page, 'decision-status', 'Deferred — revisit before validation', `v${n}: deferred status`);
  await assertText(page, 'metric-cash', 'Cash $84,000', `v${n}: defer keeps cash`);
  eq(await page.getByTestId('history-entry').count(), 1, `v${n}: defer recorded once`);
  ok((await textOf(page, 'history-entry')).includes('Deferred'), `v${n}: defer history kind`);
  await assertNoStalePending(page, 'deferred', `v${n}: defer labels`);
  await assertText(page, 'decision-flag', 'Deferred: Build guided introduction — revisit before validation', `v${n}: defer flag on project`);
  await openOverview(page);
  await assertContainsText(page, 'decision-flag', 'Deferred: Build guided introduction', `v${n}: defer flag on overview`);
  await openProject(page);

  await page.getByTestId('reopen-button').first().click();
  await assertText(page, 'decision-status', 'Open — no response committed', `v${n}: reopened status`);
  eq(await page.getByTestId('history-entry').count(), 2, `v${n}: reopen recorded`);

  await selectResponse(page, 'simplify');
  await page.getByTestId('reject-button').first().click();
  await assertText(page, 'decision-status', 'Response rejected — original risk remains', `v${n}: rejected status`);
  await assertText(page, 'metric-cash', 'Cash $84,000', `v${n}: reject keeps cash`);
  eq(await page.getByTestId('history-entry').count(), 3, `v${n}: reject recorded`);
  await assertNoStalePending(page, 'rejected', `v${n}: reject labels`);
  await assertText(page, 'decision-flag', 'Rejected: Simplify branching — original risk remains', `v${n}: reject flag on project`);
  await openOverview(page);
  await assertContainsText(page, 'decision-flag', 'Rejected: Simplify branching', `v${n}: reject flag on overview`);
  await openProject(page);

  await page.getByTestId('reopen-button').first().click();
  await selectResponse(page, 'simplify');
  await openPreview(page);
  await assertPreview(page, 'simplify');
  await page.getByTestId('confirm-button').first().click();
  await assertText(page, 'decision-status', 'Committed', `v${n}: committed status`);
  await assertText(page, 'metric-cash', 'Cash $80,000', `v${n}: committed cash`);
  await assertText(page, 'metric-runway', 'Runway 6.7 months', `v${n}: committed runway`);
  await assertText(page, 'finish-estimate', '7–9 weeks', `v${n}: committed estimate`);
  await assertText(page, 'scope-baseline', '92% of baseline', `v${n}: committed scope`);
  await assertText(page, 'readiness-text', 'At risk — follow-up validation needed', `v${n}: readiness stays at risk`);
  eq(await page.getByTestId('readiness').first().getAttribute('aria-label'), 'Readiness: At risk',
    `v${n}: readiness keeps its categorical accessible name`);
  await assertContainsText(page, 'decision-result', 'Decision committed: Simplify branching', `v${n}: commit acknowledgement`);
  await assertNoStalePending(page, 'committed', `v${n}: committed labels`);
  eq(await page.getByTestId('history-entry').count(), 5, `v${n}: history after defer/reject/reopen/commit`);
  await assertText(page, 'decision-flag', 'Committed: Simplify branching', `v${n}: commit flag on project`);

  // Duplicate guard: locked controls cannot move data.
  for (const testid of ['preview-button', 'confirm-button', 'defer-button', 'reject-button']) {
    eq(await page.getByTestId(testid).isDisabled(), true, `v${n}: ${testid} locked after commit`);
  }
  for (const id of ['simplify', 'onboarding', 'hold']) {
    eq(await page.getByTestId(`response-${id}`).isDisabled(), true, `v${n}: response ${id} locked after commit`);
  }
  eq(await page.getByTestId('reopen-button').count(), 0, `v${n}: reopen not offered after commit`);
  await page.evaluate(() => {
    document.querySelector('[data-testid="confirm-button"]').click();
    document.querySelector('[data-testid="preview-button"]').click();
  });
  await assertText(page, 'metric-cash', 'Cash $80,000', `v${n}: forced duplicate commit did not spend again`);
  eq(await page.getByTestId('history-entry').count(), 5, `v${n}: forced duplicate produced no history`);

  // Overview reflects the committed decision without invented success.
  await openOverview(page);
  await assertText(page, 'metric-cash', 'Cash $80,000', `v${n}: overview cash after commit`);
  await assertText(page, 'decision-status', 'Committed', `v${n}: overview status after commit`);
  await assertContainsText(page, 'committed-plan', 'Simplify branching', `v${n}: overview committed plan`);
  await assertContainsText(page, 'decision-flag', 'Committed: Simplify branching', `v${n}: commit flag on overview`);
  const committedSurface = norm(await page.locator('#game-surface').innerText());
  ok(!/victory|breakthrough|commercial success/i.test(committedSurface), `v${n}: no invented commercial success`);

  // Person inspection returns to the project without losing state.
  await page.getByTestId('open-person').first().click();
  await assertText(page, 'person-name', 'Mina Rao', `v${n}: person name`);
  const traits = await textOf(page, 'person-traits');
  ok(traits.includes('Methodical') && traits.includes('needs validation time'), `v${n}: Mina trait 1`);
  ok(traits.includes('Mentor') && traits.includes('coaching consumes delivery capacity'), `v${n}: Mina trait 2`);
  await assertContainsText(page, 'person-commitment', 'Signal Drift integration', `v${n}: Mina commitment`);
  await assertText(page, 'date', '18 May 2031', `v${n}: paused date while inspecting a person`);
  await openProject(page);
  await assertText(page, 'metric-cash', 'Cash $80,000', `v${n}: cash retained after person inspection`);
  await assertText(page, 'decision-status', 'Committed', `v${n}: decision retained after person inspection`);

  // Other product support obligation.
  await page.getByTestId('open-product').first().click();
  await assertContainsText(page, 'support-obligation', 'Compatibility fix promised by 2 June', `v${n}: support promise`);
  await assertContainsText(page, 'support-obligation', 'One engineer-week reserved', `v${n}: support reservation`);
  ok(norm(await page.locator('#game-surface').innerText()).includes('competes with ongoing Signal Drift production'),
    `v${n}: support opportunity cost`);
  await assertText(page, 'date', '18 May 2031', `v${n}: paused date on product`);
  await openProject(page);
  await assertText(page, 'project-name', 'Signal Drift', `v${n}: project after product inspection`);

  // Postmortem.
  await page.getByTestId('open-postmortem').first().click();
  await assertContainsText(page, 'pm-schedule', 'planned 20 weeks → actual 24 weeks', `v${n}: postmortem schedule`);
  await assertContainsText(page, 'pm-budget', 'expected $60,000 → actual $68,000', `v${n}: postmortem budget`);
  await assertContainsText(page, 'pm-receipts', 'expected $100,000 → observed $92,000', `v${n}: postmortem receipts`);
  await assertContainsText(page, 'pm-fees', '$22,000', `v${n}: postmortem fees`);
  await assertContainsText(page, 'pm-net', '$70,000', `v${n}: postmortem net receipts`);
  await assertContainsText(page, 'pm-contribution', '$2,000 after $68,000 tracked cost', `v${n}: postmortem contribution`);
  const factors = (await page.getByTestId('factor').allTextContents()).map(norm);
  eq(factors.length, 3, `v${n}: three qualified factors`);
  ok(factors.some((t) => t.includes('small sample')), `v${n}: factor small sample qualification`);
  ok(factors.some((t) => t.includes('recorded work history')), `v${n}: factor recorded history`);
  ok(factors.some((t) => t.includes('may explain') && t.includes('evidence incomplete')), `v${n}: factor uncertainty`);
  await assertText(page, 'date', '18 May 2031', `v${n}: paused date on postmortem`);

  // Capabilities: graph, keyboard list, prerequisites, inspection-only.
  await page.getByTestId('open-capabilities').first().click();
  eq(await page.getByTestId('capability-list').locator('button').count(), 5, `v${n}: five capability buttons`);
  const capabilityNames = await textOf(page, 'capability-list');
  ['Repeatable builds', 'Automated tests', 'Safe release train', 'Community practice', 'Incident process']
    .forEach((name) => ok(capabilityNames.includes(name), `v${n}: capability list has ${name}`));
  const graphCount = await page.getByTestId('capability-graph').count();
  ok(graphCount >= 1, `v${n}: connected capability view present`);
  await page.getByTestId('cap-list-automated-tests').first().click();
  await assertContainsText(page, 'cap-detail', 'Detects regressions, not design fun', `v${n}: automated tests detail`);
  await assertContainsText(page, 'cap-detail', 'Reserve $6,000 and 2 engineer-weeks', `v${n}: automated tests cost`);
  await assertContainsText(page, 'cap-note', 'Inspection only', `v${n}: inspection-only note`);
  await page.getByTestId('cap-list-safe-release-train').first().click();
  await assertContainsText(page, 'cap-and', 'Automated tests AND Incident process', `v${n}: AND prerequisite`);
  await assertContainsText(page, 'cap-detail', 'Locked', `v${n}: locked state visible`);
  await page.getByTestId('cap-list-incident-process').first().click();
  await assertContainsText(page, 'cap-detail', 'Reserve $3,000 and 1 lead-week', `v${n}: incident process cost`);
  await assertContainsText(page, 'cap-detail', 'competes with current production', `v${n}: incident process tradeoff`);
  await assertText(page, 'date', '18 May 2031', `v${n}: paused date on capabilities`);

  // Exact committed effects for all three responses.
  for (const id of ['simplify', 'onboarding', 'hold']) {
    const expected = RESPONSES[id];
    await resetFixture(page);
    await openProject(page);
    await selectResponse(page, id);
    await openPreview(page);
    await assertPreview(page, id);
    await page.getByTestId('confirm-button').first().click();
    await assertText(page, 'metric-cash', expected.commitCash, `v${n} ${id}: committed cash`);
    await assertText(page, 'metric-runway', expected.commitRunway, `v${n} ${id}: committed runway`);
    await assertText(page, 'finish-estimate', expected.commitEstimate, `v${n} ${id}: committed estimate`);
    await assertText(page, 'scope-baseline', expected.commitScope, `v${n} ${id}: committed scope`);
    await assertText(page, 'decision-status', 'Committed', `v${n} ${id}: committed status`);
    await assertText(page, 'decision-flag', `Committed: ${expected.label}`, `v${n} ${id}: commit flag on project`);
    await openOverview(page);
    await assertText(page, 'metric-cash', expected.commitCash, `v${n} ${id}: overview cash`);
    await assertText(page, 'decision-flag', `Committed: ${expected.label}`, `v${n} ${id}: commit flag on overview`);
  }
  await resetFixture(page);

  // Geometry, surface/scroller overflow and focus-outline clearance.
  for (const [width, height, railWidth] of [[1440, 900, 280], [1024, 768, 280], [390, 844, 112]]) {
    await page.setViewportSize({ width, height });
    await page.waitForTimeout(80);
    await assertOnlyVariant(page, n);
    await assertRailGeometry(page, `v${n} ${width}x${height}`, railWidth);
    await assertText(page, 'date', '18 May 2031', `v${n} ${width}x${height}: paused date`);
    await openProject(page);
    await assertFocusClearance(page, `v${n} ${width}x${height}: view heading`);
    await selectResponse(page, 'simplify');
    await assertFocusClearance(page, `v${n} ${width}x${height}: selected response`);
    await resetFixture(page);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
}

// ------------------------------------------------- state retention and switching

async function runSwitchingPreservation(page) {
  log('switching: mid-preview, deferred/rejected, post-commit, person, capability');
  await page.setViewportSize({ width: 1440, height: 900 });
  await resetFixture(page);
  await switchVariant(page, 1);
  await openProject(page);
  await selectResponse(page, 'onboarding');
  await openPreview(page);

  for (const n of [2, 3, 4, 5]) {
    await switchVariant(page, n);
    await assertText(page, 'preview-proposed-cash', RESPONSES.onboarding.proposedCash, `v${n}: preview retained after switch`);
    eq(await page.getByTestId('response-onboarding').getAttribute('aria-pressed'), 'true', `v${n}: selected response retained`);
    await assertText(page, 'date', '18 May 2031', `v${n}: paused date after switch`);
  }

  // One same-task click proves the swap is synchronous with all modules preloaded.
  const syncVariant = await page.evaluate(() => {
    document.querySelector('[data-variant-btn="4"]').click();
    return document.querySelector('#game-surface > [data-variant]').getAttribute('data-variant');
  });
  eq(syncVariant, '4', 'variant swap renders synchronously inside the same task');
  await assertText(page, 'preview-proposed-cash', RESPONSES.onboarding.proposedCash, 'v4: preview after synchronous swap');

  await switchVariant(page, 1);
  await assertText(page, 'preview-proposed-cash', RESPONSES.onboarding.proposedCash, 'v1: preview retained after round trip');
  await page.getByTestId('confirm-button').first().click();
  for (const n of [2, 3, 4, 5, 1]) {
    await switchVariant(page, n);
    await assertText(page, 'decision-status', 'Committed', `v${n}: committed status after switch`);
    await assertText(page, 'metric-cash', 'Cash $72,000', `v${n}: committed onboarding cash after switch`);
    await assertText(page, 'finish-estimate', '10–13 weeks', `v${n}: committed onboarding estimate after switch`);
    await assertText(page, 'scope-baseline', '100% of baseline', `v${n}: committed onboarding scope after switch`);
    eq(await page.getByTestId('confirm-button').isDisabled(), true, `v${n}: duplicate commit blocked after switch`);
  }

  // Deferred and rejected decisions keep their guard across switches.
  await resetFixture(page);
  await switchVariant(page, 5);
  await openProject(page);
  await selectResponse(page, 'hold');
  await page.getByTestId('defer-button').first().click();
  for (const n of [1, 2]) {
    await switchVariant(page, n);
    await assertText(page, 'decision-status', 'Deferred — revisit before validation', `v${n}: deferred status retained`);
    eq(await page.getByTestId('reopen-button').isEnabled(), true, `v${n}: reopen available for deferred decision`);
    eq(await page.getByTestId('preview-button').isDisabled(), true, `v${n}: deferred decision still open-only`);
  }
  await page.getByTestId('reopen-button').first().click();
  await selectResponse(page, 'hold');
  await page.getByTestId('reject-button').first().click();
  await switchVariant(page, 3);
  await assertText(page, 'decision-status', 'Response rejected — original risk remains', 'v3: rejected status retained');
  await assertContainsText(page, 'decision-flag', 'Rejected: Keep current plan', 'v3: rejected flag retained');
  eq(await page.getByTestId('history-entry').count(), 3, 'v3: defer + reopen + reject history retained');
  await page.getByTestId('reopen-button').first().click();
  await assertText(page, 'decision-status', 'Open — no response committed', 'v3: reopen after switch works');

  // Person context with a half-selected response.
  await resetFixture(page);
  await switchVariant(page, 2);
  await openProject(page);
  await selectResponse(page, 'simplify');
  await page.getByTestId('open-person').first().click();
  for (const n of [3, 4, 5, 1]) {
    await switchVariant(page, n);
    await assertText(page, 'person-name', 'Mina Rao', `v${n}: person context retained on switch`);
    await assertText(page, 'date', '18 May 2031', `v${n}: paused date in person context`);
  }
  await openProject(page);
  eq(await page.getByTestId('response-simplify').getAttribute('aria-pressed'), 'true', 'half-selected response retained');
  await assertText(page, 'decision-status', 'Open — no response committed', 'decision still open after person inspection');

  // Capability selection retained across switches.
  await page.getByTestId('open-capabilities').first().click();
  await page.getByTestId('cap-list-incident-process').first().click();
  for (const n of [2, 4]) {
    await switchVariant(page, n);
    await assertContainsText(page, 'cap-detail', 'Reserve $3,000 and 1 lead-week', `v${n}: selected capability retained`);
    eq(await page.getByTestId('cap-list-incident-process').getAttribute('aria-pressed'), 'true',
      `v${n}: capability list marks the retained selection`);
  }
  await resetFixture(page);
}

// ------------------------------------------------- rail typing must not act on game

async function runRailTypingIsolation(page) {
  log('rail typing: no game action, no surface rerender');
  await resetFixture(page);
  await switchVariant(page, 1);
  await openProject(page);
  await selectResponse(page, 'onboarding');
  await page.evaluate(() => {
    window.__integrationRootProbe = document.querySelector('#game-surface > [data-variant]');
  });

  const overall = page.getByLabel('Overall feedback', { exact: true });
  await overall.click();
  await page.keyboard.type('2 p c d r o 1 3 confirm defer reject reopen');
  eq(await page.evaluate(() => document.activeElement.id), 'overall-feedback', 'typing focus stays in the rail textarea');
  await assertText(page, 'decision-status', 'Open — no response committed', 'shortcut-looking typing did not decide');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'shortcut-looking typing did not spend');
  eq(await page.getByTestId('preview-panel').count(), 0, 'shortcut-looking typing did not open a preview');
  eq(await page.getByTestId('response-onboarding').getAttribute('aria-pressed'), 'true', 'rail typing did not change the draft');
  eq(await page.evaluate(() => document.querySelector('#game-surface > [data-variant]') === window.__integrationRootProbe), true,
    'rail typing did not rerender the candidate surface');
  await overall.fill('');
  await resetFixture(page);
}

// ------------------------------------------------------------- feedback contract

async function runFeedbackTests(page) {
  log('feedback: save/switch/reload/export/literal markup/clear/reset distinctions');
  await page.evaluate((key) => localStorage.removeItem(key), STORAGE_KEY);
  await page.reload();
  await waitForBoot(page);
  await switchVariant(page, 1);
  eq(await page.locator('#clear-confirm').isHidden(), true, 'clear confirmation hidden until requested');
  eq(await page.locator('#storage-warning').isHidden(), true, 'no storage warning with empty storage');

  const rating = page.getByLabel('Variant rating', { exact: true });
  const comment = page.getByLabel('Variant feedback', { exact: true });
  const overall = page.getByLabel('Overall feedback', { exact: true });

  await rating.selectOption('4');
  await comment.fill('Variant 1 notes: dense but readable.');
  await overall.fill('Overall: compare all five before choosing.');

  const stored = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)), STORAGE_KEY);
  eq(stored.version, 1, 'stored feedback version');
  eq(stored.selectedVariant, 1, 'stored selected variant');
  eq(stored.variants.length, 5, 'stored five variant entries');
  eq(stored.variants[0].rating, 4, 'stored rating');
  eq(stored.variants[0].comment, 'Variant 1 notes: dense but readable.', 'stored comment');
  eq(stored.overallComment, 'Overall: compare all five before choosing.', 'stored overall comment');
  eq(stored.variants.map((v) => v.name).join('|'), VARIANT_NAMES.join('|'), 'stored entry names match accepted names');

  await switchVariant(page, 2);
  eq(await rating.inputValue(), '', 'variant 2 starts unrated');
  eq(await comment.inputValue(), '', 'variant 2 comment starts empty');
  eq(await overall.inputValue(), 'Overall: compare all five before choosing.', 'overall comment is shared across variants');
  await rating.selectOption('2');
  await comment.fill('Variant 2 notes: editorial paper.');
  await switchVariant(page, 1);
  eq(await rating.inputValue(), '4', 'variant 1 rating restored on switch');
  eq(await comment.inputValue(), 'Variant 1 notes: dense but readable.', 'variant 1 comment restored on switch');

  await page.reload();
  await waitForBoot(page);
  await assertOnlyVariant(page, 1);
  eq(await page.getByRole('button', { name: 'Variant 1', exact: true }).getAttribute('aria-pressed'), 'true',
    'selected variant persisted across reload');
  eq(await rating.inputValue(), '4', 'rating persisted across reload');
  eq(await comment.inputValue(), 'Variant 1 notes: dense but readable.', 'comment persisted across reload');
  eq(await overall.inputValue(), 'Overall: compare all five before choosing.', 'overall comment persisted across reload');

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Export feedback' }).click(),
  ]);
  const exported = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
  eq(exported.version, 1, 'export version');
  eq(exported.selectedVariant, 1, 'export selected variant');
  eq(exported.variants.length, 5, 'export five entries');
  eq(exported.variants.find((v) => v.id === 1).rating, 4, 'export rating');
  eq(exported.variants.find((v) => v.id === 1).comment, 'Variant 1 notes: dense but readable.', 'export comment');
  eq(exported.variants.find((v) => v.id === 2).rating, 2, 'export second rating');
  eq(exported.overallComment, 'Overall: compare all five before choosing.', 'export overall comment');

  // Typed feedback is literal text: never markup, never executed, export keeps it verbatim.
  const literal = '<img src=x onerror="window.__integrationPwned=1">';
  await comment.fill(literal);
  eq(await page.locator('#review-rail img').count(), 0, 'typed feedback creates no elements in the rail');
  eq(await page.evaluate(() => window.__integrationPwned), undefined, 'typed feedback does not execute');
  const [literalDownload] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Export feedback' }).click(),
  ]);
  const literalExport = JSON.parse(fs.readFileSync(await literalDownload.path(), 'utf8'));
  eq(literalExport.variants.find((v) => v.id === 1).comment, literal, 'export keeps typed markup as a literal string');
  await page.reload();
  await waitForBoot(page);
  eq(await page.evaluate(() => window.__integrationPwned), undefined, 'typed feedback does not execute after reload');
  eq(await comment.inputValue(), literal, 'typed feedback round-trips as text');
  await comment.fill('Variant 1 notes: dense but readable.');

  // Make the fixture non-default so clear/reset distinctions are visible.
  await openProject(page);
  await selectResponse(page, 'onboarding');
  await openPreview(page);
  await page.getByTestId('confirm-button').first().click();
  await assertText(page, 'metric-cash', 'Cash $72,000', 'fixture committed before clear-feedback test');

  // Clear feedback: explicit confirmation, focus moves into it and back.
  const clearButton = page.locator('#clear-feedback');
  await clearButton.click();
  ok(await page.locator('#clear-confirm').isVisible(), 'clear confirmation appears');
  eq(await page.evaluate(() => document.activeElement.id), 'clear-confirm-yes', 'focus moves into the confirmation');
  await page.getByRole('button', { name: 'Cancel' }).click();
  eq(await page.locator('#clear-confirm').isHidden(), true, 'cancel hides the confirmation');
  eq(await page.evaluate(() => document.activeElement.id), 'clear-feedback', 'cancel returns focus to Clear feedback');
  eq(await rating.inputValue(), '4', 'cancel keeps the rating');
  eq(await comment.inputValue(), 'Variant 1 notes: dense but readable.', 'cancel keeps the comment');
  eq(await overall.inputValue(), 'Overall: compare all five before choosing.', 'cancel keeps the overall comment');
  await assertText(page, 'metric-cash', 'Cash $72,000', 'cancel keeps fixture state');

  await clearButton.focus();
  await page.keyboard.press('Enter');
  ok(await page.locator('#clear-confirm').isVisible(), 'keyboard Enter opens the confirmation');
  eq(await page.evaluate(() => document.activeElement.id), 'clear-confirm-yes', 'keyboard focus lands on Confirm clear');
  await page.keyboard.press('Tab');
  eq(await page.evaluate(() => document.activeElement.id), 'clear-cancel', 'Tab reaches Cancel in the confirmation');
  await page.keyboard.press('Enter');
  eq(await page.locator('#clear-confirm').isHidden(), true, 'keyboard cancel hides the confirmation');
  eq(await page.evaluate(() => document.activeElement.id), 'clear-feedback', 'keyboard cancel returns focus to Clear feedback');

  await clearButton.click();
  await page.getByRole('button', { name: 'Confirm clear' }).click();
  eq(await rating.inputValue(), '', 'clear resets the rating');
  eq(await comment.inputValue(), '', 'clear resets the comment');
  eq(await overall.inputValue(), '', 'clear resets the overall comment');
  eq(await page.evaluate(() => document.activeElement.id), 'clear-feedback', 'confirm returns focus to Clear feedback');
  eq(await page.getByRole('button', { name: 'Variant 1', exact: true }).getAttribute('aria-pressed'), 'true',
    'clear keeps the selected variant');
  await assertText(page, 'metric-cash', 'Cash $72,000', 'clear keeps the committed fixture state');
  const afterClear = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)), STORAGE_KEY);
  eq(afterClear.variants.every((entry) => entry.rating === null && entry.comment === ''), true, 'stored entries cleared');
  eq(afterClear.overallComment, '', 'stored overall comment cleared');
  eq(afterClear.selectedVariant, 1, 'clear keeps the stored selected variant');

  // Reset fixture clears only fixture/draft/history; feedback/selection stay.
  await rating.selectOption('3');
  await comment.fill('Variant 1 kept through reset.');
  await page.locator('#reset-fixture').click();
  eq(await page.evaluate(() => document.activeElement.id), 'reset-fixture', 'reset keeps rail focus on Reset fixture');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'reset restores cash');
  await assertText(page, 'decision-status', 'Open — no response committed', 'reset reopens the decision');
  eq(await page.getByTestId('history-entry').count(), 0, 'reset clears history');
  eq(await page.getByRole('button', { name: 'Variant 1', exact: true }).getAttribute('aria-pressed'), 'true',
    'reset keeps the selected variant');
  eq(await rating.inputValue(), '3', 'reset keeps the rating');
  eq(await comment.inputValue(), 'Variant 1 kept through reset.', 'reset keeps the comment');

  await page.reload();
  await waitForBoot(page);
  await assertText(page, 'metric-cash', 'Cash $84,000', 'fixture resets on reload');
  await assertText(page, 'decision-status', 'Open — no response committed', 'decision reopens on reload');
  eq(await rating.inputValue(), '3', 'feedback survives reload');
  eq(await comment.inputValue(), 'Variant 1 kept through reset.', 'comment survives reload');
  eq(await page.getByRole('button', { name: 'Variant 1', exact: true }).getAttribute('aria-pressed'), 'true',
    'variant selection survives reload');

  const keys = await page.evaluate(() => Object.keys(localStorage));
  eq(keys.length, 1, `lab writes exactly one storage key (got ${keys.join(', ')})`);
  eq(keys[0], STORAGE_KEY, 'lab storage key name');
}

// -------------------------------------------------------- storage failure paths

async function runStorageFailureTests(page, browser) {
  log('storage: malformed, invalid, partial-valid, denied');
  await page.evaluate((key) => localStorage.removeItem(key), STORAGE_KEY);

  // Unreadable JSON: warning, load alone never rewrites; a later user action
  // persists the repaired in-memory model.
  await page.evaluate((key) => localStorage.setItem(key, '{"version":1,'), STORAGE_KEY);
  await page.reload();
  await waitForBoot(page);
  await page.locator('#storage-warning').waitFor({ state: 'visible' });
  ok(/unreadable/i.test(norm(await page.locator('#storage-warning').textContent())), 'malformed storage warning is shown');
  eq(await page.evaluate((key) => localStorage.getItem(key), STORAGE_KEY), '{"version":1,',
    'malformed value is untouched by loading alone');
  await switchVariant(page, 2);
  await openProject(page);
  await assertText(page, 'project-name', 'Signal Drift', 'app still works after malformed storage');
  const repaired = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)), STORAGE_KEY);
  eq(repaired.version, 1, 'user action persists a valid version-1 payload after malformed load');
  eq(repaired.variants.length, 5, 'repaired payload keeps all five entries');
  eq(repaired.selectedVariant, 2, 'repaired payload records the user-selected variant');
  eq(repaired.variants.every((entry) => entry.rating === null && entry.comment === ''), true,
    'malformed feedback has no invented ratings or comments');
  await switchVariant(page, 1);
  eq(await page.evaluate((key) => JSON.parse(localStorage.getItem(key)).selectedVariant, STORAGE_KEY), 1,
    'subsequent selection updates persist normally after repair');

  // Structurally invalid payload: valid shape enforced, invalid entries rejected.
  const invalidRaw = JSON.stringify({
    version: 1,
    selectedVariant: 99,
    variants: [{ id: 99, rating: 9, comment: 7 }],
    overallComment: 42,
  });
  await page.evaluate((key) => localStorage.setItem(key, JSON.stringify({
    version: 1,
    selectedVariant: 99,
    variants: [{ id: 99, rating: 9, comment: 7 }],
    overallComment: 42,
  })), STORAGE_KEY);
  await page.reload();
  await waitForBoot(page);
  await page.locator('#storage-warning').waitFor({ state: 'visible' });
  ok(/invalid|reset/i.test(norm(await page.locator('#storage-warning').textContent())), 'invalid storage warning is shown');
  eq(await page.getByRole('button', { name: 'Variant 1', exact: true }).getAttribute('aria-pressed'), 'true',
    'invalid selection falls back to Variant 1');
  eq(await page.getByLabel('Variant rating', { exact: true }).inputValue(), '', 'invalid rating falls back to Unrated');
  eq(await page.getByLabel('Overall feedback', { exact: true }).inputValue(), '', 'invalid overall comment is cleared');
  eq(await page.evaluate((key) => localStorage.getItem(key), STORAGE_KEY), invalidRaw,
    'invalid payload is not auto-migrated on load');

  // Partially valid payload: valid entries/selection kept, only missing parts reset.
  const partialRaw = JSON.stringify({
    version: 1,
    selectedVariant: 3,
    variants: [{ id: 3, name: 'Board Map', rating: 5, comment: 'kept note' }],
    overallComment: 'kept overall',
  });
  await page.evaluate((key) => localStorage.setItem(key, JSON.stringify({
    version: 1,
    selectedVariant: 3,
    variants: [{ id: 3, name: 'Board Map', rating: 5, comment: 'kept note' }],
    overallComment: 'kept overall',
  })), STORAGE_KEY);
  await page.reload();
  await waitForBoot(page);
  await page.locator('#storage-warning').waitFor({ state: 'visible' });
  await assertOnlyVariant(page, 3);
  eq(await page.getByRole('button', { name: 'Variant 3', exact: true }).getAttribute('aria-pressed'), 'true',
    'valid saved selection is kept');
  eq(await page.getByLabel('Variant rating', { exact: true }).inputValue(), '5', 'valid saved rating is kept');
  eq(await page.getByLabel('Variant feedback', { exact: true }).inputValue(), 'kept note', 'valid saved comment is kept');
  eq(await page.getByLabel('Overall feedback', { exact: true }).inputValue(), 'kept overall', 'valid saved overall is kept');
  eq(await page.evaluate((key) => localStorage.getItem(key), STORAGE_KEY), partialRaw,
    'partial payload is not auto-migrated on load');
  await page.evaluate((key) => localStorage.removeItem(key), STORAGE_KEY);
  await page.reload();
  await waitForBoot(page);
  await page.locator('#storage-warning').waitFor({ state: 'hidden' });

  // localStorage denied entirely: warning, in-memory feedback and export still work.
  const deniedContext = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
  const deniedPage = await deniedContext.newPage();
  const deniedErrors = [];
  deniedPage.on('pageerror', (error) => deniedErrors.push(error.message));
  await deniedPage.addInitScript(() => {
    const denied = {
      getItem() { throw new Error('storage denied'); },
      setItem() { throw new Error('storage denied'); },
      removeItem() { throw new Error('storage denied'); },
    };
    Object.defineProperty(window, 'localStorage', { configurable: true, get() { return denied; } });
  });
  await deniedPage.goto(BASE);
  await waitForBoot(deniedPage);
  await deniedPage.locator('#storage-warning').waitFor({ state: 'visible' });
  ok(/unavailable/i.test(norm(await deniedPage.locator('#storage-warning').textContent())), 'denied storage warning shown');
  await deniedPage.getByLabel('Variant rating', { exact: true }).selectOption('3');
  await deniedPage.getByLabel('Variant feedback', { exact: true }).fill('memory only note');
  await deniedPage.getByRole('button', { name: 'Variant 2', exact: true }).click();
  await deniedPage.getByRole('button', { name: 'Variant 1', exact: true }).click();
  eq(await deniedPage.getByLabel('Variant rating', { exact: true }).inputValue(), '3',
    'in-memory rating retained without storage');
  eq(await deniedPage.getByLabel('Variant feedback', { exact: true }).inputValue(), 'memory only note',
    'in-memory comment retained without storage');
  const [deniedDownload] = await Promise.all([
    deniedPage.waitForEvent('download'),
    deniedPage.getByRole('button', { name: 'Export feedback' }).click(),
  ]);
  const deniedExport = JSON.parse(fs.readFileSync(await deniedDownload.path(), 'utf8'));
  eq(deniedExport.variants.find((v) => v.id === 1).rating, 3, 'export works without storage');
  eq(deniedExport.variants.find((v) => v.id === 1).comment, 'memory only note', 'export keeps in-memory text without storage');
  eq(deniedErrors.length, 0, `denied storage page errors: ${deniedErrors.join('; ')}`);
  await deniedContext.close();
}

// ----------------------------------------------------------- invalid transitions

async function runInvalidTransitionTests(page) {
  log('invalid transitions: visible guards without silent data changes');
  await resetFixture(page);
  await switchVariant(page, 1);
  await openProject(page);

  for (const testid of ['preview-button', 'confirm-button', 'defer-button', 'reject-button']) {
    eq(await page.getByTestId(testid).isDisabled(), true, `${testid} disabled before any response selection`);
  }
  await page.evaluate(() => {
    document.querySelector('[data-testid="preview-button"]').click();
    document.querySelector('[data-testid="confirm-button"]').click();
    document.querySelector('[data-testid="defer-button"]').click();
    document.querySelector('[data-testid="reject-button"]').click();
  });
  await assertText(page, 'decision-status', 'Open — no response committed', 'forced pre-selection clicks changed nothing');
  await assertText(page, 'metric-cash', 'Cash $84,000', 'forced pre-selection clicks did not spend');
  eq(await page.getByTestId('history-entry').count(), 0, 'forced pre-selection clicks recorded no history');

  await selectResponse(page, 'simplify');
  eq(await page.getByTestId('confirm-button').isDisabled(), true, 'confirm disabled until preview is open');
  await openPreview(page);
  await cancelPreview(page);
  eq(await page.getByTestId('confirm-button').isDisabled(), true, 'cancel disables confirm again');
  eq(await page.getByTestId('history-entry').count(), 0, 'cancel added no history');

  await page.getByTestId('defer-button').first().click();
  for (const testid of ['preview-button', 'confirm-button', 'defer-button', 'reject-button']) {
    eq(await page.getByTestId(testid).isDisabled(), true, `deferred: ${testid} disabled until Reopen`);
  }
  eq(await page.getByTestId('reopen-button').isEnabled(), true, 'deferred: reopen enabled');
  await assertText(page, 'decision-flag', 'Deferred: Simplify branching — revisit before validation', 'deferred flag derived from state');
  await page.evaluate(() => {
    document.querySelector('[data-testid="confirm-button"]').click();
    document.querySelector('[data-testid="preview-button"]').click();
    document.querySelector('[data-testid="reject-button"]').click();
  });
  await assertText(page, 'decision-status', 'Deferred — revisit before validation', 'guarded actions cannot override deferral');
  eq(await page.getByTestId('history-entry').count(), 1, 'no duplicate history after guarded attempts');

  await page.getByTestId('reopen-button').first().click();
  await selectResponse(page, 'hold');
  await openPreview(page);
  await page.getByTestId('confirm-button').first().click();
  await assertText(page, 'decision-status', 'Committed', 'hold committed once');
  eq(await page.getByTestId('history-entry').count(), 3, 'commit recorded once (defer + reopen + commit)');
  await page.evaluate(() => {
    document.querySelector('[data-testid="confirm-button"]').click();
    document.querySelector('[data-testid="defer-button"]').click();
    document.querySelector('[data-testid="reject-button"]').click();
  });
  await assertText(page, 'metric-cash', 'Cash $84,000', 'duplicate commit cannot spend again (hold keeps $84,000)');
  await assertText(page, 'decision-status', 'Committed', 'committed state survives duplicate attempts');
  eq(await page.getByTestId('history-entry').count(), 3, 'duplicate attempts recorded no history');
  await resetFixture(page);
}

// --------------------------------------------------------------- keyboard flow

async function runKeyboardWorkflow(page) {
  log('keyboard: real Tab/Enter/Space activation and mount-owned focus');
  await resetFixture(page);
  await switchVariant(page, 1);
  await page.locator('#game-surface > [data-variant]').focus();
  await page.keyboard.press('Tab');

  let info = await tabTo(page, (focus) => focus.testid === 'open-project');
  ok(info, 'keyboard: Tab reached open-project');
  await page.keyboard.press('Enter');
  await assertKeyboardFocus(page, { key: 'view-title' }, 'keyboard: navigation focuses the view heading');

  info = await tabTo(page, (focus) => focus.testid === 'response-onboarding');
  ok(info, 'keyboard: Tab reached response-onboarding');
  await page.keyboard.press('Enter');
  eq(await page.getByTestId('response-onboarding').getAttribute('aria-pressed'), 'true', 'keyboard: Enter selected onboarding');
  await assertKeyboardFocus(page, { testid: 'response-onboarding' }, 'keyboard: selection focus retained');

  info = await tabTo(page, (focus) => focus.testid === 'response-hold');
  ok(info, 'keyboard: Tab reached response-hold');
  await page.keyboard.press('Space');
  eq(await page.getByTestId('response-hold').getAttribute('aria-pressed'), 'true', 'keyboard: Space selected hold');
  await assertKeyboardFocus(page, { testid: 'response-hold' }, 'keyboard: Space selection focus retained');

  info = await tabTo(page, (focus) => focus.testid === 'preview-button');
  ok(info, 'keyboard: Tab reached preview-button');
  await page.keyboard.press('Enter');
  ok(await page.getByTestId('preview-panel').first().isVisible(), 'keyboard: Enter opened the preview');
  await assertKeyboardFocus(page, { testid: 'cancel-preview' }, 'keyboard: preview focuses Cancel preview');
  await page.keyboard.press('Space');
  eq(await page.getByTestId('preview-panel').count(), 0, 'keyboard: Space cancelled the preview');
  await assertKeyboardFocus(page, { testid: 'preview-button' }, 'keyboard: cancel returns focus to Preview response');

  await page.keyboard.press('Enter');
  ok(await page.getByTestId('preview-panel').first().isVisible(), 'keyboard: preview reopened for confirm');
  info = await tabTo(page, (focus) => focus.testid === 'confirm-button');
  ok(info, 'keyboard: Tab reached confirm-button');
  await page.keyboard.press('Enter');
  await assertText(page, 'decision-status', 'Committed', 'keyboard: Enter committed the decision');
  await assertKeyboardFocus(page, { testid: 'decision-result' }, 'keyboard: confirm focuses the decision result');

  await resetFixture(page);
  await openProject(page);
  info = await tabTo(page, (focus) => focus.testid === 'response-onboarding');
  await page.keyboard.press('Enter');
  info = await tabTo(page, (focus) => focus.testid === 'defer-button');
  ok(info, 'keyboard: Tab reached defer-button');
  await page.keyboard.press('Enter');
  await assertKeyboardFocus(page, { testid: 'reopen-button' }, 'keyboard: defer focuses Reopen');
  await page.keyboard.press('Enter');
  await assertText(page, 'decision-status', 'Open — no response committed', 'keyboard: reopen returns to open');
  await assertKeyboardFocus(page, { testid: 'decision-result' }, 'keyboard: reopen focuses the decision result');

  // Rail switching is native keyboard activation too, and keeps rail focus.
  await page.getByRole('button', { name: 'Variant 2', exact: true }).focus();
  await page.keyboard.press('Space');
  await assertOnlyVariant(page, 2);
  await assertKeyboardFocus(page, { variantBtn: '2' }, 'keyboard: Space switched to variant 2 with rail focus');
  await page.getByRole('button', { name: 'Variant 3', exact: true }).focus();
  await page.keyboard.press('Enter');
  await assertOnlyVariant(page, 3);
  await assertKeyboardFocus(page, { variantBtn: '3' }, 'keyboard: Enter switched to variant 3 with rail focus');
  await resetFixture(page);
}

// ------------------------------------------------------------------ CSS audit

async function auditStyles(page) {
  log('styles: all seven loaded, candidate sheets scoped, no leak to body');
  const audit = await page.evaluate(() => {
    const expected = [
      '/shared.css',
      '/variants/1/variant.css',
      '/variants/2/variant.css',
      '/variants/3/variant.css',
      '/variants/4/variant.css',
      '/variants/5/variant.css',
      '/lab.css',
    ];
    const sheets = Array.from(document.styleSheets);
    const hrefs = sheets.map((sheet) => (sheet.href ? new URL(sheet.href).pathname : '(inline)'));
    const loaded = sheets.map((sheet) => {
      try { return sheet.cssRules.length; } catch (error) { return -1; }
    });
    const violations = {};
    for (let n = 1; n <= 5; n++) {
      const sheet = sheets.find((entry) => entry.href && new URL(entry.href).pathname.endsWith('/variants/' + n + '/variant.css'));
      const bad = [];
      if (!sheet) bad.push('stylesheet missing');
      else {
        const walk = (rules) => {
          Array.from(rules).forEach((rule) => {
            if (rule.cssRules && rule.cssRules.length) walk(rule.cssRules);
            if (rule.selectorText && !rule.selectorText.includes('.variant-' + n)) bad.push(rule.selectorText);
          });
        };
        walk(sheet.cssRules);
      }
      violations[n] = bad.slice(0, 3);
    }
    return { hrefs, loaded, violations, bodyBackground: getComputedStyle(document.body).backgroundColor };
  });

  eq(audit.hrefs.length, 7, `seven stylesheets declared (got ${audit.hrefs.length})`);
  const expected = ['/shared.css',
    '/variants/1/variant.css', '/variants/2/variant.css', '/variants/3/variant.css',
    '/variants/4/variant.css', '/variants/5/variant.css', '/lab.css'];
  expected.forEach((suffix, index) => {
    ok(audit.hrefs[index] && audit.hrefs[index].endsWith(suffix), `stylesheet ${index} is ${suffix} (got ${audit.hrefs[index]})`);
  });
  eq(audit.loaded.filter((count) => count > 0).length, 7, 'all seven stylesheets loaded with parsed rules');
  for (let n = 1; n <= 5; n++) {
    eq(audit.violations[n].length, 0, `variant ${n} CSS is fully scoped to .variant-${n} (${audit.violations[n].join(' | ')})`);
  }
  eq(audit.bodyBackground, 'rgb(11, 16, 32)', 'candidate CSS does not leak onto body background');
}

// ------------------------------------------------------------ screenshots

async function captureScreenshots(page) {
  log('capturing overview/decision desktop+narrow for all five candidates');
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 900 });
  for (let n = 1; n <= 5; n++) {
    await resetFixture(page);
    await switchVariant(page, n);
    await openOverview(page);
    await page.screenshot({ path: path.join(SHOT_DIR, `v${n}-overview-desktop.png`) });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(80);
    await page.screenshot({ path: path.join(SHOT_DIR, `v${n}-overview-narrow.png`) });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(60);
    await openProject(page);
    await selectResponse(page, 'onboarding');
    await openPreview(page);
    await page.getByTestId('preview-panel').first().scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(SHOT_DIR, `v${n}-decision-desktop.png`) });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(80);
    await page.getByTestId('preview-panel').first().scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(SHOT_DIR, `v${n}-decision-narrow.png`) });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(60);
  }
  await resetFixture(page);
  await switchVariant(page, 1);
  await openProject(page);
  await selectResponse(page, 'onboarding');
  await openPreview(page);
  await page.getByTestId('preview-panel').first().screenshot({ path: path.join(SHOT_DIR, 'preview-comparison-desktop.png') });
  await page.getByTestId('open-capabilities').first().click();
  await page.getByTestId('capability-graph').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(SHOT_DIR, 'capability-graph-desktop.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(80);
  await page.screenshot({ path: path.join(SHOT_DIR, 'capability-graph-narrow.png') });
  await page.setViewportSize({ width: 1440, height: 900 });
  await switchVariant(page, 3);
  await page.getByTestId('open-capabilities').first().click();
  await page.getByTestId('cap-list-safe-release-train').first().click();
  await page.screenshot({ path: path.join(SHOT_DIR, 'v3-map-graph-desktop.png') });
  await resetFixture(page);
  log(`screenshots written to ${SHOT_DIR}`);
}

// ------------------------------------------------------------------ main

(async () => {
  const server = spawn(process.env.PYTHON || 'python3', [
    '-m', 'http.server', String(PORT), '--bind', '127.0.0.1', '--directory', REPO_ROOT,
  ], { stdio: 'ignore' });

  let browser;
  const failures = [];
  try {
    await waitForServer();
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
    const page = await context.newPage();
    const pageErrors = [];
    const consoleErrors = [];
    const requestLog = [];
    page.on('pageerror', (error) => pageErrors.push(error.message));
    page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    page.on('request', (request) => {
      const url = request.url();
      requestLog.push(url);
      if (url.startsWith('data:') || url.startsWith('blob:')) return;
      try {
        const parsed = new URL(url);
        if (parsed.hostname !== '127.0.0.1' && parsed.hostname !== 'localhost') {
          pageErrors.push('external request: ' + url);
        }
      } catch (error) {
        pageErrors.push('unparseable request: ' + url);
      }
    });

    await page.goto(BASE);
    await page.evaluate(() => document.fonts.ready);
    await waitForBoot(page);
    eq(await page.evaluate(() => document.fonts.check('14px "Studio Mono"')), true,
      'bundled Studio Mono font loads via relative URL');

    // Preload proof: five same-task switches issue no further network requests.
    const bootRequests = requestLog.length;
    const syncEnd = await page.evaluate(() => {
      for (let n = 5; n >= 1; n--) document.querySelector(`[data-variant-btn="${n}"]`).click();
      return document.querySelector('#game-surface > [data-variant]').getAttribute('data-variant');
    });
    eq(syncEnd, '1', 'five rapid switches end on Variant 1');
    await page.waitForTimeout(150);
    eq(requestLog.length, bootRequests, 'switching candidates works from preloaded modules/styles with no network');
    await assertOnlyVariant(page, 1);
    await auditStyles(page);

    for (let n = 1; n <= 5; n++) {
      await runVariantWorkflow(page, n);
    }
    await runSwitchingPreservation(page);
    await runRailTypingIsolation(page);
    await runInvalidTransitionTests(page);
    await runKeyboardWorkflow(page);
    await runFeedbackTests(page);
    await runStorageFailureTests(page, browser);
    await captureScreenshots(page);

    eq(consoleErrors.length, 0, `no console errors: ${consoleErrors.join('; ')}`);
    eq(pageErrors.length, 0, `no page errors or external requests: ${pageErrors.join('; ')}`);

    await context.close();
    log(`PASS — ${checks} checks, 25 screenshots in ${SHOT_DIR}`);
  } catch (error) {
    failures.push(error);
    console.error(error);
  } finally {
    if (browser) await browser.close().catch(() => {});
    server.kill('SIGTERM');
  }
  if (failures.length) process.exit(1);
})();
