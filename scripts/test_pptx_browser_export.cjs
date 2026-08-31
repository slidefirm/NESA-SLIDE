const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const sourcePath = path.resolve(__dirname, "..", "artifacts", "html-test", "pptx-browser-export.js");
const source = fs.readFileSync(sourcePath, "utf8");

class FakeSlide {
  constructor() {
    this.objects = [];
    this.background = null;
  }

  addShape(type, options) {
    this.objects.push({ type, options });
  }

  addText(text, options) {
    this.objects.push({ type: "text", text, options });
  }

  addImage(options) {
    this.objects.push({ type: "image", options });
  }
}

class FakePptx {
  constructor() {
    this.ShapeType = {
      ellipse: "ellipse",
      roundRect: "roundRect",
      rect: "rect",
      line: "line",
    };
    this.masters = [];
    this.slides = [];
  }

  defineSlideMaster(options) {
    this.masters.push(options);
  }

  addSlide() {
    const slide = new FakeSlide();
    this.slides.push(slide);
    return slide;
  }
}

const windowObject = { PptxGenJS: FakePptx };
vm.runInNewContext(source, { window: windowObject }, { filename: sourcePath });

function buildElement(overrides = {}) {
  return {
    kind: "shape",
    name: "rounded-surface",
    role: "background",
    shape: "roundRect",
    borderRadius: 72,
    position: { left: 100, top: 120, width: 800, height: 400, rotation: 0 },
    fill: "#F9F7F0",
    lineColor: "#D45A2F",
    lineWidth: 4,
    borders: {
      top: { width: 4, color: "#D45A2F" },
      right: { width: 1, color: "#1C7777" },
      bottom: { width: 1, color: "#1C7777" },
      left: { width: 1, color: "#1C7777" },
    },
    ...overrides,
  };
}

function build(elements) {
  return windowObject.PptxBrowserExport.buildPresentation({
    title: "border regression",
    canvas: { width: 1920, height: 1080 },
    slides: [{ backgroundColor: "#FFFFFF", elements }],
  }).pptx.slides[0].objects;
}

const roundedObjects = build([buildElement()]);
const roundedShape = roundedObjects.find((object) => object.type === "roundRect");
const roundedEdgeLines = roundedObjects.filter((object) => object.type === "line");
assert.ok(roundedShape, "rounded Surface should remain a native roundRect");
assert.equal(roundedEdgeLines.length, 1, "only the differing accent edge should be emitted");
assert.ok(roundedEdgeLines[0].options.x > 100 / 1920 * 13.333333, "accent edge should be inset from the rounded corner");
assert.ok(roundedEdgeLines[0].options.w < 800 / 1920 * 13.333333, "accent edge should not span the rectangular bounds");
assert.equal(roundedShape.options.line.color, "1C7777", "shared side border should use the rounded base outline");

const topOnlyObjects = build([buildElement({
  borders: {
    top: { width: 4, color: "#D45A2F" },
    right: { width: 0, color: "#000000" },
    bottom: { width: 0, color: "#000000" },
    left: { width: 0, color: "#000000" },
  },
})]);
assert.equal(topOnlyObjects.filter((object) => object.type === "line").length, 1, "top-only rounded border should not create side lines");

const partialObjects = build([buildElement({
  borders: {
    top: { width: 1, color: "#1C7777" },
    right: { width: 0, color: "#000000" },
    bottom: { width: 1, color: "#1C7777" },
    left: { width: 0, color: "#000000" },
  },
})]);
assert.equal(partialObjects.filter((object) => object.type === "roundRect")[0].options.line.type, "none", "partial rounded borders must not synthesize a full outline");
assert.equal(partialObjects.filter((object) => object.type === "line").length, 2, "partial rounded borders should preserve only their declared edges");

const ellipseObjects = build([buildElement({
  shape: "ellipse",
  borderRadius: 200,
})]);
assert.equal(ellipseObjects.filter((object) => object.type === "line").length, 0, "elliptical borders must not be emitted as rectangular edge lines");
assert.equal(ellipseObjects.find((object) => object.type === "ellipse").options.line.color, "1C7777", "ellipses should retain their shared native outline");

const rectangularObjects = build([buildElement({
  shape: "rect",
  borderRadius: 0,
})]);
assert.equal(rectangularObjects.filter((object) => object.type === "line").length, 4, "rectangular asymmetric borders should keep all four edges");

process.stdout.write("PPTX browser export rounded-border regression passed.\n");
