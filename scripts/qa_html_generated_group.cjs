const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--editor') out.editor = argv[++index];
    else if (argv[index] === '--report') out.report = argv[++index];
  }
  if (!out.editor || !out.report) throw new Error('--editor and --report are required');
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const editor = fs.readFileSync(path.resolve(options.editor), 'utf8');
  const executablePath = [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean).find((candidate) => fs.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
      *{box-sizing:border-box}body{margin:0;background:#111827;font-family:Arial,sans-serif}
      #bar{position:fixed;left:0;right:0;top:0;height:64px;background:#0b1220;z-index:10}
      #barInner{height:64px;display:flex;align-items:center}
      #canvasBox{position:absolute;left:20px;top:84px;width:1000px;height:650px;overflow:hidden;background:#334155}
      #stage{position:relative;width:1920px;height:1080px;transform:scale(.5);transform-origin:top left;background:#fff}
      .slide{display:none;position:absolute;inset:0;width:1920px;height:1080px;background:#f8fafc}
      .slide.active{display:block}.el,[data-edit-layer]{position:absolute}
      .card{left:180px;top:180px;width:620px;height:360px}
      .card-bg{inset:0;background:#dbeafe;border:4px solid #2563eb}
      .card-title{left:60px;top:90px;font-size:58px;font-weight:700;color:#0f172a}
      .standalone{left:1040px;top:260px;width:360px;height:180px;background:#fed7aa}
    </style></head><body>
      <div id="bar"><div id="barInner"></div></div><div id="hint"></div>
      <div id="canvasBox"><div id="stage"><section class="slide active" id="s1">
        <div class="el card" data-edit-composite="card">
          <div class="card-bg" data-edit-layer="background"></div>
          <div class="card-title" data-edit-layer="text" data-edit-fit="text">AI 預設群組</div>
        </div>
        <div class="el standalone" data-edit-kind="visual"></div>
      </section></div></div>
    </body></html>`, { waitUntil: 'domcontentloaded' });
    await page.addScriptTag({ content: editor });
    await page.waitForFunction(() => Boolean(window.EditMode));

    const title = page.locator('[data-edit-composite] [data-edit-layer="text"]');
    await title.click();
    await page.waitForTimeout(80);
    const firstSelection = await page.evaluate(() => {
      const label = document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || '';
      const frame = document.getElementById('edit-selection-frame');
      const visibleMemberFrames = [...document.querySelectorAll('.edit-selection-member-frame')]
        .filter((node) => getComputedStyle(node).display !== 'none');
      const expectedRects = [...document.querySelectorAll('[data-edit-composite] [data-edit-layer]')].map((node) => {
        if (node.dataset.editFit === 'text') {
          const range = document.createRange();
          range.selectNodeContents(node);
          const rect = range.getBoundingClientRect();
          return { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
        }
        const rect = node.getBoundingClientRect();
        return { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
      });
      const frameRects = visibleMemberFrames.map((node) => {
        const rect = node.getBoundingClientRect();
        return { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
      });
      const memberFramesMatch = expectedRects.every((expected) => frameRects.some((actual) => (
        Math.abs(actual.left - expected.left) <= 2
        && Math.abs(actual.top - expected.top) <= 2
        && Math.abs(actual.width - expected.width) <= 2
        && Math.abs(actual.height - expected.height) <= 2
      )));
      const tools = document.getElementById('edit-group-tools');
      const actionVisible = (name) => {
        const button = tools?.querySelector(`[data-action="${name}"]`);
        return Boolean(button && getComputedStyle(button).display !== 'none');
      };
      return {
        label,
        frameMode: frame?.dataset.selectionMode || '',
        visibleMemberFrames: visibleMemberFrames.length,
        memberFramesMatch,
        groupToolsVisible: Boolean(tools && getComputedStyle(tools).display !== 'none'),
        ungroupVisible: actionVisible('ungroup'),
        editMemberVisible: actionVisible('edit-group-member'),
      };
    });

    const roundTrip = await page.evaluate(() => {
      const root = document.querySelector('[data-edit-composite]');
      const frameState = () => {
        const frame = document.getElementById('edit-selection-frame');
        const visibleMemberFrames = [...document.querySelectorAll('.edit-selection-member-frame')]
          .filter((node) => getComputedStyle(node).display !== 'none').length;
        return {
          mode: frame?.dataset.selectionMode || '',
          visibleMemberFrames,
          reportedMemberFrames: Number(frame?.dataset.memberFrameCount || 0),
          label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || '',
        };
      };
      window.EditMode.ungroup();
      const ungrouped = root.dataset.editGroupState === 'ungrouped';
      const ungroupedSelection = frameState();
      window.EditMode.group();
      const regrouped = !root.dataset.editGroupState;
      const regroupedSelection = frameState();
      window.EditMode.undo();
      const undoRestoredUngrouped = root.dataset.editGroupState === 'ungrouped';
      window.EditMode.redo();
      const redoRestoredGrouped = !root.dataset.editGroupState;
      return {
        ungrouped,
        ungroupedSelection,
        regrouped,
        regroupedSelection,
        undoRestoredUngrouped,
        redoRestoredGrouped,
      };
    });

    await page.mouse.click(930, 650);
    await title.click();
    await page.locator('.standalone').click({ modifiers: ['Shift'] });
    await page.evaluate(() => window.EditMode.group());
    const nested = await page.evaluate(() => {
      const roots = [document.querySelector('[data-edit-composite]'), document.querySelector('.standalone')];
      const paths = roots.map((node) => (node.dataset.editGroup || '').split('>').filter(Boolean));
      const memberFrames = [...document.querySelectorAll('.edit-selection-member-frame')]
        .filter((node) => getComputedStyle(node).display !== 'none');
      const expectedRects = roots.map((node) => node.getBoundingClientRect());
      const memberFramesMatch = expectedRects.every((expected) => memberFrames.some((node) => {
        const actual = node.getBoundingClientRect();
        return Math.abs(actual.left - expected.left) <= 2
          && Math.abs(actual.top - expected.top) <= 2
          && Math.abs(actual.width - expected.width) <= 2
          && Math.abs(actual.height - expected.height) <= 2;
      }));
      const frame = document.getElementById('edit-selection-frame');
      return {
        paths,
        sameOuterGroup: paths.every((item) => item.length === 1) && paths[0][0] === paths[1][0],
        memberFrameCount: memberFrames.length,
        memberFramesMatch,
        selectionMode: frame?.dataset.selectionMode || '',
        reportedMemberFrameCount: Number(frame?.dataset.memberFrameCount || 0),
      };
    });

    const groupAlignment = await page.evaluate(() => {
      const roots = [document.querySelector('[data-edit-composite]'), document.querySelector('.standalone')];
      const logicalBoxes = () => {
        const stage = document.getElementById('stage');
        const stageRect = stage.getBoundingClientRect();
        const scale = stageRect.width / 1920;
        return roots.map((node) => {
          const rect = node.getBoundingClientRect();
          return {
            left: (rect.left - stageRect.left) / scale,
            top: (rect.top - stageRect.top) / scale,
            right: (rect.right - stageRect.left) / scale,
            bottom: (rect.bottom - stageRect.top) / scale,
            width: rect.width / scale,
            height: rect.height / scale,
          };
        });
      };
      const combined = (boxes) => ({
        left: Math.min(...boxes.map((box) => box.left)),
        top: Math.min(...boxes.map((box) => box.top)),
        right: Math.max(...boxes.map((box) => box.right)),
        bottom: Math.max(...boxes.map((box) => box.bottom)),
      });
      const before = logicalBoxes();
      const controls = {
        selectionMode: document.getElementById('edit-selection-frame')?.dataset.selectionMode || '',
        align: [...document.querySelectorAll('[data-align-selection-mode]')].map((button) => ({
          mode: button.dataset.alignSelectionMode,
          disabled: button.disabled,
          title: button.title,
        })),
        distribute: [...document.querySelectorAll('[data-distribute-selection-axis]')].map((button) => ({
          axis: button.dataset.distributeSelectionAxis,
          disabled: button.disabled,
        })),
      };
      document.querySelector('[data-align-selection-mode="centerX"]')?.click();
      const afterCenterX = logicalBoxes();
      document.querySelector('[data-align-selection-mode="middle"]')?.click();
      const afterBoth = logicalBoxes();
      window.EditMode.undo();
      const undoMiddle = logicalBoxes();
      window.EditMode.undo();
      const undoCenterX = logicalBoxes();
      window.EditMode.redo();
      const redoCenterX = logicalBoxes();
      window.EditMode.redo();
      const redoBoth = logicalBoxes();
      return {
        before,
        afterCenterX,
        afterBoth,
        undoMiddle,
        undoCenterX,
        redoCenterX,
        redoBoth,
        combined: {
          before: combined(before),
          afterCenterX: combined(afterCenterX),
          afterBoth: combined(afterBoth),
          undoMiddle: combined(undoMiddle),
          undoCenterX: combined(undoCenterX),
          redoCenterX: combined(redoCenterX),
          redoBoth: combined(redoBoth),
        },
        controls,
      };
    });

    const closeEnough = (actual, expected, tolerance = 0.35) => Math.abs(actual - expected) <= tolerance;
    const sameBoxes = (actual, expected) => actual.every((box, index) => (
      closeEnough(box.left, expected[index].left)
      && closeEnough(box.top, expected[index].top)
      && closeEnough(box.width, expected[index].width)
      && closeEnough(box.height, expected[index].height)
    ));
    const sameRelativeGeometry = (actual, expected) => (
      closeEnough(actual[1].left - actual[0].left, expected[1].left - expected[0].left)
      && closeEnough(actual[1].top - actual[0].top, expected[1].top - expected[0].top)
    );

    const checks = {
      generatedCompositePresentedAsGroup: /^已選取群組\s*·\s*2\s*個物件$/.test(firstSelection.label),
      generatedGroupFrame: firstSelection.frameMode === 'group',
      generatedMemberFramesCollapsed: firstSelection.visibleMemberFrames === 0,
      groupActionsAvailable: firstSelection.groupToolsVisible && firstSelection.editMemberVisible,
      ungroupSelectsAllDirectMembers: roundTrip.ungrouped
        && roundTrip.ungroupedSelection.mode === 'multi'
        && roundTrip.ungroupedSelection.visibleMemberFrames === 2
        && roundTrip.ungroupedSelection.reportedMemberFrames === 2,
      regroupCollapsesToGroupSelection: roundTrip.regrouped
        && roundTrip.regroupedSelection.mode === 'group'
        && roundTrip.regroupedSelection.visibleMemberFrames === 0
        && roundTrip.regroupedSelection.reportedMemberFrames === 0
        && /^已選取群組\s*·\s*2\s*個物件$/.test(roundTrip.regroupedSelection.label),
      undoRedoRoundTrip: roundTrip.undoRestoredUngrouped && roundTrip.redoRestoredGrouped,
      nestedGrouping: nested.sameOuterGroup,
      nestedGroupCollapsed: nested.memberFrameCount === 0
        && nested.reportedMemberFrameCount === 0
        && nested.selectionMode === 'group',
      groupAlignmentUsesSlideReference: groupAlignment.controls.selectionMode === 'group'
        && closeEnough(
          (groupAlignment.combined.afterCenterX.left + groupAlignment.combined.afterCenterX.right) / 2,
          960
        )
        && closeEnough(
          (groupAlignment.combined.afterBoth.top + groupAlignment.combined.afterBoth.bottom) / 2,
          540
        ),
      groupAlignmentPreservesRelativeGeometry: sameRelativeGeometry(
        groupAlignment.afterBoth,
        groupAlignment.before
      ),
      groupAlignmentMovesMembersTogether: closeEnough(
        groupAlignment.afterCenterX[0].left - groupAlignment.before[0].left,
        groupAlignment.afterCenterX[1].left - groupAlignment.before[1].left
      ) && closeEnough(
        groupAlignment.afterBoth[0].top - groupAlignment.afterCenterX[0].top,
        groupAlignment.afterBoth[1].top - groupAlignment.afterCenterX[1].top
      ),
      groupAlignmentPreservesSizes: groupAlignment.afterBoth.every((box, index) => (
        closeEnough(box.width, groupAlignment.before[index].width)
        && closeEnough(box.height, groupAlignment.before[index].height)
      )),
      groupAlignmentControlsUseLogicalSingleMode: groupAlignment.controls.align.length === 6
        && groupAlignment.controls.align.every((button) => !button.disabled)
        && groupAlignment.controls.distribute.length === 2
        && groupAlignment.controls.distribute.every((button) => button.disabled),
      groupAlignmentUndoRedo: sameBoxes(groupAlignment.undoMiddle, groupAlignment.afterCenterX)
        && sameBoxes(groupAlignment.undoCenterX, groupAlignment.before)
        && sameBoxes(groupAlignment.redoCenterX, groupAlignment.afterCenterX)
        && sameBoxes(groupAlignment.redoBoth, groupAlignment.afterBoth),
    };
    const result = { firstSelection, roundTrip, nested, groupAlignment, checks, pass: Object.values(checks).every(Boolean) };
    fs.mkdirSync(path.dirname(path.resolve(options.report)), { recursive: true });
    fs.writeFileSync(path.resolve(options.report), JSON.stringify(result, null, 2) + '\n', 'utf8');
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exit(1); });
