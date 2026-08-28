const fs = require('node:fs/promises');
const path = require('node:path');
const { browserExecutable, loadPlaywright } = require('./playwright_runtime.cjs');

function argsOf(argv) {
  const out = {
    slideIndex: 2,
    outerSelector: '.prod-frame[data-edit-layout-only="true"]',
    childSelector: '.module-card',
    layerSelector: 'b[data-edit-layer="text"]',
  };
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--url') out.url = argv[++index];
    else if (argv[index] === '--report') out.report = argv[++index];
    else if (argv[index] === '--screenshot') out.screenshot = argv[++index];
    else if (argv[index] === '--slide-index') out.slideIndex = Number(argv[++index]);
    else if (argv[index] === '--outer-selector') out.outerSelector = argv[++index];
    else if (argv[index] === '--child-selector') out.childSelector = argv[++index];
    else if (argv[index] === '--layer-selector') out.layerSelector = argv[++index];
  }
  if (!out.url || !out.report) throw new Error('--url and --report are required');
  return out;
}

function near(actual, expected, tolerance = 3) {
  return Math.abs(actual - expected) <= tolerance;
}

function sameRect(actual, expected, tolerance = 3) {
  return Boolean(actual && expected
    && near(actual.left, expected.left, tolerance)
    && near(actual.top, expected.top, tolerance)
    && near(actual.width, expected.width, tolerance)
    && near(actual.height, expected.height, tolerance));
}

async function clickCenter(page, locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error('click target has no visible bounding box');
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.waitForTimeout(120);
}

async function shiftClickCenter(page, locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error('shift-click target has no visible bounding box');
  await page.keyboard.down('Shift');
  try {
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  } finally {
    await page.keyboard.up('Shift');
  }
  await page.waitForTimeout(120);
}

async function clickAction(page, action) {
  const state = await page.evaluate((name) => {
    const button = document.querySelector(`[data-action="${name}"]`);
    if (!button) return { exists: false };
    if (button.disabled || button.getAttribute('aria-disabled') === 'true') {
      return { exists: true, disabled: true };
    }
    button.click();
    return { exists: true, disabled: false };
  }, action);
  if (!state.exists) throw new Error(`action not found: ${action}`);
  if (state.disabled) {
    const selection = await selectionState(page);
    throw new Error(`action is disabled: ${action}; selection=${JSON.stringify(selection)}`);
  }
  await page.waitForTimeout(100);
}

async function selectionState(page) {
  return page.evaluate(() => {
    const frame = document.getElementById('edit-selection-frame');
    const rect = frame && getComputedStyle(frame).display !== 'none'
      ? frame.getBoundingClientRect()
      : null;
    const buttonState = (action) => {
      const button = document.querySelector(`[data-action="${action}"]`);
      if (!button) return null;
      const rect = button.getBoundingClientRect();
      const style = getComputedStyle(button);
      return {
        text: (button.textContent || '').trim(),
        disabled: Boolean(button.disabled),
        ariaDisabled: button.getAttribute('aria-disabled') || '',
        visible: button.getClientRects().length > 0
          && style.display !== 'none'
          && style.visibility !== 'hidden'
          && rect.width > 1
          && rect.height > 1,
        rect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height },
        parentDisplay: button.parentElement ? getComputedStyle(button.parentElement).display : '',
      };
    };
    return {
      frame: rect ? {
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
      } : null,
      mode: frame?.dataset.selectionMode || '',
      memberFrameCount: [...document.querySelectorAll('.edit-selection-member-frame')]
        .filter((node) => getComputedStyle(node).display !== 'none').length,
      label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || '',
      editSingle: buttonState('edit-group-member'),
      previousGroup: buttonState('select-whole-group'),
    };
  });
}

async function main() {
  const options = argsOf(process.argv);
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 1800, height: 1000 } });
  try {
    await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await page.goto(options.url, { waitUntil: 'commit', timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === 'true' && Boolean(window.EditMode)
    ), null, { timeout: 120000 });

    await page.evaluate((slideIndex) => {
      const slides = [...document.querySelectorAll('.slide')];
      const active = slides[slideIndex];
      if (!active) throw new Error(`slide index ${slideIndex} not found`);
      slides.forEach((slide) => slide.classList.toggle('active', slide === active));
      document.dispatchEvent(new CustomEvent('slidechange', { detail: { index: slideIndex } }));
      window.EditMode.toggle(true);
      window.EditMode.deselect();
    }, options.slideIndex);
    await page.waitForTimeout(180);

    const activeSlide = page.locator('.slide.active');
    const outer = activeSlide.locator(options.outerSelector).first();
    const children = outer.locator(`:scope > ${options.childSelector}`);
    if (await outer.count() !== 1) throw new Error(`layout scope not found: ${options.outerSelector}`);
    if (await children.count() < 2) throw new Error(`at least two child groups are required: ${options.childSelector}`);

    await clickCenter(page, children.nth(0));
    for (let index = 1; index < await children.count(); index += 1) {
      await shiftClickCenter(page, children.nth(index));
    }
    await page.evaluate(() => window.EditMode.group());
    await page.waitForTimeout(120);
    await page.evaluate(() => window.EditMode.deselect());
    await page.waitForTimeout(80);

    await clickCenter(page, children.nth(0));
    const initialOuter = await selectionState(page);

    await clickCenter(page, children.nth(1));
    const repeatedChildClick = await selectionState(page);

    const gapPoint = await page.evaluate(({ outerSelector, childSelector }) => {
      const active = document.querySelector('.slide.active');
      const group = active?.querySelector(outerSelector);
      if (!group) return null;
      const direct = [...group.querySelectorAll(`:scope > ${childSelector}`)]
        .map((node) => node.getBoundingClientRect())
        .filter((rect) => rect.width > 2 && rect.height > 2);
      if (!direct.length) return null;
      const bounds = {
        left: Math.min(...direct.map((rect) => rect.left)),
        top: Math.min(...direct.map((rect) => rect.top)),
        right: Math.max(...direct.map((rect) => rect.right)),
        bottom: Math.max(...direct.map((rect) => rect.bottom)),
      };
      for (let y = bounds.top + 4; y < bounds.bottom - 4; y += 4) {
        for (let x = bounds.left + 4; x < bounds.right - 4; x += 4) {
          const insideMember = direct.some((rect) => (
            x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom
          ));
          if (!insideMember) return { x, y };
        }
      }
      return null;
    }, { outerSelector: options.outerSelector, childSelector: options.childSelector });
    if (!gapPoint) throw new Error('no gap point found inside the outer group frame');
    await page.mouse.click(gapPoint.x, gapPoint.y);
    await page.waitForTimeout(120);
    const gapClick = await selectionState(page);

    await clickAction(page, 'edit-group-member');
    const outerEditScope = await selectionState(page);

    await clickCenter(page, children.nth(1));
    const childSelected = await selectionState(page);
    const childRect = await children.nth(1).evaluate((node) => {
      const rect = node.getBoundingClientRect();
      return { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
    });

    const childLayer = children.nth(1).locator(options.layerSelector).first();
    if (await childLayer.count() !== 1) throw new Error(`child layer not found: ${options.layerSelector}`);
    await clickCenter(page, childLayer);
    const ordinaryChildClick = await selectionState(page);

    await clickAction(page, 'edit-group-member');
    await clickCenter(page, childLayer);
    const layerSelected = await selectionState(page);

    await clickAction(page, 'select-whole-group');
    const returnedToChild = await selectionState(page);
    await clickAction(page, 'select-whole-group');
    const returnedToOuter = await selectionState(page);

    await page.evaluate(() => window.EditMode.deselect());
    await page.waitForTimeout(80);
    await clickCenter(page, children.nth(0));
    const titleMember = activeSlide.locator('.el[data-title-stack-item="title"],.el.scene-title,h1.el').first();
    if (await titleMember.count() !== 1) throw new Error('loose title object not found');
    await shiftClickCenter(page, titleMember);
    await page.evaluate(() => window.EditMode.group());
    await page.waitForTimeout(120);
    const manualOuter = await selectionState(page);

    await clickCenter(page, children.nth(0));
    const manualOrdinaryClick = await selectionState(page);
    await clickAction(page, 'edit-group-member');
    await clickCenter(page, children.nth(0));
    const manualChildContent = await selectionState(page);
    await clickAction(page, 'edit-group-member');
    await clickCenter(page, children.nth(0));
    const manualNestedCard = await selectionState(page);
    await clickAction(page, 'edit-group-member');
    await clickCenter(page, children.nth(0).locator('[data-edit-layer]').first());
    const manualNestedLayer = await selectionState(page);
    await clickAction(page, 'select-whole-group');
    const manualReturnCard = await selectionState(page);
    await clickAction(page, 'select-whole-group');
    const manualReturnContent = await selectionState(page);
    await clickAction(page, 'select-whole-group');
    const manualReturnOuter = await selectionState(page);

    const checks = {
      firstClickSelectsOutermostGroup: initialOuter.mode === 'group'
        && initialOuter.memberFrameCount === 0,
      ordinaryChildClickKeepsOuterGroup: repeatedChildClick.mode === 'group'
        && sameRect(repeatedChildClick.frame, initialOuter.frame)
        && repeatedChildClick.memberFrameCount === 0,
      groupGapKeepsOuterGroup: gapClick.mode === 'group'
        && sameRect(gapClick.frame, initialOuter.frame)
        && gapClick.memberFrameCount === 0,
      editSingleIsExplicit: outerEditScope.mode === 'group'
        && sameRect(outerEditScope.frame, initialOuter.frame)
        && outerEditScope.previousGroup?.disabled === false,
      explicitEditSelectsDirectChildGroup: childSelected.mode === 'group'
        && sameRect(childSelected.frame, childRect)
        && !sameRect(childSelected.frame, initialOuter.frame),
      ordinaryClickDoesNotDrillChildGroup: ordinaryChildClick.mode === 'group'
        && sameRect(ordinaryChildClick.frame, childRect),
      secondExplicitEditSelectsLayer: layerSelected.mode === 'single'
        && layerSelected.editSingle?.disabled === true
        && layerSelected.previousGroup?.disabled === false,
      firstReturnRestoresChildGroup: returnedToChild.mode === 'group'
        && sameRect(returnedToChild.frame, childRect),
      secondReturnRestoresOuterGroup: returnedToOuter.mode === 'group'
        && sameRect(returnedToOuter.frame, initialOuter.frame)
        && returnedToOuter.previousGroup?.disabled === true,
      parentControlIsClear: returnedToOuter.previousGroup?.text === '上一層群組',
      manualGroupOrdinaryClickIsLocked: manualOuter.mode === 'group'
        && manualOuter.memberFrameCount === 0
        && manualOrdinaryClick.mode === 'group'
        && sameRect(manualOrdinaryClick.frame, manualOuter.frame),
      mixedNestedGroupsEnterOneLevelAtATime: manualChildContent.mode === 'group'
        && sameRect(manualChildContent.frame, initialOuter.frame)
        && manualNestedCard.mode === 'group'
        && !sameRect(manualNestedCard.frame, manualChildContent.frame)
        && manualNestedLayer.mode === 'single',
      mixedNestedGroupsReturnOneLevelAtATime: manualReturnCard.mode === 'group'
        && sameRect(manualReturnCard.frame, manualNestedCard.frame)
        && manualReturnContent.mode === 'group'
        && sameRect(manualReturnContent.frame, initialOuter.frame)
        && manualReturnOuter.mode === 'group'
        && sameRect(manualReturnOuter.frame, manualOuter.frame)
        && manualReturnOuter.previousGroup?.disabled === true,
    };
    const result = {
      pass: Object.values(checks).every(Boolean),
      checks,
      evidence: {
        initialOuter,
        repeatedChildClick,
        gapPoint,
        gapClick,
        outerEditScope,
        childRect,
        childSelected,
        ordinaryChildClick,
        layerSelected,
        returnedToChild,
        returnedToOuter,
        manualOuter,
        manualOrdinaryClick,
        manualChildContent,
        manualNestedCard,
        manualNestedLayer,
        manualReturnCard,
        manualReturnContent,
        manualReturnOuter,
      },
    };

    if (options.screenshot) {
      const screenshotPath = path.resolve(options.screenshot);
      await fs.mkdir(path.dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path: screenshotPath, fullPage: true });
    }
    const reportPath = path.resolve(options.report);
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
