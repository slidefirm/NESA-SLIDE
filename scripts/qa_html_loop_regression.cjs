const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { loadPlaywright, browserExecutable } = require("./playwright_runtime.cjs");
const { chromium } = loadPlaywright();

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
}

function near(a, b, tolerance = 2.5) {
  return Math.abs(a - b) <= tolerance;
}

async function waitReady(page) {
  await page.waitForFunction(() => (
    document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
  ), null, { timeout: 120000 });
}

async function main() {
  const options = argsOf(process.argv);
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = browserExecutable() || browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  const results = {};
  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(options.url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await waitReady(page);

    async function reload() {
      await page.reload({ waitUntil: "domcontentloaded", timeout: 30000 });
      await waitReady(page);
    }

    async function evaluateCase(name, fn) {
      try {
        results[name] = await page.evaluate(fn);
      } catch (error) {
        results[name] = { pass: false, error: error.stack || error.message || String(error) };
      }
    }

    await reload();
    await evaluateCase("contentContract", async () => {
      const slides = Array.from(document.querySelectorAll("#stage > .slide"));
      const slideChecks = slides.map((slide) => {
        const content = slide.querySelector(":scope > .content[data-content-area]");
        const fullBleed = slide.querySelector("[data-full-bleed-media=\"true\"]");
        const contentRect = content?.getBoundingClientRect();
        const contentCenter = contentRect ? {
          x: contentRect.left + contentRect.width / 2,
          y: contentRect.top + contentRect.height / 2,
        } : null;
        const contentEls = Array.from(slide.querySelectorAll(":scope > .content .el")).filter((el) => {
          const style = getComputedStyle(el);
          return style.display !== "none" && style.visibility !== "hidden" && el.getClientRects().length > 0;
        });
        const invalidContent = contentEls.filter((el) => {
          const rect = el.getBoundingClientRect();
          return !content.contains(el) || rect.left < contentRect.left - 2 || rect.right > contentRect.right + 2
            || rect.top < contentRect.top - 2 || rect.bottom > contentRect.bottom + 2;
        });
        const visibleRects = contentEls
          .filter((el) => !el.closest('[data-visual-balance-ignore="true"]'))
          .map((el) => el.getBoundingClientRect())
          .filter((rect) => rect.width > 0 && rect.height > 0);
        const union = visibleRects.length ? {
          left: Math.min(...visibleRects.map((rect) => rect.left)),
          top: Math.min(...visibleRects.map((rect) => rect.top)),
          right: Math.max(...visibleRects.map((rect) => rect.right)),
          bottom: Math.max(...visibleRects.map((rect) => rect.bottom)),
        } : null;
        const visualCenter = union ? {
          x: (union.left + union.right) / 2,
          y: (union.top + union.bottom) / 2,
        } : null;
        const layoutOnlyInvalid = Array.from(slide.querySelectorAll('[data-edit-layout-only="true"]')).filter((el) => (
          el.classList.contains("el") || el.hasAttribute("data-edit-layer") || el.hasAttribute("data-edit-composite")
        ));
        const forbiddenAggregates = slide.querySelectorAll('.el[data-edit-structure="group"],.el[data-edit-role="title-group"],.el[data-edit-role="content-group"],.el[data-edit-role="extra-group"]').length;
        const retiredRepeatAttributes = slide.querySelectorAll('[data-edit-repeat-group],[data-edit-repeat-layout],[data-edit-repeat-connectors]').length;
        return {
          id: slide.id,
          layout: slide.dataset.layoutId || "",
          contentCount: slide.querySelectorAll(":scope > .content[data-content-area]").length,
          fullBleed: Boolean(fullBleed),
          contentBoundsPass: Boolean(contentRect) && invalidContent.length === 0,
          centerPass: Boolean(!visualCenter || (near(visualCenter.x, contentCenter.x, 5) && near(visualCenter.y, contentCenter.y, 5))),
          fillRatio: contentRect && union ? ((union.right - union.left) * (union.bottom - union.top)) / (contentRect.width * contentRect.height) : null,
          invalidContent: invalidContent.slice(0, 5).map((el) => el.className),
          layoutOnlyInvalid: layoutOnlyInvalid.map((el) => el.className),
          forbiddenAggregates,
          retiredRepeatAttributes,
        };
      });
      return {
        pass: slideChecks.length > 0 && slideChecks.every((item) => item.contentCount === 1 && item.contentBoundsPass && item.centerPass && item.layoutOnlyInvalid.length === 0 && item.forbiddenAggregates === 0 && item.retiredRepeatAttributes === 0),
        slides: slideChecks,
      };
    });

    await reload();
    await evaluateCase("manualGroupUngroupHistory", async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const slide = document.querySelector("#s3");
      const members = slide ? Array.from(slide.querySelectorAll(".content-priority-card")).slice(0, 2) : [];
      if (members.length !== 2) return { pass: false, error: "priority-card fixture missing" };
      const fireClick = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0, shiftKey, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      const state = () => {
        const frameEl = document.querySelector("#edit-selection-frame");
        const badge = document.querySelector("#edit-selection-badge [data-role=label]");
        return {
          mode: frameEl?.dataset.selectionMode || "",
          memberFrameCount: Number(frameEl?.dataset.memberFrameCount || 0),
          badge: badge?.textContent?.trim() || "",
          groupIds: members.map((el) => el.dataset.editGroup || ""),
        };
      };
      window.setSlide(2);
      await frame();
      fireClick(members[0]);
      fireClick(members[1], true);
      await frame();
      const multi = state();
      window.EditMode.group();
      await frame();
      const grouped = state();
      const groupId = members[0].dataset.editGroup;
      window.EditMode.ungroup();
      await frame();
      const ungrouped = state();
      const ungroupSelectedAll = ungrouped.mode === "multi" && ungrouped.memberFrameCount === 2
        && members.every((el) => !el.dataset.editGroup);
      window.EditMode.undo();
      await frame();
      const undoGrouped = state();
      window.EditMode.redo();
      await frame();
      const redoUngrouped = state();
      return {
        pass: multi.mode === "multi" && grouped.mode === "group" && Boolean(groupId)
          && ungroupSelectedAll && undoGrouped.mode === "group" && redoUngrouped.mode === "multi" && redoUngrouped.memberFrameCount === 2,
        checks: { multi, grouped, ungrouped, undoGrouped, redoUngrouped, groupId, ungroupSelectedAll },
      };
    });

    await reload();
    await evaluateCase("generatedGroupUngroup", async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const slide = document.querySelector("#s3");
      const group = slide?.querySelector(".content-priority-card");
      if (!group) return { pass: false, error: "generated semantic module fixture missing" };
      const members = Array.from(group.querySelectorAll(":scope > [data-edit-layer]")).filter((el) => getComputedStyle(el).display !== "none");
      const fireClick = (el) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      window.setSlide(2);
      await frame();
      fireClick(group);
      await frame();
      const selectionFrame = document.querySelector("#edit-selection-frame");
      const selectedGroup = {
        mode: selectionFrame?.dataset.selectionMode || "",
        memberFrameCount: Number(selectionFrame?.dataset.memberFrameCount || 0),
      };
      window.EditMode.ungroup();
      await frame();
      const afterFrame = document.querySelector("#edit-selection-frame");
      const after = {
        mode: afterFrame?.dataset.selectionMode || "",
        memberFrameCount: Number(afterFrame?.dataset.memberFrameCount || 0),
        visibleMemberFrames: document.querySelectorAll(".edit-selection-member-frame[style*='display: block']").length,
      };
      const expected = members.length;
      return {
        pass: selectedGroup.mode === "group" && after.mode === "multi" && after.memberFrameCount === expected && after.visibleMemberFrames >= expected,
        expectedMembers: expected,
        selectedGroup,
        after,
        memberClasses: members.map((el) => el.className),
      };
    });

    await reload();
    await evaluateCase("groupResizeCollision", async () => {
      const near = (a, b, tolerance = 2.5) => Math.abs(a - b) <= tolerance;
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const slide = document.querySelector("#s3");
      const members = slide ? Array.from(slide.querySelectorAll(".content-priority-card")).slice(0, 2) : [];
      if (members.length !== 2) return { pass: false, error: "priority-card fixture missing" };
      const fireClick = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0, shiftKey, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      const textSnapshot = () => members.map((member) => {
        const root = member.getBoundingClientRect();
        const text = Array.from(member.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')).map((node) => {
          const rect = node.getBoundingClientRect();
          const style = getComputedStyle(node);
          return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, fontSize: parseFloat(style.fontSize), lineHeight: parseFloat(style.lineHeight), transform: node.style.transform || "" };
        });
        return { left: root.left, top: root.top, right: root.right, bottom: root.bottom, width: root.width, height: root.height, text };
      });
      const fits = (snapshot) => snapshot.every((member) => {
        if (member.text.some((item) => item.left < member.left - 2 || item.right > member.right + 2 || item.top < member.top - 2 || item.bottom > member.bottom + 2)) return false;
        for (let first = 0; first < member.text.length; first += 1) {
          for (let second = first + 1; second < member.text.length; second += 1) {
            const horizontal = Math.min(member.text[first].right, member.text[second].right) - Math.max(member.text[first].left, member.text[second].left);
            const vertical = Math.min(member.text[first].bottom, member.text[second].bottom) - Math.max(member.text[first].top, member.text[second].top);
            if (horizontal > 1 && vertical > 1) return false;
          }
        }
        return true;
      });
      const drag = async (name, dx, dy) => {
        const handle = document.querySelector(`.edit-resize-handle[data-handle="${name}"]`);
        if (!handle) return false;
        const rect = handle.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, button: 0, clientX: x, clientY: y }));
        window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, button: 0, clientX: x + dx, clientY: y + dy }));
        window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: x + dx, clientY: y + dy }));
        await frame();
        return true;
      };
      window.setSlide(2);
      await frame();
      fireClick(members[0]);
      fireClick(members[1], true);
      window.EditMode.group();
      await frame();
      const before = textSnapshot();
      const moderateHandle = await drag("s", 0, -before[0].height * 0.20);
      const moderate = textSnapshot();
      const moderatePass = moderateHandle && moderate.every((item, index) => item.height < before[index].height - 5)
        && fits(moderate) && moderate.some((item, index) => item.text.some((text, textIndex) => text.transform !== before[index].text[textIndex].transform));
      window.EditMode.undo();
      await frame();
      const restored = textSnapshot();
      const undoPass = restored.every((item, index) => near(item.left, before[index].left) && near(item.top, before[index].top)
        && near(item.width, before[index].width) && near(item.height, before[index].height));
      const deepHandle = await drag("s", 0, -before[0].height * 0.55);
      const deep = textSnapshot();
      const deepFontReduced = deep.some((item, index) => item.text.some((text, textIndex) => text.fontSize < before[index].text[textIndex].fontSize - 0.5));
      const deepPass = deepHandle && deepFontReduced && fits(deep);
      return {
        pass: moderatePass && undoPass && deepPass,
        checks: { moderatePass, undoPass, deepPass, moderateHandle, deepHandle, deepFontReduced, moderateFits: fits(moderate), deepFits: fits(deep) },
        before, moderate, restored, deep,
      };
    });
    await reload();
    await evaluateCase("manualMultiSelectionResize", async () => {
      const near = (a, b, tolerance = 2.5) => Math.abs(a - b) <= tolerance;
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const slide = document.querySelector("#s2");
      const content = slide?.querySelector(":scope > .content[data-content-area]");
      const rows = slide ? Array.from(slide.querySelectorAll(".toc-panel-row")).slice(0, 4) : [];
      if (!content || rows.length !== 4) return { pass: false, error: "semantic-module multi-selection fixture missing" };
      const fireClick = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0, shiftKey, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      const rectOf = (el) => {
        const rect = el?.getBoundingClientRect();
        return rect ? { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height } : null;
      };
      const snapshot = () => ({
        selection: rectOf(document.querySelector("#edit-selection-frame")),
        rows: rows.map(rectOf),
        selectionMode: document.querySelector("#edit-selection-frame")?.dataset.selectionMode || "",
      });
      const inside = (inner, outer) => Boolean(inner && outer
        && inner.left >= outer.left - 2 && inner.right <= outer.right + 2
        && inner.top >= outer.top - 2 && inner.bottom <= outer.bottom + 2);
      const rowsInsideSelection = (state) => state.rows.every((row) => inside(row, state.selection));
      const sameRows = (first, second) => first.every((item, index) => near(item.left, second[index].left)
        && near(item.top, second[index].top) && near(item.width, second[index].width) && near(item.height, second[index].height));
      const drag = async (name, dx) => {
        const handle = document.querySelector(`.edit-resize-handle[data-handle="${name}"]`);
        if (!handle) return false;
        const rect = handle.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, button: 0, clientX: x, clientY: y }));
        window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, button: 0, clientX: x + dx, clientY: y }));
        window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: x + dx, clientY: y }));
        await frame();
        return true;
      };
      window.setSlide(1);
      await frame();
      fireClick(rows[0]);
      for (const row of rows.slice(1)) fireClick(row, true);
      await frame();
      const before = snapshot();
      const dragged = await drag("e", -Math.max(180, (before.selection?.width || 720) * 0.30));
      const after = snapshot();
      const contentRect = rectOf(content);
      const bounded = inside(after.selection, contentRect);
      const rowsInside = rowsInsideSelection(after);
      window.EditMode.undo();
      await frame();
      const undo = snapshot();
      const undoPass = sameRows(before.rows, undo.rows);
      window.EditMode.redo();
      await frame();
      const redo = snapshot();
      const redoPass = sameRows(after.rows, redo.rows) && rowsInsideSelection(redo);
      return {
        pass: before.selectionMode === "multi" && dragged && bounded && rowsInside && undoPass && redoPass,
        checks: { multiSelected: before.selectionMode === "multi", dragged, bounded, rowsInside, undoPass, redoPass },
        before,
        after,
        undo,
        redo,
      };
    });

    await reload();
    await evaluateCase("manualSemanticModuleGroupBoundary", async () => {
      const near = (a, b, tolerance = 2.5) => Math.abs(a - b) <= tolerance;
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const slide = document.querySelector("#s2");
      const content = slide?.querySelector(":scope > .content[data-content-area]");
      const rows = slide ? Array.from(slide.querySelectorAll(".toc-panel-row")).slice(0, 4) : [];
      if (!content || rows.length !== 4) return { pass: false, error: "toc semantic-module fixture missing" };
      const fireClick = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0, shiftKey, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      const rectOf = (el) => {
        const rect = el?.getBoundingClientRect();
        return rect ? { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height } : null;
      };
      const snapshot = () => ({
        content: rectOf(content),
        selection: rectOf(document.querySelector("#edit-selection-frame")),
        rows: rows.map(rectOf),
        text: rows.map((row) => Array.from(row.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')).map(rectOf)),
      });
      const inside = (inner, outer) => Boolean(inner && outer
        && inner.left >= outer.left - 2 && inner.right <= outer.right + 2
        && inner.top >= outer.top - 2 && inner.bottom <= outer.bottom + 2);
      const rowsDoNotOverlap = (items) => items.every((item, first) => items.slice(first + 1).every((other) => {
        const horizontal = Math.min(item.right, other.right) - Math.max(item.left, other.left);
        const vertical = Math.min(item.bottom, other.bottom) - Math.max(item.top, other.top);
        return horizontal <= 1 || vertical <= 1;
      }));
      const textFits = (items, textItems) => items.every((item, index) => textItems[index].every((text) => inside(text, item)));
      const sameRows = (first, second) => first.every((item, index) => near(item.left, second[index].left)
        && near(item.top, second[index].top) && near(item.width, second[index].width) && near(item.height, second[index].height));
      const drag = async (name, dx, dy) => {
        const handle = document.querySelector(`.edit-resize-handle[data-handle="${name}"]`);
        if (!handle) return false;
        const rect = handle.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, button: 0, clientX: x, clientY: y }));
        window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, button: 0, clientX: x + dx, clientY: y + dy }));
        window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: x + dx, clientY: y + dy }));
        await frame();
        return true;
      };
      window.setSlide(1);
      await frame();
      fireClick(rows[0]);
      for (const row of rows.slice(1)) fireClick(row, true);
      await frame();
      window.EditMode.group();
      await frame();
      const selectionFrame = document.querySelector("#edit-selection-frame");
      const selectedAsGroup = selectionFrame?.dataset.selectionMode === "group";
      const before = snapshot();
      const handleDragged = await drag("n", 0, -Math.max(180, (before.selection?.height || 360) * 0.55));
      const after = snapshot();
      const bounded = inside(after.selection, after.content);
      const rowsInside = after.rows.every((item) => inside(item, after.content));
      const afterPass = handleDragged && bounded && rowsInside && rowsDoNotOverlap(after.rows)
        && textFits(after.rows, after.text) && after.selection.height <= after.content.height + 2;
      window.EditMode.undo();
      await frame();
      const undo = snapshot();
      const undoPass = sameRows(before.rows, undo.rows);
      window.EditMode.redo();
      await frame();
      const redo = snapshot();
      const redoPass = sameRows(after.rows, redo.rows) && inside(redo.selection, redo.content);
      return {
        pass: selectedAsGroup && afterPass && undoPass && redoPass,
        checks: { selectedAsGroup, handleDragged, bounded, rowsInside, rowsDoNotOverlap: rowsDoNotOverlap(after.rows), textFits: textFits(after.rows, after.text), afterHeightWithinContent: after.selection.height <= after.content.height + 2, undoPass, redoPass },
        before,
        after,
        undo,
        redo,
      };
    });
    await reload();
    await evaluateCase("groupAlignWholeObject", async () => {
      const near = (a, b, tolerance = 2.5) => Math.abs(a - b) <= tolerance;
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const slide = document.querySelector("#s3");
      const members = slide ? Array.from(slide.querySelectorAll(".content-priority-card")).slice(0, 2) : [];
      const alignButton = document.querySelector('[data-align-selection-mode="centerX"]');
      if (members.length !== 2 || !alignButton) return { pass: false, error: "alignment fixture missing" };
      const fireClick = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0, shiftKey, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      const boxes = () => members.map((el) => { const rect = el.getBoundingClientRect(); return { left: rect.left, top: rect.top, width: rect.width, height: rect.height, center: rect.left + rect.width / 2 }; });
      const union = (items) => ({ left: Math.min(...items.map((item) => item.left)), right: Math.max(...items.map((item) => item.left + item.width)) });
      window.setSlide(2);
      await frame();
      fireClick(members[0]);
      fireClick(members[1], true);
      window.EditMode.group();
      await frame();
      const before = boxes();
      const beforeRelative = before[1].center - before[0].center;
      alignButton.click();
      await frame();
      const after = boxes();
      const slideRect = slide.getBoundingClientRect();
      const afterUnion = union(after);
      const slideCenter = slideRect.left + slideRect.width / 2;
      const afterRelative = after[1].center - after[0].center;
      const aligned = near((afterUnion.left + afterUnion.right) / 2, slideCenter, 4);
      const relativePreserved = near(afterRelative, beforeRelative, 2);
      window.EditMode.undo();
      await frame();
      const undo = boxes();
      const undoPass = undo.every((item, index) => near(item.left, before[index].left) && near(item.top, before[index].top));
      window.EditMode.redo();
      await frame();
      const redo = boxes();
      const redoPass = redo.every((item, index) => near(item.left, after[index].left) && near(item.top, after[index].top));
      return { pass: aligned && relativePreserved && undoPass && redoPass, checks: { aligned, relativePreserved, undoPass, redoPass, slideCenter, before, after, undo, redo } };
    });

    await reload();
    await evaluateCase("circleNumberHorizontalAlignment", async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      window.setSlide(5);
      await frame();
      const slide = document.querySelector("#s6");
      const metrics = slide ? Array.from(slide.querySelectorAll(".sequence-process-node > .circle-number-metric")) : [];
      const bodyText = slide ? Array.from(slide.querySelectorAll(".sequence-process-node > b, .sequence-process-node > p")) : [];
      const metricStyles = metrics.map((el) => {
        const box = el.getBoundingClientRect();
        const range = document.createRange();
        range.selectNodeContents(el);
        const glyph = range.getBoundingClientRect();
        return {
          textAlign: getComputedStyle(el).textAlign,
          declared: el.dataset.editHorizontalAlign || "",
          inline: el.style.textAlign || "",
          glyphOffset: (glyph.left + glyph.width / 2) - (box.left + box.width / 2),
        };
      });
      const bodyStyles = bodyText.map((el) => getComputedStyle(el).textAlign);
      const pass = metrics.length === 5
        && metricStyles.every((item) => item.textAlign === "center" && item.declared === "center" && item.inline === "center" && Math.abs(item.glyphOffset) <= 1)
        && bodyStyles.every((value) => value !== "center");
      return { pass, metricStyles, bodyStyles };
    });


    await reload();
    await evaluateCase("editorChromeAndMaterialization", async () => {
      const selectionFrames = Array.from(document.querySelectorAll(".edit-selection-member-frame"));
      const helperNodes = Array.from(document.querySelectorAll('[data-edit-layout-only="true"]'));
      const generatedGroups = Array.from(document.querySelectorAll('.el[data-edit-structure="module"][data-edit-composite]'));
      const visibleHelper = helperNodes.filter((el) => {
        const style = getComputedStyle(el);
        const hasPaint = style.backgroundImage !== "none"
          || (style.backgroundColor !== "transparent" && !style.backgroundColor.endsWith(", 0)"))
          || ["borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth"].some((key) => parseFloat(style[key]) > 0)
          || style.boxShadow !== "none" || style.outlineStyle !== "none";
        return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0" && hasPaint;
      });
      const layers = Array.from(document.querySelectorAll("[data-edit-layer]"));
      const wrongLayerPosition = layers.filter((el) => el.dataset.editPosition !== "absolute");
      const wrongTextAlign = layers.filter((el) => ["text", "metric"].includes(el.dataset.editLayer) && !["start", "center", "end"].includes(el.dataset.editVerticalAlign));
      return {
        pass: generatedGroups.length > 0 && visibleHelper.length === 0 && helperNodes.every((el) => !el.classList.contains("el") && !el.hasAttribute("data-edit-layer") && !el.hasAttribute("data-edit-composite")) && wrongLayerPosition.length === 0 && wrongTextAlign.length === 0,
        generatedGroups: generatedGroups.length,
        selectionFrames: selectionFrames.length,
        helperNodes: helperNodes.length,
        helperEditableNodes: helperNodes.filter((el) => el.classList.contains("el") || el.hasAttribute("data-edit-layer") || el.hasAttribute("data-edit-composite")).length,
        visibleHelper: visibleHelper.length,
        wrongLayerPosition: wrongLayerPosition.slice(0, 10).map((el) => el.outerHTML.slice(0, 160)),
        wrongTextAlign: wrongTextAlign.slice(0, 10).map((el) => el.outerHTML.slice(0, 160)),
      };
    });
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }
  const pass = Object.values(results).every((item) => item && item.pass === true);
  const reportPath = path.resolve(options.report);
  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  const output = { url: options.url, pass, checks: results };
  await fs.writeFile(reportPath, JSON.stringify(output, null, 2) + "\n", "utf8");
  console.log(JSON.stringify(output));
  if (!pass) process.exitCode = 1;
}

main()
  .then(() => process.exit(process.exitCode || 0))
  .catch((error) => {
    console.error(error.stack || error.message || String(error));
    process.exit(1);
  });
