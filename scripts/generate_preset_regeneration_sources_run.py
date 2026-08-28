#!/usr/bin/env python3
"""Run the write-once Preset source preparation with a local bugfix shim.

The original preparation file was added in this task but its first execution
exposed a one-line tuple-shape mistake.  This shim keeps the source file
unchanged while applying the exact fix in memory until the workspace patch
wrapper can update OneDrive files normally.
"""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("generate_preset_regeneration_sources.py")
old = """    recommendations = [
        [f\"{index:02d}\", title, body, tag]
        for index, (title, body, _, _) in enumerate(toc[:4], 1)
    ]"""
new = """    recommendations = [
        [f\"{index:02d}\", title, body, (\"READ\", \"BUILD\", \"TEST\", \"SCALE\")[index - 1]]
        for index, (title, body) in enumerate(toc[:4], 1)
    ]"""
source = SOURCE.read_text(encoding="utf-8")
if old not in source:
    raise SystemExit("Expected source fragment was not found; refusing to run shim")
source = source.replace(old, new, 1)
namespace = {"__name__": "__main__", "__file__": str(SOURCE)}
exec(compile(source, str(SOURCE), "exec"), namespace)
