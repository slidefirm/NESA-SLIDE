---
name: generate-image-slide
description: Generate a single image-based slide YAML for this project using the local seven-stage prompt assembly structure instead of a generic deck format. Use when the user asks to generate, draft, convert, rewrite, or randomize an image slide YAML, prompt YAML, or presentation YAML for Image2 in this repo; when the user provides reference notes, source text, or slide intent and wants it turned into YAML; or when Codex must choose a suitable local layout, theme, and design approach from `prompt_system/` and output the result in the project's seven-stage format.
---

# Generate Image Slide

Generate one slide at a time.

This Skill constructs and validates assembled YAML. For a formal bitmap preview, follow `references/image2-preview-workflow.md`; do not start a nested `codex exec` process. When a multi-slide Image2 presentation is ready to present, also complete the PPTX review handoff below before delivery.

Do not default to a generic deck format such as:

```yaml
title:
slides:
  - type:
```

In this project, "generate presentation YAML" means generating a YAML-structured version of the local seven-stage prompt assembly format unless the user explicitly asks for another layer such as `layout YAML` or `spec YAML`.

## Workflow

You CONSTRUCT each YAML from two clean sources: the fixed seven-stage grammar
(for shape) and the chosen layout's own files (for which slots exist). Every
value is written fresh for the current slide. The seed is always
`structure + this layout's declared slots` — never a finished YAML.
`artifacts/generated-prompts/*.assembled.yaml` are outputs, not templates;
copying one drags its content and style into your result.

1. Identify source material. Use the user's reference content first; if none,
   invent reasonable demo content for this slide.

2. For a multi-slide deck, or whenever an `art_direction_ref` is provided,
   validate and read the shared direction before choosing a Layout:
   - `python scripts/art_direction.py <art-direction.yaml>`
   - choose the current `scene_role` first
   - read the renderer handoff for Theme candidates and Layout sequence
   - a `ready-for-audition` direction may produce audition slides only
   - formal output requires `--require-approved`
   A one-off Layout preview without a deck-level Story may continue without an
   Art Direction file.

3. Pick one local layout from `prompt_system/layouts/` by communication shape
   and the current scene role,
   not keywords. Default output layer is `assembled prompt YAML` (only switch if
   the user explicitly asks for layout YAML, spec YAML, or a deck format).

4. Read the chosen layout file. It is the source of spatial slots, regions,
   zones, alignment, and structure for this slide:
   - `prompt_system/layouts/<id>.yaml` → slots, decoration / design_zone, alignment, structure
   List the layout slots and decoration zones from what this file declares right
   now, not from memory.

   Also read the generated Image2 adapters for the selected sources:
   - `prompt_system/renderers/image2/layouts/<id>.yaml`
   - `prompt_system/renderers/image2/themes/<id>.yaml`
   Adapters define renderer projection only; the core layout/theme remains authoritative.

5. Decide a transient content contract for this slide from the user's material,
   the selected layout, and the slide's communication goal. This contract is an
   assembly-time decision only: choose the content fields, repeated item counts,
   optional fields, and text density that make the current slide work. Do not
   read or create persistent per-layout content-field files.

6. Read the seven-stage grammar in `references/project-format-guide.md`.
   Take the SHAPE only; do not lift any wording into your output.

7. Emit the seven sections, writing every value fresh for this slide. When an
   Art Direction exists, merge it into these sections using the mapping in the
   format guide; never add an eighth top-level section:
   - Fixed sections (page_type_and_mood, visual_base_2a, safe_zone_constraints,
     closing_design_intent): fill the grammar with this slide's values.
   - content: one entry per field in the transient content contract — no more,
     no fewer.
   - corner_decoration_2b: expand the layout's `decoration` (design_zone / prescribe
     / free_zone), one entry per zone the layout declares. A design_zone defaults
     to "open for decoration"; never emit it as empty or "no decoration" by default
     — minimalism is a style_case override, not a layout default.
   - layout_description: follow the layout's structure and regions.

8. One slide per output unless the user asks for several.

9. After rendering a project preview, inspect the actual image using
   `references/preview-qa-loop.md`, record the result, and iterate only on failed
   checks. Do not treat successful image generation as successful layout QA.

## Output Contract

Unless the user says otherwise, output YAML with exactly these seven top-level sections:

```yaml
page_type_and_mood:
visual_base_2a:
corner_decoration_2b:
layout_description:
content:
safe_zone_constraints:
closing_design_intent:
```

This is the default project output for this skill.

Do not silently convert the result into:
- a generic deck format
- a `slides:` array
- a `theme_ref + layout + validation` spec format
- a raw prose prompt without YAML structure

## Multi-slide PPTX Review Handoff

This handoff applies only after a multi-slide Image2 presentation has rendered images and is being delivered for presentation or review. It does not turn a one-off YAML request into a PPTX request.

In addition to the assembled YAML files and rendered Image2 pages, create a companion `*-image2-review.pptx` so the user can review the full deck in PowerPoint:

- Package exactly one accepted 16:9 rendered Image2 page per PPTX slide, preserving the manifest's slide order and page count.
- Keep the review PPTX alongside the deck's other delivery artifacts, and record the source image path, source YAML path, page number, and QA status for every slide in a small handoff manifest or QA ledger.
- Package only pages with a usable rendered image and completed preview QA. If any page is missing or unresolved, keep the PPTX explicitly `partial` and list the affected page numbers; do not silently omit, reorder, or replace them.
- Label the package and final response as **review-only / flattened**. It is a convenience copy for inspection, not an editable PowerPoint deliverable and not a substitute for the source YAML or Image2 images.

Use `ppt-builder` and `references/pptx-generation-rules.md` for the PPTX packaging and verification boundary. If the user asks for an editable PPTX rather than a review copy, route the work to `ppt-builder`'s `hybrid` path: use the assembled YAML as content input, generate or validate text-free Image2 backgrounds, and keep foreground content as native PowerPoint objects. Never claim that a PPTX built from complete rendered Image2 pages is editable.

## Layout Selection Heuristics

Pick the layout from the local catalog that best matches the information shape:

For a deck with Art Direction, scene role is decided before this heuristic.
The heuristic only selects a Layout inside the role and direction constraints.

- One main message plus supporting image: `left-text-right-image`
- Cover or hero statement: `hero-fullbleed` (文字左下全版), `hero-fullbleed-brand-footer` (文字左側全版), `cover-photo-frame` (左圖右文半版), `cover-photo-frame-reverse` (左文右圖半版), `cover-center-title-edge-decor` (文字置中素色), `quote-focus`, `title-center`
- Agenda or chapter map: `toc-*`, `toc-number-*`, `toc-list`
- Parallel modules or grouped insights: `cards-*`, `grid-cards`, `findings-cluster`, `team-roster`
- Timeline, path, rollout, process, cadence: `timeline-milestones`, `process-flow`, `gantt-roadmap`, `onboarding-path`, `implementation-rollout-map`
- Comparison, quadrant, options, pricing: `split-comparison`, `comparison-table`, `matrix-4quadrant`, `swot-quadrant`, `pricing-packages`, `battlecard-compare`
- KPI or review page: `kpi-scorecards`, `dashboard-overview`, `pipeline-health-review`, `business-review-rhythm`

If two layouts both fit, prefer the simpler one unless the user clearly needs denser structure.

**無法提供圖片時的版型限制：**
當 AI 無法生成、取得或嵌入實際圖片時（例如純文字輸入、無圖片素材），
禁止選擇需要照片的版型，包含：
- 半版照片類：`cover-photo-frame`、`cover-photo-frame-reverse`、`photo-left-overlay-title-right`、`chapter-text-left-photo-brand`、任何 `*-photo-*` 版型
- 滿版照片類：`hero-fullbleed`（背景設定 photo 時）、`chapter-fullbleed-overlay-title`、`closing-photo-overlay-contact`、任何 `fullbleed` 版型若其 visual_base_2a 需要真實照片
- 改選純色或文字為主的版型：`hero-fullbleed`（純色背景）、`cover-center-title-edge-decor`、`title-center`、`quote-focus`、`cards-*`、`toc-*` 等。

## Design Selection Heuristics

When choosing visual direction:

- Reuse a local theme if one is obviously suitable.
- If no single theme fits perfectly, still output the YAML in seven-stage form and synthesize a 2A/2B direction that feels consistent with the local catalog.
- Keep 2A focused on background, typography, palette, mood, and illustration style.
- For `visual_base_2a.illustration_style`: choose one of 扁平插畫 / 3D風格 / 線條圖示 / 抽象藝術 / 無.
  This is a soft style rule — it applies when the slide content contains icons or supporting illustrations.
  If the slide has no illustrations, set type to「無」. Never force illustrations to appear just because a type is set.
- Keep 2B focused on corner-only or edge-only decorations, never primary content.

## Layout Purity Rules

- Treat `prompt_system/layouts/*.yaml` as structure only: slots, regions, weights, alignment, balance, and content roles.
- Do not put concrete design treatments such as sepia, coffee brown, dark label color, blur style, photo filter, or typography mood into layout descriptions.
- Layout naming formula: content role + spatial relationship + decoration position. Example: a centered title with four-corner/edge decorations is `center-title-edge-decor`.
- Style naming formula: visual language + color/texture + decoration treatment. Example: `geometric style` describes linework, shapes, patterns, palette, and texture, so it belongs in theme / 2A / 2B.
- Stable decision sentence: first name how the slide is divided and where things sit; then name what the slide looks like. The first part is layout, the second part is style.
- The same layout can support many styles: `center-title-edge-decor` can become geometric linework, organic blobs, circuit ornaments, doodles, brand color blocks, or classic borders.
- When the user shares an image, treat it by default as a style reference the user considers good-looking. First classify it into the closest existing layout, then store its colors, typography, texture, decorative shapes, and mood as theme / 2A / 2B direction.
- Add a new layout only when the image introduces a content role, spatial relationship, or decoration region that existing layouts cannot express.
- For any layout with a half-page supporting image or image/text split, make every text-side block share one clear left edge or one clear right edge. This applies to cover layouts, `left-text-right-image`, and future half-image variants. Record the chosen text-side alignment in `layout_description`.
- A subtitle may be described structurally as a subtitle panel or differently styled subtitle area. Its job is to use a design treatment different from the main title, not to automatically become a highlight block. Its actual color, fill, border, texture, and type style belong in `visual_base_2a` or `corner_decoration_2b`, not the layout layer.
- Visual weight must match information hierarchy. Do not make one module larger, wider, higher-contrast, or more photo-heavy unless that slot is semantically primary.
- If a layout declares `visual_balance.method: equal-modules`, treat all module slots as parallel peers: equal width, equal height, equal typography scale, and equal color/contrast weight. The title can frame the set, but no module becomes a primary claim card.
- If the content needs one governing idea plus supporting modules, use a layout whose slots explicitly declare primary/supporting roles; do not force that hierarchy into an equal-modules layout just because it looks dynamic.
- Title alignment follows this priority: explicit `alignment_rules` in the selected layout first, semantic inference second, and never random or quota-based distribution.
- When the layout does not specify title alignment, center a title only when it is at most two lines, the composition is symmetric, radial, or center-focused, and there is no leading-edge reading axis. Otherwise use leading alignment for left-to-right content.
- When a short subtitle belongs to a centered framing title, keep title and subtitle on the same center axis unless the layout explicitly declares another relationship.
- Equal-width modules alone do not require a centered title. Centering also requires a centered visual axis and the absence of a left-aligned reading flow.
- When the layout does not explicitly fix title alignment, classify the title by estimated rendered width within the safe area: short below 35%, medium from 35% to 72%, and long above 72%.
- Short titles default to leading alignment and must not be enlarged merely to fill width. Medium titles default to horizontal centering when they frame the whole slide.
- Long titles must be rewritten semantically into a concise main title plus subtitle before layout. Keep the core claim in the main title and move context, scope, or explanation into the subtitle; do not solve length by extreme shrinking or arbitrary line wrapping.
- Explicit layout semantics override these defaults: covers, chapter openers, centered statements, and other declared centered-title layouts remain centered regardless of title length class.
- Treat the title block and content block as separate vertical regions. Their ranges must never overlap or merely touch.
- For ordinary information slides, reserve a transition gap of at least 5% of slide height between the bottom of the complete title block (title, subtitle, rule, and title decoration) and the top of primary content.
- Title decoration belongs inside the title region. Content diagrams, cards, connectors, labels, and shadows must not enter the title region or its transition gap.
- Before emitting YAML, calculate `content_top - title_bottom`. If it is below 5%, adjust the regions or reduce content density; do not rely on the image model to create separation.
- The transition gap is foreground-clear, not visually empty. Low-contrast 2A background texture, gradients, or continuous fields may pass through it.
- Keep 2B decoration active in declared edge and corner zones. Do not remove 2A/2B merely to satisfy title-content separation; instead keep high-contrast decoration outside the transition gap.

## Content Rules

- Use the user's reference material when available.
- Compress long notes into slide-sized content.
- Preserve the original communication goal.
- Do not overfill the slide.
- Prefer concise bullets, modules, labels, and visual descriptions.

If the user asks for "random", randomize the topic or framing, but still choose a coherent layout and design method.

## Safe-Zone Rules

Always include explicit hard constraints for content staying inside the 10%-90% safe zone unless the user provides a different project rule.

Allow only low-priority background texture or bleed effects to extend beyond the safe zone.

## Style Rules

- Write YAML, not Markdown bullets disguised as YAML.
- Keep field names stable across outputs.
- Keep the seven-stage order stable.
- Make each section concrete enough that it can be used as a prompt assembly artifact.

## References

Read [references/project-format-guide.md](references/project-format-guide.md) when you need:
- a reminder of the differences between `layout YAML`, `spec YAML`, and `assembled prompt YAML`
- a copyable seven-stage template
- a quick mapping from content shape to local layouts
