export const PPTX_STAGE_TO_ARTIFACT_SCALE = 2 / 3;
export const DEFAULT_PPTX_CORNER_RADIUS_STAGE_PX = 18;

function finiteNonNegative(value, label) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) {
    throw new Error(`${label} must be a finite non-negative number`);
  }
  return number;
}

export function resolvePptxRoundRectRadius(position, radiusStagePx = DEFAULT_PPTX_CORNER_RADIUS_STAGE_PX) {
  const width = finiteNonNegative(position?.width, "position.width");
  const height = finiteNonNegative(position?.height, "position.height");
  const requestedStagePx = finiteNonNegative(radiusStagePx, "corner_radius_stage_px");
  const shortSide = Math.min(width, height);
  if (shortSide <= 0) throw new Error("roundRect requires positive width and height");

  const requestedArtifactPx = requestedStagePx * PPTX_STAGE_TO_ARTIFACT_SCALE;
  const effectiveArtifactPx = Math.min(requestedArtifactPx, shortSide / 2);
  const adjustment = Math.max(0, Math.min(50000, Math.round((effectiveArtifactPx / shortSide) * 100000)));
  return {
    requested_stage_px: requestedStagePx,
    requested_artifact_px: requestedArtifactPx,
    effective_artifact_px: effectiveArtifactPx,
    adjustment,
    formula: `val ${adjustment}`,
  };
}
