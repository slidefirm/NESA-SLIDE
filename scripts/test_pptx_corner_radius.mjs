import assert from "node:assert/strict";
import {
  DEFAULT_PPTX_CORNER_RADIUS_STAGE_PX,
  resolvePptxRoundRectRadius,
} from "./pptx_corner_radius.mjs";

assert.equal(DEFAULT_PPTX_CORNER_RADIUS_STAGE_PX, 18);

const wideDefault = resolvePptxRoundRectRadius({ width: 650, height: 82 });
const tallDefault = resolvePptxRoundRectRadius({ width: 510, height: 132 });
assert.equal(wideDefault.requested_artifact_px, 12);
assert.equal(tallDefault.requested_artifact_px, 12);
assert.equal(wideDefault.adjustment, 14634);
assert.equal(tallDefault.adjustment, 9091);

const wide32 = resolvePptxRoundRectRadius({ width: 650, height: 82 }, 48);
const tall32 = resolvePptxRoundRectRadius({ width: 510, height: 132 }, 48);
assert.equal(wide32.effective_artifact_px, 32);
assert.equal(tall32.effective_artifact_px, 32);
assert.equal(wide32.adjustment, 39024);
assert.equal(tall32.adjustment, 24242);

const clamped = resolvePptxRoundRectRadius({ width: 40, height: 20 }, 48);
assert.equal(clamped.effective_artifact_px, 10);
assert.equal(clamped.adjustment, 50000);

assert.throws(() => resolvePptxRoundRectRadius({ width: 100, height: 20 }, -1), /non-negative/);
assert.throws(() => resolvePptxRoundRectRadius({ width: 0, height: 20 }, 18), /positive width and height/);

console.log("PPTX corner radius tests passed");
