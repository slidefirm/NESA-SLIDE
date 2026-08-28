const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--html") out.html = argv[++index];
    else if (argv[index] === "--manifest") out.manifest = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.html || !out.manifest || !out.report) {
    throw new Error("--html, --manifest, and --report are required");
  }
  return out;
}

function portablePath(value) {
  return path.relative(process.cwd(), value).split(path.sep).join("/");
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = path.resolve(options.html);
  const manifestPath = path.resolve(options.manifest);
  const reportPath = path.resolve(options.report);
  const markup = await fs.readFile(htmlPath, "utf8");
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  const motionManifest = manifest.html_runtime?.motion_runtime || {};
    const expectedVersion = motionManifest.version || "projection-content-fade-v6";
  const expectedSourceSha = motionManifest.source_sha256 || "";
  const staticChecks = {
    rendererRuntimeEmbedded: manifest.html_runtime?.motion_runtime_embedded === true,
    projectionOnlyContract: motionManifest.projection_only === true
      && motionManifest.scope === "presentation-only",
    contentFadeModeContract: motionManifest.mode === "content-fade"
      && motionManifest.default_enabled === true
      && motionManifest.toolbar_toggle === false
      && motionManifest.toolbar_location === "slide-settings-panel",
    staggeredTitleContentContract: motionManifest.sequence === "title-then-content"
      && Number(motionManifest.title_delay_ms) === 0
      && Number(motionManifest.content_delay_ms) > Number(motionManifest.title_delay_ms)
      && Number(motionManifest.duration_ms) > 0,
    backgroundProjectionContract: motionManifest.background_behavior
      === "target-slide-background-static; projection-clone-foreground-only"
      && motionManifest.background_scope === "not-in-motion-clone",
    staticRuntimeMarker: markup.includes(`data-motion-runtime="${expectedVersion}"`)
      && markup.includes(`data-motion-source-sha256="${expectedSourceSha}"`)
      && markup.includes(`<script data-motion-runtime="${expectedVersion}">`)
      && markup.includes("data-motion-background-excluded"),
  };

  const { chromium } = loadPlaywright();
  const executablePath = browserExecutable();
  if (!executablePath && !process.env.BROWSER_CDP_URL) {
    throw new Error("No Chrome or Edge executable found for HTML QA");
  }
  const browser = process.env.BROWSER_CDP_URL
    ? await chromium.connectOverCDP(process.env.BROWSER_CDP_URL)
    : await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    // Exercise the user's likely projection environment: the runtime must
    // still animate by default even when the browser advertises reduced motion.
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    const baseHref = pathToFileURL(`${path.dirname(htmlPath)}${path.sep}`).href;
    const markupWithBase = markup.replace(/<head>/i, `<head><base href="${baseHref}">`);
    await page.setContent(markupWithBase, { waitUntil: "domcontentloaded", timeout: 120000 });
    await Promise.race([
      page.evaluate(() => document.fonts?.ready),
      page.waitForTimeout(3000),
    ]);
    await page.waitForFunction(
      () => document.documentElement.dataset.motionInitStage === "ready"
        && Boolean(window.EditMode)
        && Boolean(window.MotionPreview),
      null,
      { timeout: 120000 },
    );

    const readRuntime = () => page.evaluate(() => {
      const root = document.documentElement;
      const player = document.getElementById("player");
      const button = document.getElementById("motionToggleBtn");
      const active = document.querySelector("#stage > .slide.active");
      const diagnostics = window.MotionPreview?.diagnostics?.() || null;
      return {
        version: window.MotionPreview?.version || null,
        mode: window.MotionPreview?.mode || null,
        enabled: window.MotionPreview?.enabled ?? null,
        initStage: root.dataset.motionInitStage || null,
        runState: root.dataset.motionRunState || null,
        runCount: Number(root.dataset.motionRunCount || 0),
        objectCount: Number(root.dataset.motionObjectCount || 0),
        step: Number(root.dataset.motionStep || 0),
        stepCount: Number(root.dataset.motionStepCount || 0),
        stepState: root.dataset.motionStepState || null,
        trigger: root.dataset.motionTrigger || null,
        activeSlideIndex: window.SlidePlayer?.getCurrentIndex?.() ?? null,
        editorShell: player?.classList.contains("editor-shell") || false,
        button: button ? {
          display: getComputedStyle(button).display,
          ariaPressed: button.getAttribute("aria-pressed"),
          label: button.textContent.trim(),
          ariaLabel: button.getAttribute("aria-label"),
          inSettingsPanel: Boolean(button.closest("[data-motion-settings-row]")),
          inToolbar: Boolean(button.closest("#barInner")),
        } : null,
        activeLayers: diagnostics?.activeLayers ?? 0,
        activeClones: diagnostics?.activeClones ?? 0,
        presentationMode: diagnostics?.presentationMode ?? false,
        reducedMotion: diagnostics?.reducedMotion ?? null,
        reducedMotionPreference: diagnostics?.reducedMotionPreference ?? null,
        forcedMotionPreview: diagnostics?.forcedMotionPreview ?? null,
        titleDelayMs: diagnostics?.titleDelayMs ?? null,
        contentDelayMs: diagnostics?.contentDelayMs ?? null,
        fadeDurationMs: diagnostics?.fadeDurationMs ?? null,
        revealSequence: diagnostics?.revealSequence ?? null,
        titleObjectCount: diagnostics?.titleObjectCount ?? 0,
        contentObjectCount: diagnostics?.contentObjectCount ?? 0,
        backgroundExcluded: diagnostics?.backgroundExcluded ?? false,
        activeVisibility: active?.style.visibility || "",
        targetForegroundOpacity: (() => {
          const object = active?.querySelector('.el');
          return object ? Number(getComputedStyle(object).opacity) : null;
        })(),
        projectionBackgroundMarker: document.querySelector('[data-object-reveal-slide]')?.dataset.pptxBackgroundImage || null,
        projectionBackgroundImage: (() => {
          const slide = document.querySelector('[data-object-reveal-slide]');
          return slide ? getComputedStyle(slide).backgroundImage : null;
        })(),
        projectionLayerOpacity: (() => {
          const layer = document.querySelector('[data-object-reveal-layer]');
          return layer ? Number(getComputedStyle(layer).opacity) : null;
        })(),
        firstProjectionObject: (() => {
          const object = document.querySelector('[data-object-reveal-slide] .el');
          if (!object) return null;
          const style = getComputedStyle(object);
          return {
            opacity: Number(style.opacity),
            transform: style.transform,
          };
        })(),
        firstProjectionTitle: (() => {
          const object = document.querySelector('[data-object-reveal-slide] [data-motion-reveal-role="title"]');
          if (!object) return null;
          const style = getComputedStyle(object);
          return { opacity: Number(style.opacity), transform: style.transform };
        })(),
        firstProjectionContent: (() => {
          const object = document.querySelector('[data-object-reveal-slide] [data-motion-reveal-role="content"]');
          if (!object) return null;
          const style = getComputedStyle(object);
          return { opacity: Number(style.opacity), transform: style.transform };
        })(),
        firstPendingProjectionObject: (() => {
          const object = document.querySelector('[data-object-reveal-slide] [data-motion-step="1"]');
          if (!object) return null;
          const style = getComputedStyle(object);
          return {
            opacity: Number(style.opacity),
            visibility: style.visibility,
            transform: style.transform,
          };
        })(),
      };
    });

    const authoredSnapshot = () => page.evaluate(() => {
      const active = document.querySelector("#stage > .slide.active");
      if (!active) return null;
      return {
        id: active.id,
        text: active.textContent,
        html: active.innerHTML,
        visibility: active.style.visibility || "",
      };
    });

    const editInitial = await readRuntime();
    const button = page.locator("#motionToggleBtn");
    const motionWaitMs = Math.max(700, Number(motionManifest.duration_ms) || 0)
      + (Number(motionManifest.delay_ms) || 0) + 600;

    await page.evaluate(() => window.EditMode.toggle(false));
    await page.waitForFunction(
      () => document.documentElement.dataset.motionRunState === "running",
      null,
      { timeout: 30000 },
    );
    await page.waitForTimeout(140);
    const directEntryPresentation = await readRuntime();
    await page.waitForTimeout(motionWaitMs);
    const directEntryCompleted = await readRuntime();

    await page.evaluate(() => window.SlidePlayer.setSlide(1));
    await page.waitForFunction(
      () => document.documentElement.dataset.motionRunState === "running",
      null,
      { timeout: 30000 },
    );
    await page.waitForTimeout(140);
    const pageChangeRunning = await readRuntime();
    await page.waitForTimeout(motionWaitMs);
    const pageChangeCompleted = await readRuntime();

    await page.evaluate(() => window.EditMode.toggle(true));
    await page.waitForTimeout(180);

    await page.locator("#edit-slide-style-button").click();
    await page.waitForFunction(
      () => getComputedStyle(document.getElementById("edit-slide-style-panel")).display !== "none",
      null,
      { timeout: 30000 },
    );
    await button.click();
    await page.waitForTimeout(60);
    const disabledEdit = await readRuntime();

    await page.evaluate(() => window.EditMode.toggle(false));
    await page.waitForTimeout(100);
    const disabledPresentation = await readRuntime();
    const authoredBeforeProjection = await authoredSnapshot();

    await page.evaluate(() => window.MotionPreview.setEnabled(true, true));
    await page.waitForFunction(
      () => document.documentElement.dataset.motionRunState === "running",
      null,
      { timeout: 30000 },
    );
    await page.waitForTimeout(100);
    const runningPresentation = await readRuntime();
    const authoredDuringProjection = await authoredSnapshot();
    await page.waitForTimeout(motionWaitMs);
    const completedPresentation = await readRuntime();
    const authoredAfterProjection = await authoredSnapshot();

    await page.evaluate(() => window.EditMode.toggle(true));
    await page.waitForTimeout(180);
    const restoredEdit = await readRuntime();

    const result = {
      schema: "html-content-fade-toggle-qa-v6",
      html: portablePath(htmlPath),
      manifest: portablePath(manifestPath),
      runtime: motionManifest,
      staticChecks,
      observations: {
        editInitial,
        directEntryPresentation,
        directEntryCompleted,
        pageChangeRunning,
        pageChangeCompleted,
        disabledEdit,
        disabledPresentation,
        runningPresentation,
        completedPresentation,
        restoredEdit,
      },
      checks: {
        ...staticChecks,
        runtimeReady: editInitial.initStage === "ready"
          && editInitial.version === expectedVersion
          && editInitial.mode === "content-fade",
        settingsTogglePresentAndEnabled: editInitial.button?.display !== "none"
          && editInitial.button?.ariaPressed === "true"
          && editInitial.button?.inSettingsPanel === true
          && editInitial.button?.inToolbar === false
          && editInitial.enabled === true,
        directPresentationEntryCreatesContentFade: directEntryPresentation.presentationMode
          && directEntryPresentation.reducedMotionPreference === true
          && directEntryPresentation.reducedMotion === false
          && directEntryPresentation.titleDelayMs === Number(motionManifest.title_delay_ms)
          && directEntryPresentation.contentDelayMs === Number(motionManifest.content_delay_ms)
          && directEntryPresentation.fadeDurationMs === Number(motionManifest.duration_ms)
          && directEntryPresentation.revealSequence === "title-then-content"
          && directEntryPresentation.titleObjectCount >= 1
          && directEntryPresentation.contentObjectCount >= 1
          && directEntryPresentation.activeLayers === 1
          && directEntryPresentation.activeClones >= 1
          && directEntryPresentation.runState === "running"
          && directEntryPresentation.trigger === "enter-presentation"
          && directEntryPresentation.projectionLayerOpacity > 0.95
          && directEntryPresentation.backgroundExcluded === true
          && directEntryPresentation.projectionBackgroundMarker === null
          && directEntryPresentation.projectionBackgroundImage === "none"
          && directEntryPresentation.activeVisibility === ""
          && directEntryPresentation.targetForegroundOpacity < 0.05
          && directEntryPresentation.firstProjectionTitle !== null
          && directEntryPresentation.firstProjectionContent !== null,
        directPresentationEntryCompletes: directEntryCompleted.activeLayers === 0
          && directEntryCompleted.activeClones === 0
          && directEntryCompleted.runState === "completed",
        pageChangeCreatesContentFade: pageChangeRunning.presentationMode
          && pageChangeRunning.activeSlideIndex === 1
          && pageChangeRunning.activeLayers === 1
          && pageChangeRunning.activeClones >= 1
          && pageChangeRunning.runState === "running"
          && pageChangeRunning.trigger === "page-change"
          && pageChangeRunning.projectionLayerOpacity > 0.95
          && pageChangeRunning.backgroundExcluded === true
          && pageChangeRunning.projectionBackgroundMarker === null
          && pageChangeRunning.projectionBackgroundImage === "none"
          && pageChangeRunning.activeVisibility === ""
          && pageChangeRunning.firstProjectionTitle?.opacity
            > pageChangeRunning.firstProjectionContent?.opacity + 0.05
          && pageChangeRunning.firstProjectionContent?.opacity < 0.05,
        pageChangeCompletes: pageChangeCompleted.activeLayers === 0
          && pageChangeCompleted.activeClones === 0
          && pageChangeCompleted.runState === "completed",
        presentationSettingsTogglePresent: directEntryPresentation.button?.display !== "none"
          && directEntryPresentation.button?.inSettingsPanel === true
          && directEntryPresentation.button?.inToolbar === false,
        toggleDisablesAnimation: disabledEdit.enabled === false
          && disabledEdit.button?.ariaPressed === "false",
        disabledPresentationDoesNotCreateProjection: disabledPresentation.presentationMode
          && disabledPresentation.activeLayers === 0
          && disabledPresentation.activeClones === 0,
        enabledPresentationCreatesProjection: runningPresentation.presentationMode
          && runningPresentation.activeLayers === 1
          && runningPresentation.activeClones >= 1
          && runningPresentation.runState === "running"
          && runningPresentation.projectionLayerOpacity > 0.95
          && runningPresentation.backgroundExcluded === true
          && runningPresentation.projectionBackgroundMarker === null
          && runningPresentation.projectionBackgroundImage === "none"
          && runningPresentation.activeVisibility === ""
          && runningPresentation.firstProjectionTitle?.opacity
            > runningPresentation.firstProjectionContent?.opacity + 0.05
          && runningPresentation.firstProjectionContent?.opacity < 0.05,
        projectionCompletesAndCleansUp: completedPresentation.activeLayers === 0
          && completedPresentation.activeClones === 0
          && completedPresentation.runState === "completed"
          && completedPresentation.activeVisibility === "",
        authoredDomUnchangedDuringProjection: JSON.stringify({
          id: authoredBeforeProjection?.id,
          text: authoredBeforeProjection?.text,
          html: authoredBeforeProjection?.html,
        }) === JSON.stringify({
          id: authoredDuringProjection?.id,
          text: authoredDuringProjection?.text,
          html: authoredDuringProjection?.html,
        })
          && JSON.stringify({
            id: authoredBeforeProjection?.id,
            text: authoredBeforeProjection?.text,
            html: authoredBeforeProjection?.html,
            visibility: authoredBeforeProjection?.visibility,
          }) === JSON.stringify({
            id: authoredAfterProjection?.id,
            text: authoredAfterProjection?.text,
            html: authoredAfterProjection?.html,
            visibility: authoredAfterProjection?.visibility,
          }),
        editModeRestored: restoredEdit.editorShell
          && restoredEdit.button?.display !== "none"
          && restoredEdit.button?.ariaPressed === "true"
          && restoredEdit.button?.inSettingsPanel === true
          && restoredEdit.button?.inToolbar === false
          && restoredEdit.enabled === true,
      },
    };
    result.pass = Object.values(result.checks).every(Boolean);
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(result, null, 2) + "\n", "utf8");
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }
}

main()
  .then(() => process.exit(process.exitCode || 0))
  .catch((error) => { console.error(error); process.exit(1); });
