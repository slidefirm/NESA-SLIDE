const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--screenshot") out.screenshot = argv[++index];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
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
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
  try {
    // Large self-contained decks can keep DOMContentLoaded pending while the
    // embedded editor source is parsed.  Navigation commit plus the renderer's
    // own ready flag is the stable contract used by the other HTML QA tools.
    await page.goto(options.url, { waitUntil: "commit", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });

    const result = await page.evaluate(async () => {
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      window.EditMode.toggle(true);
      await nextFrame();

      const visible = (el) => {
        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && rect.width > 12 && rect.height > 12;
      };
      const candidates = [...document.querySelectorAll("#stage > .slide.active .el")].filter((el) => (
        visible(el)
        && !el.hasAttribute("data-edit-layer")
        && !el.dataset.editGroup
        && !el.dataset.editComposite
        && el.dataset.editLayer !== "background"
      ));
      const targets = candidates.slice(0, 2);
      if (targets.length < 2) return { targetsFound: false, candidateCount: candidates.length, pass: false };

      const click = (el, shiftKey) => {
        const rect = el.getBoundingClientRect();
        const eventInit = {
          bubbles: true,
          cancelable: true,
          button: 0,
          shiftKey,
          clientX: rect.left + Math.min(rect.width / 2, 24),
          clientY: rect.top + Math.min(rect.height / 2, 24),
        };
        el.dispatchEvent(new MouseEvent("mousedown", eventInit));
        el.dispatchEvent(new MouseEvent("mouseup", eventInit));
        el.dispatchEvent(new MouseEvent("click", eventInit));
      };
      click(targets[0], false);
      click(targets[1], true);
      await nextFrame();

      const memberFrames = [...document.querySelectorAll(".edit-selection-member-frame")].filter((frame) => {
        const style = getComputedStyle(frame);
        return style.display !== "none" && style.visibility !== "hidden";
      });
      const outerFrame = document.getElementById("edit-selection-frame");
      const handles = [...document.querySelectorAll(".edit-resize-handle")].filter((handle) => (
        getComputedStyle(handle).display !== "none"
      ));
      const expectedSelectionRect = (target) => {
        const elementRect = target.getBoundingClientRect();
        const tightText = target.dataset.editFit === "text"
          && target.dataset.editFrameWidth !== "manual"
          && (target.textContent || "").trim();
        if (!tightText) return elementRect;
        const range = document.createRange();
        range.selectNodeContents(target);
        const textRect = range.getBoundingClientRect();
        return textRect.width > 0.5 && textRect.height > 0.5 ? textRect : elementRect;
      };
      const memberFramesMatch = targets.every((target) => {
        const targetRect = expectedSelectionRect(target);
        return memberFrames.some((frame) => {
          const frameRect = frame.getBoundingClientRect();
          return Math.abs(frameRect.left - targetRect.left) <= 2
            && Math.abs(frameRect.top - targetRect.top) <= 2
            && Math.abs(frameRect.width - targetRect.width) <= 2
            && Math.abs(frameRect.height - targetRect.height) <= 2;
        });
      });
      const memberFramesStyled = memberFrames.length === targets.length && memberFrames.every((frame) => {
        const style = getComputedStyle(frame);
        return parseFloat(style.borderTopWidth) >= 1
          && style.borderTopStyle === "dashed"
          && style.pointerEvents === "none"
          && style.boxShadow !== "none"
          && parseFloat(style.opacity) >= 0.9;
      });
      const selectedMemberOutlinesVisible = targets.every((target) => {
        const style = getComputedStyle(target);
        return parseFloat(style.outlineWidth) >= 2
          && style.outlineStyle === "solid"
          && style.outlineColor !== "rgba(0, 0, 0, 0)";
      });
      const outerFrameVisible = Boolean(outerFrame
        && getComputedStyle(outerFrame).display !== "none"
        && outerFrame.dataset.selectionMode === "multi");
      const outerRect = outerFrameVisible ? outerFrame.getBoundingClientRect() : null;
      const containsAllMembers = Boolean(outerRect) && memberFrames.every((frame) => {
        const rect = frame.getBoundingClientRect();
        return outerRect.left <= rect.left + 1
          && outerRect.top <= rect.top + 1
          && outerRect.right >= rect.right - 1
          && outerRect.bottom >= rect.bottom - 1;
      });

      const beforeDragRects = targets.map((target) => target.getBoundingClientRect());
      const dragOrigin = beforeDragRects[0];
      const dragStartX = dragOrigin.left + Math.min(dragOrigin.width / 2, 24);
      const dragStartY = dragOrigin.top + Math.min(dragOrigin.height / 2, 24);
      const dragEndX = dragStartX + 64;
      const dragEndY = dragStartY + 36;
      targets[0].dispatchEvent(new MouseEvent("mousedown", {
        bubbles: true,
        cancelable: true,
        button: 0,
        clientX: dragStartX,
        clientY: dragStartY,
      }));
      window.dispatchEvent(new MouseEvent("mousemove", {
        bubbles: true,
        cancelable: true,
        button: 0,
        clientX: dragEndX,
        clientY: dragEndY,
      }));
      window.dispatchEvent(new MouseEvent("mouseup", {
        bubbles: true,
        cancelable: true,
        button: 0,
        clientX: dragEndX,
        clientY: dragEndY,
      }));
      await nextFrame();
      const afterDragRects = targets.map((target) => target.getBoundingClientRect());
      const dragDeltas = afterDragRects.map((rect, index) => ({
        x: rect.left - beforeDragRects[index].left,
        y: rect.top - beforeDragRects[index].top,
      }));
      const movedTogether = Math.hypot(dragDeltas[0].x, dragDeltas[0].y) > 10
        && dragDeltas.every((delta) => (
          Math.abs(delta.x - dragDeltas[0].x) <= 1
          && Math.abs(delta.y - dragDeltas[0].y) <= 1
        ));
      const relativePositionPreserved = Math.abs(
        (afterDragRects[1].left - afterDragRects[0].left)
          - (beforeDragRects[1].left - beforeDragRects[0].left)
      ) <= 1 && Math.abs(
        (afterDragRects[1].top - afterDragRects[0].top)
          - (beforeDragRects[1].top - beforeDragRects[0].top)
      ) <= 1;
      const multiSelectionPreservedAfterDrag = document.getElementById("edit-selection-frame")?.dataset.selectionMode === "multi"
        && [...document.querySelectorAll(".edit-selection-member-frame")].filter((frame) => getComputedStyle(frame).display !== "none").length === targets.length;
      window.EditMode.undo();
      await nextFrame();
      const undoRects = targets.map((target) => target.getBoundingClientRect());
      const undoMovedAll = undoRects.every((rect, index) => (
        Math.abs(rect.left - beforeDragRects[index].left) <= 1
        && Math.abs(rect.top - beforeDragRects[index].top) <= 1
      ));
      window.EditMode.redo();
      await nextFrame();
      const redoRects = targets.map((target) => target.getBoundingClientRect());
      const redoMovedAll = redoRects.every((rect, index) => (
        Math.abs(rect.left - afterDragRects[index].left) <= 1
        && Math.abs(rect.top - afterDragRects[index].top) <= 1
      ));
      const multiDrag = {
        movedTogether,
        relativePositionPreserved,
        multiSelectionPreservedAfterDrag,
        undoMovedAll,
        redoMovedAll,
        deltas: dragDeltas,
        pass: movedTogether && relativePositionPreserved && multiSelectionPreservedAfterDrag && undoMovedAll && redoMovedAll,
      };

      const targetRect = targets[0].getBoundingClientRect();
      targets[0].dispatchEvent(new MouseEvent("contextmenu", {
        bubbles: true,
        cancelable: true,
        button: 2,
        clientX: targetRect.left + Math.min(targetRect.width / 2, 24),
        clientY: targetRect.top + Math.min(targetRect.height / 2, 24),
      }));
      await nextFrame();
      const contextMenu = document.getElementById("edit-object-context-menu");
      const contextGroupButton = contextMenu?.querySelector('[data-action="context-group"]');
      const contextMenuVisible = Boolean(contextMenu && getComputedStyle(contextMenu).display !== "none");
      const contextGroupAvailable = Boolean(
        contextGroupButton
        && getComputedStyle(contextGroupButton).display !== "none"
        && !contextGroupButton.disabled
      );
      contextGroupButton?.click();
      await nextFrame();
      const groupPaths = targets.map((target) => (target.dataset.editGroup || "").split(">").filter(Boolean));
      const contextGroupCreated = Boolean(groupPaths[0][0])
        && groupPaths.every((groupPath) => groupPath.length === 1 && groupPath[0] === groupPaths[0][0]);
      const groupedFrame = document.getElementById("edit-selection-frame");
      const newGroupSelected = groupedFrame?.dataset.selectionMode === "group";
      window.EditMode.ungroup();
      await nextFrame();
      const ungroupPreservedMultiSelection = targets.every((target) => !target.dataset.editGroup)
        && document.getElementById("edit-selection-frame")?.dataset.selectionMode === "multi";

      const pass = memberFrames.length === targets.length
        && memberFramesMatch
        && memberFramesStyled
        && selectedMemberOutlinesVisible
        && outerFrameVisible
        && containsAllMembers
        && handles.length === 8
        && multiDrag.pass
        && contextMenuVisible
        && contextGroupAvailable
        && contextGroupCreated
        && newGroupSelected
        && ungroupPreservedMultiSelection;
      return {
        targetsFound: true,
        targetCount: targets.length,
        memberFrameCount: memberFrames.length,
        memberFramesMatch,
        memberFramesStyled,
        selectedMemberOutlinesVisible,
        outerFrameVisible,
        containsAllMembers,
        handleCount: handles.length,
        multiDrag,
        contextMenuVisible,
        contextGroupAvailable,
        contextGroupCreated,
        newGroupSelected,
        ungroupPreservedMultiSelection,
        pass,
      };
    });

    if (options.screenshot) {
      const screenshotPath = path.resolve(options.screenshot);
      await fs.mkdir(path.dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path: screenshotPath, fullPage: true });
    }
    const reportPath = path.resolve(options.report);
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
