export const PPTX_CANONICAL_STAGE = Object.freeze({ width: 1920, height: 1080 });
export const PPTX_ARTIFACT_STAGE = Object.freeze({ width: 1280, height: 720 });

function finite(value, label) {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`${label} must be finite`);
  return number;
}

export function normalizeCompositionOffset(value = null) {
  const source = value && typeof value === "object" ? value : {};
  return {
    dx: finite(source.dx ?? 0, "composition_offset_percent.dx"),
    dy: finite(source.dy ?? 0, "composition_offset_percent.dy"),
    basis: source.basis || "none",
    ...(Array.isArray(source.original_vertical_union) ? { original_vertical_union: source.original_vertical_union.map(Number) } : {}),
    ...(source.original_center_y != null ? { original_center_y: Number(source.original_center_y) } : {}),
    ...(source.target_center_y != null ? { target_center_y: Number(source.target_center_y) } : {}),
  };
}

export function resolveCompositionOffset(spec = null) {
  return normalizeCompositionOffset(
    spec?._selection?.composition_offset_percent
    ?? spec?.pptx?.composition_offset_percent
    ?? spec?.composition_offset_percent,
  );
}

export function applyCompositionOffset(region, offset = null) {
  if (!Array.isArray(region) || region.length !== 4) throw new Error("PPTX region must contain [x, y, width, height]");
  const [x, y, width, height] = region.map((value, index) => finite(value, `region[${index}]`));
  const resolved = normalizeCompositionOffset(offset);
  return [x + resolved.dx, y + resolved.dy, width, height];
}

export function stageRegionToArtifact(region, offset = null) {
  const [x, y, width, height] = applyCompositionOffset(region, offset);
  return {
    left: x * (PPTX_ARTIFACT_STAGE.width / 100),
    top: y * (PPTX_ARTIFACT_STAGE.height / 100),
    width: width * (PPTX_ARTIFACT_STAGE.width / 100),
    height: height * (PPTX_ARTIFACT_STAGE.height / 100),
  };
}

export function placeholderIndices(rows) {
  const used = new Set();
  let next = 0;
  return rows.map((row, rowIndex) => {
    const explicit = row?.index;
    if (explicit != null) {
      const index = finite(explicit, `placeholder_schema[${rowIndex}].index`);
      if (!Number.isInteger(index) || index < 0) throw new Error(`placeholder_schema[${rowIndex}].index must be a non-negative integer`);
      if (used.has(index)) throw new Error(`Duplicate PPTX Placeholder index ${index}`);
      used.add(index);
      next = Math.max(next, index + 1);
      return index;
    }
    while (used.has(next)) next += 1;
    const index = next;
    used.add(index);
    next += 1;
    return index;
  });
}

export function visibleUnion(regions) {
  if (!Array.isArray(regions) || regions.length === 0) throw new Error("visibleUnion requires at least one region");
  const normalized = regions.map((region) => applyCompositionOffset(region));
  const left = Math.min(...normalized.map((region) => region[0]));
  const top = Math.min(...normalized.map((region) => region[1]));
  const right = Math.max(...normalized.map((region) => region[0] + region[2]));
  const bottom = Math.max(...normalized.map((region) => region[1] + region[3]));
  return [left, top, right - left, bottom - top];
}

export function centeredCompositionOffset(regions, targetRegion = [0, 0, 100, 100]) {
  const union = visibleUnion(regions);
  const target = applyCompositionOffset(targetRegion);
  const unionCenterX = union[0] + union[2] / 2;
  const unionCenterY = union[1] + union[3] / 2;
  const targetCenterX = target[0] + target[2] / 2;
  const targetCenterY = target[1] + target[3] / 2;
  return {
    dx: targetCenterX - unionCenterX,
    dy: targetCenterY - unionCenterY,
    basis: "visible-union-center-to-target-region-center",
    original_horizontal_union: [union[0], union[0] + union[2]],
    original_vertical_union: [union[1], union[1] + union[3]],
    original_center_x: unionCenterX,
    original_center_y: unionCenterY,
    target_center_x: targetCenterX,
    target_center_y: targetCenterY,
  };
}

export function materializedLayoutName(baseName, offset = null) {
  const resolved = normalizeCompositionOffset(offset);
  if (Math.abs(resolved.dx) < 1e-9 && Math.abs(resolved.dy) < 1e-9) return baseName;
  const encode = (value) => String(value).replace(/-/g, "m").replace(/\./g, "p");
  return `${baseName}--offset-${encode(resolved.dx)}-${encode(resolved.dy)}`;
}
