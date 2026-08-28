const fs = require('node:fs/promises');
const fsSync = require('node:fs');
const path = require('node:path');
const { fileURLToPath } = require('node:url');
const { chromium } = require('playwright');

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--url') out.url = argv[++index];
    else if (argv[index] === '--report') out.report = argv[++index];
    else if (argv[index] === '--screenshot') out.screenshot = argv[++index];
  }
  if (!out.url || !out.report) throw new Error('--url and --report are required');
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const candidates = [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
    if (options.url.startsWith('file:')) {
      const markup = await fs.readFile(fileURLToPath(options.url), 'utf8');
      await page.setContent(markup, { waitUntil: 'domcontentloaded', timeout: 120000 });
    } else {
      await page.goto(options.url, { waitUntil: 'commit', timeout: 30000 });
    }
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === 'true' && Boolean(window.EditMode)
    ), null, { timeout: 120000 });

    const result = await page.evaluate(async () => {
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const visible = (node) => {
        if (!node || !node.getClientRects().length) return false;
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 2 && rect.height > 2;
      };
      const click = (node, shiftKey = false) => {
        const rect = node.getBoundingClientRect();
        const init = {
          bubbles: true,
          cancelable: true,
          button: 0,
          shiftKey,
          clientX: rect.left + Math.min(rect.width / 2, 24),
          clientY: rect.top + Math.min(rect.height / 2, 24),
        };
        node.dispatchEvent(new MouseEvent('mousedown', init));
        node.dispatchEvent(new MouseEvent('mouseup', init));
        node.dispatchEvent(new MouseEvent('click', init));
      };
      const memberFrames = () => [...document.querySelectorAll('.edit-selection-member-frame')].filter(visible);
      const frameState = () => {
        const outer = document.getElementById('edit-selection-frame');
        return {
          mode: outer?.dataset.selectionMode || '',
          reportedCount: Number(outer?.dataset.memberFrameCount || 0),
          visibleCount: memberFrames().length,
        };
      };

      window.EditMode.toggle(true);
      await nextFrame();
      const directLayers = (root) => [...root.querySelectorAll('[data-edit-layer]')].filter((item) => (
        item.closest('.el') === root && visible(item)
      ));
      let active = document.querySelector('.slide.active');
      let composites = active ? [...active.querySelectorAll('.el[data-edit-composite]')].filter((root) => (
        visible(root) && directLayers(root).length >= 2
      )) : [];
      if (!composites.length) {
        const candidateSlide = [...document.querySelectorAll('.slide')]
          .map((slide) => ({
            slide,
            count: [...slide.querySelectorAll('.el[data-edit-composite]')]
              .filter((root) => [...root.querySelectorAll('[data-edit-layer]')]
                .filter((item) => item.closest('.el') === root).length >= 2).length,
          }))
          .sort((a, b) => b.count - a.count)[0]?.slide;
        if (candidateSlide) {
          document.querySelectorAll('.slide').forEach((slide) => slide.classList.toggle('active', slide === candidateSlide));
          active = candidateSlide;
          await nextFrame();
          composites = [...active.querySelectorAll('.el[data-edit-composite]')].filter((root) => (
            visible(root) && directLayers(root).length >= 2
          ));
        }
      }
      const generatedRoot = composites[0];
      if (!generatedRoot) return { targetFound: false, pass: false };
      const generatedMembers = directLayers(generatedRoot);
      click(generatedMembers.find((node) => node.dataset.editLayer === 'text') || generatedMembers[0]);
      await nextFrame();
      const generatedParent = generatedRoot.parentElement?.closest('.el');
      if (generatedParent && generatedParent.dataset.editComposite) {
        document.querySelector('[data-action="edit-group-member"]')?.click();
        await nextFrame();
        click(generatedMembers.find((node) => node.dataset.editLayer === 'text') || generatedMembers[0]);
        await nextFrame();
      }
      const generatedGrouped = frameState();
      generatedGrouped.expectedCount = 0;
      generatedGrouped.pass = generatedGrouped.mode === 'group'
        && generatedGrouped.visibleCount === 0
        && generatedGrouped.reportedCount === 0;

      window.EditMode.ungroup();
      await nextFrame();
      const generatedUngrouped = frameState();
      generatedUngrouped.expectedCount = generatedMembers.length;
      generatedUngrouped.pass = generatedUngrouped.mode === 'multi'
        && generatedUngrouped.visibleCount === generatedUngrouped.expectedCount
        && generatedUngrouped.reportedCount === generatedUngrouped.expectedCount;

      window.EditMode.group();
      await nextFrame();
      const generatedRegrouped = frameState();
      generatedRegrouped.expectedCount = 0;
      generatedRegrouped.pass = generatedRegrouped.mode === 'group'
        && generatedRegrouped.visibleCount === 0
        && generatedRegrouped.reportedCount === 0;

      let peer = generatedParent
        ? [...generatedParent.querySelectorAll(':scope > .el')].find((node) => visible(node) && node !== generatedRoot)
        : null;
      if (generatedParent && peer) {
        click(generatedMembers.find((node) => node.dataset.editLayer === 'text') || generatedMembers[0]);
        await nextFrame();
        document.querySelector('[data-action="edit-group-member"]')?.click();
        await nextFrame();
        click(generatedMembers.find((node) => node.dataset.editLayer === 'text') || generatedMembers[0]);
        await nextFrame();
      }
      if (!peer) {
        peer = [...active.querySelectorAll('.content .el')].find((node) => (
          visible(node) && node !== generatedRoot && !generatedRoot.contains(node)
        ));
      }
      if (!peer) {
        return {
          targetFound: true,
          generatedGrouped,
          generatedUngrouped,
          generatedRegrouped,
          manualTargetFound: false,
          pass: false,
        };
      }
      click(peer, true);
      await nextFrame();
      window.EditMode.group();
      await nextFrame();
      const manualGrouped = frameState();
      manualGrouped.expectedCount = 0;
      manualGrouped.pass = manualGrouped.mode === 'group'
        && manualGrouped.visibleCount === 0
        && manualGrouped.reportedCount === 0;

      window.EditMode.ungroup();
      await nextFrame();
      const manualUngrouped = frameState();
      manualUngrouped.expectedCount = 2;
      manualUngrouped.pass = manualUngrouped.mode === 'multi'
        && manualUngrouped.visibleCount === manualUngrouped.expectedCount
        && manualUngrouped.reportedCount === manualUngrouped.expectedCount;

      return {
        targetFound: true,
        manualTargetFound: true,
        generatedGrouped,
        generatedUngrouped,
        generatedRegrouped,
        manualGrouped,
        manualUngrouped,
        pass: generatedGrouped.pass
          && generatedUngrouped.pass
          && generatedRegrouped.pass
          && manualGrouped.pass
          && manualUngrouped.pass,
      };
    });

    if (options.screenshot) {
      const screenshotPath = path.resolve(options.screenshot);
      await fs.mkdir(path.dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path: screenshotPath, fullPage: true });
    }
    const reportPath = path.resolve(options.report);
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(result, null, 2) + '\n', 'utf8');
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }
}

main()
  .then(() => process.exit(process.exitCode || 0))
  .catch((error) => { console.error(error); process.exit(1); });
