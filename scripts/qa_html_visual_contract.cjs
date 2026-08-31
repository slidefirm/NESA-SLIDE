const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const { pathToFileURL } = require("node:url");
const { loadPlaywright, browserExecutable } = require("./playwright_runtime.cjs");

const PROJECT_ROOT = path.resolve(__dirname, "..");

function portableReportPath(value) {
  const resolved = path.resolve(value);
  const relative = path.relative(PROJECT_ROOT, resolved);
  if (relative === "") return ".";
  if (relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)) {
    return relative.split(path.sep).join("/");
  }
  return resolved.split(path.sep).join("/");
}

function argsOf(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (key === "--file") { out.file = value; i += 1; }
    else if (key === "--report") { out.report = value; i += 1; }
  }
  if (!out.file || !out.report) throw new Error("--file and --report are required");
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const { chromium } = loadPlaywright();
  const htmlPath = path.resolve(options.file);
  const markup = await fs.readFile(htmlPath, "utf8");
  const baseHref = pathToFileURL(`${path.dirname(htmlPath)}${path.sep}`).href;
  const markupWithBase = markup.replace(/<head>/i, `<head><base href="${baseHref}">`);
  const executablePath = browserExecutable();
  if (!process.env.BROWSER_CDP_URL && !executablePath) throw new Error("No Chrome or Edge executable found for visual contract QA");
  const browser = process.env.BROWSER_CDP_URL
    ? await chromium.connectOverCDP(process.env.BROWSER_CDP_URL)
    : await chromium.launch({ headless: true, executablePath });
  const report = {
    file: portableReportPath(htmlPath),
    fileSha256: crypto.createHash("sha256").update(markup).digest("hex"),
    slides: 0,
    issues: [],
    checks: { centerAxis: 0, centerAxisMembers: 0, alignmentInheritance: 0, circleNumberExceptions: 0, moduleInteriorAlignments: 0, processNumberAxis: 0, timelineSpacing: 0, timelineTextFlow: 0, accentSurface: 0, noneSurface: 0, fontFloor: 0, pageHierarchy: 0, moduleHierarchy: 0, moduleContainment: 0 },
  };
  try {
    const page = await browser.newPage({ viewport: { width: 960, height: 540 }, deviceScaleFactor: 1 });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.setContent(markupWithBase, { waitUntil: "domcontentloaded", timeout: 120000 });
    await Promise.race([
      page.evaluate(() => document.fonts?.ready),
      page.waitForTimeout(3000),
    ]);
    await page.waitForFunction(
      () => document.documentElement.dataset.layoutReady === "true",
      null,
      { timeout: 120000 },
    );
    await page.addStyleTag({ content: "#stage > .slide { display: block !important; visibility: visible !important; opacity: 1 !important; }" });
    const result = await page.evaluate(() => {
      const issues = [];
      let centerAxis = 0;
      let centerAxisMembers = 0;
      let alignmentInheritance = 0;
      let circleNumberExceptions = 0;
      let moduleInteriorAlignments = 0;
      let processNumberAxis = 0;
      let timelineSpacing = 0;
      let timelineTextFlow = 0;
      let accentSurface = 0;
      let noneSurface = 0;
      let fontFloor = 0;
      let pageHierarchy = 0;
      let moduleHierarchy = 0;
      let moduleContainment = 0;
      const round = (value) => Math.round(value * 100) / 100;
      const color = (value) => {
        const match = String(value || "").match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/i);
        return match ? [Number(match[1]), Number(match[2]), Number(match[3]), match[4] == null ? 1 : Number(match[4])] : null;
      };
      const sameColor = (left, right) => {
        const a = color(left), b = color(right);
        return Boolean(a && b && a.slice(0, 3).every((value, index) => Math.abs(value - b[index]) <= 1));
      };
      const resolvedColor = (element, variable, property) => {
        const probe = document.createElement("span");
        const rawValue = getComputedStyle(element).getPropertyValue(variable).trim();
        probe.style.setProperty(property === "backgroundColor" ? "background-color" : property, rawValue || `var(${variable})`);
        probe.style.position = "absolute";
        probe.style.visibility = "hidden";
        element.appendChild(probe);
        const value = getComputedStyle(probe)[property];
        probe.remove();
        return value;
      };
      const visible = (element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
      };
      const fontSize = (element) => Number.parseFloat(getComputedStyle(element).fontSize || "0");
      const glyphRect = (element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        const rect = range.getBoundingClientRect();
        range.detach?.();
        return rect;
      };
      const containsRect = (outer, inner, tolerance = 1) => (
        inner.left >= outer.left - tolerance
        && inner.right <= outer.right + tolerance
        && inner.top >= outer.top - tolerance
        && inner.bottom <= outer.bottom + tolerance
      );
      const pageTitleSelector = [
        '.prod-title',
        '[class*="cover-"][class*="-title"]:not([class*="subtitle"])',
        '.statement-center-headline',
        '.statement-focus-quote',
        '[class*="chapter-"][class*="-title"]',
        '.closing-title',
        '.toc-image-title',
      ].join(',');
      const moduleTitleSelector = [
        ':scope > b[data-edit-layer="text"]',
        ':scope > .metric-card-label',
        ':scope > .metric-stat-label',
        ':scope > .swot-label',
        ':scope > .price-name',
        ':scope > .diagram-node-title',
        ':scope > .org-title',
        ':scope > .pyramid-title',
      ].join(',');
      const moduleBodySelector = [
        ':scope > p[data-edit-layer="text"]',
        ':scope .metric-card-note',
        ':scope .metric-stat-note',
        ':scope .org-body',
        ':scope .pyramid-body',
        ':scope .swot-card li',
        ':scope.price-card li b[data-edit-layer="text"]',
      ].join(',');
      const slides = [...document.querySelectorAll("#stage > .slide")];
      for (const slide of slides) {
        const content = slide.querySelector('.content[data-content-area="true"]');
        if (!content) continue;
        const contentRect = content.getBoundingClientRect();
        const textNodes = [...slide.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')]
          .filter((element) => visible(element) && String(element.textContent || '').trim());
        for (const textNode of textNodes) {
          fontFloor += 1;
          const actual = fontSize(textNode);
          if (actual < 35.9) {
            issues.push({
              slide: slide.dataset.pageNumber,
              contract: 'font-floor',
              issue: 'text-below-36px',
              element: textNode.className || textNode.tagName,
              actual: round(actual),
            });
          }
        }
        const pageTitle = [...slide.querySelectorAll(pageTitleSelector)].filter(visible)
          .sort((left, right) => fontSize(right) - fontSize(left))[0];
        const pageBodies = [...slide.querySelectorAll('p[data-edit-layer="text"],li[data-edit-layer="text"]')]
          .filter((element) => visible(element) && !element.closest(pageTitleSelector));
        if (pageTitle && pageBodies.length) {
          pageHierarchy += 1;
          const titlePx = fontSize(pageTitle);
          const bodyPx = Math.max(...pageBodies.map(fontSize));
          if (titlePx < bodyPx + 5.9) {
            issues.push({
              slide: slide.dataset.pageNumber,
              contract: 'page-type-hierarchy',
              issue: 'page-title-insufficient-contrast',
              titlePx: round(titlePx),
              bodyPx: round(bodyPx),
            });
          }
        }
        for (const moduleRoot of slide.querySelectorAll('.el[data-edit-structure="module"]')) {
          if (!visible(moduleRoot)) continue;
          const titleNodes = [...moduleRoot.querySelectorAll(moduleTitleSelector)].filter(visible);
          const bodyNodes = [...moduleRoot.querySelectorAll(moduleBodySelector)].filter(visible);
          if (titleNodes.length && bodyNodes.length) {
            moduleHierarchy += 1;
            const titlePx = Math.max(...titleNodes.map(fontSize));
            const bodyPx = Math.max(...bodyNodes.map(fontSize));
            if (titlePx < bodyPx + 5.9) {
              issues.push({
                slide: slide.dataset.pageNumber,
                contract: 'module-type-hierarchy',
                issue: 'module-title-insufficient-contrast',
                element: moduleRoot.className || moduleRoot.tagName,
                titlePx: round(titlePx),
                bodyPx: round(bodyPx),
              });
            }
          }
          if (moduleRoot.dataset.overflowIntent === 'bleed') continue;
          const moduleRect = moduleRoot.getBoundingClientRect();
          for (const child of moduleRoot.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')) {
            if (!visible(child) || child.closest('[data-overflow-intent="bleed"]')) continue;
            const childRect = glyphRect(child);
            if (childRect.width <= 0 || childRect.height <= 0) continue;
            moduleContainment += 1;
            if (!containsRect(moduleRect, childRect)) {
              issues.push({
                slide: slide.dataset.pageNumber,
                contract: 'module-containment',
                issue: 'text-glyph-outside-module',
                element: child.className || child.tagName,
                overflow: {
                  left: round(Math.max(0, moduleRect.left - childRect.left)),
                  right: round(Math.max(0, childRect.right - moduleRect.right)),
                  top: round(Math.max(0, moduleRect.top - childRect.top)),
                  bottom: round(Math.max(0, childRect.bottom - moduleRect.bottom)),
                },
              });
            }
          }
        }
        const pageAlignment = slide.dataset.pageHorizontalAlign;
        if (!['left', 'center', 'right'].includes(pageAlignment)) {
          issues.push({ slide: slide.dataset.pageNumber, contract: 'page-alignment', issue: 'missing-page-horizontal-alignment', actual: pageAlignment || null });
        }
        const alignmentTargets = [...slide.querySelectorAll(
          '.el[data-edit-composite],.el[data-edit-kind="text"],[data-edit-layer="text"],[data-edit-layer="metric"]'
        )].filter(visible);
        for (const target of alignmentTargets) {
          const isCircleNumber = target.classList.contains('circle-number-metric');
          const actualAlignment = target.dataset.editHorizontalAlign;
          const actualSource = target.dataset.editAlignmentSource;
          const moduleRoot = target.closest('.el[data-edit-structure="module"]');
          const moduleInteriorAlignment = moduleRoot?.dataset.moduleInteriorAlign;
          const isModuleInterior = actualSource === 'module-interior';
          const validModuleInterior = isModuleInterior
            && target !== moduleRoot
            && ['left', 'center', 'right'].includes(moduleInteriorAlignment);
          const expectedAlignment = isCircleNumber
            ? 'center'
            : isModuleInterior
            ? moduleInteriorAlignment
            : pageAlignment;
          const expectedSource = isCircleNumber
            ? 'circle-number-exception'
            : isModuleInterior
            ? 'module-interior'
            : 'page-title';
          const computedAlignment = getComputedStyle(target).textAlign;
          if (isCircleNumber) circleNumberExceptions += 1;
          else if (isModuleInterior) moduleInteriorAlignments += 1;
          else alignmentInheritance += 1;
          if (
            (isModuleInterior && !validModuleInterior)
            || actualAlignment !== expectedAlignment
            || actualSource !== expectedSource
            || computedAlignment !== expectedAlignment
          ) {
            issues.push({
              slide: slide.dataset.pageNumber,
              contract: 'page-alignment',
              issue: isCircleNumber
                ? 'circle-number-exception-drift'
                : isModuleInterior
                ? 'module-interior-alignment-drift'
                : 'title-alignment-inheritance-drift',
              element: target.className || target.tagName,
              expectedAlignment,
              actualAlignment: actualAlignment || null,
              expectedSource,
              actualSource: actualSource || null,
              computedAlignment,
            });
          }
        }
        for (const node of slide.querySelectorAll('.sequence-process-node')) {
          const number = node.querySelector(':scope > .circle-number-metric');
          if (!visible(node) || !number || !visible(number)) continue;
          processNumberAxis += 1;
          const nodeRect = node.getBoundingClientRect();
          const numberRect = number.getBoundingClientRect();
          const delta = Math.abs((numberRect.left + numberRect.width / 2) - (nodeRect.left + nodeRect.width / 2));
          if (number.dataset.editAlignContract !== 'parent-center-axis' || delta > 3) {
            issues.push({
              slide: slide.dataset.pageNumber,
              contract: 'process-number-center-axis',
              issue: 'process-number-center-drift',
              element: node.className || node.tagName,
              delta: round(delta),
              alignmentContract: number.dataset.editAlignContract || null,
            });
          }
        }
        const centerAreas = [...slide.querySelectorAll('.title-flow-stack[data-layout-flow-align="center"]')].filter(visible);
        for (const centerArea of centerAreas) {
          centerAxis += 1;
          const areaRect = centerArea.getBoundingClientRect();
          const expectedCenter = areaRect.left + areaRect.width / 2;
          const members = [...centerArea.querySelectorAll(':scope > .el')].filter((member) => (
            member.dataset.editAlignContract === 'center-axis'
            || member.dataset.editHorizontalAlign === 'center'
            || member.dataset.editKind === 'visual'
          ));
          const visibleMembers = members.filter(visible);
          const visibleChildren = [...centerArea.querySelectorAll(":scope > .el")].filter(visible);
          centerAxisMembers += visibleMembers.length;
          if (visibleMembers.length !== visibleChildren.length) {
            issues.push({
              slide: slide.dataset.pageNumber,
              contract: "center-axis",
              issue: "missing-centered-member-contract",
              members: visibleMembers.length,
              children: visibleChildren.length,
            });
          }
          if (["cover-center-title-edge-decor", "title-center"].includes(slide.dataset.layoutId)) {
            const contentCenter = contentRect.left + contentRect.width / 2;
            const containerDelta = Math.abs(expectedCenter - contentCenter);
            if (containerDelta > 3) {
              issues.push({ slide: slide.dataset.pageNumber, contract: "center-axis", issue: "center-container-drift", delta: round(containerDelta) });
            }
          }
          for (const member of visibleMembers) {
            const rect = member.getBoundingClientRect();
            const delta = Math.abs(rect.left + rect.width / 2 - expectedCenter);
            if (delta > 3) {
              issues.push({ slide: slide.dataset.pageNumber, contract: "center-axis", issue: "center-drift", element: member.className, delta: round(delta) });
            }
          }
        }
        for (const timeline of slide.querySelectorAll('.sequence-timeline')) {
          if (!visible(timeline)) continue;
          const milestones = [...timeline.querySelectorAll(':scope > .timeline-milestone')].filter(visible);
          if (milestones.length < 2) continue;
          const centers = milestones.map((milestone) => {
            const rect = milestone.getBoundingClientRect();
            return rect.left + rect.width / 2;
          });
          const expectedStep = (centers[centers.length - 1] - centers[0]) / (centers.length - 1);
          let spacingDelta = 0;
          for (let index = 1; index < centers.length; index += 1) {
            spacingDelta = Math.max(spacingDelta, Math.abs((centers[index] - centers[index - 1]) - expectedStep));
          }
          const axis = timeline.querySelector(':scope > .timeline-axis');
          const axisRect = axis && visible(axis) ? axis.getBoundingClientRect() : null;
          const axisDelta = axisRect
            ? Math.max(Math.abs(axisRect.left - centers[0]), Math.abs(axisRect.right - centers[centers.length - 1]))
            : 0;
          timelineSpacing += 1;
          if (spacingDelta > 3 || axisDelta > 3) {
            issues.push({
              slide: slide.dataset.pageNumber,
              contract: "timeline-milestones",
              issue: "uneven-milestone-distribution",
              spacingDelta: round(spacingDelta),
              axisDelta: round(axisDelta),
              milestoneCount: milestones.length,
            });
          }
          for (const milestone of milestones) {
            const textNodes = [...milestone.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')]
              .filter(visible)
              .sort((left, right) => left.getBoundingClientRect().top - right.getBoundingClientRect().top);
            const textRects = textNodes.map((node) => node.getBoundingClientRect());
            const textOverlap = textRects.reduce((maximum, rect, index) => {
              if (index === 0) return maximum;
              return Math.max(maximum, Math.min(textRects[index - 1].bottom, rect.bottom) - Math.max(textRects[index - 1].top, rect.top));
            }, 0);
            const marker = milestone.querySelector(':scope > i');
            const markerRect = marker && visible(marker) ? marker.getBoundingClientRect() : null;
            const textTop = textRects.length ? textRects[0].top : 0;
            const textBottom = textRects.length ? textRects[textRects.length - 1].bottom : 0;
            const markerOverlap = markerRect
              ? Math.max(0, Math.min(textBottom, markerRect.bottom) - Math.max(textTop, markerRect.top))
              : 0;
            timelineTextFlow += 1;
            if (textOverlap > 1 || markerOverlap > 1) {
              issues.push({
                slide: slide.dataset.pageNumber,
                contract: "timeline-milestones",
                issue: "milestone-text-overlap",
                textOverlap: round(textOverlap),
                markerOverlap: round(markerOverlap),
              });
            }
          }
        }
        for (const root of slide.querySelectorAll('[data-visual-surface-role="accent"]')) {
          if (!visible(root)) continue;
          const bg = root.querySelector(":scope > .diagram-node-bg");
          const inkNodes = [...root.querySelectorAll("span, b, p, em")].filter(visible);
          const expectedBg = resolvedColor(root, "--accent", "backgroundColor");
          const expectedInk = resolvedColor(root, "--accent-text", "color");
          const bgStyle = bg ? getComputedStyle(bg) : null;
          accentSurface += 1;
          if (!bg || !sameColor(bgStyle.backgroundColor, expectedBg) || bgStyle.backgroundImage !== "none") {
            issues.push({ slide: slide.dataset.pageNumber, contract: "accent-surface", issue: "surface-ink-pair-background-drift", element: root.className, background: bgStyle?.background || null, expectedBackground: expectedBg });
          }
          for (const inkNode of inkNodes) {
            const actual = getComputedStyle(inkNode).color;
            if (!sameColor(actual, expectedInk)) {
              issues.push({ slide: slide.dataset.pageNumber, contract: "accent-surface", issue: "surface-ink-pair-foreground-drift", element: inkNode.className || inkNode.tagName, actual, expected: expectedInk });
            }
          }
        }
        for (const root of slide.querySelectorAll('[data-visual-surface-role="none"]')) {
          if (!visible(root)) continue;
          const bg = root.querySelector(":scope > .diagram-node-bg");
          const bgStyle = bg ? getComputedStyle(bg) : null;
          const background = color(bgStyle?.backgroundColor);
          const borderWidths = bgStyle
            ? [bgStyle.borderTopWidth, bgStyle.borderRightWidth, bgStyle.borderBottomWidth, bgStyle.borderLeftWidth]
            : [];
          noneSurface += 1;
          if (
            !bg
            || !background
            || background[3] !== 0
            || bgStyle.backgroundImage !== "none"
            || borderWidths.some((width) => Number.parseFloat(width) !== 0)
            || bgStyle.boxShadow !== "none"
          ) {
            issues.push({
              slide: slide.dataset.pageNumber,
              contract: "none-surface",
              issue: "unexpected-surface-paint",
              element: root.className,
              background: bgStyle?.background || null,
              borderWidths,
              boxShadow: bgStyle?.boxShadow || null,
            });
          }
        }
      }
      return { slides: slides.length, issues, centerAxis, centerAxisMembers, alignmentInheritance, circleNumberExceptions, moduleInteriorAlignments, processNumberAxis, timelineSpacing, timelineTextFlow, accentSurface, noneSurface, fontFloor, pageHierarchy, moduleHierarchy, moduleContainment };
    });
    report.slides = result.slides;
    report.issues.push(...result.issues);
    report.checks.centerAxis = result.centerAxis;
    report.checks.centerAxisMembers = result.centerAxisMembers;
    report.checks.alignmentInheritance = result.alignmentInheritance;
    report.checks.circleNumberExceptions = result.circleNumberExceptions;
    report.checks.moduleInteriorAlignments = result.moduleInteriorAlignments;
    report.checks.processNumberAxis = result.processNumberAxis;
    report.checks.timelineSpacing = result.timelineSpacing;
    report.checks.timelineTextFlow = result.timelineTextFlow;
    report.checks.accentSurface = result.accentSurface;
    report.checks.noneSurface = result.noneSurface;
    report.checks.fontFloor = result.fontFloor;
    report.checks.pageHierarchy = result.pageHierarchy;
    report.checks.moduleHierarchy = result.moduleHierarchy;
    report.checks.moduleContainment = result.moduleContainment;
    report.status = report.issues.length ? "fail" : "pass";
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(report, null, 2));
    process.exitCode = report.status === "pass" ? 0 : 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
