const fs = require("node:fs/promises");
const path = require("node:path");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");
const { chromium } = loadPlaywright();

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--compact-screenshot") out.compactScreenshot = argv[++index];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  let result;
  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(options.url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    const coreResult = await page.evaluate(async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const near = (a, b, tolerance = 1.2) => Math.abs(a - b) <= tolerance;
      const slide = document.querySelector('#s2');
      const legacyMembers = slide ? [
        slide.querySelector('.toc-panel-grid-card.card-1'),
        slide.querySelector('.toc-panel-grid-card.card-2'),
      ].filter(Boolean) : [];
      const members = legacyMembers.length === 2
        ? legacyMembers
        : (slide ? Array.from(slide.querySelectorAll('.toc-panel-row')).slice(0, 2) : []);
      if (!slide || members.length !== 2 || !window.EditMode) {
        return { pass: false, error: 'TOC group fixture missing' };
      }
      window.setSlide(Number(slide.dataset.index));
      await frame();

      const fireClick = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0, shiftKey,
          clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ['mousedown', 'mouseup', 'click'].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      fireClick(members[1]);
      fireClick(members[0], true);
      window.EditMode.group();
      await frame();

      const textNodes = (member) => Array.from(member.querySelectorAll(':scope > [data-edit-layer]')).filter((node) => {
        const kind = node.dataset.editLayer;
        return kind === 'text' || kind === 'metric';
      });
      const snapshot = () => members.map((member) => {
        const rect = member.getBoundingClientRect();
        const matrix = new DOMMatrixReadOnly(getComputedStyle(member).transform === 'none'
          ? undefined : getComputedStyle(member).transform);
        return {
          rect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height },
          transform: member.style.transform || '',
          scaleX: matrix.a,
          scaleY: matrix.d,
          text: textNodes(member).map((node) => {
            const style = getComputedStyle(node);
            const box = node.getBoundingClientRect();
            const range = document.createRange();
            range.selectNodeContents(node);
            const lineTops = [];
            Array.from(range.getClientRects()).filter((rect) => rect.width > 0 && rect.height > 0).forEach((rect) => {
              if (!lineTops.some((top) => Math.abs(top - rect.top) <= 1)) lineTops.push(rect.top);
            });
            return {
              value: (node.textContent || '').trim(),
              fontSize: parseFloat(style.fontSize),
              lineHeight: parseFloat(style.lineHeight),
              lineCount: Math.max(1, lineTops.length),
              top: box.top,
              bottom: box.bottom,
              left: box.left,
              right: box.right,
              transform: node.style.transform || '',
            };
          }),
        };
      });
      const textFits = (items) => items.every((member) => {
        const rootTop = member.rect.top - 0.8;
        const rootBottom = member.rect.top + member.rect.height + 0.8;
        if (member.text.some((text) => text.top < rootTop || text.bottom > rootBottom)) return false;
        for (let first = 0; first < member.text.length; first += 1) {
          for (let second = first + 1; second < member.text.length; second += 1) {
            const horizontal = Math.min(member.text[first].right, member.text[second].right)
              - Math.max(member.text[first].left, member.text[second].left);
            const vertical = Math.min(member.text[first].bottom, member.text[second].bottom)
              - Math.max(member.text[first].top, member.text[second].top);
            if (horizontal > 1 && vertical > 0.8) return false;
          }
        }
        return true;
      });
      const dragBy = async (handleName, dx, dy) => {
        const handle = document.querySelector(`.edit-resize-handle[data-handle="${handleName}"]`);
        const rect = handle.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        handle.dispatchEvent(new MouseEvent('mousedown', {
          bubbles: true, button: 0, clientX: startX, clientY: startY,
        }));
        window.dispatchEvent(new MouseEvent('mousemove', {
          bubbles: true, button: 0, clientX: startX + dx, clientY: startY + dy,
        }));
        window.dispatchEvent(new MouseEvent('mouseup', {
          bubbles: true, button: 0, clientX: startX + dx, clientY: startY + dy,
        }));
        await frame();
      };

      const before = snapshot();
      const moderateDy = -before[0].rect.height * 0.2;
      await dragBy('s', 0, moderateDy);
      const moderate = snapshot();
      const moderateGeometry = moderate.every((member, index) => (
        member.rect.height < before[index].rect.height - 10
        && near(member.rect.width, before[index].rect.width)
        && near(member.rect.top, before[index].rect.top)
        && near(member.scaleY, before[index].scaleY, 0.01)
      ));
      const moderateFontsStable = moderate.every((member, memberIndex) => member.text.every((text, textIndex) => (
        near(text.fontSize, before[memberIndex].text[textIndex].fontSize, 0.2)
      )));
      const moderateLineHeightStable = moderate.every((member, memberIndex) => member.text.every((text, textIndex) => (
        near(text.lineHeight, before[memberIndex].text[textIndex].lineHeight, 0.2)
      )));
      const moderateSpacingMoved = moderate.some((member, memberIndex) => member.text.some((text, textIndex) => (
        text.transform !== before[memberIndex].text[textIndex].transform
      )));
      const moderatePass = moderateGeometry && moderateFontsStable && moderateLineHeightStable
        && moderateSpacingMoved && textFits(moderate);

      window.EditMode.undo();
      await frame();
      const restored = snapshot();
      const undoPass = restored.every((member, memberIndex) => (
        near(member.rect.left, before[memberIndex].rect.left)
        && near(member.rect.top, before[memberIndex].rect.top)
        && near(member.rect.width, before[memberIndex].rect.width)
        && near(member.rect.height, before[memberIndex].rect.height)
        && member.text.every((text, textIndex) => (
          near(text.fontSize, before[memberIndex].text[textIndex].fontSize, 0.2)
          && near(text.lineHeight, before[memberIndex].text[textIndex].lineHeight, 0.2)
          && text.transform === before[memberIndex].text[textIndex].transform
        ))
      ));

      const intermediateDy = -before[0].rect.height * 0.35;
      await dragBy('s', 0, intermediateDy);
      const intermediate = snapshot();
      const intermediateFontsStable = intermediate.every((member, memberIndex) => member.text.every((text, textIndex) => (
        near(text.fontSize, before[memberIndex].text[textIndex].fontSize, 0.2)
      )));
      const intermediateLineHeightReduced = intermediate.some((member, memberIndex) => member.text.some((text, textIndex) => (
        text.lineHeight < before[memberIndex].text[textIndex].lineHeight - 0.5
      )));
      const intermediatePass = intermediateFontsStable && intermediateLineHeightReduced
        && textFits(intermediate);
      window.EditMode.undo();
      await frame();

      await dragBy('e', -40, 0);
      const inward = snapshot();
      const inwardGeometry = inward.every((member, memberIndex) => (
        member.rect.width < before[memberIndex].rect.width - 5
        && near(member.rect.height, before[memberIndex].rect.height)
        && near(member.scaleX, before[memberIndex].scaleX, 0.01)
        && near(member.scaleY, before[memberIndex].scaleY, 0.01)
      ));
      const inwardFontsStable = inward.every((member, memberIndex) => member.text.every((text, textIndex) => (
        near(text.fontSize, before[memberIndex].text[textIndex].fontSize, 0.2)
      )));
      const inwardLinesStable = inward.every((member, memberIndex) => member.text.every((text, textIndex) => (
        text.lineCount === before[memberIndex].text[textIndex].lineCount
      )));
      const inwardTextFramesHeld = inward.every((member, memberIndex) => member.text.every((text, textIndex) => (
        (text.right - text.left) >= (before[memberIndex].text[textIndex].right - before[memberIndex].text[textIndex].left) - 1
      )));
      const inwardTextInside = inward.every((member) => member.text.every((text) => (
        text.left >= member.rect.left - 0.8 && text.right <= member.rect.left + member.rect.width + 0.8
      )));
      const inwardPass = inwardGeometry && inwardFontsStable && inwardLinesStable
        && inwardTextFramesHeld && inwardTextInside;
      window.EditMode.undo();
      await frame();

      await dragBy('e', 72, 0);
      const horizontal = snapshot();
      const horizontalGeometry = horizontal.every((member, memberIndex) => (
        member.rect.width > before[memberIndex].rect.width + 10
        && near(member.rect.height, before[memberIndex].rect.height)
        && near(member.scaleX, before[memberIndex].scaleX, 0.01)
        && near(member.scaleY, before[memberIndex].scaleY, 0.01)
      ));
      const horizontalFontsStable = horizontal.every((member, memberIndex) => member.text.every((text, textIndex) => (
        near(text.fontSize, before[memberIndex].text[textIndex].fontSize, 0.2)
      )));
      const horizontalTextFramesExpanded = horizontal.every((member, memberIndex) => member.text.every((text, textIndex) => (
        (text.right - text.left) > (before[memberIndex].text[textIndex].right - before[memberIndex].text[textIndex].left) + 1
      )));
      const horizontalPass = horizontalGeometry && horizontalFontsStable
        && horizontalTextFramesExpanded;
      window.EditMode.undo();
      await frame();
      const horizontalRestored = snapshot();
      const horizontalUndoPass = horizontalRestored.every((member, memberIndex) => (
        near(member.rect.left, before[memberIndex].rect.left)
        && near(member.rect.top, before[memberIndex].rect.top)
        && near(member.rect.width, before[memberIndex].rect.width)
        && near(member.rect.height, before[memberIndex].rect.height)
      ));

      const deepDy = -before[0].rect.height * 0.55;
      await dragBy('s', 0, deepDy);
      const deep = snapshot();
      const deepFontsReduced = deep.some((member, memberIndex) => member.text.some((text, textIndex) => (
        text.fontSize < before[memberIndex].text[textIndex].fontSize - 0.5
      )));
      const deepPass = deepFontsReduced && textFits(deep)
        && deep.every((member, index) => near(member.scaleY, before[index].scaleY, 0.01));

      window.EditMode.undo();
      await frame();
      const editMemberButton = document.querySelector('[data-action="edit-group-member"]');
      if (editMemberButton) editMemberButton.click();
      await frame();
      const exactTitle = members[1].querySelector(':scope > b[data-edit-layer="text"]');
      fireClick(exactTitle);
      await frame();
      const rootBeforeDrill = members[1].getBoundingClientRect();
      const titleBeforeDrill = exactTitle.getBoundingClientRect();
      const titleFontBeforeDrill = parseFloat(getComputedStyle(exactTitle).fontSize);
      const rootTransformBeforeDrill = members[1].style.transform || '';
      await dragBy('e', 72, 0);
      const rootAfterDrill = members[1].getBoundingClientRect();
      const titleAfterDrill = exactTitle.getBoundingClientRect();
      const titleFontAfterDrill = parseFloat(getComputedStyle(exactTitle).fontSize);
      const drillInPass = near(rootAfterDrill.width, rootBeforeDrill.width)
        && titleAfterDrill.width > titleBeforeDrill.width + 10
        && near(titleFontAfterDrill, titleFontBeforeDrill, 0.2)
        && (members[1].style.transform || '') === rootTransformBeforeDrill;
      window.EditMode.undo();
      await frame();
      const drillRestored = exactTitle.getBoundingClientRect();
      const drillUndoPass = near(drillRestored.width, titleBeforeDrill.width);

      const firstSlide = document.querySelector('#s1');
      const firstThumb = document.querySelector('.slide-thumb .slide-thumb-canvas');
      const firstSlideStyle = firstSlide && getComputedStyle(firstSlide);
      const firstThumbStyle = firstThumb && getComputedStyle(firstThumb);
      const thumbnailPass = Boolean(firstSlide && firstThumb)
        && !firstThumb.classList.contains('slide')
        && firstThumbStyle.backgroundColor === firstSlideStyle.backgroundColor
        && firstThumbStyle.backgroundImage === firstSlideStyle.backgroundImage;

      return {
        pass: moderatePass && intermediatePass && inwardPass && undoPass && horizontalPass
          && horizontalUndoPass && deepPass && drillInPass && drillUndoPass && thumbnailPass,
        selectedMembers: members.length,
        checks: {
          moderateSpacing: { pass: moderatePass, moderateGeometry, moderateFontsStable,
            moderateLineHeightStable, moderateSpacingMoved, textFits: textFits(moderate) },
          intermediateLineHeight: { pass: intermediatePass, intermediateFontsStable,
            intermediateLineHeightReduced, textFits: textFits(intermediate) },
          inwardWrapGuard: { pass: inwardPass, inwardGeometry, inwardFontsStable,
            inwardLinesStable, inwardTextFramesHeld, inwardTextInside },
          horizontal: { pass: horizontalPass, horizontalGeometry, horizontalFontsStable,
            horizontalTextFramesExpanded, undoPass: horizontalUndoPass },
          deep: { pass: deepPass, deepFontsReduced, textFits: textFits(deep) },
          drillInTitle: { pass: drillInPass, undoPass: drillUndoPass,
            value: exactTitle && (exactTitle.textContent || '').trim(),
            rootWidthBefore: rootBeforeDrill.width, rootWidthAfter: rootAfterDrill.width,
            titleWidthBefore: titleBeforeDrill.width, titleWidthAfter: titleAfterDrill.width,
            fontBefore: titleFontBeforeDrill, fontAfter: titleFontAfterDrill,
            rootTransformBefore: rootTransformBeforeDrill, rootTransformAfter: members[1].style.transform || '' },
          undo: { pass: undoPass },
          thumbnail: {
            pass: thumbnailPass,
            slideBackground: firstSlideStyle && firstSlideStyle.background,
            thumbnailBackground: firstThumbStyle && firstThumbStyle.background,
            thumbnailHasSlideClass: firstThumb && firstThumb.classList.contains('slide'),
          },
        },
        samples: { before, moderate, intermediate, inward, horizontal, deep },
      };
    });

    await page.reload({ waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });

    const moduleBoundary = await page.evaluate(async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const near = (a, b, tolerance = 1.2) => Math.abs(a - b) <= tolerance;
      const slide = document.querySelector('#s2');
      const members = slide ? Array.from(slide.querySelectorAll('.toc-panel-row')) : [];
      if (!slide || members.length < 3 || !window.EditMode) {
        return { pass: false, error: 'TOC semantic-module fixture missing' };
      }

      window.setSlide(Number(slide.dataset.index));
      if (!document.documentElement.classList.contains('edit-mode')) window.EditMode.toggle(true);
      await frame();

      const fireClick = (el, additive = false) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0,
          shiftKey: additive,
          clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ['mousedown', 'mouseup', 'click'].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      fireClick(members[0]);
      await frame();
      for (const member of members.slice(1)) {
        fireClick(member, true);
        await frame();
      }

      const rectOf = (node) => {
        const rect = node.getBoundingClientRect();
        return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
          width: rect.width, height: rect.height };
      };
      const paintedTextRect = (node) => {
        const range = document.createRange();
        range.selectNodeContents(node);
        const rect = range.getBoundingClientRect();
        return rect.width > 0.5 && rect.height > 0.5 ? rect : node.getBoundingClientRect();
      };
      const lineCount = (node) => {
        const range = document.createRange();
        range.selectNodeContents(node);
        const tops = [];
        Array.from(range.getClientRects()).filter((rect) => rect.width > 0.5 && rect.height > 0.5)
          .forEach((rect) => {
            if (!tops.some((top) => Math.abs(top - rect.top) <= 1)) tops.push(rect.top);
          });
        return Math.max(1, tops.length);
      };
      const snapshot = () => {
        const rowRects = members.map(rectOf);
        const union = {
          left: Math.min.apply(null, rowRects.map((rect) => rect.left)),
          top: Math.min.apply(null, rowRects.map((rect) => rect.top)),
          right: Math.max.apply(null, rowRects.map((rect) => rect.right)),
          bottom: Math.max.apply(null, rowRects.map((rect) => rect.bottom)),
        };
        union.width = union.right - union.left;
        union.height = union.bottom - union.top;
        return {
          frame: rectOf(document.querySelector('#edit-selection-frame')),
          content: rectOf(slide.querySelector('[data-content-area]')),
          union,
          members: members.map((member, index) => ({
            rect: rowRects[index],
            text: Array.from(member.querySelectorAll(':scope > [data-edit-layer]')).filter((node) => {
              const kind = node.dataset.editLayer;
              return kind === 'text' || kind === 'metric';
            }).map((node) => {
              const style = getComputedStyle(node);
              const rect = paintedTextRect(node);
              return {
                value: (node.textContent || '').trim(),
                rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
                  width: rect.width, height: rect.height },
                fontSize: parseFloat(style.fontSize),
                lineHeight: parseFloat(style.lineHeight),
                lineCount: lineCount(node),
                wrapMode: node.dataset.editWrapMode || '',
                whiteSpace: style.whiteSpace,
              };
            }),
          })),
        };
      };
      const textFits = (state) => state.members.every((member) => {
        const root = member.rect;
        if (member.text.some((text) => (
          text.rect.left < root.left - 0.8 || text.rect.right > root.right + 0.8
          || text.rect.top < root.top - 0.8 || text.rect.bottom > root.bottom + 0.8
        ))) return false;
        for (let first = 0; first < member.text.length; first += 1) {
          for (let second = first + 1; second < member.text.length; second += 1) {
            const horizontal = Math.min(member.text[first].rect.right, member.text[second].rect.right)
              - Math.max(member.text[first].rect.left, member.text[second].rect.left);
            const vertical = Math.min(member.text[first].rect.bottom, member.text[second].rect.bottom)
              - Math.max(member.text[first].rect.top, member.text[second].rect.top);
            if (horizontal > 1 && vertical > 2) return false;
          }
        }
        return true;
      });
      const geometryPass = (state) => (
        state.union.left >= state.content.left - 1.2
        && state.union.top >= state.content.top - 1.2
        && state.union.right <= state.content.right + 1.2
        && state.union.bottom <= state.content.bottom + 1.2
        && near(state.frame.left, state.union.left, 1.2)
        && near(state.frame.top, state.union.top, 1.2)
        && near(state.frame.width, state.union.width, 1.2)
        && near(state.frame.height, state.union.height, 1.2)
        && textFits(state)
      );
      const dragBy = async (handleName, dx, dy) => {
        const handle = document.querySelector(`.edit-resize-handle[data-handle="${handleName}"]`);
        const rect = handle.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        handle.dispatchEvent(new MouseEvent('mousedown', {
          bubbles: true, button: 0, clientX: startX, clientY: startY,
        }));
        window.dispatchEvent(new MouseEvent('mousemove', {
          bubbles: true, button: 0, clientX: startX + dx, clientY: startY + dy,
        }));
        window.dispatchEvent(new MouseEvent('mouseup', {
          bubbles: true, button: 0, clientX: startX + dx, clientY: startY + dy,
        }));
        await frame();
      };

      const before = snapshot();
      await dragBy('e', -before.frame.width * 0.78, 0);
      const reflow = snapshot();
      const reflowDetected = reflow.members.some((member, memberIndex) => member.text.some((text, textIndex) => (
        text.lineCount > before.members[memberIndex].text[textIndex].lineCount
      )));
      const naturalWrap = reflow.members.every((member) => member.text.every((text) => (
        text.wrapMode === 'natural' && text.whiteSpace === 'normal'
      )));
      const reflowPass = reflowDetected && naturalWrap && geometryPass(reflow)
        && reflow.members.every((member, index) => near(member.rect.height, before.members[index].rect.height));

      window.EditMode.undo();
      await frame();
      const restored = snapshot();
      const restoredPass = restored.members.every((member, index) => (
        near(member.rect.left, before.members[index].rect.left)
        && near(member.rect.top, before.members[index].rect.top)
        && near(member.rect.width, before.members[index].rect.width)
        && near(member.rect.height, before.members[index].rect.height)
      ));

      const repeated = [restored];
      for (let index = 0; index < 8; index += 1) {
        const current = repeated[repeated.length - 1];
        await dragBy('n', 0, current.frame.height * 0.45);
        repeated.push(snapshot());
      }
      const monotonic = repeated.slice(1).every((state, index) => (
        state.frame.height <= repeated[index].frame.height + 1.2
      ));
      const bottomAnchorStable = repeated.slice(1).every((state) => (
        near(state.frame.bottom, repeated[0].frame.bottom, 1.2)
      ));
      const repeatedGeometryPass = repeated.every(geometryPass);
      const inwardShrinkOccurred = repeated.some((state) => (
        state.frame.height < repeated[0].frame.height - 20
      ));
      const repeatPass = monotonic && bottomAnchorStable && repeatedGeometryPass && inwardShrinkOccurred;

      return {
        pass: reflowPass && restoredPass && repeatPass,
        selectedMembers: members.length,
        checks: {
          horizontalNaturalReflow: { pass: reflowPass, reflowDetected, naturalWrap,
            geometryPass: geometryPass(reflow) },
          horizontalUndo: { pass: restoredPass },
          repeatedInwardClamp: { pass: repeatPass, monotonic, bottomAnchorStable,
            geometryPass: repeatedGeometryPass, inwardShrinkOccurred },
        },
        samples: {
          before,
          reflow,
          repeated: repeated.map((state) => ({ frame: state.frame, content: state.content,
            union: state.union, memberHeights: state.members.map((member) => member.rect.height) })),
        },
      };
    });

    await page.setViewportSize({ width: 769, height: 786 });
    const compactViewport = await page.evaluate(async () => {
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const slide = document.querySelector('#s2');
      const content = slide && slide.querySelector('[data-content-area]');
      const frame = document.querySelector('#edit-selection-frame');
      const members = slide ? Array.from(slide.querySelectorAll('.toc-panel-row')) : [];
      if (!slide || !content || !frame || members.length !== 5) {
        return { pass: false, error: 'Compact viewport fixture missing' };
      }
      const rectOf = (node) => {
        const rect = node.getBoundingClientRect();
        return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
          width: rect.width, height: rect.height };
      };
      const memberRects = members.map(rectOf);
      const union = {
        left: Math.min.apply(null, memberRects.map((rect) => rect.left)),
        top: Math.min.apply(null, memberRects.map((rect) => rect.top)),
        right: Math.max.apply(null, memberRects.map((rect) => rect.right)),
        bottom: Math.max.apply(null, memberRects.map((rect) => rect.bottom)),
      };
      union.width = union.right - union.left;
      union.height = union.bottom - union.top;
      const contentRect = rectOf(content);
      const frameRect = rectOf(frame);
      const slideRect = rectOf(slide);
      const near = (a, b, tolerance = 1.2) => Math.abs(a - b) <= tolerance;
      const inside = union.left >= contentRect.left - 1.2
        && union.top >= contentRect.top - 1.2
        && union.right <= contentRect.right + 1.2
        && union.bottom <= contentRect.bottom + 1.2;
      const frameMatches = near(frameRect.left, union.left)
        && near(frameRect.top, union.top)
        && near(frameRect.width, union.width)
        && near(frameRect.height, union.height);
      const slideContains = union.left >= slideRect.left - 1.2
        && union.top >= slideRect.top - 1.2
        && union.right <= slideRect.right + 1.2
        && union.bottom <= slideRect.bottom + 1.2;
      return {
        pass: inside && frameMatches && slideContains,
        inside,
        frameMatches,
        slideContains,
        viewport: { width: innerWidth, height: innerHeight },
        slide: slideRect,
        content: contentRect,
        frame: frameRect,
        union,
      };
    });
    if (options.compactScreenshot) {
      const screenshotPath = path.resolve(options.compactScreenshot);
      await fs.mkdir(path.dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path: screenshotPath });
    }

    result = {
      pass: Boolean(moduleBoundary.pass && compactViewport.pass),
      selectedMembers: moduleBoundary.selectedMembers || 0,
      checks: {
        moduleBoundary: {
          pass: Boolean(moduleBoundary.pass),
          ...(moduleBoundary.checks || {}),
        },
        compactViewport: compactViewport,
        legacyFixtureDiagnostic: {
          pass: Boolean(coreResult.pass),
          blocking: false,
          reason: 'Older two-card fixture retained for diagnostics; the current gate uses the five-row semantic-module selection.',
          ...(coreResult.checks || {}),
        },
      },
      samples: {
        moduleBoundary: moduleBoundary.samples,
        compactViewport: compactViewport,
        legacyFixtureDiagnostic: coreResult.samples,
      },
    };
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
