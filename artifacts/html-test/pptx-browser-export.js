(function (root) {
  'use strict';

  const SLIDE_WIDTH_IN = 13.333333;
  const SLIDE_HEIGHT_IN = 7.5;
  const MAX_SLIDES = 200;

  function finite(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? number : (fallback || 0);
  }

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function safeName(value, fallback) {
    const normalized = String(value || '')
      .normalize('NFKC')
      .replace(/[^\p{L}\p{N}_-]+/gu, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80);
    return normalized || fallback;
  }

  function color(value, fallback) {
    const text = String(value || '').trim();
    const match = text.match(/^#?([0-9a-f]{6})([0-9a-f]{2})?$/i);
    if (!match) return { color: String(fallback || '000000').replace(/^#/, '').toUpperCase(), transparency: 0 };
    return {
      color: match[1].toUpperCase(),
      transparency: match[2]
        ? clamp(Math.round((1 - parseInt(match[2], 16) / 255) * 100), 0, 100)
        : 0
    };
  }

  function position(element, canvas) {
    const source = element && element.position ? element.position : {};
    const width = Math.max(1, finite(canvas && canvas.width, 1920));
    const height = Math.max(1, finite(canvas && canvas.height, 1080));
    const rotation = finite(source.rotation, 0);
    return {
      x: clamp(finite(source.left, 0) / width * SLIDE_WIDTH_IN, -SLIDE_WIDTH_IN, SLIDE_WIDTH_IN * 2),
      y: clamp(finite(source.top, 0) / height * SLIDE_HEIGHT_IN, -SLIDE_HEIGHT_IN, SLIDE_HEIGHT_IN * 2),
      w: clamp(finite(source.width, 1) / width * SLIDE_WIDTH_IN, 0.005, SLIDE_WIDTH_IN * 2),
      h: clamp(finite(source.height, 1) / height * SLIDE_HEIGHT_IN, 0.005, SLIDE_HEIGHT_IN * 2),
      ...(Math.abs(rotation) > 0.01 ? { rotate: rotation } : {})
    };
  }

  function fillOptions(value) {
    const parsed = color(value, 'FFFFFF');
    return parsed.transparency >= 100
      ? { type: 'none' }
      : { color: parsed.color, transparency: parsed.transparency };
  }

  function borderLineOptions(side) {
    const parsed = color(side && side.color, 'FFFFFF');
    const width = finite(side && side.width, 0);
    if (width <= 0 || parsed.transparency >= 100) return { type: 'none', transparency: 100, width: 0 };
    return {
      color: parsed.color,
      transparency: parsed.transparency,
      width: Math.max(0.25, width * 0.75)
    };
  }

  function borderSides(element) {
    const borders = element && element.borders;
    if (!borders || typeof borders !== 'object') return null;
    return ['top', 'right', 'bottom', 'left'].map((name) => borderLineOptions(borders[name]));
  }

  function sameBorder(a, b) {
    return a.type === b.type
      && a.color === b.color
      && a.transparency === b.transparency
      && Math.abs(finite(a.width, 0) - finite(b.width, 0)) < 0.001;
  }

  function uniformBorder(element) {
    const sides = borderSides(element);
    if (!sides) return null;
    return sides.every((side) => sameBorder(side, sides[0])) ? sides[0] : null;
  }

  function roundedBorderBase(element) {
    if (!element || finite(element.borderRadius, 0) < 3) return null;
    const sides = borderSides(element);
    if (!sides) return null;
    // Do not turn a partial border (for example top + bottom only) into a
    // continuous PowerPoint outline that the HTML never had.
    if (sides.some((side) => !side || side.type === 'none')) return null;
    const groups = [];
    sides.forEach((side) => {
      if (!side || side.type === 'none') return;
      const group = groups.find((candidate) => sameBorder(candidate.side, side));
      if (group) group.count += 1;
      else groups.push({ side, count: 1 });
    });
    groups.sort((a, b) => b.count - a.count);
    return groups[0] && groups[0].count >= 2 ? groups[0].side : null;
  }

  function lineOptions(element) {
    const uniform = uniformBorder(element);
    if (uniform) return uniform;
    if (borderSides(element)) {
      return roundedBorderBase(element) || { type: 'none', transparency: 100, width: 0 };
    }
    return borderLineOptions({
      color: element && element.lineColor,
      width: element && element.lineWidth
    });
  }

  function shapeType(pptx, element) {
    if (element && element.shape === 'ellipse') return pptx.ShapeType.ellipse;
    if (finite(element && element.borderRadius, 0) >= 3) return pptx.ShapeType.roundRect;
    return pptx.ShapeType.rect;
  }

  function geometryLineOptions(element) {
    const parsed = color(element && element.lineColor, '000000');
    const width = finite(element && element.lineWidth, 0);
    if (width <= 0 || parsed.transparency >= 100) {
      return { type: 'none', transparency: 100, width: 0 };
    }
    return {
      color: parsed.color,
      transparency: parsed.transparency,
      width: Math.max(0.25, width * 0.75),
      dash: element.lineDash === 'dash' ? 'dash' : 'solid',
      beginArrowType: element.startArrowType || 'none',
      endArrowType: element.endArrowType || 'none'
    };
  }

  function customGeometryPoints(element, canvas) {
    const points = Array.isArray(element && element.points) ? element.points : [];
    const source = element && element.position ? element.position : {};
    const width = Math.max(1, finite(canvas && canvas.width, 1920));
    const height = Math.max(1, finite(canvas && canvas.height, 1080));
    const converted = points.map((point, index) => ({
      x: (finite(point.x, 0) - finite(source.left, 0)) / width * SLIDE_WIDTH_IN,
      y: (finite(point.y, 0) - finite(source.top, 0)) / height * SLIDE_HEIGHT_IN,
      ...(index === 0 ? { moveTo: true } : {})
    }));
    if (element && element.closed) converted.push({ close: true });
    return converted;
  }
  function firstTypeface(value) {
    return String(value || 'Noto Sans TC')
      .split(',')[0]
      .trim()
      .replace(/^["']|["']$/g, '') || 'Noto Sans TC';
  }

  function addText(slide, pptx, element, canvas) {
    const text = String(element.text || '').replace(/\r\n/g, '\n');
    if (!text.trim()) return false;
    const parsedColor = color(element.color, '111111');
    const vertical = element.verticalAlign === 'center' ? 'middle' : element.verticalAlign;
    slide.addText(text, {
      ...position(element, canvas),
      objectName: safeName(element.name, 'html-text'),
      shape: shapeType(pptx, element),
      fontFace: firstTypeface(element.fontFamily),
      fontSize: clamp(finite(element.fontSizePt, 18), 1, 240),
      color: parsedColor.color,
      transparency: parsedColor.transparency,
      bold: Boolean(element.bold),
      italic: Boolean(element.italic),
      charSpacing: finite(element.charSpacingPt, 0),
      underline: Boolean(element.underline),
      ...(element.textDirection && element.textDirection !== 'horz' ? { vert: element.textDirection } : {}),
      align: ['left', 'center', 'right', 'justify'].includes(element.textAlign)
        ? element.textAlign
        : 'left',
      valign: ['top', 'middle', 'bottom'].includes(vertical) ? vertical : 'top',
      margin: 0,
      fit: 'shrink',
      wrap: element.singleLine !== true,
      isTextBox: true,
      fill: fillOptions(element.fill),
      line: lineOptions(element),
      ...(element.hasShadow
        ? { shadow: { type: 'outer', color: '000000', opacity: 0.16, blur: 2, angle: 45, distance: 1 } }
        : {})
    });
    return true;
  }
  function addImage(slide, element, canvas) {
    if (!element.dataUrl || !String(element.dataUrl).startsWith('data:image/')) return false;
    const box = position(element, canvas);
    slide.addImage({
      data: element.dataUrl,
      altText: element.alt || element.name || 'HTML image',
      objectName: safeName(element.name, 'html-image'),
      x: box.x,
      y: box.y,
      w: box.w,
      h: box.h,
      ...(box.rotate === undefined ? {} : { rotate: box.rotate }),
      ...(element.shape === 'ellipse' || finite(element.borderRadius, 0) >= 3 ? { rounding: true } : {}),
      sizing: {
        type: element.fit === 'contain' ? 'contain' : 'cover',
        w: box.w,
        h: box.h
      }
    });
    return true;
  }

  function addShape(slide, pptx, element, canvas) {
    const fill = fillOptions(element.fill);
    const line = lineOptions(element);
    if (fill.type === 'none' && line.type === 'none') return false;
    slide.addShape(shapeType(pptx, element), {
      ...position(element, canvas),
      objectName: safeName(element.name, 'html-shape'),
      fill,
      line,
      ...(element.hasShadow
        ? { shadow: { type: 'outer', color: '000000', opacity: 0.16, blur: 2, angle: 45, distance: 1 } }
        : {})
    });
    return true;
  }

  function addCustomShape(slide, element, canvas) {
    const points = customGeometryPoints(element, canvas);
    if (points.length < 2) return false;
    const fill = fillOptions(element.fill);
    const line = geometryLineOptions(element);
    if (fill.type === 'none' && line.type === 'none') return false;
    slide.addShape('custGeom', {
      ...position(element, canvas),
      objectName: safeName(element.name, 'html-custom-geometry'),
      points,
      fill,
      line,
      ...(element.hasShadow
        ? { shadow: { type: 'outer', color: '000000', opacity: 0.16, blur: 2, angle: 45, distance: 1 } }
        : {})
    });
    return true;
  }

  function roundedEdgeBox(element, box, edge, canvas) {
    const radius = finite(element && element.borderRadius, 0);
    const rounded = element && (element.shape === 'roundRect' || radius >= 3);
    if (!rounded) {
      return edge === 'top'
        ? { x: box.x, y: box.y, w: box.w, h: 0 }
        : edge === 'right'
          ? { x: box.x + box.w, y: box.y, w: 0, h: box.h }
          : edge === 'bottom'
            ? { x: box.x, y: box.y + box.h, w: box.w, h: 0 }
            : { x: box.x, y: box.y, w: 0, h: box.h };
    }
    const canvasWidth = Math.max(1, finite(canvas && canvas.width, 1920));
    const canvasHeight = Math.max(1, finite(canvas && canvas.height, 1080));
    const sourceWidth = box.w / SLIDE_WIDTH_IN * canvasWidth;
    const sourceHeight = box.h / SLIDE_HEIGHT_IN * canvasHeight;
    const effectiveRadius = Math.min(radius, sourceWidth / 2, sourceHeight / 2);
    const insetX = effectiveRadius / canvasWidth * SLIDE_WIDTH_IN;
    const insetY = effectiveRadius / canvasHeight * SLIDE_HEIGHT_IN;
    if (edge === 'top') {
      return { x: box.x + insetX, y: box.y, w: Math.max(0, box.w - insetX * 2), h: 0 };
    }
    if (edge === 'right') {
      return { x: box.x + box.w, y: box.y + insetY, w: 0, h: Math.max(0, box.h - insetY * 2) };
    }
    if (edge === 'bottom') {
      return { x: box.x + insetX, y: box.y + box.h, w: Math.max(0, box.w - insetX * 2), h: 0 };
    }
    return { x: box.x, y: box.y + insetY, w: 0, h: Math.max(0, box.h - insetY * 2) };
  }

  function addAsymmetricBorders(slide, pptx, element, canvas) {
    const sides = borderSides(element);
    if (!sides || uniformBorder(element)) return 0;
    const box = position(element, canvas);
    if (box.rotate !== undefined && Math.abs(box.rotate) > 0.01) return 0;
    // A rounded PowerPoint shape can own one continuous outline, but it
    // cannot express four different CSS border sides.  Never draw those
    // sides across the full rectangular bounds: that recreates a square
    // frame outside the rounded HTML surface.
    if (element && element.shape === 'ellipse') return 0;
    const baseBorder = element && element.kind === 'image' ? null : roundedBorderBase(element);
    const edgeNames = ['top', 'right', 'bottom', 'left'];
    const edges = edgeNames.map((name) => ({
      name,
      ...roundedEdgeBox(element, box, name, canvas)
    }));
    let added = 0;
    edges.forEach((edge, index) => {
      const line = sides[index];
      if (!line || line.type === 'none') return;
      if (baseBorder && sameBorder(line, baseBorder)) return;
      if (Math.abs(edge.w) + Math.abs(edge.h) < 0.01) return;
      slide.addShape(pptx.ShapeType.line, {
        x: edge.x,
        y: edge.y,
        w: edge.w,
        h: edge.h,
        objectName: safeName((element.name || 'html-border') + '-' + edge.name, 'html-border'),
        line
      });
      added += 1;
    });
    return added;
  }

  function slideLayoutKey(slide, index) {
    return safeName(
      String(slide && slide.layoutId || 'slide') + '-page-' + (index + 1),
      'slide-' + (index + 1)
    );
  }

  function defineLayouts(pptx, manifest) {
    const layouts = new Map();
    manifest.slides.forEach((slide, index) => {
      const layoutKey = slideLayoutKey(slide, index);
      const title = 'HTML-' + String(layouts.size + 1).padStart(2, '0') + '-' + layoutKey;
      const background = color(slide.backgroundColor, 'FFFFFF');
      const backgroundImage = slide && slide.backgroundImage;
      const objects = backgroundImage && String(backgroundImage.dataUrl || '').startsWith('data:image/')
        ? [{
          image: {
            data: backgroundImage.dataUrl,
            objectName: safeName('slide-background-' + (index + 1), 'slide-background'),
            x: 0,
            y: 0,
            w: SLIDE_WIDTH_IN,
            h: SLIDE_HEIGHT_IN,
            sizing: {
              type: backgroundImage.fit === 'contain' ? 'contain' : 'cover',
              x: 0,
              y: 0,
              w: SLIDE_WIDTH_IN,
              h: SLIDE_HEIGHT_IN
            }
          }
        }]
        : [];
      pptx.defineSlideMaster({
        title,
        background: { color: background.color, transparency: background.transparency },
        objects
      });
      layouts.set(index, title);
    });
    return layouts;
  }

  function validateManifest(manifest) {
    if (!manifest || !Array.isArray(manifest.slides) || manifest.slides.length === 0) {
      throw new Error('manifest.slides must contain at least one slide');
    }
    if (manifest.slides.length > MAX_SLIDES) {
      throw new Error('manifest contains more than ' + MAX_SLIDES + ' slides');
    }

  }

  function buildPresentation(manifest) {
    validateManifest(manifest);
    if (typeof root.PptxGenJS !== 'function') {
      throw new Error('PptxGenJS browser runtime is unavailable');
    }
    const pptx = new root.PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'HTML Presentation Editor';
    pptx.company = 'OpenAI Codex';
    pptx.subject = 'Native editable PowerPoint positioned from the 1920x1080 HTML coordinate system';
    pptx.title = manifest.title || 'HTML presentation';
    pptx.lang = 'zh-TW';
    pptx.theme = {
      headFontFace: 'Noto Sans TC',
      bodyFontFace: 'Noto Sans TC',
      lang: 'zh-TW'
    };

    const layouts = defineLayouts(pptx, manifest);
    const warnings = [];
    let nativeObjects = 0;
    let rasterObjects = 0;
    let backgroundImages = 0;
    const fidelitySlides = 0;
    manifest.slides.forEach((slideSpec, slideIndex) => {
      const slide = pptx.addSlide({ masterName: layouts.get(slideIndex) });
      const background = color(slideSpec.backgroundColor, 'FFFFFF');
      slide.background = { color: background.color, transparency: background.transparency };
      if (slideSpec.backgroundImage && String(slideSpec.backgroundImage.dataUrl || '').startsWith('data:image/')) {
        backgroundImages += 1;
        rasterObjects += 1;
      }
      const elements = Array.isArray(slideSpec.elements) ? slideSpec.elements : [];
      elements.forEach((element, elementIndex) => {
        let added = false;
        if (element.kind === 'image') {
          added = addImage(slide, element, manifest.canvas);
          if (added) rasterObjects += 1;
        } else if (String(element.text || '').trim()) {
          added = addText(slide, pptx, element, manifest.canvas);
          if (added) nativeObjects += 1;
        } else if (element.kind === 'custom' || element.shape === 'custom') {
          added = addCustomShape(slide, element, manifest.canvas);
          if (added) nativeObjects += 1;
        } else {
          added = addShape(slide, pptx, element, manifest.canvas);
          if (added) nativeObjects += 1;
        }
        const borderObjects = addAsymmetricBorders(slide, pptx, element, manifest.canvas);
        nativeObjects += borderObjects;
        added = added || borderObjects > 0;
        if (!added) {
          warnings.push({
            slide: slideIndex + 1,
            element: safeName(element.name, 'element-' + (elementIndex + 1)),
            issue: element.kind === 'image' ? 'image-source-unavailable' : 'empty-or-invisible'
          });
        }
      });

    });

    return {
      pptx,
      summary: {
        slides: manifest.slides.length,
        layouts: layouts.size,
        nativeObjects,
        rasterObjects,
        backgroundImages,
        fidelitySlides,
        warnings
      }
    };
  }

  async function exportManifest(manifest, options) {
    const built = buildPresentation(manifest);
    const fileName = String((options && options.fileName) || manifest.fileName || 'edited-presentation.pptx')
      .replace(/[<>:"/\\|?*\u0000-\u001f]/g, '-');
    const output = await built.pptx.write({ outputType: 'blob', compression: true });
    const blob = output instanceof Blob
      ? output
      : new Blob([output], {
        type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
      });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    return {
      fileName,
      bytes: blob.size,
      slides: built.summary.slides,
      layouts: built.summary.layouts,
      nativeObjects: built.summary.nativeObjects,
      rasterObjects: built.summary.rasterObjects,
      backgroundImages: built.summary.backgroundImages,
      fidelitySlides: built.summary.fidelitySlides,
      nativeOnly: built.summary.fidelitySlides === 0 && built.summary.backgroundImages === 0,
      hybrid: built.summary.fidelitySlides === 0 && built.summary.backgroundImages > 0,
      warnings: built.summary.warnings,
      method: 'pptxgenjs-browser'
    };
  }

  root.PptxBrowserExport = {
    version: 3,
    buildPresentation,
    exportManifest
  };
}(window));
