import assert from "node:assert/strict";
import {
  applyCompositionOffset,
  centeredCompositionOffset,
  materializedLayoutName,
  placeholderIndices,
  stageRegionToArtifact,
  visibleUnion,
} from "./pptx_positioning.mjs";

const rows = [
  { id: "title", placeholder_type: "title" },
  { id: "subtitle", placeholder_type: "subtitle" },
  { id: "body-1", placeholder_type: "body" },
  { id: "body-2", placeholder_type: "body" },
];
assert.deepEqual(placeholderIndices(rows), [0, 1, 2, 3], "Placeholder indices must be globally unique, not restarted per type");
assert.deepEqual(
  placeholderIndices([{ id: "explicit", index: 4 }, { id: "auto-a" }, { id: "auto-b" }]),
  [4, 5, 6],
  "Automatic indices must continue after an explicit index",
);
assert.throws(
  () => placeholderIndices([{ id: "a", index: 2 }, { id: "b", index: 2 }]),
  /Duplicate PPTX Placeholder index 2/,
);

const offset = { dx: 0, dy: 9, basis: "visible-union-center-to-content-area-center" };
assert.deepEqual(applyCompositionOffset([8, 9, 84, 10], offset), [8, 18, 84, 10]);
assert.deepEqual(
  stageRegionToArtifact([8, 9, 84, 10], offset),
  { left: 102.4, top: 129.6, width: 1075.2, height: 72 },
);
assert.equal(
  materializedLayoutName("layout--cards-1-plus-3", offset),
  "layout--cards-1-plus-3--offset-0-9",
);

const regions = [
  [8, 9, 84, 10],
  [8, 20, 84, 7],
  [8, 33, 24, 40],
  [38, 33, 24, 40],
  [68, 33, 24, 40],
];
assert.deepEqual(visibleUnion(regions), [8, 9, 84, 64]);
const centered = centeredCompositionOffset(regions, [8, 10, 84, 80]);
assert.equal(centered.dx, 0);
assert.equal(centered.dy, 9);
assert.equal(centered.original_center_y, 41);
assert.equal(centered.target_center_y, 50);

console.log(JSON.stringify({
  status: "pass",
  unique_placeholder_indices: placeholderIndices(rows),
  approved_extra_offset: { dx: centered.dx, dy: centered.dy },
  centered_visible_union: [8, 18, 84, 64],
}));
