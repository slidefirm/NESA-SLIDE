const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { loadPlaywright, browserExecutable } = require("./playwright_runtime.cjs");

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
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({
    headless: true,
    executablePath: browserExecutable(),
    args: ["--allow-file-access-from-files"],
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());

  try {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "commit", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    await page.evaluate(() => Promise.race([
      document.fonts?.ready || Promise.resolve(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]));

    const result = await page.evaluate(async () => {
      const slides = [...document.querySelectorAll("#stage > .slide")];
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const visible = (el) => {
        if (!el) return false;
        const style = getComputedStyle(el);
        return el.getClientRects().length > 0 && style.display !== "none" && style.visibility !== "hidden";
      };
      const styleSnapshot = (el) => ({
        display: el ? getComputedStyle(el).display : null,
        inlineDisplay: el?.style?.display || "",
        displayPriority: el?.style?.getPropertyPriority("display") || "",
        contenteditable: el?.getAttribute("contenteditable") || null,
      });

      const textCandidates = slides
        .flatMap((slide) => [...slide.querySelectorAll('.el[data-edit-kind="text"][data-edit-fit="text"]')]);
      const textTarget = textCandidates.find(Boolean);
      if (textTarget) {
        textTarget.dataset.qaDeleteTarget = "true";
        const slide = textTarget.closest(".slide");
        window.setSlide(Number(slide.dataset.index));
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      }

      return {
        framework: {
          slideCount: slides.length,
          editor: Boolean(window.EditMode),
          backgroundSlideCount: slides.filter((slide) => slide.dataset.pptxBackgroundImage === "true").length,
        },
        textTarget: textTarget ? {
          text: textTarget.textContent,
          rect: (() => {
            const rect = textTarget.getBoundingClientRect();
            return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
          })(),
        } : null,
      };
    });

    if (result.textTarget) {
      await page.mouse.click(result.textTarget.rect.x, result.textTarget.rect.y);
      await page.waitForTimeout(100);
      const selected = await page.evaluate(() => {
        const target = document.querySelector('[data-qa-delete-target="true"]');
        const frame = document.getElementById("edit-selection-frame");
        return {
          ...styleSnapshotFor(target),
          selectionFrameVisible: Boolean(frame && getComputedStyle(frame).display !== "none"),
          selectionFrameMode: frame?.dataset.selectionMode || null,
        };

        function styleSnapshotFor(el) {
          if (!el) return { display: null, inlineDisplay: "", displayPriority: "", contenteditable: null };
          const style = getComputedStyle(el);
          return {
            display: style.display,
            inlineDisplay: el.style.display || "",
            displayPriority: el.style.getPropertyPriority("display") || "",
            contenteditable: el.getAttribute("contenteditable") || null,
          };
        }
      });
      await page.keyboard.press("Delete");
      await page.waitForTimeout(160);
      const afterDelete = await page.evaluate(() => {
        const target = document.querySelector('[data-qa-delete-target="true"]');
        const frame = document.getElementById("edit-selection-frame");
        const entries = window.EditMode.diagnostics().entries || [];
        const last = entries[entries.length - 1]?.command || null;
        return {
          ...styleSnapshotFor(target),
          text: target?.textContent || "",
          selectionFrameVisible: Boolean(frame && getComputedStyle(frame).display !== "none"),
          historyLabel: last?.label || null,
          deleted: Boolean(target && getComputedStyle(target).display === "none"
            && target.style.display === "none"
            && target.style.getPropertyPriority("display") === "important"),
        };

        function styleSnapshotFor(el) {
          if (!el) return { display: null, inlineDisplay: "", displayPriority: "", contenteditable: null };
          const style = getComputedStyle(el);
          return {
            display: style.display,
            inlineDisplay: el.style.display || "",
            displayPriority: el.style.getPropertyPriority("display") || "",
            contenteditable: el.getAttribute("contenteditable") || null,
          };
        }
      });
      await page.evaluate(() => window.EditMode.undo());
      await page.waitForTimeout(160);
      const afterUndo = await page.evaluate(() => {
        const target = document.querySelector('[data-qa-delete-target="true"]');
        return {
          ...styleSnapshotFor(target),
          restored: Boolean(target && getComputedStyle(target).display !== "none"),
        };

        function styleSnapshotFor(el) {
          if (!el) return { display: null, inlineDisplay: "", displayPriority: "", contenteditable: null };
          const style = getComputedStyle(el);
          return {
            display: style.display,
            inlineDisplay: el.style.display || "",
            displayPriority: el.style.getPropertyPriority("display") || "",
            contenteditable: el.getAttribute("contenteditable") || null,
          };
        }
      });
      result.textDelete = {
        selected,
        afterDelete,
        afterUndo,
        pass: selected.selectionFrameVisible && afterDelete.deleted && afterDelete.historyLabel === "刪除"
          && afterUndo.restored,
      };
    } else {
      result.textDelete = { targetFound: false, pass: false };
    }

    const maskResult = await page.evaluate(async () => {
      const slide = [...document.querySelectorAll("#stage > .slide")]
        .find((item) => item.dataset.pptxBackgroundImage === "true");
      if (!slide) return { targetFound: false, pass: false };
      window.setSlide(Number(slide.dataset.index));
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));

      const text = slide.querySelector('.el[data-edit-kind="text"], [data-edit-layer="text"]');
      const beforeForeground = text ? {
        color: getComputedStyle(text).color,
        opacity: getComputedStyle(text).opacity,
        display: getComputedStyle(text).display,
      } : null;
      const range = document.getElementById("edit-slide-mask-opacity");
      if (!range) return { targetFound: true, controlsFound: false, pass: false };
      range.value = "42";
      range.dispatchEvent(new Event("input", { bubbles: true }));
      range.dispatchEvent(new Event("change", { bubbles: true }));
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));

      const slideStyle = getComputedStyle(slide);
      const pseudo = getComputedStyle(slide, "::before");
      const afterForeground = text ? {
        color: getComputedStyle(text).color,
        opacity: getComputedStyle(text).opacity,
        display: getComputedStyle(text).display,
      } : null;
      const applied = {
        dataMask: slide.dataset.editorSlideMask || null,
        opacity: slide.dataset.editorSlideMaskOpacity || null,
        backgroundImagePresent: slideStyle.backgroundImage !== "none",
        pseudoContent: pseudo.content,
        pseudoDisplay: pseudo.display,
        pseudoOpacity: pseudo.opacity,
        pseudoZIndex: pseudo.zIndex,
        foregroundStable: JSON.stringify(beforeForeground) === JSON.stringify(afterForeground),
      };

      await window.EditMode.undo();
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const restored = {
        dataMask: slide.dataset.editorSlideMask || null,
        opacity: slide.dataset.editorSlideMaskOpacity || null,
        pseudoDisplay: getComputedStyle(slide, "::before").display,
      };
      return {
        targetFound: true,
        controlsFound: true,
        applied,
        restored,
        pass: applied.dataMask === "true"
          && applied.opacity === "0.42"
          && applied.backgroundImagePresent
          && applied.pseudoContent !== "none"
          && applied.pseudoDisplay !== "none"
          && applied.pseudoOpacity === "0.42"
          && applied.pseudoZIndex === "0"
          && applied.foregroundStable
          && restored.dataMask === null
          && restored.opacity === "0"
          && restored.pseudoDisplay === "none",
      };
    });
    result.slideMask = maskResult;
    result.pass = Boolean(result.textDelete?.pass && result.slideMask?.pass);
    await page.evaluate(() => {
      document.querySelector('[data-qa-delete-target="true"]')?.removeAttribute("data-qa-delete-target");
      localStorage.clear();
    });

    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(result, null, 2) + "\n", "utf8");
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
