const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const { pathToFileURL } = require("node:url");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

function argsOf(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i], value = argv[i + 1];
    if (key === "--html-dir") { out.htmlDir = value; i += 1; }
    else if (key === "--output-dir") { out.outputDir = value; i += 1; }
    else if (key === "--report") { out.report = value; i += 1; }
    else if (key === "--file") { out.file = value; i += 1; }
    else if (key === "--limit-slides") { out.limitSlides = Number(value); i += 1; }
    else if (key === "--allow-remote-fonts") { out.allowRemoteFonts = true; }
  }
  if (!out.htmlDir || !out.outputDir || !out.report) throw new Error("--html-dir, --output-dir and --report are required");
  return out;
}

async function activeSlideGeometry(page) {
  return page.evaluate(() => {
    const slide = document.querySelector("#stage > .slide.active");
    const slideRect = slide.getBoundingClientRect();
    const scaleX = Math.max(slide.offsetWidth ? slideRect.width / slide.offsetWidth : 1, 0.0001);
    const scaleY = Math.max(slide.offsetHeight ? slideRect.height / slide.offsetHeight : 1, 0.0001);
    const nodes = [...slide.querySelectorAll('.el,[data-edit-layer="text"],[data-edit-layer="metric"]')]
      .map((node, index) => {
        const rect = node.getBoundingClientRect();
        const style = getComputedStyle(node);
        if (style.display === "none" || style.visibility === "hidden" || rect.width <= 0 || rect.height <= 0) return null;
        return {
          index,
          rect: [
            (rect.left - slideRect.left) / scaleX,
            (rect.top - slideRect.top) / scaleY,
            rect.width / scaleX,
            rect.height / scaleY,
          ],
        };
      })
      .filter(Boolean);
    return { layout: slide.dataset.layoutId, nodes };
  });
}

function geometryDrift(before, after) {
  if (before.nodes.length !== after.nodes.length) return Infinity;
  let drift = 0;
  for (let index = 0; index < before.nodes.length; index += 1) {
    if (before.nodes[index].index !== after.nodes[index].index) return Infinity;
    for (let axis = 0; axis < 4; axis += 1) {
      drift = Math.max(drift, Math.abs(before.nodes[index].rect[axis] - after.nodes[index].rect[axis]));
    }
  }
  return drift;
}

async function main() {
  const options = argsOf(process.argv);
  const files = (await fs.readdir(options.htmlDir))
    .filter((name) => name.endsWith(".html") && (!options.file || name === options.file))
    .sort();
  if (options.file && files.length === 0) throw new Error(`HTML file not found in --html-dir: ${options.file}`);
  await fs.mkdir(options.outputDir, { recursive: true });
  const { chromium } = loadPlaywright();
  const executablePath = browserExecutable();
  if (!process.env.BROWSER_CDP_URL && !executablePath) throw new Error("No Chrome or Edge executable found for HTML QA");
  const browser = process.env.BROWSER_CDP_URL
    ? await chromium.connectOverCDP(process.env.BROWSER_CDP_URL)
    : await chromium.launch({ headless: true, executablePath });
  const report = {
    qaMode: "report-only",
    files: files.length,
    slides: 0,
    issues: [],
    orphanAdjustments: [],
    densityCoverage: { low: 0, medium: 0, high: 0 },
    fontMode: options.allowRemoteFonts ? "remote-formal-fonts" : "local-fallback-fonts",
    sources: [],
    sourceImmutability: { checked: 0, unchanged: 0, violations: [] },
    selectionGeometryChecks: 0,
  };
  try {
    for (const file of files) {
      const theme = path.basename(file, ".html");
      const outDir = path.join(options.outputDir, theme);
      await fs.rm(outDir, { recursive: true, force: true });
      await fs.mkdir(outDir, { recursive: true });
      const page = await browser.newPage({ viewport: { width: 960, height: 540 }, deviceScaleFactor: 1 });
      // Remote Google Fonts must never block local visual QA.  The deck keeps its
      // local fallback stack, while the capture continues even when the network is
      // unavailable or a font endpoint is slow.
      if (!options.allowRemoteFonts) {
        await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
        await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
      }
      const htmlPath = path.resolve(options.htmlDir, file);
      const markup = await fs.readFile(htmlPath, "utf8");
      const sourceRecord = {
        file,
        sha256: crypto.createHash("sha256").update(markup).digest("hex"),
      };
      report.sources.push(sourceRecord);
      // The generated decks are self-contained.  Loading the markup directly
      // avoids intermittent Windows/OneDrive file:// navigation stalls while
      // exercising the exact same DOM, CSS, editor runtime, and slide logic.
      // Provenance-tracked raster backgrounds remain project-local assets. A
      // file base keeps those relative URLs (and edit-mode.js) resolvable while
      // the authored markup is loaded directly for deterministic QA.
      const baseHref = pathToFileURL(`${path.dirname(htmlPath)}${path.sep}`).href;
      const markupWithBase = markup.replace(/<head>/i, `<head><base href="${baseHref}">`);
      await page.setContent(markupWithBase, {
        waitUntil: "domcontentloaded",
        timeout: 120000,
      });
      await Promise.race([
        page.evaluate(() => document.fonts?.ready),
        page.waitForTimeout(3000),
      ]);
      await page.waitForFunction(
        () => document.documentElement.dataset.layoutReady === 'true',
        null,
        { timeout: 120000 },
      );
      const count = await page.evaluate(() => document.querySelectorAll("#stage > .slide").length);
      const limit = Math.min(count, options.limitSlides || count);
      for (let index = 0; index < limit; index += 1) {
        await page.evaluate((i) => window.setSlide(i), index);
        await page.evaluate(() => window.EditMode?.toggle(true));
        await page.waitForTimeout(40);
        const beforeSelection = await activeSlideGeometry(page);
        const selectionTarget = page.locator('#stage > .slide.active .el[data-edit-composite]').first();
        let selectionDrift = null;
        let selectionTargetName = null;
        if (await selectionTarget.count()) {
          selectionTargetName = await selectionTarget.getAttribute('data-edit-composite');
          // The player/editor chrome is intentionally interactive, so a real
          // mouse click can be intercepted by a transparent overlay on dense
          // slides.  This report-only geometry check only needs the editor's
          // selection state; dispatch the same bubbling click from the target
          // instead of making the capture dependent on hit testing.
          await selectionTarget.evaluate((el) => {
            el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
          });
          await page.waitForTimeout(40);
          const afterSelection = await activeSlideGeometry(page);
          selectionDrift = geometryDrift(beforeSelection, afterSelection);
          report.selectionGeometryChecks += 1;
        }
        const qa = await page.evaluate(() => {
          const slide = document.querySelector("#stage > .slide.active");
          const issues = [];
          const slideRectForScale = slide.getBoundingClientRect();
          const geometryScale = Math.max(slide.offsetWidth ? slideRectForScale.width / slide.offsetWidth : 1, 0.0001);
          const embeddedEditor = document.querySelector('script[data-edit-mode-embedded="true"]');
          const externalEditor = document.querySelector('script[src="edit-mode.js"]');
          const frameworkReady = Boolean(
            document.getElementById("canvasBox")
            && document.getElementById("barInner")
            && document.getElementById("hint")
            && (embeddedEditor || externalEditor)
            && window.EditMode
            && document.querySelectorAll("#stage > .slide[id]").length === document.querySelectorAll("#stage > .slide").length
          );
          if (!frameworkReady) issues.push({ slot: "edit-framework", frameworkReady: false });
          for (const background of slide.querySelectorAll('.diagram-node-bg')) {
            const parent = background.parentElement;
            const backgroundZ = Number.parseInt(getComputedStyle(background).zIndex, 10) || 0;
            const exposedTextLayers = [...parent.querySelectorAll(
              ':scope > [data-edit-layer="text"],:scope > [data-edit-layer="metric"]',
            )].filter((layer) => {
              const rect = layer.getBoundingClientRect();
              const style = getComputedStyle(layer);
              return (layer.textContent || '').trim()
                && rect.width > 0 && rect.height > 0
                && style.display !== 'none' && style.visibility !== 'hidden';
            }).filter((layer) => ((Number.parseInt(getComputedStyle(layer).zIndex, 10) || 0) <= backgroundZ));
            if (exposedTextLayers.length) {
              issues.push({
                slot: 'background-layer-stack',
                element: parent.className || parent.tagName,
                backgroundZ,
                coveredTextLayers: exposedTextLayers.length,
              });
            }
          }
          for (const el of [slide, ...slide.querySelectorAll("*")]) {
            const hasDirectText = [...el.childNodes].some((node) => (
              node.nodeType === Node.TEXT_NODE && (node.textContent || "").trim()
            ));
            if (!hasDirectText) continue;
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            const fontSize = Number.parseFloat(style.fontSize) || 0;
            if (style.display !== "none" && style.visibility !== "hidden"
              && rect.width > 0 && rect.height > 0 && fontSize < 35.99) {
              issues.push({
                slot: "generated-font-floor",
                element: el.className || el.tagName,
                fontSize: Math.round(fontSize * 100) / 100,
                text: (el.textContent || "").trim().slice(0, 80),
              });
            }
          }
          // Detect Chinese orphan tails after the browser has performed the
          // real font/layout pass. A final line containing only one or two Han
          // characters is almost always an unintended wrap. Generation should
          // widen the frame, shorten the copy, or reduce type without crossing
          // the 36px floor; REVIEW must not silently accept the orphan.
          const textSelectors = '[data-edit-layer="text"],[data-edit-kind="text"]';
          const orphanCandidates = [...slide.querySelectorAll(textSelectors)]
            .filter((el) => !el.querySelector(textSelectors) && !el.matches('.axis-label'));
          for (const el of orphanCandidates) {
            if (el.dataset.orphanIntentional === 'true') continue;
            const style = getComputedStyle(el);
            const box = el.getBoundingClientRect();
            if (style.display === 'none' || style.visibility === 'hidden'
              || style.writingMode.startsWith('vertical')
              || box.width <= 0 || box.height <= 0) continue;
            const fontSize = Number.parseFloat(style.fontSize) || 0;
            const glyphs = [];
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            for (let node = walker.nextNode(); node; node = walker.nextNode()) {
              const parentStyle = getComputedStyle(node.parentElement || el);
              if (parentStyle.display === 'none' || parentStyle.visibility === 'hidden') continue;
              for (let offset = 0; offset < node.data.length;) {
                const char = String.fromCodePoint(node.data.codePointAt(offset));
                const nextOffset = offset + char.length;
                if (!/\s/u.test(char)) {
                  const range = document.createRange();
                  range.setStart(node, offset);
                  range.setEnd(node, nextOffset);
                  const rect = range.getBoundingClientRect();
                  if (rect.width > 0 && rect.height > 0) {
                    glyphs.push({ char, left: rect.left, top: rect.top });
                  }
                }
                offset = nextOffset;
              }
            }
            if (!glyphs.length) continue;
            glyphs.sort((a, b) => a.top - b.top || a.left - b.left);
            const lineTolerance = Math.max(2, fontSize * geometryScale * 0.18);
            const lines = [];
            for (const glyph of glyphs) {
              let line = lines.find((candidate) => Math.abs(candidate.top - glyph.top) <= lineTolerance);
              if (!line) {
                line = { top: glyph.top, glyphs: [] };
                lines.push(line);
              }
              line.glyphs.push(glyph);
            }
            if (lines.length < 2) continue;
            const lineTexts = lines
              .sort((a, b) => a.top - b.top)
              .map((line) => line.glyphs.sort((a, b) => a.left - b.left).map((glyph) => glyph.char).join(''));
            const tailText = lineTexts.at(-1);
            const tailCore = tailText.replace(/[，。！？、；：,.!?;:（）()「」『』【】《》〈〉—–·…]/gu, '');
            const allCore = lineTexts.join('').replace(/[^\p{Script=Han}]/gu, '');
            if (allCore.length >= 6 && /^[\p{Script=Han}]{1,2}$/u.test(tailCore)) {
              issues.push({
                slot: 'text-orphan-tail',
                element: el.className || el.tagName,
                fontSize: Math.round(fontSize * 100) / 100,
                tailText,
                lineTexts,
                hardBreaks: el.querySelectorAll('br').length,
              });
            }
          }
          if (slide.querySelector('.theme-mark,.footer.meta')) {
            issues.push({ slot: 'projection-metadata', reason: 'renderer metadata must stay in data attributes and player chrome' });
          }

          // Pattern-only decks reject all media. image-planned decks may retain one
          // independently editable semantic photo on a declared photo page, but it
          // must be loaded, visible, slot-bound, and provenance-complete.
          // Editor toolbar SVG icons live outside the active slide and are not part
          // of this check. Slide backgrounds may use CSS gradients but never image URLs.
          const assetPolicy = document.documentElement.dataset.assetPolicy
            || document.documentElement.dataset.layoutAssetPolicy
            || 'image-free';
          const allowsEmbeddedSvg = ['embedded-open-source-svg', 'embedded-provenance-svg'].includes(assetPolicy);
          const allowsEmbeddedRaster = assetPolicy === 'embedded-provenance-raster';
          const allowsEmbeddedAsset = allowsEmbeddedSvg || allowsEmbeddedRaster;
          const semanticImages = [...slide.querySelectorAll('img[data-semantic-image="true"]')];
          const semanticPhotoExpected = assetPolicy === 'image-planned'
            && slide.dataset.imageVariant === 'photo';
          const semanticImageValid = (image) => {
            const style = getComputedStyle(image);
            const rect = image.getBoundingClientRect();
            return semanticPhotoExpected
              && image.naturalWidth > 0
              && image.naturalHeight > 0
              && style.display !== 'none'
              && style.visibility !== 'hidden'
              && Number(style.opacity) !== 0
              && rect.width > 0
              && rect.height > 0
              && Boolean(image.closest('.cover-media-field,.toc-image-field,.closing-photo-field'))
              && String(image.getAttribute('src') || '').startsWith('data:image/')
              && Boolean(image.getAttribute('alt'))
              && Boolean(image.dataset.cropBehavior)
              && Boolean(image.dataset.focalRegion)
              && Boolean(image.dataset.imageProvenance)
              && Boolean(image.dataset.semanticImageSource)
              && Boolean(image.dataset.semanticImageSha256);
          };
          const invalidSemanticImages = semanticImages.filter((image) => !semanticImageValid(image));
          if ((semanticPhotoExpected && semanticImages.length !== 1) || invalidSemanticImages.length) {
            issues.push({
              slot: 'semantic-image-contract',
              expected: semanticPhotoExpected ? 1 : 0,
              actual: semanticImages.length,
              invalid: invalidSemanticImages.length,
            });
          }
          const forbiddenMedia = [...slide.querySelectorAll('img,picture,video,canvas,svg image')]
            .filter((element) => !element.matches('img[data-semantic-image="true"]'));
          if (forbiddenMedia.length) {
            issues.push({ slot: allowsEmbeddedAsset ? 'embedded-media-element' : 'image-free', count: forbiddenMedia.length });
          }
          for (const el of slide.querySelectorAll('.scene *')) {
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            if (style.display === 'none' || style.visibility === 'hidden' || rect.width <= 0 || rect.height <= 0) continue;
            if (style.backgroundImage && /url\(/i.test(style.backgroundImage)) {
              const isEmbeddedSvg = /^url\(["']?data:image\/svg\+xml/i.test(style.backgroundImage);
              const isEmbeddedRaster = /^url\(["']?data:image\/(?:jpeg|png|webp)/i.test(style.backgroundImage);
              const approvedAsset = (allowsEmbeddedSvg && isEmbeddedSvg)
                || (allowsEmbeddedRaster && isEmbeddedRaster);
              if (!approvedAsset) {
                issues.push({
                  slot: allowsEmbeddedAsset ? 'unapproved-background-asset' : 'image-free-background',
                  element: el.className || el.tagName,
                });
              }
            }
            if (style.clipPath && style.clipPath !== 'none') {
              issues.push({ slot: 'abrupt-shape', element: el.className || el.tagName, clipPath: style.clipPath });
            }
          }
          const scene = slide.querySelector('.scene');
          if (scene && scene.dataset.allowAsymmetricBalance !== 'true') {
            const sceneRect = scene.getBoundingClientRect();
            const visibleTextRects = [...scene.querySelectorAll('[data-edit-layer="text"]')]
              .map((el) => ({ el, rect: el.getBoundingClientRect(), style: getComputedStyle(el) }))
              .filter(({ el, rect, style }) => (
                (el.innerText || '').trim()
                && style.display !== 'none'
                && style.visibility !== 'hidden'
                && rect.width > 0
                && rect.height > 0
              ))
              .map(({ rect }) => rect);
            const visibleStructureRects = [...scene.querySelectorAll(
              '.thesis-mark,.thesis-notes,.cover-signature,.close-signature,.index-list,.column-grid,.flow-list,.matrix-items,.ledger,.timeline-list,.map-center,.map-nodes,.metric-grid,.contrast-grid,.close-action,[data-edit-role="hero-illustration"]'
            )]
              .map((el) => ({ rect: el.getBoundingClientRect(), style: getComputedStyle(el) }))
              .filter(({ rect, style }) => (
                style.display !== 'none'
                && style.visibility !== 'hidden'
                && rect.width > 0
                && rect.height > 0
              ))
              .map(({ rect }) => rect);
            const pseudoVisualRects = [];
            if (allowsEmbeddedSvg && slide.dataset.pseudoVisualBalance === "include") {
              const slideRect = slide.getBoundingClientRect();
              const pseudoStyle = getComputedStyle(slide, '::after');
              const pseudoWidthCss = Number.parseFloat(pseudoStyle.width) || 0;
              const pseudoHeightCss = Number.parseFloat(pseudoStyle.height) || 0;
              const isMeaningfulIllustration = (
                /^url\(["']?data:image\/svg\+xml/i.test(pseudoStyle.backgroundImage)
                && pseudoWidthCss >= 300
                && pseudoHeightCss >= 300
              );
              if (isMeaningfulIllustration) {
                const width = pseudoWidthCss * geometryScale;
                const height = pseudoHeightCss * geometryScale;
                const leftCss = Number.parseFloat(pseudoStyle.left);
                const rightCss = Number.parseFloat(pseudoStyle.right);
                const topCss = Number.parseFloat(pseudoStyle.top);
                const bottomCss = Number.parseFloat(pseudoStyle.bottom);
                const left = Number.isFinite(leftCss)
                  ? slideRect.left + leftCss * geometryScale
                  : slideRect.right - (Number.isFinite(rightCss) ? rightCss : 0) * geometryScale - width;
                const top = Number.isFinite(topCss)
                  ? slideRect.top + topCss * geometryScale
                  : slideRect.bottom - (Number.isFinite(bottomCss) ? bottomCss : 0) * geometryScale - height;
                pseudoVisualRects.push({ left, top, right: left + width, bottom: top + height });
              }
            }
            const visibleGroupRects = [...visibleTextRects, ...visibleStructureRects, ...pseudoVisualRects];
            if (visibleGroupRects.length) {
              const bounds = visibleGroupRects.reduce((acc, rect) => ({
                left: Math.min(acc.left, rect.left),
                top: Math.min(acc.top, rect.top),
                right: Math.max(acc.right, rect.right),
                bottom: Math.max(acc.bottom, rect.bottom),
              }), { left: Infinity, top: Infinity, right: -Infinity, bottom: -Infinity });
              const dx = Math.abs((bounds.left + bounds.right - sceneRect.left - sceneRect.right) / 2) / geometryScale;
              const dy = Math.abs((bounds.top + bounds.bottom - sceneRect.top - sceneRect.bottom) / 2) / geometryScale;
              if (dx > 42 || dy > 50) {
                issues.push({ slot: 'visible-content-center', dx: Math.round(dx), dy: Math.round(dy) });
              }
            }
          }

          if (document.documentElement.dataset.themeId) {
            const visible = (node) => {
              const rect = node.getBoundingClientRect();
              const style = getComputedStyle(node);
              return rect.width > 0.5 && rect.height > 0.5
                && style.display !== 'none' && style.visibility !== 'hidden' && Number.parseFloat(style.opacity) !== 0;
            };
            const rectOf = (node) => {
              const rect = node.getBoundingClientRect();
              return {
                left: rect.left,
                top: rect.top,
                right: rect.right,
                bottom: rect.bottom,
                width: rect.width,
                height: rect.height,
                centerY: (rect.top + rect.bottom) / 2,
              };
            };
            const unionOf = (rects) => rects.length ? {
              left: Math.min(...rects.map((rect) => rect.left)),
              right: Math.max(...rects.map((rect) => rect.right)),
              top: Math.min(...rects.map((rect) => rect.top)),
              bottom: Math.max(...rects.map((rect) => rect.bottom)),
            } : null;
            const ambientStyles = [
              getComputedStyle(slide),
              getComputedStyle(slide, '::before'),
              getComputedStyle(slide, '::after'),
            ];
            const explicitNoBackgroundPattern = document.documentElement.dataset.backgroundPattern === 'none';
            if (!explicitNoBackgroundPattern && !ambientStyles.some((style) => style.backgroundImage && style.backgroundImage !== 'none')) {
              issues.push({ slot: 'ambient-background', present: false });
            }

            const balancedGroups = [
              '.index-item', '.column-item', '.flow-item', '.matrix-item', '.timeline-item',
              '.map-node', '.metric-item', '.contrast-panel', '.thesis-notes li',
            ].join(',');
            for (const group of slide.querySelectorAll(balancedGroups)) {
              if (!visible(group) || group.dataset.allowAsymmetricBalance === 'true') continue;
              const groupRect = rectOf(group);
              const textBounds = unionOf(
                [...group.querySelectorAll('[data-edit-layer="text"]')].filter(visible).map(rectOf)
              );
              if (!textBounds) continue;
              const normalizedOffset = Math.abs(
                (textBounds.top + textBounds.bottom) / 2 - groupRect.centerY
              ) / Math.max(groupRect.height, 1);
              if (normalizedOffset > 0.18) {
                issues.push({
                  slot: 'group-internal-vertical-balance',
                  element: group.className || group.tagName,
                  normalizedOffset: Math.round(normalizedOffset * 1000) / 1000,
                });
              }
            }

            const repeatedGroups = [
              '.index-list', '.column-grid', '.flow-list', '.matrix-items',
              '.timeline-list', '.map-nodes', '.metric-grid', '.contrast-grid',
            ].join(',');
            for (const group of slide.querySelectorAll(repeatedGroups)) {
              if (!visible(group) || group.dataset.allowVariableWidth === 'true') continue;
              const childWidths = [...group.children].filter(visible).map((child) => rectOf(child).width);
              if (childWidths.length < 2) continue;
              const widthVariance = (Math.max(...childWidths) - Math.min(...childWidths)) / geometryScale;
              if (widthVariance > 4) {
                issues.push({
                  slot: 'same-level-width',
                  element: group.className || group.tagName,
                  widthVariance: Math.round(widthVariance * 10) / 10,
                });
              }
            }

            const titleNodes = [...slide.querySelectorAll(
              '[data-title-stack-item],.scene-title,.scene-intro,h1.el'
            )].filter(visible);
            const titleSet = new Set(titleNodes);
            const titleBounds = unionOf(titleNodes.map(rectOf));
            const contentBounds = unionOf(
              [...slide.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')]
                .filter((node) => visible(node) && !titleSet.has(node))
                .map(rectOf)
            );
            if (titleBounds && contentBounds) {
              const headerMode = slide.dataset.headerMode || 'top';
              const titleContentGap = headerMode === 'side-left'
                ? (contentBounds.left - titleBounds.right) / geometryScale
                : headerMode === 'side-right'
                  ? (titleBounds.left - contentBounds.right) / geometryScale
                  : (contentBounds.top - titleBounds.bottom) / geometryScale;
              if (titleContentGap < 10) {
                issues.push({
                  slot: 'title-content-balance',
                  gap: Math.round(titleContentGap * 10) / 10,
                });
              }
            }
          }

          // Ambient HTML depth must come from Pattern / gradient / texture / shadow.
          // Non-informational edge objects and pseudo-element stickers are a regression:
          // they make the slide feel assembled from rigid decorative pieces and also add
          // meaningless selectable objects in edit mode.
          for (const el of slide.querySelectorAll('.cover-edge-decor,.chapter-side-decor')) {
            const rect = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            if (style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0) {
              issues.push({ slot: "ambient-hard-decor", element: el.className });
            }
          }
          for (const pseudo of ['::before', '::after']) {
            const style = getComputedStyle(slide, pseudo);
            const content = style.content || 'none';
            if (style.display !== 'none' && content !== 'none' && content !== 'normal' && content !== '""') {
              const isEmbeddedSvg = /^url\(["']?data:image\/svg\+xml/i.test(content);
              if (!allowsEmbeddedSvg || !isEmbeddedSvg) {
                issues.push({ slot: "ambient-pseudo-decor", pseudo, content });
              }
            }
          }
          if (['funnel-4', 'pyramid', 'org-chart'].includes(slide.dataset.layoutId)) {
            const title = slide.querySelector('.prod-title-center-axis');
            const content = slide.querySelector('.content');
            if (!title || !content) {
              issues.push({ slot: "diagram-title-axis", reason: "missing-centered-title" });
            } else {
              const titleRect = title.getBoundingClientRect();
              const contentRect = content.getBoundingClientRect();
              const axisDelta = Math.abs(
                (titleRect.left + titleRect.right) / 2 - (contentRect.left + contentRect.right) / 2
              ) / geometryScale;
              if (axisDelta > 2) {
                issues.push({ slot: "diagram-title-axis", axisDelta: Math.round(axisDelta * 10) / 10 });
              }
            }
          }
          if (!embeddedEditor || externalEditor) {
            issues.push({ slot: "editor-self-contained", embeddedEditor: Boolean(embeddedEditor), externalEditor: Boolean(externalEditor) });
          }
          for (const el of slide.querySelectorAll('[data-edit-kind="text"]')) {
            if (!['text', 'container'].includes(el.dataset.editFit)) {
              issues.push({ slot: "text-fit-contract", element: el.className });
            }
          }
          for (const area of slide.querySelectorAll('[data-auto-layout]')) {
            const materialized = area.dataset.layoutMaterialized === "true" && area.classList.contains("layout-materialized");
            const childrenAbsolute = [...area.querySelectorAll(':scope > .el,:scope > [data-layout-item]')].every((el) => {
              const style = getComputedStyle(el);
              return style.position === "absolute"
                && Number.isFinite(parseFloat(el.style.left))
                && Number.isFinite(parseFloat(el.style.top))
                && Number.isFinite(parseFloat(el.style.width))
                && Number.isFinite(parseFloat(el.style.height));
            });
            if (!materialized || !childrenAbsolute) {
              issues.push({ slot: "layout-materialization", materialized, childrenAbsolute });
            }
          }
          for (const el of slide.querySelectorAll('[data-edit-fit="text"]')) {
            const range = document.createRange();
            range.selectNodeContents(el);
            const textRect = range.getBoundingClientRect();
            const boxRect = el.getBoundingClientRect();
            const excessWidth = (boxRect.width - textRect.width) / geometryScale;
            const excessHeight = (boxRect.height - textRect.height) / geometryScale;
            const fontSize = Number.parseFloat(getComputedStyle(el).fontSize) || 0;
            const widthTolerance = Math.max(18, fontSize * 0.35);
            // A max-content editable text root is sized from glyph advances,
            // while Range#getBoundingClientRect reports painted ink bounds.
            // Allow one font-size of advance-only width only when the authored
            // frame is intrinsic and has no scroll/crop evidence; all ordinary
            // fixed-width frames keep the strict tolerance below.
            const intrinsicTextFrame = el.dataset.editFit === 'text'
              && el.scrollWidth <= el.clientWidth + 1
              && el.scrollHeight <= el.clientHeight + 1;
            const intrinsicWidthAllowance = intrinsicTextFrame
              ? Math.max(widthTolerance, fontSize + 1)
              : widthTolerance;
            const verticalText = getComputedStyle(el).writingMode.startsWith("vertical");
            // Range boxes exclude part of vertical glyph leading/letter-spacing,
            // while the editable frame correctly includes it.  Keep the frame
            // strict, but use a writing-mode-aware tolerance.
            const heightTolerance = verticalText
              ? Math.max(40, fontSize * 2.4)
              : Math.max(20, fontSize * 0.25);
            const negativeTolerance = Math.max(24, fontSize * 0.55);
            if (excessWidth > intrinsicWidthAllowance || excessHeight > heightTolerance
              || excessWidth < -negativeTolerance || excessHeight < -negativeTolerance) {
              issues.push({
                slot: "text-boundary",
                element: el.className,
                excessWidth: Math.round(excessWidth * 10) / 10,
                excessHeight: Math.round(excessHeight * 10) / 10,
              });
            }
          }
          // Top-level page text roots are independently editable authored
          // objects. Their frames must not collide after real browser layout;
          // a title wrapping into its intro is a content-capacity failure even
          // when neither individual frame reports overflow.
          const directPageTextRoots = [...slide.querySelectorAll('.prod-frame > .el[data-edit-kind="text"]')]
            .filter((element) => {
              const style = getComputedStyle(element);
              const rect = element.getBoundingClientRect();
              return style.display !== 'none' && style.visibility !== 'hidden'
                && rect.width > 0.5 && rect.height > 0.5;
            });
          for (let firstIndex = 0; firstIndex < directPageTextRoots.length; firstIndex += 1) {
            for (let secondIndex = firstIndex + 1; secondIndex < directPageTextRoots.length; secondIndex += 1) {
              const first = directPageTextRoots[firstIndex];
              const second = directPageTextRoots[secondIndex];
              const firstRect = first.getBoundingClientRect();
              const secondRect = second.getBoundingClientRect();
              const overlapWidth = Math.min(firstRect.right, secondRect.right) - Math.max(firstRect.left, secondRect.left);
              const overlapHeight = Math.min(firstRect.bottom, secondRect.bottom) - Math.max(firstRect.top, secondRect.top);
              if (overlapWidth > 0.5 && overlapHeight > 0.5) {
                issues.push({
                  slot: 'page-text-root-overlap',
                  first: first.className || first.dataset.editId || first.tagName,
                  second: second.className || second.dataset.editId || second.tagName,
                  overlapWidth: Math.round(overlapWidth / geometryScale * 10) / 10,
                  overlapHeight: Math.round(overlapHeight / geometryScale * 10) / 10,
                });
              }
            }
          }
          for (const row of slide.querySelectorAll('[data-row-align="center"]')) {
            const rowRect = row.getBoundingClientRect();
            const visibleLayers = [...row.querySelectorAll(':scope > [data-edit-layer]')]
              .filter((el) => {
                const rect = el.getBoundingClientRect();
                const style = getComputedStyle(el);
                return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
              });
            const centers = visibleLayers.map((el) => {
                const rect = el.getBoundingClientRect();
                return (rect.top + rect.bottom) / 2;
              });
            if (centers.length > 1) {
              const spread = (Math.max(...centers) - Math.min(...centers)) / geometryScale;
              if (spread > 1.5) {
                issues.push({
                  slot: "row-vertical-center",
                  element: row.className,
                  centerSpread: Math.round(spread * 10) / 10,
                });
              }
            }
            for (const el of visibleLayers) {
              const rect = el.getBoundingClientRect();
              const outside = Math.max(
                rowRect.left - rect.left,
                rect.right - rowRect.right,
                rowRect.top - rect.top,
                rect.bottom - rowRect.bottom,
                0,
              ) / geometryScale;
              if (outside > 2) {
                issues.push({
                  slot: "row-child-overflow",
                  element: row.className,
                  child: el.tagName.toLowerCase(),
                  outside: Math.round(outside * 10) / 10,
                });
              }
            }
          }
          const title = slide.querySelector('.cover-title,.page-title');
          const subtitle = slide.querySelector('.cover-subtitle,.page-subtitle');
          if (title && subtitle) {
            const count = (el) => (el.innerText || '').replace(/\s+/g, '').length;
            const titleRect = title.getBoundingClientRect();
            const subtitleRect = subtitle.getBoundingClientRect();
            const titleSize = parseFloat(getComputedStyle(title).fontSize) || 0;
            const subtitleSize = parseFloat(getComputedStyle(subtitle).fontSize) || 0;
            if (count(title) > count(subtitle)) {
              issues.push({ slot: "title-subtitle-copy", titleLength: count(title), subtitleLength: count(subtitle) });
            }
            if (subtitleRect.width <= titleRect.width) {
              issues.push({ slot: "title-subtitle-width", titleWidth: Math.round(titleRect.width), subtitleWidth: Math.round(subtitleRect.width) });
            }
            if (subtitleSize < 32 || subtitleSize < titleSize * 0.36) {
              issues.push({ slot: "subtitle-hierarchy", titleSize, subtitleSize });
            }
          }
          for (const panel of slide.querySelectorAll('.contrast-panel')) {
            const label = panel.querySelector('.contrast-label');
            const bodyNodes = [...panel.querySelectorAll('.contrast-lead,.item-copy')]
              .filter((node) => (node.innerText || '').trim());
            if (!label || !bodyNodes.length) continue;
            const labelStyle = getComputedStyle(label);
            const labelSize = Number.parseFloat(labelStyle.fontSize) || 0;
            const labelWeight = Number.parseInt(labelStyle.fontWeight, 10) || 400;
            const bodySizes = bodyNodes.map((node) => Number.parseFloat(getComputedStyle(node).fontSize) || 0);
            const bodyWeights = bodyNodes.map((node) => Number.parseInt(getComputedStyle(node).fontWeight, 10) || 400);
            const bodySize = Math.max(...bodySizes);
            const bodyWeight = Math.max(...bodyWeights);
            if (labelSize < bodySize + 6 || labelWeight < 700 || labelWeight <= bodyWeight) {
              issues.push({
                slot: 'contrast-label-hierarchy',
                label: (label.innerText || '').trim(),
                labelSize,
                labelWeight,
                bodySize,
                bodyWeight,
              });
            }
          }
          for (const card of slide.querySelectorAll('.demo-card')) {
            const number = card.querySelector('.card-no');
            const cardTitle = card.querySelector('.card-title');
            const flow = ['.card-no', '.card-title', '.card-body', '.card-tags']
              .map((selector) => card.querySelector(selector))
              .filter(Boolean)
              .map((el) => el.getBoundingClientRect());
            if (number && cardTitle) {
              const numberSize = parseFloat(getComputedStyle(number).fontSize) || 0;
              const cardTitleSize = parseFloat(getComputedStyle(cardTitle).fontSize) || 0;
              if (numberSize + 0.5 < cardTitleSize) {
                issues.push({ slot: "card-number-hierarchy", numberSize, cardTitleSize });
              }
            }
            if (flow.length) {
              const cardRect = card.getBoundingClientRect();
              const contentTop = Math.min(...flow.map((rect) => rect.top));
              const contentBottom = Math.max(...flow.map((rect) => rect.bottom));
              const offset = Math.abs((contentTop + contentBottom) / 2 - (cardRect.top + cardRect.bottom) / 2) / geometryScale;
              const cardHeight = cardRect.height / geometryScale;
              if (offset > Math.max(18, cardHeight * 0.12)) {
                issues.push({ slot: "card-content-balance", offset: Math.round(offset * 10) / 10 });
              }
            }
          }
          const parseColor = (value) => {
            const parts = String(value || '').match(/[\d.]+/g)?.map(Number) || [];
            if (String(value || '').startsWith('color(srgb') && parts.length >= 3) {
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
          const slideBackground = parseColor(getComputedStyle(slide).backgroundColor) || [255, 255, 255, 1];
          const effectiveBackground = (el) => {
            if (el.matches('.cover-hero-title,.cover-hero-subtitle,.cover-hero-speaker,.cover-hero-org,.cover-bottom-title,.cover-bottom-subtitle,.cover-bottom-meta')) {
              return [8, 14, 24, 1];
            }
            const ownBackground = parseColor(getComputedStyle(el).backgroundColor);
            if (ownBackground && ownBackground[3] > 0) {
              return ownBackground[3] < 1 ? composite(ownBackground, slideBackground) : ownBackground;
            }
            const card = el.closest('.demo-card');
            const cardBackground = card ? card.querySelector('.card-bg') : null;
            if (cardBackground) return parseColor(getComputedStyle(cardBackground).backgroundColor) || slideBackground;
            const diagramNode = el.closest('.diagram-node');
            const nodeBackground = diagramNode?.querySelector(':scope > .diagram-node-bg');
            if (nodeBackground) {
              const color = parseColor(getComputedStyle(nodeBackground).backgroundColor);
              if (color && color[3] > 0) return color[3] < 1 ? composite(color, slideBackground) : color;
            }
            let current = el;
            while (current && current !== slide.parentElement) {
              const color = parseColor(getComputedStyle(current).backgroundColor);
              if (color && color[3] > 0) return color[3] < 1 ? composite(color, slideBackground) : color;
              if (current === slide) break;
              current = current.parentElement;
            }
            return slideBackground;
          };
          const contrastTargets = slide.querySelectorAll('[data-edit-kind="text"], [data-edit-layer="text"], [data-edit-layer="metric"]');
          for (const el of contrastTargets) {
            if (el.closest('[data-contrast-skip="true"]')) continue;
            if (!(el.innerText || '').trim()) continue;
            const style = getComputedStyle(el);
            const foreground = parseColor(style.color);
            const background = effectiveBackground(el);
            if (!foreground || !background) continue;
            let opacity = foreground[3] ?? 1;
            for (let current = el; current && current !== slide.parentElement; current = current.parentElement) {
              opacity *= Number.parseFloat(getComputedStyle(current).opacity) || 1;
              if (current === slide) break;
            }
            const renderedForeground = composite([foreground[0], foreground[1], foreground[2], opacity], background);
            const ratio = contrast(renderedForeground, background);
            const fontSize = Number.parseFloat(style.fontSize) || 0;
            const fontWeight = Number.parseInt(style.fontWeight, 10) || 400;
            const threshold = fontSize >= 28 || (fontSize >= 22 && fontWeight >= 700) ? 3 : 4.5;
            if (ratio + 0.02 < threshold) {
              issues.push({
                slot: 'text-contrast',
                element: el.className || el.tagName.toLowerCase(),
                parent: el.parentElement?.className || el.parentElement?.tagName.toLowerCase(),
                foreground: style.color,
                background: `rgba(${background.join(',')})`,
                ratio: Math.round(ratio * 100) / 100,
                threshold,
              });
            }
          }
          for (const el of slide.querySelectorAll(".el")) {
            if (el.dataset.editFit === "text") continue;
            if (el.dataset.overflowIntent === "clip") continue;
            if (el.matches('[data-visual-balance-ignore="true"]')) continue;
            const style = getComputedStyle(el);
            const intentionalClip = el.dataset.editKind === "visual"
              && ['hidden', 'clip'].includes(style.overflowX)
              && ['hidden', 'clip'].includes(style.overflowY);
            if (intentionalClip) continue;
            const excessWidth = el.scrollWidth - el.clientWidth;
            const excessHeight = el.scrollHeight - el.clientHeight;
            const overflowTolerance = el.matches('.scene, .scene-header, .scene-content') ? 12 : 3;
            const overflowX = excessWidth > overflowTolerance;
            const overflowY = excessHeight > overflowTolerance;
            if (overflowX || overflowY) issues.push({
              slot: 'element-overflow',
              element: el.className,
              overflowX,
              overflowY,
              excessWidth,
              excessHeight,
            });
          }
          for (const frame of slide.querySelectorAll('[data-visual-balance="content-bounds"]')) {
            const content = frame.closest('[data-content-area="true"]');
            if (!content) {
              issues.push({ slot: 'content-bounds-balance', reason: 'missing-content-area' });
              continue;
            }
            const candidates = [...frame.children].flatMap((child) => {
              if (child.matches('[data-edit-layout-only="true"]')) {
                return [...child.querySelectorAll('.el')].filter((root) => {
                  const parentRoot = root.parentElement?.closest('.el');
                  return !parentRoot || !frame.contains(parentRoot);
                });
              }
              if (child.matches('[data-auto-layout]')) {
                return [...child.children].filter((item) => item.matches('.el,[data-layout-item]'));
              }
              return [child];
            }).filter((child) => {
              if (child.matches('.diagram-connectors,[data-visual-balance-ignore]')) return false;
              const style = getComputedStyle(child);
              const rect = child.getBoundingClientRect();
              return style.display !== 'none'
                && style.visibility !== 'hidden'
                && Number.parseFloat(style.opacity) > 0.01
                && rect.width > 0.5
                && rect.height > 0.5;
            });
            if (!candidates.length) {
              issues.push({ slot: 'content-bounds-balance', reason: 'missing-visual-children' });
              continue;
            }
            const contentRect = content.getBoundingClientRect();
            const scaleX = content.offsetWidth ? contentRect.width / content.offsetWidth : 1;
            const scaleY = content.offsetHeight ? contentRect.height / content.offsetHeight : 1;
            const rects = candidates.map((candidate) => candidate.getBoundingClientRect());
            const visualLeft = Math.min(...rects.map((rect) => rect.left));
            const visualTop = Math.min(...rects.map((rect) => rect.top));
            const visualRight = Math.max(...rects.map((rect) => rect.right));
            const visualBottom = Math.max(...rects.map((rect) => rect.bottom));
            const leftGap = (visualLeft - contentRect.left) / scaleX;
            const topGap = (visualTop - contentRect.top) / scaleY;
            const rightGap = (contentRect.right - visualRight) / scaleX;
            const bottomGap = (contentRect.bottom - visualBottom) / scaleY;
            const horizontalGapDelta = Math.abs(leftGap - rightGap);
            const gapDelta = Math.abs(topGap - bottomGap);
            const centered = horizontalGapDelta <= 2 && gapDelta <= 2;
            const insideContent = leftGap >= -1 && topGap >= -1 && rightGap >= -1 && bottomGap >= -1;
            const runtimeBalanced = frame.dataset.visualBalanced === 'true';
            if (!centered || !insideContent || !runtimeBalanced) {
              issues.push({
                slot: 'content-bounds-balance',
                centered,
                insideContent,
                runtimeBalanced,
                leftGap: Math.round(leftGap * 10) / 10,
                topGap: Math.round(topGap * 10) / 10,
                rightGap: Math.round(rightGap * 10) / 10,
                bottomGap: Math.round(bottomGap * 10) / 10,
                horizontalGapDelta: Math.round(horizontalGapDelta * 10) / 10,
                gapDelta: Math.round(gapDelta * 10) / 10,
              });
            }
          }
          if (slide.dataset.layoutId === 'matrix-4quadrant') {
            const frame = slide.querySelector('[data-visual-balance="content-bounds"]');
            const title = frame?.querySelector('.prod-title');
            const bodyCandidates = frame
              ? [...frame.children].filter((child) => (
                child !== title
                && !child.matches('[data-visual-balance-ignore]')
                && getComputedStyle(child).display !== 'none'
                && getComputedStyle(child).visibility !== 'hidden'
              ))
              : [];
            const titleRect = title?.getBoundingClientRect();
            const bodyRects = bodyCandidates
              .map((child) => child.getBoundingClientRect())
              .filter((rect) => rect.width > 0.5 && rect.height > 0.5);
            if (!frame) {
              // Recipe-authored matrices own their balance through matrix-frame
              // and matrix-items; the legacy production frame contract is absent by design.
            } else if (!titleRect || !bodyRects.length) {
              issues.push({ slot: 'matrix-title-body-balance', reason: 'missing-title-or-body' });
            } else {
              const slideRect = slide.getBoundingClientRect();
              const scaleY = slide.offsetHeight ? slideRect.height / slide.offsetHeight : 1;
              const bodyTop = Math.min(...bodyRects.map((rect) => rect.top));
              const bodyBottom = Math.max(...bodyRects.map((rect) => rect.bottom));
              const groupTop = Math.min(titleRect.top, bodyTop);
              const groupBottom = Math.max(titleRect.bottom, bodyBottom);
              const gap = (bodyTop - titleRect.bottom) / scaleY;
              const centerDelta = (
                (groupTop + groupBottom) / 2 - (slideRect.top + slideRect.height / 2)
              ) / scaleY;
              if (gap < 40 || Math.abs(centerDelta) > 2) {
                issues.push({
                  slot: 'matrix-title-body-balance',
                  gap: Math.round(gap * 10) / 10,
                  centerDelta: Math.round(centerDelta * 10) / 10,
                  minimumGap: 40,
                  centerTolerance: 2,
                });
              }
            }
          }          for (const frame of slide.querySelectorAll('[data-content-frame="visual-balance"]')) {
            const slideRect = slide.getBoundingClientRect();
            const frameRect = frame.getBoundingClientRect();
            const expected = { x: (slideRect.left + slideRect.right) / 2, y: (slideRect.top + slideRect.bottom) / 2 };
            const frameCenter = { x: (frameRect.left + frameRect.right) / 2, y: (frameRect.top + frameRect.bottom) / 2 };
            const panelElements = [...frame.querySelectorAll(".ba-panel")];
            const panels = panelElements.map((panel) => panel.getBoundingClientRect());
            const axis = frame.querySelector(".ba-rail b")?.getBoundingClientRect();
            const near = (first, second, slidePixels = 1) => Math.abs(first - second) <= slidePixels * geometryScale;
            const centered = near(frameCenter.x, expected.x) && near(frameCenter.y, expected.y);
            const panelsBalanced = panels.length === 2
              && near(panels[0].top, panels[1].top)
              && near(panels[0].bottom, panels[1].bottom)
              && near((panels[0].top + panels[0].bottom) / 2, frameCenter.y)
              && near((panels[1].top + panels[1].bottom) / 2, frameCenter.y);
            const axisCentered = axis
              && near((axis.left + axis.right) / 2, frameCenter.x)
              && near((axis.top + axis.bottom) / 2, frameCenter.y);
            const contentFlow = panelElements.length === 2 && panelElements.every((panel) => {
              const panelRect = panel.getBoundingClientRect();
              const blocks = ['.ba-header', '.ba-subtitle', '.ba-signal', 'ul']
                .map((selector) => panel.querySelector(selector)?.getBoundingClientRect())
                .filter(Boolean);
              if (blocks.length !== 4) return false;
              const gaps = blocks.slice(1).map((block, index) => (block.top - blocks[index].bottom) / geometryScale);
              const edgeFit = near(blocks[0].top, panelRect.top, 2) && near(blocks.at(-1).bottom, panelRect.bottom, 2);
              return edgeFit && gaps.every((gap) => gap >= -1 && gap <= 24);
            });
            const density = frame.dataset.density;
            const fillRatio = Number.parseFloat(frame.dataset.fillRatio) || 1;
            const actualFillRatio = (frameRect.height / geometryScale) / 888;
            const fillCap = frame.dataset.autoFillCap !== 'soft' || Math.abs(actualFillRatio - fillRatio) <= 0.02;
            const samplePanel = panelElements[0];
            const titleSize = Number.parseFloat(getComputedStyle(samplePanel?.querySelector('.ba-header b')).fontSize) || 0;
            const subtitleSize = Number.parseFloat(getComputedStyle(samplePanel?.querySelector('.ba-subtitle')).fontSize) || 0;
            const itemSize = Number.parseFloat(getComputedStyle(samplePanel?.querySelector('li')).fontSize) || 0;
            const densityScale = density === 'low'
              ? titleSize >= 74 && subtitleSize >= 38 && itemSize >= 31
              : density === 'medium'
                ? titleSize >= 62 && subtitleSize >= 32 && itemSize >= 26
                : density === 'high'
                  ? titleSize >= 54 && subtitleSize >= 27 && itemSize >= 23
                  : false;
            if (!centered || !panelsBalanced || !axisCentered || !contentFlow || !densityScale || !fillCap) {
              issues.push({ slot: "visual-balance", centered, panelsBalanced, axisCentered: Boolean(axisCentered), contentFlow, density, densityScale, fillCap, fillRatio, actualFillRatio: Math.round(actualFillRatio * 100) / 100 });
            }
          }
          for (const frame of slide.querySelectorAll('[data-content-frame="radial-balance"]')) {
            const slideRect = slide.getBoundingClientRect();
            const frameRect = frame.getBoundingClientRect();
            const hub = frame.querySelector('.cycle-hub')?.getBoundingClientRect();
            const nodes = [...frame.querySelectorAll('.cycle-node')].map((node) => node.getBoundingClientRect());
            const arrows = [...frame.querySelectorAll('.cycle-connectors [data-cycle-arc][marker-end]')];
            const expectedNodeCount = Number.parseInt(frame.dataset.cycleNodeCount || '6', 10);
            const center = (rect) => ({ x: (rect.left + rect.right) / 2, y: (rect.top + rect.bottom) / 2 });
            const near = (first, second, slidePixels = 3) => Math.abs(first - second) <= slidePixels * geometryScale;
            const overlaps = (first, second) => first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top;
            const frameCenter = center(frameRect);
            const slideCenter = center(slideRect);
            const hubCenter = hub ? center(hub) : null;
            const nodeCenters = nodes.map(center);
            const nodeCentroid = nodeCenters.length ? {
              x: nodeCenters.reduce((sum, point) => sum + point.x, 0) / nodeCenters.length,
              y: nodeCenters.reduce((sum, point) => sum + point.y, 0) / nodeCenters.length,
            } : null;
            const hubSquare = hub ? near(hub.width, hub.height) : false;
            const hubBackground = frame.querySelector('.cycle-hub .diagram-node-bg');
            const hubRadiusValue = hubBackground ? getComputedStyle(hubBackground).borderTopLeftRadius : '0';
            const hubCircle = hub ? (hubRadiusValue.includes('%') ? Number.parseFloat(hubRadiusValue) >= 49 : Number.parseFloat(hubRadiusValue) >= (hub.width / geometryScale) * 0.45) : false;
            const nodeCircles = nodes.every((node) => near(node.width, node.height));
            const radii = hubCenter ? nodeCenters.map((point) => Math.hypot(point.x - hubCenter.x, point.y - hubCenter.y)) : [];
            const radialSpread = radii.length ? Math.max(...radii) - Math.min(...radii) : Infinity;
            const equalRadius = radialSpread <= 3 * geometryScale;
            const circleRing = frame.querySelector('.cycle-ring');
            const callouts = [...frame.querySelectorAll('.cycle-callout')].map((callout) => callout.getBoundingClientRect());
            const calloutSpan = callouts.length ? (Math.max(...callouts.map((item) => item.right)) - Math.min(...callouts.map((item) => item.left))) / frameRect.width : 0;
            const pairOverlap = nodes.some((node, index) => nodes.slice(index + 1).some((other) => overlaps(node, other)));
            const pass = Boolean(hub)
              && nodes.length === expectedNodeCount
              && arrows.length === expectedNodeCount
              && Boolean(circleRing)
              && frame.dataset.cycleGeometry === 'circle'
              && near(frameCenter.x, slideCenter.x)
              && near(frameCenter.y, slideCenter.y)
              && near(hubCenter.x, frameCenter.x)
              && near(hubCenter.y, frameCenter.y)
              && near(nodeCentroid.x, hubCenter.x)
              && near(nodeCentroid.y, hubCenter.y)
              && hubSquare
              && hubCircle
              && callouts.length === expectedNodeCount
              && calloutSpan >= 0.9
              && nodeCircles
              && equalRadius
              && !pairOverlap;
            if (!pass) issues.push({
              slot: 'radial-balance',
              hub: Boolean(hub),
              nodes: nodes.length,
              arrows: arrows.length,
              circleRing: Boolean(circleRing),
              hubSquare,
              hubCircle,
              callouts: callouts.length,
              calloutSpan: Math.round(calloutSpan * 100) / 100,
              nodeCircles,
              equalRadius,
              radialSpread: Math.round(radialSpread / geometryScale),
              pairOverlap,
            });
          }
          const orphanAdjustments = [...slide.querySelectorAll('[data-ai-orphan-adjusted-font]')].map((el) => ({
            element: el.className || el.tagName,
            originalFontSize: Number.parseFloat(el.dataset.aiOrphanOriginalFont),
            adjustedFontSize: Number.parseFloat(el.dataset.aiOrphanAdjustedFont),
            text: (el.innerText || '').trim().slice(0, 80),
          }));
          return {
            layout: slide.dataset.layoutId,
            density: slide.querySelector('.ba-frame')?.dataset.density || null,
            orphanAdjustments,
            issues,
          };
        });
        if (selectionDrift !== null && selectionDrift > 0.5) {
          qa.issues.push({
            slot: 'edit-selection-geometry-drift',
            element: selectionTargetName,
            drift: Number.isFinite(selectionDrift) ? Math.round(selectionDrift * 10) / 10 : 'node-count-changed',
          });
        }
        if (qa.issues.length) report.issues.push({ theme, slide: index + 1, layout: qa.layout, issues: qa.issues });
        if (qa.orphanAdjustments.length) {
          report.orphanAdjustments.push({
            theme,
            slide: index + 1,
            layout: qa.layout,
            adjustments: qa.orphanAdjustments,
          });
        }
        if (qa.density && Object.hasOwn(report.densityCoverage, qa.density)) report.densityCoverage[qa.density] += 1;
        await page.evaluate(() => {
          window.EditMode?.toggle(false);
          // Static captures must sample the settled authored frame. The formal
          // presentation runtime intentionally starts a projection reveal on
          // mode entry, so disable it for this report-only screenshot pass;
          // qa_html_motion_runtime.cjs covers the actual animation contract.
          window.MotionPreview?.setEnabled(false, false);
          const toolbar = document.getElementById('bar');
          const hint = document.getElementById('hint');
          if (toolbar) toolbar.style.visibility = 'hidden';
          if (hint) hint.style.visibility = 'hidden';
        });
        // Collapsing the editor sidebar triggers one player fit pass.  Waiting for
        // two frames prevents a screenshot from mixing the pre-fit and post-fit
        // stage transforms on dense slides.
        await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        await page.screenshot({ path: path.join(outDir, `slide-${String(index + 1).padStart(3, "0")}-${qa.layout}.jpg`), type: "jpeg", quality: 82 });
        report.slides += 1;
      }
      const afterMarkup = await fs.readFile(htmlPath, "utf8");
      sourceRecord.afterSha256 = crypto.createHash("sha256").update(afterMarkup).digest("hex");
      sourceRecord.unchanged = sourceRecord.sha256 === sourceRecord.afterSha256;
      report.sourceImmutability.checked += 1;
      if (sourceRecord.unchanged) report.sourceImmutability.unchanged += 1;
      else report.sourceImmutability.violations.push(file);
      await page.close();
      console.log(JSON.stringify({ theme, slides: limit }));
    }
  } finally {
    // Persist the completed QA result before asking the browser process to
    // terminate.  On Windows, a headless Chrome child can occasionally linger
    // after all screenshots are written; the report must not be lost merely
    // because process teardown is slow.
    await fs.mkdir(path.dirname(options.report), { recursive: true });
    await fs.writeFile(options.report, JSON.stringify(report, null, 2) + "\n", "utf8");
    console.log(JSON.stringify({ files: report.files, slides: report.slides, issues: report.issues.length }));
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
