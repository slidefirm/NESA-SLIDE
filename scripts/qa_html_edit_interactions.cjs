const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const os = require("node:os");
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
    // embedded editor and all slide markup are parsed. Start checking as soon
    // as navigation commits, then wait on the renderer's actual ready signal.
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "commit", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    await page.evaluate(() => Promise.race([
      document.fonts?.ready || Promise.resolve(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]));
    const result = await page.evaluate(async () => {
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const fireClick = (el) => {
        // Projection metadata was retired from slide content. Older QA used
        // the meta label as an empty click target; the active slide is now
        // the canonical selection-clear target.
        if (!el) el = document.querySelector("#stage > .slide.active");
        if (!el) throw new Error("No active slide available for QA click");
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, {
          bubbles: true, clientX: 360, clientY: 240, button: 0,
        })));
      };
      const activate = (el) => {
        const slide = el.closest(".slide");
        window.setSlide(Number(slide.dataset.index));
        return slide;
      };
      const snapshot = () => {
        const stage = document.getElementById("stage");
        const canvas = document.getElementById("canvasBox");
        const stageRect = stage.getBoundingClientRect();
        const canvasRect = canvas.getBoundingClientRect();
        return {
          transform: getComputedStyle(stage).transform,
          stageWidth: stageRect.width,
          stageHeight: stageRect.height,
          canvasWidth: canvasRect.width,
          canvasHeight: canvasRect.height,
        };
      };
      const measureTextBoundary = (el) => {
        const range = document.createRange();
        range.selectNodeContents(el);
        const box = el.getBoundingClientRect();
        const text = range.getBoundingClientRect();
        return {
          widthDifference: Math.round((box.width - text.width) * 10) / 10,
          heightDifference: Math.round((box.height - text.height) * 10) / 10,
        };
      };

      const slideIds = [...document.querySelectorAll("#stage > .slide")].map((slide) => slide.id);
      const framework = {
        slides: slideIds.length,
        uniqueSlideIds: new Set(slideIds).size,
        editMode: Boolean(window.EditMode),
        historyLimit: window.EditMode?.historyLimit || 0,
        toolbar: Boolean(document.getElementById("barInner")),
        autoLayoutsMaterialized: [...document.querySelectorAll("#stage > .slide [data-auto-layout]")]
          .every((area) => area.dataset.layoutMaterialized === "true"),
      };

      const editSnapshot = snapshot();
      window.EditMode.toggle(false);
      await nextFrame();
      const presentationSnapshot = snapshot();
      window.EditMode.toggle(true);
      await nextFrame();
      const restoredSnapshot = snapshot();
      const modeScaleStable = JSON.stringify(editSnapshot) === JSON.stringify(restoredSnapshot)
        && presentationSnapshot.stageWidth > 0
        && presentationSnapshot.stageHeight > 0
        && Math.abs(
          presentationSnapshot.stageWidth / presentationSnapshot.stageHeight
          - editSnapshot.stageWidth / editSnapshot.stageHeight
        ) < 0.001;

      const controlTarget = document.querySelector('#stage > .slide .page-title[data-edit-fit="text"]');
      let selectionControls = { targetFound: Boolean(controlTarget), pass: false };
      if (controlTarget) {
        const slide = activate(controlTarget);
        await nextFrame();
        fireClick(controlTarget);
        await nextFrame();
        const badge = document.getElementById('edit-selection-badge');
        const frame = document.getElementById('edit-selection-frame');
        const fontInput = document.getElementById('edit-font-size-input');
        const frameWidthInput = document.getElementById('edit-frame-width-input');
        const plusButton = fontInput?.parentElement?.querySelector('button:last-of-type');
        const beforeFont = parseFloat(getComputedStyle(controlTarget).fontSize);
        const badgeVisible = Boolean(badge && getComputedStyle(badge).display !== 'none');
        const frameVisible = Boolean(frame && getComputedStyle(frame).display !== 'none');
        const handlesVisible = [...document.querySelectorAll('.edit-resize-handle')]
          .filter((handle) => getComputedStyle(handle).display !== 'none').length === 8;
        const fontControlVisible = Boolean(fontInput && getComputedStyle(fontInput.parentElement).display !== 'none');
        const frameWidthControlVisible = Boolean(frameWidthInput && getComputedStyle(frameWidthInput.parentElement).display !== 'none');
        plusButton?.click();
        await nextFrame();
        const fontControlUsable = parseFloat(getComputedStyle(controlTarget).fontSize) > beforeFont;
        window.EditMode.undo();
        await nextFrame();
        const undoPass = Math.abs(parseFloat(getComputedStyle(controlTarget).fontSize) - beforeFont) <= 0.1;
        window.EditMode.redo();
        await nextFrame();
        const redoPass = parseFloat(getComputedStyle(controlTarget).fontSize) > beforeFont;
        window.EditMode.undo();
        await nextFrame();
        fireClick(slide.querySelector('.meta'));
        selectionControls = {
          targetFound: true,
          badgeVisible,
          frameVisible,
          handlesVisible,
          fontControlVisible,
          frameWidthControlVisible,
          fontControlUsable,
          undoPass,
          redoPass,
          pass: badgeVisible && frameVisible && handlesVisible && fontControlVisible
            && !frameWidthControlVisible && fontControlUsable && undoPass && redoPass,
        };
      }

      const fitTarget = document.querySelector('#stage > .slide .page-title[data-edit-fit="text"]');
      let textFit = { targetFound: Boolean(fitTarget), pass: false };
      if (fitTarget) {
        const slide = activate(fitTarget);
        await nextFrame();
        const original = fitTarget.innerHTML;
        fireClick(fitTarget);
        fireClick(fitTarget);
        await nextFrame();
        const editable = fitTarget.getAttribute("contenteditable") === "true";
        const editingFrame = document.getElementById('edit-selection-frame');
        const editingFrameRect = editingFrame?.getBoundingClientRect();
        const targetRange = document.createRange();
        targetRange.selectNodeContents(fitTarget);
        const targetRect = targetRange.getBoundingClientRect();
        const editingFrameVisible = Boolean(editingFrame && getComputedStyle(editingFrame).display !== 'none');
        const editingFrameMode = editingFrame?.dataset.selectionMode === 'text-edit';
        const editingFrameMatches = Boolean(editingFrameRect)
          && Math.abs(editingFrameRect.left - targetRect.left) <= 3
          && Math.abs(editingFrameRect.top - targetRect.top) <= 3
          && Math.abs(editingFrameRect.width - targetRect.width) <= 3
          && Math.abs(editingFrameRect.height - targetRect.height) <= 3;
        fitTarget.innerHTML = original + "｜互動 QA 延長文字";
        fitTarget.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: "QA" }));
        await nextFrame();
        const afterEdit = measureTextBoundary(fitTarget);
        fireClick(slide.querySelector(".meta"));
        window.EditMode.undo();
        await nextFrame();
        const undoPass = fitTarget.innerHTML === original;
        window.EditMode.redo();
        await nextFrame();
        const redoPass = fitTarget.innerHTML !== original;
        window.EditMode.undo();
        textFit = {
          targetFound: true,
          editable,
          editingFrameVisible,
          editingFrameMode,
          editingFrameMatches,
          afterEdit,
          undoPass,
          redoPass,
          pass: editable && editingFrameVisible && editingFrameMode && editingFrameMatches
            && Math.abs(afterEdit.widthDifference) <= 4
            && Math.abs(afterEdit.heightDifference) <= 4 && undoPass && redoPass,
        };
      }

      const layerTarget = document.querySelector('#stage > .slide .demo-card [data-edit-layer="text"].card-title');
      let compositeLayer = { targetFound: Boolean(layerTarget), pass: false };
      if (layerTarget) {
        const slide = activate(layerTarget);
        const root = layerTarget.closest(".demo-card");
        const original = layerTarget.innerHTML;
        const isVisible = (item) => {
          const style = getComputedStyle(item);
          return item.getClientRects().length > 0
            && style.display !== 'none'
            && style.visibility !== 'hidden';
        };
        const generatedMembers = [
          ...[...root.querySelectorAll('.el')].filter((item) => (
            item.parentElement?.closest('.el') === root && isVisible(item)
          )),
          ...[...root.querySelectorAll('[data-edit-layer]')].filter((item) => (
            item.closest('.el') === root && isVisible(item)
          )),
        ];
        fireClick(root);
        window.EditMode.ungroup();
        await nextFrame();
        const ungroupedFrame = document.getElementById('edit-selection-frame');
        const ungroupedMemberFrames = [...document.querySelectorAll('.edit-selection-member-frame')]
          .filter((frame) => getComputedStyle(frame).display !== 'none');
        const generatedUngroupTotalMemberFrames = document.querySelectorAll('.edit-selection-member-frame').length;
        const generatedUngroupDeclaredMemberFrames = Number(ungroupedFrame?.dataset.memberFrameCount || 0);
        const generatedUngroupOutlinedMembers = generatedMembers.filter((member) => parseFloat(getComputedStyle(member).outlineWidth) >= 1).length;
        const generatedUngroupSelectionMode = ungroupedFrame?.dataset.selectionMode || '';
        const generatedUngroupMemberFrameCount = ungroupedMemberFrames.length;
        const generatedRootStateUngrouped = root.dataset.editGroupState === 'ungrouped';
        const generatedMemberSelectionVisible = ungroupedMemberFrames.length === generatedMembers.length
          || generatedUngroupOutlinedMembers === generatedMembers.length;
        const generatedUngroupPreservesMulti = generatedMembers.length > 1
          && root.dataset.editGroupState === 'ungrouped'
          && ungroupedFrame?.dataset.selectionMode === 'multi'
          && generatedUngroupDeclaredMemberFrames === generatedMembers.length
          && generatedMemberSelectionVisible;
        window.EditMode.undo();
        await nextFrame();
        const generatedUndoFrame = document.getElementById('edit-selection-frame');
        const generatedUngroupUndoSelectionMode = generatedUndoFrame?.dataset.selectionMode || '';
        const generatedUngroupUndoPass = root.dataset.editGroupState !== 'ungrouped'
          && generatedUngroupUndoSelectionMode === 'group'
          && Number(generatedUndoFrame?.dataset.memberFrameCount || 0) === 0;
        window.EditMode.redo();
        await nextFrame();
        const generatedRedoFrame = document.getElementById('edit-selection-frame');
        const generatedUngroupRedoSelectionMode = generatedRedoFrame?.dataset.selectionMode || '';
        const generatedUngroupRedoPass = root.dataset.editGroupState === 'ungrouped'
          && generatedUngroupRedoSelectionMode === 'multi'
          && Number(generatedRedoFrame?.dataset.memberFrameCount || 0) === generatedMembers.length;
        window.EditMode.undo();
        await nextFrame();
        fireClick(root.querySelector(".card-bg"));
        fireClick(layerTarget);
        fireClick(layerTarget);
        const editable = layerTarget.getAttribute("contenteditable") === "true";
        layerTarget.innerHTML = original + " UPDATED";
        layerTarget.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: "UPDATED" }));
        fireClick(slide.querySelector(".meta"));
        window.EditMode.undo();
        await nextFrame();
        const undoPass = layerTarget.innerHTML === original;
        window.EditMode.redo();
        await nextFrame();
        const redoPass = layerTarget.innerHTML !== original;
        window.EditMode.undo();
        compositeLayer = {
          targetFound: true,
          generatedMemberCount: generatedMembers.length,
          generatedUngroupSelectionMode,
          generatedUngroupMemberFrameCount,
          generatedRootStateUngrouped,
          generatedUngroupTotalMemberFrames,
          generatedUngroupDeclaredMemberFrames,
          generatedUngroupOutlinedMembers,
          generatedMemberSelectionVisible,
          generatedUngroupPreservesMulti,
          generatedUngroupUndoPass,
          generatedUngroupUndoSelectionMode,
          generatedUngroupRedoSelectionMode,
          generatedUngroupRedoPass,
          editable,
          undoPass,
          redoPass,
          pass: generatedUngroupPreservesMulti && generatedUngroupUndoPass && generatedUngroupRedoPass
            && editable && undoPass && redoPass,
        };
      }

      const expectedTextSelectors = [
        '.cover-title', '.cover-subtitle', '.cover-speaker', '.cover-org',
        '.toc-kicker', '.toc-title', '.toc-body', '.toc-stat',
        '.card-no', '.card-metric', '.card-title', '.card-body', '.card-tags',
        '.cycle-kicker', '.cycle-hub-title', '.cycle-hub-body', '.cycle-no', '.cycle-title', '.cycle-body',
        '.ba-header span', '.ba-header b', '.ba-subtitle', '.ba-item-no', '.ba-item-text', '.ba-rail span', '.ba-rail em',
        '.page-title', '.page-subtitle', '.process-node span', '.process-node b', '.process-node p', '.process-note-text',
        '.metric span', '.metric b', '.metric em', '.takeaway-text',
        '.chart-title', '.chart-y-axis span', '.chart-labels span', '.chart-legend span', '.chart-legend small',
        '.quote', '.quote-by', '.closing-title', '.closing-body', '.closing-contact-text',
      ].join(',');
      const stageRoot = document.getElementById('stage');
      const expectedText = [...stageRoot.querySelectorAll(expectedTextSelectors)];
      const uncovered = expectedText.filter((el) => !(
        el.matches('.el[data-edit-kind="text"]')
        || el.closest('[data-edit-layer="text"],[data-edit-layer="metric"]')
      )).map((el) => el.className || el.tagName.toLowerCase());
      const layerTargets = [...stageRoot.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')];
      const directTargets = [...stageRoot.querySelectorAll('.el[data-edit-kind="text"]')];
      const activationFailures = [];
      for (const target of layerTargets.concat(directTargets)) {
        const slide = activate(target);
        const root = target.closest('.el');
        if (!root) {
          activationFailures.push({ element: target.className || target.tagName.toLowerCase(), reason: 'missing-root' });
          continue;
        }
        if (target === root) {
          fireClick(target);
          fireClick(target);
        } else {
          fireClick(root);
          fireClick(target);
          fireClick(target);
        }
        if (target.getAttribute('contenteditable') !== 'true') {
          activationFailures.push({ element: target.className || target.tagName.toLowerCase(), reason: 'not-editable' });
        }
        fireClick(slide.querySelector('.meta'));
      }
      const editabilityCoverage = {
        expectedText: expectedText.length,
        layerTargets: layerTargets.length,
        directTargets: directTargets.length,
        uncovered,
        activationFailures,
        pass: expectedText.length > 0 && uncovered.length === 0 && activationFailures.length === 0,
      };

      const representativeSelectors = [
        '.toc-intro .toc-title',
        '.cycle-node .cycle-title',
        '.ba-header b',
        '.ba-item-text',
        '.ba-rail em',
        '.process-node b',
        '.process-note-text',
        '.metric b',
        '.takeaway-text',
        '.chart-labels [data-edit-layer="text"]',
        '.chart-legend small',
        '.closing-contact-text',
      ];
      const representativeResults = [];
      for (const selector of representativeSelectors) {
        const target = stageRoot.querySelector(selector);
        if (!target) {
          representativeResults.push({ selector, targetFound: false, skipped: true, pass: true });
          continue;
        }
        const slide = activate(target);
        const root = target.closest('.el');
        const original = target.innerHTML;
        const rootChildCount = root ? root.querySelectorAll('*').length : -1;
        fireClick(root);
        fireClick(target);
        fireClick(target);
        const editable = target.getAttribute('contenteditable') === 'true';
        target.innerHTML = original + '<span data-qa-marker="representative">QA</span>';
        target.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: 'QA' }));
        fireClick(slide.querySelector('.meta'));
        window.EditMode.undo();
        await nextFrame();
        const undoPass = target.innerHTML === original;
        window.EditMode.redo();
        await nextFrame();
        const redoPass = Boolean(target.querySelector('[data-qa-marker="representative"]'));
        window.EditMode.undo();
        await nextFrame();
        const structurePreserved = Boolean(root) && root.querySelectorAll('*').length === rootChildCount;
        representativeResults.push({ selector, targetFound: true, editable, undoPass, redoPass, structurePreserved, pass: editable && undoPass && redoPass && structurePreserved });
      }
      const representativeEdits = {
        tested: representativeResults.filter((row) => !row.skipped).length,
        skipped: representativeResults.filter((row) => row.skipped).length,
        passed: representativeResults.filter((row) => !row.skipped && row.pass).length,
        failures: representativeResults.filter((row) => !row.pass),
        pass: representativeResults.filter((row) => !row.skipped).length >= 8
          && representativeResults.every((row) => row.pass),
      };

      const compositeTarget = document.querySelector('#stage > .slide .ba-panel.active[data-edit-composite]');
      let compositeScale = { targetFound: Boolean(compositeTarget), pass: false };
      if (compositeTarget) {
        activate(compositeTarget);
        await nextFrame();
        fireClick(compositeTarget);
        const handle = document.querySelector('.edit-resize-handle[data-handle="se"]');
        const lineRuns = () => [...compositeTarget.querySelectorAll('.ba-item-text')].map((el) => {
          const range = document.createRange();
          range.selectNodeContents(el);
          return range.getClientRects().length;
        });
        const beforeRect = compositeTarget.getBoundingClientRect();
        const sampleText = compositeTarget.querySelector('.ba-header b');
        const beforeTextRect = sampleText?.getBoundingClientRect();
        const beforeStyle = {
          width: compositeTarget.style.width,
          height: compositeTarget.style.height,
          transform: compositeTarget.style.transform,
        };
        const beforeLines = lineRuns();
        const handleRect = handle?.getBoundingClientRect();
        if (handle && handleRect) {
          const startX = handleRect.left + handleRect.width / 2;
          const startY = handleRect.top + handleRect.height / 2;
          const endX = startX - beforeRect.width * 0.25;
          const endY = startY - beforeRect.height * 0.25;
          handle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: startX, clientY: startY, button: 0 }));
          window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: endX, clientY: endY, button: 0 }));
          window.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: endX, clientY: endY, button: 0 }));
          await nextFrame();
          const afterRect = compositeTarget.getBoundingClientRect();
          const afterTextRect = sampleText?.getBoundingClientRect();
          const afterLines = lineRuns();
          const layoutSizeStable = compositeTarget.style.width === beforeStyle.width
            && compositeTarget.style.height === beforeStyle.height;
          const aspectRatioStable = Math.abs(
            afterRect.width / afterRect.height - beforeRect.width / beforeRect.height
          ) <= 0.01;
          const visualScaleApplied = compositeTarget.style.transform !== beforeStyle.transform
            && afterRect.width < beforeRect.width * 0.8
            && afterRect.height < beforeRect.height * 0.8;
          const lineBreaksStable = JSON.stringify(afterLines) === JSON.stringify(beforeLines);
          const groupScaleRatio = afterRect.width / beforeRect.width;
          const textScaleRatio = beforeTextRect && afterTextRect ? afterTextRect.height / beforeTextRect.height : 0;
          const textScaleSynchronized = Math.abs(textScaleRatio - groupScaleRatio) <= 0.03;
          window.EditMode.undo();
          await nextFrame();
          const undoPass = compositeTarget.style.transform === beforeStyle.transform
            && JSON.stringify(lineRuns()) === JSON.stringify(beforeLines);
          window.EditMode.redo();
          await nextFrame();
          const firstTransform = compositeTarget.style.transform;
          const redoPass = firstTransform !== beforeStyle.transform
            && JSON.stringify(lineRuns()) === JSON.stringify(beforeLines);
          const secondHandle = document.querySelector('.edit-resize-handle[data-handle="se"]');
          const secondHandleRect = secondHandle?.getBoundingClientRect();
          let repeatedScaleNormalized = false;
          let repeatedScaleUndoPass = false;
          let repeatedScaleDebug = { handleFound: Boolean(secondHandle) };
          if (secondHandle && secondHandleRect) {
            const secondBeforeRect = compositeTarget.getBoundingClientRect();
            const secondStartX = secondHandleRect.left + secondHandleRect.width / 2;
            const secondStartY = secondHandleRect.top + secondHandleRect.height / 2;
            const secondEndX = secondStartX - secondBeforeRect.width * 0.12;
            const secondEndY = secondStartY - secondBeforeRect.height * 0.12;
            secondHandle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: secondStartX, clientY: secondStartY, button: 0 }));
            window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: secondEndX, clientY: secondEndY, button: 0 }));
            window.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: secondEndX, clientY: secondEndY, button: 0 }));
            await nextFrame();
            const functionCount = (compositeTarget.style.transform.match(/[a-zA-Z0-9]+\(/g) || []).length;
            const secondAfterRect = compositeTarget.getBoundingClientRect();
            repeatedScaleDebug = {
              handleFound: true,
              handleDisplay: getComputedStyle(secondHandle).display,
              activeEditable: document.querySelector('[contenteditable="true"]')?.className || '',
              selectionFrameDisplay: getComputedStyle(document.getElementById('edit-selection-frame')).display,
              selectionMode: document.getElementById('edit-selection-frame')?.dataset.selectionMode || '',
              selectionLabel: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent || '',
              handleRect: { left: secondHandleRect.left, top: secondHandleRect.top, width: secondHandleRect.width, height: secondHandleRect.height },
              start: { x: secondStartX, y: secondStartY },
              end: { x: secondEndX, y: secondEndY },
              functionCount,
              transform: compositeTarget.style.transform,
              beforeWidth: secondBeforeRect.width,
              afterWidth: secondAfterRect.width,
              lineBreaksStable: JSON.stringify(lineRuns()) === JSON.stringify(beforeLines),
            };
            repeatedScaleNormalized = functionCount === 1
              && secondAfterRect.width < secondBeforeRect.width * 0.94
              && JSON.stringify(lineRuns()) === JSON.stringify(beforeLines);
            window.EditMode.undo();
            await nextFrame();
            repeatedScaleUndoPass = compositeTarget.style.transform === firstTransform;
          }
          window.EditMode.undo();
          await nextFrame();
          compositeScale = {
            targetFound: true,
            layoutSizeStable,
            aspectRatioStable,
            visualScaleApplied,
            textScaleSynchronized,
            lineBreaksStable,
            undoPass,
            redoPass,
            repeatedScaleNormalized,
            repeatedScaleUndoPass,
            repeatedScaleDebug,
            pass: layoutSizeStable && aspectRatioStable && visualScaleApplied && textScaleSynchronized && lineBreaksStable && undoPass && redoPass && repeatedScaleNormalized && repeatedScaleUndoPass,
          };
        }
      }

      const sideScaleTarget = document.querySelector('#stage > .slide .ba-panel.active .ba-item-text');
      let textFrameWidth = { targetFound: Boolean(sideScaleTarget), pass: false };
      if (sideScaleTarget) {
        const slide = activate(sideScaleTarget);
        const root = sideScaleTarget.closest('.el');
        fireClick(root);
        fireClick(sideScaleTarget);
        const handle = document.querySelector('.edit-resize-handle[data-handle="e"]');
        const beforeRect = sideScaleTarget.getBoundingClientRect();
        const beforeLines = (() => {
          const range = document.createRange();
          range.selectNodeContents(sideScaleTarget);
          return range.getClientRects().length;
        })();
        const beforeFontSize = parseFloat(getComputedStyle(sideScaleTarget).fontSize);
        const textRange = () => {
          const range = document.createRange();
          range.selectNodeContents(sideScaleTarget);
          return range.getBoundingClientRect();
        };
        const beforeTextRange = textRange();
        const beforeStyle = {
          left: sideScaleTarget.style.left,
          top: sideScaleTarget.style.top,
          width: sideScaleTarget.style.width,
          height: sideScaleTarget.style.height,
          fontSize: sideScaleTarget.style.fontSize,
          lineHeight: sideScaleTarget.style.lineHeight,
          transform: sideScaleTarget.style.transform,
          transformOrigin: sideScaleTarget.style.transformOrigin,
        };
        const handleRect = handle?.getBoundingClientRect();
        if (handle && handleRect) {
          const startX = handleRect.left + handleRect.width / 2;
          const startY = handleRect.top + handleRect.height / 2;
          const endX = startX + beforeRect.width * 0.35;
          handle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: startX, clientY: startY, button: 0 }));
          window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: endX, clientY: startY, button: 0 }));
          window.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: endX, clientY: startY, button: 0 }));
          await nextFrame();
          const afterRect = sideScaleTarget.getBoundingClientRect();
          const afterTextRange = textRange();
          const afterFontSize = parseFloat(getComputedStyle(sideScaleTarget).fontSize);
          const afterLines = (() => {
            const range = document.createRange();
            range.selectNodeContents(sideScaleTarget);
            return range.getClientRects().length;
          })();
          const widthChanged = afterRect.width > beforeRect.width * 1.2;
          const fontSizeStable = Math.abs(afterFontSize - beforeFontSize) <= 0.1;
          const manualFrameMode = sideScaleTarget.dataset.editFrameWidth === 'manual';
          const textFitsFrame = afterTextRange.width <= afterRect.width + 3
            && afterTextRange.height <= afterRect.height + 3;
          window.EditMode.undo();
          await nextFrame();
          const undoRect = sideScaleTarget.getBoundingClientRect();
          const undoPass = Math.abs(undoRect.left - beforeRect.left) <= 1
            && Math.abs(undoRect.top - beforeRect.top) <= 1
            && Math.abs(undoRect.width - beforeRect.width) <= 1
            && Math.abs(undoRect.height - beforeRect.height) <= 1
            && sideScaleTarget.style.transform === beforeStyle.transform
            && sideScaleTarget.style.transformOrigin === beforeStyle.transformOrigin
            && sideScaleTarget.dataset.editFrameWidth !== 'manual';
          window.EditMode.redo();
          await nextFrame();
          const redoRect = sideScaleTarget.getBoundingClientRect();
          const redoPass = sideScaleTarget.dataset.editFrameWidth === 'manual'
            && Math.abs(redoRect.width - afterRect.width) <= 1
            && Math.abs(redoRect.height - afterRect.height) <= 1;
          window.EditMode.undo();
          await nextFrame();
          fireClick(slide.querySelector('.meta'));
          textFrameWidth = {
            targetFound: true,
            widthChanged,
            fontSizeStable,
            manualFrameMode,
            textFitsFrame,
            beforeLines,
            afterLines,
            undoPass,
            redoPass,
            pass: widthChanged && fontSizeStable && manualFrameMode && textFitsFrame && undoPass && redoPass,
          };
        }
      }

      let textFrameHeight = { targetFound: Boolean(sideScaleTarget), pass: false };
      if (sideScaleTarget) {
        const slide = activate(sideScaleTarget);
        const root = sideScaleTarget.closest('.el');
        fireClick(root);
        fireClick(sideScaleTarget);
        await nextFrame();
        const handle = document.querySelector('.edit-resize-handle[data-handle="s"]');
        const beforeRect = sideScaleTarget.getBoundingClientRect();
        const beforeFontSize = parseFloat(getComputedStyle(sideScaleTarget).fontSize);
        const handleRect = handle?.getBoundingClientRect();
        if (handle && handleRect) {
          const startX = handleRect.left + handleRect.width / 2;
          const startY = handleRect.top + handleRect.height / 2;
          const endY = startY + Math.max(48, beforeRect.height * 0.8);
          handle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: startX, clientY: startY, button: 0 }));
          window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: startX, clientY: endY, button: 0 }));
          window.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: startX, clientY: endY, button: 0 }));
          await nextFrame();
          const afterRect = sideScaleTarget.getBoundingClientRect();
          const afterFontSize = parseFloat(getComputedStyle(sideScaleTarget).fontSize);
          const heightChanged = afterRect.height > beforeRect.height + 20;
          const widthStable = Math.abs(afterRect.width - beforeRect.width) <= 1;
          const fontSizeStable = Math.abs(afterFontSize - beforeFontSize) <= 0.1;
          const manualFrameMode = sideScaleTarget.dataset.editFrameHeight === 'manual';
          window.EditMode.undo();
          await nextFrame();
          const undoRect = sideScaleTarget.getBoundingClientRect();
          const undoPass = Math.abs(undoRect.width - beforeRect.width) <= 1
            && Math.abs(undoRect.height - beforeRect.height) <= 1
            && sideScaleTarget.dataset.editFrameHeight !== 'manual';
          window.EditMode.redo();
          await nextFrame();
          const redoRect = sideScaleTarget.getBoundingClientRect();
          const redoPass = sideScaleTarget.dataset.editFrameHeight === 'manual'
            && Math.abs(redoRect.width - afterRect.width) <= 1
            && Math.abs(redoRect.height - afterRect.height) <= 1;
          window.EditMode.undo();
          await nextFrame();
          fireClick(slide.querySelector('.meta'));
          textFrameHeight = {
            targetFound: true,
            heightChanged,
            widthStable,
            fontSizeStable,
            manualFrameMode,
            undoPass,
            redoPass,
            pass: heightChanged && widthStable && fontSizeStable && manualFrameMode && undoPass && redoPass,
          };
        }
      }

      const anchorTarget = document.querySelector('#stage > .slide [data-edit-fit="text"]');
      let textEditAnchor = { targetFound: Boolean(anchorTarget), pass: false };
      if (anchorTarget) {
        const slide = activate(anchorTarget);
        await nextFrame();
        const originalStyle = anchorTarget.getAttribute('style');
        const originalHtml = anchorTarget.innerHTML;
        const originalFrameWidth = anchorTarget.dataset.editFrameWidth || '';
        const originalFrameHeight = anchorTarget.dataset.editFrameHeight || '';
        const cases = [];
        const anchorX = (rect, align) => align === 'center' ? rect.left + rect.width / 2 : (align === 'right' ? rect.right : rect.left);
        for (const align of ['left', 'center', 'right']) {
          if (originalStyle === null) anchorTarget.removeAttribute('style');
          else anchorTarget.setAttribute('style', originalStyle);
          anchorTarget.innerHTML = originalHtml;
          if (originalFrameWidth) anchorTarget.dataset.editFrameWidth = originalFrameWidth;
          else delete anchorTarget.dataset.editFrameWidth;
          if (originalFrameHeight) anchorTarget.dataset.editFrameHeight = originalFrameHeight;
          else delete anchorTarget.dataset.editFrameHeight;
          anchorTarget.style.setProperty('text-align', align, 'important');
          fireClick(anchorTarget);
          fireClick(anchorTarget);
          await nextFrame();
          const beforeRect = anchorTarget.getBoundingClientRect();
          const beforeAnchor = anchorX(beforeRect, align);
          anchorTarget.dispatchEvent(new InputEvent('beforeinput', { bubbles: true, inputType: 'insertParagraph', data: null }));
          anchorTarget.innerHTML = '水平錨點測試<br>換行後仍維持定位';
          anchorTarget.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertParagraph', data: null }));
          await nextFrame();
          const afterRect = anchorTarget.getBoundingClientRect();
          const afterAnchor = anchorX(afterRect, align);
          fireClick(slide.querySelector('.meta'));
          await nextFrame();
          window.EditMode.undo();
          await nextFrame();
          const undoRect = anchorTarget.getBoundingClientRect();
          cases.push({
            align,
            drift: Math.round(Math.abs(afterAnchor - beforeAnchor) * 10) / 10,
            anchorStable: Math.abs(afterAnchor - beforeAnchor) <= 1.5,
            undoPass: anchorTarget.innerHTML === originalHtml
              && Math.abs(undoRect.left - beforeRect.left) <= 1.5
              && Math.abs(undoRect.width - beforeRect.width) <= 1.5,
          });
        }
        if (originalStyle === null) anchorTarget.removeAttribute('style');
        else anchorTarget.setAttribute('style', originalStyle);
        anchorTarget.innerHTML = originalHtml;
        if (originalFrameWidth) anchorTarget.dataset.editFrameWidth = originalFrameWidth;
        else delete anchorTarget.dataset.editFrameWidth;
        if (originalFrameHeight) anchorTarget.dataset.editFrameHeight = originalFrameHeight;
        else delete anchorTarget.dataset.editFrameHeight;
        textEditAnchor = {
          targetFound: true,
          cases,
          pass: cases.length === 3 && cases.every((item) => item.anchorStable && item.undoPass),
        };
      }

      const fontSlides = [...document.querySelectorAll('#stage > .slide')];
      let mixedFontSelection = { targetsFound: false, pass: false };
      for (const slide of fontSlides) {
        const candidates = [...slide.querySelectorAll('.el[data-edit-kind="text"]')]
          .filter((el) => !(el.dataset.editGroup || '') && el.textContent.trim());
        let pair = null;
        for (let i = 0; i < candidates.length && !pair; i += 1) {
          for (let j = i + 1; j < candidates.length; j += 1) {
            const a = Math.round(parseFloat(getComputedStyle(candidates[i]).fontSize));
            const b = Math.round(parseFloat(getComputedStyle(candidates[j]).fontSize));
            if (a !== b) {
              pair = [candidates[i], candidates[j]];
              break;
            }
          }
        }
        if (!pair) continue;
        activate(pair[0]);
        await nextFrame();
        fireClick(pair[0]);
        ['mousedown', 'mouseup', 'click'].forEach((type) => pair[1].dispatchEvent(new MouseEvent(type, {
          bubbles: true, clientX: 360, clientY: 240, button: 0, shiftKey: true,
        })));
        await nextFrame();
        const input = document.getElementById('edit-font-size-input');
        const before = pair.map((el) => Math.round(parseFloat(getComputedStyle(el).fontSize)));
        const mixedShown = Boolean(input && getComputedStyle(input).display !== 'none' && /\+$/.test(input.value));
        if (input) {
          input.focus();
          input.value = '31';
          input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: '31' }));
          input.blur();
          await nextFrame();
        }
        const appliedToAll = pair.every((el) => Math.abs(parseFloat(getComputedStyle(el).fontSize) - 31) <= 0.1);
        window.EditMode.undo();
        await nextFrame();
        const undoPass = pair.every((el, index) => Math.abs(parseFloat(getComputedStyle(el).fontSize) - before[index]) <= 0.1);
        mixedFontSelection = {
          targetsFound: true,
          before,
          displayedValue: input?.value || '',
          mixedShown,
          appliedToAll,
          undoPass,
          pass: mixedShown && appliedToAll && undoPass,
        };
        break;
      }

      const groupCards = [...document.querySelectorAll('#stage > .slide .toc-card')];
      const clickWithShift = (el) => {
        ['mousedown', 'mouseup', 'click'].forEach((type) => el.dispatchEvent(new MouseEvent(type, {
          bubbles: true, clientX: 360, clientY: 240, button: 0, shiftKey: true,
        })));
      };
      const pathOf = (el) => (el.dataset.editGroup || '').split('>').filter(Boolean);

      let contextMenuGrouping = { targetsFound: groupCards.length >= 2, pass: false };
      if (groupCards.length >= 2) {
        const cards = groupCards.slice(0, 2);
        activate(cards[0]);
        await nextFrame();
        fireClick(cards[0]);
        clickWithShift(cards[1]);
        await nextFrame();
        const memberFramesBefore = [...document.querySelectorAll('.edit-selection-member-frame')]
          .filter((frame) => getComputedStyle(frame).display !== 'none').length;
        cards[0].dispatchEvent(new MouseEvent('contextmenu', {
          bubbles: true, cancelable: true, clientX: 420, clientY: 280, button: 2,
        }));
        await nextFrame();
        const menu = document.getElementById('edit-object-context-menu');
        const groupMenuButton = menu?.querySelector('[data-action="context-group"]');
        const menuVisible = Boolean(menu && getComputedStyle(menu).display !== 'none');
        const groupActionVisible = Boolean(
          groupMenuButton
          && getComputedStyle(groupMenuButton).display !== 'none'
          && !groupMenuButton.disabled
        );
        groupMenuButton?.click();
        await nextFrame();
        const groupedPaths = cards.map(pathOf);
        const groupId = groupedPaths[0][groupedPaths[0].length - 1];
        const contextGroupCreated = Boolean(groupId)
          && groupedPaths.every((path) => path.length === 1 && path[0] === groupId);
        const groupedMemberFrames = [...document.querySelectorAll('.edit-selection-member-frame')]
          .filter((frame) => getComputedStyle(frame).display !== 'none').length;
        window.EditMode.ungroup();
        await nextFrame();
        const cleanupPass = cards.every((card) => pathOf(card).length === 0);
        contextMenuGrouping = {
          targetsFound: true,
          memberFramesBefore,
          multiSelectionPreserved: memberFramesBefore === cards.length,
          menuVisible,
          groupActionVisible,
          contextGroupCreated,
          groupedMemberFramesCollapsed: groupedMemberFrames === 0,
          cleanupPass,
          pass: memberFramesBefore === cards.length
            && menuVisible
            && groupActionVisible
            && contextGroupCreated
            && groupedMemberFrames === 0
            && cleanupPass,
        };
      }

      let nestedGrouping = { targetsFound: groupCards.length >= 4, pass: false };
      if (groupCards.length >= 4) {
        const cards = groupCards.slice(0, 4);
        activate(cards[0]);
        await nextFrame();
        fireClick(cards[0]);
        clickWithShift(cards[1]);
        window.EditMode.group();
        const firstInner = pathOf(cards[0])[0];
        fireClick(cards[2]);
        clickWithShift(cards[3]);
        window.EditMode.group();
        const secondInner = pathOf(cards[2])[0];
        fireClick(cards[0]);
        clickWithShift(cards[2]);
        window.EditMode.group();
        const nestedPaths = cards.map(pathOf);
        const outer = nestedPaths[0][nestedPaths[0].length - 1];
        await nextFrame();
        const groupedMemberFrames = [...document.querySelectorAll('.edit-selection-member-frame')]
          .filter((frame) => getComputedStyle(frame).display !== 'none');
        const groupedMemberFramesCollapsed = groupedMemberFrames.length === 0;
        const groupedMemberOutlinesCollapsed = cards.every((card) => {
          const style = getComputedStyle(card);
          return style.outlineStyle === 'none' || parseFloat(style.outlineWidth) < 1;
        });
        const outerFrame = document.getElementById('edit-selection-frame');
        const outerFrameVisible = Boolean(outerFrame
          && getComputedStyle(outerFrame).display !== 'none'
          && outerFrame.dataset.selectionMode === 'group'
          && getComputedStyle(outerFrame).borderTopStyle === 'solid');
        const groupTools = document.getElementById('edit-group-tools');
        const groupToolsVisible = Boolean(groupTools && getComputedStyle(groupTools).display !== 'none');
        cards[0].dispatchEvent(new MouseEvent('contextmenu', {
          bubbles: true, cancelable: true, clientX: 420, clientY: 280, button: 2,
        }));
        await nextFrame();
        const contextMenu = document.getElementById('edit-object-context-menu');
        const directGroupActionsVisible = ['context-group', 'context-ungroup'].every((action) => {
          const btn = contextMenu?.querySelector(`[data-action="${action}"]`);
          return Boolean(btn && getComputedStyle(btn).display !== 'none');
        });
        const nestedCreated = Boolean(firstInner && secondInner && outer)
          && firstInner !== secondInner
          && nestedPaths.every((path) => path.length === 2 && path[path.length - 1] === outer)
          && nestedPaths[0][0] === firstInner && nestedPaths[1][0] === firstInner
          && nestedPaths[2][0] === secondInner && nestedPaths[3][0] === secondInner;
        window.EditMode.ungroup();
        await nextFrame();
        const ungroupedPaths = cards.map(pathOf);
        const outerRemoved = ungroupedPaths.every((path) => path.indexOf(outer) < 0);
        const innerGroupsPreserved = ungroupedPaths[0][0] === firstInner && ungroupedPaths[1][0] === firstInner
          && ungroupedPaths[2][0] === secondInner && ungroupedPaths[3][0] === secondInner;
        const ungroupedMemberFrames = [...document.querySelectorAll('.edit-selection-member-frame')]
          .filter((frame) => getComputedStyle(frame).display !== 'none');
        const ungroupedMemberFramesVisible = ungroupedMemberFrames.length === cards.length;
        const ungroupedMemberFramesStyled = ungroupedMemberFramesVisible && ungroupedMemberFrames.every((frame) => {
          const style = getComputedStyle(frame);
          return parseFloat(style.borderTopWidth) >= 1
            && style.borderTopStyle === 'dashed'
            && style.pointerEvents === 'none'
            && style.boxShadow !== 'none'
            && parseFloat(style.opacity) >= 0.9;
        });
        const ungroupedMemberOutlinesVisible = cards.every((card) => {
          const style = getComputedStyle(card);
          return parseFloat(style.outlineWidth) >= 2
            && style.outlineStyle === 'solid'
            && style.outlineColor !== 'rgba(0, 0, 0, 0)';
        });
        const ungroupedMemberFramesMatch = ungroupedMemberFramesVisible && cards.every((card) => {
          const cardRect = card.getBoundingClientRect();
          return ungroupedMemberFrames.some((frame) => {
            const frameRect = frame.getBoundingClientRect();
            return Math.abs(frameRect.left - cardRect.left) <= 2
              && Math.abs(frameRect.top - cardRect.top) <= 2
              && Math.abs(frameRect.width - cardRect.width) <= 2
              && Math.abs(frameRect.height - cardRect.height) <= 2;
          });
        });
        const ungroupedFrame = document.getElementById('edit-selection-frame');
        const ungroupedSelectionMode = ungroupedFrame?.dataset.selectionMode === 'multi'
          && getComputedStyle(ungroupedFrame).borderTopStyle === 'dashed';
        window.EditMode.undo();
        await nextFrame();
        const undoFrame = document.getElementById('edit-selection-frame');
        const undoSelectionRestoredToGroup = undoFrame?.dataset.selectionMode === 'group'
          && Number(undoFrame?.dataset.memberFrameCount || 0) === 0;
        const undoPass = cards.every((card) => pathOf(card).indexOf(outer) >= 0)
          && undoSelectionRestoredToGroup;
        window.EditMode.redo();
        await nextFrame();
        const redoFrame = document.getElementById('edit-selection-frame');
        const redoSelectionRestoredToMulti = redoFrame?.dataset.selectionMode === 'multi'
          && Number(redoFrame?.dataset.memberFrameCount || 0) === cards.length;
        const redoPass = cards.every((card) => pathOf(card).indexOf(outer) < 0)
          && redoSelectionRestoredToMulti;
        window.EditMode.undo();
        window.EditMode.undo();
        window.EditMode.undo();
        window.EditMode.undo();
        await nextFrame();
        const cleanupPass = cards.every((card) => pathOf(card).length === 0);
        nestedGrouping = {
          targetsFound: true,
          nestedCreated,
          nestedPaths,
          outerRemoved,
          ungroupedPaths,
          innerGroupsPreserved,
          groupedMemberFrameCount: groupedMemberFrames.length,
          groupedMemberFramesCollapsed,
          groupedMemberOutlinesCollapsed,
          ungroupedMemberFrameCount: ungroupedMemberFrames.length,
          ungroupedMemberFramesVisible,
          ungroupedMemberFramesStyled,
          ungroupedMemberOutlinesVisible,
          ungroupedMemberFramesMatch,
          ungroupedSelectionMode,
          undoSelectionRestoredToGroup,
          redoSelectionRestoredToMulti,
          outerFrameVisible,
          groupToolsVisible,
          directGroupActionsVisible,
          undoPass,
          redoPass,
          cleanupPass,
          pass: nestedCreated && outerRemoved && innerGroupsPreserved
            && groupedMemberFramesCollapsed && groupedMemberOutlinesCollapsed
            && ungroupedMemberFramesVisible && ungroupedMemberFramesStyled
            && ungroupedMemberOutlinesVisible && ungroupedMemberFramesMatch && ungroupedSelectionMode
            && outerFrameVisible && groupToolsVisible && directGroupActionsVisible
            && undoPass && redoPass && cleanupPass,
        };
      }

      const pass = framework.slides > 0
        && framework.slides === framework.uniqueSlideIds
        && framework.editMode
        && framework.historyLimit === 100
        && framework.toolbar
        && framework.autoLayoutsMaterialized
        && modeScaleStable
        && selectionControls.pass
        && textFit.pass
        && compositeLayer.pass
        && compositeScale.pass
        && textFrameWidth.pass
        && textFrameHeight.pass
        && textEditAnchor.pass
        && mixedFontSelection.pass
        && contextMenuGrouping.pass
        && nestedGrouping.pass
        && editabilityCoverage.pass
        && representativeEdits.pass;
      localStorage.clear();
      return { framework, modeScaleStable, selectionControls, textFit, compositeLayer, compositeScale, textFrameWidth, textFrameHeight, textEditAnchor, mixedFontSelection, contextMenuGrouping, nestedGrouping, editabilityCoverage, representativeEdits, pass };
    });
    const prioritySetup = await page.evaluate(async () => {
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const cards = [...document.querySelectorAll('#stage > .slide .toc-card')].slice(0, 2);
      if (cards.length < 2) return null;
      const slide = cards[0].closest('.slide');
      window.setSlide(Number(slide.dataset.index));
      await nextFrame();
      const groupId = 'qa-group-priority';
      cards.forEach((card) => { card.dataset.editGroup = groupId; });
      const stage = document.getElementById('stage');
      const stageRect = stage.getBoundingClientRect();
      const scale = stage.offsetWidth ? stageRect.width / stage.offsetWidth : 1;
      const rect = cards[0].getBoundingClientRect();
      const overlay = document.createElement('div');
      overlay.id = 'qa-overlap-background';
      overlay.className = 'el';
      overlay.dataset.editKind = 'shape';
      overlay.style.cssText = [
        'left:' + ((rect.left - stageRect.left) / scale) + 'px',
        'top:' + ((rect.top - stageRect.top) / scale) + 'px',
        'width:' + (rect.width / scale) + 'px',
        'height:' + (rect.height / scale) + 'px',
        'z-index:9999',
        'background:rgba(255,0,0,.01)',
      ].join(';');
      slide.appendChild(overlay);
      await nextFrame();
      const overlayRect = overlay.getBoundingClientRect();
      return { x: overlayRect.left + overlayRect.width / 2, y: overlayRect.top + overlayRect.height / 2, groupId };
    });
    if (prioritySetup) {
      await page.mouse.click(prioritySetup.x, prioritySetup.y);
      await page.waitForTimeout(80);
      result.groupHitPriority = await page.evaluate((groupId) => {
        const visibleMembers = [...document.querySelectorAll('.edit-selection-member-frame')]
          .filter((frame) => getComputedStyle(frame).display !== 'none').length;
        const outerFrame = document.getElementById('edit-selection-frame');
        const groupSelected = Boolean(outerFrame
          && outerFrame.dataset.selectionMode === 'group'
          && getComputedStyle(outerFrame).display !== 'none'
          && getComputedStyle(outerFrame).borderTopStyle === 'solid'
          && visibleMembers === 0);
        document.querySelectorAll(`#stage > .slide .el[data-edit-group="${groupId}"]`).forEach((el) => delete el.dataset.editGroup);
        document.getElementById('qa-overlap-background')?.remove();
        document.querySelector('#stage > .slide.active .meta')?.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        return { visibleMembers, groupSelected, pass: groupSelected };
      }, prioritySetup.groupId);
    } else {
      result.groupHitPriority = { targetFound: false, pass: false };
    }
    result.pass = result.pass && result.groupHitPriority.pass;

    const exportMarker = "EXPORT-QA-MARKER";
    await page.evaluate((marker) => {
      const fireClick = (el) => {
        if (!el) el = document.querySelector("#stage > .slide.active");
        if (!el) throw new Error("No active slide available for export QA click");
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, {
          bubbles: true, clientX: 360, clientY: 240, button: 0,
        })));
      };
      const target = document.querySelector(
        '#stage > .slide .page-title[data-edit-fit="text"], #stage > .slide [data-edit-fit="text"], #stage > .slide [data-edit-layer="text"]'
      );
      if (!target) throw new Error('No editable text target found for export QA.');
      window.setSlide(Number(target.closest('.slide').dataset.index));
      fireClick(target);
      fireClick(target);
      target.innerHTML += " " + marker;
      target.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: marker }));
      fireClick(document.querySelector("#stage > .slide.active .meta"));
    }, exportMarker);
    const downloadPromise = page.waitForEvent("download");
    await page.evaluate(() => window.EditMode.export());
    const download = await downloadPromise;
    const stream = await download.createReadStream();
    const chunks = [];
    for await (const chunk of stream) chunks.push(chunk);
    const exportedHtml = Buffer.concat(chunks).toString("utf8");
    result.exportSanitized = await page.evaluate(({ markup, marker }) => {
      const doc = new DOMParser().parseFromString(markup, "text/html");
      const checks = {
        editedTextPreserved: doc.body.textContent.includes(marker),
        contenteditableRemoved: doc.querySelectorAll("[contenteditable]").length === 0,
        handlesRemoved: doc.querySelectorAll(".edit-resize-handle,.edit-guide-line,.edit-marquee-box").length === 0,
        transientPanelsRemoved: doc.querySelectorAll("#edit-draft-prompt,#edit-help-panel,#edit-mode-panel,#edit-selection-badge").length === 0,
        canvasScaleStyleRemoved: !doc.querySelector("#canvasBox")?.hasAttribute("style"),
        editorScriptPreserved: Boolean(doc.querySelector('script[data-edit-mode-embedded="true"],script[src="edit-mode.js"]')),
        selfContainedEditor: Boolean(doc.querySelector('script[data-edit-mode-embedded="true"]'))
          && !doc.querySelector('script[src="edit-mode.js"]'),
      };
      return { ...checks, pass: Object.values(checks).every(Boolean) };
    }, { markup: exportedHtml, marker: exportMarker });
    const exportQaDir = await fs.mkdtemp(path.join(os.tmpdir(), "html-export-reopen-"));
    const exportedPath = path.join(exportQaDir, "exported-deck.html");
    await fs.writeFile(exportedPath, exportedHtml, "utf8");
    const reopenedPage = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await reopenedPage.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await reopenedPage.route("https://fonts.gstatic.com/**", (route) => route.abort());
    try {
      await reopenedPage.goto(pathToFileURL(exportedPath).href, { waitUntil: "commit", timeout: 30000 });
      await reopenedPage.evaluate(() => Promise.race([
        document.fonts?.ready || Promise.resolve(),
        new Promise((resolve) => setTimeout(resolve, 3000)),
      ]));
      await reopenedPage.waitForFunction(() => (
        document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
      ), null, { timeout: 120000 });
      result.exportReopen = await reopenedPage.evaluate(async (marker) => {
        const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const fireClick = (el) => {
          if (!el) el = document.querySelector("#stage > .slide.active");
          if (!el) throw new Error("No active slide available for reopen QA click");
          ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, {
            bubbles: true, clientX: 360, clientY: 240, button: 0,
          })));
        };
        const snapshot = () => {
          const stageRect = document.getElementById("stage").getBoundingClientRect();
          const canvasRect = document.getElementById("canvasBox").getBoundingClientRect();
          return {
            transform: getComputedStyle(document.getElementById("stage")).transform,
            stageWidth: stageRect.width,
            stageHeight: stageRect.height,
            canvasWidth: canvasRect.width,
            canvasHeight: canvasRect.height,
          };
        };
        const slideIds = [...document.querySelectorAll('#stage > .slide')].map((slide) => slide.id);
        const target = document.querySelector('#stage > .slide .ba-item-text');
        const root = target?.closest('.el');
        if (target) window.setSlide(Number(target.closest('.slide').dataset.index));
        const original = target?.innerHTML || '';
        const rootChildCount = root ? root.querySelectorAll('*').length : -1;
        if (root && target) {
          fireClick(root);
          fireClick(target);
          fireClick(target);
        }
        const granularEditable = target?.getAttribute('contenteditable') === 'true';
        if (target) {
          target.innerHTML = original + '<span data-export-reopen-marker="true">REOPEN</span>';
          target.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: 'REOPEN' }));
          fireClick(target.closest('.slide').querySelector('.meta'));
        }
        window.EditMode.undo();
        await nextFrame();
        const undoPass = target?.innerHTML === original;
        window.EditMode.redo();
        await nextFrame();
        const redoPass = Boolean(target?.querySelector('[data-export-reopen-marker="true"]'));
        window.EditMode.undo();
        await nextFrame();
        const structurePreserved = Boolean(root) && root.querySelectorAll('*').length === rootChildCount;
        const editSnapshot = snapshot();
        window.EditMode.toggle(false);
        await nextFrame();
        const presentationSnapshot = snapshot();
        window.EditMode.toggle(true);
        await nextFrame();
        const restoredSnapshot = snapshot();
        const modeScaleStable = JSON.stringify(editSnapshot) === JSON.stringify(restoredSnapshot)
          && presentationSnapshot.stageWidth > 0
          && presentationSnapshot.stageHeight > 0
          && Math.abs(
            presentationSnapshot.stageWidth / presentationSnapshot.stageHeight
            - editSnapshot.stageWidth / editSnapshot.stageHeight
          ) < 0.001;
        const frameworkReinitialized = Boolean(
          window.EditMode
          && document.getElementById('barInner')
          && slideIds.length > 0
          && slideIds.length === new Set(slideIds).size
        );
        const exportMarkerPreserved = document.body.textContent.includes(marker);
        return {
          frameworkReinitialized,
          exportMarkerPreserved,
          granularEditable,
          undoPass,
          redoPass,
          structurePreserved,
          modeScaleStable,
          pass: frameworkReinitialized && exportMarkerPreserved && granularEditable && undoPass && redoPass && structurePreserved && modeScaleStable,
        };
      }, exportMarker);
    } finally {
      await reopenedPage.close();
      await fs.rm(exportQaDir, { recursive: true, force: true });
    }
    const granularDraftMarker = "GRANULAR-DRAFT-QA-MARKER";
    await page.evaluate((marker) => {
      const target = document.querySelector('#stage > .slide .ba-item-text');
      const root = target?.closest('.el');
      if (!target || !root) return;
      window.setSlide(Number(target.closest('.slide').dataset.index));
      const fireClick = (el) => {
        if (!el) el = document.querySelector("#stage > .slide.active");
        if (!el) throw new Error("No active slide available for draft QA click");
        ["mousedown", "mouseup", "click"].forEach((type) => el.dispatchEvent(new MouseEvent(type, {
          bubbles: true, clientX: 360, clientY: 240, button: 0,
        })));
      };
      fireClick(root);
      fireClick(target);
      fireClick(target);
      target.innerHTML += " " + marker;
      target.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: marker }));
      fireClick(target.closest('.slide').querySelector('.meta'));
    }, granularDraftMarker);
    await page.waitForTimeout(1700);
    const draftSaved = await page.evaluate(() => Object.keys(localStorage).some((key) => key.startsWith("edit-draft:")));
    await page.reload({ waitUntil: "load" });
    const draftPromptShown = await page.locator("#edit-draft-prompt").count() === 1;
    if (draftPromptShown) await page.locator("#edit-draft-prompt button").first().click({ force: true });
    await page.waitForTimeout(50);
    const draftTextRestored = await page.evaluate((marker) => document.body.textContent.includes(marker), exportMarker);
    const granularDraftRestored = await page.evaluate((marker) => document.body.textContent.includes(marker), granularDraftMarker);
    const draftUndoToBaseline = await page.evaluate(async (markers) => {
      window.EditMode.undo();
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      return markers.every((marker) => !document.body.textContent.includes(marker));
    }, [exportMarker, granularDraftMarker]);
    const draftRedoRestored = await page.evaluate(async (markers) => {
      window.EditMode.redo();
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      return markers.every((marker) => document.body.textContent.includes(marker));
    }, [exportMarker, granularDraftMarker]);
    await page.evaluate(() => localStorage.clear());
    result.draftRecovery = {
      draftSaved,
      draftPromptShown,
      draftTextRestored,
      granularDraftRestored,
      draftUndoToBaseline,
      draftRedoRestored,
      pass: draftSaved && draftPromptShown && draftTextRestored && granularDraftRestored && draftUndoToBaseline && draftRedoRestored,
    };
    await page.setViewportSize({ width: 960, height: 540 });
    await page.waitForTimeout(100);
    result.compactViewport = await page.evaluate(async () => {
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const stage = document.getElementById("stage");
      const canvas = document.getElementById("canvasBox");
      const toolbar = document.getElementById("barInner");
      const snapshot = () => {
        const stageRect = stage.getBoundingClientRect();
        const canvasRect = canvas.getBoundingClientRect();
        return {
          transform: getComputedStyle(stage).transform,
          stageWidth: stageRect.width,
          stageHeight: stageRect.height,
          canvasWidth: canvasRect.width,
          canvasHeight: canvasRect.height,
        };
      };
      const editSnapshot = snapshot();
      window.EditMode.toggle(false);
      await nextFrame();
      const presentationSnapshot = snapshot();
      window.setSlide(0);
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
      const nextSlide = document.querySelector("#stage > .slide.active")?.id;
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
      const previousSlide = document.querySelector("#stage > .slide.active")?.id;
      window.EditMode.toggle(true);
      await nextFrame();
      const restoredSnapshot = snapshot();
      // Overflow is a layout-space question. getBoundingClientRect() can be
      // visually scaled by a deck theme, while clientWidth and scrollWidth
      // remain in the toolbar's own coordinate system.
      const toolbarFits = toolbar.scrollWidth <= toolbar.clientWidth + 1;
      const modeScaleStable = JSON.stringify(editSnapshot) === JSON.stringify(restoredSnapshot)
        && presentationSnapshot.stageWidth > 0
        && presentationSnapshot.stageHeight > 0
        && Math.abs(
          presentationSnapshot.stageWidth / presentationSnapshot.stageHeight
          - editSnapshot.stageWidth / editSnapshot.stageHeight
        ) < 0.001;
      const keyboardNavigation = nextSlide === "s2" && previousSlide === "s1";
      return {
        viewport: { width: innerWidth, height: innerHeight },
        toolbarScrollWidth: toolbar.scrollWidth,
        toolbarClientWidth: toolbar.clientWidth,
        toolbarChildren: [...toolbar.children].map((child) => ({
          className: child.className,
          display: getComputedStyle(child).display,
          width: Math.round(child.getBoundingClientRect().width * 10) / 10,
        })),
        toolbarFits,
        modeScaleStable,
        keyboardNavigation,
        pass: toolbarFits && modeScaleStable && keyboardNavigation,
      };
    });
    result.pass = result.pass
      && result.exportSanitized.pass
      && result.exportReopen.pass
      && result.draftRecovery.pass
      && result.compactViewport.pass;
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), JSON.stringify(result, null, 2) + "\n", "utf8");
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
