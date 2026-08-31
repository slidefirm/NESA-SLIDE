"""Canonical presentation-only motion runtime for generated HTML decks.

The authored slide DOM remains the source of truth.  During presentation mode
the runtime briefly projects a cloned copy of the incoming slide and animates
that copy; the editable DOM is restored unchanged when the run completes.
"""

from __future__ import annotations

import hashlib


MOTION_RUNTIME_VERSION = "projection-content-fade-v6"
MOTION_MODE = "content-fade"
MOTION_TITLE_DELAY_MS = 0
MOTION_CONTENT_DELAY_MS = 220
# Keep the legacy manifest field aligned with the second phase so existing
# consumers still know the longest pre-content delay.
MOTION_DELAY_MS = MOTION_CONTENT_DELAY_MS
MOTION_DURATION_MS = 900
MOTION_TRANSLATE_Y_PX = 44
MOTION_SCALE_FROM = 0.985


MOTION_RUNTIME_CSS = r"""
[data-object-reveal-layer]{position:absolute;inset:0;width:1920px;height:1080px;overflow:hidden;pointer-events:none;user-select:none;z-index:60;contain:layout paint style}
[data-object-reveal-slide]{display:block!important;position:absolute!important;inset:0!important;width:1920px!important;height:1080px!important;margin:0!important;visibility:visible!important;pointer-events:none!important;user-select:none!important}
[data-object-reveal-slide] *{pointer-events:none!important;user-select:none!important}
[data-content-fade-slide] .el{will-change:opacity}
#stage > .slide.motion-authored-foreground-hidden .el{opacity:0!important}
#motionToggleBtn{width:auto;min-width:132px;min-height:34px;padding:0 12px;gap:7px;font:800 12px/1 var(--font-body);white-space:nowrap;border:1px solid rgba(15,118,110,.34);border-radius:8px;cursor:pointer}
#motionToggleBtn[data-motion-enabled="true"]{color:#0f766e;background:rgba(15,118,110,.10);border-color:rgba(15,118,110,.42)}
#motionToggleBtn[data-motion-enabled="false"]{color:rgba(24,32,40,.66);background:rgba(18,24,30,.045)}
#motionToggleBtn:focus-visible{outline:2px solid #3fd0e8;outline-offset:2px}
""".strip()
MOTION_RUNTIME_JS = r"""
(() => {
  'use strict';

  const VERSION = 'projection-content-fade-v6';
  const MODE = 'content-fade';
  const TITLE_DELAY_MS = 0;
  const CONTENT_DELAY_MS = 220;
  const FADE_DURATION_MS = 900;
  const EASING = 'cubic-bezier(.2,.7,.2,1)';
  const stage = document.querySelector('#stage');
  const player = document.querySelector('#player');
  const slidePlayer = window.SlidePlayer;
  const reduceMotionQuery = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;
  const query = new URLSearchParams(window.location.search);
  const forceMotionPreview = query.get('motion') === 'force';
  const respectReducedMotion = query.get('motion') === 'respect';
  const defaultMotionOverride = forceMotionPreview || !respectReducedMotion;

  let motionEnabled = true;
  let motionUserOverride = defaultMotionOverride;
  let toggleButton = null;
  let activeRun = null;
  let cloneSequence = 0;
  let scheduledRevealFrame = 0;
  let lastPresentationMode = false;

  document.documentElement.dataset.motionPreview = VERSION;
  document.documentElement.dataset.motionMode = MODE;
  document.documentElement.dataset.motionRevealMode = MODE;
  document.documentElement.dataset.motionEnabled = 'true';
  document.documentElement.dataset.motionForced = defaultMotionOverride ? 'true' : 'false';
  document.documentElement.dataset.motionInitStage = 'dependencies-pending';

  if (!stage || !player || !slidePlayer || typeof Element.prototype.animate !== 'function') {
    document.documentElement.dataset.motionInitStage = 'unsupported';
    return;
  }

  const diagnostics = {
    version: VERSION,
    mode: MODE,
    runs: 0,
    completed: 0,
    cancelled: 0,
    skipped: 0,
    lastIndex: slidePlayer.getCurrentIndex(),
    lastObjectCount: 0,
    lastTitleObjectCount: 0,
    lastContentObjectCount: 0,
    lastBackgroundExcluded: false,
    lastEnabled: motionEnabled,
    lastTrigger: 'ready',
    lastReason: 'ready',
    lastModeTransition: 'edit'
  };

  function isPresentationMode() {
    return player.dataset.uiMode === 'presentation'
      && !player.classList.contains('editor-shell');
  }

  function prefersReducedMotion() {
    return respectReducedMotion
      && !forceMotionPreview
      && !motionUserOverride
      && !!(reduceMotionQuery && reduceMotionQuery.matches);
  }

  function updateToggleButton() {
    if (!toggleButton) return;
    const label = motionEnabled ? '動畫：開' : '動畫：關';
    toggleButton.dataset.motionEnabled = motionEnabled ? 'true' : 'false';
    toggleButton.setAttribute('aria-pressed', motionEnabled ? 'true' : 'false');
    toggleButton.setAttribute('aria-label', '投影動畫 ' + label);
    toggleButton.title = '投影動畫 ' + label;
    const labelNode = toggleButton.querySelector('[data-motion-toggle-label]');
    if (labelNode) labelNode.textContent = label;
  }

  function captureVisibility(slide) {
    return {
      value: slide.style.getPropertyValue('visibility'),
      priority: slide.style.getPropertyPriority('visibility')
    };
  }

  function restoreVisibility(slide, saved) {
    if (!slide) return;
    if (saved && saved.value) slide.style.setProperty('visibility', saved.value, saved.priority || '');
    else slide.style.removeProperty('visibility');
  }

  function rewriteCloneIds(clone, token) {
    const idNodes = [];
    if (clone.id) idNodes.push(clone);
    idNodes.push(...clone.querySelectorAll('[id]'));
    const replacements = new Map();
    idNodes.forEach((node, index) => {
      const original = node.id;
      if (!original || replacements.has(original)) return;
      const next = token + '-' + index + '-' + original;
      replacements.set(original, next);
      node.id = next;
    });
    if (!replacements.size) return;
    [clone, ...clone.querySelectorAll('*')].forEach((node) => {
      Array.from(node.attributes || []).forEach((attribute) => {
        let value = attribute.value;
        if (!value) return;
        if (
          attribute.name === 'aria-labelledby'
          || attribute.name === 'aria-describedby'
          || attribute.name === 'for'
        ) {
          value = value.split(/\s+/).map((part) => replacements.get(part) || part).join(' ');
        } else {
          replacements.forEach((next, original) => {
            value = value.split('url(#' + original + ')').join('url(#' + next + ')');
            if (value === '#' + original) value = '#' + next;
          });
        }
        if (value !== attribute.value) node.setAttribute(attribute.name, value);
      });
    });
  }

  function motionRevealRole(node) {
    const explicit = node.dataset.motionRole || node.dataset.motionRevealRole || '';
    if (explicit === 'title' || explicit === 'content') return explicit;

    const composite = node.dataset.editComposite || '';
    if (/(?:^|[-_])(cover|hero|title|headline|heading)(?:$|[-_])/i.test(composite)) {
      return 'title';
    }

    const classTokens = String(node.className || '').split(/\s+/).filter(Boolean);
    const titleLike = classTokens.some((token) => (
      /(?:^|[-_])(title|headline|heading)(?:$|[-_])/i.test(token)
    ));
    return titleLike ? 'title' : 'content';
  }

  function hideAuthoredForeground(slide) {
    const hadClass = slide.classList.contains('motion-authored-foreground-hidden');
    slide.classList.add('motion-authored-foreground-hidden');
    return { slide, hadClass };
  }

  function restoreAuthoredForeground(state) {
    if (!state?.slide || state.hadClass) return;
    state.slide.classList.remove('motion-authored-foreground-hidden');
  }

  function removeBackgroundFromClone(clone) {
    clone.setAttribute('data-motion-background-excluded', 'true');
    clone.dataset.motionBackgroundExcluded = 'true';
    [
      'data-pptx-background-image',
      'data-pptx-background-image-src',
      'data-pptx-background-image-embedded',
      'data-editor-slide-mask'
    ].forEach((attribute) => clone.removeAttribute(attribute));
    clone.style.setProperty('background', 'transparent', 'important');
    clone.style.setProperty('background-image', 'none', 'important');
    clone.style.setProperty('background-color', 'transparent', 'important');
  }

  function makeClone(slide) {
    const clone = slide.cloneNode(true);
    clone.classList.add('active');
    clone.dataset.objectRevealSlide = VERSION;
    clone.dataset.pageFadeClone = VERSION;
    clone.dataset.contentFadeSlide = VERSION;
    clone.setAttribute('aria-hidden', 'true');
    removeBackgroundFromClone(clone);
    clone.querySelectorAll('[contenteditable]').forEach((node) => node.removeAttribute('contenteditable'));
    clone.querySelectorAll('[tabindex]').forEach((node) => node.removeAttribute('tabindex'));
    rewriteCloneIds(clone, 'page-fade-' + (++cloneSequence));
    clone.style.setProperty('display', 'block', 'important');
    clone.style.setProperty('visibility', 'visible', 'important');
    clone.style.setProperty('opacity', '1');
    return clone;
  }

  function finishRun(run, reason) {
    if (!run || run.finished) return;
    run.finished = true;
    run.animations?.forEach((animation) => {
      try { animation.cancel(); } catch (error) {}
    });
    restoreAuthoredForeground(run.authoredForeground);
    restoreVisibility(run.targetSlide, run.targetVisibility);
    run.layer.remove();
    if (activeRun === run) activeRun = null;
    diagnostics.lastReason = reason;
    document.documentElement.dataset.motionRunState = reason;
  }

  function cancelActiveRun(reason = 'cancelled') {
    if (!activeRun) return;
    diagnostics.cancelled += 1;
    finishRun(activeRun, reason);
  }

  function runContentFade(slide, index, trigger) {
    if (!isPresentationMode() || !slide) return;
    if (activeRun) cancelActiveRun('replaced');
    if (!motionEnabled) {
      diagnostics.skipped += 1;
      diagnostics.lastReason = 'disabled';
      document.documentElement.dataset.motionRunState = 'disabled';
      return;
    }
    if (prefersReducedMotion()) {
      diagnostics.skipped += 1;
      diagnostics.lastReason = 'reduced-motion';
      document.documentElement.dataset.motionRunState = 'reduced-motion';
      return;
    }

    const layer = document.createElement('div');
    layer.dataset.objectRevealLayer = VERSION;
    layer.dataset.pageFadeLayer = VERSION;
    layer.dataset.contentFadeLayer = VERSION;
    layer.setAttribute('aria-hidden', 'true');
    const clone = makeClone(slide);
    layer.appendChild(clone);
    stage.appendChild(layer);

    const targetVisibility = captureVisibility(slide);
    const authoredForeground = hideAuthoredForeground(slide);
    layer.style.opacity = '1';
    const revealNodes = [...clone.querySelectorAll('.el')].filter((node) => {
      const style = getComputedStyle(node);
      return style.display !== 'none' && style.visibility !== 'hidden';
    });
    const titleNodes = [];
    const contentNodes = [];
    revealNodes.forEach((node) => {
      const role = motionRevealRole(node);
      node.dataset.motionRevealRole = role;
      node.style.setProperty('opacity', '0');
      (role === 'title' ? titleNodes : contentNodes).push(node);
    });
    const animations = revealNodes.map((node) => node.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      {
        duration: FADE_DURATION_MS,
        delay: motionRevealRole(node) === 'title' ? TITLE_DELAY_MS : CONTENT_DELAY_MS,
        easing: EASING,
        fill: 'both'
      }
    ));
    const run = {
      layer,
      clone,
      animations,
      targetSlide: slide,
      targetVisibility,
      authoredForeground,
      finished: false
    };
    activeRun = run;
    diagnostics.runs += 1;
    diagnostics.lastIndex = index;
    diagnostics.lastObjectCount = clone.querySelectorAll('.el').length;
    diagnostics.lastTitleObjectCount = titleNodes.length;
    diagnostics.lastContentObjectCount = contentNodes.length;
    diagnostics.lastBackgroundExcluded = clone.dataset.motionBackgroundExcluded === 'true';
    diagnostics.lastEnabled = motionEnabled;
    diagnostics.lastTrigger = trigger;
    diagnostics.lastReason = 'running';
    document.documentElement.dataset.motionRunState = 'running';
    document.documentElement.dataset.motionRunCount = String(diagnostics.runs);
    document.documentElement.dataset.motionObjectCount = String(diagnostics.lastObjectCount);
    document.documentElement.dataset.motionTitleObjectCount = String(titleNodes.length);
    document.documentElement.dataset.motionContentObjectCount = String(contentNodes.length);
    document.documentElement.dataset.motionTrigger = trigger;

    Promise.all(animations.map((animation) => animation.finished)).then(() => {
      if (activeRun !== run || run.finished) return;
      diagnostics.completed += 1;
      finishRun(run, 'completed');
    }).catch(() => {});
  }

  function scheduleContentFade(index, trigger) {
    if (scheduledRevealFrame) cancelAnimationFrame(scheduledRevealFrame);
    scheduledRevealFrame = requestAnimationFrame(() => {
      scheduledRevealFrame = 0;
      const resolvedIndex = Number.isFinite(index) ? index : slidePlayer.getCurrentIndex();
      runContentFade(slidePlayer.getSlides()[resolvedIndex], resolvedIndex, trigger);
    });
  }

  function setMotionEnabled(nextEnabled, replay = true, explicit = false) {
    motionEnabled = !!nextEnabled;
    if (explicit) motionUserOverride = motionEnabled;
    diagnostics.lastEnabled = motionEnabled;
    document.documentElement.dataset.motionEnabled = motionEnabled ? 'true' : 'false';
    updateToggleButton();
    if (!motionEnabled) cancelActiveRun('disabled');
    else if (replay && isPresentationMode()) scheduleContentFade(slidePlayer.getCurrentIndex(), 'enabled');
    window.dispatchEvent(new CustomEvent('motionpreviewchange', {
      detail: { enabled: motionEnabled, mode: MODE, version: VERSION }
    }));
    return motionEnabled;
  }

  function installToggleButton() {
    const settingsPanel = document.querySelector('#edit-slide-style-panel');
    if (!settingsPanel || settingsPanel.querySelector('#motionToggleBtn')) return;
    toggleButton = document.createElement('button');
    toggleButton.id = 'motionToggleBtn';
    toggleButton.type = 'button';
    toggleButton.className = 'motion-control';
    toggleButton.dataset.editorChrome = 'true';
    toggleButton.style.cssText = 'display:inline-flex;align-items:center;justify-content:center;';
    toggleButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h3l2-5 4 10 2-5h5"/></svg><span data-motion-toggle-label></span>';
    toggleButton.addEventListener('click', (event) => {
      event.stopPropagation();
      setMotionEnabled(!motionEnabled, true, true);
    });

    const settingsRow = document.createElement('section');
    settingsRow.dataset.motionSettingsRow = 'true';
    settingsRow.dataset.editorChrome = 'true';
    settingsRow.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:14px;padding:12px 0;border-top:1px solid rgba(18,24,30,.12);';

    const settingsCopy = document.createElement('div');
    settingsCopy.style.cssText = 'display:flex;flex-direction:column;gap:4px;min-width:0;';

    const settingsTitle = document.createElement('strong');
    settingsTitle.textContent = '投影動畫';
    settingsTitle.style.cssText = 'font:800 13px/1.2 var(--font-body);';

    const settingsHelp = document.createElement('span');
    settingsHelp.textContent = '切換投影時的物件淡入動畫';
    settingsHelp.style.cssText = 'font:500 11px/1.35 var(--font-body);opacity:.72;';

    settingsCopy.append(settingsTitle, settingsHelp);
    settingsRow.append(settingsCopy, toggleButton);
    const maskSection = settingsPanel.querySelector('[data-slide-mask-controls]');
    settingsPanel.insertBefore(settingsRow, maskSection || null);
    updateToggleButton();
  }

  document.addEventListener('slidechange', (event) => {
    const nextIndex = Number(event.detail && event.detail.index);
    const index = Number.isFinite(nextIndex) ? nextIndex : slidePlayer.getCurrentIndex();
    diagnostics.lastIndex = index;
    if (!isPresentationMode()) {
      cancelActiveRun('edit-mode');
      return;
    }
    scheduleContentFade(index, 'page-change');
  });

  document.addEventListener('editmodechange', (event) => {
    const editMode = !!(event.detail && event.detail.editMode);
    diagnostics.lastModeTransition = editMode ? 'presentation-to-edit' : 'edit-to-presentation';
    lastPresentationMode = !editMode;
    if (editMode) {
      if (scheduledRevealFrame) {
        cancelAnimationFrame(scheduledRevealFrame);
        scheduledRevealFrame = 0;
      }
      cancelActiveRun('returned-to-edit');
    } else {
      scheduleContentFade(slidePlayer.getCurrentIndex(), 'enter-presentation');
    }
  });

  if (typeof MutationObserver === 'function') {
    const observer = new MutationObserver(() => {
      const presentationMode = isPresentationMode();
      if (presentationMode === lastPresentationMode) return;
      lastPresentationMode = presentationMode;
      if (!presentationMode) {
        if (scheduledRevealFrame) {
          cancelAnimationFrame(scheduledRevealFrame);
          scheduledRevealFrame = 0;
        }
        cancelActiveRun('observer-returned-to-edit');
      } else {
        scheduleContentFade(slidePlayer.getCurrentIndex(), 'presentation-state-observer');
      }
    });
    observer.observe(player, { attributes: true, attributeFilter: ['class', 'data-ui-mode'] });
  }

  if (reduceMotionQuery) {
    const handleReducedMotion = () => {
      document.documentElement.dataset.motionReduced = reduceMotionQuery.matches ? 'true' : 'false';
      if (prefersReducedMotion()) cancelActiveRun('reduced-motion');
    };
    if (typeof reduceMotionQuery.addEventListener === 'function') reduceMotionQuery.addEventListener('change', handleReducedMotion);
    else if (typeof reduceMotionQuery.addListener === 'function') reduceMotionQuery.addListener(handleReducedMotion);
    handleReducedMotion();
  }

  window.addEventListener('pagehide', () => cancelActiveRun('pagehide'));
  installToggleButton();
  window.MotionPreview = {
    version: VERSION,
    mode: MODE,
    get enabled() { return motionEnabled; },
    setEnabled: (enabled, replay = true) => setMotionEnabled(enabled, replay),
    diagnostics: () => ({
      ...diagnostics,
      activeLayers: stage.querySelectorAll('[data-object-reveal-layer]').length,
      activeClones: stage.querySelectorAll('[data-object-reveal-slide]').length,
      presentationMode: isPresentationMode(),
      reducedMotion: prefersReducedMotion(),
      forcedMotionPreview: forceMotionPreview,
      respectReducedMotion,
      motionUserOverride,
      reducedMotionPreference: !!(reduceMotionQuery && reduceMotionQuery.matches),
      revealMode: MODE,
      titleDelayMs: TITLE_DELAY_MS,
      contentDelayMs: CONTENT_DELAY_MS,
      fadeDurationMs: FADE_DURATION_MS,
      revealSequence: 'title-then-content',
      titleObjectCount: diagnostics.lastTitleObjectCount,
      contentObjectCount: diagnostics.lastContentObjectCount,
      backgroundExcluded: diagnostics.lastBackgroundExcluded,
      motionEnabled
    }),
    play: (trigger = 'manual') => {
      if (!isPresentationMode()) return false;
      scheduleContentFade(slidePlayer.getCurrentIndex(), trigger);
      return true;
    },
    cancel: () => cancelActiveRun('manual-cancel')
  };
  document.documentElement.dataset.motionInitStage = 'ready';
  lastPresentationMode = isPresentationMode();
  window.dispatchEvent(new CustomEvent('motionpreviewready', { detail: { version: VERSION } }));
})();
""".strip()


MOTION_RUNTIME_SOURCE_SHA256 = hashlib.sha256(
    (MOTION_RUNTIME_CSS + "\n" + MOTION_RUNTIME_JS).encode("utf-8")
).hexdigest().upper()


def motion_runtime_style() -> str:
    """Return the owned style block used by the formal HTML renderer."""

    return (
        f'<style data-css-owner="editor-chrome" '
        f'data-motion-runtime-style="{MOTION_RUNTIME_VERSION}">\n'
        f"{MOTION_RUNTIME_CSS}\n</style>"
    )


def motion_runtime_script() -> str:
    """Return the self-contained runtime script appended after the editor."""

    return f'<script data-motion-runtime="{MOTION_RUNTIME_VERSION}">\n{MOTION_RUNTIME_JS}\n</script>'


def motion_runtime_root_attributes() -> str:
    """Return static root metadata used by the runtime and manifest QA."""

    return (
        f'data-motion-runtime="{MOTION_RUNTIME_VERSION}" '
        f'data-motion-source-sha256="{MOTION_RUNTIME_SOURCE_SHA256}"'
    )


def motion_runtime_manifest() -> dict[str, object]:
    """Return provenance and behavior metadata for generated manifests."""

    return {
        "version": MOTION_RUNTIME_VERSION,
        "source": "scripts/html_motion_runtime.py",
        "source_sha256": MOTION_RUNTIME_SOURCE_SHA256,
        "scope": "presentation-only",
        "projection_only": True,
        "mode": MOTION_MODE,
        "default_enabled": True,
        "toolbar_toggle": False,
        "toolbar_location": "slide-settings-panel",
        "trigger_paths": [
            "editmodechange",
            "player-state-observer",
            "slidechange",
            "explicit-toggle",
        ],
        "clone_scope": "incoming-current-slide-only",
        "outgoing_page_transition": False,
        "title_delay_ms": MOTION_TITLE_DELAY_MS,
        "content_delay_ms": MOTION_CONTENT_DELAY_MS,
        "delay_ms": MOTION_DELAY_MS,
        "duration_ms": MOTION_DURATION_MS,
        "translate_y_px": 0,
        "scale_from": 1.0,
        "transition": "title-then-delayed-content-fade-in",
        "sequence": "title-then-content",
        "content_scope": "projection-clone .el objects split by data-motion-role or title-like class",
        "background_behavior": "target-slide-background-static; projection-clone-foreground-only",
        "background_scope": "not-in-motion-clone",
        "page_change_only": True,
        "key_navigation_unchanged": True,
        "reduced_motion": "forced-by-default-for-visible-presentation; use ?motion=respect to honor system preference",
        "reduced_motion_opt_in_query": "motion=respect",
        "toggle_state_lifetime": "current-page-session",
    }
