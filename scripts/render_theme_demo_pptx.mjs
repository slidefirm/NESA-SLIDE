import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

function argsOf(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) out[argv[i].replace(/^--/, "").replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = argv[i + 1];
  if (!out.matrix || !out.demo || !out.output) throw new Error("--matrix, --demo and --output are required");
  return out;
}

const C = { bg: "1A1A1A", gold: "D4AF7E", teal: "4A8B8B", orange: "FF6633", surface: "302C26", text: "F0EDE5", muted: "B7B1A7", ink: "171717" };
const FONT = "Noto Sans TC";
const SERIF = "Noto Serif TC";

function region(layout, id) {
  const slot = layout.slots.find((row) => row.id === id);
  if (!slot) throw new Error(`Missing slot ${layout.id}.${id}`);
  const [x, y, w, h] = slot.region;
  return { left: x * 12.8, top: y * 7.2, width: w * 12.8, height: h * 7.2 };
}

function addShape(slide, geometry, position, fill = "none", lineFill = "none", lineWidth = 0, name = "shape") {
  return slide.shapes.add({ geometry, name, position, fill, line: { style: "solid", fill: lineFill, width: lineWidth } });
}

function addText(slide, text, position, options = {}) {
  const shape = addShape(slide, "textbox", position, options.fill || "none", options.lineFill || "none", options.lineWidth || 0, options.name || "text");
  shape.text = text;
  shape.text.style = {
    fontSize: options.fontSize || 24,
    color: options.color || C.text,
    bold: options.bold || false,
    alignment: options.alignment || "left",
    verticalAlignment: options.verticalAlignment || "middle",
    typeface: options.typeface || FONT,
  };
  return shape;
}

function addLine(slide, x, y, width, height, color = C.gold, weight = 1, name = "line") {
  return addShape(slide, "line", { left: x, top: y, width, height }, "none", color, weight, name);
}

function addRotatedBar(slide, x1, y1, x2, y2, color, weight = 5) {
  const dx = x2 - x1; const dy = y2 - y1; const length = Math.hypot(dx, dy);
  const bar = addShape(slide, "rect", { left: (x1 + x2) / 2 - length / 2, top: (y1 + y2) / 2 - weight / 2, width: length, height: weight }, color, "none", 0, "chart-segment");
  bar.rotation = Math.atan2(dy, dx) * 180 / Math.PI;
  return bar;
}

function addChrome(slide, index, layoutId) {
  addText(slide, "BRAND EDITORIAL · LAYOUT DEMO", { left: 46, top: 25, width: 460, height: 20 }, { fontSize: 10, color: C.gold, bold: true });
  addText(slide, `${String(index + 1).padStart(2, "0")} / ${layoutId.toUpperCase()}`, { left: 770, top: 25, width: 464, height: 20 }, { fontSize: 10, color: C.gold, bold: true, alignment: "right" });
  addLine(slide, 46, 50, 1188, 0, C.gold, 0.7);
  const slash1 = addShape(slide, "rect", { left: 26, top: -18, width: 3, height: 78 }, C.gold); slash1.rotation = 45;
  const slash2 = addShape(slide, "rect", { left: 43, top: -28, width: 3, height: 78 }, C.gold); slash2.rotation = 45;
  for (let r = 0; r < 4; r += 1) for (let c = 0; c < 7; c += 1) addShape(slide, "ellipse", { left: 1150 + c * 13, top: 650 + r * 13, width: 3, height: 3 }, C.gold);
}

function addTitle(slide, spec, layout) {
  addText(slide, spec.title, region(layout, "title"), { fontSize: 46, bold: true, verticalAlignment: "top" });
  addText(slide, spec.subtitle || "", region(layout, "subtitle"), { fontSize: 26, color: C.muted, typeface: SERIF, verticalAlignment: "top" });
}

function addCard(slide, item, box, density, alternate = false) {
  addShape(slide, "rect", box, C.surface, "none", 0, `card-${item.no}`);
  addShape(slide, "rect", { left: box.left, top: box.top, width: box.width, height: 4 }, alternate ? C.teal : C.gold);
  const { numberSize, titleSize, bodySize } = density;
  const numberHeight = numberSize + 16; const titleHeight = titleSize + 10; const bodyHeight = Math.max(38, bodySize * 2.8); const tagsHeight = item.tags?.length ? 26 : 0;
  const stackHeight = numberHeight + 10 + titleHeight + 10 + bodyHeight + (tagsHeight ? 14 + tagsHeight : 0);
  const stackTop = box.top + Math.max(14, (box.height - stackHeight) / 2);
  addText(slide, item.no, { left: box.left + 22, top: stackTop, width: 100, height: numberHeight }, { fontSize: numberSize, color: C.orange, bold: true, typeface: "Georgia", verticalAlignment: "top" });
  if (item.metric) addText(slide, item.metric, { left: box.left + box.width - 168, top: box.top + 20, width: 144, height: 42 }, { fontSize: 34, color: C.gold, bold: true, alignment: "right", typeface: "Georgia" });
  const titleTop = stackTop + numberHeight + 10; const bodyTop = titleTop + titleHeight + 10;
  addText(slide, item.title, { left: box.left + 22, top: titleTop, width: box.width - 44, height: titleHeight }, { fontSize: titleSize, bold: true, verticalAlignment: "top" });
  addText(slide, item.body, { left: box.left + 22, top: bodyTop, width: box.width - 44, height: bodyHeight }, { fontSize: bodySize, color: C.muted, typeface: SERIF, verticalAlignment: "top" });
  if (item.tags?.length) addText(slide, item.tags.join("·"), { left: box.left + 22, top: bodyTop + bodyHeight + 14, width: box.width - 44, height: 26 }, { fontSize: 15, color: C.gold, bold: true, verticalAlignment: "middle" });
}

function autoCardLayout(count) {
  const columns = ({ 2: 2, 3: 3, 4: 4, 5: 5, 6: 3, 8: 4 })[count] || Math.min(count, 4);
  const rows = Math.ceil(count / columns); const cardHeight = count === 2 ? 333 : count === 3 ? 320 : count <= 5 ? 280 : 187;
  const gapX = 19; const gapY = 16; const content = { left: 64, top: 64, width: 1152, height: 592 };
  const titleHeight = 56; const subtitleHeight = 34; const titleGap = 12; const cardGap = 18;
  const groupHeight = titleHeight + titleGap + subtitleHeight + cardGap + rows * cardHeight + (rows - 1) * gapY;
  const groupTop = content.top + (content.height - groupHeight) / 2; const cardTop = groupTop + titleHeight + titleGap + subtitleHeight + cardGap;
  const cardWidth = (content.width - (columns - 1) * gapX) / columns;
  const boxes = Array.from({ length: count }, (_, index) => ({ left: content.left + (index % columns) * (cardWidth + gapX), top: cardTop + Math.floor(index / columns) * (cardHeight + gapY), width: cardWidth, height: cardHeight }));
  return { title: { left: content.left, top: groupTop, width: content.width, height: titleHeight }, subtitle: { left: content.left, top: groupTop + titleHeight + titleGap, width: content.width, height: subtitleHeight }, boxes };
}

function addTocCard(slide, item, box, alternate = false) {
  addShape(slide, "rect", box, C.surface, "none", 0, `toc-card-${item.no}`);
  addShape(slide, "rect", { left: box.left, top: box.top, width: box.width, height: 4 }, alternate ? C.teal : C.gold);
  addText(slide, item.no, { left: box.left + 30, top: box.top + 20, width: 80, height: 24 }, { fontSize: 15, color: C.orange, bold: true });
  addText(slide, item.title, { left: box.left + 30, top: box.top + 58, width: box.width - 60, height: 46 }, { fontSize: 30, bold: true, verticalAlignment: "top" });
  addText(slide, item.body, { left: box.left + 30, top: box.top + 112, width: box.width - 86, height: 70 }, { fontSize: 20, color: C.muted, typeface: SERIF, verticalAlignment: "top" });
  addText(slide, item.no, { left: box.left + box.width - 180, top: box.top + box.height - 118, width: 150, height: 98 }, { fontSize: 72, color: "3A332B", bold: true, alignment: "right", typeface: "Georgia" });
}

function renderCover(slide, spec, layout) {
  addText(slide, "SYSTEM", { left: 55, top: 90, width: 1150, height: 170 }, { fontSize: 128, color: "29251F", bold: true, typeface: "Georgia" });
  addShape(slide, "rect", { left: 0, top: 555, width: 794, height: 11 }, C.gold); addShape(slide, "rect", { left: 794, top: 555, width: 104, height: 11 }, C.orange); addShape(slide, "rect", { left: 898, top: 555, width: 382, height: 11 }, C.teal);
  addText(slide, spec.title, region(layout, "title"), { fontSize: 68, bold: true, alignment: "center", verticalAlignment: "middle" });
  addShape(slide, "rect", { left: 584, top: 380, width: 112, height: 5 }, C.gold);
  addText(slide, spec.subtitle, { left: 155, top: 398, width: 970, height: 48 }, { fontSize: 26, color: C.gold, alignment: "center", typeface: SERIF });
  addText(slide, spec.speaker, { left: 390, top: 470, width: 500, height: 28 }, { fontSize: 15, color: C.muted, alignment: "center" }); addText(slide, spec.org, { left: 390, top: 505, width: 500, height: 26 }, { fontSize: 13, color: C.muted, alignment: "center" });
  const seal = addShape(slide, "ellipse", { left: 1100, top: 604, width: 90, height: 90 }, "none", C.gold, 1.5); seal.rotation = -8; addText(slide, "SF\nDEMO", { left: 1106, top: 616, width: 78, height: 62 }, { fontSize: 15, color: C.gold, bold: true, alignment: "center" });
}

function renderToc(slide, spec, layout) {
  const box = region(layout, "panel_left"); addShape(slide, "rect", box, C.gold);
  addText(slide, spec.intro.kicker, { left: box.left + 38, top: box.top + 42, width: box.width - 76, height: 26 }, { fontSize: 14, color: C.ink, bold: true });
  addText(slide, spec.intro.title, { left: box.left + 38, top: box.top + 118, width: box.width - 76, height: 175 }, { fontSize: 46, color: C.ink, bold: true, verticalAlignment: "top" });
  addText(slide, spec.intro.body, { left: box.left + 38, top: box.top + 335, width: box.width - 76, height: 180 }, { fontSize: 20, color: "2B241D", typeface: SERIF, verticalAlignment: "top" });
  addText(slide, spec.intro.stat, { left: box.left + 38, top: box.top + box.height - 64, width: box.width - 76, height: 24 }, { fontSize: 12, color: C.ink, bold: true });
  addText(slide, "04", { left: box.left + box.width - 205, top: box.top + box.height - 148, width: 175, height: 118 }, { fontSize: 88, color: "B28E5F", bold: true, typeface: "Georgia", alignment: "right" });
  spec.items.forEach((item, i) => addTocCard(slide, item, region(layout, `chapter-${i + 1}`), i % 2 === 1));
}

function renderCards(slide, spec, layout) {
  const count = spec.items.length; const fitted = autoCardLayout(count);
  const density = count <= 4 ? { numberSize: 40, titleSize: 34, bodySize: 22 } : count === 5 ? { numberSize: 32, titleSize: 28, bodySize: 19 } : { numberSize: 26, titleSize: 24, bodySize: 17 };
  const titleSize = spec.title.length > 22 ? 44 : 48;
  addText(slide, spec.title, fitted.title, { name: "card-page-title", fontSize: titleSize, bold: true, verticalAlignment: "top" });
  addText(slide, spec.subtitle || "", fitted.subtitle, { name: "card-page-subtitle", fontSize: 26, color: C.muted, typeface: SERIF, verticalAlignment: "top" });
  spec.items.forEach((item, i) => addCard(slide, item, fitted.boxes[i], density, i % 2 === 1));
}

function renderCycle(slide, spec) {
  const items = spec.items || [];
  if (![5, 6].includes(items.length)) throw new Error("cycle renderer requires five or six items");
  const cx = 640;
  const cy = 372;
  const radius = 252;
  const nodeSize = items.length === 6 ? 126 : 138;
  const startAngle = -90;
  addShape(slide, "ellipse", { left: cx - radius, top: cy - radius, width: radius * 2, height: radius * 2 }, "none", C.gold, 1.4, "cycle-ring");
  const hubSize = 270;
  addShape(slide, "ellipse", { left: cx - hubSize / 2, top: cy - hubSize / 2, width: hubSize, height: hubSize }, C.bg, C.gold, 1.2, "cycle-hub");
  addText(slide, "SHARED LOOP", { left: cx - 95, top: cy - 55, width: 190, height: 22 }, { fontSize: 11, color: C.orange, bold: true, alignment: "center", name: "cycle-hub-kicker" });
  addText(slide, spec.title, { left: cx - 105, top: cy - 24, width: 210, height: 48 }, { fontSize: 30, bold: true, alignment: "center", name: "cycle-hub-title" });
  addText(slide, spec.subtitle || "", { left: cx - 105, top: cy + 28, width: 210, height: 54 }, { fontSize: 14, color: C.muted, typeface: SERIF, alignment: "center", name: "cycle-hub-body" });
  items.forEach((item, index) => {
    const angle = (startAngle + index * (360 / items.length)) * Math.PI / 180;
    const x = cx + Math.cos(angle) * radius - nodeSize / 2;
    const y = cy + Math.sin(angle) * radius - nodeSize / 2;
    addShape(slide, "ellipse", { left: x, top: y, width: nodeSize, height: nodeSize }, C.surface, index % 2 === 0 ? C.gold : C.teal, 1.4, `cycle-node-${index + 1}`);
    addText(slide, item.no, { left: x + 18, top: y + 17, width: nodeSize - 36, height: 31 }, { fontSize: 25, color: C.orange, bold: true, typeface: "Georgia", alignment: "center", name: `cycle-node-${index + 1}-number` });
    addText(slide, item.title, { left: x + 13, top: y + 50, width: nodeSize - 26, height: 30 }, { fontSize: 20, bold: true, alignment: "center", name: `cycle-node-${index + 1}-title` });
    addText(slide, item.body, { left: x + 12, top: y + 82, width: nodeSize - 24, height: 31 }, { fontSize: 12, color: C.muted, typeface: SERIF, alignment: "center", name: `cycle-node-${index + 1}-body` });
    const midAngle = (startAngle + (index + 0.5) * (360 / items.length)) * Math.PI / 180;
    const arrowX = cx + Math.cos(midAngle) * radius - 22;
    const arrowY = cy + Math.sin(midAngle) * radius - 18;
    const arrow = addText(slide, "→", { left: arrowX, top: arrowY, width: 44, height: 36 }, { fontSize: 28, color: C.orange, bold: true, alignment: "center", name: `cycle-arrow-${index + 1}` });
    arrow.rotation = startAngle + (index + 0.5) * (360 / items.length) + 90;
  });
}

function renderBeforeAfter(slide, spec, layout) {
  const content = { left: 64, top: 64, width: 1152, height: 592 };
  const states = [spec.before, spec.after];
  const itemCount = Math.max(...states.map((state) => state.items.length));
  const maxTitle = Math.max(...states.map((state) => state.title.length));
  const maxSubtitle = Math.max(...states.map((state) => state.subtitle.length));
  const maxItem = Math.max(...states.flatMap((state) => state.items.map((item) => item.length)));
  const density = itemCount <= 3 && maxTitle <= 8 && maxSubtitle <= 18 && maxItem <= 18
    ? { titleSize: 48, subtitleSize: 25, itemSize: 22, numberSize: 15, headerHeight: 92, subtitleHeight: 42, chartHeight: 150, rowHeight: 70, gap: 18 }
    : itemCount <= 4 && maxTitle <= 12 && maxSubtitle <= 24 && maxItem <= 24
      ? { titleSize: 43, subtitleSize: 22, itemSize: 20, numberSize: 14, headerHeight: 85, subtitleHeight: 38, chartHeight: 130, rowHeight: 62, gap: 16 }
      : { titleSize: 38, subtitleSize: 19, itemSize: 17, numberSize: 13, headerHeight: 76, subtitleHeight: 34, chartHeight: 110, rowHeight: 54, gap: 12 };
  const totalHeight = density.headerHeight + density.subtitleHeight + density.chartHeight + density.rowHeight * itemCount + density.gap * 3;
  const clusterTop = content.top + Math.max(0, (content.height - totalHeight) / 2);
  const subtitleTop = clusterTop + density.headerHeight + density.gap;
  const chartTop = subtitleTop + density.subtitleHeight + density.gap;
  const listTop = chartTop + density.chartHeight + density.gap;
  for (const [key, dim] of [["before", true], ["after", false]]) {
    const data = spec[key]; const source = region(layout, `${key}-header`); const box = { left: source.left, width: source.width };
    addText(slide, data.label, { left: box.left, top: clusterTop, width: box.width, height: 22 }, { fontSize: 15, color: dim ? C.muted : C.gold, bold: true });
    addText(slide, data.title, { left: box.left, top: clusterTop + 26, width: box.width, height: density.headerHeight - 26 }, { fontSize: density.titleSize, color: dim ? C.muted : C.text, bold: true, verticalAlignment: "top" });
    addLine(slide, box.left, clusterTop + density.headerHeight, box.width, 0, C.gold, 0.6);
    addText(slide, data.subtitle, { left: box.left, top: subtitleTop, width: box.width, height: density.subtitleHeight }, { fontSize: density.subtitleSize, color: C.muted, typeface: SERIF, verticalAlignment: "middle" });
    const ratios = dim ? [0.78, 0.38, 0.67, 0.30, 0.52] : [0.22, 0.38, 0.57, 0.75, 0.92];
    const barGap = 18; const barWidth = Math.min(70, (box.width - barGap * 4) / 5); const chartWidth = barWidth * 5 + barGap * 4; const chartLeft = box.left + (box.width - chartWidth) / 2;
    ratios.forEach((ratio, i) => { const h = density.chartHeight * ratio; addShape(slide, "rect", { left: chartLeft + i * (barWidth + barGap), top: chartTop + density.chartHeight - h, width: barWidth, height: h }, dim ? "635B52" : C.gold); });
    addLine(slide, box.left, chartTop + density.chartHeight, box.width, 0, C.gold, 0.6);
    data.items.forEach((item, i) => { const rowTop = listTop + i * density.rowHeight; addText(slide, String(i + 1).padStart(2, "0"), { left: box.left, top: rowTop, width: 48, height: density.rowHeight }, { fontSize: density.numberSize, color: C.orange, bold: true, verticalAlignment: "middle" }); addText(slide, item, { left: box.left + 56, top: rowTop, width: box.width - 56, height: density.rowHeight }, { fontSize: density.itemSize, color: dim ? C.muted : C.text, typeface: SERIF, verticalAlignment: "middle" }); addLine(slide, box.left, rowTop + density.rowHeight, box.width, 0, "5C4B3A", 0.5); });
  }
  const clusterBottom = clusterTop + totalHeight; const railCenter = chartTop + density.chartHeight / 2;
  addLine(slide, 640, clusterTop + 20, 0, totalHeight - 40, C.gold, 0.7); addShape(slide, "ellipse", { left: 610, top: railCenter - 30, width: 60, height: 60 }, C.bg, C.gold, 1); addText(slide, "→", { left: 610, top: railCenter - 30, width: 60, height: 60 }, { fontSize: 28, color: C.gold, alignment: "center" }); addText(slide, "SHIFT", { left: 605, top: railCenter - 62, width: 70, height: 22 }, { fontSize: 11, color: C.gold, bold: true, alignment: "center" }); addText(slide, spec.bridge, { left: 565, top: Math.min(railCenter + 38, clusterBottom - 30), width: 150, height: 30 }, { fontSize: 14, color: C.gold, alignment: "center" });
}

function renderProcess(slide, spec, layout) {
  addTitle(slide, spec, layout); const box = region(layout, "steps"); addLine(slide, box.left + 70, box.top + 82, box.width - 140, 0, C.gold, 2);
  const gap = box.width / spec.steps.length; spec.steps.forEach((item, i) => { const x = box.left + i * gap + 20; addShape(slide, "ellipse", { left: x, top: box.top + 45, width: 62, height: 62 }, C.bg, C.gold, 1.5); addText(slide, item.no, { left: x, top: box.top + 45, width: 62, height: 62 }, { fontSize: 14, color: C.orange, bold: true, alignment: "center" }); addText(slide, item.title, { left: x - 4, top: box.top + 128, width: gap - 28, height: 42 }, { fontSize: 28, bold: true }); addText(slide, item.body, { left: x - 4, top: box.top + 176, width: gap - 28, height: 72 }, { fontSize: 20, color: C.muted, typeface: SERIF, verticalAlignment: "top" }); });
  const note = region(layout, "note"); addShape(slide, "rect", note, "251F1C"); addShape(slide, "rect", { left: note.left, top: note.top, width: 7, height: note.height }, C.orange); addText(slide, spec.note, { left: note.left + 25, top: note.top, width: note.width - 40, height: note.height }, { fontSize: 20, color: C.text, typeface: SERIF });
}

function renderKpi(slide, spec, layout) {
  addTitle(slide, spec, layout); const box = region(layout, "scorecards"); const gap = 18; const w = (box.width - gap * 3) / 4;
  spec.metrics.forEach((item, i) => { const x = box.left + i * (w + gap); addShape(slide, "rect", { left: x, top: box.top, width: w, height: box.height }, C.surface); addShape(slide, "rect", { left: x, top: box.top, width: w, height: 4 }, C.gold); addText(slide, item.label, { left: x + 20, top: box.top + 20, width: w - 40, height: 28 }, { fontSize: 18, color: C.muted }); addText(slide, item.value, { left: x + 20, top: box.top + 58, width: w - 40, height: 90 }, { fontSize: 64, color: C.text, bold: true, typeface: "Georgia" }); addText(slide, item.delta, { left: x + 20, top: box.top + 157, width: w - 40, height: 38 }, { fontSize: 16, color: C.orange, bold: true }); });
  const take = region(layout, "takeaway"); addShape(slide, "rect", take, "251F1C"); addShape(slide, "rect", { left: take.left, top: take.top, width: 8, height: take.height }, C.gold); addText(slide, spec.takeaway, { left: take.left + 28, top: take.top, width: take.width - 50, height: take.height }, { fontSize: 24, typeface: SERIF, bold: true });
}

function renderChart(slide, spec, layout) {
  addText(slide, spec.title, { left: 74, top: 68, width: 1120, height: 62 }, { fontSize: 48, bold: true, verticalAlignment: "top" });
  const box = { left: 218, top: 150, width: 1000, height: 390 };
  [100, 75, 50, 25, 0].forEach((value, i) => { const y = box.top + 34 + i * 75; addLine(slide, box.left, y, box.width, 0, "514739", 0.6); addText(slide, String(value), { left: 152, top: y - 12, width: 48, height: 24 }, { fontSize: 15, color: C.muted, alignment: "right" }); });
  spec.series.forEach((series, si) => {
    const pts = series.values.map((v, i) => ({ x: box.left + 35 + i * ((box.width - 70) / (series.values.length - 1)), y: box.top + box.height - 40 - v * 3.2 }));
    for (let i = 0; i < pts.length - 1; i += 1) addRotatedBar(slide, pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y, si === 0 ? C.gold : C.teal, si === 0 ? 5 : 3);
    pts.forEach((p) => addShape(slide, "ellipse", { left: p.x - 5, top: p.y - 5, width: 10, height: 10 }, C.bg, si === 0 ? C.gold : C.teal, 2));
    if (si === 0) addText(slide, "94%", { left: pts.at(-1).x - 98, top: pts.at(-1).y - 48, width: 96, height: 34 }, { fontSize: 24, color: C.gold, bold: true, alignment: "right" });
  });
  spec.labels.forEach((label, i) => addText(slide, label, { left: box.left + i * (box.width / spec.labels.length), top: 560, width: box.width / spec.labels.length, height: 28 }, { fontSize: 16, color: C.muted, alignment: "center" }));
  addText(slide, `— ${spec.series[0].name}     — ${spec.series[1].name}`, { left: box.left, top: 620, width: 520, height: 30 }, { fontSize: 16, color: C.muted });
  addText(slide, spec.note, { left: 750, top: 620, width: 468, height: 34 }, { fontSize: 13, color: C.muted, alignment: "right" });
}

function renderQuote(slide, spec, layout) {
  addShape(slide, "rect", { left: 150, top: 136, width: 86, height: 6 }, C.orange); addText(slide, spec.quote, region(layout, "quote"), { fontSize: 66, bold: true, typeface: SERIF, verticalAlignment: "middle" }); addText(slide, spec.attribution, region(layout, "attribution"), { fontSize: 16, color: C.gold, bold: true }); addText(slide, "01", { left: 925, top: 130, width: 230, height: 300 }, { fontSize: 190, color: "29251F", bold: true, typeface: "Georgia", alignment: "center" });
}

function renderClosing(slide, spec, layout) {
  addShape(slide, "rect", { left: 0, top: 0, width: 730, height: 720 }, C.gold); addShape(slide, "rect", { left: 730, top: 0, width: 183, height: 720 }, C.surface); addShape(slide, "rect", { left: 913, top: 0, width: 184, height: 720 }, C.teal); addShape(slide, "rect", { left: 1097, top: 0, width: 183, height: 720 }, C.orange); addText(slide, spec.title, region(layout, "closing_title"), { fontSize: 56, color: C.ink, bold: true, verticalAlignment: "top" });
  String(spec.body).split(/\r?\n/).forEach((line, index) => {
    addText(slide, line, { left: 154, top: 350 + index * 36, width: 430, height: 30 }, { fontSize: 22, color: "2B241D", typeface: SERIF, verticalAlignment: "top", name: `closing-body-${index + 1}` });
  });
  addText(slide, spec.contact, region(layout, "social_icons"), { fontSize: 18, color: C.text, bold: true, alignment: "center" });
}

const renderers = { cover: renderCover, toc: renderToc, cards: renderCards, cycle: renderCycle, "before-after": renderBeforeAfter, process: renderProcess, kpi: renderKpi, chart: renderChart, quote: renderQuote, closing: renderClosing };

async function main() {
  const options = argsOf(process.argv); const matrix = JSON.parse(await fs.readFile(options.matrix, "utf8")); const demo = JSON.parse(await fs.readFile(options.demo, "utf8")); const theme = matrix.themes.find((row) => row.id === demo.theme_id); if (!theme) throw new Error(`Unknown theme: ${demo.theme_id}`); const layouts = new Map(matrix.layouts.map((row) => [row.id, row]));
  const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } }); const master = deck.masters.add(`theme--${theme.id}`);
  for (const [index, spec] of demo.slides.entries()) { const layoutSpec = layouts.get(spec.layout_id); if (!layoutSpec) throw new Error(`Unknown layout: ${spec.layout_id}`); const layout = deck.layouts.add(`layout--${spec.layout_id}`); layout.setParentLayoutId(master.id); const slide = deck.slides.add(); slide.setLayout(layout); slide.background.fill = C.bg; if (spec.kind !== "cover" && spec.kind !== "closing") addChrome(slide, index, spec.layout_id); renderers[spec.kind](slide, spec, layoutSpec); }
  await fs.mkdir(path.dirname(path.resolve(options.output)), { recursive: true }); const pptx = await PresentationFile.exportPptx(deck); await pptx.save(path.resolve(options.output)); console.log(JSON.stringify({ theme: theme.id, slides: demo.slides.length, output: path.resolve(options.output) }));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
