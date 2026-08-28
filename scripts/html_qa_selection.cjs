async function visibleBoxes(page, selector) {
  return page.evaluate((value) => [...document.querySelectorAll(value)]
    .filter((node) => {
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden"
        && rect.width > 0.5 && rect.height > 0.5;
    })
    .map((node) => {
      const rect = node.getBoundingClientRect();
      return {
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height / 2,
      };
    }), selector);
}

async function selectAllBySelector(page, selector) {
  const boxes = await visibleBoxes(page, selector);
  if (!boxes.length) throw new Error(`No selectable objects matched: ${selector}`);

  await page.mouse.click(boxes[0].x, boxes[0].y);
  if (boxes.length > 1) {
    await page.keyboard.down("Shift");
    try {
      for (const box of boxes.slice(1)) {
        await page.mouse.click(box.x, box.y);
      }
    } finally {
      await page.keyboard.up("Shift");
    }
  }
  await page.waitForTimeout(120);

  return page.evaluate(() => {
    const frame = document.getElementById("edit-selection-frame");
    return {
      mode: frame?.dataset?.selectionMode || "",
      memberFrameCount: [...document.querySelectorAll(".edit-selection-member-frame")]
        .filter((node) => getComputedStyle(node).display !== "none").length,
    };
  });
}

module.exports = { selectAllBySelector, visibleBoxes };
