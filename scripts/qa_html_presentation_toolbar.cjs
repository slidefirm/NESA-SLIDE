const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

function portablePath(value) {
  if (!value) return null;
  return path.relative(process.cwd(), value).split(path.sep).join("/");
}

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--html") out.html = argv[++index];
    else if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--profile") out.profile = argv[++index];
    else if (argv[index] === "--selector") out.selector = argv[++index];
  }
  if ((!out.html && !out.url) || !out.report) throw new Error("--html or --url, plus --report, are required");
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = options.html ? path.resolve(options.html) : null;
  const pageUrl = options.url || pathToFileURL(htmlPath).href;
  const { chromium } = loadPlaywright();
  const executablePath = browserExecutable();
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(pageUrl, { waitUntil: "commit", timeout: 30000 });
    if (options.selector) await page.waitForSelector(options.selector);
    await page.waitForLoadState("domcontentloaded");
    await Promise.race([page.evaluate(() => document.fonts?.ready), page.waitForTimeout(3000)]);
    await page.waitForFunction(() => Boolean(window.EditMode));

    const snapshot = () => page.evaluate(() => {
      const stage = document.getElementById("stage");
      const canvas = document.getElementById("canvasBox");
      const bar = document.getElementById("bar");
      const barInner = document.getElementById("barInner");
      const player = document.getElementById("player");
      const rail = document.getElementById("slideRail");
      const railHeader = document.getElementById("slideRailHeader");
      const hint = document.getElementById("hint");
      const stageRect = stage.getBoundingClientRect();
      const canvasRect = canvas.getBoundingClientRect();
      const barRect = bar.getBoundingClientRect();
      const railHeaderRect = railHeader?.getBoundingClientRect();
      const barStyle = getComputedStyle(bar);
      const innerStyle = getComputedStyle(barInner);
      return {
        stage: {
          transform: getComputedStyle(stage).transform,
          width: stageRect.width,
          height: stageRect.height,
          canvasWidth: canvasRect.width,
          canvasHeight: canvasRect.height,
        },
        toolbar: {
          showClass: bar.classList.contains("show"),
          editorClass: bar.classList.contains("editor-active"),
          opacity: Number(barStyle.opacity),
          pointerEvents: innerStyle.pointerEvents,
          visibleControls: [...barInner.querySelectorAll("button")]
            .filter((button) => getComputedStyle(button).display !== "none")
            .map((button) => button.getAttribute("aria-label")),
        },
        shell: {
          editorShell: player.classList.contains("editor-shell"),
          railVisible: rail && getComputedStyle(rail).display !== "none",
          railHeaderTop: railHeaderRect?.top ?? null,
          topbarDocked: Math.abs(barRect.top) <= 1,
          hintVisible: hint && getComputedStyle(hint).display !== "none",
        },
      };
    });

    const edit = await snapshot();
    await page.evaluate(() => window.EditMode.toggle(false));
    await page.waitForTimeout(360);
    const presentationInitial = await snapshot();

    await page.mouse.move(800, 450);
    await page.waitForTimeout(240);
    const presentationCenter = await snapshot();

    await page.mouse.move(800, 899);
    await page.waitForTimeout(360);
    const presentationBottom = await snapshot();

    await page.mouse.move(800, 450);
    // The hide delay and opacity transition are separate.  Wait for both so
    // the QA does not sample a harmless 0.001 transition tail as a failure.
    await page.waitForTimeout(760);
    const presentationLeftBottom = await snapshot();

    await page.keyboard.press("Escape");
    await page.waitForTimeout(360);
    const restoredEdit = await snapshot();

    const isHidden = (state) => !state.toolbar.showClass
      && !state.toolbar.editorClass
      && state.toolbar.opacity <= 0.01
      && state.toolbar.pointerEvents === "none";
    const isVisible = (state) => state.toolbar.showClass
      && !state.toolbar.editorClass
      && state.toolbar.opacity === 1
      && state.toolbar.pointerEvents === "auto";
    const stageKey = (state) => JSON.stringify(state.stage);
    const projectionScaleStable = [presentationCenter, presentationBottom, presentationLeftBottom]
      .every((state) => stageKey(state) === stageKey(presentationInitial));
    const editRoundTripStable = stageKey(restoredEdit) === stageKey(edit);
    const allowedProjectionControls = ["上一頁", "下一頁", "全螢幕 (F)", "編輯模式 (E)"];
    const projectionControlsPass = presentationBottom.toolbar.visibleControls.length === allowedProjectionControls.length
      && allowedProjectionControls.every((label) => presentationBottom.toolbar.visibleControls.includes(label));

    const result = {
      html: portablePath(htmlPath),
      url: pageUrl,
      profile: options.profile || null,
      selector: options.selector || null,
      edit,
      presentationInitial,
      presentationCenter,
      presentationBottom,
      presentationLeftBottom,
      restoredEdit,
      checks: {
        initialHidden: isHidden(presentationInitial),
        centerRemainsHidden: isHidden(presentationCenter),
        bottomReveal: isVisible(presentationBottom),
        leaveBottomHides: isHidden(presentationLeftBottom),
        editToolbarRestored: restoredEdit.toolbar.editorClass && restoredEdit.toolbar.opacity === 1,
        editorChromePresent: edit.shell.editorShell && edit.shell.railVisible && edit.shell.topbarDocked,
        railUsesTopSpace: edit.shell.railHeaderTop !== null && Math.abs(edit.shell.railHeaderTop) <= 1,
        editorChromeRestored: restoredEdit.shell.editorShell && restoredEdit.shell.railVisible && restoredEdit.shell.topbarDocked,
        railUsesTopSpaceRestored: restoredEdit.shell.railHeaderTop !== null && Math.abs(restoredEdit.shell.railHeaderTop) <= 1,
        projectionChromeHidden: !presentationInitial.shell.editorShell && !presentationInitial.shell.railVisible,
        escapeReturnsToEditMode: restoredEdit.shell.editorShell && restoredEdit.shell.railVisible,
        hintHidden: [edit, presentationInitial, presentationCenter, presentationBottom, presentationLeftBottom, restoredEdit]
          .every((state) => !state.shell.hintVisible),
        projectionControlsPass,
        projectionScaleStable,
        editRoundTripStable,
      },
    };
    result.pass = Object.values(result.checks).every(Boolean);
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), JSON.stringify(result, null, 2) + "\n", "utf8");
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }
}

main()
  .then(() => process.exit(process.exitCode || 0))
  .catch((error) => { console.error(error); process.exit(1); });
