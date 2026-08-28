const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

function argsOf(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--url') options.url = argv[++index];
    else if (argv[index] === '--report') options.report = argv[++index];
    else if (argv[index] === '--screenshot') options.screenshot = argv[++index];
  }
  if (!options.url || !options.report) throw new Error('--url and --report are required');
  return options;
}

async function nextFrame(page) {
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));
}

async function main() {
  const options = argsOf(process.argv);
  const executablePath = [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean).find((candidate) => fs.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await page.goto(options.url, { waitUntil: 'commit', timeout: 120000 });
    await page.waitForFunction(
      () => document.documentElement.dataset.layoutReady === 'true' && Boolean(window.EditMode),
      null,
      { timeout: 120000 },
    );
    await page.evaluate(() => {
      window.setSlide(1);
      window.EditMode.toggle(true);
    });
    await nextFrame(page);

    const selector = '.slide.active .toc-panel-grid-card.card-1 b[data-edit-layer="text"]';
    const target = page.locator(selector).first();
    const targetBox = await target.boundingBox();
    if (!targetBox) throw new Error(`No visible text target for ${selector}`);
    await page.mouse.click(targetBox.x + Math.min(targetBox.width / 2, 60), targetBox.y + targetBox.height / 2);
    await nextFrame(page);
    await page.evaluate(() => window.EditMode.ungroup());
    await nextFrame(page);

    const geometry = await page.evaluate((targetSelector) => {
      const targetEl = document.querySelector(targetSelector);
      const elementRect = targetEl.getBoundingClientRect();
      const rects = [];
      const walker = document.createTreeWalker(targetEl, NodeFilter.SHOW_TEXT, {
        acceptNode: (node) => (
          node.nodeValue && node.nodeValue.trim()
            ? NodeFilter.FILTER_ACCEPT
            : NodeFilter.FILTER_REJECT
        ),
      });
      let node = walker.nextNode();
      while (node) {
        const range = document.createRange();
        range.selectNodeContents(node);
        rects.push(...Array.from(range.getClientRects()).filter((rect) => rect.width > 0.5 && rect.height > 0.5));
        node = walker.nextNode();
      }
      const line = rects
        .filter((rect) => elementRect.right - rect.right >= 16)
        .sort((a, b) => (elementRect.right - b.right) - (elementRect.right - a.right))[0];
      if (!line) return null;
      const blankX = line.right + Math.min(30, (elementRect.right - line.right) / 2);
      const blankY = line.top + line.height / 2;
      const firstCard = document.querySelector('.slide.active .toc-panel-grid-card.card-1').getBoundingClientRect();
      const secondCard = document.querySelector('.slide.active .toc-panel-grid-card.card-2').getBoundingClientRect();
      return {
        glyphPoint: { x: line.left + Math.min(line.width / 2, 50), y: line.top + line.height / 2 },
        blankPoint: { x: blankX, y: blankY },
        trueBlankPoint: { x: (firstCard.right + secondCard.left) / 2, y: firstCard.top + firstCard.height / 2 },
        elementRect: {
          left: elementRect.left,
          top: elementRect.top,
          right: elementRect.right,
          bottom: elementRect.bottom,
          width: elementRect.width,
          height: elementRect.height,
        },
        glyphRects: rects.map((rect) => ({
          left: rect.left,
          top: rect.top,
          right: rect.right,
          bottom: rect.bottom,
          width: rect.width,
          height: rect.height,
        })),
      };
    }, selector);
    if (!geometry) throw new Error('The target does not expose a measurable transparent text tail');

    await page.mouse.click(geometry.glyphPoint.x, geometry.glyphPoint.y);
    await nextFrame(page);
    const selectedOnGlyph = await page.evaluate(() => (
      document.querySelector('#edit-selection-badge [data-role=label]')?.textContent?.trim() || ''
    ));

    await page.mouse.click(geometry.blankPoint.x, geometry.blankPoint.y);
    await nextFrame(page);
    const afterTailClick = await page.evaluate(() => {
      const frame = document.getElementById('edit-selection-frame');
      return {
        label: document.querySelector('#edit-selection-badge [data-role=label]')?.textContent?.trim() || '',
        frameVisible: Boolean(frame && getComputedStyle(frame).display !== 'none'),
      };
    });
    if (options.screenshot) {
      fs.mkdirSync(path.dirname(path.resolve(options.screenshot)), { recursive: true });
      await page.screenshot({ path: path.resolve(options.screenshot), fullPage: true });
    }

    await page.mouse.click(geometry.trueBlankPoint.x, geometry.trueBlankPoint.y);
    await nextFrame(page);
    const trueBlank = await page.evaluate(() => {
      const frame = document.getElementById('edit-selection-frame');
      return {
        label: document.querySelector('#edit-selection-badge [data-role=label]')?.textContent?.trim() || '',
        frameVisible: Boolean(frame && getComputedStyle(frame).display !== 'none'),
      };
    });

    const probeGeometry = await page.evaluate(() => {
      const contentArea = document.querySelector('.slide.active [data-content-area]');
      const root = document.createElement('div');
      root.className = 'el qa-transparent-wrapper';
      root.dataset.editComposite = 'qa-transparent-wrapper';
      root.dataset.editGroupState = 'ungrouped';
      root.style.cssText = 'left:620px;top:805px;width:360px;height:60px;background:transparent;border:0;padding:0;';
      const textLayer = document.createElement('span');
      textLayer.dataset.editLayer = 'text';
      textLayer.dataset.editPosition = 'absolute';
      textLayer.textContent = '定位框測試';
      textLayer.style.cssText = 'position:absolute;left:0;top:0;width:360px;height:60px;font-size:36px;line-height:1.2;color:#17343d;';
      root.appendChild(textLayer);
      contentArea.appendChild(root);
      const lineRange = document.createRange();
      lineRange.selectNodeContents(textLayer.firstChild);
      const lineRect = lineRange.getBoundingClientRect();
      const layerRect = textLayer.getBoundingClientRect();
      const tailX = Math.min(layerRect.right - 12, lineRect.right + 30);
      const tailY = lineRect.top + lineRect.height / 2;
      return {
        start: { x: tailX, y: tailY },
        end: { x: Math.min(layerRect.right - 2, tailX + 28), y: tailY + 24 },
        domTailTargetIsTextBox: Boolean(document.elementFromPoint(tailX, tailY)?.closest('.qa-transparent-wrapper [data-edit-layer="text"]')),
        tailOutsideGlyph: tailX > lineRect.right + 2,
      };
    });
    await page.mouse.move(probeGeometry.start.x, probeGeometry.start.y);
    await page.mouse.down();
    await page.mouse.move(probeGeometry.end.x, probeGeometry.end.y, { steps: 3 });
    const marqueeVisible = await page.evaluate(() => {
      const marquee = document.querySelector('.edit-marquee-box');
      return Boolean(marquee && getComputedStyle(marquee).display !== 'none');
    });
    await page.mouse.up();
    await nextFrame(page);
    const transparentWrapper = await page.evaluate(() => {
      const frame = document.getElementById('edit-selection-frame');
      const result = {
        frameVisible: Boolean(frame && getComputedStyle(frame).display !== 'none'),
        label: document.querySelector('#edit-selection-badge [data-role=label]')?.textContent?.trim() || '',
      };
      document.querySelector('.qa-transparent-wrapper')?.remove();
      return result;
    });
    transparentWrapper.domTailTargetIsTextBox = probeGeometry.domTailTargetIsTextBox;
    transparentWrapper.tailOutsideGlyph = probeGeometry.tailOutsideGlyph;
    transparentWrapper.marqueeVisibleDuringDrag = marqueeVisible;
    transparentWrapper.pass = transparentWrapper.domTailTargetIsTextBox
      && transparentWrapper.tailOutsideGlyph
      && transparentWrapper.marqueeVisibleDuringDrag
      && !transparentWrapper.frameVisible;

    const blankOutsideGlyphs = !geometry.glyphRects.some((rect) => (      geometry.blankPoint.x >= rect.left
      && geometry.blankPoint.x <= rect.right
      && geometry.blankPoint.y >= rect.top
      && geometry.blankPoint.y <= rect.bottom
    ));
    const report = {
      url: options.url,
      target: selector,
      geometry,
      checks: {
        glyphSelectsText: selectedOnGlyph === '已選取文字',
        blankPointInsideDomBox: geometry.blankPoint.x > geometry.elementRect.left
          && geometry.blankPoint.x < geometry.elementRect.right
          && geometry.blankPoint.y > geometry.elementRect.top
          && geometry.blankPoint.y < geometry.elementRect.bottom,
        blankPointOutsideGlyphs: blankOutsideGlyphs,
        transparentTailDoesNotSelectText: afterTailClick.label !== '已選取文字',
        trueBlankClearsSelection: !trueBlank.frameVisible,
        transparentWrapperTailStartsMarquee: transparentWrapper.pass,
      },
      selectedOnGlyph,
      afterTailClick,
      trueBlank,
      transparentWrapper,
    };
    report.pass = Object.values(report.checks).every(Boolean);
    fs.mkdirSync(path.dirname(path.resolve(options.report)), { recursive: true });
    fs.writeFileSync(path.resolve(options.report), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify(report));
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});