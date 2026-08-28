"""Ten additional authored HTML Theme Lab visual systems.

The shared composition CSS only supplies safe, editable geometry.  Every theme
then changes the reading axis, background field, surface language and type
hierarchy so the result is not a recoloured copy of another deck.
"""

from __future__ import annotations


def _base(theme_id: str) -> str:
    root = f'html[data-theme-id="{theme_id}"]'
    return f"""
{root} .content{{z-index:2}}
{root} .scene{{overflow:hidden}}
{root} .scene-title{{left:0;top:0;width:1480px;font-size:64px}}
{root} .scene-intro{{left:0;top:92px;width:1460px}}
{root} .cover-kicker{{left:52px;top:78px}}
{root} .cover-title{{left:52px;top:180px;width:1240px;font-size:138px;line-height:1.02}}
{root} .cover-subtitle{{left:56px;top:560px;width:1320px;font-size:60px;line-height:1.32}}
{root} .cover-meta{{left:56px;top:760px}}
{root} .cover-signature{{position:absolute;right:86px;top:94px;width:390px;height:650px}}
{root} .thesis-mark{{left:0;top:72px;font:900 260px/.8 var(--font-display);color:var(--accent);opacity:.16}}
{root} .thesis-quote{{left:150px;top:120px;width:1380px;font:800 70px/1.3 var(--font-display);color:var(--ink)}}
{root} .thesis-attribution{{left:154px;top:500px;width:1100px;font:650 18px/1.4 var(--font-utility);letter-spacing:.08em;color:var(--accent)}}
{root} .thesis-notes{{position:absolute;left:150px;right:70px;top:620px;display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin:0;padding:0;list-style:none}}
{root} .thesis-notes li{{position:relative;min-height:150px;padding:28px 26px 20px 62px}}
{root} .thesis-notes li b{{position:absolute;left:22px;top:31px;font:800 13px/1 var(--font-utility);color:var(--accent)}}
{root} .note-copy{{position:relative!important;font:600 19px/1.55 var(--font-body);color:var(--ink)}}
{root} .index-list{{position:absolute;left:0;right:0;top:220px;bottom:20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:24px}}
{root} .index-item{{position:relative;padding:34px 30px!important}}
{root} .index-label{{left:30px;top:30px}}
{root} .index-title{{left:30px;right:24px;top:86px;font-size:36px}}
{root} .index-body{{left:30px;right:28px;top:160px;font-size:18px}}
{root} .contrast-grid{{position:absolute;left:0;right:0;top:218px;bottom:24px;display:grid;grid-template-columns:1fr 1fr;gap:28px}}
{root} .contrast-panel{{position:relative;padding:42px 44px!important}}
{root} .contrast-label{{left:44px;top:38px}}
{root} .contrast-title{{left:44px;right:36px;top:88px;font-size:43px}}
{root} .contrast-lead{{left:44px;right:42px;top:165px;font-size:19px}}
{root} .contrast-panel ul{{position:absolute;left:44px;right:44px;top:278px;margin:0;padding:0;list-style:none}}
{root} .contrast-panel li{{position:relative;min-height:78px;padding:20px 12px 16px 30px;border-top:1px solid var(--line)}}
{root} .contrast-panel li:before{{content:'—';position:absolute;left:0;color:var(--accent)}}
{root} .item-copy{{position:relative!important;font:600 18px/1.48 var(--font-body);color:var(--ink)}}
{root} .column-grid{{position:absolute;left:0;right:0;top:220px;bottom:26px;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px}}
{root} .column-item{{position:relative;padding:40px 32px!important}}
{root} .column-tag{{left:32px;top:34px}}
{root} .column-title{{left:32px;right:28px;top:94px;font-size:38px}}
{root} .column-body{{left:32px;right:30px;top:174px;font-size:19px;line-height:1.62}}
{root} .flow-list{{position:absolute;left:0;right:0;top:250px;height:390px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:24px}}
{root} .flow-line{{position:absolute;left:60px;right:60px;top:435px;height:2px;background:var(--accent)}}
{root} .flow-item{{position:relative;padding:42px 26px 24px!important}}
{root} .flow-label{{left:26px;top:34px}}
{root} .flow-title{{left:26px;right:22px;top:92px;font-size:32px}}
{root} .flow-body{{left:26px;right:24px;top:164px;font-size:17px}}
{root} .matrix-frame{{position:absolute;left:180px;top:215px;width:1368px;height:560px;border:1px solid var(--line)}}
{root} .matrix-frame i:first-child{{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--line)}}
{root} .matrix-frame i:last-child{{position:absolute;left:0;right:0;top:50%;height:1px;background:var(--line)}}
{root} .matrix-items{{position:absolute;left:180px;top:215px;width:1368px;height:560px}}
{root} .matrix-item{{width:684px;height:280px;padding:34px 38px!important}}
{root} .matrix-item.item-1{{left:0;top:0}}{root} .matrix-item.item-2{{left:684px;top:0}}{root} .matrix-item.item-3{{left:0;top:280px}}{root} .matrix-item.item-4{{left:684px;top:280px}}
{root} .matrix-q{{left:38px;top:34px}}{root} .matrix-title{{left:38px;top:80px;font-size:35px}}{root} .matrix-body{{left:38px;right:34px;top:145px;font-size:18px}}
{root} .axis-label{{font:650 12px/1 var(--font-utility);letter-spacing:.1em;color:var(--muted)}}
{root} .axis-1{{left:180px;top:800px}}{root} .axis-2{{right:180px;top:800px}}{root} .axis-3{{left:68px;top:690px;transform:rotate(-90deg)}}{root} .axis-4{{left:68px;top:330px;transform:rotate(-90deg)}}
{root} .ledger{{left:0;right:0;top:210px;bottom:110px}}
{root} .scene-footer{{left:0;width:100%}}
{root} .timeline-rule{{position:absolute;left:80px;right:80px;top:465px;height:2px;background:var(--line)}}
{root} .timeline-list{{position:absolute;left:0;right:0;top:235px;bottom:70px;display:grid;grid-template-columns:repeat(4,1fr);gap:26px}}
{root} .timeline-item{{position:relative;padding:40px 28px!important}}
{root} .timeline-item:before{{content:'';position:absolute;left:28px;top:221px;width:18px;height:18px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 7px var(--bg)}}
{root} .timeline-time{{left:28px;top:34px}}{root} .timeline-title{{left:28px;right:24px;top:92px;font-size:34px}}{root} .timeline-body{{left:28px;right:26px;top:300px;font-size:18px}}
{root} .map-links{{stroke:var(--line)}}{root} .map-center{{padding:30px!important}}{root} .map-node{{padding:14px 18px!important}}
{root} .metric-grid{{position:absolute;left:0;right:0;top:220px;bottom:40px;display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr);gap:24px}}
{root} .metric-item{{position:relative;padding:40px 42px!important}}
{root} .metric-value{{left:42px;top:36px;font:850 56px/1 var(--font-display);color:var(--accent)}}
{root} .metric-label{{left:270px;right:38px;top:40px;font-size:29px}}
{root} .metric-meaning{{left:270px;right:42px;top:120px;font-size:18px}}
{root} .close-statement{{left:70px;top:100px;width:1240px;font:850 96px/1.24 var(--font-display);letter-spacing:-.04em;color:var(--ink)}}
{root} .close-body{{left:74px;top:520px;width:1070px;font:500 25px/1.6 var(--font-body);color:var(--muted)}}
{root} .close-action{{left:74px;top:710px;width:1160px;padding:20px 24px!important;font:650 20px/1.45 var(--font-body);color:var(--ink)}}
{root} .close-meta{{right:90px;bottom:54px;font:700 13px/1 var(--font-utility);letter-spacing:.14em;color:var(--accent)}}
{root} .close-signature{{position:absolute;right:86px;top:105px;width:350px;height:570px}}
"""


THEME_CSS = {
    "tide-signal-observatory": _base("tide-signal-observatory") + r'''
html[data-theme-id="tide-signal-observatory"]{--bg:#062C33;--ink:#F2F1E8;--muted:#9CC6C7;--accent:#F4C95D;--support:#2DA8A0;--line:#2D6268;--font-display:"Noto Sans TC",sans-serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="tide-signal-observatory"] .slide{background-image:radial-gradient(circle at 82% 20%,transparent 0 190px,rgba(45,168,160,.24) 192px 194px,transparent 196px 258px,rgba(244,201,93,.11) 260px 262px,transparent 264px),linear-gradient(rgba(156,198,199,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(156,198,199,.035) 1px,transparent 1px);background-size:100% 100%,64px 64px,64px 64px}
html[data-theme-id="tide-signal-observatory"] .cover-title{top:248px;width:1080px;font-size:148px}html[data-theme-id="tide-signal-observatory"] .cover-signature{border-radius:50%;border:2px solid var(--support);box-shadow:0 0 0 62px rgba(45,168,160,.08),0 0 0 126px rgba(244,201,93,.05)}html[data-theme-id="tide-signal-observatory"] .cover-signature i{position:absolute;left:50%;top:50%;width:18px;height:18px;border-radius:50%;background:var(--accent)}
html[data-theme-id="tide-signal-observatory"] :is(.column-item,.flow-item,.metric-item,.contrast-panel,.map-node,.map-center,.thesis-notes li){border:1px solid rgba(156,198,199,.22);background:rgba(7,50,58,.72);box-shadow:0 18px 42px rgba(0,0,0,.16)}
html[data-theme-id="tide-signal-observatory"] .map-links{stroke:var(--support);stroke-dasharray:6 12}html[data-theme-id="tide-signal-observatory"] .map-center{border-radius:50%;background:rgba(7,50,58,.92);border:2px solid var(--accent)}html[data-theme-id="tide-signal-observatory"] .map-center :is(.map-center-title,.map-center-body){color:var(--ink)}
html[data-theme-id="tide-signal-observatory"] .timeline-item{border-top:4px solid var(--support)}html[data-theme-id="tide-signal-observatory"] .matrix-item.item-2{background:rgba(244,201,93,.12)}html[data-theme-id="tide-signal-observatory"] .close-signature{border-radius:50%;border:2px solid var(--support);box-shadow:0 0 0 70px rgba(45,168,160,.08)}
''',
    "craft-archive-editions": _base("craft-archive-editions") + r'''
html[data-theme-id="craft-archive-editions"]{--bg:#EFE5D4;--ink:#2B2118;--muted:#625243;--accent:#922E23;--support:#315E57;--line:#CDBDA8;--font-display:"Noto Serif TC",serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="craft-archive-editions"] .slide{background-image:linear-gradient(90deg,transparent 0 128px,rgba(179,58,43,.11) 129px 131px,transparent 132px),radial-gradient(circle,rgba(43,33,24,.05) 0 1px,transparent 1.5px);background-size:100% 100%,7px 7px;box-shadow:inset 0 0 100px rgba(72,45,24,.07)}
html[data-theme-id="craft-archive-editions"] .cover-title{left:160px;top:150px;width:1040px;font-size:128px}html[data-theme-id="craft-archive-editions"] .cover-kicker,html[data-theme-id="craft-archive-editions"] .cover-subtitle,html[data-theme-id="craft-archive-editions"] .cover-meta{left:164px}html[data-theme-id="craft-archive-editions"] .cover-signature{right:70px;border-left:8px solid var(--accent);border-right:1px solid var(--ink);background:repeating-linear-gradient(0deg,transparent 0 76px,var(--line) 77px 78px)}html[data-theme-id="craft-archive-editions"] .cover-signature:before{content:'記\A 憶\A 編\A 目';white-space:pre;position:absolute;left:70px;top:52px;font:800 66px/1.35 var(--font-display);color:var(--support)}
html[data-theme-id="craft-archive-editions"] .index-list{grid-template-columns:1fr;left:120px;right:80px;gap:0}html[data-theme-id="craft-archive-editions"] .index-item{min-height:112px;border-top:1px solid var(--ink);padding:24px 28px!important}html[data-theme-id="craft-archive-editions"] .index-label{top:32px}html[data-theme-id="craft-archive-editions"] .index-title{left:150px;top:23px}html[data-theme-id="craft-archive-editions"] .index-body{left:650px;top:27px}
html[data-theme-id="craft-archive-editions"] :is(.column-item,.metric-item,.contrast-panel,.map-node,.map-center,.thesis-notes li){background:rgba(255,250,240,.72);border-top:5px solid var(--support);box-shadow:0 13px 28px rgba(78,49,28,.09)}html[data-theme-id="craft-archive-editions"] .column-item:nth-child(2n){transform:translateY(42px);border-top-color:var(--accent)}html[data-theme-id="craft-archive-editions"] .ledger-row{background:rgba(255,250,240,.45)}html[data-theme-id="craft-archive-editions"] .close-action{border-left:10px solid var(--accent);background:#fff7ea}html[data-theme-id="craft-archive-editions"] .close-signature{border:1px solid var(--ink);background:repeating-linear-gradient(0deg,transparent 0 62px,var(--line) 63px 64px)}
''',
    "incident-command-redline": _base("incident-command-redline") + r'''
html[data-theme-id="incident-command-redline"]{--bg:#111111;--ink:#F4F1EA;--muted:#AAA59C;--accent:#FF4A3D;--support:#F4C84C;--line:#404040;--font-display:"Barlow Condensed","Noto Sans TC",sans-serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="incident-command-redline"] .slide{background-image:linear-gradient(135deg,transparent 0 72%,rgba(255,74,61,.055) 72% 72.4%,transparent 72.4%),repeating-linear-gradient(0deg,transparent 0 49px,rgba(255,255,255,.025) 50px);box-shadow:inset 0 0 120px #000}
html[data-theme-id="incident-command-redline"] .slide:before{content:'';position:absolute;left:0;right:0;top:0;height:18px;background:repeating-linear-gradient(135deg,var(--accent) 0 22px,#111 22px 44px)}html[data-theme-id="incident-command-redline"] .cover-title{left:0;top:214px;width:1320px;font-size:162px;text-transform:uppercase}html[data-theme-id="incident-command-redline"] .cover-signature{right:0;border:2px solid var(--accent);clip-path:polygon(12% 0,100% 0,100% 88%,88% 100%,0 100%,0 12%);background:rgba(255,74,61,.08)}html[data-theme-id="incident-command-redline"] .cover-signature:before{content:'SEV\A 01';white-space:pre;position:absolute;left:70px;top:110px;font:800 130px/.86 var(--font-display);color:var(--accent)}
html[data-theme-id="incident-command-redline"] :is(.flow-item,.metric-item,.column-item,.contrast-panel,.thesis-notes li){background:#181818;border:1px solid #4a4a4a;box-shadow:9px 9px 0 rgba(255,74,61,.14)}html[data-theme-id="incident-command-redline"] .flow-item{clip-path:polygon(0 0,92% 0,100% 10%,100% 100%,0 100%)}html[data-theme-id="incident-command-redline"] .metric-value{font-size:78px;color:var(--support)}html[data-theme-id="incident-command-redline"] .ledger-header{background:var(--accent)}html[data-theme-id="incident-command-redline"] .ledger-head{color:#111}html[data-theme-id="incident-command-redline"] .matrix-item.item-1,html[data-theme-id="incident-command-redline"] .matrix-item.item-2{background:rgba(255,74,61,.10)}html[data-theme-id="incident-command-redline"] .close-action{border:2px solid var(--accent);background:#181818}html[data-theme-id="incident-command-redline"] .close-signature{clip-path:polygon(0 0,100% 0,100% 85%,85% 100%,0 100%);background:var(--accent)}
''',
    "harbor-ribbon-program": _base("harbor-ribbon-program") + r'''
html[data-theme-id="harbor-ribbon-program"]{--bg:#FFF4D8;--ink:#16325C;--muted:#514A61;--accent:#A62137;--support:#168F8A;--line:#D9C98F;--font-display:"Barlow Condensed","Noto Sans TC",sans-serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="harbor-ribbon-program"] .slide{background-image:repeating-conic-gradient(from 45deg at 92% 8%,rgba(244,91,105,.09) 0 12deg,transparent 12deg 24deg),linear-gradient(125deg,transparent 0 76%,rgba(22,143,138,.09) 76% 82%,transparent 82%);background-size:310px 310px,100% 100%}
html[data-theme-id="harbor-ribbon-program"] .cover-title{left:42px;top:210px;width:1120px;font-size:154px;color:var(--ink)}html[data-theme-id="harbor-ribbon-program"] .cover-signature{right:30px;top:40px;width:520px;height:760px;transform:rotate(6deg);background:linear-gradient(135deg,var(--accent) 0 31%,var(--support) 31% 63%,#F4C84C 63%);clip-path:polygon(18% 0,100% 0,82% 100%,0 100%)}
html[data-theme-id="harbor-ribbon-program"] .index-list{grid-template-columns:repeat(2,1fr);transform:rotate(-1deg)}html[data-theme-id="harbor-ribbon-program"] .index-item{background:#fff;border:3px solid var(--ink);box-shadow:10px 10px 0 var(--accent)}html[data-theme-id="harbor-ribbon-program"] .index-item:nth-child(even){transform:translateY(24px);box-shadow:10px 10px 0 var(--support)}
html[data-theme-id="harbor-ribbon-program"] .column-item{background:#fff;border:3px solid var(--ink)}html[data-theme-id="harbor-ribbon-program"] .column-item:nth-child(odd){transform:translateY(30px)}html[data-theme-id="harbor-ribbon-program"] .timeline-item{background:rgba(255,255,255,.72);border-radius:40px 8px 40px 8px}html[data-theme-id="harbor-ribbon-program"] .metric-item{background:var(--ink);color:#fff;clip-path:polygon(0 0,94% 0,100% 16%,100% 100%,6% 100%,0 84%)}html[data-theme-id="harbor-ribbon-program"] .metric-item :is(.metric-label,.metric-meaning){color:#fff}html[data-theme-id="harbor-ribbon-program"] .close-action{background:var(--accent);color:#fff}html[data-theme-id="harbor-ribbon-program"] .close-signature{transform:rotate(6deg);background:linear-gradient(var(--support),var(--accent));clip-path:polygon(16% 0,100% 0,84% 100%,0 100%)}
html[data-theme-id="harbor-ribbon-program"] .metric-item .metric-value{color:#FFF4D8}
''',
    "neighborhood-newsroom-proof": _base("neighborhood-newsroom-proof") + r'''
html[data-theme-id="neighborhood-newsroom-proof"]{--bg:#F5F0E5;--ink:#17202A;--muted:#4B5660;--accent:#A0241E;--support:#27658A;--line:#B8B1A4;--font-display:"Noto Serif TC",serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="neighborhood-newsroom-proof"] .slide{background-image:linear-gradient(rgba(23,32,42,.028) 1px,transparent 1px),radial-gradient(circle,rgba(23,32,42,.035) 0 1px,transparent 1.4px);background-size:100% 48px,5px 5px}
html[data-theme-id="neighborhood-newsroom-proof"] .cover-title{left:0;top:170px;width:1320px;font-size:142px;border-top:8px solid var(--ink);padding-top:32px!important}html[data-theme-id="neighborhood-newsroom-proof"] .cover-signature{border:1px solid var(--ink);background:repeating-linear-gradient(90deg,transparent 0 62px,var(--line) 63px 64px)}html[data-theme-id="neighborhood-newsroom-proof"] .cover-signature:before{content:'8\A PAGES';white-space:pre;position:absolute;left:58px;top:60px;font:900 110px/.9 var(--font-display);color:var(--accent)}
html[data-theme-id="neighborhood-newsroom-proof"] .column-grid{gap:0}html[data-theme-id="neighborhood-newsroom-proof"] .column-item{border-top:5px solid var(--ink);border-right:1px solid var(--line);background:rgba(255,255,255,.35)}html[data-theme-id="neighborhood-newsroom-proof"] .ledger{border-top:6px solid var(--ink)}html[data-theme-id="neighborhood-newsroom-proof"] .index-item{border-top:1px solid var(--ink);background:rgba(255,255,255,.42)}html[data-theme-id="neighborhood-newsroom-proof"] .contrast-grid{gap:0}html[data-theme-id="neighborhood-newsroom-proof"] .contrast-panel{border-top:6px solid var(--support);background:rgba(255,255,255,.42)}html[data-theme-id="neighborhood-newsroom-proof"] .contrast-right{border-top-color:var(--accent)}html[data-theme-id="neighborhood-newsroom-proof"] .close-action{border-left:9px solid var(--accent);background:#fff}html[data-theme-id="neighborhood-newsroom-proof"] .close-signature{border:2px solid var(--ink);background:repeating-linear-gradient(0deg,transparent 0 44px,var(--line) 45px 46px)}
''',
    "scent-veil-launch": _base("scent-veil-launch") + r'''
html[data-theme-id="scent-veil-launch"]{--bg:#F6F0F3;--ink:#3B2338;--muted:#67515F;--accent:#74304E;--support:#C9907B;--line:#D8C7D1;--font-display:"Noto Serif TC",serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="scent-veil-launch"] .slide{background-image:radial-gradient(circle at 82% 22%,rgba(164,74,109,.14),transparent 28%),radial-gradient(circle at 12% 82%,rgba(201,144,123,.16),transparent 32%),linear-gradient(120deg,rgba(255,255,255,.75),transparent 48%)}
html[data-theme-id="scent-veil-launch"] .cover-title{left:310px;top:205px;width:1080px;text-align:center;font-size:130px}html[data-theme-id="scent-veil-launch"] .cover-kicker,html[data-theme-id="scent-veil-launch"] .cover-meta{left:250px;width:1200px;text-align:center}html[data-theme-id="scent-veil-launch"] .cover-subtitle{left:150px;width:1420px;text-align:center}html[data-theme-id="scent-veil-launch"] .cover-signature{right:550px;top:90px;width:620px;height:620px;border-radius:50%;border:1px solid rgba(164,74,109,.3);box-shadow:0 0 90px rgba(164,74,109,.18);z-index:-1}
html[data-theme-id="scent-veil-launch"] :is(.index-item,.column-item,.metric-item,.contrast-panel,.map-node,.map-center,.thesis-notes li){background:rgba(255,255,255,.55);border:1px solid rgba(164,74,109,.18);border-radius:42px 12px 42px 12px;box-shadow:0 24px 60px rgba(89,51,76,.09);backdrop-filter:blur(12px)}html[data-theme-id="scent-veil-launch"] .index-item:nth-child(even),html[data-theme-id="scent-veil-launch"] .column-item:nth-child(even){transform:translateY(30px)}html[data-theme-id="scent-veil-launch"] .map-links{stroke:var(--accent);opacity:.35}html[data-theme-id="scent-veil-launch"] .map-center{border-radius:50%}html[data-theme-id="scent-veil-launch"] .metric-value{font-family:var(--font-display);font-size:68px}html[data-theme-id="scent-veil-launch"] .close-action{border-radius:30px;background:rgba(255,255,255,.68);box-shadow:0 18px 45px rgba(89,51,76,.09)}html[data-theme-id="scent-veil-launch"] .close-signature{border-radius:50%;border:1px solid var(--accent);box-shadow:0 0 0 64px rgba(164,74,109,.07)}
''',
    "restoration-blueprint-ledger": _base("restoration-blueprint-ledger") + r'''
html[data-theme-id="restoration-blueprint-ledger"]{--bg:#E9E2D2;--ink:#15334B;--muted:#4D5754;--accent:#7D3D20;--support:#386F73;--line:#AEB6AE;--font-display:"Noto Serif TC",serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="restoration-blueprint-ledger"] .slide{background-image:linear-gradient(rgba(21,51,75,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(21,51,75,.045) 1px,transparent 1px),linear-gradient(rgba(21,51,75,.02) 1px,transparent 1px),linear-gradient(90deg,rgba(21,51,75,.02) 1px,transparent 1px);background-size:96px 96px,96px 96px,24px 24px,24px 24px}
html[data-theme-id="restoration-blueprint-ledger"] .cover-title{left:0;top:220px;width:1120px}html[data-theme-id="restoration-blueprint-ledger"] .cover-signature{border:2px solid var(--ink);background:linear-gradient(90deg,transparent 49.7%,var(--ink) 50%,transparent 50.3%),linear-gradient(transparent 49.7%,var(--ink) 50%,transparent 50.3%)}html[data-theme-id="restoration-blueprint-ledger"] .cover-signature:before{content:'± 0.00';position:absolute;left:76px;top:76px;font:800 74px var(--font-utility);color:var(--accent)}
html[data-theme-id="restoration-blueprint-ledger"] :is(.index-item,.column-item,.metric-item,.contrast-panel,.map-node,.map-center){background:rgba(245,239,226,.72);border:1px solid var(--ink);box-shadow:8px 8px 0 rgba(21,51,75,.08)}html[data-theme-id="restoration-blueprint-ledger"] .timeline-item{border-left:3px solid var(--accent)}html[data-theme-id="restoration-blueprint-ledger"] .ledger-row{background:rgba(245,239,226,.58)}html[data-theme-id="restoration-blueprint-ledger"] .matrix-frame{border:2px solid var(--ink)}html[data-theme-id="restoration-blueprint-ledger"] .close-action{border:2px solid var(--ink);background:rgba(245,239,226,.7)}html[data-theme-id="restoration-blueprint-ledger"] .close-signature{border:2px solid var(--ink);background:linear-gradient(45deg,transparent 49.7%,var(--accent) 50%,transparent 50.3%)}
''',
    "ai-operations-signal": _base("ai-operations-signal") + r'''
html[data-theme-id="ai-operations-signal"]{--bg:#101912;--ink:#F2F5E9;--muted:#9FB0A0;--accent:#C8F169;--support:#59A7FF;--line:#405045;--font-display:"Barlow Condensed","Noto Sans TC",sans-serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="ai-operations-signal"] .slide{background-image:linear-gradient(90deg,transparent 0 17%,rgba(200,241,105,.045) 17% 17.2%,transparent 17.2% 82%,rgba(89,167,255,.04) 82% 82.2%,transparent 82.2%),linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px);background-size:100% 100%,100% 64px}
html[data-theme-id="ai-operations-signal"] .cover-title{left:0;top:238px;width:1220px;font-size:156px}html[data-theme-id="ai-operations-signal"] .cover-signature{right:20px;border-left:14px solid var(--accent);background:repeating-linear-gradient(0deg,rgba(200,241,105,.12) 0 2px,transparent 2px 54px)}html[data-theme-id="ai-operations-signal"] .cover-signature:before{content:'MODEL\A →\A WORK';white-space:pre;position:absolute;left:58px;top:74px;font:800 98px/.9 var(--font-display);color:var(--support)}
html[data-theme-id="ai-operations-signal"] .index-list{grid-template-columns:1fr;gap:0}html[data-theme-id="ai-operations-signal"] .index-item{min-height:112px;border-bottom:1px solid var(--line);padding:22px 28px!important}html[data-theme-id="ai-operations-signal"] .index-title{left:180px;top:23px}html[data-theme-id="ai-operations-signal"] .index-body{left:680px;top:27px}html[data-theme-id="ai-operations-signal"] :is(.flow-item,.metric-item,.column-item,.contrast-panel){background:#162219;border-left:8px solid var(--accent)}html[data-theme-id="ai-operations-signal"] .flow-item:nth-child(even),html[data-theme-id="ai-operations-signal"] .metric-item:nth-child(even){border-left-color:var(--support)}html[data-theme-id="ai-operations-signal"] .matrix-item.item-2{background:rgba(200,241,105,.12)}html[data-theme-id="ai-operations-signal"] .ledger-header{background:var(--accent)}html[data-theme-id="ai-operations-signal"] .ledger-head{color:#101912}html[data-theme-id="ai-operations-signal"] .close-action{background:var(--accent);color:#101912}html[data-theme-id="ai-operations-signal"] .close-signature{border-left:14px solid var(--support);background:repeating-linear-gradient(0deg,rgba(89,167,255,.12) 0 2px,transparent 2px 54px)}
''',
    "brave-classroom-contours": _base("brave-classroom-contours") + r'''
html[data-theme-id="brave-classroom-contours"]{--bg:#F7F1DE;--ink:#183E32;--muted:#4F6257;--accent:#9B3E29;--support:#5E9F87;--line:#C9D2C5;--font-display:"Noto Sans TC",sans-serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="brave-classroom-contours"] .slide{background-image:repeating-radial-gradient(ellipse at 105% 105%,transparent 0 92px,rgba(94,159,135,.11) 94px 96px,transparent 98px 152px),radial-gradient(circle at 8% 12%,rgba(227,107,76,.12),transparent 28%)}
html[data-theme-id="brave-classroom-contours"] .cover-title{left:90px;top:190px;width:1050px;font-size:140px}html[data-theme-id="brave-classroom-contours"] .cover-signature{right:40px;border-radius:38% 62% 58% 42%/48% 38% 62% 52%;background:var(--support);box-shadow:0 0 0 50px rgba(94,159,135,.12)}html[data-theme-id="brave-classroom-contours"] .cover-signature:before{content:'聽\A 見';white-space:pre;position:absolute;left:108px;top:110px;font:900 116px/.9 var(--font-display);color:#fff}
html[data-theme-id="brave-classroom-contours"] :is(.column-item,.index-item,.metric-item,.contrast-panel,.map-node,.map-center,.thesis-notes li){background:rgba(255,255,255,.68);border:0;border-radius:34% 66% 48% 52%/18% 24% 76% 82%;box-shadow:0 20px 42px rgba(24,62,50,.10)}html[data-theme-id="brave-classroom-contours"] .column-item:nth-child(even){border-radius:58% 42% 60% 40%/22% 18% 82% 78%;transform:translateY(28px)}html[data-theme-id="brave-classroom-contours"] .map-links{stroke:var(--support);stroke-width:4;opacity:.42}html[data-theme-id="brave-classroom-contours"] .flow-item{background:rgba(255,255,255,.52);border-radius:44px}html[data-theme-id="brave-classroom-contours"] .close-action{border-radius:40px;background:#fff}html[data-theme-id="brave-classroom-contours"] .close-signature{border-radius:42% 58% 60% 40%;background:var(--support)}
''',
    "night-transit-wayfinding": _base("night-transit-wayfinding") + r'''
html[data-theme-id="night-transit-wayfinding"]{--bg:#15181C;--ink:#F7F4E8;--muted:#AEB3B8;--accent:#FFB33E;--support:#41C7D9;--line:#454C52;--font-display:"Barlow Condensed","Noto Sans TC",sans-serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="night-transit-wayfinding"] .slide{background-image:linear-gradient(25deg,transparent 0 49.7%,rgba(65,199,217,.06) 49.8% 50.1%,transparent 50.2%),linear-gradient(-25deg,transparent 0 64.7%,rgba(255,179,62,.06) 64.8% 65.1%,transparent 65.2%),radial-gradient(circle at 84% 20%,rgba(65,199,217,.10),transparent 26%)}
html[data-theme-id="night-transit-wayfinding"] .cover-title{left:0;top:242px;width:1120px;font-size:158px}html[data-theme-id="night-transit-wayfinding"] .cover-signature{right:30px;background:linear-gradient(25deg,transparent 0 48%,var(--accent) 48% 52%,transparent 52%),linear-gradient(-25deg,transparent 0 48%,var(--support) 48% 52%,transparent 52%)}html[data-theme-id="night-transit-wayfinding"] .cover-signature i{position:absolute;width:42px;height:42px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 8px var(--bg)}html[data-theme-id="night-transit-wayfinding"] .cover-signature i:nth-child(1){left:30px;top:470px}html[data-theme-id="night-transit-wayfinding"] .cover-signature i:nth-child(2){left:170px;top:390px;background:var(--support)}html[data-theme-id="night-transit-wayfinding"] .cover-signature i:nth-child(3){right:30px;top:205px}
html[data-theme-id="night-transit-wayfinding"] :is(.timeline-item,.metric-item,.column-item,.contrast-panel,.flow-item){background:#1D2227;border-top:7px solid var(--accent)}html[data-theme-id="night-transit-wayfinding"] :is(.timeline-item,.metric-item,.column-item,.contrast-panel,.flow-item):nth-child(even){border-top-color:var(--support)}html[data-theme-id="night-transit-wayfinding"] .map-links{stroke:var(--support);stroke-width:5}html[data-theme-id="night-transit-wayfinding"] .map-center{border:3px solid var(--accent);border-radius:50%;background:#1D2227}html[data-theme-id="night-transit-wayfinding"] .matrix-frame{border:3px solid var(--line)}html[data-theme-id="night-transit-wayfinding"] .close-action{border:2px solid var(--accent);background:#1D2227}html[data-theme-id="night-transit-wayfinding"] .close-signature{background:linear-gradient(25deg,transparent 0 48%,var(--accent) 48% 52%,transparent 52%),linear-gradient(-25deg,transparent 0 48%,var(--support) 48% 52%,transparent 52%)}
''',
}


THEME_GRAMMARS = {
    "tide-signal-observatory": ("tidal-sonar-field", "radial-evidence-observatory"),
    "craft-archive-editions": ("craft-archive-spine", "editorial-memory-catalog"),
    "incident-command-redline": ("incident-redline-grid", "severity-led-command-room"),
    "harbor-ribbon-program": ("harbor-ribbon-poster", "festival-program-rhythm"),
    "neighborhood-newsroom-proof": ("neighborhood-proof-sheet", "local-newsroom-sequence"),
    "scent-veil-launch": ("scent-veil-field", "soft-focus-brand-ritual"),
    "restoration-blueprint-ledger": ("restoration-measure-grid", "evidence-led-conservation-ledger"),
    "ai-operations-signal": ("ai-signal-axis", "operating-system-decision-path"),
    "brave-classroom-contours": ("classroom-contour-islands", "participation-led-learning-field"),
    "night-transit-wayfinding": ("night-wayfinding-lines", "route-led-resilience-map"),
}


THEME_TECHNIQUES = {
    "tide-signal-observatory": ["sonar-rings", "tidal-grid", "radial-evidence-map", "deep-water-surface", "signal-yellow-marker"],
    "craft-archive-editions": ["vertical-catalog-spine", "paper-grain", "edition-numbering", "offset-archive-block", "vermillion-proof-mark"],
    "incident-command-redline": ["severity-stripe", "clipped-command-plate", "hard-offset-shadow", "terminal-baseline", "redline-priority-field"],
    "harbor-ribbon-program": ["woven-ribbon-field", "staggered-program-block", "poster-cutout", "festival-color-band", "playful-offset-grid"],
    "neighborhood-newsroom-proof": ["newsprint-column", "proof-registration-line", "local-edition-label", "ink-rule-system", "editorial-red-correction"],
    "scent-veil-launch": ["soft-veil-gradient", "frosted-organic-panel", "perfume-note-orbit", "serif-luxury-scale", "muted-rose-depth"],
    "restoration-blueprint-ledger": ["measured-grid", "section-line", "material-ledger", "copper-annotation", "restoration-before-after-frame"],
    "ai-operations-signal": ["decision-axis", "lime-status-strip", "model-to-work-route", "operating-ledger", "non-glow-signal-color"],
    "brave-classroom-contours": ["contour-island", "morph-radius-panel", "participation-cluster", "soft-field-shadow", "coral-response-marker"],
    "night-transit-wayfinding": ["route-crossing", "station-node", "night-contrast", "amber-cyan-status", "wayfinding-condensed-type"],
}
