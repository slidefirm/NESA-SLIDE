---
name: create-presentation
description: Use this as the front door whenever the user asks to create, draft, redesign, or generate a presentation, slide deck, PPTX, or editable HTML deck in this NESA-SLIDE workspace. It routes the request to the correct planning and renderer Skills and owns the end-to-end handoff. Do not use it for framework maintenance or release engineering.
---

# Create a presentation with NESA-SLIDE

This is the single user-facing entry point. Keep internal renderer and packaging details out of the user's way unless they affect the requested result.

## 1. Confirm the workspace is ready

If dependencies are missing, run `npm run setup`. Otherwise use `npm run doctor` for a fast capability check. Do not ask the user to install dependencies that the setup command can install safely.

All new work belongs under `workspace/<kebab-case-project>/`. Never edit shipped examples or Gallery artifacts as the user's output.

## 2. Understand the request

Use the information already provided. Ask only questions that materially change the topic, audience, length, output format, or visual direction.

If the user does not specify a format, default to an editable HTML deck. If they explicitly request PowerPoint, use the native editable PPTX workflow. If they explicitly request slide images, use Image2.

## 3. Route to the canonical Skills

Read these Skills in order as needed:

1. `.agents/skills/slide-outline-planner/SKILL.md` for narrative, page roles, and content-to-Layout planning.
2. `.agents/skills/design-presentations/SKILL.md` for coherent art direction and composition.
3. Renderer workflow:
   - Editable HTML without generated imagery: `.agents/skills/html-pattern-slide/SKILL.md`
   - Editable HTML with planned imagery: `.agents/skills/html-image-slide/SKILL.md`, then `html-pattern-slide`
   - Native editable PowerPoint: `.agents/skills/ppt-builder/SKILL.md`
   - Image slides: `.agents/skills/generate-image-slide/SKILL.md`
   - Add image backgrounds to an existing deck: `.agents/skills/slide-background-image/SKILL.md`

`.agents/skills` is canonical. Claude Code receives a checked-in mirror under `.claude/skills`; never maintain the two copies independently.

## 4. Produce and verify the deck

Follow the chosen renderer Skill completely. Preserve user content, create a reproducible manifest, and run the direct artifact QA required by that Skill. A generated file without visual, interaction, or package verification is not a finished deck.

For HTML, keep the output editable and provide the exact local URL or file. For PPTX, verify native text/shapes and package structure; do not present a flattened slide image as editable PowerPoint.

## 5. Hand off

Report only what the user needs:

- what was created;
- where to open it;
- what was verified;
- any external capability that remains unavailable.

Do not lead with internal audit history, adapter counts, or release mechanics.
