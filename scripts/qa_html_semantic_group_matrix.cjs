const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");
const { selectAllBySelector } = require("./html_qa_selection.cjs");
const { chromium } = loadPlaywright();

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--url") out.url = argv[++i];
    else if (argv[i] === "--report") out.report = argv[++i];
    else if (argv[i] === "--screenshots") out.screenshots = argv[++i];
    else if (argv[i] === "--single-layer-only") out.singleLayerOnly = true;
    else if (argv[i] === "--profile") out.profile = argv[++i];
    else if (argv[i] === "--profile-file") out.profileFile = argv[++i];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
}
const CASES = [
  { name:"index", slide:2, selector:".index-item" },
  { name:"columns", slide:3, selector:".column-item" },
  { name:"map", slide:4, selector:".map-node" },
  { name:"metrics", slide:5, selector:".metric-item" },
  { name:"timeline", slide:7, selector:".timeline-item" },
  { name:"ledger", slide:8, selector:".ledger-row:not(.ledger-header)" },
];
const CASE_PROFILES = {
  default: {
    cases:CASES, metricsSlide:5, metricsSelector:'.metric-item', moderateDrag:44,
    singleLayer:{ slide:2, moduleSelector:'.index-item', index:2, labelSelector:'.index-label', backgroundSelector:'.index-item-bg' },
    visualCase:{ slide:1, visualSelector:'.thesis-mark', textSelector:'.thesis-quote', hidden:true }
  },
  'signal-route-atlas': {
    cases:[
      { name:'index', slide:1, selector:'.index-item' },
      { name:'columns', slide:2, selector:'.column-item' },
      { name:'map', slide:7, selector:'.map-node' },
      { name:'metrics', slide:10, selector:'.metric-item' },
      { name:'timeline', slide:9, selector:'.timeline-item' },
      { name:'ledger', slide:8, selector:'.ledger-row:not(.ledger-header)' },
    ],
    metricsSlide:10, metricsSelector:'.metric-item', moderateDrag:16,
    singleLayer:{ slide:1, moduleSelector:'.index-item', index:2, labelSelector:'.index-label', backgroundSelector:'.index-item-bg' },
    visualCase:{ slide:4, visualSelector:'.flow-line', textSelector:'.flow-title', hidden:false }
  }
};
function validateProfile(profile, label) {
  if (!profile || !Array.isArray(profile.cases) || profile.cases.length < 2) {
    throw new Error(`Profile ${label} must define at least two cases`);
  }
  for (const testCase of profile.cases) {
    if (!testCase.name || !Number.isInteger(testCase.slide) || !testCase.selector) {
      throw new Error(`Profile ${label} has an invalid case`);
    }
  }
  if (!Number.isInteger(profile.metricsSlide) || !profile.metricsSelector) {
    throw new Error(`Profile ${label} must define metricsSlide and metricsSelector`);
  }
  const single = profile.singleLayer;
  if (!single || !Number.isInteger(single.slide) || !single.moduleSelector || !Number.isInteger(single.index) || !single.labelSelector || !single.backgroundSelector) {
    throw new Error(`Profile ${label} must define a complete singleLayer fixture`);
  }
  const visual = profile.visualCase;
  if (!visual || !Number.isInteger(visual.slide) || !visual.visualSelector || !visual.textSelector) {
    throw new Error(`Profile ${label} must define visualCase`);
  }
  if (!Number.isFinite(profile.moderateDrag)) profile.moderateDrag = 44;
  return profile;
}
function caseProfile(options) {
  if (options._resolvedProfile) return options._resolvedProfile;
  let label;
  let profile;
  if (options.profileFile) {
    const profilePath = path.resolve(options.profileFile);
    profile = JSON.parse(fsSync.readFileSync(profilePath, "utf8"));
    label = path.relative(process.cwd(), profilePath).split(path.sep).join('/');
  } else {
    label = options.profile || "default";
    profile = CASE_PROFILES[label];
    if (!profile) {
      throw new Error(`Unknown profile ${label}. Available: ${Object.keys(CASE_PROFILES).join(", ")}; or use --profile-file`);
    }
  }
  options._profileName = label;
  options._resolvedProfile = validateProfile(profile, label);
  return options._resolvedProfile;
}
const near = (a,b,t=3) => Math.abs(a-b) <= t;
async function ready(page, url, slide) {
  await page.addInitScript(() => localStorage.clear());
  await page.route("https://fonts.googleapis.com/**", r => r.abort());
  await page.route("https://fonts.gstatic.com/**", r => r.abort());
  await page.goto(url, { waitUntil:"domcontentloaded", timeout:60000 });
  await page.waitForFunction(() => document.documentElement.dataset.layoutReady === "true" && window.EditMode, null, { timeout:120000 });
  await page.evaluate(async (index) => {
    window.setSlide(index);
    if (!document.documentElement.classList.contains("edit-mode")) window.EditMode.toggle(true);
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  }, slide);
}
async function fireModuleClick(page, selector, index=0) {
  await page.evaluate(({selector,index}) => {
    const el = document.querySelectorAll(`.slide.active ${selector}`)[index];
    if (!el) throw new Error(`module missing: ${selector} ${index}`);
    const r = el.getBoundingClientRect();
    const init = { bubbles:true, button:0, clientX:r.left+r.width*.82, clientY:r.top+r.height*.82 };
    ["mousedown","mouseup","click"].forEach(type => el.dispatchEvent(new MouseEvent(type, init)));
  }, {selector,index});
  await page.waitForTimeout(90);
}
async function selectFormalGroup(page, selector) {
  await selectAllBySelector(page, `.slide.active ${selector}`);
  await page.evaluate(() => window.EditMode.group());
  await page.waitForTimeout(120);
}
async function dragHandle(page, name, dx, dy) {
  const box = await page.locator(`.edit-resize-handle[data-handle="${name}"]`).boundingBox();
  if (!box) throw new Error(`${name} handle missing`);
  const x=box.x+box.width/2, y=box.y+box.height/2;
  await page.mouse.move(x,y); await page.mouse.down();
  await page.mouse.move(x+dx,y+dy,{steps:10}); await page.mouse.up();
  await page.waitForTimeout(150);
}
async function snap(page, selector) {
  return page.evaluate((selector) => {
    const rect = el => { const r=el.getBoundingClientRect(); return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height}; };
    const matrix = el => { const t=getComputedStyle(el).transform; const m=new DOMMatrixReadOnly(t==='none'?undefined:t); return {x:Math.hypot(m.a,m.b),y:Math.hypot(m.c,m.d)}; };
    const members=[...document.querySelectorAll(`.slide.active ${selector}`)].filter(el=>getComputedStyle(el).display!=="none");
    const boxes=members.map(rect);
    const union={left:Math.min(...boxes.map(x=>x.left)),top:Math.min(...boxes.map(x=>x.top)),right:Math.max(...boxes.map(x=>x.right)),bottom:Math.max(...boxes.map(x=>x.bottom))};
    union.width=union.right-union.left; union.height=union.bottom-union.top;
    const frame=document.getElementById('edit-selection-frame');
    return {
      frame:rect(frame), union,
      mode:frame?.dataset.selectionMode||"",
      members:members.map(el=>({rect:rect(el),z:getComputedStyle(el).zIndex,transform:el.style.transform||"",matrix:matrix(el),fonts:[...el.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')].map(n=>parseFloat(getComputedStyle(n).fontSize))})),
    };
  }, selector);
}
async function formalResizeCase(browser, options, testCase) {
  const page=await browser.newPage({viewport:{width:1800,height:1000}});
  try {
    await ready(page, options.url, testCase.slide);
    await selectFormalGroup(page, testCase.selector);
    const before=await snap(page,testCase.selector);
    await dragHandle(page,"e",100,0);
    const east=await snap(page,testCase.selector);
    await page.evaluate(()=>window.EditMode.undo()); await page.waitForTimeout(120);
    const eastUndo=await snap(page,testCase.selector);
    await dragHandle(page,"se",90,60);
    const corner=await snap(page,testCase.selector);
    await page.evaluate(()=>window.EditMode.undo()); await page.waitForTimeout(120);
    const cornerUndo=await snap(page,testCase.selector);
    const selectionMatchesUnion = near(before.frame.left,before.union.left) && near(before.frame.top,before.union.top) && near(before.frame.width,before.union.width) && near(before.frame.height,before.union.height);
    const eastMembers = east.members.every((m,i)=>m.rect.width > before.members[i].rect.width+5 && near(m.rect.height,before.members[i].rect.height,4));
    const glyphsUndistorted = east.members.every((m,i)=>near(m.matrix.x,before.members[i].matrix.x,.02) && near(m.matrix.y,before.members[i].matrix.y,.02) && m.fonts.every((f,j)=>near(f,before.members[i].fonts[j],.2)));
    const eastRestored = eastUndo.members.every((m,i)=>near(m.rect.left,before.members[i].rect.left) && near(m.rect.top,before.members[i].rect.top) && near(m.rect.width,before.members[i].rect.width) && near(m.rect.height,before.members[i].rect.height));
    const sx=corner.frame.width/before.frame.width, sy=corner.frame.height/before.frame.height;
    const cornerProportional = sx>1.025 && sy>1.025 && Math.abs(sx-sy)<.045;
    const cornerRestored = cornerUndo.members.every((m,i)=>near(m.rect.left,before.members[i].rect.left) && near(m.rect.top,before.members[i].rect.top) && near(m.rect.width,before.members[i].rect.width) && near(m.rect.height,before.members[i].rect.height));
    const checks={selectionMatchesFullModuleUnion:selectionMatchesUnion,eastExtendsEveryModule:eastMembers,eastDoesNotDistortGlyphs:glyphsUndistorted,eastUndoRestores:eastRestored,cornerScalesProportionally:cornerProportional,cornerUndoRestores:cornerRestored};
    if(options.screenshots){await fs.mkdir(options.screenshots,{recursive:true});await page.screenshot({path:path.join(options.screenshots,`${testCase.name}-resize.png`),fullPage:true});}
    return {pass:Object.values(checks).every(Boolean),checks,before,east,corner};
  } finally { await page.close(); }
}
async function moveOverlapCase(browser, options, testCase) {
  const page=await browser.newPage({viewport:{width:1800,height:1000}});
  try {
    await ready(page, options.url, testCase.slide);
    await fireModuleClick(page,testCase.selector,0); await fireModuleClick(page,testCase.selector,0);
    const before=await snap(page,testCase.selector);
    const boxes=await page.locator(`.slide.active ${testCase.selector}`).evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.left+r.width*.82,y:r.top+r.height*.82,cx:r.left+r.width/2,cy:r.top+r.height/2};}));
    await page.mouse.move(boxes[0].x,boxes[0].y); await page.mouse.down();
    await page.mouse.move(boxes[1].cx,boxes[1].cy,{steps:12}); await page.mouse.up(); await page.waitForTimeout(160);
    const moved=await snap(page,testCase.selector);
    const paint=await page.evaluate(({selector,x,y})=>[...document.elementsFromPoint(x,y)].map(el=>el.closest?.(selector)).filter(Boolean).map(el=>[...document.querySelectorAll(`.slide.active ${selector}`)].indexOf(el)),{selector:testCase.selector,x:boxes[1].cx,y:boxes[1].cy});
    await page.evaluate(()=>window.EditMode.undo()); await page.waitForTimeout(120); const undone=await snap(page,testCase.selector);
    await page.evaluate(()=>window.EditMode.redo()); await page.waitForTimeout(120); const redone=await snap(page,testCase.selector);
    const z0=parseInt(moved.members[0].z,10)||0,z1=parseInt(moved.members[1].z,10)||0;
    const movedGeometry=!near(moved.members[0].rect.left,before.members[0].rect.left,5)||!near(moved.members[0].rect.top,before.members[0].rect.top,5);
    const undoRestores=near(undone.members[0].rect.left,before.members[0].rect.left)&&near(undone.members[0].rect.top,before.members[0].rect.top)&&String(undone.members[0].z)===String(before.members[0].z);
    const redoReplays=near(redone.members[0].rect.left,moved.members[0].rect.left)&&near(redone.members[0].rect.top,moved.members[0].rect.top)&&String(redone.members[0].z)===String(moved.members[0].z);
    const checks={moduleMovedAsUnit:movedGeometry,movedModulePromoted:z0>z1,movedModulePaintsAboveSibling:paint[0]===0,moveUndoRestoresGeometryAndLayer:undoRestores,moveRedoReplaysGeometryAndLayer:redoReplays};
    return {pass:Object.values(checks).every(Boolean),checks,before,moved,paint};
  } finally { await page.close(); }
}
async function singleLayerDragCase(browser, options) {
  const page=await browser.newPage({viewport:{width:1800,height:1000}});
  const fixture=caseProfile(options).singleLayer;
  const capture=()=>page.evaluate((config)=>{
    const rect=n=>{const r=n.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
    const card=document.querySelectorAll('.slide.active '+config.moduleSelector)[config.index];
    const label=card?.querySelector(config.labelSelector);
    const background=card?.querySelector(config.backgroundSelector);
    const frame=document.getElementById('edit-selection-frame');
    if(!label||!card||!background||!frame)throw new Error('single layer drag fixtures missing');
    const editMember=document.querySelector('[data-action="edit-group-member"]');
    return {label:rect(label),card:rect(card),background:rect(background),frame:rect(frame),labelStyle:label.getAttribute('style')||'',cardStyle:card.getAttribute('style')||'',frameMode:frame.dataset.selectionMode||'',editMemberDisabled:!!editMember?.disabled,editMemberAria:editMember?.getAttribute('aria-disabled')||''};
  },fixture);
  try {
    await ready(page,options.url,fixture.slide);
    await fireModuleClick(page,fixture.moduleSelector,fixture.index);
    const editMember=page.locator('[data-action=edit-group-member]');
    if(await editMember.count()!==1)throw new Error('edit single member control must exist');
    const preAction=await capture();
    await editMember.click();
    await page.waitForTimeout(120);
    const label=page.locator('.slide.active '+fixture.moduleSelector).nth(fixture.index).locator(fixture.labelSelector);
    if(await label.count()!==1)throw new Error('single layer label must be unique');
    await label.evaluate((node)=>{
      const r=node.getBoundingClientRect();
      const init={bubbles:true,button:0,clientX:r.left+r.width/2,clientY:r.top+r.height/2};
      ['mousedown','mouseup','click'].forEach((type)=>node.dispatchEvent(new MouseEvent(type,init)));
    });
    await page.waitForTimeout(120);
    const before=await capture();
    const selectedFrame=await page.locator('#edit-selection-frame').boundingBox();
    if(!selectedFrame)throw new Error('index label 03 selection frame is not visible');
    const x=selectedFrame.x+selectedFrame.width/2,y=selectedFrame.y+selectedFrame.height/2;
    await page.mouse.move(x,y); await page.mouse.down();
    await page.mouse.move(x+54,y+36,{steps:10}); await page.mouse.up(); await page.waitForTimeout(160);
    const moved=await capture();
    await page.evaluate(()=>window.EditMode.undo()); await page.waitForTimeout(120); const undone=await capture();
    await page.evaluate(()=>window.EditMode.redo()); await page.waitForTimeout(120); const redone=await capture();
    const layerMoved=!near(moved.label.left,before.label.left,8)&&!near(moved.label.top,before.label.top,8);
    const parentStayed=near(moved.card.left,before.card.left,1)&&near(moved.card.top,before.card.top,1);
    const backgroundStayed=near(moved.background.left,before.background.left,1)&&near(moved.background.top,before.background.top,1);
    const labelDx=moved.label.left-before.label.left,labelDy=moved.label.top-before.label.top;
    const frameDx=moved.frame.left-before.frame.left,frameDy=moved.frame.top-before.frame.top;
    const frameFollowsLayer=near(frameDx,labelDx,3)&&near(frameDy,labelDy,3)&&near(moved.frame.width,before.frame.width,2)&&near(moved.frame.height,before.frame.height,2)&&moved.frameMode==='single';
    const undoRestoresLayerOnly=near(undone.label.left,before.label.left,2)&&near(undone.label.top,before.label.top,2)&&near(undone.card.left,before.card.left,1)&&near(undone.background.left,before.background.left,1);
    const redoReplaysLayerOnly=near(redone.label.left,moved.label.left,2)&&near(redone.label.top,moved.label.top,2)&&near(redone.card.left,before.card.left,1)&&near(redone.background.left,before.background.left,1);
    const checks={selectedChildLayerMoves:layerMoved,parentModuleStaysFixed:parentStayed,parentBackgroundStaysFixed:backgroundStayed,selectionFrameFollowsChild:frameFollowsLayer,undoRestoresOnlyChild:undoRestoresLayerOnly,redoReplaysOnlyChild:redoReplaysLayerOnly};
    return {pass:Object.values(checks).every(Boolean),checks,preAction,before,moved,undone,redone};
  } finally {await page.close();}
}
async function generatedMetricsCase(browser, options) {
  const page=await browser.newPage({viewport:{width:1800,height:1000}});
  try {
    const profile=caseProfile(options);
    await ready(page,options.url,profile.metricsSlide); await selectFormalGroup(page,profile.metricsSelector);
    const before=await snap(page,profile.metricsSelector); await dragHandle(page,'e',100,0); const east=await snap(page,profile.metricsSelector);
    await page.evaluate(()=>window.EditMode.undo()); await page.waitForTimeout(120); const undone=await snap(page,profile.metricsSelector);
    const checks={generatedGroupFrameUsesModuleUnion:near(before.frame.width,before.union.width)&&near(before.frame.height,before.union.height),generatedSideHandleExtendsModules:east.members.every((m,i)=>m.rect.width>before.members[i].rect.width+5),generatedSideHandleUndistorted:east.members.every((m,i)=>near(m.matrix.x,before.members[i].matrix.x,.02)&&near(m.matrix.y,before.members[i].matrix.y,.02)),generatedUndoRestores:undone.members.every((m,i)=>near(m.rect.width,before.members[i].rect.width)&&near(m.rect.height,before.members[i].rect.height))};
    return {pass:Object.values(checks).every(Boolean),checks,before,east};
  } finally {await page.close();}
}
async function stagedCompressionCase(browser, options, testCase) {
  const page=await browser.newPage({viewport:{width:1800,height:1000}});
  const capture=()=>page.evaluate((selector)=>{
    const rect=n=>{const r=n.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
    const members=[...document.querySelectorAll(`.slide.active ${selector}`)].filter(n=>getComputedStyle(n).display!=='none');
    const boxes=members.map(rect), frame=rect(document.getElementById('edit-selection-frame'));
    const glyphRect=n=>{const layout=rect(n);if(!(n.textContent||'').trim())return layout;const range=document.createRange();range.selectNodeContents(n);const glyph=range.getBoundingClientRect();return glyph.width>.5&&glyph.height>.5?{left:glyph.left,top:glyph.top,right:glyph.right,bottom:glyph.bottom,width:glyph.width,height:glyph.height}:layout;};
    return {frame,members:members.map((el,index)=>{const cs=getComputedStyle(el),root=boxes[index],nodes=[...el.querySelectorAll('[data-edit-layer=text],[data-edit-layer=metric]')].filter(n=>getComputedStyle(n).display!=='none'),rs=nodes.map(glyphRect);let fits=rs.every(r=>r.left>=root.left-.8&&r.right<=root.right+.8&&r.top>=root.top-.8&&r.bottom<=root.bottom+.8);for(let i=0;i<rs.length;i++)for(let j=i+1;j<rs.length;j++){const x=Math.min(rs[i].right,rs[j].right)-Math.max(rs[i].left,rs[j].left),y=Math.min(rs[i].bottom,rs[j].bottom)-Math.max(rs[i].top,rs[j].top);if(x>1&&y>2)fits=false;}return {rect:root,inline:el.getAttribute('style')||'',fonts:nodes.map(n=>parseFloat(getComputedStyle(n).fontSize)),lineHeights:nodes.map(n=>parseFloat(getComputedStyle(n).lineHeight)),textRects:nodes.map((n,i)=>({tag:n.tagName,className:n.className,text:n.textContent.trim(),rect:rs[i]})),spacing:[parseFloat(cs.paddingTop)||0,parseFloat(cs.paddingBottom)||0,parseFloat(cs.rowGap)||0],fits};})};
  },testCase.selector);
  try {
    await ready(page,options.url,testCase.slide); await selectFormalGroup(page,testCase.selector);
    const before=await capture(); await dragHandle(page,'s',0,-Math.min(caseProfile(options).moderateDrag,before.frame.height*.08)); const moderate=await capture();
    await page.evaluate(()=>window.EditMode.undo()); await page.waitForTimeout(120);
    await dragHandle(page,'s',0,-Math.max(140,before.frame.height*.68)); const extreme=await capture();
    await page.evaluate(()=>window.EditMode.undo()); await page.waitForTimeout(120); const undone=await capture();
    const checks={
      moderateCompressionUsesWhitespaceFirst:moderate.members.every((m,i)=>m.fonts.every((f,j)=>near(f,before.members[i].fonts[j],.25)))&&moderate.members.some((m,i)=>m.spacing.some((v,j)=>before.members[i].spacing[j]>1&&v<before.members[i].spacing[j]-.5)),
      extremeCompressionShrinksTypography:extreme.members.every((m,i)=>m.fonts.length&&m.fonts.some((f,j)=>f<before.members[i].fonts[j]-.5)&&m.lineHeights.some((v,j)=>v<before.members[i].lineHeights[j]-.5)),
      extremeCompressionKeepsTextInside:extreme.members.every(m=>m.fits),
      verticalHandleKeepsWidth:near(extreme.frame.width,before.frame.width,4)&&extreme.frame.height<before.frame.height-80,
      undoRestores:undone.members.every((m,i)=>near(m.rect.height,before.members[i].rect.height)&&m.fonts.every((f,j)=>near(f,before.members[i].fonts[j],.25)))
    };
    return {pass:Object.values(checks).every(Boolean),checks,before,moderate,extreme};
  } finally {await page.close();}
}
async function textAndHiddenLayerCase(browser, options) {
  const page=await browser.newPage({viewport:{width:1800,height:1000}});
  try {
    const visualCase=caseProfile(options).visualCase;
    await ready(page,options.url,visualCase.slide);
    const layers=await page.evaluate(({visualSelector,textSelector})=>{
      const visual=document.querySelector('.slide.active '+visualSelector);
      const text=document.querySelector('.slide.active '+textSelector);
      return {visualDisplay:getComputedStyle(visual).display,visualContenteditable:visual.hasAttribute('contenteditable'),visualLayer:visual.dataset.editLayer,textDisplay:getComputedStyle(text).display,textLayer:text.dataset.editLayer};
    },visualCase);
    const checks={visualVisibilityMatchesProfile:visualCase.hidden?layers.visualDisplay==='none':layers.visualDisplay!=='none',visualLayerNeverBecomesTextEditable:layers.visualLayer==='visual'&&!layers.visualContenteditable,textLayerRemainsVisible:layers.textLayer==='text'&&layers.textDisplay!=='none'};
    return {pass:Object.values(checks).every(Boolean),checks,layers};
  } finally {await page.close();}
}
async function main(){
  const options=parseArgs(process.argv); const browser=await chromium.launch({headless:true,executablePath:browserExecutable()});
  const profile=caseProfile(options);
  const report={url:options.url,profile:options._profileName,cases:{}};
  try{
    if(options.singleLayerOnly){
      report.singleLayerDrag=await singleLayerDragCase(browser,options);
      report.pass=report.singleLayerDrag.pass;
    }else{
      for(const c of profile.cases){report.cases[c.name]={resize:await formalResizeCase(browser,options,c),move:await moveOverlapCase(browser,options,c)};}
      report.stagedCompression={index:await stagedCompressionCase(browser,options,profile.cases[0]),columns:await stagedCompressionCase(browser,options,profile.cases[1])};
      report.generatedMetrics=await generatedMetricsCase(browser,options);
      report.textAndHiddenLayers=await textAndHiddenLayerCase(browser,options);
      report.singleLayerDrag=await singleLayerDragCase(browser,options);
      report.pass=Object.values(report.cases).every(c=>c.resize.pass&&c.move.pass)&&Object.values(report.stagedCompression).every(c=>c.pass)&&report.generatedMetrics.pass&&report.textAndHiddenLayers.pass&&report.singleLayerDrag.pass;
    }
  }finally{await browser.close();}
  await fs.mkdir(path.dirname(options.report),{recursive:true}); await fs.writeFile(options.report,JSON.stringify(report,null,2)+"\n","utf8");
  console.log(JSON.stringify({pass:report.pass,cases:Object.fromEntries(Object.entries(report.cases).map(([k,v])=>[k,{resize:v.resize.checks,move:v.move.checks}])),stagedCompression:report.stagedCompression?Object.fromEntries(Object.entries(report.stagedCompression).map(([k,v])=>[k,v.checks])):{},generatedMetrics:report.generatedMetrics?.checks||{},textAndHiddenLayers:report.textAndHiddenLayers?.checks||{},singleLayerDrag:report.singleLayerDrag.checks}));
  if(!report.pass)process.exitCode=1;
}
main().catch(e=>{console.error(e.stack||e);process.exit(1);});
