// WP-UI-01I integration shell for the Studio Lab.
//
// One shared mount holds the accepted C-UI-S1 state; the fixed right rail switches
// between the five accepted renderers with setRenderer (synchronous, state kept)
// and owns feedback storage/export/reset. All five renderers and stylesheets are
// preloaded at boot, so numbered activation does no network work. No harness
// import, no sixth candidate, no game rules, no production wiring.
//
// Storage contract (P4): only `studio-rewrite-ui-lab-v1`, JSON version 1 with the
// five {id, name, rating:null|1..5, comment} entries, the selected variant and the
// overall comment. Loaded values are validated; invalid branches are reset in
// memory only and never auto-written back. Storage failure keeps feedback in memory
// and export working.

import { F, mount } from './shared.js';
import * as variant1 from './variants/1/variant.js';
import * as variant2 from './variants/2/variant.js';
import * as variant3 from './variants/3/variant.js';
import * as variant4 from './variants/4/variant.js';
import * as variant5 from './variants/5/variant.js';

const STORAGE_KEY = 'studio-rewrite-ui-lab-v1';

const CANDIDATES = [
  { id: 1, render: variant1.render },
  { id: 2, render: variant2.render },
  { id: 3, render: variant3.render },
  { id: 4, render: variant4.render },
  { id: 5, render: variant5.render },
].map((candidate) => {
  const meta = F.variants.find((variant) => variant.id === candidate.id);
  return {
    id: candidate.id,
    name: meta ? meta.name : 'Variant ' + candidate.id,
    render: candidate.render,
  };
});

CANDIDATES.forEach((candidate) => {
  if (typeof candidate.render !== 'function') {
    throw new Error('Variant ' + candidate.id + ' does not export render(state, dispatch)');
  }
});

const byId = (id) => document.getElementById(id);

// ------------------------------------------------------------- feedback storage

function defaultFeedback() {
  return {
    version: 1,
    selectedVariant: 1,
    variants: F.variants.map((variant) => ({ id: variant.id, name: variant.name, rating: null, comment: '' })),
    overallComment: '',
  };
}

const feedbackState = { data: defaultFeedback(), available: true };

function warn(message) {
  const node = byId('storage-warning');
  if (!node) return;
  node.hidden = false;
  if (!node.textContent) node.textContent = message;
  else if (node.textContent.indexOf(message) === -1) node.textContent += ' ' + message;
}

function railAck(message) {
  const node = byId('rail-ack');
  if (node) node.textContent = message;
}

// Validate a parsed saved payload without evaluating any of its text. Returns the
// in-memory value (valid parts kept, invalid parts defaulted) plus human-readable
// problems. The caller never writes the repaired value back automatically.
function validateFeedback(raw) {
  const problems = [];
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return { value: defaultFeedback(), problems: ['Saved feedback was not a valid object and was reset.'] };
  }
  if (raw.version !== 1) {
    return { value: defaultFeedback(), problems: ['Saved feedback version was unrecognized and was reset.'] };
  }
  const value = defaultFeedback();
  if (Number.isInteger(raw.selectedVariant) && raw.selectedVariant >= 1 && raw.selectedVariant <= 5) {
    value.selectedVariant = raw.selectedVariant;
  } else {
    problems.push('Saved selected variant was invalid; Variant 1 is selected.');
  }
  if (typeof raw.overallComment === 'string') value.overallComment = raw.overallComment;
  else problems.push('Saved overall comment was invalid and was cleared.');

  if (Array.isArray(raw.variants)) {
    value.variants.forEach((entry) => {
      const found = raw.variants.find((candidate) => (
        candidate && typeof candidate === 'object' && !Array.isArray(candidate) && candidate.id === entry.id
      ));
      if (!found) {
        problems.push('Feedback entry ' + entry.id + ' was missing and was reset.');
        return;
      }
      if (found.rating === null || found.rating === undefined) entry.rating = null;
      else if (Number.isInteger(found.rating) && found.rating >= 1 && found.rating <= 5) entry.rating = found.rating;
      else problems.push('Rating for variant ' + entry.id + ' was invalid and was reset.');
      if (typeof found.comment === 'string') entry.comment = found.comment;
      else problems.push('Comment for variant ' + entry.id + ' was invalid and was cleared.');
    });
  } else {
    problems.push('Saved feedback entries were invalid and were reset.');
  }
  return { value: value, problems: problems };
}

function loadFeedback() {
  let raw = null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch (error) {
    feedbackState.available = false;
    warn('Feedback storage is unavailable — feedback lasts only for this page.');
    return;
  }
  if (raw === null || raw === '') return;
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    warn('Saved feedback was unreadable and was reset.');
    return;
  }
  const result = validateFeedback(parsed);
  feedbackState.data = result.value;
  if (result.problems.length) warn(result.problems.join(' '));
}

function saveFeedback() {
  if (!feedbackState.available) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(feedbackState.data));
  } catch (error) {
    feedbackState.available = false;
    warn('Feedback could not be saved — feedback lasts only for this page.');
  }
}

function currentEntry() {
  const selected = feedbackState.data.selectedVariant;
  return feedbackState.data.variants.find((entry) => entry.id === selected) || feedbackState.data.variants[0];
}

// -------------------------------------------------------------------- rail state

function renderRailSelection() {
  const selected = feedbackState.data.selectedVariant;
  document.querySelectorAll('[data-variant-btn]').forEach((button) => {
    const id = Number(button.getAttribute('data-variant-btn'));
    const on = id === selected;
    button.setAttribute('aria-pressed', on ? 'true' : 'false');
    button.classList.toggle('is-selected', on);
  });
  const candidate = CANDIDATES.find((entry) => entry.id === selected) || CANDIDATES[0];
  const label = byId('selected-variant');
  if (label) label.textContent = 'Selected: Variant ' + selected + ' — ' + candidate.name;
}

function renderRailFields() {
  const entry = currentEntry();
  const rating = byId('variant-rating');
  const comment = byId('variant-feedback');
  const overall = byId('overall-feedback');
  if (rating) rating.value = entry.rating === null ? '' : String(entry.rating);
  if (comment) comment.value = entry.comment;
  if (overall) overall.value = feedbackState.data.overallComment;
}

// ------------------------------------------------------------------ rail actions

let api = null;

function selectVariant(id) {
  const candidate = CANDIDATES.find((entry) => entry.id === id);
  if (!candidate || feedbackState.data.selectedVariant === id) return;
  const previous = feedbackState.data.selectedVariant;
  feedbackState.data.selectedVariant = id;
  try {
    api.setRenderer(candidate.render);
  } catch (error) {
    feedbackState.data.selectedVariant = previous;
    renderRailSelection();
    railAck('Variant ' + id + ' could not be rendered: ' + (error && error.message ? error.message : String(error)));
    return;
  }
  saveFeedback();
  renderRailSelection();
  renderRailFields();
}

function exportFeedback() {
  const payload = {
    version: 1,
    selectedVariant: feedbackState.data.selectedVariant,
    variants: feedbackState.data.variants.map((entry) => ({
      id: entry.id,
      name: entry.name,
      rating: entry.rating,
      comment: entry.comment,
    })),
    overallComment: feedbackState.data.overallComment,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'studio-rewrite-ui-lab-feedback.json';
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  railAck('Feedback exported as studio-rewrite-ui-lab-feedback.json');
}

function clearFeedback() {
  const selected = feedbackState.data.selectedVariant;
  feedbackState.data = defaultFeedback();
  feedbackState.data.selectedVariant = selected;
  saveFeedback();
  renderRailFields();
  const confirmBox = byId('clear-confirm');
  if (confirmBox) confirmBox.hidden = true;
  const clearButton = byId('clear-feedback');
  if (clearButton) clearButton.focus();
  railAck('Feedback cleared for all five variants and the overall comment.');
}

function bindRail() {
  document.querySelectorAll('[data-variant-btn]').forEach((button) => {
    button.addEventListener('click', () => selectVariant(Number(button.getAttribute('data-variant-btn'))));
  });

  const rating = byId('variant-rating');
  if (rating) {
    rating.addEventListener('change', () => {
      currentEntry().rating = rating.value === '' ? null : Number(rating.value);
      saveFeedback();
    });
  }
  const comment = byId('variant-feedback');
  if (comment) {
    comment.addEventListener('input', () => {
      currentEntry().comment = comment.value;
      saveFeedback();
    });
  }
  const overall = byId('overall-feedback');
  if (overall) {
    overall.addEventListener('input', () => {
      feedbackState.data.overallComment = overall.value;
      saveFeedback();
    });
  }

  const exportButton = byId('export-feedback');
  if (exportButton) exportButton.addEventListener('click', exportFeedback);

  const resetButton = byId('reset-fixture');
  if (resetButton) {
    resetButton.addEventListener('click', () => {
      api.reset();
      railAck('Fixture reset to 18 May 2031. Feedback and the selected variant were kept.');
    });
  }

  const clearButton = byId('clear-feedback');
  const confirmBox = byId('clear-confirm');
  const yesButton = byId('clear-confirm-yes');
  const cancelButton = byId('clear-cancel');
  if (clearButton && confirmBox && yesButton) {
    clearButton.addEventListener('click', () => {
      confirmBox.hidden = false;
      yesButton.focus();
    });
    yesButton.addEventListener('click', clearFeedback);
  }
  if (cancelButton && confirmBox && clearButton) {
    cancelButton.addEventListener('click', () => {
      confirmBox.hidden = true;
      clearButton.focus();
    });
  }
}

// ------------------------------------------------------------------------- boot

loadFeedback();
renderRailSelection();
const initial = CANDIDATES.find((entry) => entry.id === feedbackState.data.selectedVariant) || CANDIDATES[0];
api = mount(byId('game-surface'), initial.render);
renderRailFields();
bindRail();
