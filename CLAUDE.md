# NESA-SLIDE — Claude Code Guide

This repository is a ready-to-use presentation workspace.

## When the user asks for a presentation

Immediately read and follow `.claude/skills/create-presentation/SKILL.md`. It is the single front door and will route planning, design, HTML, PPTX, and Image2 work.

- Do not make the user choose internal renderers or manifests before work can begin.
- Use existing context and ask only questions that materially change the result.
- Put every new deliverable under `workspace/<project-id>/`.
- If dependencies are missing, run `npm run setup`; otherwise use `npm run doctor`.
- Finish the artifact and its required QA before calling the task complete.

## Skill ownership

`.agents/skills/` is canonical. `.claude/skills/` is a generated, checked-in mirror for Claude Code discovery. Never edit the mirror independently.

Framework maintenance still follows `AGENTS.md`, `prompt_system/AGENTS.md`, and the formal references. Ordinary presentation requests should not start with those internal documents; start with `create-presentation`.
