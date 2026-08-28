#!/usr/bin/env python3
"""Analyze public design-system pages without retaining their copied assets/content.

The first supported corpus is Refero Styles. The script:
1. reads the public styles sitemap;
2. visits each public style page at a polite, bounded rate;
3. extracts only normalized fields, counts, and technique flags;
4. writes aggregate research artifacts, never raw HTML, images, or copied DESIGN.md.

This is research tooling, not a runtime dependency of the presentation renderer.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime as dt
import html
import json
import random
import re
import statistics
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup


DEFAULT_SITEMAP = "https://styles.refero.design/sitemaps/styles.xml"
DEFAULT_OUTPUT_DIR = Path("artifacts/research/design-intelligence")
USER_AGENT = (
    "SlideDesignResearchBot/1.0 "
    "(public design-system field study; no image or asset downloads)"
)

FIELD_RULES: OrderedDict[str, tuple[str, ...]] = OrderedDict(
    [
        ("identity", ("style reference", "theme", "brand")),
        ("colors", ("color", "palette", "colour")),
        ("typography", ("typography", "type scale", "font")),
        ("spacing", ("spacing", "density", "rhythm")),
        ("shape", ("shape", "radius", "corner")),
        ("elevation", ("elevation", "shadow", "depth")),
        ("surfaces", ("surface", "canvas", "background")),
        ("layout", ("layout", "grid", "composition")),
        ("components", ("component",)),
        ("imagery", ("imagery", "photography", "illustration", "image")),
        ("iconography", ("iconography", "icon")),
        ("motion", ("motion", "animation", "transition")),
        ("guidelines", ("guideline", "usage", "principle")),
        ("do_rules", ("do",)),
        ("dont_rules", ("don't", "dont", "do not")),
        ("accessibility", ("accessibility", "contrast")),
        ("voice", ("voice", "tone", "copywriting")),
        ("agent_prompt", ("agent prompt", "prompt guide")),
        ("implementation", ("quick start", "css variables", "tailwind", "design tokens")),
    ]
)

TECHNIQUE_RULES: OrderedDict[str, tuple[str, ...]] = OrderedDict(
    [
        ("monochrome", ("monochrome", "achromatic", "black and white")),
        ("single_accent", ("single accent", "one accent", "only chromatic")),
        ("subtle_gradient", ("subtle gradient", "faint gradient", "soft gradient")),
        ("strong_gradient", ("gradient",)),
        ("pattern", ("pattern", "grid texture", "dot grid", "grain", "noise")),
        ("hairline", ("hairline", "0.5px", "1px border", "thin rule")),
        ("flat_no_shadow", ("no shadow", "zero shadow", "without shadow")),
        (
            "soft_shadow",
            (
                "soft shadow",
                "subtle shadow",
                "ambient shadow",
                "barely-there shadow",
                "barely there shadow",
            ),
        ),
        ("heavy_shadow", ("heavy shadow", "dramatic shadow", "strong shadow")),
        ("serif_sans_pair", ("serif/sans", "serif and sans", "serif paired")),
        ("single_typeface", ("single typeface", "one typeface", "single font")),
        ("oversized_type", ("oversized type", "massive type", "monumental headline")),
        ("tight_tracking", ("tight tracking", "negative tracking", "letter-spacing")),
        ("generous_whitespace", ("generous whitespace", "negative space", "breathing room")),
        ("dense_layout", ("dense", "compact")),
        ("asymmetric_layout", ("asymmetric", "asymmetrical")),
        ("strict_grid", ("strict grid", "rigid grid", "column grid")),
        ("full_bleed", ("full-bleed", "full bleed", "bleeds to the edge")),
        ("cropped_edge", ("cropped by", "crop at the edge", "viewport edge")),
        ("cards", ("card", "panel")),
        ("pill_geometry", ("pill", "999px", "9999px")),
        ("sharp_geometry", ("sharp corner", "square corner", "0px radius")),
        ("rounded_geometry", ("rounded", "radius")),
        ("photography_led", ("photography", "photographic", "photo-led")),
        ("illustration_led", ("illustration", "illustrated")),
        ("product_ui_led", ("product ui", "dashboard", "interface screenshot")),
        ("type_led", ("typography carries", "type does", "type is the")),
        ("decorative_lines", ("decorative line", "rule", "stroke")),
        ("decorative_geometry", ("geometric", "geometry", "circle", "orb", "blob")),
        ("material_texture", ("paper", "vellum", "linen", "plaster", "grain")),
        ("dark_canvas", ("near-black", "black canvas", "dark canvas", "midnight")),
        ("light_canvas", ("white canvas", "light canvas", "paper-white", "off-white")),
    ]
)

CANONICAL_HEADING_ALIASES = {
    "tokens colors": "colors",
    "tokens typography": "typography",
    "tokens spacing shapes": "spacing_shape",
    "spacing shape": "spacing_shape",
    "spacing shapes": "spacing_shape",
    "border radius": "shape",
    "type scale": "typography",
    "agent prompt guide": "agent_prompt",
    "quick start": "implementation",
    "css custom properties": "implementation",
    "css variables": "implementation",
    "tailwind v4": "implementation",
    "design tokens": "implementation",
    "do": "do_rules",
    "dont": "dont_rules",
    "do not": "dont_rules",
}

_REQUEST_LOCK = threading.Lock()
_NEXT_REQUEST_AT = 0.0


@dataclasses.dataclass(frozen=True)
class SitemapItem:
    url: str
    last_modified: str | None


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def request_bytes(url: str, *, timeout: float, retries: int, delay: float) -> bytes:
    global _NEXT_REQUEST_AT

    error: Exception | None = None
    for attempt in range(retries + 1):
        with _REQUEST_LOCK:
            now = time.monotonic()
            if now < _NEXT_REQUEST_AT:
                time.sleep(_NEXT_REQUEST_AT - now)
            _NEXT_REQUEST_AT = time.monotonic() + max(delay, 0.0)

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "identity",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 4) + random.uniform(0.05, 0.25))

    raise RuntimeError(f"Failed to fetch {url}: {error}")


def parse_sitemap(payload: bytes) -> list[SitemapItem]:
    root = ET.fromstring(payload)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    items: list[SitemapItem] = []
    for node in root.findall("sm:url", ns):
        loc = node.findtext("sm:loc", default="", namespaces=ns).strip()
        last_modified = node.findtext("sm:lastmod", default="", namespaces=ns).strip()
        if "/style/" in loc:
            items.append(SitemapItem(loc, last_modified or None))
    return items


def normalize_heading(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"[`*_#|]", " ", value)
    value = value.replace("’", "'").replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value).strip().lower()
    value = re.sub(r"^tokens\s*[-:]\s*", "tokens ", value)
    value = value.rstrip(":")
    compact = re.sub(r"[^a-z0-9']+", " ", value).strip()
    return CANONICAL_HEADING_ALIASES.get(compact, compact)


def extract_markdown_reference(soup: BeautifulSoup) -> str:
    candidates: list[str] = []
    for selector in ("pre", "code"):
        for node in soup.select(selector):
            text = node.get_text("\n", strip=False)
            if "Style Reference" in text or "## Tokens" in text:
                candidates.append(text)
    if candidates:
        return max(candidates, key=len)

    script_candidates: list[str] = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text("", strip=False)
        if "Style Reference" in text and "Tokens" in text:
            text = bytes(text, "utf-8").decode("unicode_escape", errors="ignore")
            script_candidates.append(text)
    return max(script_candidates, key=len) if script_candidates else ""


def extract_headings(soup: BeautifulSoup, reference_text: str) -> list[str]:
    if reference_text:
        headings = [
            normalize_heading(match.group(1))
            for match in re.finditer(r"(?m)^#{1,4}\s+(.+?)\s*$", reference_text)
        ]
    else:
        headings = [
            normalize_heading(node.get_text(" ", strip=True))
            for node in soup.select("main h1,main h2")
        ]
    return sorted({heading for heading in headings if heading})


def field_presence(headings: Iterable[str], searchable_text: str) -> dict[str, bool]:
    joined_headings = "\n".join(headings)
    values: dict[str, bool] = {}
    for field, signals in FIELD_RULES.items():
        if field in {"do_rules", "dont_rules"}:
            values[field] = any(
                field in headings or signal in joined_headings for signal in signals
            )
        else:
            values[field] = any(
                signal in joined_headings or f"## {signal}" in searchable_text
                for signal in signals
            )
    return values


def count_markdown_list_items(reference_text: str, section_names: tuple[str, ...]) -> int:
    if not reference_text:
        return 0
    section_pattern = "|".join(re.escape(name) for name in section_names)
    match = re.search(
        rf"(?ims)^###?\s+(?:{section_pattern})\s*$([\s\S]*?)(?=^##{{1,4}}\s+|\Z)",
        reference_text,
    )
    if not match:
        return 0
    return len(re.findall(r"(?m)^\s*[-*]\s+", match.group(1)))


def count_components(reference_text: str) -> int:
    if not reference_text:
        return 0
    match = re.search(
        r"(?ims)^##\s+Components?\s*$([\s\S]*?)(?=^##\s+|\Z)",
        reference_text,
    )
    if not match:
        return 0
    return len(re.findall(r"(?m)^###\s+[^#\n]+$", match.group(1)))


def extract_markdown_section(reference_text: str, names: tuple[str, ...]) -> str:
    if not reference_text:
        return ""
    section_pattern = "|".join(re.escape(name) for name in names)
    match = re.search(
        rf"(?ims)^##\s+(?:{section_pattern})\s*$([\s\S]*?)(?=^##\s+|\Z)",
        reference_text,
    )
    return match.group(1) if match else ""


def positive_design_text(reference_text: str, visible_text: str) -> str:
    if not reference_text:
        return visible_text.lower()
    opening = re.split(r"(?m)^##\s+", reference_text, maxsplit=1)[0]
    selected = [
        extract_markdown_section(reference_text, names)
        for names in (
            ("Imagery",),
            ("Layout",),
            ("Surfaces",),
            ("Iconography", "Icons"),
            ("Motion", "Animation"),
        )
    ]
    return (opening + "\n" + "\n".join(selected)).lower()


def extract_brand(soup: BeautifulSoup, reference_text: str, url: str) -> str:
    match = re.search(r"(?m)^#\s+(.+?)\s+[-—]\s+Style Reference\s*$", reference_text)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    h1 = soup.find("h1")
    if h1:
        value = h1.get_text(" ", strip=True)
        value = re.sub(r"\s+design system\s*$", "", value, flags=re.I)
        if value:
            return value
    return url.rstrip("/").split("/")[-1]


def analyze_style_page(item: SitemapItem, payload: bytes) -> dict:
    soup = BeautifulSoup(payload, "html.parser")
    reference_text = extract_markdown_reference(soup)
    visible_text = soup.get_text("\n", strip=True)
    searchable_text = (reference_text or visible_text).lower()
    design_text = positive_design_text(reference_text, visible_text)
    headings = extract_headings(soup, reference_text)

    theme_match = re.search(
        r"(?:\*\*)?theme\s*:?\s*(?:\*\*)?\s*(?:\n\s*)?(light|dark|mixed)",
        reference_text + "\n" + visible_text,
        flags=re.I,
    )
    theme = theme_match.group(1).lower() if theme_match else "unknown"

    techniques = {
        name: any(signal in design_text for signal in signals)
        for name, signals in TECHNIQUE_RULES.items()
    }
    techniques["serif_sans_pair"] = techniques["serif_sans_pair"] or bool(
        re.search(r"serif[^.\n]{0,100}\bsans\b|\bsans\b[^.\n]{0,100}serif", design_text)
    )
    if re.search(r"\b(?:no|without|zero)\s+(?:decorative\s+)?gradients?\b", design_text):
        techniques["subtle_gradient"] = False
        techniques["strong_gradient"] = False
    if re.search(r"\b(?:no|without|zero)\s+(?:drop\s+)?shadows?\b", design_text):
        techniques["flat_no_shadow"] = True
        techniques["soft_shadow"] = False
        techniques["heavy_shadow"] = False
    if re.search(r"\b(?:no|without|zero)\s+cards?\b", design_text):
        techniques["cards"] = False
    if re.search(r"\b(?:no|without|zero)\s+photograph(?:y|s)?\b", design_text):
        techniques["photography_led"] = False
    if re.search(r"\b(?:no|without|zero)\s+illustrations?\b", design_text):
        techniques["illustration_led"] = False
    if techniques["strong_gradient"] and techniques["subtle_gradient"]:
        techniques["strong_gradient"] = False

    colors = sorted(set(re.findall(r"#[0-9a-fA-F]{6}\b", reference_text)))
    css_fonts = sorted(
        set(re.findall(r"--font-([a-z0-9_-]+)", reference_text, flags=re.I))
    )
    spacing_values = [
        int(value)
        for value in re.findall(r"--spacing-[a-z0-9_-]+\s*:\s*(\d+)px", reference_text)
    ]
    radius_values = [
        int(value)
        for value in re.findall(
            r"(?:radius|rounded|corner)[^;\n]{0,50}?(\d+)px",
            reference_text,
            flags=re.I,
        )
    ]

    return {
        "style_id": item.url.rstrip("/").split("/")[-1],
        "url": item.url,
        "last_modified": item.last_modified,
        "brand": extract_brand(soup, reference_text, item.url),
        "theme": theme,
        "fields": field_presence(headings, searchable_text),
        "metrics": {
            "color_token_count": len(colors),
            "font_token_count": len(css_fonts),
            "spacing_token_count": len(set(spacing_values)),
            "radius_value_count": len(set(radius_values)),
            "component_count": count_components(reference_text),
            "do_rule_count": count_markdown_list_items(reference_text, ("Do",)),
            "dont_rule_count": count_markdown_list_items(
                reference_text, ("Don't", "Dont", "Do not")
            ),
        },
        "techniques": techniques,
    }


def derive_archetypes(record: dict) -> list[str]:
    t = record["techniques"]
    archetypes: list[str] = []
    if (
        t["light_canvas"]
        and t["material_texture"]
        and t["generous_whitespace"]
        and (t["serif_sans_pair"] or t["type_led"])
    ):
        archetypes.append("editorial-paper")
    if (
        t["dark_canvas"]
        and t["hairline"]
        and t["tight_tracking"]
        and t["single_accent"]
    ):
        archetypes.append("precision-dark")
    if t["type_led"] and t["flat_no_shadow"] and t["monochrome"]:
        archetypes.append("flat-typographic")
    if (
        t["light_canvas"]
        and t["cards"]
        and t["rounded_geometry"]
        and t["soft_shadow"]
    ):
        archetypes.append("soft-product")
    if (
        t["dark_canvas"]
        and (t["strong_gradient"] or t["subtle_gradient"])
        and t["full_bleed"]
    ):
        archetypes.append("immersive-atmospheric")
    if t["photography_led"] and t["full_bleed"] and t["generous_whitespace"]:
        archetypes.append("photographic-editorial")
    if t["illustration_led"] and not t["photography_led"]:
        archetypes.append("illustration-led")
    if t["product_ui_led"] and t["strict_grid"] and t["dense_layout"]:
        archetypes.append("grid-data")
    if not archetypes:
        archetypes.append("unclassified")
    return archetypes


def summarize(records: list[dict], errors: list[dict], total_urls: int) -> dict:
    field_counts: Counter[str] = Counter()
    technique_counts: Counter[str] = Counter()
    theme_counts: Counter[str] = Counter()
    archetype_counts: Counter[str] = Counter()
    theme_technique_counts: dict[str, Counter[str]] = {}

    metric_values: dict[str, list[int]] = {}
    for record in records:
        theme_counts[record["theme"]] += 1
        archetype_counts.update(derive_archetypes(record))
        theme_counter = theme_technique_counts.setdefault(record["theme"], Counter())
        for field, present in record["fields"].items():
            if present:
                field_counts[field] += 1
        for technique, present in record["techniques"].items():
            if present:
                technique_counts[technique] += 1
                theme_counter[technique] += 1
        for metric, value in record["metrics"].items():
            metric_values.setdefault(metric, []).append(value)

    success_count = len(records)
    denominator = max(success_count, 1)

    def with_rate(counter: Counter[str]) -> list[dict]:
        return [
            {
                "name": name,
                "count": count,
                "rate": round(count / denominator, 4),
            }
            for name, count in counter.most_common()
        ]

    metric_summary = {}
    for metric, values in metric_values.items():
        metric_summary[metric] = {
            "min": min(values),
            "median": statistics.median(values),
            "mean": round(statistics.fmean(values), 2),
            "max": max(values),
        }

    technique_names = list(TECHNIQUE_RULES)
    cooccurrence: list[dict] = []
    minimum_joint = max(5, round(success_count * 0.02))
    for index, left in enumerate(technique_names):
        left_count = technique_counts[left]
        if not left_count:
            continue
        for right in technique_names[index + 1 :]:
            right_count = technique_counts[right]
            if not right_count:
                continue
            joint = sum(
                1
                for record in records
                if record["techniques"][left] and record["techniques"][right]
            )
            if joint < minimum_joint:
                continue
            joint_rate = joint / denominator
            expected = (left_count / denominator) * (right_count / denominator)
            lift = joint_rate / expected if expected else 0.0
            if lift < 1.1:
                continue
            cooccurrence.append(
                {
                    "left": left,
                    "right": right,
                    "count": joint,
                    "joint_rate": round(joint_rate, 4),
                    "lift": round(lift, 3),
                }
            )
    cooccurrence.sort(key=lambda item: (-item["lift"], -item["count"]))

    theme_technique_frequency = {}
    for theme, counter in theme_technique_counts.items():
        theme_denominator = max(theme_counts[theme], 1)
        theme_technique_frequency[theme] = [
            {
                "name": name,
                "count": count,
                "rate": round(count / theme_denominator, 4),
            }
            for name, count in counter.most_common()
        ]

    return {
        "generated_at": utc_now(),
        "source": "Refero Styles public style pages",
        "sitemap": DEFAULT_SITEMAP,
        "total_urls": total_urls,
        "success_count": success_count,
        "error_count": len(errors),
        "coverage_rate": round(success_count / max(total_urls, 1), 4),
        "theme_distribution": dict(theme_counts.most_common()),
        "archetype_distribution": dict(archetype_counts.most_common()),
        "field_frequency": with_rate(field_counts),
        "technique_frequency": with_rate(technique_counts),
        "technique_cooccurrence": cooccurrence[:80],
        "theme_technique_frequency": theme_technique_frequency,
        "metric_summary": metric_summary,
        "errors": errors,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_markdown_report(path: Path, summary: dict) -> None:
    lines = [
        "# 公開設計系統欄位研究：Refero Styles",
        "",
        f"- 產生時間：{summary['generated_at']}",
        f"- Sitemap 公開設計頁：{summary['total_urls']}",
        f"- 成功分析：{summary['success_count']}",
        f"- 失敗：{summary['error_count']}",
        f"- 覆蓋率：{summary['coverage_rate']:.1%}",
        "",
        "本研究只保留正規化欄位、計數與設計手法標記；不保存原始 HTML、圖片、",
        "品牌資產、DESIGN.md 全文或第三方元件程式碼。",
        "",
        "## 共通欄位覆蓋率",
        "",
        "| 欄位 | 設計數 | 覆蓋率 |",
        "|---|---:|---:|",
    ]
    for item in summary["field_frequency"]:
        lines.append(f"| `{item['name']}` | {item['count']} | {item['rate']:.1%} |")

    lines.extend(
        [
            "",
            "## 常見設計手法",
            "",
            "| 手法 | 設計數 | 覆蓋率 |",
            "|---|---:|---:|",
        ]
    )
    for item in summary["technique_frequency"]:
        lines.append(f"| `{item['name']}` | {item['count']} | {item['rate']:.1%} |")

    lines.extend(
        [
            "",
            "## 主題分布",
            "",
            "| 主題 | 設計數 |",
            "|---|---:|",
        ]
    )
    for name, count in summary["theme_distribution"].items():
        lines.append(f"| `{name}` | {count} |")

    lines.extend(
        [
            "",
            "## 衍生設計 Archetype",
            "",
            "這些名稱是本專案對手法共現關係的重新命名，不是來源網站的分類。",
            "",
            "| Archetype | 設計數 |",
            "|---|---:|",
        ]
    )
    for name, count in summary["archetype_distribution"].items():
        lines.append(f"| `{name}` | {count} |")

    lines.extend(
        [
            "",
            "## 高關聯手法組合",
            "",
            "Lift 大於 1 表示兩種手法同時出現的機率高於獨立隨機預期。",
            "",
            "| 手法 A | 手法 B | 共同出現 | Lift |",
            "|---|---|---:|---:|",
        ]
    )
    for item in summary["technique_cooccurrence"][:30]:
        lines.append(
            f"| `{item['left']}` | `{item['right']}` | {item['count']} | {item['lift']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## 研究限制",
            "",
            "- 統計只反映公開 sitemap 在本次執行時可存取的頁面。",
            "- 關鍵字標記代表設計文件提及該手法，不等同於人工視覺評分。",
            "- 欄位頻率用來建立我們自己的設計語法，不代表直接複製任何來源。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sitemap", default=DEFAULT_SITEMAP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--single-url", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.workers < 1 or args.workers > 8:
        raise SystemExit("--workers must be between 1 and 8")

    if args.single_url:
        items = [SitemapItem(args.single_url, None)]
        total_urls = 1
    else:
        sitemap = request_bytes(
            args.sitemap,
            timeout=args.timeout,
            retries=args.retries,
            delay=args.delay,
        )
        items = parse_sitemap(sitemap)
        total_urls = len(items)
        if args.max_items > 0:
            items = items[: args.max_items]

    records: list[dict] = []
    errors: list[dict] = []

    def process(item: SitemapItem) -> dict:
        payload = request_bytes(
            item.url,
            timeout=args.timeout,
            retries=args.retries,
            delay=args.delay,
        )
        return analyze_style_page(item, payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_item = {executor.submit(process, item): item for item in items}
        completed = 0
        for future in concurrent.futures.as_completed(future_to_item):
            item = future_to_item[future]
            completed += 1
            try:
                records.append(future.result())
            except Exception as exc:  # keep the corpus run useful when a page fails
                errors.append({"url": item.url, "error": str(exc)})
            if completed % 50 == 0 or completed == len(items):
                print(
                    f"processed={completed}/{len(items)} "
                    f"success={len(records)} errors={len(errors)}",
                    flush=True,
                )

    records.sort(key=lambda record: record["style_id"])
    summary = summarize(records, errors, total_urls if not args.max_items else len(items))

    write_json(args.output_dir / "refero-style-records.json", records)
    write_json(args.output_dir / "refero-style-summary.json", summary)
    write_markdown_report(args.output_dir / "refero-style-summary.md", summary)

    print(f"records={args.output_dir / 'refero-style-records.json'}")
    print(f"summary={args.output_dir / 'refero-style-summary.json'}")
    print(f"report={args.output_dir / 'refero-style-summary.md'}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
