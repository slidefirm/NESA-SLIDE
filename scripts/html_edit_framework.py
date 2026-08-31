#!/usr/bin/env python3
"""Shared editable-player shell for every generated presentation HTML."""

from __future__ import annotations

import hashlib
import shutil
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EDIT_MODE_SOURCE = PROJECT_ROOT / "src" / "html-editor" / "edit-mode.js"
PPTXGEN_SOURCE = PROJECT_ROOT / "artifacts" / "html-test" / "pptxgen.bundle.js"
PPTX_BROWSER_EXPORT_SOURCE = PROJECT_ROOT / "artifacts" / "html-test" / "pptx-browser-export.js"
PPTX_BROWSER_RUNTIME_BRIDGE = r'''
(function(root){
  // Some local-file WebViews do not expose a top-level `var` as a window
  // property. The editor and browser adapter intentionally use this explicit
  // global contract, so bridge the bundle export before the editor invokes it.
  if (typeof root.PptxGenJS !== 'function' && typeof PptxGenJS === 'function') {
    root.PptxGenJS = PptxGenJS;
  }
  root.__pptxBrowserRuntimeReady = (
    typeof root.PptxGenJS === 'function'
    && typeof root.PptxBrowserExport?.exportManifest === 'function'
  );
})(typeof window !== 'undefined' ? window : globalThis);
'''


EDITABLE_PLAYER_CSS = r"""
:root{--editor-rail-width:232px;--editor-rail-collapsed-width:44px;--editor-topbar-height:142px;--editor-workspace-gap:16px}
#player{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;overflow:hidden;background:#000;transition:background-color .22s ease}
#player.cursor-hidden{cursor:none}
#canvasBox{position:absolute;overflow:hidden}
#stage{position:absolute;left:0;top:0;transform-origin:top left}
#bar{position:absolute;inset-inline:0;bottom:0;z-index:80;display:flex;justify-content:center;padding:0 16px 16px;pointer-events:none;transform:translateY(28px) scale(.94);opacity:0;filter:blur(4px);transition:transform .28s ease,opacity .28s ease,filter .28s ease}
#bar.presentation-reset{transition:none!important}
#bar.show,#bar.editor-active{transform:none;opacity:1;filter:none}
#barInner{pointer-events:auto;display:flex;align-items:center;gap:4px;min-height:44px;max-width:calc(100vw - 32px);padding:0 8px;border:1px solid rgba(255,255,255,.14);border-radius:999px;background:rgba(8,8,8,.72);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);color:rgba(255,255,255,.88);box-shadow:0 10px 36px rgba(0,0,0,.55);overflow:hidden}
#bar:not(.show):not(.editor-active) #barInner{pointer-events:none}
#barInner button{width:32px;height:32px;padding:0;border:0;border-radius:999px;background:transparent;color:inherit;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;flex:0 0 auto}
#barInner button:hover{background:rgba(255,255,255,.12)}
#barInner button:disabled{opacity:.3;pointer-events:none}
#barInner svg{width:17px;height:17px;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round;stroke-linejoin:round}
#barInner .divider{width:1px;height:16px;margin:0 4px;background:rgba(255,255,255,.16);flex:0 0 auto}
#barInner .counter{padding:0 7px;font:600 11px/1 var(--font-mono);letter-spacing:.08em;white-space:nowrap;color:rgba(255,255,255,.78)}
#barInner .edit-mode-label{display:none;align-items:center;gap:8px;padding:0 10px;color:#eef2f7;font:750 12px/1 var(--font-body);letter-spacing:.04em;white-space:nowrap}
#barInner .edit-mode-label:before{content:"";width:7px;height:7px;border-radius:50%;background:#3fd0e8;box-shadow:0 0 0 4px rgba(63,208,232,.12)}
#player.editor-shell #barInner .presentation-only{display:none!important}
#player:not(.editor-shell) #barInner .edit-only{display:none!important}
#player.editor-shell #barInner .edit-mode-label{display:inline-flex}
#player.editor-shell #barInner .mode-toggle{margin-left:auto;background:rgba(63,208,232,.1);color:#6be2f3}
#slideRail{position:absolute;left:0;top:0;bottom:0;width:var(--editor-rail-width);z-index:90;display:none;box-sizing:border-box;background:#15181d;border-right:1px solid rgba(255,255,255,.1);color:#eef2f7;box-shadow:12px 0 32px rgba(0,0,0,.28)}
#slideRailHeader{height:62px;box-sizing:border-box;padding:13px 16px 10px;border-bottom:1px solid rgba(255,255,255,.08);display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
#slideRailHeader strong{font:750 14px/1.2 var(--font-body);letter-spacing:.04em}
#slideRailHeader span{font:500 10px/1.35 var(--font-body);color:rgba(238,242,247,.52);text-align:right}
#slideRailToggle{width:30px;height:30px;flex:0 0 30px;margin:-6px -7px 0 0;padding:0;border:0;border-radius:8px;background:transparent;color:rgba(238,242,247,.72);display:inline-flex;align-items:center;justify-content:center;cursor:pointer}
#slideRailToggle:hover{background:rgba(255,255,255,.08);color:#fff}
#slideRailToggle:focus-visible{outline:2px solid #3fd0e8;outline-offset:2px}
#slideRailToggle svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform .18s ease}
#slideThumbList{height:calc(100% - 62px);box-sizing:border-box;overflow-y:auto;padding:12px 12px 24px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.24) transparent}
.slide-thumb{width:100%;box-sizing:border-box;display:grid;grid-template-columns:26px minmax(0,1fr);gap:8px;align-items:start;padding:7px 6px;margin:0 0 7px;border:1px solid transparent;border-radius:10px;background:transparent;color:inherit;text-align:left;cursor:pointer}
.slide-thumb:hover{background:rgba(255,255,255,.055)}
.slide-thumb.active{background:rgba(63,208,232,.09);border-color:rgba(63,208,232,.62)}
.slide-thumb.drag-before{box-shadow:inset 0 3px 0 #3fd0e8}
.slide-thumb.drag-after{box-shadow:inset 0 -3px 0 #3fd0e8}
.slide-thumb-number{padding-top:5px;font:700 11px/1 var(--font-mono);color:rgba(238,242,247,.58);text-align:center}
.slide-thumb.active .slide-thumb-number{color:#3fd0e8}
.slide-thumb-preview{position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;border-radius:5px;background:#05070a;box-shadow:0 0 0 1px rgba(255,255,255,.12),0 4px 12px rgba(0,0,0,.25);isolation:isolate}
.slide-thumb-canvas{position:absolute!important;left:0!important;top:0!important;width:1920px!important;height:1080px!important;margin:0!important;display:block!important;visibility:visible!important;transform-origin:top left!important;pointer-events:none!important;user-select:none!important;box-shadow:none!important}
.slide-thumb-canvas *{pointer-events:none!important}
#player.editor-shell{background:#24272d}
#player.editor-shell #slideRail{display:block}
#player.editor-shell #bar{left:var(--editor-rail-width);right:0;top:0;bottom:auto;box-sizing:border-box;height:var(--editor-topbar-height);padding:7px 10px;justify-content:flex-start;align-items:stretch;flex-direction:column;gap:6px;transform:none;opacity:1;filter:none;background:#15181d;border-bottom:1px solid rgba(255,255,255,.1);pointer-events:auto;transition:none}
#player.editor-shell.rail-collapsed #slideRail{width:var(--editor-rail-collapsed-width);box-shadow:none}
#player.editor-shell.rail-collapsed #slideRailHeader{padding:13px 6px 10px;justify-content:center}
#player.editor-shell.rail-collapsed #slideRailHeader strong,#player.editor-shell.rail-collapsed #slideRailHeader span{display:none}
#player.editor-shell.rail-collapsed #slideRailToggle{margin:-6px 0 0}
#player.editor-shell.rail-collapsed #slideRailToggle svg{transform:rotate(180deg)}
#player.editor-shell.rail-collapsed #slideThumbList{display:none}
#player.editor-shell.rail-collapsed #bar{left:var(--editor-rail-collapsed-width)}
#player.editor-shell #barInner{width:100%;max-width:none;min-height:42px;flex:0 0 42px;box-sizing:border-box;border:0;border-radius:8px;background:rgba(255,255,255,.045);box-shadow:none;overflow-x:auto;overflow-y:hidden;justify-content:flex-start}
#player.editor-shell #bar:not(.show):not(.editor-active) #barInner{pointer-events:auto}
#player.editor-shell #hint{display:none!important}
#hint{display:none!important;position:absolute;right:18px;bottom:18px;z-index:70;color:rgba(255,255,255,.46);font:500 13px/1.35 var(--font-body);letter-spacing:.03em;pointer-events:none;transition:opacity .25s}
#hint.hide{opacity:0}
"""


PLAYER_RUNTIME = r"""
(function(){
  const CW=__CW__,CH=__CH__;
  const player=document.getElementById('player');
  const box=document.getElementById('canvasBox');
  const stage=document.getElementById('stage');
  let slides=Array.from(stage.querySelectorAll(':scope > .slide'));
  const bar=document.getElementById('bar');
  const barInner=document.getElementById('barInner');
  const hint=document.getElementById('hint');
  const slideRail=document.getElementById('slideRail');
  const thumbList=document.getElementById('slideThumbList');
  const slideRailToggle=document.getElementById('slideRailToggle');
  let current=0,editActive=true,hideTimer=null,counter=null;
  let railCollapsed=false;
  let draggedSlideId=null;
  let thumbPointerDrag=null,suppressThumbClick=false;
  const GENERATED_TEXT_MIN_PX=36;
  // A module may originate from a renderer with independently positioned
  // label/title/body layers. Resolve their real post-font gap before freezing
  // geometry so hard-coded source offsets cannot collapse readable text.
  const MIN_SEMANTIC_TEXT_STACK_GAP=16;
const EDIT_GROUP_FIT_VERSION='visible-union-v8-font-ready';
  const PRESENTATION_BAR_TRIGGER_PX=112;
  const PRESENTATION_BAR_LEAVE_DELAY_MS=140;
  function slidesIn(scope){
    const root=scope||document;
    if(root.matches?.('.slide'))return [root];
    return Array.from(root.querySelectorAll('.slide'));
  }
  function fitGeneratedEditGroup(group){
    if(!group||(group.dataset.editFitMaterialized==='true'&&group.dataset.editFitVersion===EDIT_GROUP_FIT_VERSION))return false;
    const titleFlowStack=group.classList.contains('title-flow-stack')||((group.firstElementChild&&group.firstElementChild.classList.contains('scene-title-stack')));
    if(titleFlowStack&&document.documentElement.dataset.layoutFontsReady!=='true')return false;
    const isVisible=(child)=>{
      const style=getComputedStyle(child);
      const rect=child.getBoundingClientRect();
      return style.display!=='none'&&style.visibility!=='hidden'&&rect.width>0.5&&rect.height>0.5;
    };
    const directChildren=Array.from(group.children).filter(isVisible);
    if(!directChildren.length)return false;
    const measurementChildren=directChildren.flatMap((child)=>{
      if(!child.matches('[data-edit-layout-only="true"]'))return [child];
      return Array.from(child.querySelectorAll('.el')).filter((root)=>{
        const parentRoot=root.parentElement&&root.parentElement.closest('.el');
        return parentRoot===group&&isVisible(root);
      });
    });
    if(!measurementChildren.length)return false;
    const groupRect=group.getBoundingClientRect();
    const scaleX=group.offsetWidth?groupRect.width/group.offsetWidth:1;
    const scaleY=group.offsetHeight?groupRect.height/group.offsetHeight:1;
    const visibleRect=(child,layoutRect)=>{
      const layer=child.dataset?child.dataset.editLayer:'';
      const tightText=!!(child.dataset&&child.dataset.editFit==='text')||layer==='text'||layer==='metric';
      if(!tightText||!(child.textContent||'').trim())return layoutRect;
      const style=getComputedStyle(child);
      const borderWidth=['borderLeftWidth','borderRightWidth','borderTopWidth','borderBottomWidth']
        .reduce((sum,key)=>sum+(parseFloat(style[key])||0),0);
      const background=String(style.backgroundColor||'');
      const decorated=borderWidth>0.5
        ||(style.backgroundImage&&style.backgroundImage!=='none')
        ||(background&&background!=='transparent'&&!/rgba?\([^)]*,\s*0(?:\.0+)?\s*\)$/.test(background));
      if(decorated)return layoutRect;
      const range=document.createRange();
      range.selectNodeContents(child);
      const textRect=range.getBoundingClientRect();
      return textRect.width>0.5&&textRect.height>0.5?textRect:layoutRect;
    };
    const measuredBoxes=measurementChildren.map((child)=>{
      const layoutRect=child.getBoundingClientRect();
      const rect=visibleRect(child,layoutRect);
      return {
        left:(rect.left-groupRect.left)/scaleX,
        top:(rect.top-groupRect.top)/scaleY,
        width:rect.width/scaleX,
        height:rect.height/scaleY,
      };
    });
    const left=Math.min(...measuredBoxes.map((box)=>box.left));
    const top=Math.min(...measuredBoxes.map((box)=>box.top));
    const right=Math.max(...measuredBoxes.map((box)=>box.left+box.width));
    const bottom=Math.max(...measuredBoxes.map((box)=>box.top+box.height));
    const round=(value)=>Math.round(value*10)/10;
    const translateToken=(token,size)=>{
      if(!token||token==='none'||token==='0'||token==='0px')return 0;
      if(token.endsWith('%'))return (parseFloat(token)||0)*size/100;
      const value=parseFloat(token);
      return Number.isFinite(value)?value:0;
    };
    const sourceLeft=group.offsetLeft;
    const sourceTop=group.offsetTop;
    directChildren.map((child)=>{
      const layoutRect=child.getBoundingClientRect();
      const rect=visibleRect(child,layoutRect);
      return {
        child,
        left:(rect.left-groupRect.left)/scaleX,
        top:(rect.top-groupRect.top)/scaleY,
        width:rect.width/scaleX+((rect===layoutRect)?0:2),
        height:rect.height/scaleY,
      };
    }).forEach(({child,left:layoutLeft,top:layoutTop,width:layoutWidth,height:layoutHeight})=>{
      // The visible-union bounds already include an element's individual
      // translate. Repositioning from that visible rect must compensate for
      // the translate, otherwise a centered child (translate:-50%) is shifted
      // twice after the group is shrunk to its visible bounds.
      const translateTokens=String(getComputedStyle(child).translate||'').trim().split(/\s+/).filter(Boolean);
      const translateX=translateToken(translateTokens[0],layoutWidth);
      const translateY=translateToken(translateTokens[1]||'0',layoutHeight);
      child.style.setProperty('position','absolute','important');
      child.style.setProperty('left',round(layoutLeft-left-translateX)+'px','important');
      child.style.setProperty('top',round(layoutTop-top-translateY)+'px','important');
      child.style.setProperty('width',round(layoutWidth)+'px','important');
      child.style.setProperty('height',round(layoutHeight)+'px','important');
      child.style.setProperty('right','auto','important');
      child.style.setProperty('bottom','auto','important');
      child.style.setProperty('margin','0','important');
    });
    group.style.setProperty('left',round(sourceLeft+left)+'px','important');
    group.style.setProperty('top',round(sourceTop+top)+'px','important');
    group.style.setProperty('width',round(right-left)+'px','important');
    group.style.setProperty('height',round(bottom-top)+'px','important');
    group.dataset.editFitMaterialized='true';
    group.dataset.editFitVersion=EDIT_GROUP_FIT_VERSION;
    return true;
  }
  function fitGeneratedEditGroups(root){
    let fitted=0;
    slidesIn(root).forEach((slide)=>{
      const visible=slide.classList.contains('active');
      const previousDisplay=slide.style.display;
      const previousVisibility=slide.style.visibility;
      const previousOpacity=slide.style.opacity;
      const previousPointerEvents=slide.style.pointerEvents;
      if(!visible){
        slide.style.display='block';
        // visibility:hidden is inherited and made every child fail the
        // visibility predicate. Opacity keeps the slide measurable without
        // exposing it or allowing pointer interaction.
        slide.style.visibility='visible';
        slide.style.opacity='0';
        slide.style.pointerEvents='none';
      }
      slide.querySelectorAll('[data-edit-fit-children="true"]').forEach((group)=>{
        if(fitGeneratedEditGroup(group))fitted+=1;
      });
      if(!visible){
        slide.style.display=previousDisplay;
        slide.style.visibility=previousVisibility;
        slide.style.opacity=previousOpacity;
        slide.style.pointerEvents=previousPointerEvents;
      }
    });
    document.documentElement.dataset.editFitGroups=String(fitted);
    return fitted;
  }
  function hasDirectText(node){
    return Array.from(node.childNodes||[]).some((child)=>child.nodeType===Node.TEXT_NODE&&(child.textContent||'').trim());
  }
  function enforceGeneratedTextMinimum(root){
    const html=document.documentElement;
    if(html.dataset.aiFontFloorApplied==='true')return;
    slidesIn(root).forEach((slide)=>{
      Array.from(slide.querySelectorAll('*')).forEach((node)=>{
        if(!hasDirectText(node)||/^(SCRIPT|STYLE|NOSCRIPT)$/.test(node.tagName))return;
        const style=getComputedStyle(node);
        const size=parseFloat(style.fontSize);
        if(Number.isNaN(size)||size>=GENERATED_TEXT_MIN_PX)return;
        const lineHeight=parseFloat(style.lineHeight);
        const ratio=!Number.isNaN(lineHeight)&&size>0?Math.max(1,lineHeight/size):null;
        node.style.setProperty('font-size',GENERATED_TEXT_MIN_PX+'px','important');
        if(ratio!==null)node.style.setProperty('line-height',Math.round(GENERATED_TEXT_MIN_PX*ratio*10)/10+'px','important');
        node.dataset.aiFontFloor=String(GENERATED_TEXT_MIN_PX);
      });
    });
    html.dataset.aiFontFloor=String(GENERATED_TEXT_MIN_PX);
    html.dataset.aiFontFloorApplied='true';
  }
  // Glyph-level line reconstruction. Author <br> breaks are real lines here, so
  // wrap-quality passes can still read a headline that carries a manual break.
  function textLineRuns(node,options){
    if(!node)return null;
    // Off-screen slides are laid out under visibility:hidden so every page can
    // resolve geometry without flashing. That state still produces real glyph
    // rects, so a caller doing the hiding may opt out of the visibility test.
    const ignoreVisibility=!!(options&&options.ignoreVisibility);
    const style=getComputedStyle(node);
    const box=node.getBoundingClientRect();
    if(style.display==='none'||(!ignoreVisibility&&style.visibility==='hidden')||style.writingMode.startsWith('vertical')||box.width<=0||box.height<=0)return null;
    const fontSize=parseFloat(style.fontSize)||0;
    const scale=Math.max(node.offsetWidth?box.width/node.offsetWidth:1,0.0001);
    const glyphs=[];
    const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);
    while(walker.nextNode()){
      const textNode=walker.currentNode;
      const parentStyle=getComputedStyle(textNode.parentElement||node);
      if(parentStyle.display==='none'||(!ignoreVisibility&&parentStyle.visibility==='hidden'))continue;
      for(let offset=0;offset<textNode.data.length;){
        const char=String.fromCodePoint(textNode.data.codePointAt(offset));
        const nextOffset=offset+char.length;
        if(!/\s/u.test(char)){
          const range=document.createRange();
          range.setStart(textNode,offset);
          range.setEnd(textNode,nextOffset);
          const rect=range.getBoundingClientRect();
          if(rect.width>0&&rect.height>0)glyphs.push({char,left:rect.left,right:rect.right,top:rect.top});
        }
        offset=nextOffset;
      }
    }
    if(!glyphs.length)return null;
    glyphs.sort((first,second)=>first.top-second.top||first.left-second.left);
    const tolerance=Math.max(2,fontSize*scale*0.18);
    const rows=[];
    glyphs.forEach((glyph)=>{
      let row=rows.find((candidate)=>Math.abs(candidate.top-glyph.top)<=tolerance);
      if(!row){row={top:glyph.top,glyphs:[]};rows.push(row)}
      row.glyphs.push(glyph);
    });
    const lines=rows.sort((first,second)=>first.top-second.top).map((row)=>{
      const ordered=row.glyphs.sort((first,second)=>first.left-second.left);
      const left=Math.min(...ordered.map((glyph)=>glyph.left));
      const right=Math.max(...ordered.map((glyph)=>glyph.right));
      return {
        text:ordered.map((glyph)=>glyph.char).join(''),
        width:Math.max(0,(right-left)/scale),
      };
    });
    return {scale,lines};
  }
  function textLineSummary(node){
    if(!node||node.querySelector('br'))return null;
    const runs=textLineRuns(node);
    if(!runs)return null;
    const lineTexts=runs.lines.map((line)=>line.text);
    const tailText=lineTexts.at(-1)||'';
    const tailCore=tailText.replace(/[，。！？、；：,.!?;:（）()「」『』【】《》〈〉—–·…]/gu,'');
    const allCore=lineTexts.join('').replace(/[^\p{Script=Han}]/gu,'');
    return {
      lineTexts,
      tailText,
      orphan:lineTexts.length>1&&allCore.length>=6&&/^[\p{Script=Han}]{1,2}$/u.test(tailCore),
    };
  }
  function repairGeneratedTextOrphans(root){
    let adjusted=0,unresolved=0;
    slidesIn(root).forEach((slide)=>{
      const visible=slide.classList.contains('active');
      const previousDisplay=slide.style.display;
      const previousVisibility=slide.style.visibility;
      const previousOpacity=slide.style.opacity;
      const previousPointerEvents=slide.style.pointerEvents;
      if(!visible){slide.style.display='block';slide.style.visibility='hidden'}
      const selector='[data-edit-layer="text"],[data-edit-kind="text"]';
      Array.from(slide.querySelectorAll(selector)).filter((node)=>!node.querySelector(selector)).forEach((node)=>{
        let summary=textLineSummary(node);
        if(!summary?.orphan)return;
        const computed=getComputedStyle(node);
        const originalSize=parseFloat(computed.fontSize)||0;
        const lineHeight=parseFloat(computed.lineHeight);
        const ratio=!Number.isNaN(lineHeight)&&originalSize>0?Math.max(1,lineHeight/originalSize):null;
        let size=originalSize;
        while(summary?.orphan&&size>GENERATED_TEXT_MIN_PX){
          const next=Math.max(GENERATED_TEXT_MIN_PX,size-1);
          if(next===size)break;
          size=next;
          node.style.setProperty('font-size',size+'px','important');
          if(ratio!==null)node.style.setProperty('line-height',(Math.round(size*ratio*10)/10)+'px','important');
          summary=textLineSummary(node);
        }
        if(size!==originalSize){
          node.dataset.aiOrphanOriginalFont=String(originalSize);
          node.dataset.aiOrphanAdjustedFont=String(size);
          adjusted+=1;
        }
        if(summary?.orphan){
          node.dataset.aiOrphanUnresolved='true';
          unresolved+=1;
        }else{
          delete node.dataset.aiOrphanUnresolved;
        }
      });
      if(!visible){slide.style.display=previousDisplay;slide.style.visibility=previousVisibility}
    });
    document.documentElement.dataset.aiOrphanAdjusted=String(adjusted);
    document.documentElement.dataset.aiOrphanUnresolved=String(unresolved);
    return {adjusted,unresolved};
  }
  // A headline that runs past its authored max-width breaks on pure character
  // fit. CJK copy has no spaces, so that break can split a word and strand a
  // short tail, and the later fit-to-text pass then freezes the box around the
  // stranded result. Reclaim the horizontal room the layout already owns before
  // any geometry is frozen. Only widen, never shrink, and only for headline
  // roles whose current break is measurably lopsided.
  const HEADLINE_RELAX_MIN_PX=52;
  const HEADLINE_RELAX_TAIL_RATIO=0.5;
  function availableTextWidth(element){
    const parent=element.parentElement;
    if(!parent)return 0;
    const parentWidth=parent.clientWidth||parent.offsetWidth||0;
    if(parentWidth<=0)return 0;
    const style=getComputedStyle(element);
    if(style.position!=='absolute')return parentWidth;
    const left=element.offsetLeft;
    if((style.translate||'').indexOf('-50%')>=0)return Math.max(0,Math.min(left,parentWidth-left)*2);
    return Math.max(0,parentWidth-left);
  }
  function naturalTextWidth(element,scale){
    const previousWhiteSpace=element.style.whiteSpace;
    const previousMaxWidth=element.style.maxWidth;
    const previousWidth=element.style.width;
    element.style.whiteSpace='nowrap';
    element.style.maxWidth='none';
    element.style.width='max-content';
    const range=document.createRange();
    range.selectNodeContents(element);
    const measured=range.getBoundingClientRect().width/scale;
    element.style.whiteSpace=previousWhiteSpace;
    element.style.maxWidth=previousMaxWidth;
    element.style.width=previousWidth;
    return measured;
  }
  function relaxGeneratedTextWrapping(root){
    let relaxed=0;
    slidesIn(root).forEach((slide)=>{
      const visible=slide.classList.contains('active');
      const previousDisplay=slide.style.display;
      const previousVisibility=slide.style.visibility;
      if(!visible){slide.style.display='block';slide.style.visibility='hidden'}
      const slideRect=slide.getBoundingClientRect();
      const scale=Math.max(slide.offsetWidth?slideRect.width/slide.offsetWidth:1,0.0001);
      slide.querySelectorAll('.el[data-edit-fit="text"]').forEach((element)=>{
        if(!element.textContent.trim())return;
        if(element.dataset.overflowIntent==='clip'||element.dataset.orphanIntentional==='true')return;
        const style=getComputedStyle(element);
        if(style.writingMode.startsWith('vertical'))return;
        if((parseFloat(style.fontSize)||0)<HEADLINE_RELAX_MIN_PX)return;
        const before=textLineRuns(element,{ignoreVisibility:true});
        if(!before||before.lines.length<2)return;
        const widest=Math.max(...before.lines.map((line)=>line.width));
        const tail=before.lines[before.lines.length-1].width;
        if(widest<=0||tail/widest>=HEADLINE_RELAX_TAIL_RATIO)return;
        const current=element.getBoundingClientRect().width/scale;
        const natural=naturalTextWidth(element,scale);
        if(natural<=current+1)return;
        const target=Math.min(availableTextWidth(element),natural);
        if(target<=current+1)return;
        const previousMaxWidth=element.style.maxWidth;
        element.style.maxWidth=Math.ceil(target)+'px';
        const after=textLineRuns(element,{ignoreVisibility:true});
        if(!after||after.lines.length>=before.lines.length){
          element.style.maxWidth=previousMaxWidth;
          return;
        }
        element.dataset.textWrapRelaxed=Math.ceil(target)+'px';
        relaxed+=1;
      });
      if(!visible){slide.style.display=previousDisplay;slide.style.visibility=previousVisibility}
    });
    document.documentElement.dataset.textWrapRelaxed=String(relaxed);
    return relaxed;
  }
  function directLayoutChildren(area){
    return Array.from(area.children).filter((child)=>child.matches('.el,[data-layout-item]'));
  }
  function measuredLayoutBox(area,child){
    const areaRect=area.getBoundingClientRect();
    const scaleX=area.offsetWidth?areaRect.width/area.offsetWidth:1;
    const scaleY=area.offsetHeight?areaRect.height/area.offsetHeight:1;
    const rect=child.getBoundingClientRect();
    let visualRect=rect;
    const isTextFit=child.dataset.editFit==='text';
    const verticalText=isTextFit&&getComputedStyle(child).writingMode.startsWith('vertical');
    if(isTextFit&&child.textContent.trim()){
      const range=document.createRange();
      range.selectNodeContents(child);
      const textRect=range.getBoundingClientRect();
      if(textRect.width>0&&textRect.height>0)visualRect=textRect;
    }
    const textBuffer=isTextFit?2:0;
    const measuredWidth=verticalText?Math.max(rect.width,visualRect.width):visualRect.width;
    return {
      child,
      left:(visualRect.left-areaRect.left)/scaleX,
      top:(visualRect.top-areaRect.top)/scaleY,
      width:measuredWidth/scaleX+textBuffer,
      height:visualRect.height/scaleY,
    };
  }
  function materializedAreaNeedsRepair(area){
    if(!area||area.dataset.layoutMaterialized!=='true')return false;
    return directLayoutChildren(area).some((child)=>{
      const style=getComputedStyle(child);
      if(style.display==='none'||style.visibility==='hidden')return false;
      // A materialized layout item must keep an explicit position.  If a
      // saved HTML contains position:absolute with auto left/top, the item
      // has lost its visual geometry and the browser falls back to the
      // static position at the parent's origin on reload.
      return style.position!=='absolute'||style.left==='auto'||style.top==='auto'
        ||child.style.getPropertyValue('left')===''||child.style.getPropertyValue('top')==='';
    });
  }
  function resetMaterializedArea(area){
    directLayoutChildren(area).forEach((child)=>{
      if(child.dataset.layoutSourceStyle!==undefined)child.setAttribute('style',child.dataset.layoutSourceStyle);
      else child.removeAttribute('style');
    });
    if(area.dataset.layoutSourceStyle!==undefined)area.setAttribute('style',area.dataset.layoutSourceStyle);
    area.classList.remove('layout-materialized');
    delete area.dataset.layoutMaterialized;
  }
  function materializeArea(area){
    if(!area)return;
    if(area.dataset.layoutMaterialized==='true'){
      if(!materializedAreaNeedsRepair(area))return;
      resetMaterializedArea(area);
    }
    if(area.dataset.layoutSourceStyle===undefined)area.dataset.layoutSourceStyle=area.getAttribute('style')||'';
    const children=directLayoutChildren(area);
    const boxes=children.map((child)=>{
      if(child.dataset.layoutSourceStyle===undefined)child.dataset.layoutSourceStyle=child.getAttribute('style')||'';
      return measuredLayoutBox(area,child);
    });
    area.classList.add('layout-materialized');
    area.dataset.layoutMaterialized='true';
    area.style.display='block';
    boxes.forEach(({child,left,top,width,height})=>{
      child.style.position='absolute';
      child.style.left=(Math.round(left*10)/10)+'px';
      child.style.top=(Math.round(top*10)/10)+'px';
      child.style.width=(Math.round(width*10)/10)+'px';
      child.style.height=(Math.round(height*10)/10)+'px';
      child.style.maxWidth='none';
      child.style.maxHeight='none';
      child.style.margin='0';
      child.style.flex='none';
    });
    // Freeze the first visible-flow measurement with inline importance. The
    // measurement already includes glyph insets and transforms; measuring it
    // again after writing left/top would apply those offsets a second time.
    const freezeMeasuredBox=({child,left,top,width,height})=>{
      child.style.setProperty('position','absolute','important');
      child.style.setProperty('left',(Math.round(left*10)/10)+'px','important');
      child.style.setProperty('top',(Math.round(top*10)/10)+'px','important');
      child.style.setProperty('width',(Math.round(width*10)/10)+'px','important');
      child.style.setProperty('height',(Math.round(height*10)/10)+'px','important');
      child.style.setProperty('max-width','none','important');
      child.style.setProperty('max-height','none','important');
      child.style.setProperty('margin','0','important');
      child.style.setProperty('flex','none','important');
    };
    boxes.forEach(freezeMeasuredBox);
    // Vertical text can reflow along its block axis only after the important
    // width has replaced a theme's max-content rule. Stabilize that final
    // glyph box once more so the editable frame hugs the visible label.
    children
      .filter((child)=>child.dataset.editFit==='text'&&getComputedStyle(child).writingMode.startsWith('vertical'))
      .map((child)=>{
        const measured=measuredLayoutBox(area,child);
        const source=boxes.find((box)=>box.child===child)||measured;
        return {...measured,left:source.left,top:source.top};
      })
      .forEach(freezeMeasuredBox);
  }
  function directFlowRoots(container){
    return Array.from(container?.children||[]).filter((child)=>child.matches?.('.el'));
  }
  function visibleFlowRoots(container){
    return directFlowRoots(container).filter((child)=>{
      const style=getComputedStyle(child);
      const rect=child.getBoundingClientRect();
      // Inactive slides are temporarily laid out with visibility:hidden so
      // every page can resolve geometry without flashing on screen.
      return style.display!=='none'&&rect.width>0.5&&rect.height>0.5;
    });
  }
  function resetLayoutFlowFollower(follower){
    if(!follower)return;
    if(follower.dataset.layoutFollowSourceTop===undefined){
      follower.dataset.layoutFollowSourceTop=follower.style.top||'0px';
    }
    follower.style.top=follower.dataset.layoutFollowSourceTop||'0px';
    delete follower.dataset.layoutFollowResolved;
    delete follower.dataset.layoutFollowShift;
  }
  function resolveLayoutFlowFollower(follower){
    if(!follower)return false;
    const slide=follower.closest('.slide');
    const flowId=follower.dataset.layoutFollow||'';
    if(!slide||!flowId)return false;
    const source=Array.from(slide.querySelectorAll('[data-layout-flow-id]'))
      .find((candidate)=>candidate.dataset.layoutFlowId===flowId);
    if(!source)return false;
    resetLayoutFlowFollower(follower);
    const sourceRoots=visibleFlowRoots(source);
    const followerRoots=visibleFlowRoots(follower);
    if(!sourceRoots.length||!followerRoots.length)return false;
    const frame=follower.closest('.prod-frame,[data-content-area="true"]')||slide;
    const frameRect=frame.getBoundingClientRect();
    const scaleY=Math.max(frame.offsetHeight?frameRect.height/frame.offsetHeight:1,0.0001);
    const sourceBottom=Math.max(...sourceRoots.map((root)=>root.getBoundingClientRect().bottom));
    const followerTop=Math.min(...followerRoots.map((root)=>root.getBoundingClientRect().top));
    const gap=Math.max(0,Number.parseFloat(follower.dataset.layoutFollowGap)||0);
    const shift=Math.max(0,(sourceBottom+gap*scaleY-followerTop)/scaleY);
    const sourceTop=Number.parseFloat(follower.dataset.layoutFollowSourceTop)||0;
    follower.style.top=(Math.round((sourceTop+shift)*10)/10)+'px';
    follower.dataset.layoutFollowResolved='true';
    follower.dataset.layoutFollowShift=(Math.round(shift*10)/10).toString();
    return true;
  }
  function resolveLayoutFlowFollowers(root){
    slidesIn(root).forEach((slide)=>{
      slide.querySelectorAll('[data-layout-follow]').forEach(resolveLayoutFlowFollower);
    });
  }
  function materializeAutoLayouts(root){
    slidesIn(root).forEach((slide)=>{
      const visible=slide.classList.contains('active');
      const previousDisplay=slide.style.display;
      const previousVisibility=slide.style.visibility;
      const previousOpacity=slide.style.opacity;
      const previousPointerEvents=slide.style.pointerEvents;
      if(!visible){slide.style.display='block';slide.style.visibility='hidden'}
      slide.querySelectorAll('[data-auto-layout]').forEach(materializeArea);
      resolveLayoutFlowFollowers(slide);
      if(!visible){slide.style.display=previousDisplay;slide.style.visibility=previousVisibility}
    });
  }
  function textPaintRect(element){
    const range=document.createRange();
    range.selectNodeContents(element);
    const rangeRect=range.getBoundingClientRect();
    if(rangeRect.width>.5&&rangeRect.height>.5)return rangeRect;
    return element.getBoundingClientRect();
  }
  function directStackTextLayers(root){
    return Array.from(root.children).filter((child)=>{
      if(child.dataset.editLayer!=='text'||child.dataset.editPosition==='flow')return false;
      const style=getComputedStyle(child);
      const rect=textPaintRect(child);
      return style.position==='absolute'
        &&style.display!=='none'
        &&style.visibility!=='hidden'
        &&rect.width>.5
        &&rect.height>.5;
    });
  }
  function sharesTextColumn(first,second){
    const overlap=Math.max(0,Math.min(first.right,second.right)-Math.max(first.left,second.left));
    const narrower=Math.max(1,Math.min(first.width,second.width));
    return overlap/narrower>=.56;
  }
  function stackGapFor(root){
    const declared=Number.parseFloat(getComputedStyle(root).getPropertyValue('--semantic-text-stack-gap'));
    return Number.isFinite(declared)&&declared>0?declared:MIN_SEMANTIC_TEXT_STACK_GAP;
  }
  function resetSemanticTextStacks(root){
    const scope=root&&root.querySelectorAll?root:document;
    scope.querySelectorAll('[data-semantic-text-stack-source-top]').forEach((layer)=>{
      const top=layer.dataset.semanticTextStackSourceTop||'';
      const priority=layer.dataset.semanticTextStackSourceTopPriority||'';
      if(top)layer.style.setProperty('top',top,priority);
      else layer.style.removeProperty('top');
      delete layer.dataset.semanticTextStackSourceTop;
      delete layer.dataset.semanticTextStackSourceTopPriority;
      delete layer.dataset.semanticTextStackAdjusted;
    });
    scope.querySelectorAll('[data-semantic-text-stack-overflow]').forEach((module)=>{
      delete module.dataset.semanticTextStackOverflow;
    });
  }
  function resolveSemanticTextStack(module){
    const layers=directStackTextLayers(module)
      .map((layer)=>({layer,rect:textPaintRect(layer)}))
      .sort((a,b)=>a.rect.top-b.rect.top||a.rect.left-b.rect.left);
    if(layers.length<2)return {adjustments:0,overflow:false};
    const moduleRect=module.getBoundingClientRect();
    const scaleY=Math.max(module.offsetHeight?moduleRect.height/module.offsetHeight:1,.0001);
    const minGap=stackGapFor(module);
    let adjustments=0;
    let overflow=false;
    const columns=[];
    layers.forEach((entry)=>{
      const column=columns.find((candidate)=>sharesTextColumn(candidate.last.rect,entry.rect));
      if(column){
        column.items.push(entry);
        column.last=entry;
      }else{
        columns.push({last:entry,items:[entry]});
      }
    });
    columns.forEach((column)=>{
      let previous=column.items[0];
      for(let index=1;index<column.items.length;index+=1){
        const current=column.items[index];
        const previousRect=textPaintRect(previous.layer);
        const currentRect=textPaintRect(current.layer);
        const gap=(currentRect.top-previousRect.bottom)/scaleY;
        if(gap>=minGap){
          previous={layer:current.layer,rect:currentRect};
          continue;
        }
        const shift=minGap-gap;
        const nextBottom=currentRect.bottom+shift*scaleY;
        if(nextBottom>moduleRect.bottom-minGap*scaleY){
          overflow=true;
          previous={layer:current.layer,rect:currentRect};
          continue;
        }
        if(current.layer.dataset.semanticTextStackSourceTop===undefined){
          current.layer.dataset.semanticTextStackSourceTop=current.layer.style.getPropertyValue('top');
          current.layer.dataset.semanticTextStackSourceTopPriority=current.layer.style.getPropertyPriority('top');
        }
        const localTop=(currentRect.top-moduleRect.top)/scaleY+shift;
        current.layer.style.setProperty('top',(Math.round(localTop*10)/10)+'px');
        current.layer.dataset.semanticTextStackAdjusted='true';
        adjustments+=1;
        previous={layer:current.layer,rect:textPaintRect(current.layer)};
      }
    });
    if(overflow)module.dataset.semanticTextStackOverflow='true';
    return {adjustments,overflow};
  }
  function resolveSemanticTextStacks(root){
    const scope=root&&root.querySelectorAll?root:document;
    let adjustments=0;
    let overflows=0;
    scope.querySelectorAll('.el[data-edit-structure="module"],.el[data-edit-composite]').forEach((module)=>{
      const result=resolveSemanticTextStack(module);
      adjustments+=result.adjustments;
      if(result.overflow)overflows+=1;
    });
    document.documentElement.dataset.semanticTextStackAdjustments=String(adjustments);
    document.documentElement.dataset.semanticTextStackOverflows=String(overflows);
    return {adjustments,overflows};
  }
  function freezeTextFitGeometry(root){
    // Theme/Preset type choices are resolved before layout-ready. Freeze the
    // resulting text root box so a later cascade change cannot make max-content
    // silently move centered or right-anchored objects.
    slidesIn(root).forEach((slide)=>{
      const visible=slide.classList.contains('active');
      const previousDisplay=slide.style.display;
      const previousVisibility=slide.style.visibility;
      if(!visible){slide.style.display='block';slide.style.visibility='hidden'}
      slide.querySelectorAll('.el[data-edit-fit="text"]').forEach((element)=>{
        if(element.dataset.layoutSourceStyle===undefined)element.dataset.layoutSourceStyle=element.getAttribute('style')||'';
        const elementRect=element.getBoundingClientRect();
        const slideRect=slide.getBoundingClientRect();
        const scaleX=Math.max(slide.offsetWidth?slideRect.width/slide.offsetWidth:1,0.0001);
        const scaleY=Math.max(slide.offsetHeight?slideRect.height/slide.offsetHeight:1,0.0001);
        const range=document.createRange();
        range.selectNodeContents(element);
        const rangeRect=range.getBoundingClientRect();
        const beforeLines=textLineSummary(element)?.lineTexts.length||0;
        const computed=getComputedStyle(element);
        let width=Math.ceil(Math.max(
          parseFloat(computed.width)||0,
          element.scrollWidth,
          elementRect.width/scaleX,
          rangeRect.width/scaleX,
        ))+2;
        if(width<=0)return;
        element.style.width=width+'px';
        element.style.maxWidth='none';
        element.style.maxHeight='none';
        // max-content may resolve to a fractional width. Freezing offsetWidth
        // floors that value and can push the last glyph onto a new line. Keep
        // widening by a tiny amount until the pre-freeze line count is stable.
        for(let attempt=0;attempt<4&&beforeLines;attempt+=1){
          const afterLines=textLineSummary(element)?.lineTexts.length||0;
          if(afterLines<=beforeLines)break;
          width+=2;
          element.style.width=width+'px';
        }
        const finalRange=document.createRange();
        finalRange.selectNodeContents(element);
        const finalRangeRect=finalRange.getBoundingClientRect();
        const height=Math.ceil(Math.max(
          parseFloat(getComputedStyle(element).height)||0,
          element.scrollHeight,
          finalRangeRect.height/scaleY,
        ))+1;
        if(height<=0)return;
        element.style.height=height+'px';
        element.dataset.layoutMaterialized='true';
      });
      if(!visible){slide.style.display=previousDisplay;slide.style.visibility=previousVisibility}
    });
  }
  function visualChildren(frame){
    const isVisible=(child)=>{
      if(child.matches('.diagram-connectors,[data-visual-balance-ignore]'))return false;
      const style=getComputedStyle(child);
      if(style.display==='none'||Number.parseFloat(style.opacity)<=0.01)return false;
      const rect=child.getBoundingClientRect();
      return rect.width>0.5&&rect.height>0.5;
    };
    const expandLayoutOnly=(child)=>{
      if(!child.matches('[data-edit-layout-only="true"],[data-auto-layout],[data-layout-follow]'))return [child];
      const nested=Array.from(child.children).flatMap(expandLayoutOnly);
      return nested.length?nested:[child];
    };
    return Array.from(frame.children).flatMap(expandLayoutOnly).filter(isVisible);
  }
  function balanceFrameToContentBounds(frame){
    if(!frame||frame.dataset.visualBalanced==='true')return;
    const content=frame.closest('[data-content-area="true"]');
    if(!content)return;
    if(frame.dataset.visualBalanceSourceLeft===undefined)frame.dataset.visualBalanceSourceLeft=frame.style.left||'';
    if(frame.dataset.visualBalanceSourceTop===undefined)frame.dataset.visualBalanceSourceTop=frame.style.top||'';
    const nodes=visualChildren(frame);
    if(!nodes.length)return;
    const contentRect=content.getBoundingClientRect();
    const scaleX=content.offsetWidth?contentRect.width/content.offsetWidth:1;
    const scaleY=content.offsetHeight?contentRect.height/content.offsetHeight:1;
    const rects=nodes.map((node)=>node.getBoundingClientRect());
    const left=Math.min(...rects.map((rect)=>rect.left));
    const top=Math.min(...rects.map((rect)=>rect.top));
    const right=Math.max(...rects.map((rect)=>rect.right));
    const bottom=Math.max(...rects.map((rect)=>rect.bottom));
    const desiredCenterX=(contentRect.left+contentRect.right)/2;
    const desiredCenter=(contentRect.top+contentRect.bottom)/2;
    const visualCenterX=(left+right)/2;
    const visualCenter=(top+bottom)/2;
    const deltaX=(desiredCenterX-visualCenterX)/scaleX;
    const delta=(desiredCenter-visualCenter)/scaleY;
    frame.style.left=(Math.round((frame.offsetLeft+deltaX)*10)/10)+'px';
    frame.style.top=(Math.round((frame.offsetTop+delta)*10)/10)+'px';
    frame.dataset.visualBalanced='true';
    const leftGap=(left-contentRect.left)/scaleX+deltaX;
    const topGap=(top-contentRect.top)/scaleY+delta;
    const rightGap=(contentRect.right-right)/scaleX-deltaX;
    const bottomGap=(contentRect.bottom-bottom)/scaleY-delta;
    frame.dataset.visualLeftGap=(Math.round(leftGap*10)/10).toString();
    frame.dataset.visualTopGap=(Math.round(topGap*10)/10).toString();
    frame.dataset.visualRightGap=(Math.round(rightGap*10)/10).toString();
    frame.dataset.visualBottomGap=(Math.round(bottomGap*10)/10).toString();
  }
  function balanceVisualFrames(root){
    slidesIn(root).forEach((slide)=>{
      const visible=slide.classList.contains('active');
      const previousDisplay=slide.style.display;
      const previousVisibility=slide.style.visibility;
      const previousOpacity=slide.style.opacity;
      const previousPointerEvents=slide.style.pointerEvents;
      if(!visible){slide.style.display='block';slide.style.visibility='hidden'}
      slide.querySelectorAll('[data-visual-balance="content-bounds"]').forEach(balanceFrameToContentBounds);
      if(!visible){slide.style.display=previousDisplay;slide.style.visibility=previousVisibility}
    });
  }
  function reapplyAutoLayout(target){
    const scope=target&&target.querySelectorAll?target:(document.querySelector('.slide.active')||document);
    const apply=()=>{
      scope.querySelectorAll('[data-visual-balance="content-bounds"]').forEach((frame)=>{
        const sourceLeft=frame.dataset.visualBalanceSourceLeft;
        const sourceTop=frame.dataset.visualBalanceSourceTop;
        if(sourceLeft)frame.style.left=sourceLeft;
        else frame.style.removeProperty('left');
        if(sourceTop)frame.style.top=sourceTop;
        else frame.style.removeProperty('top');
        delete frame.dataset.visualBalanced;
        delete frame.dataset.visualLeftGap;
        delete frame.dataset.visualTopGap;
        delete frame.dataset.visualRightGap;
        delete frame.dataset.visualBottomGap;
      });
      scope.querySelectorAll('[data-layout-follow]').forEach(resetLayoutFlowFollower);
      resetSemanticTextStacks(scope);
      scope.querySelectorAll('[data-auto-layout]').forEach((area)=>{
        directLayoutChildren(area).forEach((child)=>child.setAttribute('style',child.dataset.layoutSourceStyle||''));
        area.setAttribute('style',area.dataset.layoutSourceStyle||'');
        area.classList.remove('layout-materialized');
        delete area.dataset.layoutMaterialized;
        materializeArea(area);
      });
      resolveLayoutFlowFollowers(scope);
      resolveSemanticTextStacks(scope);
      balanceVisualFrames(scope);
    };
    const tracked=[];
    scope.querySelectorAll('[data-auto-layout]').forEach((area)=>{
      tracked.push(area,...directLayoutChildren(area));
    });
    scope.querySelectorAll('[data-visual-balance="content-bounds"]').forEach((frame)=>tracked.push(frame));
    scope.querySelectorAll('[data-layout-follow]').forEach((follower)=>tracked.push(follower));
    if(window.EditMode&&typeof window.EditMode.runSnapshotBatch==='function'){
      return window.EditMode.runSnapshotBatch('重新套用 Layout',tracked,apply);
    }
    apply();
    return true;
  }
  function fit(){
    const rootStyle=getComputedStyle(document.documentElement);
    const expandedRailWidth=parseFloat(rootStyle.getPropertyValue('--editor-rail-width'))||232;
    const collapsedRailWidth=parseFloat(rootStyle.getPropertyValue('--editor-rail-collapsed-width'))||44;
    const railWidth=editActive?(railCollapsed?collapsedRailWidth:expandedRailWidth):0;
    const topbarHeight=editActive?(parseFloat(rootStyle.getPropertyValue('--editor-topbar-height'))||58):0;
    const gap=editActive?(parseFloat(rootStyle.getPropertyValue('--editor-workspace-gap'))||16):0;
    const availableWidth=Math.max(1,innerWidth-railWidth-gap*2);
    const availableHeight=Math.max(1,innerHeight-topbarHeight-gap*2);
    const scale=Math.min(availableWidth/CW,availableHeight/CH);
    box.style.width=(CW*scale)+'px';
    box.style.height=(CH*scale)+'px';
    box.style.left=(railWidth+gap+(availableWidth-CW*scale)/2)+'px';
    box.style.top=(topbarHeight+gap+(availableHeight-CH*scale)/2)+'px';
    stage.style.width=CW+'px';
    stage.style.height=CH+'px';
    stage.style.transform='scale('+scale+')';
  }
  function setRailCollapsed(force){
    railCollapsed=force===undefined?!railCollapsed:!!force;
    player.classList.toggle('rail-collapsed',railCollapsed);
    if(slideRailToggle){
      const label=railCollapsed?'展開投影片縮圖':'收合投影片縮圖';
      slideRailToggle.setAttribute('aria-expanded',String(!railCollapsed));
      slideRailToggle.setAttribute('aria-label',label);
      slideRailToggle.title=label;
    }
    if(!railCollapsed&&thumbList){
      const activeThumb=thumbList.querySelector('.slide-thumb.active');
      if(activeThumb)activeThumb.scrollIntoView({block:'nearest'});
    }
    fit();
    requestAnimationFrame(()=>window.dispatchEvent(new CustomEvent('railcollapsechange',{detail:{collapsed:railCollapsed}})));
    return railCollapsed;
  }
  if(slideRailToggle)slideRailToggle.addEventListener('click',(event)=>{
    event.stopPropagation();
    setRailCollapsed();
  });
  function updateCounter(){if(counter)counter.textContent=String(current+1).padStart(2,'0')+' / '+String(slides.length).padStart(2,'0')}
  function ensureSlideIds(){
    slides.forEach((slide,index)=>{
      if(!slide.id)slide.id='slide-'+String(index+1).padStart(2,'0');
      slide.dataset.slideOrder=String(index+1);
    });
  }
  function namespaceThumbnailIds(clone,prefix){
    const idMap=new Map();
    clone.querySelectorAll('[id]').forEach((node)=>{
      const oldId=node.id;
      const nextId=prefix+'-'+oldId;
      idMap.set(oldId,nextId);
      node.id=nextId;
    });
    const refAttrs=['href','xlink:href','clip-path','mask','filter','fill','stroke','aria-labelledby','aria-describedby'];
    clone.querySelectorAll('*').forEach((node)=>{
      refAttrs.forEach((attr)=>{
        const value=node.getAttribute(attr);
        if(!value)return;
        let next=value;
        idMap.forEach((newId,oldId)=>{next=next.replaceAll('#'+oldId,'#'+newId)});
        if(next!==value)node.setAttribute(attr,next);
      });
      const style=node.getAttribute('style');
      if(style){
        let nextStyle=style;
        idMap.forEach((newId,oldId)=>{nextStyle=nextStyle.replaceAll('url(#'+oldId+')','url(#'+newId+')')});
        if(nextStyle!==style)node.setAttribute('style',nextStyle);
      }
    });
  }
  function createThumbnailCanvas(slide,index){
    const host=document.createElement('span');
    host.className='slide-thumb-canvas';
    host.dataset.thumbnailClone='true';
    host.dataset.thumbnailSourceId=slide.id||'';
    host.setAttribute('aria-hidden','true');
    const shadow=host.attachShadow({mode:'open'});
    document.querySelectorAll('style,link[rel="stylesheet"]').forEach((node)=>{
      shadow.appendChild(node.cloneNode(true));
    });
    const isolation=document.createElement('style');
    isolation.textContent=':host{display:block;width:1920px;height:1080px;overflow:hidden;pointer-events:none;user-select:none}#stage{position:relative!important;left:0!important;top:0!important;width:1920px!important;height:1080px!important;transform:none!important;overflow:hidden!important}#stage>.slide{display:block!important;visibility:visible!important;position:absolute!important;left:0!important;top:0!important;width:1920px!important;height:1080px!important;margin:0!important;transform:none!important;box-shadow:none!important}*{pointer-events:none!important}';
    shadow.appendChild(isolation);
    const clone=slide.cloneNode(true);
    clone.classList.remove('active');
    // Keep the original slide id/class inside an isolated shadow tree so every
    // slide-scoped selector, pseudo-element and SVG reference renders exactly
    // like the stage without leaking duplicate ids or `.slide` nodes into the
    // editor's document-level queries.
    const sourceStyle=getComputedStyle(slide);
    ['background','box-shadow','color','font-family','font-size','font-weight','line-height','letter-spacing'].forEach((property)=>{
      const value=sourceStyle.getPropertyValue(property);
      if(value)clone.style.setProperty(property,value,'important');
    });
    Array.from(sourceStyle).filter((property)=>property.startsWith('--')).forEach((property)=>{
      const value=sourceStyle.getPropertyValue(property);
      if(value)clone.style.setProperty(property,value);
    });
clone.querySelectorAll('[contenteditable]').forEach((node)=>node.removeAttribute('contenteditable'));
    [clone,...clone.querySelectorAll('[style]')].forEach((node)=>{
      node.style.removeProperty('outline');
      node.style.removeProperty('outline-offset');
      node.style.removeProperty('cursor');
    });
    clone.querySelectorAll('[data-editor-chrome],.edit-resize-handle,.edit-guide-line,.edit-marquee-box,.edit-selection-member-frame,.edit-hard-break-marker').forEach((node)=>node.remove());
    const mirrorStage=document.createElement('main');
    mirrorStage.id='stage';
    mirrorStage.dataset.thumbnailStage=String(index);
    mirrorStage.appendChild(clone);
    // Mirror the document theme context inside the shadow tree. Authored deck
    // recipes intentionally scope their CSS with selectors such as
    // `html[data-theme-id="..."] .slide[...]`; without a local html/body
    // context those rules cannot cross the shadow boundary and thumbnails fall
    // back to the base layout artwork instead of matching the live slide.
    const contextRoot=document.createElement('html');
    Array.from(document.documentElement.attributes).forEach((attr)=>contextRoot.setAttribute(attr.name,attr.value));
    const contextBody=document.createElement('body');
    Array.from(document.body.attributes).forEach((attr)=>contextBody.setAttribute(attr.name,attr.value));
    contextBody.appendChild(mirrorStage);
    contextRoot.appendChild(contextBody);
    shadow.appendChild(contextRoot);
    return host;
  }
  function fitThumbnailCanvas(preview){
    const canvas=preview&&preview.querySelector('.slide-thumb-canvas');
    if(!canvas)return;
    const width=preview.getBoundingClientRect().width||preview.clientWidth||1;
    canvas.style.setProperty('transform','scale('+(width/CW)+')','important');
  }
  const thumbnailResizeObserver=typeof ResizeObserver==='function'
    ?new ResizeObserver((entries)=>entries.forEach((entry)=>fitThumbnailCanvas(entry.target)))
    :null;
  function updateThumbnailState(){
    if(!thumbList)return;
    Array.from(thumbList.querySelectorAll('.slide-thumb')).forEach((thumb,index)=>{
      thumb.classList.toggle('active',index===current);
      thumb.setAttribute('aria-current',index===current?'page':'false');
      const number=thumb.querySelector('.slide-thumb-number');
      if(number)number.textContent=String(index+1).padStart(2,'0');
    });
    const activeThumb=thumbList.querySelector('.slide-thumb.active');
    if(activeThumb&&editActive)activeThumb.scrollIntoView({block:'nearest'});
  }
  function renderThumbnails(){
    if(!thumbList)return;
    if(thumbnailResizeObserver)thumbnailResizeObserver.disconnect();
    thumbList.innerHTML='';
    ensureSlideIds();
    slides.forEach((slide,index)=>{
      const thumb=document.createElement('button');
      thumb.type='button';
      thumb.className='slide-thumb';
      thumb.dataset.slideId=slide.id;
      thumb.dataset.editorChrome='true';
      thumb.draggable=false;
      thumb.setAttribute('aria-label','前往第 '+(index+1)+' 頁；可拖曳調整順序');
      const number=document.createElement('span');
      number.className='slide-thumb-number';
      const preview=document.createElement('span');
      preview.className='slide-thumb-preview';
      preview.appendChild(createThumbnailCanvas(slide,index+1));
      thumb.append(number,preview);
      thumb.addEventListener('click',(event)=>{
        event.stopPropagation();
        if(suppressThumbClick){suppressThumbClick=false;return}
        setSlide(slides.findIndex((item)=>item.id===slide.id));
      });
      thumb.addEventListener('mousedown',(event)=>{
        if(!editActive||event.button!==0)return;
        event.stopPropagation();
        draggedSlideId=slide.id;
        thumbPointerDrag={id:slide.id,startX:event.clientX,startY:event.clientY,moved:false};
      });
      thumb.addEventListener('dragstart',(event)=>{
        draggedSlideId=slide.id;
        event.dataTransfer.effectAllowed='move';
        event.dataTransfer.setData('text/plain',slide.id);
      });
      thumb.addEventListener('dragover',(event)=>{
        if(!editActive||!draggedSlideId||draggedSlideId===slide.id)return;
        event.preventDefault();
        const rect=thumb.getBoundingClientRect();
        const before=event.clientY<rect.top+rect.height/2;
        thumb.classList.toggle('drag-before',before);
        thumb.classList.toggle('drag-after',!before);
      });
      thumb.addEventListener('dragleave',()=>thumb.classList.remove('drag-before','drag-after'));
      thumb.addEventListener('drop',(event)=>{
        event.preventDefault();
        const sourceId=event.dataTransfer.getData('text/plain')||draggedSlideId;
        const beforeOrder=slides.map((item)=>item.id);
        if(!sourceId||sourceId===slide.id)return;
        const next=beforeOrder.filter((id)=>id!==sourceId);
        let insertAt=next.indexOf(slide.id);
        const rect=thumb.getBoundingClientRect();
        if(event.clientY>=rect.top+rect.height/2)insertAt+=1;
        next.splice(Math.max(0,insertAt),0,sourceId);
        reorderSlides(next,{notify:true});
      });
      thumb.addEventListener('dragend',()=>{
        draggedSlideId=null;
        Array.from(thumbList.querySelectorAll('.slide-thumb')).forEach((item)=>item.classList.remove('drag-before','drag-after'));
      });
      thumbList.appendChild(thumb);
      if(thumbnailResizeObserver)thumbnailResizeObserver.observe(preview);
      fitThumbnailCanvas(preview);
    });
    updateThumbnailState();
    // The vertical scrollbar can appear only after the final thumbnail is
    // appended, narrowing every preview after its first scale calculation.
    // Refit on the settled layout so the complete 16:9 slide stays visible.
    requestAnimationFrame(()=>thumbList.querySelectorAll('.slide-thumb-preview').forEach(fitThumbnailCanvas));
    document.documentElement.dataset.thumbnailSyncReady='true';
  }
  function thumbnailMutationIsVisual(mutation){
    const node=mutation.target&&mutation.target.nodeType===1?mutation.target:mutation.target?.parentElement;
    if(!node)return false;
    if(node.closest?.('[data-editor-chrome="true"],.edit-resize-handle,.edit-guide-line,.edit-marquee-box,.edit-selection-member-frame,.edit-hard-break-marker'))return false;
    if(mutation.type==='attributes'&&mutation.attributeName==='data-slide-order')return false;
    if(mutation.type==='attributes'&&mutation.attributeName==='class'&&node.parentElement===stage){
      const normalize=(value)=>String(value||'').split(/\s+/).filter((token)=>token&&token!=='active').sort().join(' ');
      if(normalize(mutation.oldValue)===normalize(node.className))return false;
    }
    return true;
  }
  function scheduleThumbnailRebuild(){
    if(!editActive)return;
    document.documentElement.dataset.thumbnailSyncReady='false';
    clearTimeout(scheduleThumbnailRebuild.timer);
    scheduleThumbnailRebuild.timer=setTimeout(()=>renderThumbnails(),180);
  }
  const thumbnailStageObserver=new MutationObserver((mutations)=>{
    if(mutations.some(thumbnailMutationIsVisual))scheduleThumbnailRebuild();
  });
  thumbnailStageObserver.observe(stage,{attributes:true,attributeOldValue:true,characterData:true,childList:true,subtree:true});
  function refreshSlides(preferredId){
    slides=Array.from(stage.querySelectorAll(':scope > .slide'));
    ensureSlideIds();
    const preferredIndex=preferredId?slides.findIndex((slide)=>slide.id===preferredId):-1;
    current=preferredIndex>=0?preferredIndex:Math.max(0,Math.min(current,slides.length-1));
    slides.forEach((slide,index)=>slide.classList.toggle('active',index===current));
    updateCounter();
    renderThumbnails();
    return slides.slice();
  }
  function reorderSlides(order,options){
    const before=slides.map((slide)=>slide.id);
    const activeId=slides[current]?slides[current].id:null;
    const byId=new Map(slides.map((slide)=>[slide.id,slide]));
    (order||[]).forEach((id)=>{const slide=byId.get(id);if(slide){stage.appendChild(slide);byId.delete(id)}});
    byId.forEach((slide)=>stage.appendChild(slide));
    refreshSlides(activeId);
    const after=slides.map((slide)=>slide.id);
    if(options?.notify&&before.join('|')!==after.join('|')){
      document.dispatchEvent(new CustomEvent('slidesreordered',{detail:{before,after}}));
    }
    return after;
  }
  function clearThumbDropIndicators(){
    if(!thumbList)return;
    Array.from(thumbList.querySelectorAll('.slide-thumb')).forEach((item)=>item.classList.remove('drag-before','drag-after'));
  }
  function reorderSlideRelative(sourceId,targetId,before){
    const order=slides.map((item)=>item.id);
    if(!sourceId||!targetId||sourceId===targetId)return order;
    const next=order.filter((id)=>id!==sourceId);
    let insertAt=next.indexOf(targetId);
    if(insertAt<0)return order;
    if(!before)insertAt+=1;
    next.splice(insertAt,0,sourceId);
    return reorderSlides(next,{notify:true});
  }
  document.addEventListener('mousemove',(event)=>{
    if(!thumbPointerDrag||!editActive)return;
    const dx=Math.abs(event.clientX-thumbPointerDrag.startX);
    const dy=Math.abs(event.clientY-thumbPointerDrag.startY);
    if(!thumbPointerDrag.moved&&Math.max(dx,dy)<5)return;
    thumbPointerDrag.moved=true;
    clearThumbDropIndicators();
    const target=document.elementFromPoint(event.clientX,event.clientY)?.closest?.('.slide-thumb');
    if(!target||target.dataset.slideId===thumbPointerDrag.id)return;
    const rect=target.getBoundingClientRect();
    const before=event.clientY<rect.top+rect.height/2;
    target.classList.toggle('drag-before',before);
    target.classList.toggle('drag-after',!before);
    event.preventDefault();
  });
  document.addEventListener('mouseup',(event)=>{
    if(!thumbPointerDrag)return;
    const drag=thumbPointerDrag;
    thumbPointerDrag=null;
    const target=document.elementFromPoint(event.clientX,event.clientY)?.closest?.('.slide-thumb');
    if(drag.moved&&target&&target.dataset.slideId!==drag.id){
      const rect=target.getBoundingClientRect();
      reorderSlideRelative(drag.id,target.dataset.slideId,event.clientY<rect.top+rect.height/2);
      suppressThumbClick=true;
      setTimeout(()=>{suppressThumbClick=false},80);
    }
    draggedSlideId=null;
    clearThumbDropIndicators();
  });
  function setSlide(index){
    current=Math.max(0,Math.min(slides.length-1,Number(index)||0));
    slides.forEach((slide,i)=>slide.classList.toggle('active',i===current));
    updateCounter();
    updateThumbnailState();
    document.dispatchEvent(new CustomEvent('slidechange',{detail:{index:current,id:slides[current]?.id||''}}));
    return current;
  }
  function makeButton(label,svg,onClick){
    const button=document.createElement('button');
    button.type='button';button.title=label;button.setAttribute('aria-label',label);button.innerHTML=svg;
    button.addEventListener('click',(event)=>{event.stopPropagation();onClick()});
    return button;
  }
  function divider(){const node=document.createElement('span');node.className='divider';return node}
  function showBar(sticky){
    bar.classList.add('show');
    clearTimeout(hideTimer);
    if(sticky)bar.classList.add('editor-active');
  }
  function hidePresentationBar(immediate){
    if(editActive)return;
    clearTimeout(hideTimer);
    const hide=()=>bar.classList.remove('show');
    if(immediate)hide();
    else hideTimer=setTimeout(hide,PRESENTATION_BAR_LEAVE_DELAY_MS);
  }
  function buildToolbar(){
    barInner.innerHTML='';
    const prev=makeButton('上一頁','<svg viewBox="0 0 24 24"><path d="m15 18-6-6 6-6"/></svg>',()=>setSlide(current-1));
    counter=document.createElement('span');counter.className='counter';
    const next=makeButton('下一頁','<svg viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>',()=>setSlide(current+1));
    const full=makeButton('全螢幕 (F)','<svg viewBox="0 0 24 24"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>',()=>{if(!document.fullscreenElement)player.requestFullscreen?.();else document.exitFullscreen?.()});
    const presentationDivider=divider();
    [prev,counter,next,presentationDivider,full].forEach((node)=>node.classList.add('presentation-only'));
    barInner.append(prev,counter,next,presentationDivider,full);
    updateCounter();
  }
  window.setSlide=setSlide;
  window.SlidePlayer={
    setSlide,
    getSlides:()=>slides.slice(),
    getOrder:()=>slides.map((slide)=>slide.id),
    getCurrentIndex:()=>current,
    refreshSlides,
    reorderSlides:(order,options)=>reorderSlides(order,options||{}),
    setRailCollapsed,
    toggleRail:()=>setRailCollapsed(),
    isRailCollapsed:()=>railCollapsed
  };
  window.getTextLineSummary=textLineSummary;
  window.repairGeneratedTextOrphans=repairGeneratedTextOrphans;
  window.fitGeneratedEditGroups=fitGeneratedEditGroups;
  window.materializeAutoLayouts=materializeAutoLayouts;
  window.resolveSemanticTextStacks=resolveSemanticTextStacks;
  window.resolveLayoutFlowFollowers=resolveLayoutFlowFollowers;
  window.freezeTextFitGeometry=freezeTextFitGeometry;
  window.balanceVisualFrames=balanceVisualFrames;
  window.reapplyAutoLayout=reapplyAutoLayout;
  document.addEventListener('editmodechange',(event)=>{
    editActive=!!event.detail?.editMode;
    player.classList.toggle('editor-shell',editActive);
    player.dataset.uiMode=editActive?'edit':'presentation';
    bar.classList.toggle('editor-active',editActive);
    if(editActive){showBar(true);renderThumbnails()}
    else{
      bar.classList.add('presentation-reset');
      hidePresentationBar(true);
      requestAnimationFrame(()=>requestAnimationFrame(()=>bar.classList.remove('presentation-reset')));
    }
    fit();
  });
  addEventListener('resize',fit);
  addEventListener('resize',()=>thumbList&&thumbList.querySelectorAll('.slide-thumb-preview').forEach(fitThumbnailCanvas));
  addEventListener('mousemove',(event)=>{
    if(editActive)return;
    if(event.clientY>=innerHeight-PRESENTATION_BAR_TRIGGER_PX)showBar(false);
    else hidePresentationBar(false);
  });
  document.addEventListener('mouseleave',()=>hidePresentationBar(true));
  box.addEventListener('click',(event)=>{if(!editActive)setSlide(current+(event.clientX<innerWidth/2?-1:1))});
  addEventListener('keydown',(event)=>{
    const target=event.target;
    if(target&&(target.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)))return;
    if(event.key==='f'||event.key==='F'){event.preventDefault();if(!document.fullscreenElement)player.requestFullscreen?.();else document.exitFullscreen?.();return}
    if(event.key==='Home'){setSlide(0);return}
    if(event.key==='End'){setSlide(slides.length-1);return}
    if(['ArrowRight','ArrowDown',' ','PageDown'].includes(event.key)){event.preventDefault();setSlide(current+1)}
    if(['ArrowLeft','ArrowUp','PageUp'].includes(event.key)){event.preventDefault();setSlide(current-1)}
  });
  const layoutFontsReady=document.fonts&&document.fonts.ready?document.fonts.ready:Promise.resolve();
  layoutFontsReady.then(()=>{
    enforceGeneratedTextMinimum(stage);
    // Wrap quality is decided before geometry is frozen. Running this after
    // materialize would only shrink type inside an already-stranded box.
    relaxGeneratedTextWrapping(stage);
    materializeAutoLayouts();
    // Text repair can change the final visual bounds. Balance only after every
    // geometry-changing typography pass has completed. Generated groups must
    // not be materialized before this point or the later font floor will make
    // their stored bounds stale.
    repairGeneratedTextOrphans(stage);
    resolveSemanticTextStacks(stage);
    document.documentElement.dataset.layoutFontsReady='true';
    freezeTextFitGeometry(stage);
    fitGeneratedEditGroups(stage);
    balanceVisualFrames();
    renderThumbnails();
    document.documentElement.dataset.layoutReady='true';
    window.dispatchEvent(new CustomEvent('slide-layout-ready'));
  });
  buildToolbar();
  refreshSlides();
  setRailCollapsed(false);
  const requested=new URLSearchParams(location.search).get('slide');
  setSlide(requested?Number(requested)-1:0);fit();
  bar.classList.add('editor-active');showBar(true);
  if(hint)setTimeout(()=>hint.classList.add('hide'),4200);
})();
"""


def load_edit_mode_source() -> str:
    if not EDIT_MODE_SOURCE.exists():
        raise FileNotFoundError(f"Missing shared edit-mode asset: {EDIT_MODE_SOURCE}")
    source_text = EDIT_MODE_SOURCE.read_text(encoding="utf-8")
    # Projection mode must never enter or mirror fullscreen on its own.
    # `exitFullscreen` is intentionally allowed for the Escape-to-edit path:
    # the user explicitly requested leaving fullscreen before editor chrome
    # is restored.
    forbidden = [token for token in ("requestFullscreen", "syncProjectionFullscreen") if token in source_text]
    if forbidden:
        raise ValueError(f"Edit/presentation mode must not enter or mirror fullscreen: {forbidden}")
    return source_text


def load_pptx_browser_runtime() -> str:
    """Load the self-contained browser PPTX runtime for every formal HTML deck."""

    sources = (PPTXGEN_SOURCE, PPTX_BROWSER_EXPORT_SOURCE)
    missing = [str(path) for path in sources if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing embedded PPTX browser runtime assets: {missing}")
    runtime = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    if "PptxGenJS" not in runtime or "PptxBrowserExport" not in runtime:
        raise ValueError("PPTX browser runtime is missing PptxGenJS or PptxBrowserExport")
    return runtime + "\n" + PPTX_BROWSER_RUNTIME_BRIDGE.strip() + "\n"


def pptx_browser_runtime_sha256() -> str:
    return hashlib.sha256(load_pptx_browser_runtime().encode("utf-8")).hexdigest()

def editable_player_markup(slides_html: str, canvas_width: int, canvas_height: int) -> str:
    runtime = PLAYER_RUNTIME.replace("__CW__", str(canvas_width)).replace("__CH__", str(canvas_height))
    pptx_runtime = load_pptx_browser_runtime().replace("</script", "<\\/script")
    edit_mode_source = load_edit_mode_source().replace("</script", "<\\/script")
    return f'''<div id="player" class="editor-shell" data-ui-mode="edit"><aside id="slideRail" data-editor-chrome="true" aria-label="投影片縮圖"><div id="slideRailHeader"><strong>投影片</strong><span>拖曳縮圖<br>調整頁序</span><button id="slideRailToggle" type="button" aria-expanded="true" aria-label="收合投影片縮圖" title="收合投影片縮圖"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg></button></div><div id="slideThumbList"></div></aside><div id="canvasBox"><main id="stage">{slides_html}</main></div>
<div id="bar" class="show editor-active"><div id="barInner"></div></div>
<div id="hint" aria-hidden="true"></div></div>
<script>{runtime}</script><script data-pptx-browser-runtime-embedded="true">{pptx_runtime}</script><script data-edit-mode-embedded="true">{edit_mode_source}</script>'''


def ensure_edit_mode_asset(output_dir: Path) -> Path:
    source_text = load_edit_mode_source()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "edit-mode.js"
    if destination.resolve() != EDIT_MODE_SOURCE.resolve():
        # A Theme Lab build renders many decks into the same directory.  Avoid
        # reopening the identical OneDrive destination for every deck; Windows
        # can transiently reject that redundant overwrite while sync is active.
        if destination.exists():
            try:
                if destination.read_text(encoding="utf-8") == source_text:
                    return destination
            except OSError:
                pass
        shutil.copyfile(EDIT_MODE_SOURCE, destination)
    return destination



class EditLayerPositionValidator(HTMLParser):
    """Validate the positioning and vertical-alignment half of the edit contract."""

    EDGE_ANCHORS = {"bottom"}

    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        layer_kind = values.get("data-edit-layer")
        if not layer_kind:
            return
        position = values.get("data-edit-position")
        class_name = values.get("class", "")
        label = f"<{tag} class={class_name!r} data-edit-layer={layer_kind!r}>"
        if position not in {"absolute", "flow"}:
            self.errors.append(f"{label} requires data-edit-position=absolute or flow")
        if layer_kind in {"background", "visual"} and position != "absolute":
            self.errors.append(f"{label} must use data-edit-position=absolute")
        if layer_kind != "text" and position == "flow":
            self.errors.append(f"{label} cannot participate in semantic text flow")
        if layer_kind in {"text", "metric"} and values.get("data-edit-vertical-align") not in {"start", "center", "end"}:
            self.errors.append(f"{label} requires data-edit-vertical-align=start, center, or end")
        anchor = values.get("data-edit-anchor")
        if anchor is not None:
            if layer_kind != "visual" or anchor not in self.EDGE_ANCHORS:
                self.errors.append(
                    f"{label} data-edit-anchor must be one of {sorted(self.EDGE_ANCHORS)!r} on a visual layer"
                )


class EditModuleStructureValidator(HTMLParser):
    """Validate the flat initial object tree and semantic module ownership."""

    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []
        self.stack: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if self.stack and self.stack[-1]["is_module"] and not self.stack[-1]["has_child"]:
            self.stack[-1]["has_child"] = True
            if values.get("data-edit-layer") != "background":
                self.errors.append(
                    f'{self.stack[-1]["label"]} must begin with a data-edit-layer="background" child'
                )
            if values.get("data-edit-position") != "absolute":
                self.errors.append(
                    f'{self.stack[-1]["label"]} background child must use data-edit-position="absolute"'
                )
        structure = values.get("data-edit-structure")
        is_module = structure == "module"
        is_group = structure == "group"
        class_tokens = set((values.get("class") or "").split())
        label = f'<{tag} class={values.get("class", "")!r}>'
        if (
            any(entry["is_module"] for entry in self.stack)
            and values.get("data-edit-layer")
            and "el" in class_tokens
        ):
            self.errors.append(
                f"{label} semantic-module layers belong to the module root and cannot also be .el roots"
            )
        retired_repeat_attrs = sorted(name for name in values if name.startswith("data-edit-repeat-"))
        if retired_repeat_attrs:
            self.errors.append(
                f"{label} uses retired Repeat Group attributes: {retired_repeat_attrs!r}"
            )
        if values.get("data-edit-role") in {"title-group", "content-group", "extra-group"} or is_group:
            self.errors.append(
                f"{label} generated aggregate groups are retired; keep loose objects flat and use semantic modules only"
            )
        if values.get("data-edit-layout-only") == "true":
            if "el" in class_tokens:
                self.errors.append(f"{label} layout-only container cannot be an .el")
            if values.get("data-edit-layer") or values.get("data-edit-composite"):
                self.errors.append(f"{label} layout-only container cannot be an edit layer or composite")
        if values.get("data-visual-balance") == "content-bounds" and values.get("data-edit-layout-only") != "true":
            self.errors.append(
                f'{label} content-bounds centering must live on data-edit-layout-only="true"'
            )
        if is_module:
            if "el" not in class_tokens:
                self.errors.append(f"{label} semantic module must be an .el")
            if not values.get("data-edit-composite"):
                self.errors.append(f"{label} semantic module requires data-edit-composite")
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}:
            self.stack.append({"tag": tag, "is_module": is_module, "has_child": False, "label": label})

    def handle_endtag(self, tag: str) -> None:
        while self.stack:
            entry = self.stack.pop()
            if entry["is_module"] and not entry["has_child"]:
                self.errors.append(f'{entry["label"]} semantic module requires editable children')
            if entry["tag"] == tag:
                break

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def validate_edit_layer_positions(markup: str) -> None:
    parser = EditLayerPositionValidator()
    parser.feed(markup)
    parser.close()
    if parser.errors:
        raise ValueError("Invalid edit-layer positioning contract:\n- " + "\n- ".join(parser.errors))


def validate_edit_module_structures(markup: str) -> None:
    parser = EditModuleStructureValidator()
    parser.feed(markup)
    parser.close()
    if parser.errors:
        raise ValueError("Invalid editable module structure:\n- " + "\n- ".join(parser.errors))


def validate_semantic_editable_html(document: str) -> None:
    validate_editable_html(document)
    validate_edit_layer_positions(document)
    validate_edit_module_structures(document)

def validate_editable_html(document: str) -> None:
    required = ['id="canvasBox"', 'id="slideRail"', 'id="slideThumbList"', 'id="barInner"', 'id="hint"', 'data-pptx-browser-runtime-embedded="true"', 'data-edit-mode-embedded="true"']
    missing = [fragment for fragment in required if fragment not in document]
    if missing:
        raise ValueError(f"Generated HTML is missing edit framework hooks: {missing}")
