(function attachHtmlVisualQaProbe(root) {
  "use strict";

  function runHtmlVisualQa() {
    const parseColor = (value) => {
      const input = String(value || "");
      const parts = input.match(/[\d.]+/g)?.map(Number) || [];
      if (input.startsWith("color(srgb") && parts.length >= 3) {
        return [parts[0] * 255, parts[1] * 255, parts[2] * 255, parts[3] ?? 1];
      }
      return parts.length >= 3 ? [parts[0], parts[1], parts[2], parts[3] ?? 1] : null;
    };
    const composite = (foreground, background) => {
      const alpha = foreground[3] ?? 1;
      return [
        foreground[0] * alpha + background[0] * (1 - alpha),
        foreground[1] * alpha + background[1] * (1 - alpha),
        foreground[2] * alpha + background[2] * (1 - alpha),
        1,
      ];
    };
    const luminance = (color) => {
      const values = color.slice(0, 3).map((value) => {
        const channel = value / 255;
        return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
      });
      return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
    };
    const contrast = (first, second) => {
      const values = [luminance(first), luminance(second)].sort((a, b) => b - a);
      return (values[0] + 0.05) / (values[1] + 0.05);
    };
    const round = (value, places = 1) => {
      const factor = 10 ** places;
      return Math.round(value * factor) / factor;
    };
    const toNumber = (value) => {
      const match = String(value || "").match(/-?[\d.]+/);
      return match ? +match[0] : NaN;
    };
    const isNumericStyle = (value) => /^-?[\d.]+(?:px|%)?$/.test(String(value || "").trim());
    const slide = document.querySelector(".slide.active");
    if (!slide) return { layout: null, issues: [{ slot: "active-slide", present: false }] };

    const issues = [];
    const slideRect = slide.getBoundingClientRect();
    const geometryScale = Math.max(slide.offsetWidth ? slideRect.width / slide.offsetWidth : 1, 0.0001);
    const rectOf = (node) => {
      const rect = node.getBoundingClientRect();
      return {
        left: rect.left,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height,
        centerX: (rect.left + rect.right) / 2,
        centerY: (rect.top + rect.bottom) / 2,
      };
    };
    const isVisible = (node) => {
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return rect.width > 0.5 && rect.height > 0.5
        && style.display !== "none" && style.visibility !== "hidden" && +style.opacity !== 0;
    };
    const unionOf = (rects) => rects.length ? {
      left: Math.min(...rects.map((rect) => rect.left)),
      top: Math.min(...rects.map((rect) => rect.top)),
      right: Math.max(...rects.map((rect) => rect.right)),
      bottom: Math.max(...rects.map((rect) => rect.bottom)),
    } : null;
    const embeddedEditor = document.querySelector('script[data-edit-mode-embedded="true"]');
    const externalEditor = document.querySelector('script[src="edit-mode.js"]');
    const frameworkReady = Boolean(
      document.getElementById("canvasBox")
      && document.getElementById("barInner")
      && document.getElementById("hint")
      && embeddedEditor
      && !externalEditor
      && document.querySelectorAll(".slide[id]").length === document.querySelectorAll(".slide").length
    );
    if (!frameworkReady) {
      issues.push({
        slot: "edit-framework",
        frameworkReady,
        embeddedEditor: Boolean(embeddedEditor),
        externalEditor: Boolean(externalEditor),
      });
    }

    for (const el of slide.querySelectorAll('[data-edit-kind="text"]')) {
      if (el.dataset.editFit !== "text") {
        issues.push({ slot: "text-fit-contract", element: el.className });
      }
    }

    const textSelectors = '[data-edit-layer="text"],[data-edit-kind="text"]';
    for (const el of [...slide.querySelectorAll(textSelectors)].filter((node) => !node.querySelector(textSelectors))) {
      if (el.dataset.orphanIntentional === "true") continue;
      const summary = root.getTextLineSummary?.(el);
      if (summary?.orphan) {
        issues.push({
          slot: "text-orphan-tail",
          element: el.className || el.tagName,
          fontSize: round(parseFloat(getComputedStyle(el).fontSize) || 0, 2),
          tailText: summary.tailText,
          lineTexts: summary.lineTexts,
          hardBreaks: el.querySelectorAll("br").length,
        });
      }
    }

    for (const area of slide.querySelectorAll("[data-auto-layout]")) {
      const materialized = area.dataset.layoutMaterialized === "true" && area.classList.contains("layout-materialized");
      const childrenAbsolute = [...area.querySelectorAll(":scope > .el,:scope > [data-layout-item]")].every((el) => {
        const style = getComputedStyle(el);
        return style.position === "absolute"
          && isNumericStyle(el.style.left)
          && isNumericStyle(el.style.top)
          && isNumericStyle(el.style.width)
          && isNumericStyle(el.style.height);
      });
      if (!materialized || !childrenAbsolute) {
        issues.push({ slot: "layout-materialization", materialized, childrenAbsolute });
      }
    }

    const containmentTolerance = 8 * geometryScale;
    for (const el of slide.querySelectorAll(".el")) {
      const rect = el.getBoundingClientRect();
      const visible = rect.width > 0.5 && rect.height > 0.5;
      if (!visible) {
        issues.push({ slot: "element-geometry", element: el.className, width: round(rect.width), height: round(rect.height) });
        continue;
      }
      const out = {
        left: rect.left < slideRect.left - containmentTolerance,
        top: rect.top < slideRect.top - containmentTolerance,
        right: rect.right > slideRect.right + containmentTolerance,
        bottom: rect.bottom > slideRect.bottom + containmentTolerance,
      };
      if (Object.values(out).some(Boolean) && el.dataset.allowBleed !== "true") {
        issues.push({ slot: "slide-containment", element: el.className, ...out });
      }
    }

    for (const el of slide.querySelectorAll('[data-edit-fit="text"]')) {
      const text = (el.innerText || "").trim();
      if (!text) continue;
      const range = document.createRange();
      range.selectNodeContents(el);
      const textRect = range.getBoundingClientRect();
      if (
        textRect.left < slideRect.left - containmentTolerance
        || textRect.top < slideRect.top - containmentTolerance
        || textRect.right > slideRect.right + containmentTolerance
        || textRect.bottom > slideRect.bottom + containmentTolerance
      ) {
        issues.push({ slot: "text-slide-containment", element: el.className });
      }
    }

    if (document.documentElement.dataset.themeId) {
      const slideStyle = getComputedStyle(slide);
      const beforeStyle = getComputedStyle(slide, "::before");
      const afterStyle = getComputedStyle(slide, "::after");
      const hasAmbientBackground = [slideStyle, beforeStyle, afterStyle]
        .some((style) => style.backgroundImage && style.backgroundImage !== "none");
      if (!hasAmbientBackground) {
        issues.push({ slot: "ambient-background", present: false });
      }

      const balancedGroupSelector = [
        ".index-item", ".column-item", ".flow-item", ".matrix-item", ".timeline-item",
        ".map-node", ".metric-item", ".contrast-panel", ".thesis-notes li",
      ].join(",");
      for (const group of slide.querySelectorAll(balancedGroupSelector)) {
        if (!isVisible(group) || group.dataset.allowAsymmetricBalance === "true") continue;
        const groupRect = rectOf(group);
        const textRects = [...group.querySelectorAll('[data-edit-layer="text"]')]
          .filter(isVisible)
          .map(rectOf);
        const textUnion = unionOf(textRects);
        if (!textUnion) continue;
        const textCenterY = (textUnion.top + textUnion.bottom) / 2;
        const normalizedOffset = Math.abs(textCenterY - groupRect.centerY) / Math.max(groupRect.height, 1);
        if (normalizedOffset > 0.18) {
          issues.push({
            slot: "group-internal-vertical-balance",
            element: group.className || group.tagName.toLowerCase(),
            normalizedOffset: round(normalizedOffset, 3),
          });
        }
      }

      const repeatedGroupSelector = [
        ".index-list", ".column-grid", ".flow-list", ".matrix-items",
        ".timeline-list", ".map-nodes", ".metric-grid", ".contrast-grid",
      ].join(",");
      for (const group of slide.querySelectorAll(repeatedGroupSelector)) {
        if (!isVisible(group) || group.dataset.allowVariableWidth === "true") continue;
        const children = [...group.children].filter(isVisible).map(rectOf);
        if (children.length < 2) continue;
        const widthVariance = (Math.max(...children.map((rect) => rect.width))
          - Math.min(...children.map((rect) => rect.width))) / geometryScale;
        if (widthVariance > 4) {
          issues.push({
            slot: "same-level-width",
            element: group.className || group.tagName.toLowerCase(),
            widthVariance: round(widthVariance, 2),
          });
        }
      }

      const content = slide.querySelector(".content");
      const contentRect = content ? rectOf(content) : null;
      const semanticSurfaces = [
        ".index-item", ".column-item", ".flow-item", ".matrix-item", ".timeline-item",
        ".map-node", ".map-center", ".metric-item", ".contrast-panel", ".thesis-notes li",
        ".ledger", ".scene-footer",
      ].join(",");
      const visibleContentRects = [
        ...slide.querySelectorAll('[data-edit-layer="text"],' + semanticSurfaces),
      ].filter((node) => isVisible(node) && !node.closest(".folio,.index-tab")).map(rectOf);
      const visibleContent = unionOf(visibleContentRects);
      if (contentRect && visibleContent) {
        const topGap = (visibleContent.top - contentRect.top) / geometryScale;
        const bottomGap = (contentRect.bottom - visibleContent.bottom) / geometryScale;
        const gapDifference = Math.abs(topGap - bottomGap);
        if (gapDifference > 100 && !slide.querySelector('[data-visual-balance="intentional-asymmetry"]')) {
          issues.push({
            slot: "overall-content-balance",
            topGap: round(topGap),
            bottomGap: round(bottomGap),
            gapDifference: round(gapDifference),
          });
        }
      }

      const titleNodes = [...slide.querySelectorAll(
        '[data-title-stack-item],.scene-title,.scene-intro,h1.el'
      )].filter(isVisible);
      const titleSet = new Set(titleNodes);
      const titleRects = titleNodes.map(rectOf);
      const bodyRects = [...slide.querySelectorAll(
        '[data-edit-layer="text"],[data-edit-layer="metric"],' + semanticSurfaces
      )].filter((node) => isVisible(node) && !titleSet.has(node)).map(rectOf);
      const titleBounds = unionOf(titleRects);
      const bodyBounds = unionOf(bodyRects);
      if (titleBounds && bodyBounds) {
        const gap = (bodyBounds.top - titleBounds.bottom) / geometryScale;
        if (gap < 10) {
          issues.push({ slot: "title-content-balance", gap: round(gap) });
        }
      }
    }

    const slideBackground = parseColor(getComputedStyle(slide).backgroundColor) || [255, 255, 255, 1];
    const backgroundLayers = [
      ".diagram-node-bg", ".card-bg", ".module-card-bg", ".metric-card-bg", ".funnel-bg",
      ".compare-panel-bg", ".toc-panel-bg", ".panel-bg", ".split-panel-bg",
    ].join(",");
    const surfaceSelectors = [
      ".diagram-node", ".demo-card", ".module-card", ".metric-card", ".funnel-stage",
      ".compare-panel", ".toc-panel-grid-card", ".toc-panel-row", ".toc-wide-panel",
      ".split-panel", ".content-priority-card", ".content-panel",
    ].join(",");
    const reliableBackground = (el) => {
      for (let current = el; current && current !== slide.parentElement; current = current.parentElement) {
        const style = getComputedStyle(current);
        const color = parseColor(style.backgroundColor);
        if (color && color[3] >= 0.94 && style.backgroundImage === "none") return color;
        if (current === slide) break;
      }
      const surface = el.closest(surfaceSelectors);
      const layer = surface?.querySelector(`:scope > ${backgroundLayers.split(",").join(", :scope > ")}`);
      if (layer) {
        const color = parseColor(getComputedStyle(layer).backgroundColor);
        if (color && color[3] >= 0.94) return color;
      }
      const slideStyle = getComputedStyle(slide);
      if (slideStyle.backgroundImage === "none" && slideBackground[3] >= 0.94) return slideBackground;
      return null;
    };

    for (const el of slide.querySelectorAll('[data-edit-kind="text"]')) {
      if (!(el.innerText || "").trim()) continue;
      const style = getComputedStyle(el);
      const foreground = parseColor(style.color);
      const background = reliableBackground(el);
      if (!foreground || !background) continue;
      let opacity = foreground[3] ?? 1;
      for (let current = el; current && current !== slide.parentElement; current = current.parentElement) {
        opacity *= toNumber(getComputedStyle(current).opacity) || 1;
        if (current === slide) break;
      }
      const renderedForeground = composite([foreground[0], foreground[1], foreground[2], opacity], background);
      const ratio = contrast(renderedForeground, background);
      const fontSize = toNumber(style.fontSize) || 0;
      const fontWeight = toNumber(style.fontWeight) || 400;
      const threshold = fontSize >= 28 || (fontSize >= 22 && fontWeight >= 700) ? 3 : 4.5;
      if (ratio + 0.02 < threshold) {
        issues.push({
          slot: "text-contrast",
          element: el.className || el.tagName.toLowerCase(),
          ratio: round(ratio, 2),
          threshold,
        });
      }
    }

    for (const frame of slide.querySelectorAll('[data-content-frame="radial-balance"]')) {
      const frameRect = frame.getBoundingClientRect();
      const hub = frame.querySelector(".cycle-hub")?.getBoundingClientRect();
      const nodes = [...frame.querySelectorAll(".cycle-node")].map((node) => node.getBoundingClientRect());
      const arrows = [...frame.querySelectorAll('.cycle-connectors [data-cycle-arc][marker-end]')];
      const expectedNodeCount = Number.parseInt(frame.dataset.cycleNodeCount || '6', 10);
      const center = (rect) => ({ x: (rect.left + rect.right) / 2, y: (rect.top + rect.bottom) / 2 });
      const near = (first, second, slidePixels = 3) => Math.abs(first - second) <= slidePixels * geometryScale;
      const overlaps = (first, second) => first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top;
      const frameCenter = center(frameRect);
      const slideCenter = center(slideRect);
      const hubCenter = hub ? center(hub) : null;
      const hubBackground = frame.querySelector('.cycle-hub .diagram-node-bg');
      const hubRadiusValue = hubBackground ? getComputedStyle(hubBackground).borderTopLeftRadius : '0';
      const hubCircle = hub ? (hubRadiusValue.includes('%') ? Number.parseFloat(hubRadiusValue) >= 49 : Number.parseFloat(hubRadiusValue) >= (hub.width / geometryScale) * 0.45) : false;
      const nodeCenters = nodes.map(center);
      const nodeCentroid = nodeCenters.length ? {
        x: nodeCenters.reduce((sum, point) => sum + point.x, 0) / nodeCenters.length,
        y: nodeCenters.reduce((sum, point) => sum + point.y, 0) / nodeCenters.length,
      } : null;
      const radii = hubCenter ? nodeCenters.map((point) => Math.hypot(point.x - hubCenter.x, point.y - hubCenter.y)) : [];
      const equalRadius = radii.length ? Math.max(...radii) - Math.min(...radii) <= 3 * geometryScale : false;
      const callouts = [...frame.querySelectorAll('.cycle-callout')].map((callout) => callout.getBoundingClientRect());
      const calloutSpan = callouts.length ? (Math.max(...callouts.map((item) => item.right)) - Math.min(...callouts.map((item) => item.left))) / frameRect.width : 0;
      const pass = Boolean(hub)
        && nodes.length === expectedNodeCount
        && arrows.length === expectedNodeCount
        && Boolean(frame.querySelector(".cycle-ring"))
        && frame.dataset.cycleGeometry === "circle"
        && near(frameCenter.x, slideCenter.x)
        && near(frameCenter.y, slideCenter.y)
        && near(hubCenter.x, frameCenter.x)
        && near(hubCenter.y, frameCenter.y)
        && near(nodeCentroid.x, hubCenter.x)
        && near(nodeCentroid.y, hubCenter.y)
        && near(hub.width, hub.height)
        && hubCircle
        && callouts.length === expectedNodeCount
        && calloutSpan >= 0.9
        && nodes.every((node) => near(node.width, node.height))
        && equalRadius
        && !nodes.some((node, index) => nodes.slice(index + 1).some((other) => overlaps(node, other)));
      if (!pass) issues.push({ slot: "radial-balance", pass: false, nodes: nodes.length, arrows: arrows.length, equalRadius, hubCircle, callouts: callouts.length, calloutSpan: round(calloutSpan, 2) });
    }

    return {
      layout: slide.dataset.layoutId || slide.id || null,
      issueCount: issues.length,
      issues,
      viewport: { width: window.innerWidth, height: window.innerHeight },
    };
  }

  root.runHtmlVisualQa = runHtmlVisualQa;
  if (typeof module !== "undefined" && module.exports) module.exports = runHtmlVisualQa;
}(typeof window !== "undefined" ? window : globalThis));
