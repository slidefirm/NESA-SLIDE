# Project Format Guide

## Purpose

This project uses multiple YAML layers. When the user asks for "generate presentation YAML", default to the assembled prompt layer unless they explicitly request another layer.

For a multi-slide deck, Art Direction is a deck-level input before Theme/Layout
selection. Validate it with `scripts/art_direction.py`, choose the current scene
role, then merge its handoff into the existing seven assembled sections. Do not
add an eighth top-level section. The authoritative mapping is in the project
root `references/project-format-guide.md`.

## The Three Relevant Layers

### 1. Layout YAML

Use when the user wants the page skeleton only.

Characteristics:
- `id`
- `slots`
- `region`
- `weight`
- `alignment_rules`
- no actual slide content

Example shape:

```yaml
id: toc-4
slots:
  - id: title
    region: [8, 10, 84, 10]
    weight: hero
```

### 2. Spec YAML

Use when the user explicitly asks for a single-slide structured spec.

Characteristics:
- `theme_ref`
- `layout`
- `content`
- `composition_rules`
- `validation`

### 3. Assembled Prompt YAML

Default layer for this skill.

Characteristics:
- mirrors the local seven-stage prompt formula
- content is concrete and slide-ready
- can be converted into prose prompt later

## Default Seven-Stage Template

```yaml
page_type_and_mood:
  prompt: ""

visual_base_2a:
  background: {}
  typography: {}
  color_system: {}

corner_decoration_2b:
  rule: ""
  top_left: {}
  top_right: {}
  bottom_left: {}
  bottom_right: {}

layout_description:
  structure: ""

content:
  title: ""
  body: {}

safe_zone_constraints:
  hard_constraint: ""

closing_design_intent:
  prompt: ""
```

## Selection Guide

### If the content is...

- title + narrative + one visual
  - prefer `left-text-right-image`
- statement or chapter break
  - prefer `quote-focus`, `title-center`, `chapter-opener`
- modules or cards
  - prefer `cards-*`, `grid-cards`, `findings-cluster`
- process or journey
  - prefer `process-flow`, `timeline-milestones`, `customer-journey`, `onboarding-path`
- comparison or structured alternatives
  - prefer `split-comparison`, `comparison-table`, `matrix-4quadrant`, `pricing-packages`
- KPI / dashboard / review
  - prefer `kpi-scorecards`, `dashboard-overview`, `pipeline-health-review`

## Anti-Patterns

Do not output:

```yaml
title:
theme:
slides:
  - type: cover
```

unless the user explicitly asks for a deck-level format.

Do not collapse seven-stage output into a single prose block when the user asked for YAML.
