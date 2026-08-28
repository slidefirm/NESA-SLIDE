from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from html_theme_lab_catalog import load_catalog as load_html_theme_catalog
from html_preset_themes import load_html_preset_theme_catalog
from html_preset_registry import load_preset_registry, published_entries

try:
    import yaml
except ModuleNotFoundError:  # keep this generator runnable in bare Python.
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
THEMES_DIR = ROOT / "prompt_system" / "themes"
JS_OUT = ROOT / "artifacts" / "deploy" / "themes-gallery.js"
STYLE_CASES_DIR = ROOT / "prompt_system" / "style_cases"
STYLE_CASE_PREVIEWS_DIR = ROOT / "artifacts" / "deploy" / "layout-style-cases"
DEPLOY_DIR = ROOT / "artifacts" / "deploy"
THEME_PREVIEWS_DIR = DEPLOY_DIR / "theme-previews"
HTML_PRESET_PREVIEWS_DIR = DEPLOY_DIR / "theme-presets"
HTML_THEME_CONTACT_SHEETS_DIR = ROOT / "artifacts" / "theme-demos" / "html-theme-lab" / "qa" / "contact-sheets"
HTML_THEME_DECKS_DIR = ROOT / "artifacts" / "theme-demos" / "html-theme-lab" / "html"
HTML_PRESET_DEPLOY_DIR = DEPLOY_DIR / "theme-html-lab"
CURATED_HTML_PRESET_CATALOG = ROOT / "prompt_system" / "renderers" / "html" / "preset-themes.yaml"
IMAGE_EXTS = (".webp", ".png", ".jpg", ".jpeg")
THEME_SOURCE_THRESHOLD = 42


def palette_values(palette: dict) -> list[str]:
    """Return stable, unique hex colors from an authored HTML Theme palette."""
    colors: list[str] = []
    for value in palette.values():
        color = str(value or "").upper()
        if re.fullmatch(r"#[0-9A-F]{6}", color) and color not in colors:
            colors.append(color)
    return colors


def load_authored_html_preset_themes(include_ids: set[str] | None = None) -> list[dict]:
    """Normalize accepted HTML Presets into the same catalog card contract."""
    catalog = load_html_theme_catalog()
    presets: list[dict] = []
    HTML_PRESET_PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    for row in catalog.get("themes", []):
        if row.get("publish", True) is False:
            continue
        theme_id = row["theme_id"]
        if include_ids is not None and theme_id not in include_ids:
            continue
        contact_sheet = HTML_THEME_CONTACT_SHEETS_DIR / theme_id / "contact-01.jpg"
        preview_image = ""
        if contact_sheet.is_file():
            deployed_preview = HTML_PRESET_PREVIEWS_DIR / f"{theme_id}.jpg"
            shutil.copy2(contact_sheet, deployed_preview)
            preview_image = rel_deploy_path(deployed_preview)
        source_html = HTML_THEME_DECKS_DIR / f"{theme_id}.html"
        html_url = ""
        if source_html.is_file():
            deployed_html = HTML_PRESET_DEPLOY_DIR / theme_id / "index.html"
            deployed_html.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_html, deployed_html)
            html_url = f"/theme-html-lab/{theme_id}/"
        palette = row.get("palette", {}) or row.get("theme", {}).get("palette", {}) or {}
        colors = palette_values(palette)
        colors += ["#F7F7F5", "#172033", "#667085", "#35B7C8"]
        typography = row.get("typography", {}) or row.get("theme", {}).get("typography", {}) or {}
        slide_count = int(row.get("slide_count", len(row.get("slides", []))))
        presets.append({
            "id": theme_id,
            "display_name": row.get("display_name") or row.get("theme", {}).get("display_name") or theme_id,
            "background_color": colors[0],
            "background_style": " · ".join(filter(None, [row.get("pattern", ""), row.get("material", "")])),
            "primary": colors[1],
            "primary_use": "主要文字與結構",
            "secondary": colors[2],
            "secondary_use": "次要層級與輔助資訊",
            "accent": colors[3],
            "accent_use": "狀態、重點與導引",
            "support_hexes": colors[4:6],
            "typography_heading": typography.get("display", "Noto Sans TC"),
            "typography_body": typography.get("body", "Noto Sans TC"),
            "illustration_default": "純 HTML pattern、陰影與語意化結構，不依賴圖片式底圖",
            "mood": ["HTML Preset", row.get("family", "內容先行")],
            "deco_names": list(row.get("decorations", [])),
            "closing": row.get("design_intent", "")[:240],
            "preview_image": preview_image,
            "preview_label": f"HTML Preset · {slide_count} 頁",
            "preview_source": "html-theme-lab",
            "preview_match_score": 1000,
            "preview_source_theme": theme_id,
            "preview_yaml_path": row.get("_content_source", ""),
            "preview_match_method": "authored-html-preset",
            "theme_kind": "html-preset",
            "theme_kind_label": "HTML Preset",
            "html_url": html_url,
            "topic_title": (row.get("topic") or {}).get("title", ""),
            "slide_count": slide_count,
            "pattern": row.get("pattern", ""),
            "material": row.get("material", ""),
            "design_intent": row.get("design_intent", ""),
        })
    return presets


def curated_preset_preview(theme_id: str, preset: dict) -> tuple[str, str]:
    """Deploy the best available QA/style-case preview for a curated preset."""
    candidates: list[Path] = [
        HTML_THEME_CONTACT_SHEETS_DIR / theme_id / "contact-01.jpg",
        ROOT / "artifacts" / "html-style-case-examples" / "qa" / "contact-sheets-final" / theme_id / "contact-01.jpg",
    ]
    source_style_case = ROOT / str(preset.get("source_style_case", ""))
    if source_style_case.is_file():
        style_case = safe_load_yaml(source_style_case.read_text(encoding="utf-8"))
        case_preview = (style_case.get("composition_notes") or {}).get("case_preview")
        if case_preview:
            candidates.append(ROOT / str(case_preview))
        for ext in IMAGE_EXTS:
            candidates.append(STYLE_CASE_PREVIEWS_DIR / f"{source_style_case.stem}{ext}")

    source = next((path for path in candidates if path.is_file()), None)
    if not source:
        return "", ""
    suffix = ".jpg" if source.suffix.lower() == ".jpeg" else source.suffix.lower()
    deployed_preview = HTML_PRESET_PREVIEWS_DIR / f"{theme_id}{suffix}"
    shutil.copy2(source, deployed_preview)
    return rel_deploy_path(deployed_preview), source.relative_to(ROOT).as_posix()


def deploy_curated_preset_html(theme_id: str) -> tuple[str, int]:
    """Publish a real editable case when the curated preset has an authored deck."""
    source_html = HTML_THEME_DECKS_DIR / f"{theme_id}.html"
    if not source_html.is_file():
        return "", 0
    markup = source_html.read_text(encoding="utf-8")
    slide_count = len(re.findall(
        r'<section\b[^>]*\bclass=(["\'])[^"\']*\bslide\b[^"\']*\1',
        markup,
        flags=re.IGNORECASE,
    ))
    deployed_html = HTML_PRESET_DEPLOY_DIR / theme_id / "index.html"
    deployed_html.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_html, deployed_html)
    return f"/theme-html-lab/{theme_id}/", slide_count


def load_curated_html_preset_themes(include_ids: set[str] | None = None) -> list[dict]:
    """Expose registry-selected reusable preset-themes.yaml entries."""
    catalog = load_html_preset_theme_catalog(CURATED_HTML_PRESET_CATALOG)
    presets: list[dict] = []
    HTML_PRESET_PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    for theme_id, preset in (catalog.get("themes") or {}).items():
        if include_ids is not None and theme_id not in include_ids:
            continue
        palette = preset.get("palette") or {}
        preview_image, preview_source_path = curated_preset_preview(theme_id, preset)
        html_url, slide_count = deploy_curated_preset_html(theme_id)
        techniques = list(preset.get("techniques") or [])
        layouts = list(preset.get("example_layouts") or [])
        presets.append({
            "id": theme_id,
            "display_name": preset.get("display_name") or theme_id,
            "background_color": palette.get("background", "#F7F7F5"),
            "background_style": preset.get("composition", ""),
            "primary": palette.get("text", "#172033"),
            "primary_use": "主要文字與結構",
            "secondary": palette.get("muted", "#667085"),
            "secondary_use": "次要層級與輔助資訊",
            "accent": palette.get("accent", "#35B7C8"),
            "accent_use": "狀態、重點與導引",
            "support_hexes": [
                color for color in (palette.get("support"), palette.get("surface"))
                if color
            ],
            "typography_heading": "Noto Sans TC",
            "typography_body": "Noto Sans TC",
            "illustration_default": "純 HTML Pattern、字體、陰影與語意化幾何",
            "mood": ["HTML Preset", "正式 Preset Catalog"],
            "deco_names": techniques[:4],
            "closing": preset.get("composition", "")[:240],
            "preview_image": preview_image,
            "preview_label": f"HTML Preset · {slide_count} 頁" if slide_count else "HTML Preset · 可重複選取",
            "preview_source": "html-preset-catalog",
            "preview_match_score": 1000 if preview_image else 0,
            "preview_source_theme": theme_id,
            "preview_yaml_path": preset.get("source_style_case", ""),
            "preview_match_method": "curated-html-preset-catalog",
            "preview_source_path": preview_source_path,
            "theme_kind": "html-preset",
            "theme_kind_label": "HTML Preset",
            "html_url": html_url,
            "topic_title": "",
            "slide_count": slide_count,
            "pattern": preset.get("design_dialect", ""),
            "material": " · ".join(techniques),
            "design_intent": preset.get("composition", ""),
            "base_theme": preset.get("base_theme", ""),
            "example_layouts": layouts,
        })
    return presets


def safe_load_yaml(text: str) -> dict:
    if not yaml:
        return {}
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def extract_scalar(text: str, key: str, default: str = "") -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(.+?)\s*$", text)
    if not match:
        return default
    value = match.group(1).strip()
    if value in {">", "|"}:
        return default
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
    return value


def extract_section(text: str, key: str) -> str:
    match = re.search(rf"(?m)^({re.escape(key)}):\s*(?:>|\\|)?\s*$", text)
    if not match:
        return ""
    start = match.end()
    following = text[start:]
    end_match = re.search(r"(?m)^[A-Za-z_][A-Za-z0-9_ -]*:\s*", following)
    return following[:end_match.start()] if end_match else following


def extract_nested_scalar(section: str, key: str, default: str = "") -> str:
    return extract_scalar(section, key, default)


def extract_palette_color(section: str, color_key: str, default: str) -> str:
    pattern = rf"(?ms)^\s*{re.escape(color_key)}:\s*(.*?)(?=^\s{{4}}[A-Za-z_-]+:|\Z)"
    match = re.search(pattern, section)
    if not match:
        return default
    return extract_scalar(match.group(1), "hex", default)


def extract_palette_use(section: str, color_key: str) -> str:
    pattern = rf"(?ms)^\s*{re.escape(color_key)}:\s*(.*?)(?=^\s{{4}}[A-Za-z_-]+:|\Z)"
    match = re.search(pattern, section)
    if not match:
        return ""
    return extract_scalar(match.group(1), "use", "")


def extract_inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []
    return [part.strip().strip('"\'') for part in value[1:-1].split(",") if part.strip()]


def load_theme_fallback(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    theme_id = extract_scalar(text, "id")
    if not theme_id:
        return None
    visual_base = extract_section(text, "visual_base")
    palette = extract_section(visual_base, "  color_palette")
    typography = extract_section(visual_base, "  typography")
    illustration = extract_section(visual_base, "  illustration_style")
    decoration = extract_section(text, "decoration_vocabulary")
    closing = re.sub(r"\s+", " ", extract_section(text, "closing_statement").strip())
    mood = extract_inline_list(extract_scalar(visual_base, "mood"))
    deco_names = re.findall(r"(?m)^\s*-\s+name:\s*(.+?)\s*$", decoration)
    support_hexes = re.findall(r"hex:\s*[\"']?(#[0-9A-Fa-f]{6})[\"']?", extract_section(palette, "    support"))
    return {
        "id": theme_id,
        "display_name": extract_scalar(text, "display_name", theme_id),
        "background_color": extract_nested_scalar(visual_base, "background_color", "#F8F8F8"),
        "background_style": extract_nested_scalar(visual_base, "background_style", ""),
        "primary": extract_palette_color(palette, "primary", "#333333"),
        "primary_use": extract_palette_use(palette, "primary"),
        "secondary": extract_palette_color(palette, "secondary", "#666666"),
        "secondary_use": extract_palette_use(palette, "secondary"),
        "accent": extract_palette_color(palette, "accent", "#999999"),
        "accent_use": extract_palette_use(palette, "accent"),
        "support_hexes": support_hexes,
        "typography_heading": compact_text(extract_section(typography, "    heading")).strip(),
        "typography_body": compact_text(extract_section(typography, "    body")).strip(),
        "illustration_default": extract_nested_scalar(illustration, "default", ""),
        "mood": mood,
        "deco_names": [name.strip().strip('"\'') for name in deco_names],
        "closing": closing[:160] if closing else "",
        "theme_kind": "spec",
        "theme_kind_label": "規格 Theme",
    }


def typo_text(t) -> str:
    """typography.heading / body 為結構化 dict（family/weight/size_hint/note）；
    兼容尚未結構化的舊式單行字串。"""
    if isinstance(t, dict):
        main = " ".join(p for p in [t.get("family", ""), t.get("weight", "")] if p)
        extras = "，".join(p for p in [t.get("size_hint", ""), t.get("note", "")] if p)
        return f"{main}（{extras}）" if extras else main
    return t or ""


def rel_deploy_path(path: Path) -> str:
    return path.resolve().relative_to(DEPLOY_DIR.resolve()).as_posix()


def words_for_match(value) -> set[str]:
    text = ""
    if isinstance(value, dict):
        text = " ".join(str(v) for v in value.values())
    elif isinstance(value, list):
        text = " ".join(str(v) for v in value)
    else:
        text = str(value or "")
    text = text.lower()
    ascii_words = re.findall(r"[a-z0-9][a-z0-9-]{1,}", text)
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    words = set()
    for word in ascii_words:
        words.add(word)
        words.update(part for part in word.split("-") if len(part) >= 3)
    for chunk in cjk_chunks:
        words.add(chunk)
        if len(chunk) > 4:
            for idx in range(0, len(chunk) - 1):
                words.add(chunk[idx:idx + 2])
    return words


def compact_text(value) -> str:
    if isinstance(value, dict):
        return " ".join(compact_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(compact_text(v) for v in value)
    return str(value or "")


def hexes_from_text(value) -> list[str]:
    text = compact_text(value)
    return sorted(set(color.upper() for color in re.findall(r"#[0-9A-Fa-f]{6}", text)))


def hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    value = (value or "").strip().lstrip("#")
    if len(value) != 6:
        return None
    try:
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    except ValueError:
        return None


def color_distance(left: str, right: str) -> float:
    left_rgb = hex_to_rgb(left)
    right_rgb = hex_to_rgb(right)
    if not left_rgb or not right_rgb:
        return 999.0
    return sum((a - b) ** 2 for a, b in zip(left_rgb, right_rgb)) ** 0.5


def theme_palette(theme: dict) -> list[str]:
    colors = [
        theme.get("background_color", ""),
        theme.get("primary", ""),
        theme.get("secondary", ""),
        theme.get("accent", ""),
        *theme.get("support_hexes", []),
    ]
    return [color.upper() for color in colors if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(color or ""))]


def palette_match_score(theme: dict, candidate_hexes: list[str]) -> int:
    if not candidate_hexes:
        return 0
    score = 0
    matched = 0
    for color in theme_palette(theme):
        distances = [color_distance(color, candidate) for candidate in candidate_hexes]
        nearest = min(distances) if distances else 999
        if nearest == 0:
            score += 20
            matched += 1
        elif nearest <= 28:
            score += 14
            matched += 1
        elif nearest <= 52:
            score += 8
            matched += 1
    if matched >= 3:
        score += 16
    elif matched >= 2:
        score += 8
    return score


def theme_text_signal(theme: dict, candidate: dict) -> int:
    candidate_text = candidate["text"].lower()
    theme_id = theme.get("id", "")
    score = 0

    if theme_id and theme_id in candidate_text:
        score += 80
    for part in theme_id.split("-"):
        if len(part) >= 4 and part in candidate_text:
            score += 6

    theme_text = " ".join([
        theme.get("display_name", ""),
        theme.get("background_style", ""),
        " ".join(theme.get("mood", [])),
        " ".join(theme.get("deco_names", [])),
        theme.get("illustration_default", ""),
    ])
    score += len(words_for_match(theme_text) & candidate["words"]) * 3
    return score


def theme_id_part_signal(theme: dict, candidate: dict) -> int:
    candidate_text = candidate["text"].lower()
    return sum(
        1
        for part in theme.get("id", "").split("-")
        if len(part) >= 4 and part in candidate_text
    )


def provenance_score(theme: dict, candidate: dict) -> int:
    return palette_match_score(theme, candidate.get("hexes", [])) + theme_text_signal(theme, candidate)


def attach_source_theme(candidates: list[dict], themes: list[dict]) -> None:
    by_id = {theme["id"]: theme for theme in themes}
    for candidate in candidates:
        explicit = candidate.get("explicit_theme_id")
        if explicit in by_id:
            candidate["source_theme_id"] = explicit
            candidate["source_theme_match"] = "yaml-theme-id"
            candidate["source_theme_score"] = 999
            continue

        ranked = sorted(
            ((provenance_score(theme, candidate), theme) for theme in themes),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked:
            continue
        best_score, best_theme = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0
        best_palette_score = palette_match_score(best_theme, candidate.get("hexes", []))
        best_text_signal = theme_text_signal(best_theme, candidate)
        if (
            best_score >= THEME_SOURCE_THRESHOLD
            and best_score - second_score >= 6
            and best_palette_score >= 28
            and best_text_signal >= 6
            and theme_id_part_signal(best_theme, candidate) >= 1
        ):
            candidate["source_theme_id"] = best_theme["id"]
            candidate["source_theme_match"] = "yaml-palette"
            candidate["source_theme_score"] = best_score


def explicit_theme_id_from_text(text: str, theme_ids: set[str]) -> str:
    lowered = text.lower()
    for theme_id in sorted(theme_ids, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9-]){re.escape(theme_id)}(?![a-z0-9-])", lowered):
            return theme_id
    return ""


def preview_for_style_case(path: Path) -> Path | None:
    stem = path.stem
    for ext in IMAGE_EXTS:
        candidate = STYLE_CASE_PREVIEWS_DIR / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def load_style_case_candidates(theme_ids: set[str]) -> list[dict]:
    candidates = []
    for path in sorted(STYLE_CASES_DIR.glob("*.yaml")):
        preview = preview_for_style_case(path)
        if not preview:
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            data = safe_load_yaml(raw)
        except Exception:
            continue
        text = compact_text(data) if data else raw
        candidates.append({
            "image": rel_deploy_path(preview),
            "label": data.get("display_name") or extract_scalar(raw, "display_name", path.stem),
            "source": "style-case",
            "text": f"{path.stem} {text}",
            "words": words_for_match(f"{path.stem} {text}"),
            "hexes": hexes_from_text(text),
            "yaml_path": path.relative_to(ROOT).as_posix(),
            "explicit_theme_id": explicit_theme_id_from_text(f"{path.stem} {text}", theme_ids),
            "layout_id": data.get("layout_id", "") or extract_scalar(raw, "layout_id", ""),
        })
    return candidates


def candidate_score(theme: dict, candidate: dict) -> int:
    if candidate.get("source_theme_id") != theme.get("id"):
        return 0

    theme_text = " ".join([
        theme.get("id", ""),
        theme.get("display_name", ""),
        theme.get("background_style", ""),
        " ".join(theme.get("mood", [])),
        " ".join(theme.get("deco_names", [])),
        theme.get("closing", ""),
        theme.get("illustration_default", ""),
    ])
    theme_words = words_for_match(theme_text)
    score = len(theme_words & candidate["words"]) * 3
    score += int(candidate.get("source_theme_score", 0))
    score += palette_match_score(theme, candidate.get("hexes", []))

    if candidate["source"] == "style-case":
        score += 12
    if candidate.get("source_theme_match") == "yaml-theme-id":
        score += 80
    return score


def attach_theme_previews(themes: list[dict]) -> None:
    theme_ids = {theme["id"] for theme in themes}
    candidates = load_style_case_candidates(theme_ids)
    attach_source_theme(candidates, themes)
    used_images: set[str] = set()
    for theme in themes:
        for ext in IMAGE_EXTS:
            generated = THEME_PREVIEWS_DIR / f"{theme['id']}-cards-1-plus-3-codex{ext}"
            if generated.exists():
                theme["preview_image"] = rel_deploy_path(generated)
                theme["preview_label"] = f"1+3 新圖：{theme['display_name']}"
                theme["preview_source"] = "theme-preview-generated"
                theme["preview_match_score"] = 1000
                theme["preview_source_theme"] = theme["id"]
                theme["preview_yaml_path"] = f"artifacts/generated-prompts/theme-previews/{theme['id']}.cards-1-plus-3.assembled.yaml"
                theme["preview_match_method"] = "generated-from-theme-yaml"
                break
        if theme.get("preview_image"):
            continue
        ranked = sorted(
            ((candidate_score(theme, candidate), candidate) for candidate in candidates),
            key=lambda item: item[0],
            reverse=True,
        )
        selected = None
        for score, candidate in ranked:
            if score <= 0:
                break
            if candidate["image"] not in used_images:
                selected = (score, candidate)
                break
        if not selected and ranked and ranked[0][0] > 0:
            selected = ranked[0]
        if not selected:
            continue
        score, candidate = selected
        used_images.add(candidate["image"])
        theme["preview_image"] = candidate["image"]
        theme["preview_label"] = f"YAML配對：{candidate['label']}"
        theme["preview_source"] = candidate["source"]
        theme["preview_match_score"] = score
        theme["preview_source_theme"] = candidate.get("source_theme_id", "")
        theme["preview_yaml_path"] = candidate.get("yaml_path", "")
        theme["preview_match_method"] = candidate.get("source_theme_match", "")


def load_theme(path: Path) -> dict | None:
    try:
        if not yaml:
            return load_theme_fallback(path)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "id" not in data:
            return None

        vb = data.get("visual_base", {}) or {}
        cp = vb.get("color_palette", {}) or {}
        support = cp.get("support", []) or []
        support_hexes = [s.get("hex", "") for s in (support if isinstance(support, list) else []) if s.get("hex")]

        mood_raw = vb.get("mood", []) or []
        mood = mood_raw if isinstance(mood_raw, list) else [str(mood_raw)]

        dv = data.get("decoration_vocabulary", []) or []
        deco_names = [d.get("name", "") for d in (dv if isinstance(dv, list) else []) if d.get("name")]

        closing = data.get("closing_statement", "") or ""
        if hasattr(closing, "strip"):
            closing = re.sub(r"\s+", " ", closing.strip())

        return {
            "id": data.get("id", ""),
            "display_name": data.get("display_name", data.get("id", "")),
            "background_color": vb.get("background_color", "#F8F8F8"),
            "background_style": vb.get("background_style", ""),
            "primary": cp.get("primary", {}).get("hex", "#333333"),
            "primary_use": cp.get("primary", {}).get("use", ""),
            "secondary": cp.get("secondary", {}).get("hex", "#666666"),
            "secondary_use": cp.get("secondary", {}).get("use", ""),
            "accent": cp.get("accent", {}).get("hex", "#999999"),
            "accent_use": cp.get("accent", {}).get("use", ""),
            "support_hexes": support_hexes,
            "typography_heading": typo_text(vb.get("typography", {}).get("heading", "")),
            "typography_body": typo_text(vb.get("typography", {}).get("body", "")),
            "illustration_default": (vb.get("illustration_style", {}) or {}).get("default", ""),
            "mood": mood,
            "deco_names": deco_names,
            "closing": closing[:160] if closing else "",
            "theme_kind": "spec",
            "theme_kind_label": "規格 Theme",
        }
    except Exception as e:
        print(f"  skip {path.name}: {e}")
        return None


def main() -> None:
    theme_files = sorted(THEMES_DIR.glob("*.yaml"))
    theme_files = [f for f in theme_files if f.name != "README.md"]

    themes = []
    for path in theme_files:
        if path.stem == "README":
            continue
        theme = load_theme(path)
        if theme:
            themes.append(theme)
            print(f"  ok  {theme['id']} — {theme['display_name']}")

    attach_theme_previews(themes)
    registry = load_preset_registry(check_gallery=False)
    registry_entries = published_entries(registry)
    authored_ids = {
        row["id"] for row in registry_entries if row["gallery_source"] == "theme-lab"
    }
    curated_ids = {
        row["id"] for row in registry_entries if row["gallery_source"] == "reusable-preset"
    }
    preset_by_id = {
        row["id"]: row
        for row in (
            load_authored_html_preset_themes(authored_ids)
            + load_curated_html_preset_themes(curated_ids)
        )
    }
    missing = [row["id"] for row in registry_entries if row["id"] not in preset_by_id]
    extra = sorted(set(preset_by_id) - {row["id"] for row in registry_entries})
    if missing or extra:
        raise ValueError(f"Preset registry/Gallery source mismatch: missing={missing} extra={extra}")
    for registry_row in registry_entries:
        preset = preset_by_id[registry_row["id"]]
        preset["display_name"] = registry_row["display_name"]
        preset["preset_registry_status"] = registry_row["gallery_status"]
        preset["preset_capabilities"] = list(registry_row["capabilities"])
        gallery_html_artifact = registry_row.get("gallery_html_artifact")
        if gallery_html_artifact:
            artifact_path = ROOT / gallery_html_artifact
            markup = artifact_path.read_text(encoding="utf-8")
            preset["html_url"] = registry_row["gallery_html_url"]
            preset["slide_count"] = len(re.findall(
                r'<section\b[^>]*\bclass=(["\'])[^"\']*\bslide\b[^"\']*\1',
                markup,
                flags=re.IGNORECASE,
            ))
            preset["preview_label"] = f"HTML Preset · {preset['slide_count']} 頁"
        themes.append(preset)

    payload = json.dumps(themes, ensure_ascii=False, indent=2)
    js = f"window.THEME_GALLERY = {payload};\n"
    JS_OUT.write_text(js, encoding="utf-8")
    print(f"\n完成：{len(themes)} 個 theme → {JS_OUT}")


if __name__ == "__main__":
    main()
