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
  }
  if (!out.html || !out.report) throw new Error("--html and --report are required");
  return out;
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
  // The editor uses a fixed 1920×1080 slide coordinate system internally.
  // A smaller browser viewport keeps large multi-slide decks responsive while
  // preserving the same before/after geometry comparisons used below.
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
  try {
    const markup = await fs.readFile(htmlPath, "utf8");
    await page.setContent(markup, { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.waitForFunction(() => document.documentElement.dataset.layoutReady === "true", null, { timeout: 60000 });
    await page.evaluate(() => Promise.race([
      document.fonts?.ready || Promise.resolve(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]));
    const result = await page.evaluate(async () => {
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const slide = document.querySelector(".slide.active");
      if (!slide || !window.EditMode) throw new Error("Editable slide framework is unavailable");

      const makeText = (id, html, top, maxWidth) => {
        const el = document.createElement("div");
        el.id = id;
        el.className = "el qa-wrap-fixture";
        el.dataset.editKind = "text";
        el.dataset.editFit = "text";
        el.style.cssText = [
          "position:absolute",
          "left:120px",
          `top:${top}px`,
          "width:max-content",
          "height:auto",
          `max-width:${maxWidth}px`,
          "font-size:48px",
          "line-height:1.2",
          "font-family:var(--font-body)",
          "text-wrap:balance",
          "color:#111827",
          "z-index:999",
        ].join(";");
        el.innerHTML = html;
        slide.querySelector("[data-content-area]")?.appendChild(el) || slide.appendChild(el);
        return el;
      };

      const natural = makeText(
        "qa-natural-wrap",
        "沒有硬換行的文字在框變寬之後，應該自然補回上一行，而不是繼續維持平衡斷行",
        120,
        620,
      );
      const hard = makeText("qa-hard-break", "作者指定第一行<br>作者指定第二行", 420, 760);
      const fontGrow = makeText("qa-font-grow", "字級放大時保持目前這一行", 760, 1200);
      fontGrow.style.textAlign = "center";
      const fontGrowPeer = makeText("qa-font-grow-peer", "群組裡的第二行也不應突然換行", 840, 760);
      fontGrowPeer.style.left = "760px";
      fontGrowPeer.style.textAlign = "center";
      const orphan = makeText("qa-orphan-tail", "換".repeat(21), 40, 481);
      orphan.style.width = "481px";
      orphan.style.maxWidth = "481px";
      orphan.style.textWrap = "wrap";
      await nextFrame();

      const lineCount = (el) => {
        const tops = [];
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
          if (!walker.currentNode.textContent.trim()) continue;
          const range = document.createRange();
          range.selectNodeContents(walker.currentNode);
          Array.from(range.getClientRects()).forEach((rect) => {
            if (!tops.some((top) => Math.abs(top - rect.top) <= 1)) tops.push(rect.top);
          });
        }
        return tops.length;
      };
      const click = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = {
          bubbles: true,
          clientX: rect.left + Math.min(20, rect.width / 2),
          clientY: rect.top + Math.min(20, rect.height / 2),
          button: 0,
          shiftKey,
        };
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      const dragHandle = async (position, dx, dy) => {
        const handle = document.querySelector(`.edit-resize-handle[data-handle="${position}"]`);
        if (!handle || getComputedStyle(handle).display === "none") throw new Error(`Handle ${position} is unavailable`);
        const rect = handle.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, clientX: startX, clientY: startY, button: 0 }));
        window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: startX + dx, clientY: startY + dy, button: 0 }));
        window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: startX + dx, clientY: startY + dy, button: 0 }));
        await nextFrame();
      };

      const orphanBefore = {
        summary: window.getTextLineSummary?.(orphan) || null,
        fontSize: parseFloat(getComputedStyle(orphan).fontSize),
      };
      const orphanRepair = window.repairGeneratedTextOrphans?.(slide) || null;
      await nextFrame();
      const orphanAfter = {
        summary: window.getTextLineSummary?.(orphan) || null,
        fontSize: parseFloat(getComputedStyle(orphan).fontSize),
      };
      const orphanPass = Boolean(
        orphanBefore.summary?.orphan
        && !orphanAfter.summary?.orphan
        && orphanAfter.fontSize < orphanBefore.fontSize
        && orphanAfter.fontSize >= 36
        && orphan.dataset.aiOrphanAdjustedFont
        && orphanRepair?.adjusted >= 1
      );

      click(natural);
      await nextFrame();
      const naturalBefore = {
        lines: lineCount(natural),
        width: natural.getBoundingClientRect().width,
        textWrap: getComputedStyle(natural).textWrap,
        html: natural.innerHTML,
      };
      await dragHandle("e", 720, 0);
      const naturalAfter = {
        lines: lineCount(natural),
        width: natural.getBoundingClientRect().width,
        textWrap: getComputedStyle(natural).textWrap,
        wrapMode: natural.dataset.editWrapMode || "",
        html: natural.innerHTML,
      };
      const naturalPass = naturalBefore.lines > 1
        && naturalAfter.width > naturalBefore.width + 300
        && naturalAfter.lines < naturalBefore.lines
        && naturalAfter.wrapMode === "natural"
        && naturalAfter.textWrap !== "balance"
        && naturalAfter.html === naturalBefore.html;
      window.EditMode.undo();
      await nextFrame();
      const naturalUndoPass = lineCount(natural) === naturalBefore.lines
        && !natural.dataset.editWrapMode
        && getComputedStyle(natural).textWrap === naturalBefore.textWrap;

      click(hard);
      await nextFrame();
      const hardBefore = {
        lines: lineCount(hard),
        html: hard.innerHTML,
        width: hard.getBoundingClientRect().width,
      };
      const markerVisible = document.querySelectorAll(".edit-hard-break-marker").length === 1;
      await dragHandle("se", 180, 100);
      const hardAfter = {
        lines: lineCount(hard),
        html: hard.innerHTML,
        width: hard.getBoundingClientRect().width,
      };
      const proportionalPass = hardAfter.width > hardBefore.width
        && hardAfter.lines === hardBefore.lines
        && hardAfter.html === hardBefore.html;
      window.EditMode.undo();
      await nextFrame();

      click(natural);
      click(hard, true);
      window.EditMode.group();
      await nextFrame();
      const groupedBefore = {
        naturalLines: lineCount(natural),
        hardLines: lineCount(hard),
        naturalHtml: natural.innerHTML,
        hardHtml: hard.innerHTML,
      };
      await dragHandle("se", -120, -80);
      const groupScalePass = lineCount(natural) === groupedBefore.naturalLines
        && lineCount(hard) === groupedBefore.hardLines
        && natural.innerHTML === groupedBefore.naturalHtml
        && hard.innerHTML === groupedBefore.hardHtml;
      window.EditMode.undo();
      await nextFrame();

      click(fontGrow);
      await nextFrame();
      const fontGrowBefore = {
        lines: lineCount(fontGrow),
        width: fontGrow.getBoundingClientRect().width,
        fontSize: parseFloat(getComputedStyle(fontGrow).fontSize),
        center: fontGrow.getBoundingClientRect().left + fontGrow.getBoundingClientRect().width / 2,
      };
      window.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "]" }));
      await nextFrame();
      const fontGrowAfter = {
        lines: lineCount(fontGrow),
        width: fontGrow.getBoundingClientRect().width,
        fontSize: parseFloat(getComputedStyle(fontGrow).fontSize),
        center: fontGrow.getBoundingClientRect().left + fontGrow.getBoundingClientRect().width / 2,
      };
      const fontGrowPass = fontGrowBefore.lines === 1
        && fontGrowAfter.lines === fontGrowBefore.lines
        && fontGrowAfter.fontSize > fontGrowBefore.fontSize
        && fontGrowAfter.width > fontGrowBefore.width
        && Math.abs(fontGrowAfter.center - fontGrowBefore.center) <= 2;
      window.EditMode.undo();
      await nextFrame();
      const fontGrowUndoPass = lineCount(fontGrow) === fontGrowBefore.lines
        && Math.abs(fontGrow.getBoundingClientRect().width - fontGrowBefore.width) <= 2
        && Math.abs(parseFloat(getComputedStyle(fontGrow).fontSize) - fontGrowBefore.fontSize) <= 0.5;

      click(fontGrow);
      click(fontGrowPeer, true);
      window.EditMode.group();
      await nextFrame();
      const groupedFontBefore = [fontGrow, fontGrowPeer].map((el) => ({
        lines: lineCount(el),
        width: el.getBoundingClientRect().width,
        fontSize: parseFloat(getComputedStyle(el).fontSize),
        center: el.getBoundingClientRect().left + el.getBoundingClientRect().width / 2,
      }));
      window.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "]" }));
      await nextFrame();
      const groupedFontAfter = [fontGrow, fontGrowPeer].map((el) => ({
        lines: lineCount(el),
        width: el.getBoundingClientRect().width,
        fontSize: parseFloat(getComputedStyle(el).fontSize),
        center: el.getBoundingClientRect().left + el.getBoundingClientRect().width / 2,
      }));
      const groupedFontPass = groupedFontAfter.every((after, index) => (
        groupedFontBefore[index].lines === 1
        && after.lines === groupedFontBefore[index].lines
        && after.fontSize > groupedFontBefore[index].fontSize
        && after.width > groupedFontBefore[index].width
        && Math.abs(after.center - groupedFontBefore[index].center) <= 2
      ));
      window.EditMode.undo();
      await nextFrame();
      const groupedFontUndoPass = [fontGrow, fontGrowPeer].every((el, index) => (
        lineCount(el) === groupedFontBefore[index].lines
        && Math.abs(el.getBoundingClientRect().width - groupedFontBefore[index].width) <= 2
        && Math.abs(parseFloat(getComputedStyle(el).fontSize) - groupedFontBefore[index].fontSize) <= 0.5
      ));

      click(hard);
      await nextFrame();
      const markerRestored = document.querySelectorAll(".edit-hard-break-marker").length === 1;
      window.EditMode.toggle(false);
      await nextFrame();
      const markerHiddenInProjection = document.querySelectorAll(".edit-hard-break-marker").length === 0;
      window.EditMode.toggle(true);
      await nextFrame();

      natural.remove();
      hard.remove();
      fontGrow.remove();
      fontGrowPeer.remove();
      orphan.remove();
      return {
        html: location.href,
        orphanTail: { before: orphanBefore, after: orphanAfter, repair: orphanRepair, pass: orphanPass },
        naturalWrap: { before: naturalBefore, after: naturalAfter, undoPass: naturalUndoPass, pass: naturalPass && naturalUndoPass },
        hardBreak: { before: hardBefore, after: hardAfter, markerVisible, markerRestored, proportionalPass },
        groupScale: { pass: groupScalePass },
        fontSizeGrowth: { before: fontGrowBefore, after: fontGrowAfter, undoPass: fontGrowUndoPass, pass: fontGrowPass && fontGrowUndoPass },
        groupedFontSizeGrowth: {
          before: groupedFontBefore,
          after: groupedFontAfter,
          undoPass: groupedFontUndoPass,
          pass: groupedFontPass && groupedFontUndoPass,
        },
        projection: { markerHidden: markerHiddenInProjection },
        pass: orphanPass && naturalPass && naturalUndoPass && markerVisible && markerRestored
          && proportionalPass && groupScalePass && fontGrowPass && fontGrowUndoPass
          && groupedFontPass && groupedFontUndoPass && markerHiddenInProjection,
      };
    });

    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(result, null, 2));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
