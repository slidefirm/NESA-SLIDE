const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
}

function near(a, b, tolerance = 1.2) {
  return Math.abs(a - b) <= tolerance;
}

async function main() {
  const options = argsOf(process.argv);
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  let result;
  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(options.url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    result = await page.evaluate(async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const near = (a, b, tolerance = 1.2) => Math.abs(a - b) <= tolerance;
      const slide = document.querySelector('.slide[data-layout-id="before-after"]');
      const members = slide ? [
        slide.querySelector(".compare-panel.before"),
        slide.querySelector(".compare-rail"),
        slide.querySelector(".compare-panel.after"),
      ].filter(Boolean) : [];
      if (!slide || members.length !== 3 || !window.EditMode) {
        return { pass: false, error: "before-after group fixture missing" };
      }
      window.setSlide(Number(slide.dataset.index));
      await frame();

      const fireClick = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0, shiftKey,
          clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      fireClick(members[0]);
      fireClick(members[1], true);
      fireClick(members[2], true);
      window.EditMode.group();
      await frame();

      const rects = () => members.map((el) => {
        const rect = el.getBoundingClientRect();
        const computedTransform = getComputedStyle(el).transform;
        const matrix = new DOMMatrixReadOnly(computedTransform === 'none' ? undefined : computedTransform);
        return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
          width: rect.width, height: rect.height, transform: el.style.transform || "",
          scaleX: Math.hypot(matrix.a, matrix.b), scaleY: Math.hypot(matrix.c, matrix.d) };
      });
      const bounds = (items) => ({
        left: Math.min(...items.map((item) => item.left)),
        top: Math.min(...items.map((item) => item.top)),
        right: Math.max(...items.map((item) => item.right)),
        bottom: Math.max(...items.map((item) => item.bottom)),
      });
      const dragHandle = async (handleName, dx, dy) => {
        const handle = document.querySelector(`.edit-resize-handle[data-handle="${handleName}"]`);
        const handleRect = handle?.getBoundingClientRect();
        if (!handle || !handleRect) return { pass: false, error: "handle missing" };
        const before = rects();
        const beforeBounds = bounds(before);
        const startX = handleRect.left + handleRect.width / 2;
        const startY = handleRect.top + handleRect.height / 2;
        handle.dispatchEvent(new MouseEvent("mousedown", {
          bubbles: true, button: 0, clientX: startX, clientY: startY,
        }));
        window.dispatchEvent(new MouseEvent("mousemove", {
          bubbles: true, button: 0, clientX: startX + dx, clientY: startY + dy,
        }));
        window.dispatchEvent(new MouseEvent("mouseup", {
          bubbles: true, button: 0, clientX: startX + dx, clientY: startY + dy,
        }));
        await frame();
        const after = rects();
        const afterBounds = bounds(after);
        const horizontal = handleName === "e" || handleName === "w";
        const memberAxisPass = after.every((item, index) => (
          horizontal
            ? item.width > before[index].width + 1 && near(item.height, before[index].height)
            : item.height > before[index].height + 1 && near(item.width, before[index].width)
        ));
        const anchorPass = handleName === "e" ? near(afterBounds.left, beforeBounds.left)
          : handleName === "w" ? near(afterBounds.right, beforeBounds.right)
            : handleName === "s" ? near(afterBounds.top, beforeBounds.top)
              : near(afterBounds.bottom, beforeBounds.bottom);
        const undistortedTransforms = after.every((item, index) => (
          near(item.scaleX, before[index].scaleX, 0.01) && near(item.scaleY, before[index].scaleY, 0.01)
        ));
        window.EditMode.undo();
        await frame();
        const restored = rects();
        const undoPass = restored.every((item, index) => (
          near(item.left, before[index].left) && near(item.top, before[index].top)
          && near(item.width, before[index].width) && near(item.height, before[index].height)
          && item.transform === before[index].transform
        ));
        return { pass: memberAxisPass && anchorPass && undistortedTransforms && undoPass,
          memberAxisPass, anchorPass, undistortedTransforms, undoPass, before, after };
      };

      const checks = {
        east: await dragHandle("e", 72, 0),
        west: await dragHandle("w", -72, 0),
        south: await dragHandle("s", 0, 72),
        north: await dragHandle("n", 0, -72),
      };
      return { pass: Object.values(checks).every((check) => check.pass),
        selectedMembers: members.length, checks };
    });
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }
  const reportPath = path.resolve(options.report);
  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, JSON.stringify({ url: options.url, ...result }, null, 2) + "\n", "utf8");
  console.log(JSON.stringify(result));
  if (!result.pass) process.exitCode = 1;
}

main()
  .then(() => process.exit(process.exitCode || 0))
  .catch((error) => {
    console.error(error.stack || error.message || String(error));
    process.exit(1);
  });
