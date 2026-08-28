const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");
const JSZip = require("jszip");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--html") out.html = argv[++index];
    else if (argv[index] === "--output") out.output = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--sentinel") out.sentinel = argv[++index];
  }
  if (!out.html || !out.output || !out.report) {
    throw new Error("--html, --output and --report are required");
  }
  return out;
}

function decodeXml(value) {
  return String(value || "")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function safeName(value, fallback) {
  const normalized = String(value || "")
    .normalize("NFKC")
    .replace(/[^\p{L}\p{N}_-]+/gu, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
  return normalized || fallback;
}

function rotationDelta(actual, expected) {
  const raw = Math.abs((actual || 0) - (expected || 0)) % 360;
  return Math.min(raw, 360 - raw);
}

function nativePositionAudit(manifest, slideXml) {
  const emuPerCssPixel = 6350;
  const actualSlides = slideXml.map((xml) => {
    const objects = new Map();
    const collect = (pattern, kind) => {
      let match = null;
      while ((match = pattern.exec(xml))) {
        const block = match[1];
        const nameMatch = block.match(/<p:cNvPr\b[^>]*\bname="([^"]*)"/);
        const descriptionMatch = block.match(/<p:cNvPr\b[^>]*\bdescr="([^"]*)"/);
        const xfrmMatch = block.match(/<a:xfrm\b([^>]*)>([\s\S]*?)<\/a:xfrm>/);
        if (!nameMatch || !xfrmMatch) continue;
        const offset = xfrmMatch[2].match(/<a:off\b[^>]*\bx="(-?\d+)"[^>]*\by="(-?\d+)"/);
        const extent = xfrmMatch[2].match(/<a:ext\b[^>]*\bcx="(-?\d+)"[^>]*\bcy="(-?\d+)"/);
        if (!offset || !extent) continue;
        const rotation = xfrmMatch[1].match(/\brot="(-?\d+)"/);
        objects.set(decodeXml(nameMatch[1]), {
          left: Number(offset[1]) / emuPerCssPixel,
          top: Number(offset[2]) / emuPerCssPixel,
          width: Number(extent[1]) / emuPerCssPixel,
          height: Number(extent[2]) / emuPerCssPixel,
          rotation: rotation ? Number(rotation[1]) / 60000 : 0,
          kind,
          description: descriptionMatch ? decodeXml(descriptionMatch[1]) : "",
        });
      }
    };
    collect(/<p:sp>([\s\S]*?)<\/p:sp>/g, "shape");
    collect(/<p:pic>([\s\S]*?)<\/p:pic>/g, "picture");
    return objects;
  });
  const deltas = [];
  const rotationDeltas = [];
  const missing = [];
  let expected = 0;
  let matched = 0;
  let delegated = 0;
  (manifest?.slides || []).forEach((slide, slideIndex) => {
    const actual = actualSlides[slideIndex] || new Map();
    (slide.elements || []).forEach((element) => {
      expected += 1;
      const name = safeName(element.name, `element-${slideIndex + 1}`);
      const found = actual.get(name);
      if (!found) {
        if ([...actual.keys()].some((actualName) => actualName.startsWith(name + '-'))) {
          delegated += 1;
          return;
        }
        missing.push({ slide: slideIndex + 1, name });
        return;
      }
      matched += 1;
      const source = element.position || {};
      deltas.push(
        Math.abs(found.left - Number(source.left || 0)),
        Math.abs(found.top - Number(source.top || 0)),
        Math.abs(found.width - Number(source.width || 0)),
        Math.abs(found.height - Number(source.height || 0)),
      );
      rotationDeltas.push(rotationDelta(found.rotation, Number(source.rotation || 0)));
    });
  });
  const sorted = deltas.slice().sort((a, b) => a - b);
  const percentile = sorted.length ? sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))] : null;
  return {
    coordinateSystem: manifest?.coordinateSystem || null,
    expectedObjects: expected,
    matchedObjects: matched,
    delegatedObjects: delegated,
    missingObjects: missing.length,
    missing: missing.slice(0, 20),
    maxDeltaPx: deltas.length ? Math.max(...deltas) : null,
    p95DeltaPx: percentile,
    maxRotationDeltaDegrees: rotationDeltas.length ? Math.max(...rotationDeltas) : null,
  };
}
function nativeTextLayoutAudit(manifest, slideXml) {
  const actualSlides = slideXml.map((xml) => {
    const blocks = new Map();
    const shapePattern = /<p:sp>([\s\S]*?)<\/p:sp>/g;
    let shapeMatch = null;
    while ((shapeMatch = shapePattern.exec(xml))) {
      const block = shapeMatch[1];
      const nameMatch = block.match(/<p:cNvPr\b[^>]*\bname="([^"]*)"/);
      if (nameMatch) blocks.set(decodeXml(nameMatch[1]), block);
    }
    return blocks;
  });
  const wideEllipseText = [];
  const singleLineWrapFailures = [];
  let textObjects = 0;
  let singleLineObjects = 0;
  (manifest?.slides || []).forEach((slide, slideIndex) => {
    const actual = actualSlides[slideIndex] || new Map();
    (slide.elements || []).forEach((element) => {
      if (!String(element.text || '').trim()) return;
      textObjects += 1;
      const source = element.position || {};
      const width = Math.max(1, Number(source.width || 1));
      const height = Math.max(1, Number(source.height || 1));
      const ratio = Math.max(width, height) / Math.min(width, height);
      if (element.shape === 'ellipse' && ratio > 1.2) {
        wideEllipseText.push({ slide: slideIndex + 1, name: element.name, ratio });
      }
      if (element.singleLine === true) {
        singleLineObjects += 1;
        const name = safeName(element.name, `element-${slideIndex + 1}`);
        const block = actual.get(name) || '';
        if (!/<a:bodyPr\b[^>]*\bwrap="none"/.test(block)) {
          singleLineWrapFailures.push({ slide: slideIndex + 1, name });
        }
      }
    });
  });
  return {
    textObjects,
    singleLineObjects,
    wideEllipseText: wideEllipseText.slice(0, 20),
    singleLineWrapFailures: singleLineWrapFailures.slice(0, 20),
    pass: wideEllipseText.length === 0 && singleLineWrapFailures.length === 0,
  };
}

function svgTextProjectionAudit(manifest, slideXml) {
  const actualSlides = slideXml.map((xml) => {
    const blocks = new Map();
    const shapePattern = /<p:sp>([\s\S]*?)<\/p:sp>/g;
    let shapeMatch = null;
    while ((shapeMatch = shapePattern.exec(xml))) {
      const block = shapeMatch[1];
      const nameMatch = block.match(/<p:cNvPr\b[^>]*\bname="([^"]*)"/);
      if (nameMatch) blocks.set(decodeXml(nameMatch[1]), block);
    }
    return blocks;
  });
  const expected = [
    { slideId: "s7", text: "100", anchor: "end" },
    { slideId: "s7", text: "R1", anchor: "middle" },
    { slideId: "s7", text: "指標值（0–100）", anchor: "start" },
  ];
  const targets = expected.map((expectation) => {
    const slideIndex = (manifest?.slides || []).findIndex((slide) => slide.id === expectation.slideId);
    const slide = slideIndex >= 0 ? manifest.slides[slideIndex] : null;
    const element = (slide?.elements || []).find((candidate) => candidate.text === expectation.text);
    const name = safeName(element?.name, `missing-${expectation.slideId}`);
    const block = slideIndex >= 0 ? (actualSlides[slideIndex]?.get(name) || "") : "";
    const metrics = element?.svgTextMetrics || {};
    const manifestChecks = {
      found: Boolean(element),
      projection: element?.svgTextProjection === "metrics",
      singleLine: element?.singleLine === true && element?.renderedLineCount === 1,
      fit: element?.fit === "none",
      anchor: element?.svgTextAnchor === expectation.anchor,
      safeWidth: Number(metrics.safeWidth || 0) > Number(metrics.measuredWidth || 0),
      positiveStageWidth: Number(element?.position?.width || 0) > 0,
    };
    const xmlChecks = {
      nonWrapping: /<a:bodyPr\b[^>]*\bwrap="none"/.test(block),
      noShrinkAutofit: !/<a:normAutofit\b/.test(block),
    };
    return {
      ...expectation,
      name,
      width: element?.position?.width || 0,
      measuredWidth: metrics.measuredWidth || 0,
      safeWidth: metrics.safeWidth || 0,
      manifestChecks,
      xmlChecks,
      pass: Object.values(manifestChecks).every(Boolean) && Object.values(xmlChecks).every(Boolean),
    };
  });
  return {
    targets,
    pass: targets.length === expected.length && targets.every((target) => target.pass),
  };
}

function semanticPictureAudit(positionManifest, slideXml) {
  const emuPerCssPixel = 6350;
  const actualPictures = [];
  slideXml.forEach((xml, slideIndex) => {
    const pattern = /<p:pic>([\s\S]*?)<\/p:pic>/g;
    let match = null;
    while ((match = pattern.exec(xml))) {
      const block = match[1];
      const nameMatch = block.match(/<p:cNvPr\b[^>]*\bname="([^"]*)"/);
      const descriptionMatch = block.match(/<p:cNvPr\b[^>]*\bdescr="([^"]*)"/);
      const xfrmMatch = block.match(/<a:xfrm\b[^>]*>([\s\S]*?)<\/a:xfrm>/);
      const offset = xfrmMatch?.[1].match(/<a:off\b[^>]*\bx="(-?\d+)"[^>]*\by="(-?\d+)"/);
      const extent = xfrmMatch?.[1].match(/<a:ext\b[^>]*\bcx="(-?\d+)"[^>]*\bcy="(-?\d+)"/);
      actualPictures.push({
        slide: slideIndex + 1,
        name: nameMatch ? decodeXml(nameMatch[1]) : "",
        description: descriptionMatch ? decodeXml(descriptionMatch[1]) : "",
        position: offset && extent ? {
          left: Number(offset[1]) / emuPerCssPixel,
          top: Number(offset[2]) / emuPerCssPixel,
          width: Number(extent[1]) / emuPerCssPixel,
          height: Number(extent[2]) / emuPerCssPixel,
        } : null,
      });
    }
  });
  const expected = (positionManifest?.slides || []).flatMap((slide, slideIndex) => (
    (slide.elements || []).filter((element) => element.kind === "image").map((element) => ({
      slide: slideIndex + 1,
      slideId: slide.id,
      name: safeName(element.name, `semantic-${slideIndex + 1}`),
      alt: element.alt || "",
      fit: element.fit || "",
      position: element.position || {},
    }))
  ));
  const dom = positionManifest?.semanticDom || [];
  const manifestDomMismatches = expected.filter((element) => !dom.some((image) => (
    image.slideId === element.slideId
    && image.alt === element.alt
    && image.cropBehavior
    && image.focalRegion
    && image.source
    && image.sha256
    && image.staged === "true"
    && image.isDataUrl === true
  )));
  const missingPictures = expected.filter((element) => !actualPictures.some((picture) => (
    picture.slide === element.slide && picture.name === element.name
  )));
  const altMismatches = expected.filter((element) => {
    const actual = actualPictures.find((picture) => picture.slide === element.slide && picture.name === element.name);
    return !actual || actual.description !== element.alt;
  });
  const cropMismatches = expected.filter((element) => element.fit !== "cover");
  const positionMismatches = expected.filter((element) => {
    const actual = actualPictures.find((picture) => picture.slide === element.slide && picture.name === element.name);
    if (!actual?.position) return true;
    const expectedPosition = element.position;
    return ["left", "top", "width", "height"].some((key) => (
      Math.abs(Number(actual.position[key] || 0) - Number(expectedPosition[key] || 0)) > 0.01
    ));
  });
  return {
    domSemanticPictures: dom,
    expectedSemanticPictures: expected,
    actualSlidePictures: actualPictures,
    manifestDomMismatches,
    missingPictures,
    altMismatches,
    cropMismatches,
    positionMismatches,
    pass: dom.length === 4
      && expected.length === 4
      && actualPictures.length === 4
      && manifestDomMismatches.length === 0
      && missingPictures.length === 0
      && altMismatches.length === 0
      && cropMismatches.length === 0
      && positionMismatches.length === 0,
  };
}
async function main() {
  const options = argsOf(process.argv);
  const htmlPath = path.resolve(options.html);
  const outputPath = path.resolve(options.output);
  const reportPath = path.resolve(options.report);
  const fileUrl = pathToFileURL(htmlPath).href;
  const candidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 900 },
    acceptDownloads: true,
  });
  const consoleErrors = [];
  const pageErrors = [];
  const networkRequests = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    if (/^https?:/i.test(request.url())) networkRequests.push(request.url());
  });
  await page.route(/^https?:\/\//i, (route) => route.abort());

  try {
    await page.goto(fileUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
    try {
      await page.waitForFunction(() => (
        document.documentElement.dataset.layoutReady === "true"
        && Boolean(window.EditMode?.exportPptx)
        && typeof window.PptxGenJS === "function"
        && typeof window.PptxBrowserExport?.exportManifest === "function"
      ), null, { timeout: 120000 });
    } catch (error) {
      const diagnostic = await page.evaluate(() => ({
        readyState: document.readyState,
        layoutReady: document.documentElement.dataset.layoutReady || "",
        editMode: typeof window.EditMode,
        pptxGenJS: typeof window.PptxGenJS,
        browserExport: typeof window.PptxBrowserExport,
        bodyText: (document.body?.innerText || "").slice(0, 200),
      }));
      throw new Error(`Browser runtime did not become ready: ${JSON.stringify({ diagnostic, consoleErrors, pageErrors })}`);
    }

    const framework = await page.evaluate(() => {
      const toggle = document.getElementById("edit-save-menu-toggle");
      const menu = document.getElementById("edit-save-menu");
      const pptxItem = [...(menu?.querySelectorAll("button") || [])].find((button) => (
        /PPTX|PowerPoint/i.test(button.getAttribute("aria-label") || "")
        || /PPTX/i.test(button.textContent || "")
      ));
      return {
        title: document.title,
        slides: document.querySelectorAll("#stage > .slide").length,
        saveMenuToggle: {
          selector: "#edit-save-menu-toggle",
          present: Boolean(toggle),
          ariaExpanded: toggle?.getAttribute("aria-expanded") || null,
          enabled: Boolean(toggle && !toggle.disabled),
        },
        pptxMenuItem: {
          selector: "#edit-save-menu button[aria-label*=PPTX], #edit-save-menu button",
          present: Boolean(pptxItem),
          label: pptxItem?.getAttribute("aria-label") || "",
          text: (pptxItem?.textContent || "").trim(),
          enabled: Boolean(pptxItem && !pptxItem.disabled),
        },
        embeddedRuntimeCount: document.querySelectorAll(
          'script[data-pptx-browser-runtime-embedded="true"]'
        ).length,
      };
    });

    const editProbe = options.sentinel
      ? await page.evaluate((sentinel) => {
        const nodes = [...document.querySelectorAll("#stage > .slide .el, #stage > .slide [data-edit-layer]")];
        const target = nodes.find((node) => [...node.childNodes].some((child) => (
          child.nodeType === Node.TEXT_NODE && String(child.nodeValue || "").trim()
        )));
        if (!target) throw new Error("Unable to find a direct text node for the edit round-trip probe");
        const textNode = [...target.childNodes].find((child) => (
          child.nodeType === Node.TEXT_NODE && String(child.nodeValue || "").trim()
        ));
        textNode.nodeValue = sentinel;
        return {
          slide: target.closest(".slide")?.id || "",
          className: target.className || "",
          value: sentinel,
        };
      }, options.sentinel)
      : null;

    const positionManifest = await page.evaluate(async () => {
      const manifest = await window.EditMode.buildPptxManifest();
      return {
        coordinateSystem: manifest.coordinateSystem,
        semanticDom: [...document.querySelectorAll('#stage > .slide img[data-semantic-image="true"]')].map((image) => ({
          slideId: image.closest('.slide')?.id || '',
          alt: image.getAttribute('alt') || '',
          cropBehavior: image.getAttribute('data-crop-behavior') || '',
          focalRegion: image.getAttribute('data-focal-region') || '',
          source: image.getAttribute('data-semantic-image-source') || image.getAttribute('src') || '',
          sha256: image.getAttribute('data-semantic-image-sha256') || '',
          staged: image.getAttribute('data-semantic-image-staged') || '',
          isDataUrl: (image.getAttribute('src') || '').startsWith('data:image/'),
        })),
        backgroundLayers: manifest.slides.map((slide, index) => {
          const node = document.querySelectorAll("#stage > .slide")[index];
          const style = getComputedStyle(node);
          return {
            cssBackgroundImage: style.backgroundImage,
            manifestHasRasterBackground: Boolean(slide.backgroundImage?.dataUrl),
            backgroundRole: slide.backgroundImage?.role || "",
            nativeDecorations: slide.elements.filter((element) => String(element.name || "").includes("-slide-bg-")).length,
          };
        }),
        slides: manifest.slides.map((slide) => ({
          id: slide.id,
          elements: slide.elements.map((element) => ({
            name: element.name,
            position: element.position,
            text: element.text || '',
            shape: element.shape || '',
            singleLine: element.singleLine === true,
            renderedLineCount: element.renderedLineCount,
            kind: element.kind || '',
            alt: element.alt || '',
            fit: element.fit || '',
            svgTextProjection: element.svgTextProjection || '',
            svgTextAnchor: element.svgTextAnchor || '',
            svgTextMetrics: element.svgTextMetrics || null,
          })),
        })),
      };
    });

    const startedAt = Date.now();
    const downloadPromise = page.waitForEvent("download", { timeout: 240000 });
    const resultPromise = page.evaluate(() => new Promise((resolve) => {
      document.addEventListener("editpptxexported", (event) => resolve({
        exported: true,
        ...event.detail,
      }), { once: true });
    }));
    const clickPromise = page.evaluate(async () => {
      const toggle = document.getElementById("edit-save-menu-toggle");
      const menu = document.getElementById("edit-save-menu");
      if (!toggle || !menu) throw new Error("PPTX save menu controls are unavailable");
      toggle.click();
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const menuVisible = getComputedStyle(menu).display !== "none";
      const ariaExpanded = toggle.getAttribute("aria-expanded") === "true";
      const button = [...menu.querySelectorAll("button")].find((candidate) => (
        /PPTX|PowerPoint/i.test(candidate.getAttribute("aria-label") || "")
        || /PPTX/i.test(candidate.textContent || "")
      ));
      if (!button || button.disabled) throw new Error("PPTX save-menu item is unavailable");
      button.click();
      return {
        clicked: true,
        menuVisible,
        ariaExpanded,
        itemSelector: "#edit-save-menu button",
        itemLabel: button.getAttribute("aria-label") || "",
        itemText: (button.textContent || "").trim(),
      };
    });
    const [download, result, menuAction] = await Promise.all([
      downloadPromise,
      resultPromise,
      clickPromise,
    ]);
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await download.saveAs(outputPath);
    const exportMs = Date.now() - startedAt;
    const file = await fs.stat(outputPath);
    const signature = Buffer.alloc(4);
    const handle = await fs.open(outputPath, "r");
    await handle.read(signature, 0, 4, 0);
    await handle.close();
    const archive = await JSZip.loadAsync(await fs.readFile(outputPath));
    const mediaFiles = Object.keys(archive.files).filter((name) => /^ppt\/media\/.+/.test(name) && !archive.files[name].dir);
    const slidePaths = Object.keys(archive.files).filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name)).sort((a, b) => Number(a.match(/slide(\d+)\.xml$/)[1]) - Number(b.match(/slide(\d+)\.xml$/)[1]));
    const slideXml = await Promise.all(slidePaths.map((name) => archive.file(name).async("string")));
    const layoutPaths = Object.keys(archive.files).filter((name) => /^ppt\/slideLayouts\/slideLayout\d+\.xml$/.test(name)).sort((a, b) => Number(a.match(/slideLayout(\d+)\.xml$/)[1]) - Number(b.match(/slideLayout(\d+)\.xml$/)[1]));
    const layoutXml = await Promise.all(layoutPaths.map((name) => archive.file(name).async("string")));
    const layoutRasterBackgrounds = layoutXml.filter((xml) => /<p:pic\b[\s\S]*?<a:blip\b/.test(xml)).length;
    const slidePictureObjects = slideXml.reduce((sum, xml) => sum + (xml.match(/<p:pic\b/g) || []).length, 0);
    const expectedBackgrounds = positionManifest.backgroundLayers.filter((layer) => layer.manifestHasRasterBackground).length;
    const joinedSlideXml = slideXml.join("\n");
    const editedValueRoundTrip = options.sentinel
      ? slideXml.some((xml) => xml.includes(options.sentinel))
      : true;
    const fidelityOverlayObjects = (joinedSlideXml.match(/HTML-Fidelity-Overlay/g) || []).length;
    const positioning = nativePositionAudit(positionManifest, slideXml);
    const textLayout = nativeTextLayoutAudit(positionManifest, slideXml);
    const svgTextProjection = svgTextProjectionAudit(positionManifest, slideXml);
    const semanticPictures = semanticPictureAudit(positionManifest, slideXml);
    const checks = {
      fileProtocol: fileUrl.startsWith("file://"),
      frameworkReady: Boolean(framework.title),
      slideCount: framework.slides > 0,
      pptxSaveMenuTogglePresent: framework.saveMenuToggle.present && framework.saveMenuToggle.enabled,
      pptxMenuItemPresent: framework.pptxMenuItem.present && framework.pptxMenuItem.enabled,
      pptxMenuOpened: menuAction?.menuVisible === true && menuAction?.ariaExpanded === true,
      runtimeEmbeddedOnce: framework.embeddedRuntimeCount === 1,
      saveMenuItemClicked: menuAction?.clicked === true,
      editedValueRoundTrip,
      browserMethod: result?.exported === true && result?.method === "pptxgenjs-browser",
      exportedSlideCount: result?.slides === framework.slides,
      backgroundCountReported: result?.backgroundImages === expectedBackgrounds,
      contentMode: expectedBackgrounds > 0
        ? result?.hybrid === true && result?.fidelitySlides === 0
        : result?.nativeOnly === true && result?.fidelitySlides === 0,
      noFidelityOverlayObjects: fidelityOverlayObjects === 0,
      rasterMediaFilesPresent: mediaFiles.length >= expectedBackgrounds,
      backgroundImagesOnLayouts: layoutRasterBackgrounds === expectedBackgrounds,
      semanticPicturesOnSlides: slidePictureObjects === 4 && semanticPictures.pass,
      backgroundParity: positionManifest.backgroundLayers.every((layer) => layer.cssBackgroundImage === "none" || layer.manifestHasRasterBackground || layer.nativeDecorations > 0),
      nativePositioning: positioning.matchedObjects > 0
        && positioning.missingObjects <= (result?.warnings?.length || 0)
        && positioning.maxDeltaPx <= 0.01
        && positioning.maxRotationDeltaDegrees <= 0.01,
      nativeTextLayout: textLayout.pass,
      svgTextProjection: svgTextProjection.pass,
      noLocalServerRoute: !networkRequests.some((url) => /\/__export-pptx(?:\?|$)/.test(url)),
      suggestedFileName: download.suggestedFilename().toLowerCase().endsWith(".pptx"),
      zipSignature: signature.equals(Buffer.from([0x50, 0x4b, 0x03, 0x04])),
      outputBytes: file.size > 10000,
      noPageErrors: pageErrors.length === 0,
    };
    const report = {
      html: htmlPath,
      url: fileUrl,
      output: outputPath,
      bytes: file.size,
      exportMs,
      framework,
      saveMenuAction: menuAction,
      editProbe,
      result,
      download: { suggestedFileName: download.suggestedFilename() },
      networkRequests,
      consoleErrors,
      pageErrors,
      package: {
        fidelityOverlayObjects,
        mediaFiles,
        layoutPaths,
        layoutRasterBackgrounds,
        slidePictureObjects,
        expectedBackgrounds,
        expectedSemanticPictures: semanticPictures.expectedSemanticPictures.length,
      },
      positioning,
      textLayout,
      svgTextProjection,
      semanticPictures,
      checks,
      pass: Object.values(checks).every(Boolean),
    };
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
