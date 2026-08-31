const fs = require('node:fs/promises');
const fsSync = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

function optionsOf(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--html') options.html = argv[++index];
    else if (argv[index] === '--report') options.report = argv[++index];
  }
  if (!options.html || !options.report) throw new Error('--html and --report are required');
  return options;
}

async function main() {
  const options = optionsOf(process.argv);
  const htmlPath = path.resolve(options.html);
  const reportPath = path.resolve(options.report);
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean);
  const executablePath = browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
  await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
  try {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'commit', timeout: 30000 });
    await page.waitForFunction(() => document.documentElement.dataset.layoutReady === 'true' && Boolean(window.EditMode), null, { timeout: 120000 });
    const result = await page.evaluate(async () => {
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const fireClick = (el) => ['mousedown', 'mouseup', 'click'].forEach((type) => el.dispatchEvent(new MouseEvent(type, {
        bubbles: true, clientX: 480, clientY: 260, button: 0,
      })));
      const resizeWithHandle = async (target, position, dx, dy) => {
        fireClick(target);
        await nextFrame();
        const handle = document.querySelector(`.edit-resize-handle[data-handle="${position}"]`);
        const rect = handle?.getBoundingClientRect();
        if (!handle || !rect) return false;
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        handle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: x, clientY: y, button: 0 }));
        window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: x + dx, clientY: y + dy, button: 0 }));
        window.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: x + dx, clientY: y + dy, button: 0 }));
        await nextFrame();
        return true;
      };

      window.EditMode.toggle(true);
      await nextFrame();
      const target = [...document.querySelectorAll('.slide [data-edit-fit="text"]')]
        .find((el) => getComputedStyle(el).display !== 'none' && (el.textContent || '').trim());
      if (!target) return { targetFound: false, pass: false };
      window.setSlide(Number(target.closest('.slide').dataset.index));
      await nextFrame();

      const beforeWidthRect = target.getBoundingClientRect();
      const beforeWidthFont = parseFloat(getComputedStyle(target).fontSize);
      const widthHandleFound = await resizeWithHandle(target, 'e', Math.max(72, beforeWidthRect.width * 0.22), 0);
      const afterWidthRect = target.getBoundingClientRect();
      const afterWidthFont = parseFloat(getComputedStyle(target).fontSize);
      const textRangeAfterWidth = document.createRange();
      textRangeAfterWidth.selectNodeContents(target);
      const afterWidthTextRect = textRangeAfterWidth.getBoundingClientRect();
      const horizontalFrameResize = {
        handleFound: widthHandleFound,
        widthChanged: afterWidthRect.width > beforeWidthRect.width + 40,
        fontStable: Math.abs(afterWidthFont - beforeWidthFont) <= 0.1,
        manualWidth: target.dataset.editFrameWidth === 'manual',
        textFitsFrame: afterWidthTextRect.width <= afterWidthRect.width + 3
          && afterWidthTextRect.height <= afterWidthRect.height + 3,
      };
      window.EditMode.undo();
      await nextFrame();
      const widthUndoRect = target.getBoundingClientRect();
      horizontalFrameResize.undoPass = Math.abs(widthUndoRect.width - beforeWidthRect.width) <= 1.5
        && Math.abs(widthUndoRect.height - beforeWidthRect.height) <= 1.5
        && target.dataset.editFrameWidth !== 'manual';
      horizontalFrameResize.pass = Object.values(horizontalFrameResize).every(Boolean);

      const beforeHeightRect = target.getBoundingClientRect();
      const beforeHeightFont = parseFloat(getComputedStyle(target).fontSize);
      const heightHandleFound = await resizeWithHandle(target, 's', 0, Math.max(54, beforeHeightRect.height * 0.75));
      const afterHeightRect = target.getBoundingClientRect();
      const afterHeightFont = parseFloat(getComputedStyle(target).fontSize);
      const verticalFrameResize = {
        handleFound: heightHandleFound,
        heightChanged: afterHeightRect.height > beforeHeightRect.height + 24,
        widthStable: Math.abs(afterHeightRect.width - beforeHeightRect.width) <= 1.5,
        fontStable: Math.abs(afterHeightFont - beforeHeightFont) <= 0.1,
        manualHeight: target.dataset.editFrameHeight === 'manual',
      };
      window.EditMode.undo();
      await nextFrame();
      const heightUndoRect = target.getBoundingClientRect();
      verticalFrameResize.undoPass = Math.abs(heightUndoRect.width - beforeHeightRect.width) <= 1.5
        && Math.abs(heightUndoRect.height - beforeHeightRect.height) <= 1.5
        && target.dataset.editFrameHeight !== 'manual';
      verticalFrameResize.pass = Object.values(verticalFrameResize).every(Boolean);

      const beforeCornerRect = target.getBoundingClientRect();
      const textRange = document.createRange();
      textRange.selectNodeContents(target);
      const beforeTextRect = textRange.getBoundingClientRect();
      const cornerHandleFound = await resizeWithHandle(target, 'se', beforeCornerRect.width * 0.18, beforeCornerRect.height * 0.18);
      const afterCornerRect = target.getBoundingClientRect();
      const afterTextRect = textRange.getBoundingClientRect();
      const widthRatio = afterCornerRect.width / beforeCornerRect.width;
      const heightRatio = afterCornerRect.height / beforeCornerRect.height;
      const textRatio = afterTextRect.height / beforeTextRect.height;
      const cornerScale = {
        handleFound: cornerHandleFound,
        aspectStable: Math.abs(widthRatio - heightRatio) <= 0.02,
        contentScaled: widthRatio > 1.08 && Math.abs(textRatio - widthRatio) <= 0.04,
      };
      window.EditMode.undo();
      await nextFrame();
      const cornerUndoRect = target.getBoundingClientRect();
      cornerScale.undoPass = Math.abs(cornerUndoRect.width - beforeCornerRect.width) <= 1.5
        && Math.abs(cornerUndoRect.height - beforeCornerRect.height) <= 1.5;
      cornerScale.pass = Object.values(cornerScale).every(Boolean);

      const originalStyle = target.getAttribute('style');
      const originalHtml = target.innerHTML;
      const originalFrameWidth = target.dataset.editFrameWidth || '';
      const originalFrameHeight = target.dataset.editFrameHeight || '';
      const anchorX = (rect, align) => align === 'center' ? rect.left + rect.width / 2 : (align === 'right' ? rect.right : rect.left);
      const anchorCases = [];
      for (const align of ['left', 'center', 'right']) {
        if (originalStyle === null) target.removeAttribute('style');
        else target.setAttribute('style', originalStyle);
        target.innerHTML = originalHtml;
        if (originalFrameWidth) target.dataset.editFrameWidth = originalFrameWidth;
        else delete target.dataset.editFrameWidth;
        if (originalFrameHeight) target.dataset.editFrameHeight = originalFrameHeight;
        else delete target.dataset.editFrameHeight;
        target.style.setProperty('text-align', align, 'important');
        fireClick(target);
        fireClick(target);
        await nextFrame();
        const beforeRect = target.getBoundingClientRect();
        const beforeAnchor = anchorX(beforeRect, align);
        target.dispatchEvent(new InputEvent('beforeinput', { bubbles: true, inputType: 'insertParagraph', data: null }));
        target.innerHTML = '水平錨點測試<br>換行後仍維持定位';
        target.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertParagraph', data: null }));
        await nextFrame();
        const afterRect = target.getBoundingClientRect();
        const afterAnchor = anchorX(afterRect, align);
        fireClick(target.closest('.slide'));
        await nextFrame();
        window.EditMode.undo();
        await nextFrame();
        const undoRect = target.getBoundingClientRect();
        anchorCases.push({
          align,
          drift: Math.round(Math.abs(afterAnchor - beforeAnchor) * 10) / 10,
          anchorStable: Math.abs(afterAnchor - beforeAnchor) <= 1.5,
          undoPass: target.innerHTML === originalHtml
            && Math.abs(undoRect.left - beforeRect.left) <= 1.5
            && Math.abs(undoRect.width - beforeRect.width) <= 1.5,
        });
      }
      const textEditAnchor = {
        cases: anchorCases,
        pass: anchorCases.length === 3 && anchorCases.every((item) => item.anchorStable && item.undoPass),
      };
      return {
        targetFound: true,
        horizontalFrameResize,
        verticalFrameResize,
        cornerScale,
        textEditAnchor,
        pass: horizontalFrameResize.pass && verticalFrameResize.pass && cornerScale.pass && textEditAnchor.pass,
      };
    });
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(result, null, 2), 'utf8');
    process.stdout.write(JSON.stringify(result, null, 2));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await Promise.race([
      browser.close(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
  }
}

main().then(() => {
  process.exit(process.exitCode || 0);
}).catch((error) => {
  console.error(error);
  process.exit(1);
});
