"""Pattern-only authored HTML Theme system.

The public Theme Lab deliberately separates four decisions:

1. semantic composition (contrast, flow, metrics, ...)
2. composition variant (split, stack, rail, orbit, ...)
3. title/content placement
4. Theme pattern and palette

All slide-content decoration is CSS text, pattern, color, or elementary
geometry.  The module does not load photos, illustrations, icons, SVG files,
or raster assets.
"""

from __future__ import annotations

import hashlib
from typing import Any


GOOGLE_FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Noto+Sans+TC:wght@400;500;600;700;800;900'
    '&family=Noto+Serif+TC:wght@500;600;700;800;900'
    '&family=Roboto+Mono:wght@500;600;700'
    '&display=swap" rel="stylesheet">'
)


REDESIGN_BASE_CSS = r"""
*{box-sizing:border-box}
html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#111}
body{font-family:var(--font-body);color:var(--ink)}
#stage{width:1920px;height:1080px}
.slide{
  --hx:36px;--hy:16px;--hw:1510px;--ix:36px;--iy:112px;--iw:1480px;
  --cx:36px;--cy:220px;--cw:1656px;--ch:610px;--cm:864px;
  position:absolute;inset:0;width:1920px;height:1080px;display:none;overflow:hidden;
  background-color:var(--bg);color:var(--ink)
}
.slide.active{display:block}
.slide:before,.slide:after{pointer-events:none}
.content{position:absolute;left:96px;top:96px;width:1728px;height:888px;z-index:2}
.el{position:absolute;padding:0;border:0;background:transparent;overflow:visible}
.el[data-edit-structure="module"]{isolation:isolate}
.scene{isolation:isolate}
.scene-header{z-index:4}.scene-content{z-index:3;overflow:visible}
.scene [data-edit-position="absolute"]{position:absolute;margin:0;padding:0}
.scene [data-edit-position="flow"]{position:relative;inset:auto;width:auto;height:auto;margin:0}
.scene [data-edit-position="absolute"][data-edit-layer="text"][data-edit-vertical-align="center"]{
  display:flex;flex-direction:column;justify-content:center;align-items:stretch
}
.scene [data-edit-structure="module"][data-edit-composite]>[data-edit-layer="background"]{
  position:absolute!important;inset:0!important;width:auto!important;height:auto!important;
  margin:0!important;padding:0!important
}
.folio{
  position:absolute;left:30px;right:30px;bottom:22px;display:flex;justify-content:space-between;
  z-index:6;font:600 36px/1 var(--font-utility);letter-spacing:.08em;
  color:var(--muted);pointer-events:none
}

/* Title/content placement is a real layout decision, not a scale transform. */
.slide[data-header-mode="top"]{
  --hx:36px;--hy:14px;--hw:1580px;--ix:38px;--iy:160px;--iw:1510px;
  --cx:36px;--cy:250px;--cw:1656px;--ch:584px;--cm:864px
}
.slide[data-header-mode="band"]{
  --hx:36px;--hy:18px;--hw:980px;--ix:1080px;--iy:25px;--iw:610px;
  --cx:36px;--cy:166px;--cw:1656px;--ch:668px;--cm:864px
}
.slide[data-header-mode="side-left"]{
  --hx:34px;--hy:82px;--hw:430px;--ix:36px;--iy:322px;--iw:430px;
  --cx:560px;--cy:42px;--cw:1132px;--ch:792px;--cm:1126px
}
.slide[data-header-mode="side-right"]{
  --hx:1230px;--hy:82px;--hw:462px;--ix:1232px;--iy:322px;--iw:450px;
  --cx:36px;--cy:42px;--cw:1120px;--ch:792px;--cm:596px
}
.scene-title{
  left:var(--hx);top:var(--hy);width:var(--hw);
  font:800 62px/1.12 var(--font-display);letter-spacing:-.04em;color:var(--ink)
}
.scene-intro{
  left:var(--ix);top:var(--iy);width:var(--iw);
  font:500 36px/1.42 var(--font-body);letter-spacing:-.015em;color:var(--muted)
}
.slide:is([data-header-mode="top"],[data-header-mode="side-left"],[data-header-mode="side-right"]) .scene-header{
  display:flex;align-items:flex-start;box-sizing:border-box;
  padding:var(--hy) 0 0 var(--hx)!important
}
.slide:is([data-header-mode="top"],[data-header-mode="side-left"],[data-header-mode="side-right"]) .scene-title-stack{
  position:relative;display:flex;flex-direction:column;align-items:flex-start;gap:.35em;
  width:max-content;max-width:var(--hw)
}
.slide:is([data-header-mode="top"],[data-header-mode="side-left"],[data-header-mode="side-right"]) .scene-title-stack>[data-title-stack-item]{
  position:relative!important;inset:auto!important;margin-top:0!important;margin-bottom:0!important
}
.slide:is([data-header-mode="top"],[data-header-mode="side-left"],[data-header-mode="side-right"]) .scene-title-stack>.scene-title{
  width:max-content!important;max-width:var(--hw)!important;margin-left:0!important;margin-right:0!important
}
.slide:is([data-header-mode="top"],[data-header-mode="side-left"],[data-header-mode="side-right"]) .scene-title-stack>.scene-intro{
  width:max-content!important;max-width:var(--iw)!important;
  margin-left:0!important;margin-right:0!important
}
.slide[data-header-mode^="side"] .scene-title{font-size:72px;line-height:1.08}
.slide[data-header-mode^="side"] .scene-intro{font-size:36px;line-height:1.52}
.slide[data-header-mode="band"] .scene-title{font-size:58px}
.slide[data-header-mode="band"] .scene-intro{font-size:36px}

.index-list,.contrast-grid,.column-grid,.flow-list,.matrix-items,.ledger,
.timeline-list,.map-nodes,.metric-grid{
  position:absolute;left:var(--cx);top:var(--cy);width:var(--cw);height:var(--ch)
}
.column-slot,.metric-slot{position:relative;min-width:0;min-height:0}
.column-slot>.column-item,.metric-slot>.metric-item{
  position:relative!important;width:100%;height:100%
}
.index-item,.column-item,.flow-item,.matrix-item,.timeline-item,.map-node,
.metric-item,.contrast-panel,.ledger-row,.map-center{position:relative}
.index-label,.column-tag,.flow-label,.matrix-q,.timeline-time,.contrast-label{
  font:700 36px/1 var(--font-utility);letter-spacing:.08em;color:var(--accent)
}
.index-title,.column-title,.flow-title,.matrix-title,.timeline-title,.map-label,
.metric-label,.contrast-title,.map-center-title{
  font:800 40px/1.18 var(--font-display);letter-spacing:-.03em;color:var(--ink)
}
.index-body,.column-body,.flow-body,.matrix-body,.timeline-body,.map-body,
.metric-meaning,.contrast-lead,.map-center-body,.item-copy{
  font:500 36px/1.4 var(--font-body);letter-spacing:-.015em;color:var(--muted);
  text-wrap:balance;line-break:strict;word-break:auto-phrase
}
.scene-footer{
  left:var(--cx);bottom:0;width:var(--cw);min-height:58px;
  padding:14px 20px!important;border:0!important;background:transparent!important;font:600 36px/1.25 var(--font-body);color:var(--ink);display:flex!important;align-items:center;justify-content:center
}
.scene-footer-bg{position:absolute!important;left:0!important;top:0!important;width:100%!important;height:100%!important;background:var(--footer-background,transparent);border:var(--footer-border,0);border-top:var(--footer-border-top,1px solid var(--line));pointer-events:auto}
.scene-footer-text{position:relative!important;width:100%;font:inherit;color:inherit;text-align:inherit}

/* Content surfaces vary independently. They never force every item into a card. */
.slide[data-surface-mode="open"] :is(
  .index-item,.column-item,.flow-item,.matrix-item,.timeline-item,.map-node,
  .metric-item,.contrast-panel,.map-center
){background:transparent;border-color:color-mix(in srgb,var(--line) 62%,transparent)}
.slide[data-surface-mode="marker"] :is(
  .index-item,.column-item,.flow-item,.matrix-item,.timeline-item,.map-node,
  .metric-item,.contrast-panel
){background:linear-gradient(90deg,var(--accent) 0 8px,transparent 8px);padding-left:28px!important}
.slide[data-surface-mode="banded"] :is(
  .index-item,.column-item,.flow-item,.matrix-item,.timeline-item,.map-node,
  .metric-item,.contrast-panel
){background:linear-gradient(90deg,color-mix(in srgb,var(--surface) 84%,transparent) 0 92%,transparent 92%)}
.slide[data-surface-mode="soft-field"] :is(
  .index-item,.column-item,.flow-item,.matrix-item,.timeline-item,.map-node,
  .metric-item,.contrast-panel,.map-center
){background:color-mix(in srgb,var(--surface) 78%,transparent);border-radius:var(--soft-radius)}
.column-item-bg,.metric-item-bg,.map-node-bg,.map-center-bg,
.thesis-note-bg,.ledger-sheet-bg,.ledger-row-bg{
  position:absolute!important;inset:0!important;width:100%;height:100%;
  border-radius:inherit;background:transparent;pointer-events:none;z-index:0
}
.thesis-note>*:not(.thesis-note-bg),.ledger>*:not(.ledger-sheet-bg),.ledger-row>*:not(.ledger-row-bg){position:relative;z-index:1}
.map-node>*:not(.map-node-bg),.map-center>*:not(.map-center-bg){position:relative;z-index:1}
.contrast-panel,.flow-item{background:transparent!important}
.contrast-panel-bg,.flow-item-bg{
  position:absolute;inset:0;width:100%;height:100%;border-radius:inherit;
  background:transparent
}
.slide[data-surface-mode="marker"] :is(.contrast-panel-bg,.flow-item-bg){
  background:linear-gradient(90deg,var(--accent) 0 8px,transparent 8px)
}
.slide[data-surface-mode="banded"] :is(.contrast-panel-bg,.flow-item-bg){
  background:linear-gradient(90deg,color-mix(in srgb,var(--surface) 84%,transparent) 0 92%,transparent 92%)
}
.slide[data-surface-mode="soft-field"] :is(.contrast-panel-bg,.flow-item-bg){
  background:color-mix(in srgb,var(--surface) 78%,transparent)
}

/* Cover: three genuinely different information arrangements. */
.cover-kicker{font:700 36px/1 var(--font-utility);letter-spacing:.12em;color:var(--accent)}
.cover-title{font:800 122px/.98 var(--font-display);letter-spacing:-.065em;color:var(--ink)}
.cover-subtitle{font:500 52px/1.42 var(--font-body);color:var(--muted);text-wrap:balance}
.cover-meta{font:700 36px/1 var(--font-utility);letter-spacing:.10em;color:var(--ink)}
.cover-signature,.close-signature{position:absolute}
.cover-signature i,.close-signature i{position:absolute;display:block}
.slide[data-composition-variant="cover-split"] .cover-kicker{left:36px;top:108px}
.slide[data-composition-variant="cover-split"] .cover-title{left:36px;top:205px;width:980px}
.slide[data-composition-variant="cover-split"] .cover-subtitle{left:40px;top:570px;width:1100px}
.slide[data-composition-variant="cover-split"] .cover-meta{left:40px;top:790px}
.slide[data-composition-variant="cover-split"] .cover-signature{
  right:70px;top:96px;width:570px;height:660px;border:3px solid var(--line);border-radius:50%
}
.slide[data-composition-variant="cover-split"] .cover-signature:before,
.slide[data-composition-variant="cover-split"] .cover-signature:after{
  content:"";position:absolute;border:3px solid var(--accent);border-radius:50%
}
.slide[data-composition-variant="cover-split"] .cover-signature:before{inset:86px}
.slide[data-composition-variant="cover-split"] .cover-signature:after{inset:205px}
.slide[data-composition-variant="cover-split"] .cover-signature i{
  left:-50px;top:50%;width:650px;height:3px;background:var(--accent);transform:rotate(-18deg)
}
.slide[data-composition-variant="cover-center"] .cover-kicker{left:214px;top:90px;width:1300px;text-align:center}
.slide[data-composition-variant="cover-center"] .cover-title{left:150px;top:220px;width:1428px;text-align:center;font-size:138px}
.slide[data-composition-variant="cover-center"] .cover-subtitle{left:114px;top:590px;width:1500px;text-align:center}
.slide[data-composition-variant="cover-center"] .cover-meta{left:500px;top:802px;width:728px;text-align:center}
.slide[data-composition-variant="cover-center"] .cover-signature{
  left:354px;top:155px;width:1020px;height:520px;border:2px solid var(--line);border-radius:50%
}
.slide[data-composition-variant="cover-center"] .cover-signature i{
  left:calc(50% - 6px);top:calc(50% - 6px);width:12px;height:12px;border-radius:50%;
  background:var(--accent);box-shadow:240px 0 0 var(--support),-240px 0 0 var(--support)
}
.slide[data-composition-variant="cover-edge"] .cover-kicker{left:650px;top:86px}
.slide[data-composition-variant="cover-edge"] .cover-title{left:640px;top:194px;width:1030px;font-size:128px}
.slide[data-composition-variant="cover-edge"] .cover-subtitle{left:590px;top:570px;width:1120px}
.slide[data-composition-variant="cover-edge"] .cover-meta{left:650px;top:790px}
.slide[data-composition-variant="cover-edge"] .cover-signature{
  left:34px;top:72px;width:470px;height:744px;
  background:repeating-linear-gradient(135deg,var(--accent) 0 12px,transparent 12px 42px)
}
.slide[data-composition-variant="cover-edge"] .cover-signature:before{
  content:"";position:absolute;left:112px;top:102px;width:250px;height:520px;
  border:4px solid var(--ink);border-radius:50%
}

/* Thesis. */
.thesis-mark{font:800 240px/.8 var(--font-display);color:var(--accent)}
.thesis-quote{font:750 72px/1.32 var(--font-display);letter-spacing:-.035em;color:var(--ink)}
.thesis-attribution{font:700 36px/1.35 var(--font-utility);letter-spacing:.06em;color:var(--accent)}
.thesis-notes{position:absolute;margin:0;padding:0;list-style:none}
.thesis-notes li{position:relative}
.thesis-notes b{font:700 36px/1 var(--font-utility);color:var(--accent)}
.note-copy{position:relative!important;font:500 36px/1.42 var(--font-body);color:var(--muted);text-wrap:balance}
.slide[data-composition-variant="thesis-spine"] .thesis-mark{left:20px;top:68px}
.slide[data-composition-variant="thesis-spine"] .thesis-quote{left:300px;top:112px;width:1330px}
.slide[data-composition-variant="thesis-spine"] .thesis-attribution{left:305px;top:570px;width:1200px}
.slide[data-composition-variant="thesis-spine"] .thesis-notes{
  left:304px;right:42px;bottom:34px;display:grid;grid-template-columns:repeat(3,1fr);gap:38px
}
.slide[data-composition-variant="thesis-spine"] .thesis-notes li{padding:22px 0 0 52px;border-top:2px solid var(--line)}
.slide[data-composition-variant="thesis-spine"] .thesis-notes b{position:absolute;left:0;top:25px}
.slide[data-composition-variant="thesis-pause"] .thesis-mark{left:790px;top:50px}
.slide[data-composition-variant="thesis-pause"] .thesis-quote{left:190px;top:150px;width:1350px;text-align:center}
.slide[data-composition-variant="thesis-pause"] .thesis-attribution{left:390px;top:570px;width:950px;text-align:center}
.slide[data-composition-variant="thesis-pause"] .thesis-notes{
  left:210px;right:210px;bottom:38px;display:flex;justify-content:center;gap:52px
}
.slide[data-composition-variant="thesis-pause"] .thesis-notes li{width:30%;padding-top:18px;text-align:center}
.slide[data-composition-variant="thesis-corner"] .thesis-mark{right:20px;top:180px}
.slide[data-composition-variant="thesis-corner"] .thesis-quote{left:44px;top:190px;width:1200px;font-size:58px}
.slide[data-composition-variant="thesis-corner"] .thesis-attribution{left:48px;top:680px;width:980px}
.slide[data-composition-variant="thesis-corner"] .thesis-notes{
  right:30px;top:380px;width:520px;display:grid;gap:24px
}
.slide[data-composition-variant="thesis-corner"] .thesis-notes li{padding:12px 0 16px 55px;border-bottom:2px solid var(--line)}
.slide[data-composition-variant="thesis-corner"] .thesis-notes b{position:absolute;left:0;top:18px}

/* Index. */
.slide[data-composition-variant="index-rail"] .index-list{display:grid;grid-template-rows:repeat(4,1fr)}
.index-list{box-sizing:border-box;padding-block:18px}
.slide[data-composition-variant="index-rail"] .index-item{
  display:grid;grid-template-columns:120px 390px 1fr;align-items:center;border-bottom:2px solid var(--line)
}
.slide[data-composition-variant="index-rail"] .index-item>*{position:relative!important;left:auto;top:auto;width:auto}
.slide[data-composition-variant="index-rail"] .index-label{font-size:54px}
.slide[data-composition-variant="index-stagger"] .index-list{
  display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr);gap:28px 48px
}
.slide[data-composition-variant="index-stagger"] .index-item{padding:34px 36px!important;border-top:8px solid var(--accent)}
.slide[data-composition-variant="index-stagger"] .index-item:nth-child(even){border-top-color:var(--support)}
.slide[data-composition-variant="index-stagger"] .index-label{left:36px;top:28px;font-size:64px}
.slide[data-composition-variant="index-stagger"] .index-title{left:150px;right:30px;top:38px}
.slide[data-composition-variant="index-stagger"] .index-body{left:36px;right:34px;top:125px}
.slide[data-composition-variant="index-runway"] .index-list{display:grid;grid-template-columns:repeat(4,1fr);gap:22px}
.slide[data-composition-variant="index-runway"] .index-item{padding:32px 28px!important;border-left:3px solid var(--line)}
.slide[data-composition-variant="index-runway"] .index-label{left:28px;top:24px;font-size:82px;color:var(--support)}
.slide[data-composition-variant="index-runway"] .index-title{left:28px;right:24px;top:148px}
.slide[data-composition-variant="index-runway"] .index-body{left:28px;right:24px;top:248px}

/* Contrast. */
.contrast-panel ul{position:absolute;margin:0;padding:0;list-style:none}
.contrast-panel li{position:relative}
.slide[data-composition-variant="contrast-axis"] .contrast-grid{display:block}
.slide[data-composition-variant="contrast-axis"] .contrast-panel{position:absolute!important;top:0!important;width:50%!important;height:100%!important;padding:28px 54px!important}
.slide[data-composition-variant="contrast-axis"] .contrast-left{left:0!important;right:auto!important;border-right:0}
.slide[data-composition-variant="contrast-axis"] .contrast-right{left:50%!important;right:auto!important}
.slide[data-composition-variant="contrast-axis"] .contrast-left .contrast-panel-bg{
  border-right:3px solid var(--line)
}
.slide[data-composition-variant="contrast-axis"] .contrast-label{left:54px;top:28px}
.slide[data-composition-variant="contrast-axis"] .contrast-title{left:54px;right:40px;top:78px;font-size:54px}
.slide[data-composition-variant="contrast-axis"] .contrast-lead{left:54px;right:40px;top:160px}
.slide[data-composition-variant="contrast-axis"] .contrast-panel ul{left:54px;right:40px;top:305px}
.slide[data-composition-variant="contrast-axis"] .contrast-panel li{padding:18px 0;border-top:2px solid var(--line)}
.slide[data-composition-variant="contrast-stack"] .contrast-grid{display:block}
.slide[data-composition-variant="contrast-stack"] .contrast-panel{
  position:absolute!important;left:0!important;width:100%!important;height:calc(50% - 11px)!important;
  display:grid;grid-template-columns:150px 360px 1fr;align-items:center;padding:22px 34px!important
}
.slide[data-composition-variant="contrast-stack"] .contrast-left{top:0!important;bottom:auto!important}
.slide[data-composition-variant="contrast-stack"] .contrast-right{top:auto!important;bottom:0!important}
.slide[data-composition-variant="contrast-stack"] .contrast-panel>*{position:relative!important;left:auto;top:auto;width:auto}
.slide[data-composition-variant="contrast-stack"] .contrast-panel ul{
  position:relative;display:grid;grid-template-columns:repeat(3,1fr);gap:20px
}
.slide[data-composition-variant="contrast-stack"] .contrast-lead{display:none}
.slide[data-composition-variant="contrast-stack"] .contrast-panel li{padding-left:16px;border-left:5px solid var(--accent)}
.slide[data-composition-variant="contrast-offset"] .contrast-panel{
  position:absolute;width:58%;height:76%;padding:40px 44px!important;border-top:8px solid var(--accent)
}
.slide[data-composition-variant="contrast-offset"] .contrast-left{left:0;top:0}
.slide[data-composition-variant="contrast-offset"] .contrast-right{right:0;bottom:0;border-top-color:var(--support)}
.slide[data-composition-variant="contrast-offset"] .contrast-label{left:44px;top:34px}
.slide[data-composition-variant="contrast-offset"] .contrast-title{left:44px;right:38px;top:84px}
.slide[data-composition-variant="contrast-offset"] .contrast-lead{left:44px;right:40px;top:150px}
.slide[data-composition-variant="contrast-offset"] .contrast-panel ul{left:44px;right:40px;top:275px}
.slide[data-composition-variant="contrast-offset"] .contrast-panel li{padding:14px 0;border-top:1px solid var(--line)}

/* Columns. */
.slide[data-composition-variant="columns-open"] .column-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px}
.slide[data-composition-variant="columns-open"] .column-item{
  position:relative!important;padding:30px 26px!important;border-left:3px solid var(--line)
}
.slide[data-composition-variant="columns-open"] .column-tag{left:26px;top:26px}
.slide[data-composition-variant="columns-open"] .column-title{left:26px;right:20px;top:82px}
.slide[data-composition-variant="columns-open"] .column-body{left:26px;right:22px;top:180px}
.slide[data-composition-variant="columns-stagger"] .column-grid{
  display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr);gap:24px 36px
}
.slide[data-composition-variant="columns-stagger"] .column-item{position:relative!important;padding:28px 32px!important}
.slide[data-composition-variant="columns-stagger"] .column-tag{left:32px;top:26px}
.slide[data-composition-variant="columns-stagger"] .column-title{left:175px;right:26px;top:24px}
.slide[data-composition-variant="columns-stagger"] .column-body{left:32px;right:28px;top:102px}
.slide[data-composition-variant="columns-bands"] .column-grid{display:grid;grid-template-rows:repeat(4,1fr);gap:12px}
.slide[data-composition-variant="columns-bands"] .column-slot{display:flex;align-items:stretch}
.slide[data-composition-variant="columns-bands"] .column-item{
  position:relative!important;display:grid;grid-template-columns:170px 390px minmax(0,1fr);
  align-items:center;width:min(100%,1280px);padding:20px 30px!important
}
.slide[data-composition-variant="columns-bands"] .column-item>*:not(.column-item-bg){
  position:relative!important;left:auto;top:auto;width:auto
}

/* Flow. */
.slide[data-composition-variant="flow-track"] .flow-line{
  position:absolute;left:calc(var(--cx) + 44px);top:calc(var(--cy) + var(--ch) - 72px);
  width:calc(var(--cw) - 88px);height:6px;background:var(--line)
}
.slide[data-composition-variant="flow-track"] .flow-list{display:flex;gap:24px;height:calc(var(--ch) - 140px)}
.slide[data-composition-variant="flow-track"] .flow-item{position:relative;flex:1;padding:22px 18px!important;text-align:center}
.slide[data-composition-variant="flow-track"] .flow-item:after{
  content:"";position:absolute;left:calc(50% - 13px);top:calc(100% + 55px);width:26px;height:26px;
  border-radius:50%;background:var(--accent);box-shadow:0 0 0 8px var(--bg)
}
.slide[data-composition-variant="flow-track"] .flow-label{left:0;right:0;top:20px}
.slide[data-composition-variant="flow-track"] .flow-title{left:8px;right:8px;top:82px}
.slide[data-composition-variant="flow-track"] .flow-body{left:12px;right:12px;top:305px}
.slide[data-composition-variant="flow-steps"] .flow-list{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr);gap:24px}
.slide[data-composition-variant="flow-steps"] .flow-item{position:relative;padding:26px 30px!important}.slide[data-composition-variant="flow-steps"] .flow-item-bg{border-top:8px solid var(--accent)}
.slide[data-composition-variant="flow-steps"] .flow-item:nth-child(2),
.slide[data-composition-variant="flow-steps"] .flow-item:nth-child(5){transform:translateY(28px)}
.slide[data-composition-variant="flow-steps"] .flow-item:nth-child(3n){transform:translateY(56px)}.slide[data-composition-variant="flow-steps"] .flow-item:nth-child(3n) .flow-item-bg{border-color:var(--support)}
.slide[data-composition-variant="flow-steps"] .flow-label{left:30px;top:24px}
.slide[data-composition-variant="flow-steps"] .flow-title{left:104px;right:24px;top:20px}
.slide[data-composition-variant="flow-steps"] .flow-body{left:30px;right:26px;top:100px}
.slide[data-composition-variant="flow-lanes"] .flow-list{display:grid;grid-template-rows:repeat(6,1fr);gap:8px}
.slide[data-composition-variant="flow-lanes"] .flow-item{
  position:relative;display:grid;grid-template-columns:130px 360px 1fr;align-items:center;padding:12px 24px!important
}
.slide[data-composition-variant="flow-lanes"] .flow-item>*:not(.flow-item-bg){position:relative!important;left:auto;top:auto;width:auto}

/* Matrix. */
.matrix-frame{position:absolute;left:var(--cx);top:var(--cy);width:var(--cw);height:var(--ch)}
.matrix-frame i{position:absolute;display:block;background:var(--line)}
.axis-label{font:650 36px/1 var(--font-utility);letter-spacing:.04em;color:var(--muted)}
.axis-label{width:max-content;max-width:320px;white-space:nowrap}
.axis-1{left:var(--cx);top:calc(var(--cy) + var(--ch) + .35em)}
.axis-2{right:calc(1728px - var(--cx) - var(--cw));top:calc(var(--cy) + var(--ch) + .35em);text-align:right}
.axis-3,.axis-4{left:calc(var(--cx) - 2.1em);transform:rotate(-90deg);transform-origin:left top}
.axis-3{top:calc(var(--cy) + var(--ch))}
.axis-4{top:calc(var(--cy) + 5.4em)}
.slide[data-composition-variant="matrix-cross"] .matrix-frame i:first-child{left:50%;top:0;width:3px;height:100%}
.slide[data-composition-variant="matrix-cross"] .matrix-frame i:last-child{left:0;top:50%;width:100%;height:3px}
.slide[data-composition-variant="matrix-cross"] .matrix-items{
  display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr)
}
.slide[data-composition-variant="matrix-cross"] .matrix-item{padding:32px 42px!important}
.slide[data-composition-variant="matrix-cross"] .matrix-q{left:42px;top:28px}
.slide[data-composition-variant="matrix-cross"] .matrix-title{left:42px;right:28px;top:78px}
.slide[data-composition-variant="matrix-cross"] .matrix-body{left:42px;right:34px;top:154px}
.slide[data-composition-variant="matrix-diagonal"] .matrix-frame{
  background:linear-gradient(155deg,transparent 49.7%,var(--line) 49.8% 50.2%,transparent 50.3%)
}
.slide[data-composition-variant="matrix-diagonal"] .matrix-items{display:grid;grid-template-columns:repeat(4,1fr);gap:22px}
.slide[data-composition-variant="matrix-diagonal"] .matrix-item{
  height:58%;padding:28px 26px!important;border-top:8px solid var(--accent)
}
.slide[data-composition-variant="matrix-diagonal"] .matrix-item:nth-child(1){align-self:end}
.slide[data-composition-variant="matrix-diagonal"] .matrix-item:nth-child(2){margin-top:150px}
.slide[data-composition-variant="matrix-diagonal"] .matrix-item:nth-child(3){margin-top:72px}
.slide[data-composition-variant="matrix-diagonal"] .matrix-q{left:26px;top:24px}
.slide[data-composition-variant="matrix-diagonal"] .matrix-title{left:26px;right:22px;top:80px}
.slide[data-composition-variant="matrix-diagonal"] .matrix-body{left:26px;right:22px;top:162px}
.slide[data-composition-variant="matrix-corners"] .matrix-items{
  display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr);gap:54px
}
.slide[data-composition-variant="matrix-corners"] .matrix-item{padding:28px 38px!important;border:3px solid var(--line)}
.slide[data-composition-variant="matrix-corners"] .matrix-item:before{
  content:"";position:absolute;width:72px;height:72px;border-top:12px solid var(--accent);border-left:12px solid var(--accent)
}
.slide[data-composition-variant="matrix-corners"] .matrix-q{left:130px;top:28px}
.slide[data-composition-variant="matrix-corners"] .matrix-title{left:130px;right:30px;top:80px}
.slide[data-composition-variant="matrix-corners"] .matrix-body{left:38px;right:34px;top:162px}

/* Ledger: data keeps row semantics, while rhythm and emphasis vary. */
.ledger-row{width:100%;display:grid;grid-template-columns:1.05fr 1.45fr 1.65fr 1.5fr}
.ledger-cell{
  position:relative!important;padding:16px 20px!important;
  font:500 36px/1.34 var(--font-body);color:var(--ink);text-wrap:balance
}
.ledger-head{font:700 36px/1.2 var(--font-utility);letter-spacing:.05em;color:var(--accent)}
.slide[data-composition-variant="ledger-open"] .ledger-row{border-bottom:2px solid var(--line)}
.slide[data-composition-variant="ledger-open"] .ledger-header{border-top:5px solid var(--ink)}
.slide[data-composition-variant="ledger-open"] .scene-footer{white-space:nowrap}
.slide[data-composition-variant="ledger-bands"] .ledger{display:grid;grid-template-rows:auto repeat(4,1fr);gap:10px}
.slide[data-composition-variant="ledger-bands"] .ledger-row{align-items:center;background:color-mix(in srgb,var(--surface) 80%,transparent)}
.slide[data-composition-variant="ledger-bands"] .ledger-row:nth-child(odd){margin-left:42px;width:calc(100% - 42px)}
.slide[data-composition-variant="ledger-index"] .ledger-row{grid-template-columns:.7fr 1.4fr 1.6fr 1.5fr;border-bottom:2px solid var(--line)}
.slide[data-composition-variant="ledger-index"] .ledger-row:not(.ledger-header) .ledger-cell:first-child{
  font:800 38px/1 var(--font-display);color:var(--accent)
}

/* Timeline. */
.slide[data-composition-variant="timeline-horizontal"] .timeline-rule{
  position:absolute;left:calc(var(--cx) + 30px);top:calc(var(--cy) + 236px);
  width:calc(var(--cw) - 60px);height:5px;background:var(--line)
}
.slide[data-composition-variant="timeline-horizontal"] .timeline-list{display:grid;grid-template-columns:repeat(4,1fr);gap:28px}
.slide[data-composition-variant="timeline-horizontal"] .timeline-item{padding:26px 22px!important}
.slide[data-composition-variant="timeline-horizontal"] .timeline-item:after{
  content:"";position:absolute;left:22px;top:222px;width:28px;height:28px;border-radius:50%;
  background:var(--accent);box-shadow:0 0 0 8px var(--bg)
}
.slide[data-composition-variant="timeline-horizontal"] .timeline-time{left:22px;top:20px}
.slide[data-composition-variant="timeline-horizontal"] .timeline-title{left:22px;right:18px;top:76px}
.slide[data-composition-variant="timeline-horizontal"] .timeline-body{left:22px;right:18px;top:292px}
.slide[data-composition-variant="timeline-spine"] .timeline-rule{
  position:absolute;left:var(--cm);top:var(--cy);width:5px;height:var(--ch);background:var(--line)
}
.slide[data-composition-variant="timeline-spine"] .timeline-list{display:grid;grid-template-rows:repeat(4,1fr)}
.slide[data-composition-variant="timeline-spine"] .timeline-item{width:47%;padding:18px 28px!important}
.slide[data-composition-variant="timeline-spine"] .timeline-item:nth-child(even){margin-left:53%}
.slide[data-composition-variant="timeline-spine"] .timeline-time{left:28px;top:18px}
.slide[data-composition-variant="timeline-spine"] .timeline-title{left:170px;right:20px;top:14px}
.slide[data-composition-variant="timeline-spine"] .timeline-body{left:28px;right:20px;top:72px}
.slide[data-composition-variant="timeline-steps"] .timeline-list{display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:100%;align-items:start;gap:24px}
.slide[data-composition-variant="timeline-steps"] .timeline-item{height:70%;padding:28px 26px!important;border-top:8px solid var(--accent)}
.slide[data-composition-variant="timeline-steps"] .timeline-item:nth-child(2){margin-top:40px}
.slide[data-composition-variant="timeline-steps"] .timeline-item:nth-child(3){margin-top:80px}
.slide[data-composition-variant="timeline-steps"] .timeline-item:nth-child(4){margin-top:120px}
.slide[data-composition-variant="timeline-steps"] .timeline-time{left:26px;top:24px}
.slide[data-composition-variant="timeline-steps"] .timeline-title{left:26px;right:22px;top:78px}
.slide[data-composition-variant="timeline-steps"] .timeline-body{left:26px;right:22px;top:166px}

/* Relationship map: CSS circles and placement only. */
.map-center{position:absolute;padding:28px!important;text-align:center}
.map-center-title,.map-center-body{position:relative!important;left:auto!important;top:auto!important}
.map-center-body{margin-top:14px!important}
.slide[data-composition-variant="map-orbit"] .map-center{
  left:calc(var(--cm) - 190px);top:calc(var(--cy) + 180px);
  width:380px;height:260px;border:4px solid var(--accent);border-radius:50%
}
.slide[data-composition-variant="map-orbit"] .map-nodes{position:absolute}
.slide[data-composition-variant="map-orbit"] .map-node{position:absolute;width:280px;height:170px;text-align:center}
.slide[data-composition-variant="map-orbit"] .map-node:nth-child(1){left:calc(50% - 140px);top:0}
.slide[data-composition-variant="map-orbit"] .map-node:nth-child(2){right:0;top:90px}
.slide[data-composition-variant="map-orbit"] .map-node:nth-child(3){right:0;bottom:80px}
.slide[data-composition-variant="map-orbit"] .map-node:nth-child(4){left:calc(50% - 140px);bottom:0}
.slide[data-composition-variant="map-orbit"] .map-node:nth-child(5){left:0;bottom:80px}
.slide[data-composition-variant="map-orbit"] .map-node:nth-child(6){left:0;top:90px}
.slide[data-composition-variant="map-orbit"] .map-label{left:0;top:0;width:100%}
.slide[data-composition-variant="map-orbit"] .map-body{left:0;top:54px;width:100%}
.slide[data-composition-variant="map-constellation"] .map-center{
  left:var(--cx);top:calc(var(--cy) + 105px);width:340px;height:390px;
  display:grid;place-content:center;border-right:6px solid var(--accent)
}
.slide[data-composition-variant="map-constellation"] .map-nodes{
  left:calc(var(--cx) + 400px);width:calc(var(--cw) - 400px);
  display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(3,1fr);gap:20px
}
.slide[data-composition-variant="map-constellation"] .map-node{padding:24px 28px!important}
.slide[data-composition-variant="map-constellation"] .map-label{left:28px;top:20px}
.slide[data-composition-variant="map-constellation"] .map-body{left:28px;right:24px;top:76px}
.slide[data-composition-variant="map-lanes"] .map-center{
  left:calc(var(--cm) - 260px);top:var(--cy);width:520px;height:160px;
  border-bottom:6px solid var(--accent)
}
.slide[data-composition-variant="map-lanes"] .map-nodes{
  top:calc(var(--cy) + 210px);height:calc(var(--ch) - 210px);
  display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr);gap:20px
}
.slide[data-composition-variant="map-lanes"] .map-node{padding:22px 28px!important;text-align:center}
.slide[data-composition-variant="map-lanes"] .map-label{left:20px;right:20px;top:18px}
.slide[data-composition-variant="map-lanes"] .map-body{left:20px;right:20px;top:76px}

/* Metrics. */
.slide[data-composition-variant="metrics-stack"] .metric-grid{
  display:grid;grid-template-rows:repeat(4,1fr);gap:12px
}
.slide[data-composition-variant="metrics-stack"] .metric-item{
  display:grid;grid-template-columns:170px 640px minmax(0,1fr);column-gap:54px;
  align-items:center;padding:18px 30px!important
}
.slide[data-composition-variant="metrics-stack"] .metric-value{
  font:800 64px/1 var(--font-display);color:var(--accent)
}
.slide[data-composition-variant="metrics-strip"] .metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px}
.slide[data-composition-variant="metrics-strip"] .metric-item{padding:30px 26px!important;border-top:8px solid var(--accent)}
.slide[data-composition-variant="metrics-strip"] .metric-value{left:26px;top:28px;font:800 78px/1 var(--font-display);color:var(--accent)}
.slide[data-composition-variant="metrics-strip"] .metric-label{left:26px;right:20px;top:138px}
.slide[data-composition-variant="metrics-strip"] .metric-meaning{left:26px;right:20px;top:268px}
.slide[data-composition-variant="metrics-cross"] .metric-grid{
  display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr)
}
.slide[data-composition-variant="metrics-cross"] .metric-item{padding:30px 36px!important}
.slide[data-composition-variant="metrics-cross"] .metric-item:nth-child(odd){border-right:3px solid var(--line)}
.slide[data-composition-variant="metrics-cross"] .metric-item:nth-child(-n+2){border-bottom:3px solid var(--line)}
.slide[data-composition-variant="metrics-cross"] .metric-value{left:36px;top:28px;font:800 72px/1 var(--font-display);color:var(--accent)}
.slide[data-composition-variant="metrics-cross"] .metric-label{left:260px;right:28px;top:32px}
.slide[data-composition-variant="metrics-cross"] .metric-meaning{left:260px;right:28px;top:112px}

/* Close. */
.close-statement{font:800 90px/1.04 var(--font-display);letter-spacing:-.05em;color:var(--ink)}
.close-body{font:500 42px/1.5 var(--font-body);color:var(--muted)}
.close-action{font:700 36px/1.42 var(--font-body);color:var(--ink)}
.close-meta{font:700 36px/1 var(--font-utility);letter-spacing:.10em;color:var(--accent)}
.slide[data-composition-variant="close-split"] .close-statement{left:36px;top:130px;width:1120px}
.slide[data-composition-variant="close-split"] .close-body{left:40px;top:500px;width:960px}
.slide[data-composition-variant="close-split"] .close-action{left:40px;top:710px;width:980px}
.slide[data-composition-variant="close-split"] .close-meta{left:40px;bottom:42px}
.slide[data-composition-variant="close-split"] .close-signature{
  right:50px;top:115px;width:520px;height:610px;border:4px solid var(--line);border-radius:50%
}
.slide[data-composition-variant="close-split"] .close-signature i{
  left:70px;right:70px;height:5px;background:var(--accent);transform:rotate(-18deg)
}
.slide[data-composition-variant="close-split"] .close-signature i:nth-child(1){top:160px}
.slide[data-composition-variant="close-split"] .close-signature i:nth-child(2){top:300px}
.slide[data-composition-variant="close-split"] .close-signature i:nth-child(3){top:440px}
.slide[data-composition-variant="close-center"] .close-statement{left:180px;top:145px;width:1368px;text-align:center}
.slide[data-composition-variant="close-center"] .close-body{left:320px;top:500px;width:1088px;text-align:center}
.slide[data-composition-variant="close-center"] .close-action{left:350px;top:700px;width:1028px;text-align:center}
.slide[data-composition-variant="close-center"] .close-meta{left:500px;bottom:42px;width:728px;text-align:center}
.slide[data-composition-variant="close-center"] .close-signature{
  left:290px;top:100px;width:1148px;height:540px;border:3px solid var(--line);border-radius:50%
}
.slide[data-composition-variant="close-edge"] .close-statement{left:560px;top:105px;width:1120px}
.slide[data-composition-variant="close-edge"] .close-body{left:614px;top:485px;width:980px}
.slide[data-composition-variant="close-edge"] .close-action{left:614px;top:690px;width:980px}
.slide[data-composition-variant="close-edge"] .close-meta{left:614px;bottom:42px}
.slide[data-composition-variant="close-edge"] .close-signature{
  left:20px;top:60px;width:430px;height:760px;
  background:repeating-radial-gradient(circle at 50% 50%,transparent 0 38px,var(--accent) 39px 42px,transparent 43px 80px)
}

/* Keep every semantic module internally centered. Variant rules still decide
   the outer arrangement; text boxes remain independent editor objects. */
.slide :is(
  .index-item,.column-item,.flow-item,.matrix-item,.timeline-item,.map-node,
  .metric-item,.contrast-panel
){
  position:relative!important;display:flex;flex-direction:column;justify-content:center;
  gap:18px;padding:28px 30px!important;min-width:0;min-height:0
}
.scene [data-edit-position="flow"]{
  position:relative!important;inset:auto!important;width:auto!important;height:auto!important;
  margin:0!important
}
.slide .contrast-panel ul{
  position:relative!important;inset:auto!important;width:100%;margin:4px 0 0;padding:0;
  display:grid;gap:10px;list-style:none
}
.slide .contrast-panel li{padding:8px 0;border-top:2px solid var(--line)}
.slide .map-center{
  display:flex;flex-direction:column;justify-content:center;gap:14px
}

.slide[data-composition-variant="index-rail"] .index-item,
.slide[data-composition-variant="contrast-stack"] .contrast-panel,
.slide[data-composition-variant="columns-bands"] .column-item,
.slide[data-composition-variant="flow-lanes"] .flow-item,
.slide[data-composition-variant="metrics-stack"] .metric-item{
  display:grid!important
}
.slide[data-composition-variant="index-rail"] .index-list{grid-template-rows:none;grid-auto-rows:1fr}
.slide[data-composition-variant="index-stagger"] .index-list{grid-template-rows:none;grid-auto-rows:minmax(0,1fr)}
.slide[data-composition-variant="flow-lanes"] .flow-list{grid-template-rows:none;grid-auto-rows:1fr}
.slide[data-composition-variant="timeline-horizontal"] .timeline-item{
  justify-content:flex-start
}
.slide[data-composition-variant="timeline-horizontal"] .timeline-body{
  margin-top:210px!important
}
.slide[data-composition-variant="flow-track"] .flow-item{
  justify-content:center
}
.slide[data-composition-variant="flow-track"] .flow-body{
  margin-top:0!important
}
.slide[data-composition-variant="timeline-spine"] .timeline-item{
  display:grid!important;grid-template-columns:145px 1fr;grid-template-rows:auto auto;
  align-items:center;align-content:center
}
.slide[data-composition-variant="timeline-spine"] .timeline-body{grid-column:1/3}
.slide[data-composition-variant="metrics-cross"] .metric-item{
  display:grid!important;grid-template-columns:200px 1fr;grid-template-rows:auto 1fr;align-items:center
}
.slide[data-composition-variant="metrics-cross"] .metric-meaning{grid-column:2}
.slide[data-composition-variant="contrast-offset"] .contrast-panel{position:absolute!important}
.slide[data-composition-variant="contrast-offset"] .contrast-left{left:0!important;right:auto!important;top:0!important;bottom:auto!important}
.slide[data-composition-variant="contrast-offset"] .contrast-right{left:auto!important;right:0!important;top:auto!important;bottom:0!important}
.slide[data-composition-variant="map-orbit"] .map-node{position:absolute!important}
.contrast-label{font-size:44px}
.index-runway .index-label,
.slide[data-composition-variant="index-runway"] .index-label{color:var(--accent)}
.scene-title,.scene-intro,.index-title,.column-title,.flow-title,.matrix-title,
.timeline-title,.map-label,.metric-label,.contrast-title,.close-statement{
  text-wrap:balance;line-break:strict;word-break:auto-phrase
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


COMPOSITION_VARIANTS = {
    "cover": ("cover-split", "cover-center", "cover-edge"),
    "thesis": ("thesis-spine", "thesis-pause", "thesis-corner"),
    "index": ("index-rail", "index-stagger", "index-runway"),
    "contrast": ("contrast-axis", "contrast-stack", "contrast-offset"),
    "columns": ("columns-open", "columns-stagger", "columns-bands"),
    "flow": ("flow-track", "flow-steps", "flow-lanes"),
    "matrix": ("matrix-cross", "matrix-diagonal", "matrix-corners"),
    "ledger": ("ledger-open", "ledger-bands", "ledger-index"),
    "timeline": ("timeline-horizontal", "timeline-spine", "timeline-steps"),
    "map": ("map-orbit", "map-constellation", "map-lanes"),
    "metrics": ("metrics-stack", "metrics-strip", "metrics-cross"),
    "close": ("close-split", "close-center", "close-edge"),
}

HEADER_MODES = {
    "cover": ("immersive",),
    "thesis": ("immersive",),
    "close": ("immersive",),
    "index": ("top", "side-left", "band"),
    "contrast": ("top", "side-left", "side-right", "band"),
    "columns": ("top", "band"),
    "flow": ("top", "band"),
    "matrix": ("top", "band"),
    "ledger": ("top",),
    "timeline": ("top", "side-left", "side-right"),
    "map": ("top", "side-left"),
    "metrics": ("top", "band"),
}

SURFACE_MODES = ("open", "marker", "banded", "soft-field")

THEME_SURFACE_POOLS = {
    "tide-signal-observatory": ("open", "marker", "soft-field"),
    "harbor-ribbon-program": ("open", "marker", "soft-field"),
    "scent-veil-launch": ("open", "marker", "soft-field"),
    "brave-classroom-contours": ("open", "marker", "soft-field"),
    "moonlit-herbarium-atlas": ("open", "marker", "soft-field"),
}

THEME_SEEDS = {
    "line-argument-journal": 0,
    "signal-route-atlas": 5,
    "field-index-manual": 9,
    "tide-signal-observatory": 14,
    "craft-archive-editions": 18,
    "incident-command-redline": 23,
    "harbor-ribbon-program": 29,
    "neighborhood-newsroom-proof": 34,
    "scent-veil-launch": 39,
    "restoration-blueprint-ledger": 44,
    "ai-operations-signal": 49,
    "brave-classroom-contours": 55,
    "night-transit-wayfinding": 61,
    "moonlit-herbarium-atlas": 67,
}

THEME_LAYOUT_OVERRIDES = {
    "signal-route-atlas": {
        "cover-center-title-edge-decor": {
            "composition_variant": "cover-center",
            "header_mode": "immersive",
            "surface_mode": "terminal-open",
            "recipe_id": "route-cover-terminal-window",
        },
        "toc-5-panel-rows": {
            "composition_variant": "index-rail",
            "header_mode": "side-left",
            "surface_mode": "station-rows",
            "recipe_id": "route-index-transfer-spine",
        },
        "cards-1-plus-4": {
            "composition_variant": "columns-stagger",
            "header_mode": "top",
            "surface_mode": "platform-bays",
            "recipe_id": "route-source-platforms",
        },
        "toc-4-panel-rows": {
            "composition_variant": "ledger-index",
            "header_mode": "top",
            "surface_mode": "ticket-ledger",
            "recipe_id": "route-ticket-taxonomy",
        },
        "process-flow": {
            "composition_variant": "flow-track",
            "header_mode": "band",
            "surface_mode": "mainline",
            "recipe_id": "route-six-stop-mainline",
        },
        "matrix-4quadrant": {
            "composition_variant": "matrix-cross",
            "header_mode": "top",
            "surface_mode": "junction-field",
            "recipe_id": "route-confidence-crossing",
        },
        "strategic-priorities": {
            "composition_variant": "columns-bands",
            "header_mode": "band",
            "surface_mode": "dispatch-lanes",
            "recipe_id": "route-experiment-dispatch",
        },
        "cycle-hub-6": {
            "composition_variant": "map-orbit",
            "header_mode": "side-left",
            "surface_mode": "loop-map",
            "recipe_id": "route-decision-loop",
        },
        "comparison-table": {
            "composition_variant": "ledger-bands",
            "header_mode": "top",
            "surface_mode": "parallel-lines",
            "recipe_id": "route-service-blueprint",
        },
        "timeline-milestones": {
            "composition_variant": "timeline-horizontal",
            "header_mode": "side-right",
            "surface_mode": "timetable",
            "recipe_id": "route-operating-timetable",
        },
        "kpi-scorecards": {
            "composition_variant": "metrics-cross",
            "header_mode": "band",
            "surface_mode": "health-board",
            "recipe_id": "route-health-board",
        },
        "title-center": {
            "composition_variant": "close-center",
            "header_mode": "immersive",
            "surface_mode": "terminal-close",
            "recipe_id": "route-terminal-close",
        },
    },
    "scent-veil-launch": {
        "scent-cover-veil-current-flow-v3": {
            "composition_variant": "cover-split",
            "header_mode": "immersive",
            "surface_mode": "open",
            "recipe_id": "scent-cover-perfume-label",
        },
        "scent-memory-thesis-current-flow-v3": {
            "composition_variant": "thesis-spine",
            "header_mode": "immersive",
            "surface_mode": "open",
            "recipe_id": "scent-thesis-memory-halo",
        },
        "scent-ritual-index-current-flow-v3": {
            "composition_variant": "index-runway",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-index-four-moments",
        },
        "scent-audience-columns-current-flow-v3": {
            "composition_variant": "columns-open",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-audience-guidance-columns",
        },
        "scent-note-map-current-flow-v3": {
            "composition_variant": "map-constellation",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-map-memory-core",
        },
        "scent-experience-metrics-current-flow-v3": {
            "composition_variant": "metrics-cross",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-metrics-memory-signals",
        },
        "scent-sales-contrast-current-flow-v3": {
            "composition_variant": "contrast-axis",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-contrast-feel-before-formula",
        },
        "scent-launch-timeline-current-flow-v3": {
            "composition_variant": "timeline-horizontal",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-timeline-release-rail",
        },
        "scent-touchpoint-ledger-current-flow-v3": {
            "composition_variant": "ledger-open",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-ledger-touchpoint-breath",
        },
        "scent-close-memory-current-flow-v3": {
            "composition_variant": "close-split",
            "header_mode": "immersive",
            "surface_mode": "open",
            "recipe_id": "scent-close-lingering-trails",
        },
        "scent-cover-veil-current-flow-v4": {
            "composition_variant": "cover-split",
            "header_mode": "immersive",
            "surface_mode": "open",
            "recipe_id": "scent-v4-cover-thread",
        },
        "scent-memory-thesis-current-flow-v4": {
            "composition_variant": "thesis-spine",
            "header_mode": "immersive",
            "surface_mode": "open",
            "recipe_id": "scent-v4-thesis-frame",
        },
        "scent-ritual-index-current-flow-v4": {
            "composition_variant": "index-runway",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-index-thread",
        },
        "scent-audience-columns-current-flow-v4": {
            "composition_variant": "columns-open",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-audience-rules",
        },
        "scent-note-map-current-flow-v4": {
            "composition_variant": "map-constellation",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-map-index",
        },
        "scent-experience-metrics-current-flow-v4": {
            "composition_variant": "metrics-cross",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-metrics-rules",
        },
        "scent-sales-contrast-current-flow-v4": {
            "composition_variant": "contrast-axis",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-contrast-divider",
        },
        "scent-launch-timeline-current-flow-v4": {
            "composition_variant": "timeline-horizontal",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-timeline-thread",
        },
        "scent-touchpoint-ledger-current-flow-v4": {
            "composition_variant": "ledger-open",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-ledger-rules",
        },
        "scent-close-memory-current-flow-v4": {
            "composition_variant": "close-split",
            "header_mode": "immersive",
            "surface_mode": "open",
            "recipe_id": "scent-v4-close-return",
        },
        "scent-cover-veil-current-flow-v5": {
            "composition_variant": "cover-split",
            "header_mode": "immersive",
            "surface_mode": "open",
            "recipe_id": "scent-v4-cover-thread",
        },
        "scent-memory-thesis-current-flow-v5": {
            "composition_variant": "thesis-spine",
            "header_mode": "immersive",
            "surface_mode": "open",
            "recipe_id": "scent-v4-thesis-frame",
        },
        "scent-ritual-index-current-flow-v5": {
            "composition_variant": "index-runway",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-index-thread",
        },
        "scent-audience-columns-current-flow-v5": {
            "composition_variant": "columns-open",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-audience-rules",
        },
        "scent-note-map-current-flow-v5": {
            "composition_variant": "map-constellation",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-map-index",
        },
        "scent-experience-metrics-current-flow-v5": {
            "composition_variant": "metrics-cross",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-metrics-rules",
        },
        "scent-sales-contrast-current-flow-v5": {
            "composition_variant": "contrast-axis",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-contrast-divider",
        },
        "scent-launch-timeline-current-flow-v5": {
            "composition_variant": "timeline-horizontal",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-timeline-thread",
        },
        "scent-touchpoint-ledger-current-flow-v5": {
            "composition_variant": "ledger-open",
            "header_mode": "top",
            "surface_mode": "open",
            "recipe_id": "scent-v4-ledger-rules",
        },
        "scent-close-memory-current-flow-v5": {
            "composition_variant": "close-split",
            "header_mode": "immersive",
            "surface_mode": "open",
            "recipe_id": "scent-v4-close-return",
        },
        "scent-cover-veil-current-flow-v6": {
            "composition_variant": "cover-split",
            "header_mode": "immersive",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-cover-thread",
        },
        "scent-memory-thesis-current-flow-v6": {
            "composition_variant": "thesis-spine",
            "header_mode": "immersive",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-thesis-frame",
        },
        "scent-ritual-index-current-flow-v6": {
            "composition_variant": "index-runway",
            "header_mode": "top",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-index-thread",
        },
        "scent-audience-columns-current-flow-v6": {
            "composition_variant": "columns-open",
            "header_mode": "top",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-audience-rules",
        },
        "scent-note-map-current-flow-v6": {
            "composition_variant": "map-constellation",
            "header_mode": "top",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-map-index",
        },
        "scent-experience-metrics-current-flow-v6": {
            "composition_variant": "metrics-cross",
            "header_mode": "top",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-metrics-rules",
        },
        "scent-sales-contrast-current-flow-v6": {
            "composition_variant": "contrast-axis",
            "header_mode": "top",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-contrast-divider",
        },
        "scent-launch-timeline-current-flow-v6": {
            "composition_variant": "timeline-horizontal",
            "header_mode": "top",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-timeline-thread",
        },
        "scent-touchpoint-ledger-current-flow-v6": {
            "composition_variant": "ledger-open",
            "header_mode": "top",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-ledger-rules",
        },
        "scent-close-memory-current-flow-v6": {
            "composition_variant": "close-split",
            "header_mode": "immersive",
            "surface_mode": "veil-pane",
            "recipe_id": "scent-v4-close-return",
        },
    },
    "brave-classroom-contours": {
        # Five equal steps, two equal comparison panels, and four equal weeks
        # share one visible axis. These are deliberate capacity decisions, not
        # decorative exceptions.
        "brave-lesson-flow": {
            "composition_variant": "flow-track",
            "header_mode": "band",
            "surface_mode": "soft-field",
        },
        "brave-pressure-contrast": {
            "composition_variant": "contrast-axis",
            "header_mode": "top",
            "surface_mode": "soft-field",
        },
        "brave-pilot-timeline": {
            "composition_variant": "timeline-horizontal",
            "header_mode": "top",
            "surface_mode": "open",
        },
    },
}


def _content_units(slide: dict[str, Any]) -> int:
    composition = slide["composition"]
    if composition == "contrast":
        return sum(len(slide.get(side, {}).get("items", [])) + 1 for side in ("left", "right"))
    if composition == "map":
        return len(slide.get("nodes", [])) + (1 if slide.get("center") else 0)
    return len(slide.get("items", []))


def _capacity_safe_variants(
    composition: str,
    variants: tuple[str, ...],
    units: int,
) -> tuple[str, ...]:
    """Remove variants whose fixed geometry cannot balance the item count."""

    rejected: set[str] = set()
    if composition == "flow" and units not in (3, 6):
        rejected.add("flow-steps")
    if composition == "index" and units != 4:
        rejected.add("index-stagger")
    if composition == "index" and units > 4:
        rejected.add("index-runway")
    if composition == "contrast" and units > 6:
        rejected.add("contrast-offset")
    safe = tuple(variant for variant in variants if variant not in rejected)
    return safe or variants


def resolve_deck_design(theme_id: str, slides: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return explicit recipes first, with seeded selection only as a fallback."""

    seed = THEME_SEEDS[theme_id]
    decisions: list[dict[str, str]] = []
    previous_header = ""
    previous_surface = ""
    for index, slide in enumerate(slides):
        composition = slide["composition"]
        explicit = THEME_LAYOUT_OVERRIDES.get(theme_id, {}).get(slide["layout_id"])
        if explicit:
            decision = {"composition": composition, **explicit}
            decisions.append(decision)
            previous_header = decision["header_mode"]
            previous_surface = decision["surface_mode"]
            continue
        digest = int(
            hashlib.sha256(
                f"{theme_id}|{slide['layout_id']}|{composition}".encode("utf-8")
            ).hexdigest()[:8],
            16,
        )
        units = _content_units(slide)
        variants = _capacity_safe_variants(
            composition,
            COMPOSITION_VARIANTS[composition],
            units,
        )
        variant = variants[(digest + seed + index) % len(variants)]

        headers = HEADER_MODES[composition]
        title_length = len(str(slide.get("title", "")).replace(" ", ""))
        intro_length = len(str(slide.get("intro", "")).replace(" ", ""))
        if title_length > 18 or intro_length > 42 or units >= 6:
            compact_headers = tuple(mode for mode in headers if not mode.startswith("side"))
            if compact_headers:
                headers = compact_headers
        header = headers[(seed + index + digest // 7) % len(headers)]
        if len(headers) > 1 and header == previous_header:
            header = headers[(headers.index(header) + 1) % len(headers)]

        surface_pool = THEME_SURFACE_POOLS.get(
            theme_id,
            SURFACE_MODES[:3],
        )
        surface = surface_pool[(seed + index + digest // 13) % len(surface_pool)]
        if surface == previous_surface:
            surface = surface_pool[(surface_pool.index(surface) + 1) % len(surface_pool)]

        decision = {
            "composition": composition,
            "composition_variant": variant,
            "header_mode": header,
            "surface_mode": surface,
        }
        decisions.append(decision)
        previous_header = decision["header_mode"]
        previous_surface = decision["surface_mode"]
    return decisions


def _theme_css(theme_id: str, spec: dict[str, str]) -> str:
    selector = f'html[data-theme-id="{theme_id}"]'
    return (
        f"{selector}{{--bg:{spec['bg']};--surface:{spec['surface']};--ink:{spec['ink']};"
        f"--muted:{spec['muted']};--accent:{spec['accent']};--support:{spec['support']};"
        f"--line:{spec['line']};--soft-radius:{spec['radius']};"
        f"--font-display:{spec['display']};--font-body:{spec['body']};"
        f"--font-utility:{spec['utility']}}}\n"
        f"{selector} .slide{{{spec['slide']}}}\n"
        f"{selector} .slide:before{{content:\"\";position:absolute;z-index:1;{spec['before']}}}\n"
        f"{selector} .slide:after{{content:\"\";position:absolute;z-index:1;{spec['after']}}}\n"
        f"{selector} .content{{z-index:2}}\n"
    )


_SANS = '"Noto Sans TC",sans-serif'
_SERIF = '"Noto Serif TC",serif'
_CONDENSED = '"Noto Sans TC",sans-serif'
_MONO = '"Roboto Mono","Noto Sans TC",monospace'

_THEME_SPECS = {
    "line-argument-journal": {
        "bg": "#F5F4F0", "surface": "#FFFFFF", "ink": "#17191A", "muted": "#5D666D",
        "accent": "#8D3028", "support": "#A7AA9F", "line": "#C7C9C5", "radius": "0px",
        "display": _SERIF, "body": _SANS, "utility": _MONO,
        "slide": "background-image:repeating-linear-gradient(0deg,transparent 0 53px,rgba(23,25,26,.045) 54px 55px)",
        "before": "left:76px;top:0;bottom:0;width:2px;background:rgba(141,48,40,.18)",
        "after": "left:76px;right:76px;top:62px;height:2px;background:var(--ink);opacity:.45",
    },
    "signal-route-atlas": {
        "bg": "#F2EFE5", "surface": "#FAF8F1", "ink": "#102A36", "muted": "#4E6269",
        "accent": "#D45A2F", "support": "#1C7777", "line": "#A9B9B7", "radius": "0px",
        "display": _SANS, "body": _SANS, "utility": _MONO,
        "slide": "background-image:linear-gradient(rgba(16,42,54,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(16,42,54,.05) 1px,transparent 1px);background-size:72px 72px",
        "before": "display:none",
        "after": "display:none",
    },
    "field-index-manual": {
        "bg": "#E9EEE8", "surface": "#FAFAF7", "ink": "#143D2D", "muted": "#52645A",
        "accent": "#87374B", "support": "#D6B34A", "line": "#B9C4BA", "radius": "4px",
        "display": _SERIF, "body": _SANS, "utility": _MONO,
        "slide": "background-image:radial-gradient(circle,rgba(20,61,45,.10) 1.4px,transparent 1.6px);background-size:34px 34px",
        "before": "left:58px;right:58px;top:54px;bottom:54px;border:2px solid rgba(20,61,45,.18)",
        "after": "right:44px;top:112px;width:80px;height:230px;background:repeating-linear-gradient(0deg,var(--accent) 0 22px,transparent 22px 42px)",
    },
    "tide-signal-observatory": {
        "bg": "#F2F1E8", "surface": "#FBFAF4", "ink": "#062C33", "muted": "#577A7B",
        "accent": "#B9432C", "support": "#246E79", "line": "#ABC1BF", "radius": "26px",
        "display": _SANS, "body": _SANS, "utility": _MONO,
        "slide": "background-image:repeating-radial-gradient(ellipse at 12% 112%,transparent 0 54px,rgba(44,135,149,.10) 55px 58px,transparent 59px 104px)",
        "before": "left:0;right:0;bottom:0;height:180px;background:linear-gradient(0deg,rgba(44,135,149,.13),transparent)",
        "after": "right:74px;top:64px;width:190px;height:190px;border:4px solid var(--accent);border-radius:50%;opacity:.45",
    },
    "craft-archive-editions": {
        "bg": "#EFE6D7", "surface": "#F8F1E6", "ink": "#382C25", "muted": "#796B60",
        "accent": "#A44D32", "support": "#2F6B66", "line": "#C8B8A2", "radius": "0px",
        "display": _SERIF, "body": _SANS, "utility": _MONO,
        "slide": "background-image:linear-gradient(45deg,rgba(56,44,37,.035) 25%,transparent 25% 75%,rgba(56,44,37,.035) 75%),linear-gradient(-45deg,rgba(164,77,50,.028) 25%,transparent 25% 75%,rgba(164,77,50,.028) 75%);background-size:42px 42px",
        "before": "left:64px;top:72px;width:250px;height:16px;background:repeating-linear-gradient(90deg,var(--accent) 0 18px,transparent 18px 30px)",
        "after": "right:70px;bottom:70px;width:300px;height:150px;border-right:6px solid var(--support);border-bottom:6px solid var(--support)",
    },
    "incident-command-redline": {
        "bg": "#F1F2F0", "surface": "#FFFFFF", "ink": "#171B1D", "muted": "#5E6668",
        "accent": "#D3332B", "support": "#F0A31B", "line": "#BFC4C4", "radius": "0px",
        "display": _CONDENSED, "body": _SANS, "utility": _MONO,
        "slide": "background-image:linear-gradient(90deg,transparent 0 94%,rgba(211,51,43,.05) 94%)",
        "before": "left:0;top:0;width:100%;height:18px;background:repeating-linear-gradient(135deg,var(--accent) 0 22px,var(--ink) 22px 44px)",
        "after": "right:56px;top:78px;width:120px;height:120px;border:10px solid var(--support);transform:rotate(45deg);opacity:.35",
    },
    "harbor-ribbon-program": {
        "bg": "#F4F7F6", "surface": "#FFFFFF", "ink": "#183B4A", "muted": "#5C747D",
        "accent": "#E0593E", "support": "#2D8A89", "line": "#BED1D2", "radius": "34px",
        "display": _SANS, "body": _SANS, "utility": _MONO,
        "slide": "background-image:linear-gradient(165deg,transparent 0 68%,rgba(45,138,137,.09) 68% 76%,transparent 76%)",
        "before": "left:-100px;top:188px;width:730px;height:70px;border-radius:0 80px 80px 0;background:var(--accent);opacity:.16",
        "after": "right:-160px;bottom:130px;width:880px;height:86px;border-radius:80px 0 0 80px;background:var(--support);opacity:.16",
    },
    "neighborhood-newsroom-proof": {
        "bg": "#F6F1E6", "surface": "#FFFDF7", "ink": "#262522", "muted": "#706B61",
        "accent": "#C64636", "support": "#7896A1", "line": "#CFC5B4", "radius": "0px",
        "display": _CONDENSED, "body": _SANS, "utility": _MONO,
        "slide": (
            "background-image:"
            "linear-gradient(112deg,rgba(198,70,54,.035),transparent 28%),"
            "radial-gradient(circle at 84% 18%,rgba(120,150,161,.075),transparent 34%),"
            "repeating-linear-gradient(0deg,transparent 0 43px,rgba(38,37,34,.032) 44px 45px),"
            "radial-gradient(circle,rgba(38,37,34,.032) 0 1.1px,transparent 1.5px);"
            "background-size:100% 100%,100% 100%,100% 45px,8px 8px"
        ),
        "before": "left:0;right:0;top:52px;height:2px;background:rgba(38,37,34,.16)",
        "after": "display:none",
    },
    "scent-veil-launch": {
        "bg": "#FAF4F6", "surface": "#FFFDFE", "ink": "#4D3545", "muted": "#876D7D",
        "accent": "#AD496F", "support": "#C99CA9", "line": "#DFC8D1", "radius": "0px",
        "display": _SANS, "body": _SANS, "utility": _MONO,
        "slide": "background-image:none",
        "before": "display:none",
        "after": "display:none",
    },
    "restoration-blueprint-ledger": {
        "bg": "#E9E2D2", "surface": "#F4EFE5", "ink": "#15334B", "muted": "#6A716E",
        "accent": "#A94E20", "support": "#386F73", "line": "#B8AA94", "radius": "2px",
        "display": _SANS, "body": _SANS, "utility": _MONO,
        "slide": "background-image:linear-gradient(rgba(45,125,154,.09) 1px,transparent 1px),linear-gradient(90deg,rgba(45,125,154,.09) 1px,transparent 1px);background-size:42px 42px",
        "before": "left:48px;top:48px;right:48px;bottom:48px;border:2px dashed rgba(45,125,154,.34)",
        "after": "right:74px;top:70px;width:250px;height:74px;background:repeating-linear-gradient(90deg,var(--support) 0 2px,transparent 2px 25px);opacity:.45",
    },
    "ai-operations-signal": {
        "bg": "#0E211D", "surface": "#17312B", "ink": "#F2F5E8", "muted": "#B4C2B9",
        "accent": "#B3E35B", "support": "#51A1C8", "line": "#36574F", "radius": "18px",
        "display": _CONDENSED, "body": _SANS, "utility": _MONO,
        "slide": "background-image:radial-gradient(circle,rgba(179,227,91,.10) 1.5px,transparent 1.8px),linear-gradient(90deg,transparent 49.8%,rgba(81,161,200,.05) 50%,transparent 50.2%);background-size:36px 36px,260px 100%",
        "before": "right:115px;top:88px;width:430px;height:430px;border:3px solid rgba(81,161,200,.28);border-radius:50%;box-shadow:0 0 0 80px rgba(81,161,200,.05),0 0 0 160px rgba(81,161,200,.03)",
        "after": "left:70px;bottom:66px;width:390px;height:5px;background:linear-gradient(90deg,var(--accent) 0 46%,var(--support) 46%)",
    },
    "brave-classroom-contours": {
        "bg": "#F2F0E8", "surface": "#FBFAF5", "ink": "#20352F", "muted": "#66766F",
        "accent": "#D45A3A", "support": "#5F927C", "line": "#C6CEC7", "radius": "56px",
        "display": _SANS, "body": _SANS, "utility": _MONO,
        "slide": (
            "background-image:"
            "radial-gradient(circle at 82% 18%,rgba(95,146,124,.085),transparent 31%),"
            "radial-gradient(circle at 14% 86%,rgba(212,90,58,.050),transparent 29%),"
            "radial-gradient(circle,rgba(32,53,47,.030) 0 1.1px,transparent 1.55px);"
            "background-size:100% 100%,100% 100%,36px 36px"
        ),
        "before": "display:none",
        "after": "display:none",
    },
    "night-transit-wayfinding": {
        "bg": "#15181C", "surface": "#20262B", "ink": "#F7F4E8", "muted": "#AEB3B8",
        "accent": "#FFB33E", "support": "#41C7D9", "line": "#394149", "radius": "8px",
        "display": _CONDENSED, "body": _SANS, "utility": _MONO,
        "slide": "background-image:radial-gradient(circle,rgba(65,199,217,.12) 1.4px,transparent 1.8px);background-size:44px 44px",
        "before": "left:0;top:230px;width:72%;height:7px;background:linear-gradient(90deg,var(--accent),var(--support));transform:rotate(-7deg)",
        "after": "right:85px;top:72px;width:220px;height:220px;border:5px solid var(--support);border-radius:50%;opacity:.28",
    },
    "moonlit-herbarium-atlas": {
        "bg": "#102E2B", "surface": "#173C37", "ink": "#F4EBDD", "muted": "#B7C4BD",
        "accent": "#D9563F", "support": "#6DAA93", "line": "#365D55", "radius": "38px",
        "display": _SERIF, "body": _SANS, "utility": _MONO,
        "slide": "background-image:repeating-radial-gradient(ellipse at 90% 10%,transparent 0 48px,rgba(109,170,147,.10) 49px 52px,transparent 53px 96px)",
        "before": "right:70px;top:70px;width:280px;height:410px;border:4px solid rgba(109,170,147,.25);border-radius:50% 50% 20% 20%",
        "after": "left:80px;bottom:70px;width:240px;height:4px;background:var(--accent)",
    },
}

THEME_CSS = {
    theme_id: _theme_css(theme_id, spec)
    for theme_id, spec in _THEME_SPECS.items()
}

# These two directions intentionally rely on typography, information surfaces,
# quiet CSS patterns and low-contrast gradients. Their cover composition must
# not reintroduce generic rings, blobs or striped illustration stand-ins.
THEME_CSS["neighborhood-newsroom-proof"] += r"""
html[data-theme-id="neighborhood-newsroom-proof"] .cover-signature{display:none}
html[data-theme-id="neighborhood-newsroom-proof"] .cover-kicker{left:150px!important;top:112px!important}
html[data-theme-id="neighborhood-newsroom-proof"] .cover-title{left:150px!important;top:216px!important;width:1320px!important;font-size:132px!important}
html[data-theme-id="neighborhood-newsroom-proof"] .cover-subtitle{left:150px!important;top:570px!important;width:1480px!important}
html[data-theme-id="neighborhood-newsroom-proof"] .cover-meta{left:150px!important;top:806px!important}
html[data-theme-id="neighborhood-newsroom-proof"] .close-signature{display:none}
html[data-theme-id="neighborhood-newsroom-proof"] .close-statement{left:190px!important;top:145px!important;width:1348px!important}
html[data-theme-id="neighborhood-newsroom-proof"] .close-body{left:190px!important;top:500px!important;width:1280px!important}
html[data-theme-id="neighborhood-newsroom-proof"] .close-action{left:190px!important;top:700px!important;width:1280px!important}
html[data-theme-id="neighborhood-newsroom-proof"] .close-meta{left:190px!important;bottom:90px!important}
"""
THEME_CSS["brave-classroom-contours"] += r"""
html[data-theme-id="brave-classroom-contours"] .cover-signature{display:none}
html[data-theme-id="brave-classroom-contours"] .cover-kicker{left:150px!important;top:112px!important}
html[data-theme-id="brave-classroom-contours"] .cover-title{left:150px!important;top:220px!important;width:1320px!important;font-size:132px!important}
html[data-theme-id="brave-classroom-contours"] .cover-subtitle{left:150px!important;top:566px!important;width:1480px!important}
html[data-theme-id="brave-classroom-contours"] .cover-meta{left:150px!important;top:806px!important}
html[data-theme-id="brave-classroom-contours"] .close-signature{display:none}
html[data-theme-id="brave-classroom-contours"] .close-meta{bottom:90px!important}
"""
THEME_CSS["scent-veil-launch"] += r"""
/* Scent Veil V3: explicit page recipes. Background graphics belong to each
   composition instead of repeating one global pseudo-element on every slide. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe]{
  background-color:#FAF4F6;
  background-image:
    linear-gradient(112deg,rgba(173,73,111,.035),transparent 34%),
    radial-gradient(ellipse at 82% 18%,rgba(201,156,169,.12),transparent 30%);
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe]::before,
html[data-theme-id="scent-veil-launch"] .slide[data-recipe]::after{
  content:"";display:block;position:absolute;pointer-events:none;z-index:1
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe] .scene-title{
  font-size:62px;line-height:1.18;letter-spacing:-.035em
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe] .scene-intro{
  font-size:36px;line-height:1.5
}

/* 01 — a perfume label and a veil field frame the launch statement. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"]::before{
  right:128px;top:88px;width:520px;height:842px;border:2px solid rgba(173,73,111,.28);
  border-radius:260px;background:linear-gradient(180deg,rgba(255,253,254,.92),rgba(201,156,169,.10));
  box-shadow:0 42px 90px rgba(77,53,69,.08)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"]::after{
  left:88px;top:118px;width:18px;height:690px;
  background:linear-gradient(var(--accent) 0 24%,transparent 24% 31%,var(--support) 31% 69%,transparent 69% 76%,var(--ink) 76%);
  border-radius:99px;opacity:.9
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-kicker{left:88px;top:104px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-title{
  left:88px;top:232px;width:1060px;font-size:118px;line-height:1.08;letter-spacing:-.055em
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-subtitle{
  left:92px;top:574px;width:1080px;font-size:48px;line-height:1.48
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-meta{left:92px;top:804px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-signature{
  right:72px;top:112px;width:430px;height:646px;border:0;border-radius:0;background:none
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-signature i{
  left:54px;right:28px;width:auto;height:3px;background:var(--accent);transform:rotate(-14deg);opacity:.82
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-signature i:nth-child(1){top:120px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-signature i:nth-child(2){top:220px;left:96px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-signature i:nth-child(3){top:320px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-signature i:nth-child(4){top:420px;left:96px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-cover-perfume-label"] .cover-signature i:nth-child(5){top:520px}

/* 02 — the quote sits inside a memory halo; the three notes form an index. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-thesis-memory-halo"]::before{
  left:186px;top:92px;width:1180px;height:650px;border:2px solid rgba(173,73,111,.20);
  border-radius:50%;box-shadow:0 0 0 92px rgba(201,156,169,.055),0 0 0 184px rgba(201,156,169,.025)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-thesis-memory-halo"]::after{
  left:454px;right:118px;bottom:212px;height:2px;background:linear-gradient(90deg,var(--accent),rgba(173,73,111,.08))
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-thesis-memory-halo"] .thesis-mark{
  left:44px;top:70px;font-size:220px;line-height:.8;color:rgba(173,73,111,.22)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-thesis-memory-halo"] .thesis-quote{
  left:250px;top:126px;width:1250px;font-size:68px;line-height:1.38;letter-spacing:-.04em
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-thesis-memory-halo"] .thesis-attribution{
  left:254px;top:575px;width:1220px;font-size:36px
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-thesis-memory-halo"] .thesis-notes{
  left:254px;right:36px;bottom:28px;display:grid;grid-template-columns:repeat(3,1fr);gap:32px
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-thesis-memory-halo"] .thesis-notes li{
  min-height:118px;padding:26px 18px 18px 64px;border-top:2px solid var(--line);background:rgba(255,253,254,.54)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-thesis-memory-halo"] .thesis-notes b{position:absolute;left:18px;top:30px}

/* 03 — four moments are editorial stations, not generic cards. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-index-four-moments"]::before{
  left:0;right:0;top:454px;height:210px;background:linear-gradient(90deg,transparent,rgba(201,156,169,.12) 18% 82%,transparent)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-index-four-moments"]::after{
  left:145px;top:470px;width:1500px;height:2px;background:var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-index-four-moments"] .index-list{
  left:36px;top:292px;width:1656px;height:470px;display:grid;grid-template-columns:repeat(4,1fr);gap:0;padding:0
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-index-four-moments"] .index-item{
  justify-content:flex-start;padding:28px 32px!important;border-left:2px solid var(--line);background:transparent
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-index-four-moments"] .index-item:last-child{border-right:2px solid var(--line)}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-index-four-moments"] .index-label{font-size:70px;color:var(--accent)}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-index-four-moments"] .index-title{margin-top:46px!important;font-size:44px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-index-four-moments"] .index-body{margin-top:100px!important}

/* 04 — guidance levels use an open editorial column field. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-audience-guidance-columns"]::before{
  right:108px;top:298px;width:760px;height:540px;border:2px solid rgba(173,73,111,.13);border-radius:50%;transform:rotate(-8deg)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-audience-guidance-columns"]::after{
  left:98px;right:98px;bottom:156px;height:1px;background:linear-gradient(90deg,var(--accent),rgba(173,73,111,.08))
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-audience-guidance-columns"] .column-grid{
  left:36px;top:294px;width:1656px;height:430px;display:grid;grid-template-columns:repeat(4,1fr);gap:0
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-audience-guidance-columns"] .column-item{
  height:430px;padding:34px 30px!important;border-left:2px solid var(--line);border-radius:0;background:rgba(255,253,254,.40)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-audience-guidance-columns"] .column-item:last-child{border-right:2px solid var(--line)}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-audience-guidance-columns"] .column-item-bg{background:transparent}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-audience-guidance-columns"] .column-tag{font-size:36px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-audience-guidance-columns"] .column-title{margin-top:66px!important;font-size:42px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-audience-guidance-columns"] .column-body{margin-top:34px!important}

/* 05 — the original memory ring becomes a deliberate 1+6 relationship map. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"]::before{
  left:120px;top:372px;width:520px;height:420px;border:32px solid rgba(201,156,169,.32);border-radius:50%;
  box-shadow:0 0 0 34px rgba(173,73,111,.10),0 0 0 68px rgba(201,156,169,.06)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"]::after{
  left:646px;top:574px;width:1020px;height:3px;background:linear-gradient(90deg,var(--accent),transparent)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"] .map-center{
  left:82px;top:322px;width:540px;height:360px;padding:62px!important;border:0;border-radius:50%;background:rgba(255,253,254,.78)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"] .map-center-bg{background:transparent}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"] .map-center-title{font-size:48px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"] .map-nodes{
  left:670px;top:286px;width:1010px;height:470px;display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(3,1fr);gap:22px 34px
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"] .map-node{
  padding:24px 28px!important;text-align:left;border-radius:0;border-top:2px solid var(--line);background:transparent
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"] .map-node-bg{
  background:linear-gradient(90deg,rgba(255,253,254,.68),transparent);border-radius:0
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"] .map-label{font-size:40px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-map-memory-core"] .map-body{margin-top:10px!important}

/* 06 — four memory signals share one crosshair, without detached cards. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-metrics-memory-signals"]::before{
  left:140px;top:318px;width:1490px;height:470px;background:radial-gradient(ellipse at center,rgba(201,156,169,.13),transparent 62%)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-metrics-memory-signals"]::after{
  left:860px;top:330px;width:2px;height:450px;background:var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-metrics-memory-signals"] .metric-grid{
  left:110px;top:292px;width:1508px;height:480px;display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-metrics-memory-signals"] .metric-item{
  padding:34px 42px!important;border-radius:0;background:transparent
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-metrics-memory-signals"] .metric-slot:nth-child(-n+2) .metric-item{border-bottom:2px solid var(--line)}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-metrics-memory-signals"] .metric-item-bg{background:transparent}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-metrics-memory-signals"] .metric-value{font-size:70px;line-height:1;color:var(--accent)}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-metrics-memory-signals"] .metric-label{font-size:38px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-metrics-memory-signals"] .metric-meaning{font-size:36px}

/* 07 — a single vertical veil separates formula-first from feeling-first. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-contrast-feel-before-formula"]::before{
  left:840px;top:302px;width:210px;height:520px;background:linear-gradient(90deg,transparent,rgba(173,73,111,.10),transparent)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-contrast-feel-before-formula"]::after{
  left:958px;top:300px;width:2px;height:520px;background:var(--accent);opacity:.55
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-contrast-feel-before-formula"] .contrast-grid{
  left:36px;top:286px;width:1656px;height:500px
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-contrast-feel-before-formula"] .contrast-panel{
  padding:40px 60px!important;background:transparent
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-contrast-feel-before-formula"] .contrast-panel-bg{background:transparent;border-radius:0}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-contrast-feel-before-formula"] .contrast-title{font-size:50px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-contrast-feel-before-formula"] .contrast-panel li{padding:14px 0}

/* 08 — chronology is a rail with four anchored moments, never four tall cards. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-timeline-release-rail"]::before{
  left:90px;right:90px;top:516px;height:120px;background:linear-gradient(90deg,transparent,rgba(201,156,169,.14) 12% 88%,transparent)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-timeline-release-rail"]::after{
  right:122px;top:420px;width:180px;height:180px;border:2px solid rgba(173,73,111,.24);border-radius:50%
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-timeline-release-rail"] .timeline-rule{
  left:72px;top:494px;width:1584px;height:4px;background:var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-timeline-release-rail"] .timeline-list{
  left:72px;top:292px;width:1584px;height:430px;display:grid;grid-template-columns:repeat(4,1fr);gap:36px
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-timeline-release-rail"] .timeline-item{
  height:430px;justify-content:flex-start;padding:18px 16px!important;border:0;border-radius:0;background:transparent
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-timeline-release-rail"] .timeline-item::after{
  left:16px;top:186px;width:28px;height:28px;background:var(--accent);box-shadow:0 0 0 8px var(--bg)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-timeline-release-rail"] .timeline-time{font-size:36px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-timeline-release-rail"] .timeline-title{margin-top:32px!important;font-size:42px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-timeline-release-rail"] .timeline-body{margin-top:172px!important}

/* 09 — the table is a paper ledger with one breathing note. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-ledger-touchpoint-breath"]::before{
  left:96px;right:96px;top:326px;height:440px;background:repeating-linear-gradient(0deg,rgba(173,73,111,.035) 0 1px,transparent 1px 88px)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-ledger-touchpoint-breath"]::after{
  left:98px;top:326px;width:12px;height:440px;background:linear-gradient(var(--accent),var(--support))
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-ledger-touchpoint-breath"] .ledger{
  left:36px;top:282px;width:1656px;height:auto;border-top:4px solid var(--ink)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-ledger-touchpoint-breath"] .ledger-row{
  min-height:96px;border-bottom:2px solid var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-ledger-touchpoint-breath"] .ledger-cell{padding:20px 22px!important;font-size:36px;line-height:1.35}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-ledger-touchpoint-breath"] .scene-footer{
  left:36px;bottom:4px;width:1656px;min-height:76px;padding:18px 24px!important;--footer-border-top:2px solid var(--accent);white-space:nowrap
}

/* 10 — three scent trails carry the final statement off the page. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"]::before{
  right:112px;top:104px;width:560px;height:740px;border:2px solid rgba(173,73,111,.25);border-radius:50%;
  box-shadow:0 0 0 58px rgba(201,156,169,.06)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"]::after{
  left:92px;bottom:120px;width:920px;height:2px;background:linear-gradient(90deg,var(--accent),transparent)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-statement{
  left:82px;top:112px;width:1030px;font-size:88px;line-height:1.18;letter-spacing:-.045em
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-body{left:86px;top:510px;width:1040px;font-size:40px;line-height:1.6}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-action{left:86px;top:700px;width:1100px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-meta{left:86px;bottom:34px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-signature{
  right:72px;top:90px;width:480px;height:690px;border:0;background:none
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-signature i{
  left:62px;right:38px;height:5px;background:var(--accent);transform:rotate(-17deg)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-signature i:nth-child(1){top:190px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-signature i:nth-child(2){top:330px;left:104px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-signature i:nth-child(3){top:470px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-close-lingering-trails"] .close-signature i:nth-child(n+4){display:none}
"""

THEME_CSS["scent-veil-launch"] += r"""
/* Scent Veil V4: design comes from type frames, structural rules and one
   continuous editorial thread. No gradient field, haze, ellipse, capsule,
   decorative trail, shadow or large empty card is allowed. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe^="scent-v4-"]{
  background:#FAF7F8!important;background-image:none!important
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe^="scent-v4-"]::before,
html[data-theme-id="scent-veil-launch"] .slide[data-recipe^="scent-v4-"]::after{
  content:none!important;display:none!important;background:none!important;border:0!important;box-shadow:none!important
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe^="scent-v4-"] :is(
  .index-item,.column-item,.map-node,.map-center,.metric-item,.contrast-panel,.timeline-item,
  .index-item-bg,.column-item-bg,.map-node-bg,.map-center-bg,.metric-item-bg,.contrast-panel-bg
){background:transparent!important;background-image:none!important;border-radius:0!important;box-shadow:none!important}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe^="scent-v4-"] .scene-title{
  padding-left:28px!important;border-left:5px solid var(--accent);font-size:62px;line-height:1.16
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe^="scent-v4-"] .scene-intro{
  padding-bottom:18px!important;border-bottom:2px solid var(--line);font-size:36px;line-height:1.45
}

/* 01 — the thread begins inside the title frame, not in the background. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-cover-thread"] .cover-signature{display:none!important}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-cover-thread"] .cover-kicker{
  left:72px;top:70px;width:1584px;padding-bottom:20px!important;border-bottom:2px solid var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-cover-thread"] .cover-title{
  left:72px;top:220px;width:1320px;padding-left:38px!important;border-left:7px solid var(--accent);
  font-size:126px;line-height:1.06
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-cover-thread"] .cover-subtitle{
  left:116px;top:590px;width:1390px;font-size:52px;line-height:1.48
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-cover-thread"] .cover-meta{
  left:116px;top:812px;width:1540px;padding-top:20px!important;border-top:2px solid var(--line)
}

/* 02 — one framed quote and three ruled notes. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-thesis-frame"] .thesis-mark{display:none!important}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-thesis-frame"] .thesis-quote{
  left:92px;top:100px;width:1450px;padding-left:42px!important;border-left:7px solid var(--accent);
  font-size:72px;line-height:1.34
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-thesis-frame"] .thesis-attribution{left:140px;top:570px;width:1380px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-thesis-frame"] .thesis-notes{
  left:140px;right:72px;bottom:44px;display:grid;grid-template-columns:repeat(3,1fr);gap:42px
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-thesis-frame"] .thesis-notes li{
  padding:24px 0 0 58px;border-top:3px solid var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-thesis-frame"] .thesis-notes b{position:absolute;left:0;top:29px}

/* 03 — four open stations share one continuous top rule. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-index-thread"] .index-list{
  left:36px;top:314px;width:1656px;height:382px;display:grid;grid-template-columns:repeat(4,1fr);gap:0;padding:0
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-index-thread"] .index-item{
  height:382px;justify-content:flex-start!important;gap:30px;padding:30px 30px!important;
  border-top:4px solid var(--accent);border-left:2px solid var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-index-thread"] .index-item:first-child{border-left:0}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-index-thread"] .index-label{font-size:58px;color:var(--accent)}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-index-thread"] .index-title{font-size:46px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-index-thread"] .index-body{font-size:36px;line-height:1.48}

/* 04 — guidance levels are columns on the same thread, not cards. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-audience-rules"] .column-grid{
  left:36px;top:306px;width:1656px;height:420px;display:grid;grid-template-columns:repeat(4,1fr);gap:0
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-audience-rules"] .column-item{
  height:420px;justify-content:flex-start!important;gap:34px;padding:28px 30px!important;
  border-top:4px solid var(--accent);border-left:2px solid var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-audience-rules"] .column-item:first-child{border-left:0}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-audience-rules"] .column-tag{font-size:36px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-audience-rules"] .column-title{font-size:44px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-audience-rules"] .column-body{font-size:36px;line-height:1.5}

/* 05 — a framed memory statement and a six-entry ruled index. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-map-index"] .map-links{display:none!important}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-map-index"] .map-center{
  left:48px;top:314px;width:438px;height:330px;padding:38px!important;
  border-left:7px solid var(--accent);border-bottom:3px solid var(--line);text-align:left
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-map-index"] .map-center-title{font-size:48px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-map-index"] .map-center-body{font-size:36px;line-height:1.5}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-map-index"] .map-nodes{
  left:560px;top:292px;width:1132px;height:432px;display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(3,1fr);gap:0
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-map-index"] .map-node{
  justify-content:center!important;gap:14px;padding:22px 30px!important;border-top:2px solid var(--line);border-left:2px solid var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-map-index"] .map-node:nth-child(-n+2){border-top:4px solid var(--accent)}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-map-index"] .map-label{font-size:42px}

/* 06 — four memory signals are separated only by the semantic crosshair. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-metrics-rules"] .metric-grid{
  left:36px;top:302px;width:1656px;height:446px;border-top:4px solid var(--accent)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-metrics-rules"] .metric-item{padding:34px 42px!important}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-metrics-rules"] .metric-value{font-size:66px;color:var(--accent)}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-metrics-rules"] .metric-label{font-size:40px}

/* 07 — one divider connects two editorial arguments. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-contrast-divider"] .contrast-grid{
  left:36px;top:276px;width:1656px;height:500px;border-top:4px solid var(--accent)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-contrast-divider"] .contrast-panel{padding:34px 58px!important}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-contrast-divider"] .contrast-left .contrast-panel-bg{border-right:3px solid var(--line)}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-contrast-divider"] .contrast-title{font-size:50px}

/* 08 — the same thread becomes the actual launch timeline. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-rule{
  left:72px;top:492px;width:1584px;height:4px;background:var(--accent)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-list{
  left:72px;top:292px;width:1584px;height:420px;display:grid;grid-template-columns:repeat(4,1fr);gap:36px
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-item{
  height:420px;justify-content:flex-start!important;padding:18px 18px!important;border:0
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-item::after{
  left:18px;top:186px;width:26px;height:26px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 7px var(--bg)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-time{font-size:36px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-title{margin-top:28px!important;font-size:42px}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-body{margin-top:170px!important}

/* 09 — the thread resolves into a clean ledger rule system. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-ledger-rules"] .ledger{
  left:36px;top:292px;width:1656px;height:auto;border-top:4px solid var(--accent)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-ledger-rules"] .ledger-row{min-height:96px;border-bottom:2px solid var(--line);background:transparent}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-ledger-rules"] .ledger-cell{padding:20px 22px!important;font-size:36px;line-height:1.35}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-ledger-rules"] .scene-footer{
  left:36px;bottom:2px;width:1656px;min-height:74px;padding:18px 0!important;--footer-border-top:3px solid var(--accent);--footer-background:transparent
}

/* 10 — the thread returns to the statement frame and stops. */
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-close-return"] .close-signature{display:none!important}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-close-return"] .close-statement{
  left:82px;top:130px;width:1460px;padding-left:42px!important;border-left:7px solid var(--accent);
  font-size:90px;line-height:1.18
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-close-return"] .close-body{left:130px;top:510px;width:1560px;font-size:40px;line-height:1.58}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-close-return"] .close-action{
  left:130px;top:700px;width:1390px;padding:22px 0!important;border-top:3px solid var(--accent);border-bottom:2px solid var(--line)
}
html[data-theme-id="scent-veil-launch"] .slide[data-recipe="scent-v4-close-return"] .close-meta{left:130px;bottom:40px}

/* Scent Veil V5: keep the accepted V4 editorial structure, but place it on a
   generated raster paper field. The asset is a real background material, not
   CSS-drawn geometry; it contains no text, objects, circles or line motifs. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v5"] .slide[data-recipe^="scent-v4-"]{
  background-color:#FAF7F8!important;
  background-image:url("assets/scent-paper-field-v1.png")!important;
  background-repeat:no-repeat!important;
  background-position:center center!important;
  background-size:cover!important;
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v5"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-item::after{
  box-shadow:0 0 0 7px #FAF7F8
}
/* Scent Veil V6: "veil panes" restore the original Preset's soft rectangular
   content surfaces without repeating one universal card. Every semantic family
   uses the same translucent perfume-paper material with a different silhouette,
   edge rhythm and depth. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe^="scent-v4-"]{
  --veil-fill:rgba(255,252,253,.68);
  --veil-fill-soft:rgba(255,252,253,.50);
  --veil-line:rgba(173,73,111,.22);
  --veil-line-soft:rgba(173,73,111,.14);
  --veil-shadow:0 22px 52px rgba(83,47,69,.10),inset 0 1px 0 rgba(255,255,255,.88);
  --veil-shadow-soft:0 12px 34px rgba(83,47,69,.07),inset 0 1px 0 rgba(255,255,255,.72);
  background-color:#FAF7F8!important;
  background-image:url("assets/scent-paper-field-v1.png")!important;
  background-repeat:no-repeat!important;
  background-position:center center!important;
  background-size:cover!important;
}

/* Quote notes: three low, editorial slips rather than three empty cards. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-thesis-frame"] .thesis-notes li{
  position:relative;background:transparent!important;border:1px solid transparent!important;
  border-top:3px solid transparent!important;border-radius:20px 6px 20px 6px!important;
  box-shadow:none!important;padding:28px 22px 24px 62px!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-thesis-frame"] .thesis-note-bg{
  background:var(--veil-fill-soft)!important;border:1px solid var(--veil-line-soft)!important;
  border-top:3px solid var(--accent)!important;border-radius:inherit!important;
  box-shadow:var(--veil-shadow-soft)!important
}

/* Index: tall staggered perfume blotter panes. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-index-thread"] .index-list{
  top:298px;height:438px;gap:22px
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-index-thread"] .index-item{
  height:408px;background:var(--veil-fill)!important;border:1px solid var(--veil-line)!important;
  border-top:4px solid var(--accent)!important;border-radius:44px 14px 44px 14px!important;
  box-shadow:var(--veil-shadow)!important;padding:32px 30px!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-index-thread"] .index-item:nth-child(even){
  margin-top:22px;border-radius:14px 44px 14px 44px!important;background:rgba(255,252,253,.58)!important
}

/* Audience: slimmer edge-lit columns with alternating softness. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-audience-rules"] .column-grid{
  top:296px;height:438px;gap:18px
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-audience-rules"] .column-item{
  height:414px;background:var(--veil-fill-soft)!important;border:1px solid var(--veil-line-soft)!important;
  border-left:4px solid var(--accent)!important;border-radius:12px 38px 12px 24px!important;
  box-shadow:var(--veil-shadow-soft)!important;padding:30px 30px!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-audience-rules"] .column-item:nth-child(even){
  margin-top:16px;border-radius:38px 12px 24px 12px!important;background:rgba(255,252,253,.62)!important
}

/* Memory map: one anchored core and six small translucent note panes. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-map-index"] .map-center{
  background:var(--veil-fill)!important;border:1px solid var(--veil-line)!important;border-left:7px solid var(--accent)!important;
  border-radius:34px 10px 34px 10px!important;box-shadow:var(--veil-shadow)!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-map-index"] .map-nodes{gap:16px}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-map-index"] .map-node{
  background:var(--veil-fill-soft)!important;border:1px solid var(--veil-line-soft)!important;
  border-radius:18px 6px 18px 6px!important;box-shadow:var(--veil-shadow-soft)!important
}

/* Metrics: luminous quadrants, stronger at the value edge. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-metrics-rules"] .metric-grid{
  top:294px;height:458px;gap:18px;border-top:0
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-metrics-rules"] .metric-item{
  background:var(--veil-fill)!important;border:1px solid var(--veil-line)!important;border-top:4px solid var(--accent)!important;
  border-radius:34px 10px!important;box-shadow:0 18px 46px rgba(83,47,69,.09),0 0 34px rgba(201,156,169,.10),inset 0 1px 0 rgba(255,255,255,.88)!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-metrics-rules"] .metric-item:nth-child(2),
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-metrics-rules"] .metric-item:nth-child(3){border-radius:10px 34px!important}

/* Contrast: two mirrored wide panes rather than two repeated cards. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-contrast-divider"] .contrast-grid{
  top:274px;height:504px;gap:26px;border-top:0
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-contrast-divider"] .scene-content{
  overflow:visible
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-contrast-divider"] .contrast-panel{
  background:var(--veil-fill)!important;border:1px solid var(--veil-line)!important;box-shadow:var(--veil-shadow)!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-contrast-divider"] .contrast-left{
  border-radius:46px 12px 12px 46px!important;border-left:5px solid var(--accent)!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-contrast-divider"] .contrast-right{
  border-radius:12px 46px 46px 12px!important;border-right:5px solid var(--support)!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-contrast-divider"] .contrast-panel-bg{border:0!important;background:transparent!important}

/* Timeline: translucent stage strips sit behind the continuous thread. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-list{gap:28px}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-item{
  background:rgba(255,252,253,.48)!important;border:1px solid var(--veil-line-soft)!important;
  border-radius:36px 10px 36px 10px!important;box-shadow:var(--veil-shadow-soft)!important;padding:24px 24px!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-item:nth-child(even){
  background:rgba(255,252,253,.62)!important;border-radius:10px 36px 10px 36px!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-body{
  margin-top:142px!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-timeline-thread"] .timeline-item::after{
  box-shadow:0 0 0 7px rgba(250,247,248,.94)
}

/* Ledger: one bounded sheet; rows remain rows instead of individual cards. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-ledger-rules"] .ledger{
  overflow:visible!important;background:transparent!important;position:absolute!important;
  border:1px solid transparent!important;border-top:5px solid transparent!important;
  border-radius:30px 10px 30px 10px!important;box-shadow:none!important;padding:5px 1px 1px!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-ledger-rules"] .ledger-sheet-bg{
  background:rgba(255,252,253,.60)!important;border:1px solid var(--veil-line)!important;
  border-top:5px solid var(--accent)!important;border-radius:inherit!important;
  box-shadow:var(--veil-shadow)!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-ledger-rules"] .ledger-row{
  position:relative;background:transparent!important;border-bottom:1px solid transparent!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-ledger-rules"] .ledger-row-bg{
  background:rgba(255,252,253,.36)!important;border-bottom:1px solid var(--veil-line-soft)!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-ledger-rules"] .ledger-header{
  background:transparent!important;border-top:0!important
}
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-ledger-rules"] .ledger-header .ledger-row-bg{
  background:rgba(173,73,111,.08)!important;border-top:0!important
}

/* Close: a short horizontal scent label, not another full card. */
html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe="scent-v4-close-return"] .close-action{
  background:var(--veil-fill-soft)!important;border:1px solid var(--veil-line)!important;border-top:3px solid var(--accent)!important;
  border-radius:26px 8px!important;box-shadow:var(--veil-shadow-soft)!important;padding:24px 30px!important
}
"""

THEME_GRAMMARS = {
    "line-argument-journal": ("line-led-argument", "rail-to-proof-sequence"),
    "signal-route-atlas": ("transfer-atlas-system", "station-to-decision-sequence"),
    "field-index-manual": ("indexed-field-pattern", "catalog-to-handoff-sequence"),
    "tide-signal-observatory": ("tidal-horizon-pattern", "observation-to-action-sequence"),
    "craft-archive-editions": ("woven-archive-pattern", "material-to-provenance-sequence"),
    "incident-command-redline": ("command-stripe-pattern", "incident-to-control-sequence"),
    "harbor-ribbon-program": ("harbor-band-pattern", "program-to-arrival-sequence"),
    "neighborhood-newsroom-proof": ("halftone-proof-pattern", "source-to-public-proof-sequence"),
    "scent-veil-launch": ("editorial-scent-thread", "text-rule-sequence"),
    "restoration-blueprint-ledger": ("blueprint-grid-pattern", "condition-to-restoration-sequence"),
    "ai-operations-signal": ("signal-field-pattern", "governance-to-operation-sequence"),
    "brave-classroom-contours": ("learning-contour-pattern", "question-to-agency-sequence"),
    "night-transit-wayfinding": ("night-route-pattern", "risk-to-safe-arrival-sequence"),
    "moonlit-herbarium-atlas": ("moonlit-contour-pattern", "bloom-to-stewardship-sequence"),
}

THEME_TECHNIQUES = {
    theme_id: [
        "pattern-and-geometry-only",
        "deterministic-composition-variation",
        "independent-header-placement",
        "independent-surface-treatment",
        "minimum-36px-generated-type",
        "editable-text-and-css-geometry",
        f"{dialect_id}-signature",
        composition_mode,
    ]
    for theme_id, (dialect_id, composition_mode) in THEME_GRAMMARS.items()
}
THEME_TECHNIQUES["signal-route-atlas"].extend(["single-transfer-spine", "semantic-surface-variation"])

# Deliberately empty. HTML slide content must not depend on illustration assets.
THEME_ASSET_PROVENANCE: dict[str, list[dict[str, str]]] = {}

# Signal Route Atlas is a transfer-map system, not a decorated card theme.
# One transfer spine changes role on every page: terminal frame, timetable,
# route line, junction, loop, dispatch lane, and status board.
THEME_CSS["signal-route-atlas"] += r"""
html[data-theme-id="signal-route-atlas"] .slide[data-recipe^="route-"]{
  background-color:#F2EFE5!important;
  background-image:
    linear-gradient(rgba(16,42,54,.045) 1px,transparent 1px),
    linear-gradient(90deg,rgba(16,42,54,.045) 1px,transparent 1px)!important;
  background-size:72px 72px!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe^="route-"]::before,
html[data-theme-id="signal-route-atlas"] .slide[data-recipe^="route-"]::after{
  content:none!important;display:none!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe^="route-"] .scene-title{
  font-size:62px;line-height:1.12;letter-spacing:-.04em
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe^="route-"] .scene-intro{
  font-size:36px;line-height:1.4;color:#4E6269
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe^="route-"] :is(
  .index-item-bg,.matrix-item-bg,.ledger-row-bg,.timeline-item-bg
){
  position:absolute!important;inset:0!important;width:100%;height:100%;z-index:0;pointer-events:none
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe^="route-"] :is(
  .index-item,.matrix-item,.ledger-row,.timeline-item
)>*:not(.index-item-bg):not(.matrix-item-bg):not(.ledger-row-bg):not(.timeline-item-bg){
  position:relative;z-index:1
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe^="route-"] .folio{
  color:#4E6269;border-top:2px solid rgba(16,42,54,.18);padding-top:12px
}

/* 01. Terminal window: routes approach the thesis but never cross the type. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature{
  left:60px;top:54px;width:1608px;height:740px;border:0;border-radius:0;z-index:0
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature::before,
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature::after{
  content:"";position:absolute;width:44px;height:44px;border:9px solid #F2EFE5;border-radius:50%;z-index:2
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature::before{
  left:116px;top:118px;background:var(--accent);box-shadow:1230px 34px 0 var(--support)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature::after{
  left:270px;bottom:74px;background:var(--support);box-shadow:980px -32px 0 var(--accent)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature i{
  height:9px;border-radius:0;background:var(--support)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature i:nth-child(1){left:-80px;top:144px;width:520px;transform:rotate(7deg)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature i:nth-child(2){right:-90px;top:178px;width:510px;transform:rotate(-6deg);background:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature i:nth-child(3){left:-50px;bottom:110px;width:600px;transform:rotate(-4deg);background:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature i:nth-child(4){right:-70px;bottom:130px;width:560px;transform:rotate(5deg)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-signature i:nth-child(5){left:170px;right:170px;top:76px;height:588px;border:3px solid rgba(16,42,54,.34);background:transparent!important}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-kicker{
  left:218px;top:86px;width:1292px;text-align:center;z-index:3
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-title{
  left:220px;top:202px;width:1288px;padding:34px 48px!important;border:5px solid var(--ink);
  background:#FAF8F1;text-align:center;font-size:126px;line-height:1.02;z-index:3
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-subtitle{
  left:250px;top:596px;width:1228px;text-align:center;font-size:46px;line-height:1.42;z-index:3
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-meta{
  left:394px;top:798px;width:940px;text-align:center;z-index:3
}

/* 02. A five-stop timetable with one visible transfer spine. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .scene-title{
  left:34px;top:72px;width:430px;font-size:76px;line-height:1.05
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .scene-intro{
  left:38px;top:390px;width:420px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .index-list{
  left:560px;top:34px;width:1132px;height:800px;display:grid;grid-template-rows:repeat(5,1fr);
  padding:0 0 0 64px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .index-list::before{
  content:"";position:absolute;left:25px;top:54px;bottom:54px;width:9px;background:var(--support);z-index:0
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .index-item{
  display:grid!important;grid-template-columns:100px 350px 1fr;align-items:center;gap:22px;
  padding:18px 30px!important;border-bottom:2px solid rgba(16,42,54,.28)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .index-item-bg{
  background:rgba(250,248,241,.72);border-left:8px solid transparent
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .index-item-bg::before{
  content:"";position:absolute;left:-55px;top:calc(50% - 19px);width:38px;height:38px;
  border:8px solid #F2EFE5;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px var(--ink)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .index-item:nth-child(3) .index-item-bg{
  background:rgba(28,119,119,.11);border-left-color:var(--support)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] :is(.index-label,.index-title,.index-body){
  position:relative!important;inset:auto!important;width:auto!important;margin:0!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .index-label{font-size:42px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .index-title{font-size:40px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-index-transfer-spine"] .index-body{font-size:36px;line-height:1.3}

/* 03. One entry rule anchors four independent source platforms. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-grid{
  left:36px;top:250px;width:1656px;height:584px;display:grid;
  grid-template-columns:.94fr 1fr 1fr;grid-template-rows:repeat(2,1fr);gap:18px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-item:first-child{grid-row:1/3}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-item{
  display:flex!important;flex-direction:column;justify-content:center;gap:16px;padding:28px 30px!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-item-bg{
  background:#FAF8F1;border:3px solid rgba(16,42,54,.42);border-top:12px solid var(--support)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-item:nth-child(3) .column-item-bg,
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-item:nth-child(5) .column-item-bg{border-top-color:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-item:first-child .column-item-bg{background:var(--ink);border-color:var(--ink);border-top-color:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-item:first-child :is(.column-tag,.column-title,.column-body){color:#FAF8F1}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-item:first-child .column-title{font-size:56px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-title{font-size:42px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-body{font-size:36px;line-height:1.32}

/* 04. Perforated evidence tickets replace the generic data table. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger{
  left:36px;top:242px;width:1656px;height:490px;display:grid;grid-template-rows:70px repeat(4,1fr);gap:8px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-row{
  display:grid!important;grid-template-columns:.72fr 1.15fr 1.55fr 1.25fr;align-items:center;padding:0!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-row-bg{
  background:#FAF8F1;border:2px dashed rgba(16,42,54,.42)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-row-bg::before,
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-row-bg::after{
  content:"";position:absolute;top:calc(50% - 15px);width:30px;height:30px;border-radius:50%;background:#F2EFE5
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-row-bg::before{left:-16px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-row-bg::after{right:-16px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-header .ledger-row-bg{background:var(--ink);border-style:solid}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-cell{
  padding:.4em .75em!important;font-size:36px;line-height:1.22
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-header .ledger-cell{color:#FAF8F1}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-row:not(.ledger-header)>.ledger-cell:nth-child(2){font-weight:800;color:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .scene-footer{
  left:36px;bottom:0;width:1656px;--footer-background:var(--support);--footer-border:0;--footer-border-top:0;color:#FAF8F1;text-align:center
}

/* 05. Six stops share one main line; the panels are station signs, not cards. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-list{
  left:36px;top:224px;width:1656px;height:420px;display:grid;grid-template-columns:repeat(6,1fr);gap:14px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-line{
  left:90px;top:676px;width:1548px;height:10px;background:linear-gradient(90deg,var(--accent) 0 34%,var(--support) 34% 100%)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-item{
  display:flex!important;justify-content:flex-start;gap:18px;padding:30px 16px!important;text-align:center
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-item-bg{
  background:rgba(250,248,241,.82);border-top:10px solid var(--support);border-bottom:3px solid rgba(16,42,54,.32)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-item:nth-child(-n+2) .flow-item-bg{border-top-color:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-item::after{
  left:calc(50% - 20px);top:calc(100% + 20px);width:40px;height:40px;border:9px solid #F2EFE5;
  background:var(--support);box-shadow:0 0 0 3px var(--ink)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-item:nth-child(-n+2)::after{background:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-label{font-size:42px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-title{font-size:44px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-body{font-size:36px;line-height:1.25}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .scene-footer{
  left:190px;bottom:8px;width:1348px;text-align:center;--footer-border:3px solid var(--ink);--footer-border-top:3px solid var(--ink);--footer-background:#FAF8F1
}

/* 06. A route junction reserves a true label rail around the plot field. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] :is(.matrix-frame,.matrix-items){
  left:110px;top:252px;width:1582px;height:512px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .matrix-frame i:first-child{
  left:calc(50% - 5px);width:10px;background:var(--support)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .matrix-frame i:last-child{
  top:calc(50% - 5px);height:10px;background:var(--accent)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .matrix-item{
  display:flex!important;justify-content:center;padding:22px 40px!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .matrix-item-bg{
  background:rgba(250,248,241,.72);border:2px solid rgba(16,42,54,.16)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .matrix-item:nth-child(2) .matrix-item-bg{
  background:rgba(28,119,119,.14);border:4px solid var(--support)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .matrix-q{font-size:36px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .matrix-title{font-size:44px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .matrix-body{font-size:36px;line-height:1.3}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .axis-1{left:110px;top:782px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .axis-2{right:36px;top:782px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] :is(.axis-3,.axis-4){
  left:36px;width:max-content;transform:rotate(-90deg);transform-origin:left top;text-align:left
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .axis-3{top:746px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-confidence-crossing"] .axis-4{top:500px}

/* 07. Ordered dispatch lanes share one measured ornament reserve. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-grid{
  left:36px;top:182px;width:1656px;height:640px;display:grid;grid-template-rows:repeat(4,1fr);gap:12px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-item{
  --lane-ornament:18px;--lane-ornament-max:72px;--lane-content-inset:34px;
  width:100%;display:grid!important;grid-template-columns:450px 400px minmax(0,1fr);align-items:center;
  padding:18px var(--lane-content-inset) 18px calc(var(--lane-ornament-max) + var(--lane-content-inset))!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-item-bg{
  background:rgba(250,248,241,.82);border-left:var(--lane-ornament) solid var(--support);border-bottom:2px solid rgba(16,42,54,.25)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-item:nth-child(1){--lane-ornament:72px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-item:nth-child(1) .column-item-bg{border-left-color:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-item:nth-child(2){--lane-ornament:54px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-item:nth-child(3){--lane-ornament:36px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-tag{font-size:36px;white-space:nowrap;min-width:0}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-title{font-size:44px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-experiment-dispatch"] .column-body{font-size:36px;line-height:1.28}

/* 08. The explicit editable route loop closes around the decision log. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-route-loop{
  left:630px;top:78px;width:1010px;height:704px;border:9px solid var(--support);
  border-left-color:var(--accent);border-bottom-color:var(--accent);border-radius:50%;z-index:0
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-center{
  left:934px;top:286px;width:390px;height:276px;border:5px solid var(--ink);border-radius:0;background:#FAF8F1;z-index:3
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-center-title{font-size:44px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-center-body{font-size:36px;line-height:1.3}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-nodes{
  left:560px;top:42px;width:1132px;height:792
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-node{
  width:270px;height:158px;padding:22px 20px!important;background:#FAF8F1;text-align:center;border:3px solid var(--ink);z-index:2
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-node:nth-child(1){left:431px;top:0}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-node:nth-child(2){right:0;top:102px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-node:nth-child(3){right:0;bottom:102px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-node:nth-child(4){left:431px;bottom:0}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-node:nth-child(5){left:0;bottom:102px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-node:nth-child(6){left:0;top:102px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-label{font-size:40px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-body{font-size:36px;line-height:1.22}

/* 09. Four parallel service lines stay synchronized across one dispatch table. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger{
  left:36px;top:244px;width:1656px;height:488px;display:grid;grid-template-rows:70px repeat(4,1fr);gap:8px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger-row{
  display:grid!important;grid-template-columns:.72fr 1.22fr 1.22fr 1.22fr;align-items:center;padding:0!important;margin:0!important;width:100%!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger-row-bg{
  background:rgba(250,248,241,.86);border-left:16px solid var(--support);border-bottom:2px solid rgba(16,42,54,.28)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger-header .ledger-row-bg{background:var(--ink);border-left-color:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger-row:nth-child(3) .ledger-row-bg,
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger-row:nth-child(5) .ledger-row-bg{border-left-color:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger-cell{
  padding:.4em .75em!important;font-size:36px;line-height:1.22
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger-row>.ledger-row-bg+.ledger-cell{
  padding-inline-start:1.25em!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger-header .ledger-cell{color:#FAF8F1}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .scene-footer{
  left:36px;bottom:0;width:1656px;text-align:center;--footer-border:3px solid var(--support);--footer-border-top:3px solid var(--support);--footer-background:#FAF8F1
}

/* 10. Operating cadence becomes a vertical timetable beside the narrative. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .scene-title{
  left:1230px;top:76px;width:462px;font-size:72px;line-height:1.06
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .scene-intro{
  left:1232px;top:430px;width:450px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-list{
  left:36px;top:42px;width:1120px;height:792px;display:grid;grid-template-rows:repeat(4,1fr);gap:12px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-rule{
  left:72px;top:82px;width:9px;height:660px;background:linear-gradient(var(--accent) 0 28%,var(--support) 28% 100%)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-item{
  display:grid!important;grid-template-columns:220px 300px 1fr;align-items:center;gap:22px;padding:22px 34px 22px 82px!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-item-bg{
  background:rgba(250,248,241,.84);border-bottom:3px solid rgba(16,42,54,.34)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-item::after{
  left:18px;top:calc(50% - 20px);width:40px;height:40px;border:8px solid #F2EFE5;background:var(--support);box-shadow:0 0 0 3px var(--ink)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-item:first-child::after{background:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] :is(.timeline-time,.timeline-title,.timeline-body){
  position:relative!important;inset:auto!important;width:auto!important;margin:0!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-time{font-size:36px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-title{font-size:42px}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-body{font-size:36px;line-height:1.28}

/* 11. The route-health board wraps its sparse content before centering the full board. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-health-board"] .metric-grid{
  left:36px;top:236px;width:1656px;height:480px;display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-health-board"] .metric-item{
  --health-content-inset-block:28px;--health-content-inset-inline:38px;--health-copy-gap:16px;
  display:grid!important;grid-template-columns:250px minmax(0,1fr);grid-template-rows:max-content max-content;
  align-content:center;align-items:center;column-gap:0;row-gap:var(--health-copy-gap);
  padding:var(--health-content-inset-block) var(--health-content-inset-inline)!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-health-board"] .metric-item-bg{background:rgba(250,248,241,.82)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-health-board"] .metric-item:nth-child(odd) .metric-item-bg{border-right:8px solid var(--support)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-health-board"] .metric-item:nth-child(-n+2) .metric-item-bg{border-bottom:8px solid var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-health-board"] .metric-value{
  position:relative!important;inset:auto!important;font-size:64px;line-height:1;color:var(--accent);grid-row:1/3;align-self:center
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-health-board"] .metric-label{
  position:relative!important;inset:auto!important;font-size:42px;align-self:end
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-health-board"] .metric-meaning{
  position:relative!important;inset:auto!important;font-size:36px;line-height:1.3;align-self:start
}

/* 12. The route resolves into one terminal promise and one next action. */
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-signature{
  left:170px;top:528px;width:1388px;height:178px;border:0;border-radius:0;z-index:0
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-signature i{
  top:78px;height:10px;transform:none;background:var(--support)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-signature i:nth-child(1){left:0;width:34%;background:var(--accent)}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-signature i:nth-child(2){left:34%;width:34%}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-signature i:nth-child(3){left:68%;width:32%}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-signature i::after{
  content:"";position:absolute;right:-20px;top:-15px;width:40px;height:40px;border:8px solid #F2EFE5;border-radius:50%;background:inherit;box-shadow:0 0 0 3px var(--ink)
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-statement{
  left:180px;top:108px;width:1368px;text-align:center;font-size:96px;line-height:1.08;z-index:2
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-body{
  left:284px;top:430px;width:1160px;text-align:center;font-size:42px;line-height:1.45;z-index:2
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-action{
  left:300px;top:716px;width:1128px;padding:20px 26px!important;text-align:center;border:4px solid var(--ink);background:#FAF8F1;z-index:2
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-terminal-close"] .close-meta{
  left:470px;bottom:36px;width:788px;text-align:center;z-index:2
}
"""

# Browser-QA refinements for intentional asymmetry, background-layer contrast,
# and station geometry kept inside each editable module boundary.
THEME_CSS["signal-route-atlas"] += r"""
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-cover-terminal-window"] .cover-subtitle{
  left:164px;width:1400px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-source-platforms"] .column-item:first-child{
  background:var(--ink)!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-row{
  overflow:hidden!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-header{
  background:var(--ink)!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-ticket-taxonomy"] .ledger-cell{
  min-width:0;overflow:hidden
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-line{
  top:618px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-item{
  justify-content:center;overflow:hidden!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-six-stop-mainline"] .flow-item::after{
  top:auto;bottom:4px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-decision-loop"] .map-node{
  height:166px
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-service-blueprint"] .ledger-header{
  background:var(--ink)!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-list{
  grid-template-columns:1fr!important;grid-template-rows:repeat(4,1fr)!important
}
html[data-theme-id="signal-route-atlas"] .slide[data-recipe="route-operating-timetable"] .timeline-item{
  width:100%!important;height:auto!important;margin:0!important;overflow:hidden!important
}
"""
