"""Opt-in HTML + generated-background experiment.

This runner never mutates the input HTML and never writes to production gallery or
deploy directories. The legacy ``prepare``/``apply`` commands support a single
background trial; ``prepare-deck``/``materialize-deck``/``apply-deck`` measure and
attach one generated background per slide beneath the unchanged HTML foreground.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = ROOT / "workspace" / "html-image-background"
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080
TARGET_ASPECT_RATIO = CANVAS_WIDTH / CANVAS_HEIGHT
ASPECT_RATIO_TOLERANCE = 0.005
PROTECTION_HALO_PX = 96
MIN_OPEN_ZONE_WIDTH = 320
MIN_OPEN_ZONE_HEIGHT = 240
LAYOUT_SAFE_ZONE_PROFILES = {
    "cover-photo-frame": "half-image",
    "cover-photo-frame-reverse": "half-image",
    "chapter-text-left-photo-brand": "half-image",
    "photo-left-overlay-title-right": "half-image",
    "cover-photo-overlay-block": "full-bleed",
    "chapter-fullbleed-overlay-title": "full-bleed",
    "closing-photo-overlay-contact": "full-bleed",
}
LAYOUT_DECORATION_CACHE: dict[str, dict] = {}
PALETTE_TOKEN_NAMES = (
    "--bg",
    "--surface",
    "--ink",
    "--text",
    "--primary",
    "--muted",
    "--accent",
    "--support",
    "--support-accent",
    "--surface-text",
    "--surface-muted",
)
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
FILE_URI_RE = re.compile(r"^file:///", re.IGNORECASE)
NEUTRAL_STYLE = """
<style id="html-image-background-experiment-neutral" data-css-owner="background-experiment">
  /* Experiment-only paint override. Layout geometry remains untouched. */
  html body #stage > section.slide,
  html body section.slide {
    background-color: var(--bg, #f4f1ea);
    background-image: none;
  }
</style>
"""

MASK_SCRIPT = r"""
<script id="html-image-background-mask-builder">
window.addEventListener('load', async () => {
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  const slide = document.querySelector('.slide.active') || document.querySelector('.slide');
  if (!slide) return;
  const slideRect = slide.getBoundingClientRect();
  const canvas = document.createElement('canvas');
  canvas.width = 1920;
  canvas.height = 1080;
  canvas.style.cssText = 'position:absolute;inset:0;width:1920px;height:1080px;z-index:2147483647;pointer-events:none';
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, 1920, 1080);
  const GUARD = 96;

  const alphaOf = (value) => {
    const input = String(value || '').trim().toLowerCase();
    if (!input || input === 'transparent' || input === 'none') return 0;
    const rgba = input.match(/^rgba?\((.*)\)$/);
    if (rgba) {
      const parts = rgba[1].split(/[,\s/]+/).filter(Boolean);
      const alpha = parts.length >= 4 ? Number(parts[3]) : 1;
      return Number.isFinite(alpha) ? alpha : 1;
    }
    const colorFunction = input.match(/\/\s*([\d.]+)\s*\)$/);
    return colorFunction ? Number(colorFunction[1]) : 1;
  };
  const hasDirectText = (el) => Array.from(el.childNodes).some(
    node => node.nodeType === Node.TEXT_NODE && node.textContent.trim()
  );
  const hasOutline = (style) =>
    style.outlineStyle !== 'none' &&
    parseFloat(style.outlineWidth) > 0 &&
    alphaOf(style.outlineColor) > 0.04;
  const hasBorder = (style) =>
    ['Top', 'Right', 'Bottom', 'Left'].some(side =>
      parseFloat(style[`border${side}Width`]) > 0 &&
      style[`border${side}Style`] !== 'none'
    ) || hasOutline(style);
  const hasVisualPaint = (style) =>
    alphaOf(style.backgroundColor) > 0.04 ||
    Boolean(style.backgroundImage && style.backgroundImage !== 'none') ||
    Boolean(style.boxShadow && style.boxShadow !== 'none') ||
    Boolean(style.textShadow && style.textShadow !== 'none') ||
    Boolean(style.filter && style.filter !== 'none') ||
    hasBorder(style);
  const hasProtectedPseudo = (el, pseudo) => {
    const style = getComputedStyle(el, pseudo);
    if (!style || style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) {
      return false;
    }
    const content = String(style.content || '').trim();
    const hasContent = content && !['none', 'normal', '""', "''"].includes(content);
    return hasContent || hasVisualPaint(style);
  };
  const isProtected = (el, style) => {
    const tag = el.tagName;
    if (['IMG', 'SVG', 'CANVAS', 'TABLE', 'VIDEO'].includes(tag)) return true;
    if (hasDirectText(el)) return true;
    if (hasVisualPaint(style)) return true;
    return hasProtectedPseudo(el, '::before') || hasProtectedPseudo(el, '::after');
  };

  const boxes = [];
  slide.querySelectorAll('*').forEach(el => {
    if (el === canvas || el.closest('#html-image-background-mask-builder')) return;
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return;
    if (el.matches('[data-content-area="true"], [data-edit-layout-only="true"], .prod-frame, .title-flow-stack')) return;
    const rect = el.getBoundingClientRect();
    if (rect.width < 0.5 || rect.height < 0.5 || !isProtected(el, style)) return;
    const scaleX = 1920 / slideRect.width;
    const scaleY = 1080 / slideRect.height;
    const pad = GUARD;
    boxes.push({
      x: Math.max(0, (rect.left - slideRect.left) * scaleX - pad),
      y: Math.max(0, (rect.top - slideRect.top) * scaleY - pad),
      w: Math.min(1920, rect.width * scaleX + pad * 2),
      h: Math.min(1080, rect.height * scaleY + pad * 2)
    });
  });

  // Collapse nearby element boxes into a few broad rectangular composition zones.
  // These rectangles guide generation; they are not used to cut the final image.
  const gap = 12;
  let merged = boxes.slice();
  let changed = true;
  while (changed) {
    changed = false;
    outer: for (let i = 0; i < merged.length; i++) {
      for (let j = i + 1; j < merged.length; j++) {
        const a = merged[i], b = merged[j];
        const near = a.x <= b.x + b.w + gap && a.x + a.w + gap >= b.x &&
          a.y <= b.y + b.h + gap && a.y + a.h + gap >= b.y;
        if (!near) continue;
        const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
        const right = Math.max(a.x + a.w, b.x + b.w);
        const bottom = Math.max(a.y + a.h, b.y + b.h);
        merged[i] = { x, y, w: right - x, h: bottom - y };
        merged.splice(j, 1);
        changed = true;
        break outer;
      }
    }
  }

  ctx.fillStyle = '#000';
  merged.forEach(box => ctx.fillRect(box.x, box.y, box.w, box.h));
  slide.replaceChildren(canvas);
  document.body.style.background = '#000';
});
</script>
"""

PER_SLIDE_MASK_SCRIPT = r"""
<script id="html-image-background-per-slide-mask-builder">
window.addEventListener('load', async () => {
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  const stage = document.querySelector('#stage');
  const slides = stage
    ? Array.from(stage.children).filter(item => item.classList.contains('slide'))
    : Array.from(document.querySelectorAll('.slide'));
  if (!slides.length) return;

  const originalState = slides.map(slide => ({
    className: slide.className,
    style: slide.getAttribute('style'),
  }));
  const orderedSlides = slides.slice().sort((a, b) =>
    Number(a.dataset.index ?? 0) - Number(b.dataset.index ?? 0)
  );
  const GUARD = 96;
  const PALETTE_NAMES = [
    '--bg', '--surface', '--ink', '--text', '--primary', '--muted',
    '--accent', '--support', '--support-accent', '--surface-text', '--surface-muted'
  ];
  const setActive = (target) => {
    slides.forEach(item => {
      const names = String(item.className || '').split(/\s+/).filter(Boolean).filter(name => name !== 'active');
      if (item === target) names.push('active');
      item.className = names.join(' ');
    });
  };
  const alphaOf = (value) => {
    const input = String(value || '').trim().toLowerCase();
    if (!input || input === 'transparent' || input === 'none') return 0;
    const rgba = input.match(/^rgba?\((.*)\)$/);
    if (rgba) {
      const parts = rgba[1].split(/[,\s/]+/).filter(Boolean);
      const alpha = parts.length >= 4 ? Number(parts[3]) : 1;
      return Number.isFinite(alpha) ? alpha : 1;
    }
    const colorFunction = input.match(/\/\s*([\d.]+)\s*\)$/);
    return colorFunction ? Number(colorFunction[1]) : 1;
  };
  const hasDirectText = (el) => Array.from(el.childNodes).some(
    node => node.nodeType === Node.TEXT_NODE && node.textContent.trim()
  );
  const hasOutline = (style) =>
    style.outlineStyle !== 'none' &&
    parseFloat(style.outlineWidth) > 0 &&
    alphaOf(style.outlineColor) > 0.04;
  const hasBorder = (style) =>
    ['Top', 'Right', 'Bottom', 'Left'].some(side =>
      parseFloat(style[`border${side}Width`]) > 0 &&
      style[`border${side}Style`] !== 'none'
    ) || hasOutline(style);
  const hasVisualPaint = (style) =>
    alphaOf(style.backgroundColor) > 0.04 ||
    Boolean(style.backgroundImage && style.backgroundImage !== 'none') ||
    Boolean(style.boxShadow && style.boxShadow !== 'none') ||
    Boolean(style.textShadow && style.textShadow !== 'none') ||
    Boolean(style.filter && style.filter !== 'none') ||
    hasBorder(style);
  const hasProtectedPseudo = (el, pseudo) => {
    const style = getComputedStyle(el, pseudo);
    if (!style || style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) {
      return false;
    }
    const content = String(style.content || '').trim();
    const hasContent = content && !['none', 'normal', '""', "''"].includes(content);
    return hasContent || hasVisualPaint(style);
  };
  const readPalette = (slide) => {
    const style = getComputedStyle(slide);
    return Object.fromEntries(PALETTE_NAMES.map(name => [name, style.getPropertyValue(name).trim()])
      .filter(([, value]) => value));
  };
  const nextFrame = (callback) => {
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(callback);
    else setTimeout(callback, 25);
  };
  const sleepFrame = () => new Promise(resolve => nextFrame(() => nextFrame(resolve)));
  const rectToBox = (rect, slideRect, pad) => {
    const scaleX = 1920 / slideRect.width;
    const scaleY = 1080 / slideRect.height;
    return {
      x: Math.max(0, (rect.left - slideRect.left) * scaleX - pad),
      y: Math.max(0, (rect.top - slideRect.top) * scaleY - pad),
      w: Math.min(1920, rect.width * scaleX + pad * 2),
      h: Math.min(1080, rect.height * scaleY + pad * 2),
    };
  };
  const mergeBoxes = (boxes) => {
    const gap = 12;
    let merged = boxes.slice();
    let changed = true;
    while (changed) {
      changed = false;
      outer: for (let i = 0; i < merged.length; i++) {
        for (let j = i + 1; j < merged.length; j++) {
          const a = merged[i], b = merged[j];
          const near = a.x <= b.x + b.w + gap && a.x + a.w + gap >= b.x &&
            a.y <= b.y + b.h + gap && a.y + a.h + gap >= b.y;
          if (!near) continue;
          const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
          const right = Math.max(a.x + a.w, b.x + b.w);
          const bottom = Math.max(a.y + a.h, b.y + b.h);
          merged[i] = { x, y, w: right - x, h: bottom - y };
          merged.splice(j, 1);
          changed = true;
          break outer;
        }
      }
    }
    return merged;
  };

  const records = [];
  for (const slide of orderedSlides) {
    setActive(slide);
    await sleepFrame();

    const slideRect = slide.getBoundingClientRect();
    const boxes = [];
    const foregroundColors = new Set();
    let measurementUncertain = slideRect.width < 1 || slideRect.height < 1;
    slide.querySelectorAll('*').forEach(el => {
      if (el.closest('#html-image-background-per-slide-mask-builder')) return;
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return;
      if (el.matches('[data-content-area="true"], [data-edit-layout-only="true"], .prod-frame, .title-flow-stack')) return;
      const rect = el.getBoundingClientRect();
      const tag = el.tagName;
      const text = hasDirectText(el);
      const pseudoBefore = hasProtectedPseudo(el, '::before');
      const pseudoAfter = hasProtectedPseudo(el, '::after');
      const protectedElement = ['IMG', 'SVG', 'CANVAS', 'TABLE', 'VIDEO'].includes(tag) ||
        text || hasVisualPaint(style) || pseudoBefore || pseudoAfter;
      if (!protectedElement) return;
      if (rect.width < 0.5 || rect.height < 0.5) {
        if (text || ['IMG', 'SVG', 'CANVAS', 'TABLE', 'VIDEO'].includes(tag)) {
          measurementUncertain = true;
        }
        return;
      }
      if (text && style.color && style.color !== 'transparent') foregroundColors.add(style.color);
      boxes.push(rectToBox(rect, slideRect, GUARD));
    });

    records.push({
      index: Number(slide.dataset.index ?? records.length),
      id: slide.id || null,
      scene_id: slide.dataset.sceneId || null,
      scene_role: slide.dataset.sceneRole || null,
      layout_id: slide.dataset.layoutId || null,
      page_number: Number(slide.dataset.pageNumber ?? records.length + 1),
      slide_rect: {
        left: slideRect.left,
        top: slideRect.top,
        width: slideRect.width,
        height: slideRect.height,
      },
      occupied_boxes: mergeBoxes(boxes),
      measurement_guard_px: GUARD,
      measurement_uncertain: measurementUncertain,
      palette_tokens: readPalette(slide),
      foreground_colors: Array.from(foregroundColors),
    });
  }

  slides.forEach((slide, index) => {
    slide.className = originalState[index].className;
    if (originalState[index].style === null) slide.removeAttribute('style');
    else slide.setAttribute('style', originalState[index].style);
  });
  window.__htmlImageBackgroundPerSlideMasks = records;
  document.documentElement.dataset.htmlImageBackgroundMasksReady = 'true';
});
</script>
"""

SINGLE_SLIDE_MASK_SCRIPT = r"""
<script id="html-image-background-single-slide-mask-builder">
window.addEventListener('load', async () => {
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  await new Promise(resolve => setTimeout(resolve, 80));
  const slide = document.getElementById('__TARGET_SLIDE_ID__');
  if (!slide) {
    console.log(JSON.stringify({ type: 'html-image-background-mask', error: 'target slide not found' }));
    return;
  }
  const slideRect = slide.getBoundingClientRect();
  const GUARD = 96;
  const PALETTE_NAMES = [
    '--bg', '--surface', '--ink', '--text', '--primary', '--muted',
    '--accent', '--support', '--support-accent', '--surface-text', '--surface-muted'
  ];
  const alphaOf = (value) => {
    const input = String(value || '').trim().toLowerCase();
    if (!input || input === 'transparent' || input === 'none') return 0;
    const rgba = input.match(/^rgba?\((.*)\)$/);
    if (rgba) {
      const parts = rgba[1].split(/[,\s/]+/).filter(Boolean);
      const alpha = parts.length >= 4 ? Number(parts[3]) : 1;
      return Number.isFinite(alpha) ? alpha : 1;
    }
    const colorFunction = input.match(/\/\s*([\d.]+)\s*\)$/);
    return colorFunction ? Number(colorFunction[1]) : 1;
  };
  const hasDirectText = (el) => Array.from(el.childNodes).some(
    node => node.nodeType === 3 && node.textContent.trim()
  );
  const hasOutline = (style) =>
    style.outlineStyle !== 'none' &&
    parseFloat(style.outlineWidth) > 0 &&
    alphaOf(style.outlineColor) > 0.04;
  const hasBorder = (style) =>
    ['Top', 'Right', 'Bottom', 'Left'].some(side =>
      parseFloat(style[`border${side}Width`]) > 0 &&
      style[`border${side}Style`] !== 'none'
    ) || hasOutline(style);
  const hasVisualPaint = (style) =>
    alphaOf(style.backgroundColor) > 0.04 ||
    Boolean(style.backgroundImage && style.backgroundImage !== 'none') ||
    Boolean(style.boxShadow && style.boxShadow !== 'none') ||
    Boolean(style.textShadow && style.textShadow !== 'none') ||
    Boolean(style.filter && style.filter !== 'none') ||
    hasBorder(style);
  const hasProtectedPseudo = (el, pseudo) => {
    const style = getComputedStyle(el, pseudo);
    if (!style || style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) {
      return false;
    }
    const content = String(style.content || '').trim();
    const hasContent = content && !['none', 'normal', '""', "''"].includes(content);
    return hasContent || hasVisualPaint(style);
  };
  const readPalette = () => {
    const style = getComputedStyle(slide);
    return Object.fromEntries(PALETTE_NAMES.map(name => [name, style.getPropertyValue(name).trim()])
      .filter(([, value]) => value));
  };
  const toBox = (rect, pad) => {
    const scaleX = 1920 / slideRect.width;
    const scaleY = 1080 / slideRect.height;
    return {
      x: Math.max(0, (rect.left - slideRect.left) * scaleX - pad),
      y: Math.max(0, (rect.top - slideRect.top) * scaleY - pad),
      w: Math.min(1920, rect.width * scaleX + pad * 2),
      h: Math.min(1080, rect.height * scaleY + pad * 2),
    };
  };
  const mergeBoxes = (boxes) => {
    const gap = 12;
    let merged = boxes.slice();
    let changed = true;
    while (changed) {
      changed = false;
      outer: for (let i = 0; i < merged.length; i++) {
        for (let j = i + 1; j < merged.length; j++) {
          const a = merged[i], b = merged[j];
          const near = a.x <= b.x + b.w + gap && a.x + a.w + gap >= b.x &&
            a.y <= b.y + b.h + gap && a.y + a.h + gap >= b.y;
          if (!near) continue;
          const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
          const right = Math.max(a.x + a.w, b.x + b.w);
          const bottom = Math.max(a.y + a.h, b.y + b.h);
          merged[i] = { x, y, w: right - x, h: bottom - y };
          merged.splice(j, 1);
          changed = true;
          break outer;
        }
      }
    }
    return merged;
  };

  const boxes = [];
  const foregroundColors = new Set();
  let measurementUncertain = slideRect.width < 1 || slideRect.height < 1;
  slide.querySelectorAll('*').forEach(el => {
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return;
    if (el.matches('[data-content-area="true"], [data-edit-layout-only="true"], .prod-frame, .title-flow-stack')) return;
    const rect = el.getBoundingClientRect();
    const text = hasDirectText(el);
    const pseudoBefore = hasProtectedPseudo(el, '::before');
    const pseudoAfter = hasProtectedPseudo(el, '::after');
    const protectedElement = ['IMG', 'SVG', 'CANVAS', 'TABLE', 'VIDEO'].includes(el.tagName) ||
      text || hasVisualPaint(style) || pseudoBefore || pseudoAfter;
    if (!protectedElement) return;
    if (rect.width < 0.5 || rect.height < 0.5) {
      if (text || ['IMG', 'SVG', 'CANVAS', 'TABLE', 'VIDEO'].includes(el.tagName)) {
        measurementUncertain = true;
      }
      return;
    }
    if (text && style.color && style.color !== 'transparent') foregroundColors.add(style.color);
    boxes.push(toBox(rect, GUARD));
  });

  const records = boxes.slice();
  console.log(JSON.stringify({ type: 'html-image-background-mask', payload: {
    index: Number(slide.dataset.index || 0),
    id: slide.id || null,
    scene_id: slide.dataset.sceneId || null,
    scene_role: slide.dataset.sceneRole || null,
    layout_id: slide.dataset.layoutId || null,
    page_number: Number(slide.dataset.pageNumber || 1),
    slide_rect: {
      left: slideRect.left,
      top: slideRect.top,
      width: slideRect.width,
      height: slideRect.height,
    },
    occupied_boxes: mergeBoxes(records),
    measurement_guard_px: GUARD,
    measurement_uncertain: measurementUncertain,
    palette_tokens: readPalette(),
    foreground_colors: Array.from(foregroundColors),
  }}));
});
</script>
"""

PROMPT = """Use case: productivity-visual
Asset type: one model-native 16:9 raster background placed underneath an existing editable HTML slide
Image input order is binding:
1. Image 1 is the actual clean foreground screenshot. It has the highest spatial and contrast priority. Do not reproduce its content.
2. Image 2 is the occupancy mask. It is conservative guidance only and never overrides visible foreground evidence in Image 1.
Primary request: create one continuous edge-to-edge ambient material field that supports the existing foreground palette and hierarchy, with a visibly separate 2A material layer and a visibly separate 2B edge/corner/seam design layer.
Composition/framing: preserve a 96px protected halo around every text glyph, line, border, shadow, pseudo-element, card, chart, icon, and design object. Keep 2A low-frequency and subordinate across that halo. Verified connected open zones must be at least 320x240px; place the required 2B primitives only in the declared or profile-default 2B zones, using the verified open zones and outer edges. 2B is allowed to be cropped by the slide edge and is not a foreground object.
Continuity rule: quiet regions must arise naturally inside the same material field. Never trace, echo, outline, brighten, darken, blur, or cut out the occupancy-mask shape; no visible mask boundary or panel-shaped calm zone. If no verified open zone exists, use the profile 2B edge/corner/seam zones with low-frequency 2A; texture-only mode is not acceptable.
Palette and contrast: use the supplied Theme palette and foreground colors as a binding luminance contract. Keep normal text at or above 4.5:1, large text at or above 3:1, and meaningful design lines or nodes at or above 3:1.
Hard exclusions: no text, pseudo-text, letters, numbers, logos, watermarks, UI, cards, fake panels, white boxes, cutouts, blur patches, rings, grids, maps, coastlines, contours, routes, network lines, nodes, crosshairs, compass graphics, diagrams, doodles, plants, flowers, moons, stars, DNA, molecules, buildings, flags, rulers, blueprint marks, stamps, people, devices, or recognizable objects. Do not create a full-page frame or a foreground-like object. Profile-authorized 2B primitives such as cropped bands, short hairlines, L-shaped corner brackets, dots/dashes, arcs, or angled transitions are explicitly allowed and required only inside the declared/default 2B zones; they must remain abstract decoration and must not become a chart, UI, symbol, or recognizable object.
Raster-layer boundary: those authorized 2B primitives are pixels in this generated background only; do not imply, redraw, or create editable HTML/CSS/inline-SVG/pseudo-element foreground objects.
2B visibility gate: the final raster must visibly show the specified 2B edge/corner/seam treatment at normal slide viewing size. A texture-only, gradient-only, broad-color-field-only, or invisible-ornament result fails and must be regenerated.
Output: background raster only; do not redraw, imitate, flatten, or replace the editable HTML foreground.
"""

PER_SLIDE_PROMPT = PROMPT


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _inject_before_head_close(html: str, fragment: str) -> str:
    marker = "</head>"
    index = html.lower().find(marker)
    if index < 0:
        raise ValueError("Input HTML has no </head> tag.")
    return html[:index] + fragment + "\n" + html[index:]


def _remove_neutral_paint_override(html: str) -> str:
    """Remove the prepare-only neutral paint rule before creating a final deck."""
    pattern = re.compile(
        r'<style\b(?=[^>]*\bid=["\']html-image-background-experiment-neutral["\'])[^>]*>.*?</style>',
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub("", html, count=1)


def _raster_data_url(path: Path) -> str:
    """Return an inline raster data URL so a file:// HTML remains self-contained."""
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime = mime_types.get(path.suffix.lower())
    if not mime:
        raise ValueError(f"Unsupported raster suffix for inline background: {path.suffix}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_from_file_uri(value: str) -> Path:
    parsed = urlparse(value)
    local = unquote(parsed.path)
    if parsed.netloc:
        local = f"//{parsed.netloc}{local}"
    if re.match(r"^/[A-Za-z]:/", local):
        local = local[1:]
    return Path(local)


def _is_absolute_path_string(value: str) -> bool:
    return bool(
        FILE_URI_RE.match(value)
        or WINDOWS_ABSOLUTE_PATH_RE.match(value)
        or Path(value).is_absolute()
    )


def _portable_workspace_path(path: Path, *, label: str = "workspace path") -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} is outside the repository and cannot enter run.json") from exc
    portable = relative.as_posix()
    if not portable or portable == "." or "\\" in portable or _is_absolute_path_string(portable):
        raise ValueError(f"{label} is not a repository-relative POSIX path: {portable!r}")
    return portable


def _try_portable_workspace_path(path: Path) -> str | None:
    try:
        return _portable_workspace_path(path)
    except ValueError:
        return None


def _resolve_manifest_path(
    value: object,
    *,
    run_dir: Path,
    label: str,
    fallback_base: Path | None = None,
    prefer_run_dir: bool = False,
) -> Path:
    """Resolve legacy absolute paths and repository-relative POSIX paths.

    New manifests are rooted at ``ROOT``. A leading ``./``/``../`` remains a
    legacy run-relative form. For older capture payloads, callers may prefer the
    run directory and still fall back to the repository root.
    """
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError(f"{label} must be a non-empty path")
    raw = str(value).strip()
    if FILE_URI_RE.match(raw):
        return _path_from_file_uri(raw).resolve()
    normalized = raw.replace("\\", "/")
    if WINDOWS_ABSOLUTE_PATH_RE.match(normalized) or Path(normalized).is_absolute():
        return Path(normalized).resolve()

    relative = Path(normalized)
    if normalized.startswith("./") or normalized.startswith("../"):
        candidates = [run_dir / relative]
    else:
        bases = [run_dir, ROOT] if prefer_run_dir else [ROOT, run_dir]
        candidates = [base / relative for base in bases]
    if fallback_base is not None:
        candidates.append(fallback_base / relative)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def _external_file_provenance(path: Path) -> dict:
    """Describe an external input without leaking its host filesystem path."""
    resolved = path.resolve()
    return {
        "scope": "external-untracked",
        "basename": resolved.name,
        "byte_length": resolved.stat().st_size,
        "sha256": _sha256_file(resolved),
    }


def _portable_or_external_source(path: Path) -> tuple[str | None, dict | None]:
    portable = _try_portable_workspace_path(path)
    if portable is not None:
        return portable, None
    return None, _external_file_provenance(path)


def _ensure_repo_resident_copy(path: Path, destination: Path, *, label: str) -> Path:
    """Keep resumable manifest inputs inside the repository without rewriting bytes."""
    resolved = path.resolve()
    if _try_portable_workspace_path(resolved) is not None:
        return resolved
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if _sha256_file(destination) != _sha256_file(resolved):
            raise ValueError(f"Existing portable {label} copy does not match the external input")
    else:
        shutil.copy2(resolved, destination)
    return destination.resolve()


def _portableize_manifest_data(value: object, *, location: str = "run") -> object:
    if isinstance(value, dict):
        return {
            str(key): _portableize_manifest_data(item, location=f"{location}.{key}")
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _portableize_manifest_data(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, str):
        if FILE_URI_RE.match(value):
            return _portable_workspace_path(_path_from_file_uri(value), label=location)
        if WINDOWS_ABSOLUTE_PATH_RE.match(value) or Path(value).is_absolute():
            return _portable_workspace_path(Path(value), label=location)
        if "\\" in value:
            return value.replace("\\", "/")
    return value


def _portable_manifest_violations(value: object, *, location: str = "run") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            issues.extend(_portable_manifest_violations(item, location=f"{location}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            issues.extend(_portable_manifest_violations(item, location=f"{location}[{index}]"))
    elif isinstance(value, str):
        if FILE_URI_RE.match(value) or WINDOWS_ABSOLUTE_PATH_RE.match(value) or Path(value).is_absolute():
            issues.append(f"{location}: absolute path {value!r}")
        if "\\" in value:
            issues.append(f"{location}: backslash path {value!r}")
    return issues


def _write_run_manifest(manifest_path: Path, manifest: dict) -> dict:
    portable = _portableize_manifest_data(manifest)
    if not isinstance(portable, dict):  # pragma: no cover - defensive type guard
        raise TypeError("run manifest must be an object")
    portable["path_contract"] = {
        "base": "repository-root",
        "format": "repository-relative-posix",
        "external_paths_recorded": False,
    }
    issues = _portable_manifest_violations(portable)
    if issues:
        raise ValueError("run.json portability violation: " + "; ".join(issues))
    manifest_path.write_text(
        json.dumps(portable, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return portable


def _raster_dimensions(path: Path) -> tuple[int, int, str | None]:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - environment-specific fallback
        raise RuntimeError("Pillow is required to inspect raster dimensions") from exc
    try:
        with Image.open(path) as image:
            width, height = image.size
            image_format = image.format
    except Exception as exc:
        raise ValueError(f"Unreadable raster image: {path}") from exc
    if width <= 0 or height <= 0:
        raise ValueError(f"Raster dimensions must be positive: {path}")
    return int(width), int(height), image_format


def _raster_provenance(path: Path) -> dict:
    """Validate a model-native 16:9 raster without forcing a 1920x1080 rewrite."""
    width, height, image_format = _raster_dimensions(path)
    aspect_ratio = width / height
    relative_error = abs(aspect_ratio - TARGET_ASPECT_RATIO) / TARGET_ASPECT_RATIO
    if relative_error > ASPECT_RATIO_TOLERANCE:
        raise ValueError(
            f"Raster {path.name} is {width}x{height} ({aspect_ratio:.6f}); "
            f"expected 16:9 within {ASPECT_RATIO_TOLERANCE:.3%} relative error"
        )
    provenance = {
        "dimensions": {"width": width, "height": height},
        "format": image_format,
        "byte_length": path.stat().st_size,
        "sha256": _sha256_file(path),
        "aspect_ratio": round(aspect_ratio, 8),
        "target_aspect_ratio": round(TARGET_ASPECT_RATIO, 8),
        "aspect_ratio_relative_error": round(relative_error, 8),
        "aspect_ratio_tolerance": ASPECT_RATIO_TOLERANCE,
    }
    portable_source = _try_portable_workspace_path(path)
    if portable_source is not None:
        provenance["source_path"] = portable_source
    else:
        provenance["external_source"] = {
            "scope": "external-untracked",
            "basename": path.name,
            "sha256": provenance["sha256"],
        }
    return provenance


def _slide_mapping(provenance: dict) -> dict:
    dimensions = provenance["dimensions"]
    width = int(dimensions["width"])
    height = int(dimensions["height"])
    uniform_scale = min(CANVAS_WIDTH / width, CANVAS_HEIGHT / height)
    mapped_width = width * uniform_scale
    mapped_height = height * uniform_scale
    horizontal_letterbox = max(0.0, (CANVAS_WIDTH - mapped_width) / 2)
    vertical_letterbox = max(0.0, (CANVAS_HEIGHT - mapped_height) / 2)
    return {
        "method": "css-uniform-contain",
        "target_dimensions": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
        "uniform_scale": round(uniform_scale, 8),
        "mapped_dimensions": {
            "width": round(mapped_width, 4),
            "height": round(mapped_height, 4),
        },
        "letterbox_px": {
            "left": round(horizontal_letterbox, 4),
            "right": round(horizontal_letterbox, 4),
            "top": round(vertical_letterbox, 4),
            "bottom": round(vertical_letterbox, 4),
        },
        "crop": False,
        "non_uniform_stretch": False,
        "content_reconstruction": False,
        "adapted_copy_created": False,
    }


def _extract_palette_tokens(html: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for name in PALETTE_TOKEN_NAMES:
        matches = re.findall(rf"{re.escape(name)}\s*:\s*([^;}}]+)", html, re.IGNORECASE)
        if matches:
            tokens[name] = re.sub(r"\s*!important\s*$", "", matches[-1].strip(), flags=re.IGNORECASE)
    return tokens


def _palette_contrast_contract(record: dict, fallback_tokens: dict[str, str]) -> dict:
    tokens = dict(fallback_tokens)
    measured_tokens = record.get("palette_tokens")
    if isinstance(measured_tokens, dict):
        tokens.update({str(key): str(value) for key, value in measured_tokens.items() if value})
    foreground_colors = record.get("foreground_colors")
    if not isinstance(foreground_colors, list):
        foreground_colors = []
    return {
        "palette_tokens": tokens,
        "foreground_colors": sorted({str(value) for value in foreground_colors if value}),
        "background_base": tokens.get("--bg") or tokens.get("--surface") or "#f4f1ea",
        "minimum_contrast_ratios": {
            "normal_text": 4.5,
            "large_text": 3.0,
            "meaningful_design_object": 3.0,
        },
        "protected_halo_px": PROTECTION_HALO_PX,
        "policy": "Preserve or exceed the source Theme contrast throughout every protected region.",
    }


def _css_escape_identifier(value: object) -> str:
    """Return a CSS identifier escape suitable for an element id selector."""
    text = str(value or "")
    if not text:
        raise ValueError("A non-empty slide id is required for the final background selector")
    escaped: list[str] = []
    for index, char in enumerate(text):
        codepoint = ord(char)
        if codepoint == 0:
            escaped.append("\ufffd")
        elif (
            1 <= codepoint <= 31
            or codepoint == 127
            or (index == 0 and char.isdigit())
            or (index == 1 and text[0] == "-" and char.isdigit())
        ):
            escaped.append(f"\\{codepoint:x} ")
        elif index == 0 and char == "-" and len(text) == 1:
            escaped.append("\\-")
        elif codepoint >= 128 or char.isalnum() or char in {"-", "_"}:
            escaped.append(char)
        else:
            escaped.append(f"\\{char}")
    return "".join(escaped)


def _final_slide_background_selector(slide_id: object) -> str:
    """Target one top-level slide with enough specificity to beat neutral paint.

    The editor thumbnail renderer mirrors ``html > body > #stage > section.slide``
    and preserves the source slide id inside its isolated shadow tree, so this
    same selector also paints the corresponding thumbnail clone.
    """
    return f"html body #stage > section.slide#{_css_escape_identifier(slide_id)}"


def _mark_slide_background(
    html: str,
    slide_id: str | None,
    relative_src: str,
    *,
    embedded: bool = False,
) -> str:
    """Record the raster background contract on the matching slide element."""
    if not slide_id:
        return html
    pattern = re.compile(
        rf'<section\b(?=[^>]*\sclass="slide(?:\s[^\"]*)?")'
        rf'(?=[^>]*\sid="{re.escape(slide_id)}")(?P<attrs>[^>]*)>',
        re.IGNORECASE,
    )

    def replace(match: re.Match[str]) -> str:
        attrs = re.sub(
            r'\sdata-pptx-background-image(?:-(?:src|embedded))?="[^"]*"',
            "",
            match.group("attrs"),
            flags=re.IGNORECASE,
        )
        embedded_attr = ' data-pptx-background-image-embedded="true"' if embedded else ""
        return (
            f'<section{attrs}'
            f' data-pptx-background-image="true"'
            f' data-pptx-background-image-src="{relative_src}"'
            f'{embedded_attr}>'
        )

    return pattern.sub(replace, html, count=1)


def _safe_run_dir(input_path: Path, requested: Path | None) -> Path:
    run_dir = requested.resolve() if requested else EXPERIMENT_ROOT / input_path.stem
    experiment_root = EXPERIMENT_ROOT.resolve()
    if run_dir != experiment_root and experiment_root not in run_dir.parents:
        raise ValueError(f"run-dir must stay under {experiment_root}")
    return run_dir


def prepare(args: argparse.Namespace) -> None:
    source = Path(args.input).resolve()
    if not source.is_file() or source.suffix.lower() != ".html":
        raise ValueError("--input must be an existing .html file")

    run_dir = _safe_run_dir(source, Path(args.run_dir) if args.run_dir else None)
    run_dir.mkdir(parents=True, exist_ok=True)
    neutral_path = run_dir / "neutral.html"
    mask_html_path = run_dir / "mask.html"
    prompt_path = run_dir / "imagegen-prompt.txt"
    manifest_path = run_dir / "run.json"

    original = source.read_text(encoding="utf-8")
    neutral_path.write_text(_inject_before_head_close(original, NEUTRAL_STYLE), encoding="utf-8")
    mask_html_path.write_text(
        _inject_before_head_close(_inject_before_head_close(original, NEUTRAL_STYLE), MASK_SCRIPT),
        encoding="utf-8",
    )
    prompt_path.write_text(PROMPT, encoding="utf-8")

    source_html, external_source = _portable_or_external_source(source)
    manifest = {
        "mode": "html-image-background-experiment",
        "status": "prepared",
        "created_at": _utc_now(),
        "source_html": source_html,
        "source_html_provenance": external_source,
        "source_was_modified": False,
        "neutral_html": _portable_workspace_path(neutral_path),
        "mask_html": _portable_workspace_path(mask_html_path),
        "protected_region_mask": _portable_workspace_path(run_dir / "protected-mask.png"),
        "reference_screenshot": _portable_workspace_path(run_dir / "neutral-reference.png"),
        "imagegen_prompt": _portable_workspace_path(prompt_path),
        "background": None,
        "final_html": None,
        "production_integration": False,
    }
    _write_run_manifest(manifest_path, manifest)
    print(neutral_path)
    print(prompt_path)
    print(manifest_path)


def apply_background(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    experiment_root = EXPERIMENT_ROOT.resolve()
    if run_dir != experiment_root and experiment_root not in run_dir.parents:
        raise ValueError(f"run-dir must stay under {experiment_root}")

    manifest_path = run_dir / "run.json"
    neutral_path = run_dir / "neutral.html"
    source_background = Path(args.background).resolve()
    source_mask = Path(args.mask).resolve() if args.mask else run_dir / "protected-mask.png"
    if not manifest_path.is_file() or not neutral_path.is_file():
        raise ValueError("run-dir is not a prepared experiment run")
    if not source_background.is_file() or source_background.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("--background must be an existing PNG, JPG, or WebP image")
    if not source_mask.is_file() or source_mask.suffix.lower() != ".png":
        raise ValueError("A PNG protected-region mask is required; capture mask.html as protected-mask.png first")
    provenance = _raster_provenance(source_background)
    mapping = _slide_mapping(provenance)

    background_path = run_dir / ("background" + source_background.suffix.lower())
    if source_background != background_path:
        shutil.copy2(source_background, background_path)
    if _sha256_file(background_path) != provenance["sha256"]:
        raise ValueError("Copied background bytes do not match the preserved model output")
    mask_path = run_dir / "protected-mask.png"
    if source_mask != mask_path:
        shutil.copy2(source_mask, mask_path)
    embedded_data_url = _raster_data_url(background_path)
    neutral_html = _remove_neutral_paint_override(
        neutral_path.read_text(encoding="utf-8")
    )
    slide_specs = _extract_slide_specs(neutral_html)
    if not slide_specs:
        raise ValueError("The prepared HTML must contain top-level section.slide elements with ids")
    selector_list = ",\n  ".join(
        _final_slide_background_selector(spec["id"])
        for spec in slide_specs
    )

    background_style = f"""
<style id="html-image-background-experiment-final" data-css-owner="background-experiment">
  {selector_list} {{
    background-color: var(--bg, #f4f1ea);
    background-image: url("{embedded_data_url}");
    background-position: center;
    background-repeat: no-repeat;
    background-size: contain;
  }}
</style>
"""
    final_path = run_dir / "final.html"
    final_html = neutral_html
    relative_src = f"./{background_path.name}"
    for spec in slide_specs:
        final_html = _mark_slide_background(
            final_html,
            spec["id"],
            relative_src,
            embedded=True,
        )
    final_html = _inject_before_head_close(final_html, background_style)
    final_path.write_text(final_html, encoding="utf-8")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing_source = manifest.get("source_html")
    if existing_source:
        source_path = _resolve_manifest_path(
            existing_source,
            run_dir=run_dir,
            label="source_html",
        )
        source_html, external_source = _portable_or_external_source(source_path)
        manifest["source_html"] = source_html
        manifest["source_html_provenance"] = external_source
    manifest.update(
        {
            "status": "needs-review",
            "updated_at": _utc_now(),
            "background": _portable_workspace_path(background_path),
            "protected_region_mask": _portable_workspace_path(mask_path),
            "mask_usage": "generation-guidance-only",
            "post_generation_cutout": False,
            "model_output_provenance": provenance,
            "slide_mapping": mapping,
            "final_html": _portable_workspace_path(final_path),
            "source_was_modified": False,
            "production_integration": False,
            "qa": {
                "automatic_pass": False,
                "reason": "Experimental backgrounds require visual review for foreground contrast.",
            },
        }
    )
    _write_run_manifest(manifest_path, manifest)
    print(final_path)
    print(background_path)
    print(manifest_path)


def _validate_run_dir(run_dir: Path) -> Path:
    run_dir = run_dir.resolve()
    experiment_root = EXPERIMENT_ROOT.resolve()
    if run_dir != experiment_root and experiment_root not in run_dir.parents:
        raise ValueError(f"run-dir must stay under {experiment_root}")
    return run_dir


def _reference_screenshot(source: Path, index: int) -> Path | None:
    capture_dir = source.parent.parent / "qa" / "captures" / source.stem
    if not capture_dir.is_dir():
        return None
    candidates = sorted(
        path
        for suffix in ("jpg", "jpeg", "png", "webp")
        for path in capture_dir.glob(f"slide-{index + 1:03d}-*.{suffix}")
    )
    return candidates[0].resolve() if candidates else None


def _resolve_reference_screenshot(
    record: dict,
    source: Path,
    index: int,
    run_dir: Path,
) -> Path | None:
    explicit = record.get("source_reference") or record.get("reference_screenshot")
    if explicit:
        candidate = _resolve_manifest_path(
            explicit,
            run_dir=run_dir,
            label=f"slide {index + 1} reference screenshot",
            fallback_base=source.parent,
            prefer_run_dir=True,
        )
        if candidate.is_file():
            return candidate.resolve()
    return _reference_screenshot(source, index)


def _extract_slide_specs(html: str) -> list[dict]:
    pattern = re.compile(
        r'<section\b(?=[^>]*\sclass="slide(?:\s+[^"]*)?")'
        r'(?=[^>]*\sid="([^"]+)")(?P<attrs>[^>]*)>',
        re.IGNORECASE | re.DOTALL,
    )
    specs = []
    for position, match in enumerate(pattern.finditer(html)):
        attrs = match.group("attrs")
        index_match = re.search(r'data-index="(\d+)"', attrs, re.IGNORECASE)
        specs.append(
            {
                "index": int(index_match.group(1)) if index_match else position,
                "id": match.group(1),
            }
        )
    return sorted(specs, key=lambda item: item["index"])


def _html_attribute(tag: str, name: str) -> str | None:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
        tag,
        re.IGNORECASE | re.DOTALL,
    )
    return match.group(2).strip() if match else None


def _slide_markup_for_id(html: str, slide_id: str, *, slide_number: int) -> tuple[str, str]:
    start = re.search(
        rf'<section\b(?=[^>]*\bid=["\']{re.escape(slide_id)}["\'])[^>]*>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if start is None:
        raise ValueError(f"Slide {slide_number} id {slide_id!r} is missing from source HTML")
    end = re.search(r"</section\s*>", html[start.end() :], re.IGNORECASE)
    if end is None:
        raise ValueError(f"Slide {slide_number} id {slide_id!r} has no closing section tag")
    return start.group(0), html[start.end() : start.end() + end.start()]


def _semantic_photo_contract(
    source_markup: str,
    slide_id: str,
    *,
    slide_number: int,
) -> dict[str, Any]:
    """Validate the optional Raster/Photo contract without treating photos as backgrounds."""

    start_tag, body = _slide_markup_for_id(source_markup, slide_id, slide_number=slide_number)
    raw_variant = _html_attribute(start_tag, "data-image-variant")
    if raw_variant is None:
        return {"image_variant": None, "semantic_photos": []}
    image_variant = raw_variant.lower()
    if image_variant not in {"raster", "photo"}:
        raise ValueError(
            f"Slide {slide_number} data-image-variant must be 'raster' or 'photo'; "
            f"got {raw_variant!r}"
        )

    photo_tags = list(
        re.finditer(
            r'<img\b(?=[^>]*\bdata-semantic-image=["\']true["\'])[^>]*>',
            body,
            re.IGNORECASE | re.DOTALL,
        )
    )
    if image_variant == "raster":
        if photo_tags:
            raise ValueError(
                f"Slide {slide_number} is Raster but declares data-semantic-image; "
                "choose Photo for a page with an independent illustration"
            )
        return {"image_variant": "raster", "semantic_photos": []}

    page_claim = _html_attribute(start_tag, "data-photo-brief") or _html_attribute(
        start_tag, "data-page-claim"
    )
    if not page_claim:
        raise ValueError(
            f"Slide {slide_number} is Photo but is missing data-photo-brief or data-page-claim"
        )
    if not photo_tags:
        raise ValueError(
            f"Slide {slide_number} is Photo but has no independent "
            '<img data-semantic-image="true">'
        )

    semantic_photos = []
    for photo_tag in photo_tags:
        tag = photo_tag.group(0)
        src = _html_attribute(tag, "src")
        alt = _html_attribute(tag, "alt")
        if not src:
            raise ValueError(
                f"Slide {slide_number} semantic photo is missing its src; it cannot be a CSS background"
            )
        if not alt:
            raise ValueError(f"Slide {slide_number} semantic photo is missing its alt text")
        semantic_photos.append(
            {
                "alt": alt,
                "source_kind": "data-url" if src.startswith("data:") else "src",
            }
        )
    return {
        "image_variant": "photo",
        "photo_brief": page_claim,
        "semantic_photos": semantic_photos,
    }


def prepare_deck(args: argparse.Namespace) -> None:
    """Prepare an isolated run that can measure and apply backgrounds per slide."""
    source = Path(args.input).resolve()
    if not source.is_file() or source.suffix.lower() != ".html":
        raise ValueError("--input must be an existing .html file")

    run_dir = _safe_run_dir(source, Path(args.run_dir) if args.run_dir else None)
    run_dir.mkdir(parents=True, exist_ok=True)
    neutral_path = run_dir / "neutral.html"
    mask_html_path = run_dir / "mask.html"
    prompt_template_path = run_dir / "imagegen-prompt-template.txt"
    masks_json_path = run_dir / "masks.json"
    manifest_path = run_dir / "run.json"

    original = source.read_text(encoding="utf-8")
    slide_specs = _extract_slide_specs(original)
    if not slide_specs:
        raise ValueError("Input HTML has no top-level section.slide elements")
    neutral_html = _inject_before_head_close(original, NEUTRAL_STYLE)
    neutral_path.write_text(neutral_html, encoding="utf-8")
    mask_pages_dir = run_dir / "mask-pages"
    mask_pages_dir.mkdir(parents=True, exist_ok=True)
    mask_page_paths = []
    for spec in slide_specs:
        visibility_style = f"""
<style id="html-image-background-mask-visibility-{spec['index']}" data-css-owner="background-experiment">
  /* This page statically exposes exactly one slide for measurement. */
  html body #stage > section.slide {{ display: none; }}
  html body #stage > section.slide#{spec['id']} {{ display: block; }}
</style>
"""
        page_html = _inject_before_head_close(neutral_html, visibility_style)
        page_html = _inject_before_head_close(
            page_html,
            SINGLE_SLIDE_MASK_SCRIPT.replace("__TARGET_SLIDE_ID__", spec["id"]),
        )
        page_path = mask_pages_dir / f"mask-{spec['index'] + 1:03d}.html"
        page_path.write_text(page_html, encoding="utf-8")
        mask_page_paths.append(page_path)
    mask_html_path.write_text(mask_page_paths[0].read_text(encoding="utf-8"), encoding="utf-8")
    prompt_template_path.write_text(PER_SLIDE_PROMPT, encoding="utf-8")

    source_html, external_source = _portable_or_external_source(source)
    manifest = {
        "mode": "html-image-background-per-slide-experiment",
        "status": "prepared",
        "created_at": _utc_now(),
        "source_html": source_html,
        "source_html_provenance": external_source,
        "source_was_modified": False,
        "neutral_html": _portable_workspace_path(neutral_path),
        "mask_html": _portable_workspace_path(mask_html_path),
        "mask_pages_directory": _portable_workspace_path(mask_pages_dir),
        "mask_pages": [_portable_workspace_path(path) for path in mask_page_paths],
        "masks_json": _portable_workspace_path(masks_json_path),
        "imagegen_prompt_template": _portable_workspace_path(prompt_template_path),
        "slide_count": len(slide_specs),
        "slide_specs": slide_specs,
        "slide_records": [],
        "final_html": None,
        "production_integration": False,
    }
    _write_run_manifest(manifest_path, manifest)
    print(neutral_path)
    print(mask_pages_dir)
    print(prompt_template_path)
    print(manifest_path)


def _boxes_with_required_guard(boxes: list[dict], measured_guard: object) -> list[dict]:
    try:
        current_guard = max(0.0, float(measured_guard))
    except (TypeError, ValueError):
        current_guard = 0.0
    additional = max(0.0, PROTECTION_HALO_PX - current_guard)
    expanded = []
    for box in boxes if isinstance(boxes, list) else []:
        if not isinstance(box, dict):
            expanded.append(box)
            continue
        try:
            x = float(box["x"])
            y = float(box["y"])
            width = float(box["w"])
            height = float(box["h"])
        except (KeyError, TypeError, ValueError):
            expanded.append(box)
            continue
        left = max(0.0, x - additional)
        top = max(0.0, y - additional)
        right = min(float(CANVAS_WIDTH), x + width + additional)
        bottom = min(float(CANVAS_HEIGHT), y + height + additional)
        expanded.append({**box, "x": left, "y": top, "w": right - left, "h": bottom - top})
    return expanded


def _normalized_occupied_boxes(boxes: list[dict]) -> list[tuple[float, float, float, float]] | None:
    if not isinstance(boxes, list) or not boxes:
        return None
    normalized = []
    for box in boxes:
        if not isinstance(box, dict):
            return None
        try:
            x = float(box["x"])
            y = float(box["y"])
            width = float(box["w"])
            height = float(box["h"])
        except (KeyError, TypeError, ValueError):
            return None
        if not all(math.isfinite(value) for value in (x, y, width, height)):
            return None
        if width <= 0 or height <= 0:
            return None
        left = max(0.0, min(float(CANVAS_WIDTH), x))
        top = max(0.0, min(float(CANVAS_HEIGHT), y))
        right = max(0.0, min(float(CANVAS_WIDTH), x + width))
        bottom = max(0.0, min(float(CANVAS_HEIGHT), y + height))
        if right <= left or bottom <= top:
            return None
        normalized.append((left, top, right, bottom))
    return normalized


def _candidate_open_zones(
    boxes: list[dict],
    *,
    measurement_uncertain: bool = True,
) -> list[dict[str, int]]:
    """Return only verified connected empty rectangles; uncertainty fails closed."""
    if measurement_uncertain:
        return []
    normalized = _normalized_occupied_boxes(boxes)
    if not normalized:
        return []

    x_edges = sorted({0.0, float(CANVAS_WIDTH), *(value for box in normalized for value in (box[0], box[2]))})
    candidates: list[dict[str, int]] = []
    for left_index, left in enumerate(x_edges[:-1]):
        for right in x_edges[left_index + 1 :]:
            width = right - left
            if width < MIN_OPEN_ZONE_WIDTH:
                continue
            blocked = sorted(
                (top, bottom)
                for box_left, top, box_right, bottom in normalized
                if box_left < right and box_right > left
            )
            merged: list[list[float]] = []
            for top, bottom in blocked:
                if not merged or top > merged[-1][1]:
                    merged.append([top, bottom])
                else:
                    merged[-1][1] = max(merged[-1][1], bottom)
            cursor = 0.0
            for top, bottom in [*merged, [float(CANVAS_HEIGHT), float(CANVAS_HEIGHT)]]:
                if top - cursor >= MIN_OPEN_ZONE_HEIGHT:
                    candidates.append(
                        {
                            "x": round(left),
                            "y": round(cursor),
                            "w": round(width),
                            "h": round(top - cursor),
                        }
                    )
                cursor = max(cursor, bottom)

    unique = {tuple(row[key] for key in ("x", "y", "w", "h")): row for row in candidates}
    ranked = sorted(unique.values(), key=lambda row: row["w"] * row["h"], reverse=True)
    maximal: list[dict[str, int]] = []
    for row in ranked:
        right = row["x"] + row["w"]
        bottom = row["y"] + row["h"]
        if any(
            row["x"] >= kept["x"]
            and row["y"] >= kept["y"]
            and right <= kept["x"] + kept["w"]
            and bottom <= kept["y"] + kept["h"]
            for kept in maximal
        ):
            continue
        maximal.append(row)
    return maximal[:4]


def _layout_decoration(layout: str) -> dict:
    """Load the concrete 2B decoration contract from the canonical layout YAML."""
    if layout in LAYOUT_DECORATION_CACHE:
        return LAYOUT_DECORATION_CACHE[layout]
    decoration: dict = {}
    if re.fullmatch(r"[A-Za-z0-9_-]+", layout):
        for suffix in (".yaml", ".yml"):
            path = ROOT / "prompt_system" / "layouts" / f"{layout}{suffix}"
            if not path.is_file():
                continue
            try:
                document = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                document = None
            if isinstance(document, dict) and isinstance(document.get("decoration"), dict):
                decoration = document["decoration"]
            break
    LAYOUT_DECORATION_CACHE[layout] = decoration
    return decoration


def _default_2b_spec(profile: str, layout: str) -> dict:
    """Return an explicit visible 2B recipe when a layout has no decoration block."""
    visibility = {
        "light_background": "15-22% opacity minimum; use the theme accent or support-accent",
        "dark_background": "30-45% opacity minimum; use a clearly separated theme accent",
        "normal_viewing_size": "2B must be distinguishable from the 2A material at normal slide size",
    }
    if profile == "half-image":
        return {
            "required": True,
            "source": "profile-default",
            "named_zones": [
                "image-side outer edge and one image-side corner, outside the measured foreground halo",
                "image-text seam or the nearest unoccupied transition strip",
            ],
            "prescribe": {
                "visible_primitives": [
                    "one continuous 1-2px seam hairline or a narrow 2-4% seam band",
                    "one cropped angular or organic edge band/bracket on the image side, 6-14% of slide width",
                ],
                "placement": "Keep both primitives on the image side or seam; never cross into the text/readability region or the protected image subject.",
                "palette": "theme accent plus one support-accent; abstract, no text or recognizable object",
            },
            "free_zone": {
                "type": "image-side directional edge composition",
                "rule": "Let a broad low-frequency tonal mass follow the image side and terminate at the seam; the seam primitive must remain visibly separate from this 2A mass.",
            },
            "visibility": visibility,
            "acceptance": "If the result reads as one uniform texture with no seam or image-side edge primitive, regenerate.",
            "layout": layout,
        }
    if profile == "full-bleed":
        return {
            "required": True,
            "source": "profile-default",
            "named_zones": [
                "one outer vertical or horizontal edge outside the overlay/readability window",
                "one image-aware corner crop or edge transition, never a generic four-corner frame",
            ],
            "prescribe": {
                "visible_primitives": [
                    "one cropped 2-4% side band or 1-3px edge line",
                    "one large image-aware angled transition or partial arc, 10-24% of slide width, clipped by the slide edge",
                ],
                "placement": "Follow the visual direction of the full-bleed field and stay outside overlay/readability windows and the image focal subject.",
                "palette": "theme accent with image-derived tonal variation; abstract, no frame and no recognizable object",
            },
            "free_zone": {
                "type": "off-center full-bleed edge composition",
                "rule": "Use one broad off-center 2A field plus the specified cropped 2B edge treatment; never repeat four corners or create a paper border.",
            },
            "visibility": visibility,
            "acceptance": "If the result reads as only a photo-like field or gradient with no image-aware edge treatment, regenerate.",
            "layout": layout,
        }
    return {
        "required": True,
        "source": "profile-default",
        "named_zones": [
            "outer top-left and bottom-right corners, 2-6% inset, using only unoccupied portions",
            "the widest verified outer edge or corner free zone, moved away from any measured foreground halo",
        ],
        "prescribe": {
            "visible_primitives": [
                "two cropped L-shaped corner brackets, each 6-12% of slide width with 1-2px strokes",
                "one short hairline or 3-5 dot/dash cluster near an outer edge, clearly separate from 2A texture",
            ],
            "placement": "Use asymmetrical outer-edge placement; if a corner is occupied, move that primitive to the farthest visible outer edge. Never enter text, cards, charts, connectors, or semantic modules.",
            "palette": "theme accent or support-accent at visible opacity; abstract decoration, no text or recognizable object",
        },
        "free_zone": {
            "type": "asymmetric edge and corner free zone",
            "rule": "Use a broad low-frequency accent wash or wedge attached to one edge as 2A support, while keeping the two 2B primitives visibly readable on top of or beside it.",
        },
        "visibility": visibility,
        "acceptance": "If the result reads as only paper, texture, or gradient with no visible brackets/edge marks, regenerate.",
        "layout": layout,
    }


def _resolve_2b_spec(layout: str, profile: str) -> dict:
    """Combine canonical layout decoration with a mandatory visible profile recipe."""
    fallback = _default_2b_spec(profile, layout)
    decoration = _layout_decoration(layout)
    if not decoration:
        return fallback
    return {
        **fallback,
        "source": "layout.decoration+profile-required-visibility",
        "layout_decoration": {
            "design_zone": decoration.get("design_zone"),
            "prescribe": decoration.get("prescribe"),
            "free_zone": decoration.get("free_zone"),
        },
        "prescribe": {
            "layout_prescribe": decoration.get("prescribe"),
            "required_visible_primitives": fallback["prescribe"]["visible_primitives"],
            "placement": fallback["prescribe"]["placement"],
            "palette": fallback["prescribe"]["palette"],
        },
        "free_zone": {
            "layout_free_zone": decoration.get("free_zone"),
            "fallback_rule": fallback["free_zone"]["rule"],
        },
    }


def _layout_safe_zone_contract(record: dict) -> dict:
    """Resolve layout meaning and a concrete, visible 2A/2B contract."""
    layout = str(record.get("layout_id") or "unknown")
    profile = LAYOUT_SAFE_ZONE_PROFILES.get(layout, "content")

    if profile == "half-image":
        if layout == "cover-photo-frame":
            image_region = "left image region x=0-40%, y=0-100%"
            text_region = "right text/readability region x=48-96%, y=18-90%"
            seam_region = "image-text seam x=40-42%; decorative left edge touches the photo boundary; preserve a 6% clear gutter before the text region at 48%"
        elif layout == "cover-photo-frame-reverse":
            image_region = "right image region x=60-100%, y=0-100%"
            text_region = "left text/readability region x=8-56%, y=18-90%"
            seam_region = "image-text seam x=56-60%"
        elif layout == "chapter-text-left-photo-brand":
            image_region = "right photo region x=45-100%, y=0-100%"
            text_region = "left content/readability region x=10-46%, y=20-78%"
            seam_region = "photo boundary and brand overlay x=45-85%"
        else:
            image_region = "left framed-photo region x=4-52%, y=3-97%"
            text_region = "right title/body readability region x=55-95%, y=20-84%"
            seam_region = "framed-photo to text gap x=52-55%"
        contract = {
            "profile": profile,
            "background_mode": "half-image-directional-material",
            "profile_instruction": "Create a visibly directional half-slide composition: the image side is materially richer and more active, the text side is quieter and lower-frequency, and the seam is a controlled transition rather than a hard rectangle. If no image description is supplied, use abstract material only and do not invent a recognizable subject.",
            "2b_direction": "2B is required: use a visible image-side edge primitive and a controlled seam accent; never place generic corner ornaments over the text side or image focal area.",
            "semantic_safe_regions": [text_region, "the image focal subject and crop must remain visually coherent"],
            "free_design_regions": [image_region, seam_region],
            "forbidden_regions": ["measured protected foreground", "text/readability region", "image focal subject", "fake text, UI, chart, or second image"],
            "rationale": f"layout={layout} declares a half-image composition; design the image side and seam separately from the text side",
        }
    elif profile == "full-bleed":
        if layout == "cover-photo-overlay-block":
            overlay_region = "left overlay/readability window x=5-51%, y=13-70%"
            structure_region = "right photo field x=17-100%, y=0-100%, with accent bar x=97-100%"
        elif layout == "chapter-fullbleed-overlay-title":
            overlay_region = "top-left title overlay/readability window x=5-37%, y=8-32%"
            structure_region = "full-slide photo field with right number panel x=82-100%"
        else:
            overlay_region = "left-center closing overlay and contact readability window x=8-62%, y=24-78%"
            structure_region = "full-slide photo field; keep the right side visually open"
        contract = {
            "profile": profile,
            "background_mode": "full-bleed-composition",
            "profile_instruction": "Create one continuous full-bleed composition with a broad off-center tonal flow or focal field. Keep the declared text-overlay window visibly quieter and contrast-safe, while the remaining field carries the visual movement. Do not turn the slide into a paper frame or a four-corner pattern.",
            "2b_direction": "2B is required: use visible edge treatment that follows the full-bleed composition and stays outside the overlay/readability windows; replace generic corners with image-aware cropping, not with texture-only material.",
            "semantic_safe_regions": [overlay_region, "all overlay text, contact, and panel regions must remain contrast-safe"],
            "free_design_regions": [structure_region, "remaining photo field outside the readability windows"],
            "forbidden_regions": ["measured protected foreground", "overlay/readability windows", "image focal subject behind text", "unrelated paper frame or generic four-corner ornament"],
            "rationale": f"layout={layout} declares a full-bleed image composition; reserve the overlay window and compose the remaining field around it",
        }
    else:
        contract = {
            "profile": "content",
            "background_mode": "content-material",
            "profile_instruction": "Create a content-page field with a calm readable center/content area and visibly richer but low-frequency peripheral material. Add the required asymmetrical 2B edge/corner treatment without creating a fake panel or object.",
            "2b_direction": "2B is required: use declared content-page edge/corner zones when present, otherwise use the profile-default outer-edge recipe; it must not enter text, card, chart, or connector regions.",
            "semantic_safe_regions": ["content body and transition region need a quiet, readable, low-frequency field"],
            "free_design_regions": ["verified connected open zones", "declared or profile-default edge and corner design zones"],
            "forbidden_regions": ["measured protected foreground", "text, cards, charts, connectors, and semantic modules"],
            "rationale": f"layout={layout} is a content-led composition; use the content SAFE ZONE as a designed readable field",
        }
    contract["2b_required"] = True
    contract["2b_spec"] = _resolve_2b_spec(layout, profile)
    contract["decoration_source"] = contract["2b_spec"]["source"]
    return contract


def materialize_deck(args: argparse.Namespace) -> None:
    """Turn browser-measured per-slide boxes into masks and per-slide prompts."""
    run_dir = _validate_run_dir(Path(args.run_dir))
    manifest_path = run_dir / "run.json"
    if not manifest_path.is_file():
        raise ValueError("A prepared run and browser-exported masks.json are required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.masks_json:
        masks_json_path = Path(args.masks_json).resolve()
    elif manifest.get("masks_json"):
        masks_json_path = _resolve_manifest_path(
            manifest["masks_json"],
            run_dir=run_dir,
            label="masks_json",
        )
    else:
        masks_json_path = run_dir / "masks.json"
    if not masks_json_path.is_file():
        raise ValueError("A prepared run and browser-exported masks.json are required")
    masks_json_path = _ensure_repo_resident_copy(
        masks_json_path,
        run_dir / "masks.json",
        label="masks.json",
    )
    payload = json.loads(masks_json_path.read_text(encoding="utf-8"))
    records = payload.get("records", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list) or not records:
        raise ValueError("masks.json must contain a non-empty array of per-slide records")
    records = sorted(records, key=lambda item: int(item.get("index", 0)))

    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:  # pragma: no cover - environment-specific fallback
        raise RuntimeError("Pillow is required to materialize protected-region masks") from exc

    prompt_dir = run_dir / "prompts"
    mask_dir = run_dir / "masks"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)
    source_value = manifest.get("source_html")
    if source_value:
        source = _resolve_manifest_path(
            source_value,
            run_dir=run_dir,
            label="source_html",
        )
    else:
        source = run_dir / "neutral.html"
    if not source.is_file():
        raise ValueError("Prepared source HTML is missing")
    source_html, external_source = _portable_or_external_source(source)
    manifest["source_html"] = source_html
    manifest["source_html_provenance"] = external_source
    source_markup = source.read_text(encoding="utf-8")
    fallback_palette = _extract_palette_tokens(source_markup)
    slide_records = []

    for position, record in enumerate(records):
        index = int(record.get("index", position))
        number = index + 1
        slide_id = str(record.get("id") or "")
        recorded_variant = record.get("image_variant")
        if slide_id and (
            "data-image-variant" in source_markup.lower()
            or recorded_variant not in (None, "")
        ):
            image_contract = _semantic_photo_contract(
                source_markup,
                slide_id,
                slide_number=number,
            )
        else:
            image_contract = {"image_variant": None, "semantic_photos": []}
        if recorded_variant not in (None, "") and recorded_variant != image_contract["image_variant"]:
            raise ValueError(
                f"Slide {number} image-variant handoff does not match source HTML: "
                f"{recorded_variant!r} != {image_contract['image_variant']!r}"
            )
        raw_boxes = record.get("occupied_boxes", []) or []
        boxes = _boxes_with_required_guard(raw_boxes, record.get("measurement_guard_px"))
        measurement_uncertain = bool(record.get("measurement_uncertain", True))
        normalized_boxes = _normalized_occupied_boxes(boxes)
        if not normalized_boxes:
            measurement_uncertain = True
            boxes = [{"x": 0, "y": 0, "w": CANVAS_WIDTH, "h": CANVAS_HEIGHT}]
            normalized_boxes = [(0.0, 0.0, float(CANVAS_WIDTH), float(CANVAS_HEIGHT))]
        mask_path = mask_dir / f"protected-mask-{number:03d}.png"
        image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
        draw = ImageDraw.Draw(image)
        for left, top, box_right, box_bottom in normalized_boxes:
            x = max(0, min(CANVAS_WIDTH - 1, round(left)))
            y = max(0, min(CANVAS_HEIGHT - 1, round(top)))
            right = max(x, min(CANVAS_WIDTH - 1, round(box_right)))
            bottom = max(y, min(CANVAS_HEIGHT - 1, round(box_bottom)))
            draw.rectangle((x, y, right, bottom), fill="black")
        image.save(mask_path)

        reference = _resolve_reference_screenshot(record, source, index, run_dir)
        if reference is not None:
            reference = _ensure_repo_resident_copy(
                reference,
                run_dir / "references" / f"slide-{number:03d}-clean-foreground{reference.suffix.lower()}",
                label=f"slide {number} reference",
            )
        reference_provenance = _raster_provenance(reference) if reference else None
        if reference is None:
            measurement_uncertain = True
        palette_contract = _palette_contrast_contract(record, fallback_palette)
        open_zones = _candidate_open_zones(
            boxes,
            measurement_uncertain=measurement_uncertain,
        )
        generation_mode = (
            "ambient-material-with-verified-open-zone-and-required-2b"
            if open_zones
            else "profile-2b-plus-low-frequency-material"
        )
        safe_zone_contract = _layout_safe_zone_contract(record)
        box_text = ", ".join(
            f"x={round(float(box.get('x', 0)))}, y={round(float(box.get('y', 0)))}, "
            f"w={round(float(box.get('w', 0)))}, h={round(float(box.get('h', 0)))}"
            for box in boxes
        )
        open_zone_text = (
            "; ".join(
                f"x={zone['x']}, y={zone['y']}, w={zone['w']}, h={zone['h']}"
                for zone in open_zones
            )
            if open_zones
            else "none; use the profile 2B edge/corner/seam zones only and keep all other variation low-frequency"
        )
        imagegen_inputs = [
            {
                "order": 1,
                "role": "actual-clean-foreground-screenshot",
                "priority": "highest",
                "path": _portable_workspace_path(reference) if reference else None,
            },
            {
                "order": 2,
                "role": "occupancy-mask-guidance-only",
                "priority": "secondary",
                "path": _portable_workspace_path(mask_path),
            },
        ]
        prompt = (
            PER_SLIDE_PROMPT
            + f"\nSlide metadata: slide {number}; scene role={record.get('scene_role') or 'unknown'}; "
              f"layout={record.get('layout_id') or 'unknown'}; scene id={record.get('scene_id') or 'unknown'}"
            + f"\nImage 1 source (highest priority): {_portable_workspace_path(reference) if reference else 'MISSING - do not generate until supplied'}"
            + f"\nImage 2 source (mask guidance only): {_portable_workspace_path(mask_path)}"
            + f"\nOccupied foreground zones in {CANVAS_WIDTH}x{CANVAS_HEIGHT} coordinates, already including a {PROTECTION_HALO_PX}px halo: {box_text}"
            + f"\nVerified connected open zones (minimum {MIN_OPEN_ZONE_WIDTH}x{MIN_OPEN_ZONE_HEIGHT}px): {open_zone_text}"
            + f"\nGeneration mode: {generation_mode}"
            + "\nLayout-aware SAFE ZONE contract: "
            + json.dumps(safe_zone_contract, ensure_ascii=False, sort_keys=True)
            + f"\nProfile behavior: {safe_zone_contract['profile_instruction']}"
            + f"\nProfile-specific 2B behavior: {safe_zone_contract['2b_direction']}"
            + "\n2A rule: use the source Theme palette, material, tonal range, and mood as one low-frequency base field; do not add text or recognizable foreground content."
            + "\n2B required decoration spec: "
            + json.dumps(safe_zone_contract["2b_spec"], ensure_ascii=False, sort_keys=True)
            + "\n2B implementation rule: visibly render every required_visible_primitives item in its named zone, using the specified scale and opacity. Keep it outside the protected foreground, but do not make it so faint that it disappears."
            + "\n2B acceptance rule: at normal slide viewing size, the edge/corner/seam treatment must be visibly distinguishable from 2A. If the output reads as texture-only, gradient-only, or broad-color-field-only, regenerate it."
            + "\nPalette and foreground contrast contract: "
            + json.dumps(palette_contract, ensure_ascii=False, sort_keys=True)
        )
        if image_contract["image_variant"] == "photo":
            prompt += (
                "\nPhoto-page contract: the independent semantic photo/illustration is already "
                "attached as protected foreground. Its page brief is "
                + json.dumps(image_contract["photo_brief"], ensure_ascii=False)
                + ". Generate only the abstract Raster beneath it; do not reproduce, merge, "
                "or substitute the semantic subject."
            )
        prompt_path = prompt_dir / f"slide-{number:03d}-imagegen-prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        slide_records.append(
            {
                **record,
                "scene_role": record.get("scene_role") or "unknown",
                "occupied_boxes": boxes,
                "measurement_guard_px": PROTECTION_HALO_PX,
                "measurement_uncertain": measurement_uncertain,
                "mask": _portable_workspace_path(mask_path),
                "prompt": _portable_workspace_path(prompt_path),
                "source_reference": _portable_workspace_path(reference) if reference else None,
                "reference_screenshot": _portable_workspace_path(reference) if reference else None,
                "source_reference_provenance": reference_provenance,
                "imagegen_inputs": imagegen_inputs,
                "palette_contrast_contract": palette_contract,
                "minimum_open_zone": {
                    "width": MIN_OPEN_ZONE_WIDTH,
                    "height": MIN_OPEN_ZONE_HEIGHT,
                },
                "generation_mode": generation_mode,
                "image_variant": image_contract["image_variant"],
                "semantic_photo_contract": {
                    key: value for key, value in image_contract.items() if key != "image_variant"
                },
                "safe_zone_profile": safe_zone_contract["profile"],
                "two_a_two_b_required": True,
                "safe_zone_contract": safe_zone_contract,
                "generation_ready": reference is not None,
                "generation_blockers": [] if reference else ["missing-actual-clean-foreground-screenshot"],
                "background": None,
                "open_zone_candidates": open_zones,
                "post_generation_cutout": False,
            }
        )

    manifest.update(
        {
            "status": "masks-materialized",
            "updated_at": _utc_now(),
            "masks_json": _portable_workspace_path(masks_json_path),
            "slide_count": len(slide_records),
            "slide_records": slide_records,
            "source_was_modified": False,
            "generation_contract": {
                "asset_type": "model-native-16:9-raster",
                "protected_halo_px": PROTECTION_HALO_PX,
                "minimum_open_zone": {
                    "width": MIN_OPEN_ZONE_WIDTH,
                    "height": MIN_OPEN_ZONE_HEIGHT,
                },
                "input_order": [
                    "actual-clean-foreground-screenshot",
                    "occupancy-mask-guidance-only",
                ],
                "post_generation_cutout": False,
                "safe_zone_profiles": sorted(set(item["safe_zone_profile"] for item in slide_records)),
                "two_a_two_b_required": True,
                "two_a_definition": "low-frequency material, palette, tonal range, texture, lighting, and mood",
                "two_b_definition": "visible profile-specific edge, corner, seam, or image-aware primitive in a named or profile-default zone",
                "two_b_visibility_gate": {
                    "light_background_minimum_opacity": "15-20%",
                    "dark_background_minimum_opacity": "30%+",
                    "texture_only_fails": True,
                },
            },
            "post_generation_cutout": False,
        }
    )
    _write_run_manifest(manifest_path, manifest)
    print(mask_dir)
    print(prompt_dir)
    print(manifest_path)


def apply_deck(args: argparse.Namespace) -> None:
    """Attach one generated background to each matching slide in the isolated copy."""
    run_dir = _validate_run_dir(Path(args.run_dir))
    manifest_path = run_dir / "run.json"
    neutral_path = run_dir / "neutral.html"
    background_dir = Path(args.background_dir).resolve()
    if not manifest_path.is_file() or not neutral_path.is_file():
        raise ValueError("run-dir is not a prepared per-slide experiment run")
    if not background_dir.is_dir():
        raise ValueError("--background-dir must be an existing directory")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("slide_records") or []
    if not records:
        raise ValueError("Materialize masks before applying per-slide backgrounds")

    neutral_html = _remove_neutral_paint_override(
        neutral_path.read_text(encoding="utf-8")
    )
    source_slide_ids = {spec["id"] for spec in _extract_slide_specs(neutral_html)}
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    preflight = []
    for position, record in enumerate(records):
        index = int(record.get("index", position))
        number = index + 1
        slide_id = str(record.get("id") or "")
        if not slide_id:
            raise ValueError(f"Slide {number} is missing the id required for exact background mapping")
        if slide_id not in source_slide_ids:
            raise ValueError(f"Slide {number} id {slide_id!r} is not a top-level slide in neutral.html")
        source_image_contract = _semantic_photo_contract(
            neutral_html,
            slide_id,
            slide_number=number,
        )
        if record.get("image_variant") != source_image_contract["image_variant"]:
            raise ValueError(
                f"Slide {number} image-variant contract changed after mask materialization"
            )
        if record.get("generation_ready") is not True:
            raise ValueError(
                f"Slide {number} is not generation-ready; an actual clean foreground screenshot is required"
            )
        source_reference = record.get("source_reference") or record.get("reference_screenshot")
        mask = record.get("mask")
        palette_contract = record.get("palette_contrast_contract")
        input_roles = [row.get("role") for row in record.get("imagegen_inputs", []) if isinstance(row, dict)]
        if not source_reference:
            raise ValueError(f"Slide {number} is missing its source foreground reference")
        source_reference_path = _resolve_manifest_path(
            source_reference,
            run_dir=run_dir,
            label=f"slide {number} source reference",
        )
        if not source_reference_path.is_file():
            raise ValueError(f"Slide {number} is missing its source foreground reference")
        source_reference_path = _ensure_repo_resident_copy(
            source_reference_path,
            run_dir / "references" / f"slide-{number:03d}-clean-foreground{source_reference_path.suffix.lower()}",
            label=f"slide {number} source reference",
        )
        if not mask:
            raise ValueError(f"Slide {number} is missing its occupancy mask")
        mask_path = _resolve_manifest_path(
            mask,
            run_dir=run_dir,
            label=f"slide {number} occupancy mask",
        )
        if not mask_path.is_file():
            raise ValueError(f"Slide {number} is missing its occupancy mask")
        mask_path = _ensure_repo_resident_copy(
            mask_path,
            run_dir / "masks" / f"protected-mask-{number:03d}{mask_path.suffix.lower()}",
            label=f"slide {number} occupancy mask",
        )
        if "scene_role" not in record:
            raise ValueError(f"Slide {number} is missing scene_role provenance")
        if not isinstance(palette_contract, dict) or not palette_contract:
            raise ValueError(f"Slide {number} is missing its palette/contrast contract")
        if input_roles[:2] != [
            "actual-clean-foreground-screenshot",
            "occupancy-mask-guidance-only",
        ]:
            raise ValueError(f"Slide {number} must record foreground reference before mask guidance")
        if record.get("post_generation_cutout") is not False:
            raise ValueError(f"Slide {number} must declare post_generation_cutout=false")
        prompt_value = record.get("prompt")
        prompt_path: Path | None = None
        if prompt_value:
            prompt_path = _resolve_manifest_path(
                prompt_value,
                run_dir=run_dir,
                label=f"slide {number} prompt",
            )
            if not prompt_path.is_file():
                raise ValueError(f"Slide {number} prompt is missing")
            prompt_path = _ensure_repo_resident_copy(
                prompt_path,
                run_dir / "prompts" / f"slide-{number:03d}-imagegen-prompt.txt",
                label=f"slide {number} prompt",
            )
        portable_reference = _portable_workspace_path(source_reference_path)
        portable_mask = _portable_workspace_path(mask_path)
        portable_inputs = []
        for input_record in record.get("imagegen_inputs", []):
            if not isinstance(input_record, dict):
                continue
            role = input_record.get("role")
            portable_inputs.append(
                {
                    **input_record,
                    "path": (
                        portable_reference
                        if role == "actual-clean-foreground-screenshot"
                        else portable_mask
                        if role == "occupancy-mask-guidance-only"
                        else input_record.get("path")
                    ),
                }
            )
        record_for_write = {
            **record,
            "source_reference": portable_reference,
            "reference_screenshot": portable_reference,
            "source_reference_provenance": _raster_provenance(source_reference_path),
            "mask": portable_mask,
            "prompt": _portable_workspace_path(prompt_path) if prompt_path else None,
            "imagegen_inputs": portable_inputs,
        }
        candidates = sorted(
            item for item in background_dir.glob(f"slide-{number:03d}.*")
            if item.is_file() and item.suffix.lower() in allowed_suffixes
        )
        if len(candidates) != 1:
            raise ValueError(
                f"Expected exactly one slide-{number:03d}.* background in {background_dir}; "
                f"found {len(candidates)}"
            )
        source_background = candidates[0].resolve()
        provenance = _raster_provenance(source_background)
        preflight.append(
            (
                record_for_write,
                index,
                number,
                source_background,
                provenance,
                _slide_mapping(provenance),
                _final_slide_background_selector(slide_id),
            )
        )

    backgrounds_dir = run_dir / "backgrounds"
    backgrounds_dir.mkdir(parents=True, exist_ok=True)
    css_rules = []
    applied_records = []
    for record, index, number, source_background, provenance, mapping, selector in preflight:
        destination = backgrounds_dir / f"slide-{number:03d}{source_background.suffix.lower()}"
        if source_background != destination.resolve():
            shutil.copy2(source_background, destination)
        destination_hash = _sha256_file(destination)
        if destination_hash != provenance["sha256"]:
            raise ValueError(f"Slide {number} adjacent copy does not match the preserved model output")
        embedded_data_url = _raster_data_url(destination)
        css_rules.append(
            f"  {selector} {{\n"
            f"    background-color: var(--bg, #f4f1ea);\n"
            f"    /* Inline the raster so file:// HTML and the browser PPTX exporter can read it. */\n"
            f"    background-image: url(\"{embedded_data_url}\");\n"
            f"    background-position: center;\n"
            f"    background-repeat: no-repeat;\n"
            f"    background-size: contain;\n"
            f"  }}"
        )
        portable_model_source, external_model_source = _portable_or_external_source(source_background)
        preserved_model_output = {
            "source": portable_model_source,
            "adjacent_byte_preserving_copy": _portable_workspace_path(destination),
            "sha256": destination_hash,
        }
        if external_model_source is not None:
            preserved_model_output["external_source"] = external_model_source
        applied_records.append(
            {
                **record,
                "background": _portable_workspace_path(destination),
                "model_output_provenance": provenance,
                "preserved_model_output": preserved_model_output,
                "slide_mapping": mapping,
                "post_generation_cutout": False,
            }
        )

    background_style = (
        '<style id="html-image-background-per-slide-experiment-final" data-css-owner="background-experiment">\n'
        "  /* Each selector maps one generated asset to one detected slide. */\n"
        + "\n".join(css_rules)
        + "\n</style>"
    )
    final_path = run_dir / "final.html"
    final_html = neutral_html
    for record in applied_records:
        final_html = _mark_slide_background(
            final_html,
            record.get("id"),
            f"./backgrounds/slide-{int(record.get('index', 0)) + 1:03d}{Path(record['background']).suffix.lower()}",
            embedded=True,
        )
    final_html = _inject_before_head_close(final_html, background_style)
    final_path.write_text(final_html, encoding="utf-8")

    manifest.update(
        {
            "mode": "html-image-background-per-slide-experiment",
            "status": "needs-review",
            "updated_at": _utc_now(),
            "background_mode": "per-slide",
            "html_asset_policy": "inline-model-bytes-with-adjacent-byte-preserving-source-copy",
            "dimension_contract": {
                "target_slide": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
                "target_aspect_ratio": round(TARGET_ASPECT_RATIO, 8),
                "aspect_ratio_tolerance": ASPECT_RATIO_TOLERANCE,
                "mapping": "css-uniform-contain",
                "crop": False,
                "non_uniform_stretch": False,
                "content_reconstruction": False,
            },
            "backgrounds_directory": _portable_workspace_path(backgrounds_dir),
            "slide_records": applied_records,
            "final_html": _portable_workspace_path(final_path),
            "source_was_modified": False,
            "production_integration": False,
            "mask_usage": "generation-guidance-only",
            "post_generation_cutout": False,
            "qa": {
                "automatic_pass": False,
                "reason": "Per-slide generated backgrounds require visual review for foreground contrast and semantic fit.",
            },
        }
    )
    existing_source = manifest.get("source_html")
    if existing_source:
        source_path = _resolve_manifest_path(
            existing_source,
            run_dir=run_dir,
            label="source_html",
        )
        source_html, external_source = _portable_or_external_source(source_path)
        manifest["source_html"] = source_html
        manifest["source_html_provenance"] = external_source
    _write_run_manifest(manifest_path, manifest)
    print(final_path)
    print(backgrounds_dir)
    print(manifest_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Isolated HTML + image background experiment")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="Create a neutral HTML copy and imagegen prompt")
    prepare_parser.add_argument("--input", required=True, help="Source HTML; it will not be modified")
    prepare_parser.add_argument("--run-dir", help="Optional directory under artifacts/experiments/html-image-background")
    prepare_parser.set_defaults(func=prepare)

    apply_parser = subparsers.add_parser("apply", help="Attach a generated background to the isolated HTML copy")
    apply_parser.add_argument("--run-dir", required=True, help="Prepared experiment run directory")
    apply_parser.add_argument("--background", required=True, help="Generated background image")
    apply_parser.add_argument("--mask", help="Protected-region PNG mask; defaults to <run-dir>/protected-mask.png")
    apply_parser.set_defaults(func=apply_background)

    prepare_deck_parser = subparsers.add_parser(
        "prepare-deck", help="Create an isolated per-slide mask-measurement run"
    )
    prepare_deck_parser.add_argument("--input", required=True, help="Source HTML; it will not be modified")
    prepare_deck_parser.add_argument("--run-dir", help="Optional directory under artifacts/experiments/html-image-background")
    prepare_deck_parser.set_defaults(func=prepare_deck)

    materialize_parser = subparsers.add_parser(
        "materialize-deck", help="Create one protected mask and prompt per slide from masks.json"
    )
    materialize_parser.add_argument("--run-dir", required=True, help="Prepared per-slide experiment run directory")
    materialize_parser.add_argument("--masks-json", help="Browser-exported per-slide masks JSON")
    materialize_parser.set_defaults(func=materialize_deck)

    apply_deck_parser = subparsers.add_parser(
        "apply-deck", help="Attach one generated background to each slide"
    )
    apply_deck_parser.add_argument("--run-dir", required=True, help="Prepared per-slide experiment run directory")
    apply_deck_parser.add_argument("--background-dir", required=True, help="Directory containing slide-001.* backgrounds")
    apply_deck_parser.set_defaults(func=apply_deck)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
