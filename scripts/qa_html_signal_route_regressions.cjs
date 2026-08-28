const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--url") out.url = argv[++i];
    else if (argv[i] === "--report") out.report = argv[++i];
    else if (argv[i] === "--screenshots") out.screenshots = argv[++i];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
}
function browserExecutable() {
  return [process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean).find(fsSync.existsSync);
}
function overlaps(a, b, tolerance = 1) {
  return Math.min(a.right, b.right) - Math.max(a.left, b.left) > tolerance
    && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > tolerance;
}
async function ready(page, url) {
  await page.addInitScript(() => localStorage.clear());
  await page.route("https://fonts.googleapis.com/**", route => route.abort());
  await page.route("https://fonts.gstatic.com/**", route => route.abort());
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => document.documentElement.dataset.layoutReady === "true" && window.EditMode, null, { timeout: 120000 });
  await page.evaluate(() => {
    if (document.documentElement.classList.contains("edit-mode")) window.EditMode.toggle(false);
  });
  return { httpStatus:response.status() };
}
async function showSlide(page, index) {
  await page.evaluate(async slideIndex => {
    window.setSlide(slideIndex);
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, index);
}
async function capture(page, dir, name) {
  if (!dir) return;
  await fs.mkdir(dir, { recursive: true });
  await page.locator(".slide.active").screenshot({ path: path.join(dir, name + ".png") });
}
async function matrixCase(page, screenshots) {
  await showSlide(page, 5);
  const result = await page.evaluate(() => {
    const rect = node => { const r = node.getBoundingClientRect(); return { left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height }; };
    const glyphRect = node => { const range=document.createRange(); range.selectNodeContents(node); const r=range.getBoundingClientRect(); return { left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height }; };
    const labels = [...document.querySelectorAll(".slide.active .axis-label")].map(node => ({ className:node.className, text:node.textContent.trim(), rect:glyphRect(node) }));
    const items = [...document.querySelectorAll(".slide.active .matrix-item")].map(rect);
    const frame = rect(document.querySelector(".slide.active .matrix-frame"));
    return { labels, items, frame };
  });
  const labelPairsClear = result.labels.every((label,index) => result.labels.every((other,otherIndex) => index === otherIndex || !overlaps(label.rect, other.rect)));
  const labelsClearItems = result.labels.every(label => result.items.every(item => !overlaps(label.rect, item)));
  const checks = {
    fourIndependentAxisLabels: result.labels.length === 4 && new Set(result.labels.map(label => label.text)).size === 4,
    axisLabelsDoNotOverlapEachOther: labelPairsClear,
    axisLabelsDoNotOverlapQuadrants: labelsClearItems,
  };
  await capture(page, screenshots, "slide-06-matrix");
  return { pass:Object.values(checks).every(Boolean), checks, geometry:result };
}
async function dispatchCase(page, screenshots) {
  await showSlide(page, 6);
  const result = await page.evaluate(() => {
    const rect = node => { const r=node.getBoundingClientRect(); return { left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height }; };
    const glyphRect = node => { const range=document.createRange(); range.selectNodeContents(node); const r=range.getBoundingClientRect(); return { left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height }; };
    return [...document.querySelectorAll(".slide.active .column-item")].map(item => {
      const tag=item.querySelector(".column-tag"), title=item.querySelector(".column-title"), background=item.querySelector(".column-item-bg");
      const itemRect=rect(item), tagRect=rect(tag), titleRect=glyphRect(title), glyph=glyphRect(tag), border=parseFloat(getComputedStyle(background).borderLeftWidth)||0;
      const scale=itemRect.width/item.offsetWidth, paintedBorder=border*scale;
      return { text:tag.textContent.trim(), item:itemRect, tag:tagRect, title:titleRect, glyph, border, paintedBorder, tagClearance:glyph.left-(itemRect.left+paintedBorder), clipped:glyph.left<itemRect.left-1||glyph.right>titleRect.left-8||glyph.top<itemRect.top-1||glyph.bottom>itemRect.bottom+1 };
    });
  });
  const checks = {
    allTagsInsideModules: result.every(row => row.tag.left>=row.item.left-1&&row.tag.right<=row.item.right+1&&row.tag.top>=row.item.top-1&&row.tag.bottom<=row.item.bottom+1),
    paintedOrnamentsReserveContentInset: result.every(row => row.tagClearance>=20),
    longTagIsNotClipped: result[0]?.text === "01 / COMPREHENSION" && !result[0].clipped,
  };
  await capture(page, screenshots, "slide-07-dispatch");
  return { pass:Object.values(checks).every(Boolean), checks, geometry:result };
}
async function healthCase(page, screenshots) {
  await showSlide(page, 10);
  const result = await page.evaluate(() => {
    const rect = node => { const r=node.getBoundingClientRect(); return { left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height }; };
    const grid=rect(document.querySelector(".slide.active .metric-grid"));
    const items=[...document.querySelectorAll(".slide.active .metric-item")].map(item => {
      const itemRect=rect(item), textRects=[...item.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')].map(rect);
      const union={left:Math.min(...textRects.map(r=>r.left)),top:Math.min(...textRects.map(r=>r.top)),right:Math.max(...textRects.map(r=>r.right)),bottom:Math.max(...textRects.map(r=>r.bottom))};
      union.width=union.right-union.left; union.height=union.bottom-union.top;
      return { item:itemRect, textUnion:union, verticalFill:union.height/itemRect.height, centeredOffset:Math.abs((union.top+union.bottom)/2-(itemRect.top+itemRect.bottom)/2) };
    });
    return { grid, items };
  });
  const checks = {
    healthBoardIsCompact: result.grid.height<=520,
    contentUsesCardHeight: result.items.every(row=>row.verticalFill>=0.42),
    contentGroupsAreVerticallyCentered: result.items.every(row=>row.centeredOffset<=row.item.height*0.16),
  };
  await capture(page, screenshots, "slide-11-health");
  return { pass:Object.values(checks).every(Boolean), checks, geometry:result };
}
async function main() {
  const options=parseArgs(process.argv), browser=await chromium.launch({headless:true,executablePath:browserExecutable()}), report={url:options.url,cases:{}};
  try {
    const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
    const consoleErrors=[];
    page.on("console",message=>{const text=message.text();if(message.type()==="error"&&!/Failed to load resource: net::ERR_FAILED/.test(text))consoleErrors.push(text)});
    const navigation=await ready(page,options.url);
    report.meta=await page.evaluate(()=>({themeId:document.documentElement.dataset.themeId,assembly:document.documentElement.dataset.htmlAssembly,revision:document.documentElement.dataset.deckRevision,slides:document.querySelectorAll("#stage>.slide").length,editor:!!window.EditMode,layoutReady:document.documentElement.dataset.layoutReady}));
    report.meta.httpStatus=navigation.httpStatus;
    report.meta.consoleErrors=consoleErrors;
    report.cases.matrix=await matrixCase(page,options.screenshots);
    report.cases.dispatch=await dispatchCase(page,options.screenshots);
    report.cases.health=await healthCase(page,options.screenshots);
    report.pass=Object.values(report.cases).every(test=>test.pass)&&report.meta.httpStatus===200&&report.meta.themeId==="signal-route-atlas"&&report.meta.slides===12&&report.meta.editor&&report.meta.layoutReady==="true"&&report.meta.consoleErrors.length===0;
    await page.close();
  } finally { await browser.close(); }
  await fs.mkdir(path.dirname(options.report),{recursive:true}); await fs.writeFile(options.report,JSON.stringify(report,null,2)+"\n","utf8");
  console.log(JSON.stringify({pass:report.pass,cases:Object.fromEntries(Object.entries(report.cases).map(([key,value])=>[key,value.checks]))}));
  if(!report.pass)process.exitCode=1;
}
main().catch(error=>{console.error(error.stack||error);process.exit(1);});
