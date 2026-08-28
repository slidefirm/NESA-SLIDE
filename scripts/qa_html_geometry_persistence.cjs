const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--html") out.html = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--screenshot-dir") out.screenshotDir = argv[++index];
  }
  if (!out.html || !out.report) throw new Error("--html and --report are required");
  return out;
}

function closeEnough(a, b, tolerance = 1.5) {
  return Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) <= tolerance;
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = path.resolve(options.html);
  const reportPath = path.resolve(options.report);
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  if (!executablePath) throw new Error("No Chrome or Edge executable found for HTML QA");

  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
  const report = {
    html: htmlPath,
    materialization: null,
    textEditGuides: null,
    operationChain: null,
    draftReload: null,
    undoToBaseline: null,
    revisionIsolation: null,
    operationLog: null,
    pass: false,
  };

  const waitReady = async () => {
    await Promise.race([
      page.waitForLoadState("load"),
      page.waitForTimeout(3000),
    ]);
    await page.evaluate(() => Promise.race([
      document.fonts?.ready || Promise.resolve(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]));
    await page.waitForFunction(() => document.documentElement.dataset.layoutReady === "true");
    await page.waitForTimeout(80);
  };

  try {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await waitReady();

    const baseline = await page.evaluate(() => {
      const round = (value) => Math.round(value * 10) / 10;
      const state = (selector) => {
        const el = document.querySelector(selector);
        if (!el) return null;
        const style = getComputedStyle(el);
        return {
          selector,
          left: round(parseFloat(style.left)),
          top: round(parseFloat(style.top)),
          width: round(parseFloat(style.width)),
          height: round(parseFloat(style.height)),
          fontSize: round(parseFloat(style.fontSize)),
          groupId: el.dataset.editGroup || "",
        };
      };
      const area = document.querySelector(".slide.active [data-auto-layout]");
      const areaRect = area.getBoundingClientRect();
      const scaleX = area.offsetWidth ? areaRect.width / area.offsetWidth : 1;
      const scaleY = area.offsetHeight ? areaRect.height / area.offsetHeight : 1;
      const geometry = [...area.children]
        .filter((el) => el.matches(".el,[data-layout-item]") && getComputedStyle(el).display !== "none")
        .map((el) => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          const actual = {
            left: (rect.left - areaRect.left) / scaleX,
            top: (rect.top - areaRect.top) / scaleY,
            width: rect.width / scaleX,
            height: rect.height / scaleY,
          };
          const computed = {
            left: parseFloat(style.left),
            top: parseFloat(style.top),
            width: parseFloat(style.width),
            height: parseFloat(style.height),
          };
          const delta = Object.fromEntries(Object.keys(actual).map((key) => [key, round(actual[key] - computed[key])]));
          const priorities = Object.fromEntries(["left", "top", "width", "height"].map((key) => [key, el.style.getPropertyPriority(key)]));
          return { className: el.className, actual, computed, delta, priorities };
        });
      return {
        revision: document.documentElement.dataset.deckRevision || "",
        title: state(".cover-center-title"),
        subtitle: state(".cover-center-subtitle"),
        speaker: state(".cover-center-speaker"),
        org: state(".cover-center-org"),
        geometry,
      };
    });

    const geometryFailures = baseline.geometry.filter((entry) => {
      const deltasOk = Object.values(entry.delta).every((value) => Math.abs(value) <= 0.8);
      const prioritiesOk = Object.values(entry.priorities).every((value) => value === "important");
      return !deltasOk || !prioritiesOk;
    });
    report.materialization = {
      revision: baseline.revision,
      checked: baseline.geometry.length,
      failures: geometryFailures,
      pass: Boolean(baseline.revision) && baseline.geometry.length >= 3 && geometryFailures.length === 0,
    };

    if (options.screenshotDir) {
      const screenshotDir = path.resolve(options.screenshotDir);
      await fs.mkdir(screenshotDir, { recursive: true });
      const slideCount = await page.locator(".slide").count();
      for (let index = 0; index < slideCount; index += 1) {
        await page.evaluate((slideIndex) => window.setSlide(slideIndex), index);
        await page.waitForTimeout(80);
        await page.locator(".slide.active").screenshot({
          path: path.join(screenshotDir, `slide-${String(index + 1).padStart(3, "0")}.png`),
        });
      }
      await page.evaluate(() => window.setSlide(0));
      await page.waitForTimeout(80);
    }

    report.textEditGuides = await page.evaluate(async () => {
      const settle = () => new Promise((resolve) => setTimeout(resolve, 50));
      const active = document.querySelector(".slide.active");
      const stage = document.querySelector("#stage") || active?.parentElement;
      if (!active || !stage) return { pass: false, reason: "missing-stage" };
      const probe = document.createElement("div");
      probe.className = "el qa-text-guide-probe";
      probe.dataset.editLayer = "text";
      probe.dataset.editFit = "text";
      probe.textContent = "對齊輔助線";
      probe.style.cssText = [
        "position:absolute",
        "left:760px",
        "top:420px",
        "width:400px",
        "height:90px",
        "z-index:999",
        "display:flex",
        "align-items:center",
        "justify-content:center",
        "padding:0",
        "border:0",
        "background:transparent",
        "font:700 36px/1 sans-serif",
        "text-align:center",
        "color:#111827",
      ].join(";");
      active.appendChild(probe);
      const click = () => {
        const rect = probe.getBoundingClientRect();
        const init = {
          bubbles: true,
          clientX: rect.left + rect.width / 2,
          clientY: rect.top + rect.height / 2,
          button: 0,
        };
        ["mousedown", "mouseup", "click"].forEach((type) => probe.dispatchEvent(new MouseEvent(type, init)));
      };
      click();
      await settle();
      click();
      await settle();

      const guide = document.querySelector('.edit-guide-line[data-guide-axis="x"]');
      const guideRect = guide?.getBoundingClientRect();
      const stageRect = stage.getBoundingClientRect();
      const expectedX = stageRect.left + stageRect.width / 2;
      const visibleDuringTextEdit = Boolean(guide && getComputedStyle(guide).display !== "none");
      const centered = Boolean(guideRect && Math.abs(guideRect.left - expectedX) <= 1.5);
      const spansStage = Boolean(guideRect && Math.abs(guideRect.top - stageRect.top) <= 1.5
        && Math.abs(guideRect.height - stageRect.height) <= 2);
      const source = guide?.dataset.guideSource || "";

      window.EditMode.toggle(false);
      await settle();
      const hiddenInProjection = !guide || getComputedStyle(guide).display === "none";
      window.EditMode.toggle(true);
      probe.remove();
      await settle();
      return {
        visibleDuringTextEdit,
        centered,
        spansStage,
        source,
        hiddenInProjection,
        pass: visibleDuringTextEdit && centered && spansStage && hiddenInProjection,
      };
    });

    const operationResult = await page.evaluate(async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const click = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = {
          bubbles: true,
          clientX: rect.left + rect.width / 2,
          clientY: rect.top + rect.height / 2,
          button: 0,
          shiftKey,
        };
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      const resize = async (position, dx, dy) => {
        const handle = document.querySelector(`.edit-resize-handle[data-handle="${position}"]`);
        if (!handle || getComputedStyle(handle).display === "none") return false;
        const rect = handle.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, clientX: x, clientY: y, button: 0 }));
        window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: x + dx, clientY: y + dy, button: 0 }));
        window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: x + dx, clientY: y + dy, button: 0 }));
        await frame();
        return true;
      };
      const state = (selector) => {
        const el = document.querySelector(selector);
        const style = getComputedStyle(el);
        return {
          left: parseFloat(style.left),
          top: parseFloat(style.top),
          width: parseFloat(style.width),
          height: parseFloat(style.height),
          fontSize: parseFloat(style.fontSize),
          groupId: el.dataset.editGroup || "",
        };
      };
      const containment = () => {
        const content = document.querySelector(".slide.active [data-content-area]").getBoundingClientRect();
        return [".cover-center-title", ".cover-center-subtitle", ".cover-center-speaker", ".cover-center-org"]
          .map((selector) => {
            const rect = document.querySelector(selector).getBoundingClientRect();
            return {
              selector,
              inside: rect.left >= content.left - 2 && rect.top >= content.top - 2
                && rect.right <= content.right + 2 && rect.bottom <= content.bottom + 2,
              rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom },
            };
          });
      };

      const title = document.querySelector(".cover-center-title");
      const subtitle = document.querySelector(".cover-center-subtitle");
      click(title);
      click(subtitle, true);
      await frame();
      window.EditMode.group();
      await frame();
      const grouped = Boolean(title.dataset.editGroup && title.dataset.editGroup === subtitle.dataset.editGroup);
      const scaled = await resize("se", 48, 28);
      const widened = await resize("e", 36, 0);
      document.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowDown", shiftKey: true }));
      await frame();
      const diagnostics = window.EditMode.diagnostics();
      return {
        grouped,
        scaled,
        widened,
        title: state(".cover-center-title"),
        subtitle: state(".cover-center-subtitle"),
        speaker: state(".cover-center-speaker"),
        org: state(".cover-center-org"),
        containment: containment(),
        diagnostics,
      };
    });

    const changed = ["title", "subtitle"].some((key) => {
      return !closeEnough(operationResult[key].top, baseline[key].top, 0.2)
        || !closeEnough(operationResult[key].width, baseline[key].width, 0.2);
    });
    report.operationChain = {
      grouped: operationResult.grouped,
      scaled: operationResult.scaled,
      widened: operationResult.widened,
      changed,
      containment: operationResult.containment,
      diagnosticEntries: operationResult.diagnostics.entries.length,
      pass: operationResult.grouped && operationResult.scaled && operationResult.widened && changed
        && operationResult.containment.every((entry) => entry.inside)
        && operationResult.diagnostics.entries.length >= 3,
    };

    await page.waitForTimeout(1800);
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await waitReady();
    const promptShown = await page.locator("#edit-draft-prompt").isVisible().catch(() => false);
    if (promptShown) await page.locator("#edit-draft-prompt button").first().click();
    await page.waitForTimeout(120);
    const restored = await page.evaluate(() => {
      const state = (selector) => {
        const el = document.querySelector(selector);
        const style = getComputedStyle(el);
        return {
          left: parseFloat(style.left), top: parseFloat(style.top), width: parseFloat(style.width),
          height: parseFloat(style.height), fontSize: parseFloat(style.fontSize), groupId: el.dataset.editGroup || "",
        };
      };
      return {
        title: state(".cover-center-title"), subtitle: state(".cover-center-subtitle"),
        speaker: state(".cover-center-speaker"), org: state(".cover-center-org"),
        diagnostics: window.EditMode.diagnostics(),
      };
    });
    const restoredMatches = ["title", "subtitle", "speaker", "org"].every((key) => {
      return ["left", "top", "width", "height", "fontSize"].every((prop) => closeEnough(restored[key][prop], operationResult[key][prop]));
    });
    report.draftReload = {
      promptShown,
      restoredMatches,
      groupRestored: Boolean(restored.title.groupId && restored.title.groupId === restored.subtitle.groupId),
      expected: {
        title: operationResult.title,
        subtitle: operationResult.subtitle,
        speaker: operationResult.speaker,
        org: operationResult.org,
      },
      actual: {
        title: restored.title,
        subtitle: restored.subtitle,
        speaker: restored.speaker,
        org: restored.org,
      },
      pass: promptShown && restoredMatches && Boolean(restored.title.groupId),
    };

    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(120);
    const undone = await page.evaluate(() => {
      const state = (selector) => {
        const el = document.querySelector(selector);
        const style = getComputedStyle(el);
        return {
          left: parseFloat(style.left), top: parseFloat(style.top), width: parseFloat(style.width),
          height: parseFloat(style.height), fontSize: parseFloat(style.fontSize), groupId: el.dataset.editGroup || "",
        };
      };
      return { title: state(".cover-center-title"), subtitle: state(".cover-center-subtitle") };
    });
    const undoMatches = ["title", "subtitle"].every((key) => {
      return ["left", "top", "width", "height", "fontSize"].every((prop) => closeEnough(undone[key][prop], baseline[key][prop]));
    });
    report.undoToBaseline = {
      geometryMatches: undoMatches,
      groupCleared: !undone.title.groupId && !undone.subtitle.groupId,
      pass: undoMatches && !undone.title.groupId && !undone.subtitle.groupId,
    };

    const revisionSetup = await page.evaluate(() => {
      const diagnostics = window.EditMode.diagnostics();
      localStorage.setItem(diagnostics.draftKey, JSON.stringify({
        schemaVersion: diagnostics.schemaVersion,
        revision: "wrong-revision",
        savedAt: Date.now(),
        entries: [{ key: "s1::0", left: "9999px", top: "9999px", width: "10px", height: "10px" }],
      }));
      return diagnostics;
    });
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await waitReady();
    const revisionResult = await page.evaluate((draftKey) => {
      const title = document.querySelector(".cover-center-title");
      const style = getComputedStyle(title);
      return {
        prompt: Boolean(document.getElementById("edit-draft-prompt")),
        draftRemoved: localStorage.getItem(draftKey) === null,
        title: { left: parseFloat(style.left), top: parseFloat(style.top), width: parseFloat(style.width), height: parseFloat(style.height) },
        diagnostics: window.EditMode.diagnostics(),
      };
    }, revisionSetup.draftKey);
    const revisionBaseline = ["left", "top", "width", "height"].every((prop) => closeEnough(revisionResult.title[prop], baseline.title[prop]));
    report.revisionIsolation = {
      promptSuppressed: !revisionResult.prompt,
      draftRemoved: revisionResult.draftRemoved,
      baselinePreserved: revisionBaseline,
      pass: !revisionResult.prompt && revisionResult.draftRemoved && revisionBaseline,
    };

    const entries = await page.evaluate(async () => {
      const title = document.querySelector(".cover-center-title");
      const rect = title.getBoundingClientRect();
      const init = { bubbles: true, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2, button: 0 };
      ["mousedown", "mouseup", "click"].forEach((type) => title.dispatchEvent(new MouseEvent(type, init)));
      document.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowRight" }));
      await new Promise((resolve) => setTimeout(resolve, 750));
      for (let index = 0; index < 106; index += 1) {
        if (index % 2 === 0) window.EditMode.undo();
        else window.EditMode.redo();
      }
      document.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "ArrowRight" }));
      await new Promise((resolve) => setTimeout(resolve, 750));
      return window.EditMode.diagnostics().entries;
    });
    report.operationLog = {
      limit: 100,
      count: entries.length,
      actions: [...new Set(entries.map((entry) => entry.action))],
      geometryRecorded: entries.some((entry) => entry.command?.items?.some((item) => item.before && item.after)),
      pass: entries.length === 100
        && entries.some((entry) => entry.action === "commit")
        && entries.some((entry) => entry.action === "undo"),
    };

    report.pass = [
      report.materialization,
      report.textEditGuides,
      report.operationChain,
      report.draftReload,
      report.undoToBaseline,
      report.revisionIsolation,
      report.operationLog,
    ].every((section) => section.pass);
  } finally {
    await browser.close();
  }

  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");
  console.log(JSON.stringify(report));
  if (!report.pass) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
