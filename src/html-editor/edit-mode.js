(function () {

  const stage = document.getElementById('stage');

  const barInner = document.getElementById('barInner');

  const canvasBox = document.getElementById('canvasBox');

  const player = document.getElementById('player');

  const hint = document.getElementById('hint');

  if (!stage || !barInner) return;

  if (hint) {

    hint.textContent = '';

    hint.style.display = 'none';

    hint.setAttribute('aria-hidden', 'true');

  }



  const M = {

    edit: '\u7de8\u8f2f',

    export: '\u532f\u51fa',

    exportAs: '\u53e6\u5b58\u65b0\u6a94',

    save: '\u5b58\u6a94',

    saveStart: '\u958b\u59cb\u5b58\u6a94',

    saveProgress: '\u5132\u5b58\u9032\u5ea6',

    saveDirectTo: '\u76f4\u63a5\u5b58\u56de\uff1a',

    saveVerified: '\u5df2\u9a57\u8b49\u53ef\u5feb\u901f\u5b58\u6a94',

    saveBindingMissing: '\u5c1a\u672a\u7d81\u5b9a HTML \u6a94\u6848',

    saveBindingUnavailable: '\u539f\u672c\u7684\u5b58\u6a94\u7d81\u5b9a\u5df2\u5931\u6548\uff0c\u8acb\u91cd\u65b0\u958b\u59cb\u5b58\u6a94',

    previewReadOnly: '\u9810\u89bd\u6a21\u5f0f\u4e0d\u6703\u4fee\u6539\u6a94\u6848',

    undo: '\u5fa9\u539f',

    redo: '\u91cd\u505a',

    editMode: '\u7de8\u8f2f\u6a21\u5f0f',

    present: '\u6295\u5f71',

    presentMode: '\u6295\u5f71\u6a21\u5f0f',

    undoLabel: '\u5fa9\u539f',

    redoLabel: '\u91cd\u505a',

    exportHtml: '\u53e6\u5b58\u65b0\u6a94 HTML',

    exportPptx: '\u532f\u51fa PPTX',

    exportPptxFull: '\u532f\u51fa\u53ef\u7de8\u8f2f PowerPoint',

    pptxExporting: '\u6b63\u5728\u5efa\u7acb\u53ef\u7de8\u8f2f PPTX\u2026',

    pptxExportDone: '\u5df2\u532f\u51fa\u53ef\u7de8\u8f2f PPTX',

    pptxExportFailed: 'PPTX \u532f\u51fa\u5931\u6557\uff1a',

    pptxRuntimeMissing: 'PPTX \u532f\u51fa\u5143\u4ef6\u672a\u5d4c\u5165\u6b64 HTML\uff0c\u8acb\u91cd\u65b0\u540c\u6b65\u6b63\u5f0f\u7de8\u8f2f\u5668',

    undoDone: '\u5df2\u5fa9\u539f\uff1a{label}',

    redoDone: '\u5df2\u91cd\u505a\uff1a{label}',

    noUndo: '\u6c92\u6709\u53ef\u5fa9\u539f\u7684\u64cd\u4f5c',

    noRedo: '\u6c92\u6709\u53ef\u91cd\u505a\u7684\u64cd\u4f5c',

    moveChange: '\u62d6\u66f3',

    resizeChange: '\u7e2e\u653e',

    textChange: '\u6587\u5b57',

    styleChange: '\u6a23\u5f0f',

    batchChange: '\u6279\u6b21',

    fontSizeLabel: '\u5b57\u7d1a',

    fontFamilyLabel: '\u5b57\u9ad4',

    fontFamilyMixed: '\u591a\u7a2e\u5b57\u9ad4',

    fontFamilyChange: '\u66f4\u63db\u5b57\u9ad4',

    fontDecrease: '\u5b57\u7d1a -1px',

    fontIncrease: '\u5b57\u7d1a +1px',

    fontPeerApply: '\u5957\u7528\u5230\u540c\u985e\u5143\u7d20',

    fontPeerApplied: '\u5df2\u5957\u7528\u5230 {count} \u500b\u540c\u985e\u5143\u7d20',

    fontPeerMismatch: '\u6b64\u5143\u7d20 {current}px\uff0c\u5176\u4ed6 {count} \u500b\u540c\u985e\u5143\u7d20\u662f {sizes}',

    textEditing: '\u6587\u5b57\u7de8\u8f2f\u4e2d\uff5c\u76f4\u63a5\u8f38\u5165\u5167\u5bb9\uff0cEsc \u7d50\u675f',

    enterEdit: '\u5df2\u9032\u5165\u7de8\u8f2f\u6a21\u5f0f\uff5c\u5148\u9ede\u9078\u53d6\uff0c\u518d\u9ede\u4e00\u6b21\u5167\u5bb9\u6539\u5b57',

    enableFirst: '\u8acb\u5148\u6309\u300c{action}\u300d',

    enableEditFirst: '\u8acb\u5148\u6309\u300c\u7de8\u8f2f\u300d\u518d\u4f7f\u7528\u300c{action}\u300d',

    needServer: '\u76ee\u524d\u662f file:// \u958b\u555f\uff0c\u300c{action}\u300d\u8acb\u6539\u7528 http://127.0.0.1:7392',

    exportDone: '\u5df2\u53e6\u5b58 HTML \u4e26\u5efa\u7acb\u5feb\u901f\u5b58\u6a94\u9023\u7dda',

    exportFailed: '\u532f\u51fa\u5931\u6557\uff0c\u8acb\u518d\u8a66\u4e00\u6b21',

    savedAt: '\u5df2\u8986\u5beb\u76ee\u524d HTML\uff1a',

    savedViaPicker: '\u5df2\u5132\u5b58 HTML \u6a94\u6848 ',

    saveBindAndSave: '\u7d81\u5b9a\u4e26\u5b58\u6a94',

    savedViaHandle: '\u5df2\u5132\u5b58\u4e26\u76f4\u63a5\u5beb\u56de HTML\uff1a',

    saveAsOpened: '\u5df2\u4e0b\u8f09\u53e6\u5b58\u526f\u672c\uff0c\u672a\u5efa\u7acb\u5feb\u901f\u5b58\u6a94\u9023\u7dda',

    saveCanceled: '\u5df2\u53d6\u6d88\u5b58\u6a94',

    saveUnavailable: '\u6b64\u700f\u89bd\u5668\u7121\u6cd5\u958b\u555f\u300c\u53e6\u5b58\u65b0\u6a94\u300d\uff0c\u8acb\u4f7f\u7528 Chrome\u3001Edge \u6216\u53ef\u5beb\u5165 localhost\u3002',

    saveFailed: '\u5b58\u6a94\u5931\u6557\uff0c\u672a\u8986\u5beb\u76ee\u524d HTML\uff1a',

    autoSaveEnabled: '\u5df2\u958b\u555f\u81ea\u52d5\u5b58\u6a94',

    autoSaveDraftOnly: '\u5df2\u81ea\u52d5\u4fdd\u7559\u8349\u7a3f\uff0c\u8981\u5beb\u56de HTML \u8acb\u4f7f\u7528\u672c\u6a5f server',

    autoSaving: '\u6b63\u5728\u81ea\u52d5\u5b58\u6a94\u2026',

    autoSaved: '\u5df2\u81ea\u52d5\u5b58\u6a94\uff1a',

    autoSaveFailed: '\u81ea\u52d5\u5b58\u6a94\u5931\u6557\uff0c\u8349\u7a3f\u4ecd\u5df2\u4fdd\u7559\uff1a',

    autoSaveQueued: '\u5df2\u8a18\u9304\u65b0\u8b8a\u66f4\uff0c\u7b49\u5f85\u4e0b\u4e00\u6b21\u81ea\u52d5\u5b58\u6a94',

    draftFound: '\u5075\u6e2c\u5230\u4e0a\u6b21\u672a\u5b58\u6a94\u7684\u7de8\u8f2f\uff1a',

    restore: '\u9084\u539f',

    discard: '\u4e1f\u68c4',

    draftRestoreChange: '\u6062\u5fa9\u8349\u7a3f',

    readOnlyElement: '\u9019\u500b\u5143\u7d20\u76ee\u524d\u53ea\u80fd\u79fb\u52d5\u6216\u7e2e\u653e',

    saveShortcut: '\u5132\u5b58',

    saveFallback: '\u700f\u89bd\u5668\u7121\u6cd5\u958b\u555f\u5b58\u6a94\u8996\u7a97\uff0c\u5df2\u6539\u70ba\u4e0b\u8f09 HTML',

    savedViaLocalServer: '\u5df2\u900f\u904e\u672c\u6a5f server \u5132\u5b58 ',

    multiSelected: '\u5df2\u9078 {count} \u500b\u5143\u7d20',

    grouped: '\u5df2\u5efa\u7acb\u7fa4\u7d44',

    groupChange: '\u7fa4\u7d44',

    groupHint: '\u5df2\u9078\u53d6\u6574\u7d44\uff5c\u6309\u4f4f Ctrl\uff0fCmd \u53ef\u76f4\u63a5\u9078\u53d6\u7fa4\u7d44\u5167\u7269\u4ef6\u6216\u7de8\u8f2f\u6587\u5b57',

    groupAction: '\u7fa4\u7d44',

    contextGroupAction: '\u7d44\u6210\u7fa4\u7d44',

    groupSelected: '\u5df2\u9078\u53d6\u7fa4\u7d44 \u00b7 {count} \u500b\u7269\u4ef6',

    editGroupMember: '\u7de8\u8f2f\u7fa4\u7d44\u5167\u7269\u4ef6',

    editGroupMemberHelp: '\u9032\u5165\u7fa4\u7d44\u5167\u7de8\u8f2f\uff0c\u63a5\u8457\u9ede\u9078\u8981\u4fee\u6539\u7684\u6587\u5b57\u6216\u5716\u5f62',

    groupMemberPickHint: '\u5df2\u9032\u5165\u7fa4\u7d44\u5167\u7de8\u8f2f\uff5c\u8acb\u9ede\u9078\u8981\u4fee\u6539\u7684\u6587\u5b57\u6216\u5716\u5f62',

    selectWholeGroup: '\u8fd4\u56de\u6574\u7d44\u9078\u53d6',

    selectWholeGroupHelp: '\u96e2\u958b\u7fa4\u7d44\u5167\u7de8\u8f2f\uff0c\u91cd\u65b0\u9078\u53d6\u6574\u500b\u7fa4\u7d44',

    ungrouped: '\u5df2\u53d6\u6d88\u6700\u5916\u5c64\u7fa4\u7d44',

    ungroupChange: '\u53d6\u6d88\u7fa4\u7d44',

    objectActions: '\u7269\u4ef6\u64cd\u4f5c',

    insert: '\u65b0\u589e\u7269\u4ef6',

    insertHelp: '\u65b0\u589e\u6587\u5b57\u65b9\u584a\u6216\u5716\u6848',

    insertPanelTitle: '\u65b0\u589e\u7269\u4ef6',

    insertPanelHelp: '\u6587\u5b57\u65b9\u584a\u8207\u5716\u5f62\u8acb\u62d6\u66f3\u6c7a\u5b9a\u5927\u5c0f',

    insertDragHint: '\u8acb\u5728\u756b\u5e03\u4e0a\u62d6\u66f3\u51fa\u5927\u5c0f\uff0c\u653e\u958b\u5f8c\u5efa\u7acb',

    insertTextBox: '\u6587\u5b57\u65b9\u584a',

    insertRect: '\u77e9\u5f62',

    insertRoundRect: '\u5713\u89d2\u77e9\u5f62',

    insertEllipse: '\u6a62\u5713',

    insertImage: '\u5716\u7247',

    insertImageUpload: '\u4e0a\u50b3\u5716\u7247',

    insertImageHelp: '\u9078\u53d6\u5716\u7247\u5f8c\u76f4\u63a5\u653e\u5165\u672c\u9801',

    insertedTextBox: '\u5df2\u65b0\u589e\u6587\u5b57\u65b9\u584a',

    insertedShape: '\u5df2\u65b0\u589e\u5716\u6848',

    insertedImage: '\u5df2\u65b0\u589e\u5716\u7247',

    imageFileTypes: '\u652f\u63f4 PNG\u3001JPEG\u3001WebP\u3001GIF',

    imageReadFailed: '\u5716\u7247\u8b80\u53d6\u5931\u6557\uff0c\u8acb\u91cd\u65b0\u9078\u64c7',

    needGroup: '\u8acb\u5148\u9078\u53d6\u4e00\u500b\u7fa4\u7d44',

    bold: '\u7c97\u9ad4',

    italic: '\u659c\u9ad4',

    underline: '\u5e95\u7dda',

    alignLeft: '\u9760\u5de6',

    alignCenter: '\u7f6e\u4e2d',

    alignRight: '\u9760\u53f3',

    verticalTop: '\u6587\u5b57\u9760\u4e0a',

    verticalCenter: '\u6587\u5b57\u5782\u76f4\u7f6e\u4e2d',

    verticalBottom: '\u6587\u5b57\u9760\u4e0b',

    duplicate: '\u8907\u88fd',

    bringFront: '\u79fb\u5230\u6700\u4e0a\u5c64',

    sendBack: '\u79fb\u5230\u6700\u4e0b\u5c64',

    delete: '\u522a\u9664',

    deleteHelp: '\u522a\u9664\u9078\u53d6\u7269\u4ef6',

    moveMode: '\u5df2\u9078\u53d6\u5143\u7d20',

    selectedText: '\u5df2\u9078\u53d6\u6587\u5b57',

    selectedVisual: '\u5df2\u9078\u53d6\u5716\u5f62',

    selectedBackground: '\u5df2\u9078\u53d6\u80cc\u666f',

    generatedGroupRegrouped: '\u5df2\u91cd\u65b0\u7fa4\u7d44 AI \u751f\u6210\u7269\u4ef6',

    textMode: '\u6587\u5b57\u7de8\u8f2f\u4e2d',

    resizeMode: '\u8abf\u6574\u5927\u5c0f',

    moveHint: '\u62d6\u66f3\u53ef\u79fb\u52d5\uff0c\u62d6\u7bc0\u9ede\u53ef\u7e2e\u653e\uff0c\u518d\u9ede\u4e00\u6b21\u6587\u5b57\u5167\u5bb9\u53ef\u6539\u5b57',

    textHint: '\u76f4\u63a5\u8f38\u5165\u5167\u5bb9\uff0cEsc \u7d50\u675f\u7de8\u8f2f',

    resizeHint: '\u62d6\u66f3\u5916\u5708\u7bc0\u9ede\u53ef\u8abf\u6574\u5927\u5c0f\uff0c\u6309\u4f4f Ctrl \u4ee5\u4e2d\u5fc3\u7e2e\u653e',

    modePanelTitle: '\u7de8\u8f2f\u72c0\u614b',

    modePanelHelp: '\u81ea\u52d5\u5224\u5b9a',

    switchMove: '\u9032\u5165\u5143\u7d20\u9078\u53d6',

    switchText: '\u9032\u5165\u6587\u5b57\u7de8\u8f2f',

    switchResize: '\u9032\u5165\u5927\u5c0f\u8abf\u6574',

    textModeReadonly: '\u9019\u500b\u5143\u7d20\u4e0d\u662f\u6587\u5b57\uff0c\u8acb\u6539\u7528\u79fb\u52d5\u6216\u7e2e\u653e',

    resizeSelectFirst: '\u5148\u9078\u53d6\u5143\u7d20\uff0c\u518d\u62d6\u66f3\u63a7\u5236\u9ede',

    idleMode: '\u672a\u9078\u53d6\u5143\u7d20',

    idleHint: '\u6b64\u6642\u53ef\u7528\u5de6\u53f3\u9375\u63db\u9801\uff0c\u8981\u7de8\u8f2f\u76f4\u63a5\u9ede\u64ca\u5143\u7d20\u5373\u53ef',

    idleBadgeHint: '\u5de6\u53f3\u9375\u53ef\u76f4\u63a5\u63db\u9801',

    exitTool: '\u96e2\u958b\u7576\u524d\u7de8\u8f2f\u6a21\u5f0f',

    paste: '\u8cbc\u4e0a',

    copiedEls: '\u5df2\u8907\u88fd {count} \u500b\u5143\u7d20\uff0c\u53ef\u7528 Ctrl+V \u8cbc\u4e0a',

    pastedEls: '\u5df2\u8cbc\u4e0a {count} \u500b\u5143\u7d20',

    alignElsLeft: '\u9760\u5de6\u5c0d\u9f4a',

    alignElsCenterX: '\u6c34\u5e73\u7f6e\u4e2d',

    alignElsRight: '\u9760\u53f3\u5c0d\u9f4a',

    alignElsTop: '\u9760\u4e0a\u5c0d\u9f4a',

    alignElsMiddle: '\u5782\u76f4\u7f6e\u4e2d',

    alignElsBottom: '\u9760\u4e0b\u5c0d\u9f4a',

    alignSlideLeft: '\u9760\u6295\u5f71\u7247\u5de6\u7de3',

    alignSlideCenterX: '\u5c0d\u9f4a\u6295\u5f71\u7247\u6c34\u5e73\u4e2d\u5fc3',

    alignSlideRight: '\u9760\u6295\u5f71\u7247\u53f3\u7de3',

    alignSlideTop: '\u9760\u6295\u5f71\u7247\u4e0a\u7de3',

    alignSlideMiddle: '\u5c0d\u9f4a\u6295\u5f71\u7247\u5782\u76f4\u4e2d\u5fc3',

    alignSlideBottom: '\u9760\u6295\u5f71\u7247\u4e0b\u7de3',

    distributeH: '\u6c34\u5e73\u7b49\u8ddd',

    distributeV: '\u5782\u76f4\u7b49\u8ddd',

    needMultiSelect: '\u8acb\u5148\u6309\u4f4f Shift \u6216\u6846\u9078\u591a\u500b\u5143\u7d20',

    needDistribute: '\u7b49\u8ddd\u5206\u4f48\u9700\u9078\u53d6\u81f3\u5c11 3 \u500b\u5143\u7d20',

    lineHeightLabel: '\u884c\u9ad8',

    letterSpacingLabel: '\u5b57\u8ddd',

    frameWidthLabel: '\u6846\u5bec',

    frameWidthChange: '\u8abf\u6574\u6587\u5b57\u6846\u5bec\u5ea6',

    customColor: '\u81ea\u8a02\u984f\u8272',

    textColor: '\u6587\u5b57\u984f\u8272',

    textBoxBackground: '\u7269\u4ef6\u80cc\u666f',

    textBoxBackgroundChange: '\u66f4\u63db\u7269\u4ef6\u80cc\u666f',

    clearTextBoxBackground: '\u6e05\u9664\u7269\u4ef6\u80cc\u666f',

    presentationStyle: '\u6295\u5f71\u7247\u8a2d\u5b9a',

    defaultFont: '\u9810\u8a2d\u5b57\u9ad4',

    defaultFontChange: '\u66f4\u63db\u9810\u8a2d\u5b57\u9ad4',

    slideBackground: '\u672c\u9801\u80cc\u666f',

    slideBackgroundChange: '\u66f4\u63db\u6295\u5f71\u7247\u80cc\u666f',

    slideMask: '\u9801\u9762\u906e\u7f69',

    slideMaskColor: '\u906e\u7f69\u984f\u8272',

    slideMaskOpacity: '\u906e\u7f69\u900f\u660e\u5ea6',

    slideMaskReset: '\u6e05\u9664\u9801\u9762\u906e\u7f69',

    slideMaskChange: '\u8abf\u6574\u9801\u9762\u906e\u7f69',

    slideMaskHelp: '\u53ea\u4f5c\u7528\u65bc\u80cc\u666f\u5c64\uff0c\u4e0d\u6539\u8b8a\u6587\u5b57\u8207\u5716\u5f62',

    resetPreset: '\u91cd\u8a2d\u70ba Preset',

    slideOrderChange: '\u8abf\u6574\u6295\u5f71\u7247\u9806\u5e8f',

  };



  const originalHintText = hint ? hint.textContent : '';

  const HANDLE_SIZE = 10;

  const HANDLE_POSITIONS = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];

  const HANDLE_CURSORS = {

    nw: 'nwse-resize',

    n: 'ns-resize',

    ne: 'nesw-resize',

    e: 'ew-resize',

    se: 'nwse-resize',

    s: 'ns-resize',

    sw: 'nesw-resize',

    w: 'ew-resize'

  };

  const DRAG_THRESHOLD = 4;

  const TEXT_HIT_SLOP_PX = 2;

  const MIN_SIZE = 20;

  const INSERT_IMAGE_HEIGHT = 260;

  const INSERT_IMAGE_MAX_WIDTH = 720;

  const AUTO_RESIZE_MIN_FONT_RATIO = 0.62;

  const UNDO_LIMIT = 100;

  const DRAFT_SCHEMA_VERSION = 3;

  const AUTO_SAVE_DELAY_MS = 1500;

  const OPERATION_LOG_LIMIT = 100;

  const GUIDE_THRESHOLD = 6;



  let editMode = true;

  let currentTool = null;

  let pendingInsertKind = null;

  let insertDrawState = null;

  let insertImageFileInput = null;

  let selectedEl = null;

  let selectedEls = [];

  let textEditingEl = null;

  let dragEl = null;

  let dragCandidateEl = null;

  let dragStartX = 0;

  let dragStartY = 0;

  let dragCandidateStartX = 0;

  let dragCandidateStartY = 0;

  let dragGrabOffsetX = 0;

  let dragGrabOffsetY = 0;

  let dragScale = 1;

  let elStartLeft = 0;

  let elStartTop = 0;

  let resizeEl = null;

  let resizeHandle = null;

  let resizeScale = 1;

  let resizeStartX = 0;

  let resizeStartY = 0;

  let resizeStartLeft = 0;

  let resizeStartTop = 0;

  let resizeStartW = 0;

  let resizeStartH = 0;

  let resizeStartFontSize = 0;

  let resizeTypographyStart = [];

  let dragStartState = null;

  let dragGroupStartStates = null;

  let resizeStartState = null;

  let resizeGroupStartStates = null;

  let resizeVisualStart = null;

  let resizeAdaptiveStart = null;

  let resizeMode = 'none';

  let resizeFrameWidthOnly = false;

  let resizeFrameHeightOnly = false;

  let textEditStartHtml = null;

  let textEditStartState = null;

  let textEditInputAnchor = null;

  let pendingFontCommand = null;

  let pendingFontBatchCommand = null;

  let pendingSlideMaskCommand = null;

  let draftTimer = null;

  let autoSaveTimer = null;

  let activeSavePromise = null;

  let autoSaveQueued = false;

  let autoSaveState = 'idle';

  let autoSaveLastSavedAt = null;

  let autoSaveLastError = '';

  let documentChangeVersion = 0;

  let operationLog = null;

  let readoutTimer = null;

  let previousUserSelect = '';

  let pointerDownSelectedEl = null;

  let pointerDownWasSelected = false;

  let pointerInteractionMoved = false;

  let pendingTextEditEl = null;

  let groupEditScopes = [];

  let pendingNudgeCommand = null;

  let nudgeTimer = null;

  let clipboardData = null;

  let marqueeCandidate = false;

  let marqueeActive = false;

  let marqueeStartX = 0;

  let marqueeStartY = 0;

  let marqueeBox = null;

  let insertDrawBox = null;

  let lastPaletteSignature = null;

  let groupSequence = 0;

  let selectedGroupId = null;

  let selectedGroupDepth = -1;

  let selectionRefreshRaf = 0;

  let selectionResizeObserver = null;

  let slideOrderDirty = false;

  let thumbnailRefreshTimer = null;



  const originalPositions = new WeakMap();

  const originalSizes = new WeakMap();

  const originalTexts = new WeakMap();

  const originalStyles = new WeakMap();

  // Typography recovery is scoped to the axis being edited. For example, a
  // vertical shrink that starts after a horizontal squeeze must recover only
  // to the squeezed typography, not to the deck's untouched source size.
  const adaptiveAxisTypographyBaselines = new WeakMap();

  const changedElements = new Set();

  const textDirty = new WeakSet();

  const undoStack = [];

  const redoStack = [];

  const handles = {};

  const labeledToolbarBtns = [];



  let editBtn = null;

  let editModeLabel = null;

  let exportBtn = null;

  let exportPptxBtn = null;

  let saveGroup = null;

  let saveMenuToggle = null;

  let saveMenu = null;

  let undoBtn = null;

  let redoBtn = null;

  let saveBtn = null;

  let insertBtn = null;

  let imageUploadBtn = null;

  let insertPanel = null;

  let modePanel = null;

  let modeButtons = {};

  let modeStatusLabel = null;

  let modeStatusHint = null;

  let selectionBadge = null;

  let selectionFrame = null;

  let selectionMemberFrames = [];

  let hardBreakMarkers = [];

  let fontControlRow = null;

  let fontFamilySelect = null;

  let fontSizeInput = null;

  let fontMinusBtn = null;

  let fontPlusBtn = null;

  let peerAdvisoryRow = null;

  let peerAdvisoryText = null;

  let peerApplyBtn = null;

  let boldBtn = null;

  let italicBtn = null;

  let underlineBtn = null;

  let alignLeftBtn = null;

  let alignCenterBtn = null;

  let alignRightBtn = null;

  let verticalTopBtn = null;

  let verticalCenterBtn = null;

  let verticalBottomBtn = null;

  let colorControlRow = null;

  let backgroundColorControlRow = null;

  let textToolRow = null;

  let textAlignToolRow = null;

  let alignToolRow = null;

  let groupToolRow = null;

  let groupBtn = null;

  let ungroupBtn = null;

  let editGroupMemberBtn = null;

  let selectWholeGroupBtn = null;

  let objectContextMenu = null;

  let contextDuplicateBtn = null;

  let contextBringFrontBtn = null;

  let contextSendBackBtn = null;

  let contextGroupBtn = null;

  let contextDeleteBtn = null;

  let contextUngroupBtn = null;

  let lineHeightInput = null;

  let letterSpacingInput = null;

  let fontSizeRange = null;

  let lineHeightRange = null;

  let letterSpacingRange = null;

  let guideX = null;

  let guideY = null;

  let actionStatus = null;

  let appearanceBtn = null;

  let appearancePanel = null;

  let deckFontSelect = null;

  let slideMaskColorInput = null;

  let slideMaskOpacityRange = null;

  let slideMaskOpacityValue = null;

  let slideMaskResetButton = null;

  function t(template, vars) {

    let out = template;

    Object.keys(vars || {}).forEach((key) => {

      out = out.replace(new RegExp('\\{' + key + '\\}', 'g'), vars[key]);

    });

    return out;

  }



  function setReadout(text) {

    if (hint) {

      hint.dataset.lastMessage = text || '';

      hint.style.display = 'none';

      hint.textContent = '';

      hint.classList.add('hide');

      hint.setAttribute('aria-hidden', 'true');

    }

    if (actionStatus) {

      actionStatus.textContent = text || '';

      actionStatus.style.display = text ? 'inline-flex' : 'none';

      actionStatus.setAttribute('aria-hidden', text ? 'false' : 'true');

    }

  }



  function lockPointerSelection() {

    previousUserSelect = document.body.style.userSelect;

    document.body.style.userSelect = 'none';

  }



  function unlockPointerSelection() {

    document.body.style.userSelect = previousUserSelect;

  }



  function restoreReadout() {

    setReadout('');

  }



  function showTransientReadout(text, ms) {

    setReadout(text);

    if (readoutTimer) clearTimeout(readoutTimer);

    readoutTimer = setTimeout(() => {

      readoutTimer = null;

      restoreReadout();

    }, ms || 1600);

  }



  function setAutoSaveState(state, detail) {

    autoSaveState = state || 'idle';

    if (!saveBtn) return;

    saveBtn.dataset.autoSaveState = autoSaveState;

    saveBtn.dataset.autoSaveEnabled = isWritableDevServer() ? 'true' : 'draft-only';

    if (detail) saveBtn.dataset.autoSaveDetail = detail;

    else delete saveBtn.dataset.autoSaveDetail;

  }



  function getScale() {

    const match = stage.style.transform.match(/scale\(([\d.]+)\)/);

    return match ? parseFloat(match[1]) : 1;

  }



  function isTypingContext() {

    const ae = document.activeElement;

    return !!(ae && (ae.isContentEditable || ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA'));

  }



  function isReadOnlyPreview() {

    try {

      const params = new URLSearchParams(location.search || '');

      return params.get('preview') === '1' || params.get('readonly') === '1';

    } catch (err) {

      return false;

    }

  }



  function isWritableDevServer() {

    return !isReadOnlyPreview()

      && (location.protocol === 'http:' || location.protocol === 'https:')

      && (location.hostname === '127.0.0.1' || location.hostname === 'localhost');

  }



  function requireEditMode(actionLabel) {

    if (editMode) return true;

    showTransientReadout(t(M.enableEditFirst, { action: actionLabel }));

    return false;

  }



  function elementLabel(el) {

    const cls = (el.className || '').toString().replace(/\bel\b/, '').trim();

    return cls || el.tagName.toLowerCase();

  }



  function elementRole(el) {

    if (!el || !el.classList) return '';

    const classes = Array.from(el.classList);

    const idx = classes.indexOf('el');

    return idx >= 0 ? (classes[idx + 1] || '') : '';

  }



  function findPeers(el) {

    const role = elementRole(el);

    const slide = el ? el.closest('.slide') : null;

    if (!role || !slide) return [];

    return Array.from(slide.querySelectorAll('.el')).filter((peer) => {

      return peer !== el && elementRole(peer) === role && hasOwnUniformFontSize(peer);

    });

  }



  function activeSelectedEls() {

    selectedEls = selectedEls.filter((el) => el && document.contains(el));

    if (selectedEl && selectedEls.indexOf(selectedEl) < 0 && document.contains(selectedEl)) {

      selectedEls.unshift(selectedEl);

    }

    return selectedEls.slice();

  }



  function setSelection(els, primary, groupIdValue, depthHint) {

    selectedEls = Array.from(new Set((els || []).filter((el) => el && document.contains(el))));

    selectedEl = primary && selectedEls.indexOf(primary) >= 0 ? primary : (selectedEls[0] || null);

    selectedGroupId = groupIdValue || null;

    if (selectedGroupId && selectedEl) selectedGroupDepth = groupPath(selectedEl).indexOf(selectedGroupId);

    else selectedGroupDepth = Number.isInteger(depthHint) ? depthHint : -1;

    observeSelectedGeometry();

    scheduleSelectionRefresh();

  }

  function captureSelectionSnapshot() {

    const keys = activeSelectedEls()

      .map((el) => elementKey(el))

      .filter((key) => typeof key === 'string' && key.length > 0);

    return {

      keys: keys,

      primaryKey: selectedEl ? elementKey(selectedEl) : null,

      groupId: selectedGroupId || null,

      groupDepth: selectedGroupDepth,

      tool: currentTool

    };

  }



  function restoreSelectionSnapshot(snapshot) {

    if (!snapshot || !Array.isArray(snapshot.keys)) return false;

    const targets = snapshot.keys

      .map((key) => elementByKey(key))

      .filter((el) => el && document.contains(el));

    const primaryCandidate = snapshot.primaryKey ? elementByKey(snapshot.primaryKey) : null;

    const primary = primaryCandidate && targets.indexOf(primaryCandidate) >= 0

      ? primaryCandidate

      : (targets[0] || null);

    setSelection(

      targets,

      primary,

      snapshot.groupId || null,

      Number.isInteger(snapshot.groupDepth) ? snapshot.groupDepth : -1

    );

    currentTool = snapshot.tool || (targets.length ? 'move' : null);

    applyEditableState();

    if (targets.length) repositionHandles();

    else hideHandles();

    updateSelectionBadge();

    return true;

  }



  function fitAdaptiveTypography(item, reposition, restoreScale) {

    const adaptive = item.adaptive;
    const maximumScale = Math.max(1, restoreScale || 1);

    const apply = (fontScale) => {

      // Shrinking consumes line-height spacing before type. During recovery,
      // line-height must grow only proportionally; squaring a scale above one
      // makes the old line box hit the frame before the glyph size can return.
      applyAdaptiveTypographyMetrics(adaptive.typography, Math.min(1, fontScale), fontScale);

      reposition(item);

      adaptive.appliedLineHeightScale = fontScale;

      adaptive.appliedFontScale = fontScale;

    };

    if (maximumScale > 1) {
      apply(maximumScale);
      if (adaptiveGroupTextFits(item)) return maximumScale;

      apply(1);
      if (adaptiveGroupTextFits(item)) {
        let valid = 1;
        let invalid = maximumScale;
        for (let index = 0; index < 10; index += 1) {
          const candidate = (valid + invalid) / 2;
          apply(candidate);
          if (adaptiveGroupTextFits(item)) valid = candidate;
          else invalid = candidate;
        }
        apply(valid);
        return valid;
      }
    }

    apply(1);

    if (adaptiveGroupTextFits(item)) return 1;



    // The font-size floor controls how far the whole type system may shrink.

    // minimumLineHeightScale is a ratio guard inside

    // applyAdaptiveTypographyMetrics; treating it as a global scale floor

    // prevents text from shrinking when spacing has already been exhausted.

    const minimumScale = adaptive.minimumFontScale;

    apply(minimumScale);

    if (!adaptiveGroupTextFits(item)) return minimumScale;



    let low = minimumScale;

    let high = 1;

    for (let index = 0; index < 10; index += 1) {

      const candidate = (low + high) / 2;

      apply(candidate);

      if (adaptiveGroupTextFits(item)) low = candidate;

      else high = candidate;

    }

    apply(low);

    return low;

  }



  function attachSelectionHistoryTransition(undoDepth, beforeSnapshot, afterSnapshot) {

    if (undoStack.length <= undoDepth) return false;

    const command = undoStack[undoStack.length - 1];

    if (!command) return false;

    command.selectionBefore = beforeSnapshot;

    command.selectionAfter = afterSnapshot;

    return true;

  }





  function reconcileSelectedGroup() {

    if (!selectedGroupId) return;

    const selected = activeSelectedEls().map(editableRoot);

    if (!selected.length || selected.some((el) => groupPath(el).indexOf(selectedGroupId) < 0)) {

      selectedGroupId = null;

      selectedGroupDepth = -1;

    }

  }



  function editableElements(slide) {

    if (!slide) return [];

    return Array.from(slide.querySelectorAll('.el,[data-edit-layer]')).filter((el) => {

      const root = el.classList && el.classList.contains('el') ? el : el.closest('.el');

      return !(el.matches && el.matches('[data-content-area]'))

        && !(root && root.dataset && root.dataset.editLayoutOnly === 'true');

    });

  }



  function editableRoot(el) {

    if (!el) return null;

    const root = el.classList && el.classList.contains('el') ? el : el.closest('.el');

    if (root && root.matches && root.matches('[data-content-area]')) return null;

    if (root && root.dataset && root.dataset.editLayoutOnly === 'true') return null;

    return root;

  }



  // data-edit-composite is an internal renderer/container detail.  In the

  // editor it is exposed as an AI-generated group so authors do not have to

  // learn a second grouping concept.  The wrapper stays intact to preserve

  // materialized geometry; ungrouping only switches hit-testing to its layers.

  function isCompositeRoot(el) {

    const root = editableRoot(el);

    return !!(root && root.dataset && root.dataset.editComposite);

  }



  function isGeneratedGroup(el) {

    const root = editableRoot(el);

    return isCompositeRoot(root) && root.dataset.editGroupState !== 'ungrouped';

  }



  function generatedGroupMembers(el) {

    const root = editableRoot(el);

    if (!isCompositeRoot(root)) return [];

    const isVisible = (item) => {

      const style = getComputedStyle(item);

      return item.getClientRects().length > 0

        && style.display !== 'none'

        && style.visibility !== 'hidden';

    };

    const nestedRoots = Array.from(root.querySelectorAll('.el')).filter((item) => {

      const parentRoot = item.parentElement && item.parentElement.closest('.el');

      return parentRoot === root && isVisible(item);

    });

    const directLayers = Array.from(root.querySelectorAll('[data-edit-layer]')).filter((item) => (

      item.closest('.el') === root && isVisible(item)

    ));

    if (nestedRoots.length) return nestedRoots.concat(directLayers);

    return directLayers;

  }



  function materializeUngroupedLayerGeometry(root, members) {

    if (!root || !Array.isArray(members) || !members.length) return;

    // Measure every member before changing any one of them.  A flow parent
    // (for example the <ul> inside a comparison panel) will reflow as soon
    // as its first child becomes absolute.  Reading offsetLeft/offsetTop in
    // the old loop therefore made later siblings collapse to zero.
    const snapshots = members.map((member) => {

      if (!member || !document.contains(member)) return null;

      const computedStyle = getComputedStyle(member);

      if (computedStyle.display === 'none' || computedStyle.visibility === 'hidden') return null;

      const rect = member.getBoundingClientRect();

      if (!(rect.width > 0.5 && rect.height > 0.5)) return null;

      const offsetParent = member.offsetParent && (
        member.offsetParent === root || root.contains(member.offsetParent)
      ) ? member.offsetParent : root;
      const parentBox = stageBox(offsetParent);
      const parentScale = Math.max(getElementVisualScale(offsetParent), 0.0001);
      const borderLeft = Number(offsetParent.clientLeft) || 0;
      const borderTop = Number(offsetParent.clientTop) || 0;
      const box = stageBox(member);

      return {
        member: member,
        left: (box.left - parentBox.left) / parentScale - borderLeft,
        top: (box.top - parentBox.top) / parentScale - borderTop,
        width: Math.max(MIN_SIZE, Math.round(box.width * 10) / 10),
        height: Math.max(MIN_SIZE, Math.round(box.height * 10) / 10)
      };

    }).filter(Boolean);

    snapshots.forEach((snapshot) => {

      const member = snapshot.member;



      // Keep the renderer wrapper as a transparent geometry owner, but turn

      // every direct layer into a stable, movable absolute frame.  Without

      // this materialization, a text layer with width:auto remains constrained

      // by the surface after its left/top moves beyond the surface boundary.

      setUserStyle(member, 'position', 'absolute');

      setUserStyle(member, 'inset', 'auto');

      setUserStyle(member, 'left', Math.round(snapshot.left * 10) / 10 + 'px');

      setUserStyle(member, 'top', Math.round(snapshot.top * 10) / 10 + 'px');

      setUserStyle(member, 'right', 'auto');

      setUserStyle(member, 'bottom', 'auto');

      setUserStyle(member, 'width', snapshot.width + 'px');

      setUserStyle(member, 'height', snapshot.height + 'px');

      setUserStyle(member, 'max-width', 'none');

      setUserStyle(member, 'max-height', 'none');

      setUserStyle(member, 'box-sizing', 'border-box');

      if (member.dataset) member.dataset.editPosition = 'absolute';

    });

  }



  function clearGroupEditScopes() {

    groupEditScopes.length = 0;

  }



  function currentGroupEditScope() {

    while (groupEditScopes.length) {

      const scope = groupEditScopes[groupEditScopes.length - 1];

      const generatedValid = scope.kind === 'generated'

        && scope.group

        && document.contains(scope.group)

        && isGeneratedGroup(scope.group);

      const manualValid = scope.kind === 'manual'

        && scope.primary

        && document.contains(scope.primary)

        && groupPath(scope.primary).indexOf(scope.groupId) >= 0;

      if (generatedValid || manualValid) return scope;

      groupEditScopes.pop();

    }

    return null;

  }



  function rectContainsPoint(rect, clientX, clientY) {

    return !!(rect

      && Number.isFinite(clientX)

      && Number.isFinite(clientY)

      && clientX >= rect.left

      && clientX <= rect.right

      && clientY >= rect.top

      && clientY <= rect.bottom);

  }



  function unionSelectionRect(targets) {

    const rects = (targets || [])

      .filter((target) => target && document.contains(target) && getComputedStyle(target).display !== 'none')

      .map(visualSelectionRect)

      .filter((rect) => rect && rect.width > 0.5 && rect.height > 0.5);

    if (!rects.length) return null;

    const left = Math.min.apply(null, rects.map((rect) => rect.left));

    const top = Math.min.apply(null, rects.map((rect) => rect.top));

    const right = Math.max.apply(null, rects.map((rect) => rect.right));

    const bottom = Math.max.apply(null, rects.map((rect) => rect.bottom));

    return { left: left, top: top, right: right, bottom: bottom, width: right - left, height: bottom - top };

  }



  function groupEditScopeRect(scope) {

    if (!scope) return null;

    if (scope.kind === 'generated') return unionSelectionRect([scope.group]);

    if (scope.kind === 'manual') return unionSelectionRect(groupMembers(scope.primary, scope.groupId));

    return null;

  }



  function groupEditScopeContainsPoint(scope, clientX, clientY) {

    return rectContainsPoint(groupEditScopeRect(scope), clientX, clientY);

  }



  function directGeneratedGroupMember(group, root, layer) {

    if (!group || !root || !isGeneratedGroup(group)) return null;

    if (root === group) {

      return layer && layer.closest('.el') === group ? layer : group;

    }

    if (!group.contains(root)) return null;

    let candidate = root;

    let parent = candidate.parentElement && candidate.parentElement.closest('.el');

    while (candidate && parent && parent !== group) {

      candidate = parent;

      parent = candidate.parentElement && candidate.parentElement.closest('.el');

    }

    return parent === group ? candidate : null;

  }



  function outermostGeneratedGroup(root) {

    let current = root;

    let outermost = null;

    while (current) {

      if (isGeneratedGroup(current)) outermost = current;

      current = current.parentElement && current.parentElement.closest('.el');

    }

    return outermost;

  }



  function selectedFormalGroupTargetAtPoint(clientX, clientY) {

    const targets = activeSelectedEls();

    if (!targets.length || selectionPresentationMode(targets) !== 'group') return null;

    const primary = editableRoot(selectedEl) || editableRoot(targets[0]);

    if (!primary) return null;

    const groupTargets = selectedGroupId ? groupMembers(primary, selectedGroupId) : [primary];

    return rectContainsPoint(unionSelectionRect(groupTargets), clientX, clientY) ? primary : null;

  }



  function groupResizeLeafTargets(targets) {

    const leaves = [];

    const seen = new Set();

    const add = (target) => {

      if (!target || seen.has(target) || getComputedStyle(target).display === 'none') return;

      seen.add(target);

      leaves.push(target);

    };

    const visit = (target) => {

      const directLayer = target && target.dataset && target.dataset.editLayer

        && !(target.classList && target.classList.contains('el'));

      if (directLayer) {

        add(target);

        return;

      }

      const root = editableRoot(target) || target;

      if (!root) return;

      // A semantic module owns real geometry and must remain atomic. A broader

      // generated composite is only grouping context: when it is regrouped

      // with a sibling, resize its visible leaf modules and direct surfaces.

      if (root.dataset && root.dataset.editStructure === 'module') {

        add(root);

        return;

      }

      if (isCompositeRoot(root)) {

        const members = generatedGroupMembers(root).filter((member) => (

          (member.classList && member.classList.contains('el'))

          || (member.dataset && (member.dataset.editLayer === 'visual'

            || member.dataset.editLayer === 'background'))

        ));

        if (members.length) {

          members.forEach(visit);

          return;

        }

      }

      add(root);

    };

    (targets || []).forEach(visit);

    return leaves;

  }



  function generatedGroupCount(el) {

    return Math.max(1, generatedGroupMembers(el).length);

  }



  function groupPath(el) {

    const root = editableRoot(el);

    const value = root && root.dataset ? (root.dataset.editGroup || '') : '';

    return value ? value.split('>').filter(Boolean) : [];

  }



  function groupId(el) {

    return groupPath(el).join('>');

  }



  function setGroupPath(el, path) {

    const root = editableRoot(el);

    if (!root || !root.dataset) return;

    const value = (path || []).filter(Boolean).join('>');

    if (value) root.dataset.editGroup = value;

    else delete root.dataset.editGroup;

  }



  function outerGroupId(el) {

    const path = groupPath(el);

    return path.length ? path[path.length - 1] : '';

  }



  function groupMembers(el, explicitId) {

    const id = explicitId || outerGroupId(el);

    const slide = el ? el.closest('.slide') : null;

    if (!id || !slide) return el ? [el] : [];

    return Array.from(slide.querySelectorAll('.el')).filter((item) => groupPath(item).indexOf(id) >= 0 && getComputedStyle(item).display !== 'none');

  }



  function newGroupId() {

    groupSequence += 1;

    return 'group-' + Date.now().toString(36) + '-' + groupSequence.toString(36);

  }



  function remapCloneGroups(clones) {

    const replacements = {};

    (clones || []).forEach((clone) => {

      const path = groupPath(clone).map((id) => {

        if (!replacements[id]) replacements[id] = newGroupId();

        return replacements[id];

      });

      setGroupPath(clone, path);

    });

  }



  function isEditorChromeTarget(node) {

    return !!(node && node.closest && node.closest(

      '[data-editor-chrome],#bar,#edit-mode-panel,#edit-selection-badge,#edit-draft-prompt,#edit-help-panel'

    ));

  }



  function isTightTextPointerTarget(el) {

    if (!el || !(el.textContent || '').trim()) return false;

    const editLayer = el.dataset ? el.dataset.editLayer : '';

    const usesTextBounds = !!(el.dataset && el.dataset.editFit === 'text')

      || editLayer === 'text'

      || editLayer === 'metric';

    if (!usesTextBounds) return false;

    const style = getComputedStyle(el);

    const borderWidth = ['borderLeftWidth', 'borderRightWidth', 'borderTopWidth', 'borderBottomWidth']

      .reduce((sum, key) => sum + (parseFloat(style[key]) || 0), 0);

    const background = String(style.backgroundColor || '');

    return !(borderWidth > 0.5

      || (style.backgroundImage && style.backgroundImage !== 'none')

      || (background && background !== 'transparent' && !/rgba?\([^)]*,\s*0(?:\.0+)?\s*\)$/.test(background)));

  }



  function textPointerRects(el) {

    if (!isTightTextPointerTarget(el) || !document.createRange || !document.createTreeWalker) return [];

    const rects = [];

    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {

      acceptNode: (node) => (

        node.nodeValue && node.nodeValue.trim()

          ? NodeFilter.FILTER_ACCEPT

          : NodeFilter.FILTER_REJECT

      )

    });

    let node = walker.nextNode();

    while (node) {

      const range = document.createRange();

      range.selectNodeContents(node);

      Array.from(range.getClientRects()).forEach((rect) => {

        if (rect.width > 0.5 && rect.height > 0.5) rects.push(rect);

      });

      node = walker.nextNode();

    }

    return rects;

  }



  function pointerTargetContainsPoint(target, clientX, clientY) {

    if (isGeneratedGroup(target) && target.dataset && target.dataset.editFitChildren === 'true') {

      // A formal group owns its complete visible-union frame. Gaps between

      // members are part of that frame and must not expose child objects or

      // unrelated objects underneath the group.

      return rectContainsPoint(unionSelectionRect([target]), clientX, clientY);

    }

    if (!isTightTextPointerTarget(target)) return true;

    const rects = textPointerRects(target);

    if (!rects.length) return false;

    return rects.some((rect) => (

      clientX >= rect.left - TEXT_HIT_SLOP_PX

      && clientX <= rect.right + TEXT_HIT_SLOP_PX

      && clientY >= rect.top - TEXT_HIT_SLOP_PX

      && clientY <= rect.bottom + TEXT_HIT_SLOP_PX

    ));

  }



  function directLayerAtPoint(root, clientX, clientY) {

    if (!root) return null;

    const layers = Array.from(root.querySelectorAll('[data-edit-layer]')).filter((item) => {

      if (item.closest('.el') !== root) return false;

      const style = getComputedStyle(item);

      if (style.display === 'none' || style.visibility === 'hidden') return false;

      const rect = item.getBoundingClientRect();

      return rect.width > 0.5 && rect.height > 0.5

        && clientX >= rect.left && clientX <= rect.right

        && clientY >= rect.top && clientY <= rect.bottom;

    });

    // A text frame can be much wider or taller than its visible glyphs.  Do

    // not let that transparent part consume the hit and then abort selection;

    // only a foreground layer that truly contains the pointer may outrank the

    // background.  Otherwise the same point must fall back to the real board.

    const foreground = layers.filter((item) => (

      item.dataset.editLayer !== 'background'

      && pointerTargetContainsPoint(item, clientX, clientY)

    ));

    return foreground[foreground.length - 1]

      || layers.find((item) => item.dataset.editLayer === 'background')

      || null;

  }



  function pointerTargetForRoot(root, layer, additiveSelection, directGroupSelection) {

    if (!root || getComputedStyle(root).display === 'none') return null;

    if (root.matches && root.matches('[data-content-area]')) return null;

    if (root.dataset && root.dataset.editLayoutOnly === 'true') return null;

    // Ctrl/Cmd is an explicit, one-click group bypass. It never mutates the
    // formal group path or persistent drill-in scope; releasing the modifier
    // restores ordinary whole-group hit testing.
    if (directGroupSelection) {

      if (layer && root.contains(layer)) return layer;

      return root;

    }

    const editScope = currentGroupEditScope();

    if (editScope && editScope.kind === 'generated') {

      return directGeneratedGroupMember(editScope.group, root, layer);

    }

    if (editScope && editScope.kind === 'manual') {

      return groupPath(root).indexOf(editScope.groupId) >= 0 ? root : null;

    }

    const manualGroupPath = groupPath(root);

    if (manualGroupPath.length > 0) return root;

    // Ordinary clicking is deterministic: any descendant of a generated

    // hierarchy resolves to the outermost formal group. A child becomes a

    // target only while an explicit edit-group scope is active.

    const generatedAncestor = outermostGeneratedGroup(root);

    if (generatedAncestor) return generatedAncestor;

    if (layer && root.contains(layer) && isCompositeRoot(root) && !isGeneratedGroup(root)) return layer;

    const selectedSiblingLayer = selectedEl

      && selectedEl.dataset

      && selectedEl.dataset.editLayer

      && editableRoot(selectedEl) === root;

    if (layer && root.contains(layer)

      && ((activeSelectedEls().length === 1 && (selectedEl === root || selectedEl === layer))

        || selectedSiblingLayer)) return layer;

    // An ungrouped renderer composite remains in the DOM only to preserve its

    // authored geometry. Its transparent wrapper must no longer be a pointer

    // target; otherwise a later click recreates the full-group selection.

    if (isCompositeRoot(root) && !isGeneratedGroup(root)) return null;

    return root;

  }



  function pointerTargetsAt(clientX, clientY, additiveSelection, directGroupSelection) {

    if (!Number.isFinite(clientX) || !Number.isFinite(clientY) || !document.elementsFromPoint) return [];

    const active = document.querySelector('.slide.active');

    if (!active) return [];

    const seen = new Set();

    const targets = document.elementsFromPoint(clientX, clientY).reduce((items, node) => {

      if (!node || !node.closest || isEditorChromeTarget(node) || node.closest('#overview')) return items;

      const root = node.closest('.el');

      if (!root || !active.contains(root)) return items;

      const layoutOnly = node.closest('[data-edit-layout-only="true"]');

      if (layoutOnly && root === layoutOnly.closest('.el')) return items;

      let layer = node.closest('[data-edit-layer]');

      if ((!layer || !root.contains(layer)) && isCompositeRoot(root)
        && (directGroupSelection || !isGeneratedGroup(root))) {

        layer = directLayerAtPoint(root, clientX, clientY);

      }

      const target = pointerTargetForRoot(
        root,
        layer && root.contains(layer) ? layer : null,
        additiveSelection,
        directGroupSelection
      );

      if (!target || seen.has(target) || !pointerTargetContainsPoint(target, clientX, clientY)) return items;

      seen.add(target);

      items.push(target);

      return items;

    }, []);

    const selectedRoot = editableRoot(selectedEl);

    if (selectedRoot && isGeneratedGroup(selectedRoot)) {

      const selectedLayerIndex = targets.findIndex((target) => (

        target !== selectedRoot

        && target.dataset

        && target.dataset.editLayer

        && editableRoot(target) === selectedRoot

      ));

      if (selectedLayerIndex > 0) {

        const selectedLayer = targets.splice(selectedLayerIndex, 1)[0];

        targets.unshift(selectedLayer);

      }

    }

    return targets;

  }



  function marqueeSelectionTargets(slide) {

    if (!slide) return [];

    const targets = [];

    Array.from(slide.querySelectorAll('.el')).forEach((root) => {

      if (root.dataset && root.dataset.editLayoutOnly === 'true') return;

      const parentRoot = root.parentElement && root.parentElement.closest('.el');

      if (parentRoot && isGeneratedGroup(parentRoot)) return;

      if (isCompositeRoot(root) && !isGeneratedGroup(root)) {

        generatedGroupMembers(root).forEach((member) => targets.push(member));

      } else {

        targets.push(root);

      }

    });

    return Array.from(new Set(targets)).filter((target) => {

      const style = getComputedStyle(target);

      return target.getClientRects().length > 0

        && style.display !== 'none'

        && style.visibility !== 'hidden';

    });

  }



  function resolvePointerTarget(node, clientX, clientY, preferHitTest, additiveSelection, directGroupSelection) {

    if (!node || !node.closest) return null;

    if (node.closest('#overview') || isEditorChromeTarget(node)) return null;

    const activeScope = currentGroupEditScope();

    if (activeScope && !groupEditScopeContainsPoint(activeScope, clientX, clientY)) {

      clearGroupEditScopes();

    }

    if (!currentGroupEditScope() && !additiveSelection && !directGroupSelection) {

      const lockedGroup = selectedFormalGroupTargetAtPoint(clientX, clientY);

      if (lockedGroup) return lockedGroup;

    }

    if (preferHitTest) {

      const hitTargets = pointerTargetsAt(clientX, clientY, additiveSelection, directGroupSelection);

      return hitTargets.length ? hitTargets[0] : null;

    }

    const root = node.closest('.el');

    if (!root) return null;

    const layoutOnly = node.closest('[data-edit-layout-only="true"]');

    if (layoutOnly && root === layoutOnly.closest('.el')) return null;

    const layer = root.contains(node) ? node.closest('[data-edit-layer]') : null;

    const directLayer = (!layer || !root.contains(layer)) && directGroupSelection && isCompositeRoot(root)
      ? directLayerAtPoint(root, clientX, clientY)
      : null;
    return pointerTargetForRoot(
      root,
      directLayer || (layer && root.contains(layer) ? layer : null),
      additiveSelection,
      directGroupSelection
    );

  }



  function selectionLabel() {

    const count = activeSelectedEls().length;

    const targets = selectedTargets();

    const presentationMode = selectionPresentationMode(targets);

    if (presentationMode === 'group') {

      const primary = editableRoot(selectedEl) || editableRoot(targets[0]);

      const memberCount = selectedGroupId

        ? groupMembers(primary, selectedGroupId).length

        : generatedGroupCount(primary);

      return t(M.groupSelected, { count: memberCount });

    }

    if (count > 1) return t(M.multiSelected, { count: count });

    const target = targets[0];

    if (target && target.dataset && target.dataset.editLayer === 'background') return M.selectedBackground;

    if (isTextEditableElement(target)) return M.selectedText;

    if (target) return M.selectedVisual;

    return currentToolMeta().label;

  }



  function selectedTargets() {

    return activeSelectedEls().length ? activeSelectedEls() : (selectedEl ? [selectedEl] : []);

  }



  function scheduleSelectionRefresh() {

    if (selectionRefreshRaf) cancelAnimationFrame(selectionRefreshRaf);

    selectionRefreshRaf = requestAnimationFrame(() => {

      selectionRefreshRaf = 0;

      if (!editMode || !selectedEl) return;

      repositionHandles();

      requestAnimationFrame(() => {

        if (editMode && selectedEl) repositionHandles();

      });

    });

  }



  function observeSelectedGeometry() {

    if (selectionResizeObserver) selectionResizeObserver.disconnect();

    if (!window.ResizeObserver) return;

    if (!selectionResizeObserver) {

      selectionResizeObserver = new ResizeObserver(() => scheduleSelectionRefresh());

    }

    Array.from(new Set(selectedTargets().filter(Boolean))).forEach((el) => selectionResizeObserver.observe(el));

  }



  function isTextEditableElement(el) {

    if (!el) return false;

    if (el.dataset && el.dataset.editComposite) return false;

    const editLayer = el.dataset ? el.dataset.editLayer : '';

    if (editLayer && editLayer !== 'text' && editLayer !== 'metric') return false;

    if (el.dataset && el.dataset.editKind && el.dataset.editKind !== 'text') return false;

    if (!el.textContent || !el.textContent.trim()) return false;

    if (el.querySelector('.el')) return false;

    const tag = el.tagName;

    if (tag === 'IMG' || tag === 'VIDEO' || tag === 'CANVAS' || tag === 'SVG') return false;

    return true;

  }



  function resolveResizeMode(targets, target, handle) {

    const items = (targets || []).filter(Boolean);

    const corner = handle && handle.length === 2;

    const horizontal = handle === 'e' || handle === 'w';

    if (items.length > 1) {

      return corner ? 'group-proportional' : (horizontal ? 'group-width' : 'group-height');

    }

    if (isTextEditableElement(target)) {

      return corner ? 'text-proportional' : (horizontal ? 'text-frame-width' : 'text-frame-height');

    }

    if (isCompositeRoot(target)) {

      return corner ? 'composite-proportional' : (horizontal ? 'composite-width' : 'composite-height');

    }

    return corner ? 'element-proportional' : (horizontal ? 'element-width' : 'element-height');

  }



  function selectedTextTargets() {

    const targets = selectedTargets().filter(Boolean);

    if (!targets.length) return [];

    if (selectionPresentationMode(targets) !== 'group') {

      // A normal multi-selection may contain both text and visual layers.
      // Keep the visible text subset addressable so text color and typography
      // commands do not fall through to a composite wrapper's background.
      return Array.from(new Set(targets.filter(isTextEditableElement)));

    }



    // The group frame is the authority for group operations.  Once a footer,

    // caption, or nested module is inside that frame, its visible text layers

    // must participate in the same typography batch instead of being silently

    // omitted because the selected root itself is a visual composite.

    const primary = editableRoot(selectedEl) || editableRoot(targets[0]);

    const scopes = selectedGroupId

      ? Array.from(new Set(targets.map(editableRoot).filter(Boolean)))

      : (primary ? [primary] : []);

    const candidates = [];

    scopes.forEach((scope) => {

      if (isTextEditableElement(scope)) candidates.push(scope);

      scope.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"],[data-edit-kind="text"],[data-edit-kind="metric"],.el').forEach((item) => {

        if (isTextEditableElement(item)) candidates.push(item);

      });

    });

    return Array.from(new Set(candidates)).filter((el) => {

      const style = getComputedStyle(el);

      return el.getClientRects().length > 0

        && style.display !== 'none'

        && style.visibility !== 'hidden';

    });

  }



  function groupSurfaceTarget(el) {

    if (!el) return null;

    if (el.dataset && el.dataset.editLayer === 'background') return el;

    const root = editableRoot(el) || el;

    if (!root) return null;

    const directBackground = Array.from(root.children || []).find((child) => {

      const style = getComputedStyle(child);

      return child.dataset

        && child.dataset.editLayer === 'background'

        && style.display !== 'none'

        && style.visibility !== 'hidden';

    });

    if (directBackground) return directBackground;

    // A manually inserted primitive can own its surface directly on the root
    // instead of exposing a separate background layer.  Include that root in
    // a whole-group paint operation, while never treating a plain text frame
    // as a surface target.
    if (isTextEditableElement(root)) return null;

    const style = getComputedStyle(root);

    const background = String(style.backgroundColor || '');

    const hasSurfacePaint = (style.backgroundImage && style.backgroundImage !== 'none')

      || (background

        && background !== 'transparent'

        && !/rgba?\([^)]*,\s*0(?:\.0+)?\s*\)$/.test(background));

    return hasSurfacePaint ? root : null;

  }



  function isUngroupedDirectLayer(el) {

    if (!el || !el.hasAttribute || !el.hasAttribute('data-edit-layer')) return false;

    const root = el.closest && el.closest('.el');

    return !!(root

      && root !== el

      && root.dataset

      && root.dataset.editComposite

      && root.dataset.editGroupState === 'ungrouped');

  }



  function selectionBackgroundTarget(el) {

    if (!el) return null;

    if (el.dataset && el.dataset.editLayer === 'background') return el;

    // Once a semantic module is ungrouped, its direct layers are the
    // editable paint targets. Do not resolve them back to the preserved
    // renderer wrapper, otherwise a child color change paints the wrapper's
    // background instead of the selected child.
    if (isUngroupedDirectLayer(el)) return el;

    if (isTextEditableElement(el)) return el;

    const root = editableRoot(el);

    if (!root || root !== el) return null;

    return groupSurfaceTarget(root);

  }



  function selectionCapabilities() {

    const targets = selectedTargets().filter(Boolean);

    const textTargets = selectedTextTargets();

    const presentationMode = selectionPresentationMode(targets);

    const activeGroupEditScope = currentGroupEditScope();

    const groupText = presentationMode === 'group' && textTargets.length > 0;

    // A whole group is an atomic object.  Its descendant text nodes must not
    // become background-color targets by accident; authors can still edit a
    // specific member after entering the explicit group-edit scope.
    const wholeGroup = presentationMode === 'group' && !activeGroupEditScope;

    const allText = targets.length > 0 && targets.every(isTextEditableElement);

    const allBackground = targets.length > 0 && targets.every((el) => {

      return el.dataset && el.dataset.editLayer === 'background';

    });

    const compositeBackgroundTargets = targets.map((el) => {

      const root = editableRoot(el);

      if (!root) return null;

      return Array.from(root.children || []).find((child) => {

        return child.dataset && child.dataset.editLayer === 'background';

      }) || null;

    });

    const allCompositeBackground = targets.length > 0

      && compositeBackgroundTargets.every(Boolean);

    const wholeGroupSurfaceTargets = wholeGroup

      ? Array.from(new Set(targets.map(groupSurfaceTarget).filter(Boolean)))

      : [];

    const wholeGroupBackgroundTargets = wholeGroup

      ? Array.from(new Set(

        (groupText ? textTargets : []).concat(wholeGroupSurfaceTargets)

      ))

      : [];

    const objectBackgroundTargets = Array.from(new Set(

      targets.map(selectionBackgroundTarget).filter(Boolean)

    ));

    const backgroundTargets = wholeGroup

      ? wholeGroupBackgroundTargets

      : objectBackgroundTargets;

    const colorTargets = groupText

      ? textTargets

      : (textTargets.length ? textTargets : objectBackgroundTargets);

    return {

      targets: targets,

      allText: allText,

      allBackground: allBackground,

      allCompositeBackground: allCompositeBackground,

      textTargets: textTargets,

      backgroundTargets: backgroundTargets,

      wholeGroup: wholeGroup,

      colorTargets: colorTargets,

      canUseTextTools: textTargets.length > 0,

      canUseColor: colorTargets.length > 0,

      canUseBackground: backgroundTargets.length > 0

    };

  }



  function hasDirectText(el) {

    return Array.from(el.childNodes || []).some((node) => {

      return node.nodeType === 3 && node.nodeValue && node.nodeValue.trim();

    });

  }



  function isVerticalTextBox(el) {

    if (!isTextEditableElement(el)) return false;

    // Flow/auto-height text has no spare frame height to align within. Turning
    // it into a flex box changes grid and inline layout, so vertical alignment
    // controls apply only to fixed-frame text.
    if (el.dataset && el.dataset.editPosition === 'flow') return false;

    const blockChildren = Array.from(el.children || []).filter((child) => {

      return !['BR', 'SPAN', 'STRONG', 'EM', 'B', 'I', 'U', 'SUP', 'SUB'].includes(child.tagName);

    });

    return blockChildren.length === 0;

  }



  function verticalAlignmentState(el) {

    if (!el) return 'start';

    if (el.dataset && el.dataset.editVerticalAlign) return el.dataset.editVerticalAlign;

    const cs = getComputedStyle(el);

    if (cs.display === 'flex' && cs.flexDirection === 'column') {

      if (cs.justifyContent === 'center') return 'center';

      if (cs.justifyContent === 'flex-end' || cs.justifyContent === 'end') return 'end';

    }

    return isVerticalTextBox(el) ? 'center' : 'start';

  }



  function applyDeclaredVerticalAlignment(el, overrideValue) {

    if (!isVerticalTextBox(el)) return;

    const value = overrideValue || (el.dataset && el.dataset.editVerticalAlign) || 'center';

    el.dataset.editVerticalAlign = value;

    setUserStyle(el, 'display', 'flex');

    setUserStyle(el, 'flex-direction', 'column');

    setUserStyle(el, 'justify-content', value === 'start' ? 'flex-start' : (value === 'end' ? 'flex-end' : 'center'));

    setUserStyle(el, 'align-items', 'stretch');

    setUserStyle(el, 'align-content', '');

  }



  function applyDeclaredHorizontalAlignment(el) {

    if (!isTextEditableElement(el)) return;

    const value = el.dataset && el.dataset.editHorizontalAlign;

    if (!['left', 'center', 'right', 'justify'].includes(value)) return;

    // A renderer-provided default must not overwrite a deliberate user

    // alignment that is already stored as an inline style.

    if (el.style.textAlign) return;

    setUserStyle(el, 'text-align', value);

  }






  function scalableTextNodes(el) {

    const nodes = [];

    if (hasDirectText(el)) nodes.push(el);

    Array.from(el.querySelectorAll('*')).forEach((node) => {

      if (hasDirectText(node)) nodes.push(node);

    });

    return nodes;

  }



  function captureInlineTypography(el) {

    const descendants = Array.from(el.querySelectorAll('*'));

    return descendants.reduce((items, node, index) => {

      if (!hasDirectText(node)) return items;

      items.push({

        index: index,

        fontFamily: node.style.fontFamily,

        fontSize: node.style.fontSize,

        lineHeight: node.style.lineHeight,

        letterSpacing: node.style.letterSpacing

      });

      return items;

    }, []);

  }



  function typographySignature(items) {

    return (items || []).map((item) => {

      return [item.index, item.fontFamily, item.fontSize, item.lineHeight, item.letterSpacing].join(':');

    }).join('|');

  }



  function applyInlineTypography(el, items) {

    const descendants = Array.from(el.querySelectorAll('*'));

    (items || []).forEach((item) => {

      const node = descendants[item.index];

      if (!node) return;

      if (Object.prototype.hasOwnProperty.call(item, 'fontFamily')) {

        setUserStyle(node, 'font-family', item.fontFamily || '');

      }

      setUserStyle(node, 'font-size', item.fontSize || '');

      setUserStyle(node, 'line-height', item.lineHeight || '');

      setUserStyle(node, 'letter-spacing', item.letterSpacing || '');

    });

  }



  function serializeInlineTypography(el) {

    return captureInlineTypography(el).filter((item) => {

      return item.fontFamily || item.fontSize || item.lineHeight || item.letterSpacing;

    });

  }



  function getBaseFontSize(el) {

    return parseFloat(getComputedStyle(el).fontSize) || 0;

  }



  function getElementVisualScale(el) {

    if (!el) return 1;

    const rect = el.getBoundingClientRect();

    const viewerScale = getScale() || 1;

    const rawWidth = el.offsetWidth || parseFloat(getComputedStyle(el).width) || 0;

    const rawHeight = el.offsetHeight || parseFloat(getComputedStyle(el).height) || 0;

    const scaleX = rawWidth > 0 ? rect.width / (rawWidth * viewerScale) : NaN;

    const scaleY = rawHeight > 0 ? rect.height / (rawHeight * viewerScale) : NaN;

    const usable = [scaleX, scaleY].filter((value) => Number.isFinite(value) && value > 0);

    if (usable.length === 2) return Math.sqrt(usable[0] * usable[1]);

    return usable[0] || 1;

  }



  function getCurrentFontSize(el) {

    return getBaseFontSize(el) * getElementVisualScale(el);

  }



  function hasOwnUniformFontSize(el) {

    if (!isTextEditableElement(el)) return false;

    const ownSize = getCurrentFontSize(el);

    const textChildren = Array.from(el.children || []).filter((child) => {

      return child.textContent && child.textContent.trim();

    });

    return textChildren.every((child) => {

      return Math.abs((getCurrentFontSize(child) || ownSize) - ownSize) <= 0.5;

    });

  }



  function fontEditableTargets() {

    return selectedTextTargets().filter(hasOwnUniformFontSize);

  }



  function selectedFontSummary() {

    const targets = fontEditableTargets();

    const primary = targets.indexOf(selectedEl) >= 0 ? selectedEl : targets[0];

    const sizes = targets.map((el) => Math.round(getCurrentFontSize(el) * 10) / 10);

    const unique = Array.from(new Set(sizes.map((size) => Math.round(size * 10) / 10)));

    return { targets: targets, primary: primary, sizes: sizes, mixed: unique.length > 1 };

  }



  function styleNumber(el, prop, fallback) {

    const computedValue = parseFloat(getComputedStyle(el)[prop]);

    if (!Number.isNaN(computedValue)) return computedValue;

    const inlineValue = parseFloat(el.style[prop]);

    if (!Number.isNaN(inlineValue)) return inlineValue;

    return fallback || 0;

  }



  function setUserStyle(el, property, value) {

    if (!el || !el.style) return;

    if (value === undefined || value === null || value === '') {

      el.style.removeProperty(property);

      return;

    }

    // User edits are the final authority.  Theme Lab cases legitimately use

    // !important for their initial art direction; a normal inline declaration

    // would appear in DevTools while the computed style stayed unchanged.

    el.style.setProperty(property, String(value), 'important');

  }



  const UNGROUP_GEOMETRY_PROPERTIES = [

    'position', 'left', 'top', 'right', 'bottom', 'inset',

    'width', 'height', 'max-width', 'max-height', 'box-sizing'

  ];



  function captureInlineGeometry(el) {

    if (!el || !el.style) return {};

    return UNGROUP_GEOMETRY_PROPERTIES.reduce((snapshot, property) => {

      snapshot[property] = {

        value: el.style.getPropertyValue(property),

        priority: el.style.getPropertyPriority(property)

      };

      return snapshot;

    }, {});

  }



  function inlineGeometrySignature(snapshot) {

    return UNGROUP_GEOMETRY_PROPERTIES.map((property) => {

      const item = snapshot && snapshot[property] ? snapshot[property] : {};

      return property + ':' + (item.value || '') + ':' + (item.priority || '');

    }).join('|');

  }



  function restoreInlineGeometry(el, snapshot) {

    if (!el || !el.style || !snapshot) return;

    UNGROUP_GEOMETRY_PROPERTIES.forEach((property) => {

      const item = snapshot[property] || {};

      if (item.value) el.style.setProperty(property, item.value, item.priority || '');

      else el.style.removeProperty(property);

    });

  }



  function captureSnapshotVisualGeometry(el) {

    const root = editableRoot(el);

    if (!el || root !== el || !isCompositeRoot(el)) return null;

    const computedStyle = getComputedStyle(el);
    const box = stageBox(el);

    return {

      left: box.left,

      top: box.top,

      width: box.width,

      height: box.height,

      position: computedStyle.position

    };

  }



  function restoreSnapshotVisualGeometry(el, snapshot) {

    if (!el || !snapshot || !isCompositeRoot(el)) return;

    const offsetParent = el.offsetParent && (
      el.offsetParent === stage || stage.contains(el.offsetParent)
    ) ? el.offsetParent : stage;
    const parentBox = stageBox(offsetParent);
    const parentScale = Math.max(getElementVisualScale(offsetParent), 0.0001);
    const borderLeft = Number(offsetParent.clientLeft) || 0;
    const borderTop = Number(offsetParent.clientTop) || 0;
    const left = (snapshot.left - parentBox.left) / parentScale - borderLeft;
    const top = (snapshot.top - parentBox.top) / parentScale - borderTop;

    // Snapshot geometry is the final owner for generated composite roots.
    // Reassert it after inline-style restoration so a blank historical
    // left/top cannot fall back to the wrapper's static position.
    if (snapshot.position && snapshot.position !== 'static') {

      setUserStyle(el, 'position', snapshot.position);

    }

    setUserStyle(el, 'left', Math.round(left * 10) / 10 + 'px');

    setUserStyle(el, 'top', Math.round(top * 10) / 10 + 'px');

    if (Number.isFinite(snapshot.width)) {

      setUserStyle(el, 'width', Math.round(snapshot.width * 10) / 10 + 'px');

    }

    if (Number.isFinite(snapshot.height)) {

      setUserStyle(el, 'height', Math.round(snapshot.height * 10) / 10 + 'px');

    }

  }



  function measureSnapshotState(el) {

    const state = measureElementState(el);
    const snapshotGeometry = captureSnapshotVisualGeometry(el);

    if (snapshotGeometry) state.snapshotGeometry = snapshotGeometry;

    return state;

  }



  function setNaturalTextWrap(el) {

    if (!el || !el.style) return;

    el.dataset.editWrapMode = 'natural';

    // Side-handle resizing changes the text frame, not the typography.  Once

    // the author changes that width, let the browser fill each line normally.

    // Explicit <br> elements remain hard breaks and are intentionally kept.

    setUserStyle(el, 'text-wrap', 'wrap');

    setUserStyle(el, 'white-space', 'normal');

  }



  function horizontalTextAnchorMode(el) {

    const style = getComputedStyle(el);

    const align = String(style.textAlign || 'left').toLowerCase();

    const rtl = String(style.direction || 'ltr').toLowerCase() === 'rtl';

    if (align === 'center') return 'center';

    if (align === 'right' || (align === 'end' && !rtl) || (align === 'start' && rtl)) return 'right';

    return 'left';

  }



  function captureTextHorizontalAnchor(el) {

    const box = stageBox(el);

    const mode = horizontalTextAnchorMode(el);

    return {

      mode: mode,

      x: mode === 'center' ? box.left + box.width / 2 : (mode === 'right' ? box.right : box.left)

    };

  }



  function restoreTextHorizontalAnchor(el, anchor) {

    if (!el || !anchor) return;

    const box = stageBox(el);

    const mode = horizontalTextAnchorMode(el);

    const currentX = mode === 'center' ? box.left + box.width / 2 : (mode === 'right' ? box.right : box.left);

    const delta = anchor.x - currentX;

    if (Math.abs(delta) <= 0.05) return;

    setUserStyle(el, 'left', (Math.round((styleNumber(el, 'left', el.offsetLeft) + delta) * 10) / 10) + 'px');

  }



  function measureElementState(el) {

    const rect = el.getBoundingClientRect();

    const scale = getScale() || 1;

    const typography = captureInlineTypography(el);

    const geometryInline = captureInlineGeometry(el);

    const computedStyle = getComputedStyle(el);

    const verticalInline = {

      top: el.style.top || '',

      height: el.style.height || '',

      fontSize: el.style.fontSize || '',

      lineHeight: el.style.lineHeight || '',

      paddingTop: el.style.paddingTop || '',

      paddingBottom: el.style.paddingBottom || '',

      rowGap: el.style.rowGap || '',

      transform: el.style.transform || '',

      transformOrigin: el.style.transformOrigin || ''

    };

    return {

      left: Math.round(styleNumber(el, 'left', el.offsetLeft) * 10) / 10,

      top: Math.round(styleNumber(el, 'top', el.offsetTop) * 10) / 10,

      width: Math.round(styleNumber(el, 'width', rect.width / scale) * 10) / 10,

      height: Math.round(styleNumber(el, 'height', rect.height / scale) * 10) / 10,

      fontSize: Math.round(getBaseFontSize(el) * 10) / 10,

      fontFamily: el.style.fontFamily || '',

      fontWeight: el.style.fontWeight || computedStyle.fontWeight,

      fontStyle: el.style.fontStyle || computedStyle.fontStyle,

      textDecorationLine: el.style.textDecorationLine || computedStyle.textDecorationLine,

      textAlign: el.style.textAlign || computedStyle.textAlign,

      color: el.style.color || computedStyle.color,

      colorInline: el.style.color || '',

      background: el.style.background || computedStyle.background,

      backgroundInline: el.style.background || '',

      borderColor: el.style.borderColor || computedStyle.borderColor,

      zIndex: el.style.zIndex || computedStyle.zIndex,

      display: el.style.display || computedStyle.display,

      lineHeight: el.style.lineHeight || computedStyle.lineHeight,

      letterSpacing: el.style.letterSpacing || computedStyle.letterSpacing,

      paddingLeft: el.style.paddingLeft || computedStyle.paddingLeft,

      paddingRight: el.style.paddingRight || computedStyle.paddingRight,

      paddingTop: el.style.paddingTop || computedStyle.paddingTop,

      paddingBottom: el.style.paddingBottom || computedStyle.paddingBottom,

      rowGap: el.style.rowGap || computedStyle.rowGap,

      columnGap: el.style.columnGap || computedStyle.columnGap,

      textWrap: el.style.textWrap || computedStyle.textWrap,

      whiteSpace: el.style.whiteSpace || computedStyle.whiteSpace,

      wrapMode: el.dataset && el.dataset.editWrapMode ? el.dataset.editWrapMode : '',

      alignContent: el.style.alignContent || computedStyle.alignContent,

      flexDirection: el.style.flexDirection || computedStyle.flexDirection,

      justifyContent: el.style.justifyContent || computedStyle.justifyContent,

      alignItems: el.style.alignItems || computedStyle.alignItems,

      verticalAlign: el.dataset && el.dataset.editVerticalAlign ? el.dataset.editVerticalAlign : '',

      frameWidthMode: el.dataset && el.dataset.editFrameWidth ? el.dataset.editFrameWidth : '',

      frameHeightMode: el.dataset && el.dataset.editFrameHeight ? el.dataset.editFrameHeight : '',

      compositeGroupState: el.dataset && el.dataset.editGroupState ? el.dataset.editGroupState : '',

      editPosition: el.dataset && el.dataset.editPosition ? el.dataset.editPosition : '',

      geometryInline: geometryInline,

      geometryInlineSignature: inlineGeometrySignature(geometryInline),

      groupId: groupId(el),

      transform: el.style.transform || '',

      transformOrigin: el.style.transformOrigin || '',

      verticalInline: verticalInline,

      verticalInlineSignature: Object.keys(verticalInline).map((key) => (

        key + ':' + verticalInline[key]

      )).join('|'),

      typography: typography,

      typographySignature: typographySignature(typography)

    };

  }



  function snapshotElementState(el) {

    const state = measureElementState(el);

    state.html = el.innerHTML;

    return state;

  }



  function ensureOriginalGeometry(el) {

    const state = measureElementState(el);

    if (!originalPositions.has(el)) {

      originalPositions.set(el, { left: state.left, top: state.top });

    }

    if (!originalSizes.has(el)) {

      originalSizes.set(el, {

        width: state.width,

        height: state.height,

        fontSize: state.fontSize

      });

    }

    if (!originalStyles.has(el)) {

      originalStyles.set(el, {

        fontFamily: state.fontFamily,

        fontWeight: state.fontWeight,

        fontStyle: state.fontStyle,

        textDecorationLine: state.textDecorationLine,

        textAlign: state.textAlign,

        color: state.color,

        background: state.background,

        borderColor: state.borderColor,

        zIndex: state.zIndex,

        display: state.display,

        lineHeight: state.lineHeight,

        letterSpacing: state.letterSpacing,

        paddingLeft: state.paddingLeft,

        paddingRight: state.paddingRight,

        textWrap: state.textWrap,

        whiteSpace: state.whiteSpace,

        columnGap: state.columnGap,

        wrapMode: state.wrapMode,

        alignContent: state.alignContent,

        flexDirection: state.flexDirection,

        justifyContent: state.justifyContent,

        alignItems: state.alignItems,

        verticalAlign: state.verticalAlign,

        frameWidthMode: state.frameWidthMode,

        frameHeightMode: state.frameHeightMode,

        compositeGroupState: state.compositeGroupState,

        groupId: state.groupId,

        transform: state.transform,

        transformOrigin: state.transformOrigin,

        typographySignature: state.typographySignature

      });

    }

    return state;

  }



  function stateChanged(before, after, keys) {

    return keys.some((key) => {

      const a = before ? before[key] : undefined;

      const b = after ? after[key] : undefined;

      if (typeof a === 'number' || typeof b === 'number') return Math.abs((a || 0) - (b || 0)) > 0.5;

      return a !== b;

    });

  }



  function fitTextElementToContent(el) {

    if (!el || !el.dataset || el.dataset.editFit !== 'text') return;

    const keepManualHeight = el.dataset.editFrameHeight === 'manual';

    const manualHeight = keepManualHeight

      ? Math.max(MIN_SIZE, parseFloat(el.style.height) || el.getBoundingClientRect().height / Math.max(getScale(), 0.0001))

      : null;

    if (el.dataset.editFrameWidth === 'manual') {

      setNaturalTextWrap(el);

      const manualWidth = Math.max(MIN_SIZE, parseFloat(el.style.width) || el.getBoundingClientRect().width / Math.max(getScale(), 0.0001));

      setUserStyle(el, 'width', Math.round(manualWidth * 10) / 10 + 'px');

      setUserStyle(el, 'max-width', 'none');

      setUserStyle(el, 'height', 'auto');

      const range = document.createRange();

      range.selectNodeContents(el);

      const rect = range.getBoundingClientRect();

      const scale = getScale() || 1;

      const cs = getComputedStyle(el);

      const paddingY = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);

      const height = Math.max(MIN_SIZE, Math.ceil(rect.height / scale + paddingY));

      setUserStyle(el, 'height', (keepManualHeight ? manualHeight : height) + 'px');

      if (selectedEls.indexOf(el) >= 0 || selectedEl === el) scheduleSelectionRefresh();

      return;

    }

    const sourceProbe = document.createElement('div');

    sourceProbe.style.cssText = el.dataset.layoutSourceStyle || '';

    let maxWidth = el.dataset.editFitMaxWidth || sourceProbe.style.maxWidth || el.style.maxWidth;

    if ((!maxWidth || maxWidth === 'none') && el.dataset.editUserSized === '1') maxWidth = el.style.width;

    if (!maxWidth || maxWidth === 'none') maxWidth = '100%';

    if (!el.dataset.editFitMaxWidth) el.dataset.editFitMaxWidth = maxWidth;

    setUserStyle(el, 'width', 'max-content');

    setUserStyle(el, 'height', 'auto');

    setUserStyle(el, 'max-width', maxWidth);

    setUserStyle(el, 'max-height', 'none');

    const range = document.createRange();

    range.selectNodeContents(el);

    const rect = range.getBoundingClientRect();

    const stageRect = stage.getBoundingClientRect();

    const scale = stage.offsetWidth ? stageRect.width / stage.offsetWidth : 1;

    const width = Math.max(2, Math.ceil(rect.width / Math.max(scale, 0.0001) + 2));

    const height = Math.max(2, Math.ceil(rect.height / Math.max(scale, 0.0001)));

    setUserStyle(el, 'width', width + 'px');

    setUserStyle(el, 'height', (keepManualHeight ? manualHeight : height) + 'px');

    setUserStyle(el, 'max-width', 'none');

    if (selectedEls.indexOf(el) >= 0 || selectedEl === el) repositionHandles();

  }



  function commandKeys(type, command) {

    if (type === 'move') return ['left', 'top', 'zIndex', 'transform', 'transformOrigin'];

    if (type === 'text') return ['left', 'top', 'width', 'height', 'frameWidthMode', 'frameHeightMode', 'textWrap', 'whiteSpace', 'wrapMode', 'html'];

    if (type === 'style') return ['width', 'height', 'fontSize', 'fontFamily', 'fontWeight', 'fontStyle', 'textDecorationLine', 'textAlign', 'color', 'background', 'borderColor', 'zIndex', 'display', 'lineHeight', 'letterSpacing', 'paddingLeft', 'paddingRight', 'paddingTop', 'paddingBottom', 'rowGap', 'columnGap', 'textWrap', 'whiteSpace', 'wrapMode', 'alignContent', 'flexDirection', 'justifyContent', 'alignItems', 'verticalAlign', 'frameWidthMode', 'frameHeightMode', 'compositeGroupState', 'groupId', 'transform', 'transformOrigin', 'typographySignature'];

    if (type === 'snapshot') return ['left', 'top', 'width', 'height', 'fontSize', 'fontFamily', 'fontWeight', 'fontStyle', 'textDecorationLine', 'textAlign', 'color', 'background', 'borderColor', 'zIndex', 'display', 'lineHeight', 'letterSpacing', 'paddingLeft', 'paddingRight', 'paddingTop', 'paddingBottom', 'rowGap', 'columnGap', 'textWrap', 'whiteSpace', 'wrapMode', 'alignContent', 'flexDirection', 'justifyContent', 'alignItems', 'verticalAlign', 'frameWidthMode', 'frameHeightMode', 'compositeGroupState', 'editPosition', 'groupId', 'transform', 'transformOrigin', 'geometryInlineSignature', 'typographySignature', 'html'];

    if (type === 'resize' && command && command.axis === 'vertical') {

      const keys = ['top', 'fontSize', 'lineHeight', 'paddingTop', 'paddingBottom', 'rowGap', 'frameHeightMode', 'transform', 'transformOrigin', 'verticalInlineSignature', 'typographySignature'];

      if (command.verticalOwnsHeight) keys.splice(1, 0, 'height');

      return keys;

    }

    return ['left', 'top', 'width', 'height', 'fontSize', 'paddingLeft', 'paddingRight', 'paddingTop', 'paddingBottom', 'rowGap', 'columnGap', 'frameWidthMode', 'frameHeightMode', 'textWrap', 'whiteSpace', 'wrapMode', 'transform', 'transformOrigin', 'typographySignature'];

  }



  function commandLabel(command) {

    if (command.type === 'deck-font') return command.label || M.defaultFontChange;

    if (command.type === 'slide-background') return command.label || M.slideBackgroundChange;

    if (command.type === 'slide-mask') return command.label || M.slideMaskChange;

    if (command.type === 'slide-order') return command.label || M.slideOrderChange;

    if (command.type === 'batch') return command.label || M.batchChange;

    const prefix = command.type === 'move' ? M.moveChange : (command.type === 'text' ? M.textChange : (command.type === 'style' ? M.styleChange : M.resizeChange));

    const el = command.el && document.contains(command.el) ? command.el : elementByKey(command.key);

    return prefix + ' ' + (el ? elementLabel(el) : command.key);

  }



  function commandChanged(command) {

    if (command.type === 'deck-font' || command.type === 'slide-background' || command.type === 'slide-mask') {

      return appearanceStateChanged(command.before, command.after);

    }

    if (command.type === 'slide-order') {

      return (command.before || []).join('|') !== (command.after || []).join('|');

    }

    if (command.type === 'batch') {

      return (command.items || []).some((item) => {

        if (item.type === 'slide-order') {

          return (item.before || []).join('|') !== (item.after || []).join('|');

        }

        if (item.type === 'deck-font' || item.type === 'slide-background' || item.type === 'slide-mask') {

          return appearanceStateChanged(item.before, item.after);

        }

        return stateChanged(item.before, item.after, commandKeys(item.type || command.itemType || 'style', item));

      });

    }

    return stateChanged(command.before, command.after, commandKeys(command.type, command));

  }



  function pushCommand(command) {

    const changed = !!(command && commandChanged(command));

    if (!changed) return;

    if (command.el) command.key = command.key || elementKey(command.el);

    undoStack.push(command);

    if (undoStack.length > UNDO_LIMIT) undoStack.shift();

    redoStack.length = 0;

    appendOperationLog('commit', command);

    updateActionStates();

  }



  function applyCommandState(command, state) {

    if (command.type === 'deck-font') {

      applyDeckFontState(state || {});

      lastPaletteSignature = null;

      updateAppearanceControls();

      updateFontControls();

      scheduleThumbnailRefresh();

      scheduleDraftSave();

      return document.documentElement;

    }

    if (command.type === 'slide-background') {

      const slide = command.slideId ? document.getElementById(command.slideId) : null;

      if (!slide) return null;

      const value = state && typeof state.backgroundColor === 'string' ? state.backgroundColor : '';

      if (value) slide.style.backgroundColor = value;

      else slide.style.removeProperty('background-color');

      lastPaletteSignature = null;

      updateAppearanceControls();

      refreshColorSwatches();

      scheduleThumbnailRefresh();

      scheduleDraftSave();

      return slide;

    }

    if (command.type === 'slide-mask') {

      const slide = command.slideId ? document.getElementById(command.slideId) : null;

      if (!slide) return null;

      applySlideMaskState(slide, state || {});

      updateAppearanceControls();

      scheduleThumbnailRefresh();

      scheduleDraftSave();

      return slide;

    }

    if (command.type === 'slide-order') {

      if (window.SlidePlayer && typeof window.SlidePlayer.reorderSlides === 'function' && Array.isArray(state)) {

        window.SlidePlayer.reorderSlides(state, { notify: false });

        updateSlideOrderDirty();

        scheduleDraftSave();

      }

      return null;

    }

    if (command.type === 'batch') {
      (command.items || []).forEach((item) => {

        applyCommandState(item, state === 'after' ? item.after : item.before);

      });

      reconcileSelectedGroup();

      updateActionStates();

      return null;

    }

    const el = command.el && document.contains(command.el) ? command.el : elementByKey(command.key);

    if (!el || !state) return null;

    if (command.type === 'move') {

      // Move history owns position only. Replaying the full measured state

      // converted intrinsic text geometry such as width:max-content and

      // height:auto into fixed pixel frames, which could re-wrap text after

      // an otherwise harmless move + undo. Visual group moves additionally

      // use transform, and module moves may promote z-index, so preserve only

      // those positional fields here.

      if (state.left !== undefined) setUserStyle(el, 'left', state.left + 'px');

      if (state.top !== undefined) setUserStyle(el, 'top', state.top + 'px');

      if (state.zIndex !== undefined) setUserStyle(el, 'z-index', state.zIndex === 'auto' ? '' : state.zIndex);

      if (state.transform !== undefined) setUserStyle(el, 'transform', state.transform);

      if (state.transformOrigin !== undefined) setUserStyle(el, 'transform-origin', state.transformOrigin);

      if (selectedEl) repositionHandles();

      updateSelectionBadge();

      recordChange(el);

      scheduleDraftSave();

      return el;

    }

    if (command.type === 'resize' && command.axis === 'vertical') {

      // A vertical resize owns only vertical geometry. Replaying a complete
      // measured state here would turn intrinsic text widths (auto/max-content)
      // into fixed pixel frames after Undo/Redo. That hidden horizontal edit can
      // force a title to wrap or make adjacent labels appear to collide on the
      // next resize, even though the user only dragged a top/bottom handle.
      const changed = (key) => stateChanged(command.before, command.after, [key]);

      const hasInlineState = !!(

        state.verticalInline

        && command.before.verticalInline

        && command.after.verticalInline

      );

      const inlineChanged = (key, measuredKey) => hasInlineState

        ? command.before.verticalInline[key] !== command.after.verticalInline[key]

        : changed(measuredKey || key);

      const inlineValue = (key, fallback) => hasInlineState

        ? state.verticalInline[key]

        : fallback;

      if (inlineChanged('top') && state.top !== undefined) {

        setUserStyle(el, 'top', inlineValue('top', state.top + 'px'));

      }

      if (command.verticalOwnsHeight && inlineChanged('height') && state.height !== undefined) {

        setUserStyle(el, 'height', inlineValue('height', state.height + 'px'));

      }

      if (inlineChanged('fontSize') && state.fontSize !== undefined) {

        setUserStyle(el, 'font-size', inlineValue('fontSize', state.fontSize + 'px'));

      }

      if (inlineChanged('lineHeight') && state.lineHeight !== undefined) {

        setUserStyle(el, 'line-height', inlineValue('lineHeight', state.lineHeight));

      }

      if (inlineChanged('paddingTop') && state.paddingTop !== undefined) {

        setUserStyle(el, 'padding-top', inlineValue('paddingTop', state.paddingTop));

      }

      if (inlineChanged('paddingBottom') && state.paddingBottom !== undefined) {

        setUserStyle(el, 'padding-bottom', inlineValue('paddingBottom', state.paddingBottom));

      }

      if (inlineChanged('rowGap') && state.rowGap !== undefined) {

        const rowGap = inlineValue('rowGap', state.rowGap === 'normal' ? '' : state.rowGap);

        setUserStyle(el, 'row-gap', rowGap);

      }

      if ((inlineChanged('transform') || inlineChanged('transformOrigin')) && state.transform !== undefined) {

        setUserStyle(el, 'transform', inlineValue('transform', state.transform));

      }

      if ((inlineChanged('transform') || inlineChanged('transformOrigin')) && state.transformOrigin !== undefined) {

        setUserStyle(el, 'transform-origin', inlineValue('transformOrigin', state.transformOrigin));

      }

      if (changed('typographySignature') && state.typography !== undefined) applyInlineTypography(el, state.typography);

      if (changed('frameHeightMode') && state.frameHeightMode !== undefined) {

        if (state.frameHeightMode) el.dataset.editFrameHeight = state.frameHeightMode;

        else delete el.dataset.editFrameHeight;

      }

      if (selectedEl) repositionHandles();

      updateSelectionBadge();

      recordChange(el);

      scheduleDraftSave();

      return el;

    }

    if (state.left !== undefined) setUserStyle(el, 'left', state.left + 'px');

    if (state.top !== undefined) setUserStyle(el, 'top', state.top + 'px');

    if (state.width !== undefined) setUserStyle(el, 'width', state.width + 'px');

    if (state.height !== undefined) setUserStyle(el, 'height', state.height + 'px');

    if (state.fontSize !== undefined) setUserStyle(el, 'font-size', state.fontSize + 'px');

    if (state.fontFamily !== undefined) setUserStyle(el, 'font-family', state.fontFamily);

    if (state.fontWeight !== undefined) setUserStyle(el, 'font-weight', state.fontWeight);

    if (state.fontStyle !== undefined) setUserStyle(el, 'font-style', state.fontStyle);

    if (state.textDecorationLine !== undefined) setUserStyle(el, 'text-decoration-line', state.textDecorationLine);

    if (state.textAlign !== undefined) setUserStyle(el, 'text-align', state.textAlign);

    if (state.color !== undefined) {

      setUserStyle(el, 'color', state.colorInline !== undefined ? state.colorInline : state.color);

    }

    if (state.background !== undefined) {

      setUserStyle(el, 'background', state.backgroundInline !== undefined ? state.backgroundInline : state.background);

    }

    if (state.borderColor !== undefined) setUserStyle(el, 'border-color', state.borderColor);

    if (state.zIndex !== undefined) setUserStyle(el, 'z-index', state.zIndex === 'auto' ? '' : state.zIndex);

    if (state.display !== undefined) setUserStyle(el, 'display', state.display);

    if (state.lineHeight !== undefined) setUserStyle(el, 'line-height', state.lineHeight);

    if (state.letterSpacing !== undefined) setUserStyle(el, 'letter-spacing', state.letterSpacing);

    if (state.paddingLeft !== undefined) setUserStyle(el, 'padding-left', state.paddingLeft);

    if (state.paddingRight !== undefined) setUserStyle(el, 'padding-right', state.paddingRight);

    if (state.paddingTop !== undefined) setUserStyle(el, 'padding-top', state.paddingTop);

    if (state.paddingBottom !== undefined) setUserStyle(el, 'padding-bottom', state.paddingBottom);

    if (state.rowGap !== undefined) setUserStyle(el, 'row-gap', state.rowGap === 'normal' ? '' : state.rowGap);

    if (state.columnGap !== undefined) setUserStyle(el, 'column-gap', state.columnGap === 'normal' ? '' : state.columnGap);

    if (state.textWrap !== undefined) setUserStyle(el, 'text-wrap', state.textWrap);

    if (state.whiteSpace !== undefined) setUserStyle(el, 'white-space', state.whiteSpace);

    if (state.wrapMode !== undefined) {

      if (state.wrapMode) el.dataset.editWrapMode = state.wrapMode;

      else delete el.dataset.editWrapMode;

    }

    if (state.alignContent !== undefined) setUserStyle(el, 'align-content', state.alignContent === 'normal' ? '' : state.alignContent);

    if (state.flexDirection !== undefined) setUserStyle(el, 'flex-direction', state.flexDirection);

    if (state.justifyContent !== undefined) setUserStyle(el, 'justify-content', state.justifyContent);

    if (state.alignItems !== undefined) setUserStyle(el, 'align-items', state.alignItems);

    if (state.verticalAlign !== undefined) {

      if (state.verticalAlign) el.dataset.editVerticalAlign = state.verticalAlign;

      else delete el.dataset.editVerticalAlign;

    }

    if (state.frameWidthMode !== undefined) {

      if (state.frameWidthMode) el.dataset.editFrameWidth = state.frameWidthMode;

      else delete el.dataset.editFrameWidth;

    }

    if (state.frameHeightMode !== undefined) {

      if (state.frameHeightMode) el.dataset.editFrameHeight = state.frameHeightMode;

      else delete el.dataset.editFrameHeight;

    }

    if (state.compositeGroupState !== undefined) {

      if (state.compositeGroupState) el.dataset.editGroupState = state.compositeGroupState;

      else delete el.dataset.editGroupState;

    }

    if (command.type === 'snapshot' && state.editPosition !== undefined) {

      if (state.editPosition) el.dataset.editPosition = state.editPosition;

      else if (el.dataset) delete el.dataset.editPosition;

    }

    if (state.groupId !== undefined) {

      if (state.groupId) el.dataset.editGroup = state.groupId;

      else delete el.dataset.editGroup;

    }

    if (state.transform !== undefined) setUserStyle(el, 'transform', state.transform);

    if (state.transformOrigin !== undefined) setUserStyle(el, 'transform-origin', state.transformOrigin);

    if (state.typography !== undefined) applyInlineTypography(el, state.typography);

    if (state.html !== undefined) {

      el.innerHTML = state.html;

      // Text-only edits need a fresh text boundary.  Snapshot/draft commands

      // already carry authoritative geometry; measuring them again after a

      // transform would multiply the scale into width/height a second time.

      if (state.width === undefined || state.height === undefined) fitTextElementToContent(el);

    }

    if (command.type === 'snapshot' && state.geometryInline) {

      restoreInlineGeometry(el, state.geometryInline);

      // A materialized generated member may have received an important
      // left/top while it was ungrouped.  In a few browser/layout paths the
      // normal restore removes that promotion but fails to put back an
      // original inline side, leaving an absolute member at (0, 0).  Restore
      // the exact source value when it is known; numeric state is the safe
      // fallback for legacy snapshots that did not record the inline value.
      if (getComputedStyle(el).position === 'absolute') {

        ['left', 'top'].forEach((property) => {

          if (el.style.getPropertyValue(property)) return;

          const inlineState = state.geometryInline[property] || {};

          if (inlineState.value) {

            el.style.setProperty(property, inlineState.value, inlineState.priority || '');

            return;

          }

          const numeric = state[property];

          if (Number.isFinite(numeric)) setUserStyle(el, property, numeric + 'px');

        });

      }

    }

    if (command.type === 'snapshot' && state.snapshotGeometry) {

      restoreSnapshotVisualGeometry(el, state.snapshotGeometry);

    }

    // Undo/redo and restored drafts must never leave the toolbar claiming an

    // object is selected while its frame and handles stay hidden.  Rebuild the

    // active selection geometry after every applied state, even when the

    // command target was resolved from a serialized key instead of the current

    // selectedEls array.

    if (selectedEl) repositionHandles();

    updateSelectionBadge();

    recordChange(el);

    scheduleDraftSave();

    return el;

  }



  function undo() {

    commitPendingChanges();

    clearGroupEditScopes();

    if (!undoStack.length) {

      showTransientReadout(M.noUndo);

      return;

    }

    const command = undoStack.pop();

    applyCommandState(command, command.type === 'batch' ? 'before' : command.before);

    restoreSelectionSnapshot(command.selectionBefore);

    if (command.type === 'batch' && command.label === M.draftRestoreChange) {

      if (draftTimer) clearTimeout(draftTimer);

      draftTimer = null;

      clearDraft();

      (command.items || []).forEach((item) => {

        const target = item.el && document.contains(item.el) ? item.el : elementByKey(item.key);

        if (!target) return;

        changedElements.delete(target);

        textDirty.delete(target);

      });

    }

    redoStack.push(command);

    appendOperationLog('undo', command);

    showTransientReadout(t(M.undoDone, { label: commandLabel(command) }));

    updateActionStates();

    scheduleSelectionRefresh();

  }



  function redo() {

    if (!redoStack.length) {

      showTransientReadout(M.noRedo);

      return;

    }

    commitPendingChanges();

    clearGroupEditScopes();

    const command = redoStack.pop();

    applyCommandState(command, command.type === 'batch' ? 'after' : command.after);

    restoreSelectionSnapshot(command.selectionAfter);

    undoStack.push(command);

    appendOperationLog('redo', command);

    showTransientReadout(t(M.redoDone, { label: commandLabel(command) }));

    updateActionStates();

    scheduleSelectionRefresh();

  }



  function currentToolMeta() {

    if (!currentTool) {

      return {

        key: 'idle',

        label: M.idleMode,

        hint: M.idleHint,

        color: '#9DB2C6',

        soft: 'rgba(157,178,198,.16)',

        line: 'rgba(157,178,198,.52)',

        handle: '#9DB2C6'

      };

    }

    if (currentTool === 'text') {

      return {

        key: 'text',

        label: M.textMode,

        hint: M.textHint,

        color: '#6EE7B7',

        soft: 'rgba(110,231,183,.18)',

        line: 'rgba(110,231,183,.72)',

        handle: '#6EE7B7'

      };

    }

    if (currentTool === 'insert') {

      return {

        key: 'insert',

        label: M.insert,

        hint: M.insertDragHint,

        color: '#3FD0E8',

        soft: 'rgba(63,208,232,.18)',

        line: 'rgba(63,208,232,.72)',

        handle: '#3FD0E8'

      };

    }

    if (currentTool === 'resize') {

      return {

        key: 'resize',

        label: M.resizeMode,

        hint: M.resizeHint,

        color: '#F6C35B',

        soft: 'rgba(246,195,91,.18)',

        line: 'rgba(246,195,91,.78)',

        handle: '#F6C35B'

      };

    }

    return {

      key: 'move',

      label: M.moveMode,

      hint: M.moveHint,

      color: '#3FD0E8',

      soft: 'rgba(63,208,232,.18)',

      line: 'rgba(63,208,232,.72)',

      handle: '#3FD0E8'

    };

  }



  function placeCaretAtEnd(el) {

    if (!window.getSelection || !document.createRange) return;

    const range = document.createRange();

    range.selectNodeContents(el);

    range.collapse(false);

    const sel = window.getSelection();

    sel.removeAllRanges();

    sel.addRange(range);

  }



  function showHandles() {

    if (!editMode || !selectedEl || textEditingEl) {

      hideHandles();

      return;

    }

    const meta = currentTool === 'resize' ? currentToolMeta() : {

      handle: '#F6C35B',

      soft: 'rgba(246,195,91,.18)'

    };

    HANDLE_POSITIONS.forEach((pos) => {

      handles[pos].style.background = meta.handle;

      handles[pos].style.boxShadow = '0 0 0 3px ' + meta.soft;

      handles[pos].style.display = 'block';

    });

  }



  function hideResizeHandles() {

    HANDLE_POSITIONS.forEach((pos) => {

      handles[pos].style.display = 'none';

    });

  }



  function hideSelectionMemberFrames() {

    selectionMemberFrames.forEach((frame) => {

      frame.style.display = 'none';

    });

  }



  function hideHardBreakMarkers() {

    hardBreakMarkers.forEach((marker) => marker.remove());

    hardBreakMarkers = [];

  }



  function syncHardBreakMarkers() {

    hideHardBreakMarkers();

    if (!editMode || !selectedEl) return;

    const targets = selectedTextTargets();

    if (!targets.length) return;

    const meta = currentToolMeta();

    targets.forEach((target) => {

      target.querySelectorAll('br').forEach((hardBreak) => {

        const rect = hardBreak.getBoundingClientRect();

        if (!rect || (!rect.width && !rect.height)) return;

        const marker = document.createElement('span');

        marker.className = 'edit-hard-break-marker';

        marker.textContent = '\u21b5';

        marker.setAttribute('aria-hidden', 'true');

        marker.style.cssText =

          'position:fixed;pointer-events:none;z-index:103;display:block;' +

          'left:' + Math.round(rect.left + 3) + 'px;' +

          'top:' + Math.round(rect.top + rect.height * 0.68 - 7) + 'px;' +

          'font:700 12px/1 var(--font-mono,monospace);color:' + meta.color + ';opacity:.34;' +

          'text-shadow:0 1px 2px rgba(255,255,255,.35);user-select:none;';

        document.body.appendChild(marker);

        hardBreakMarkers.push(marker);

      });

    });

  }



  function hideHandles() {

    hideResizeHandles();

    if (selectionFrame) selectionFrame.style.display = 'none';

    hideSelectionMemberFrames();

    hideHardBreakMarkers();

    hideGuides();

  }



  function syncSelectionMemberFrames(rects, color) {

    const count = rects.length;

    while (selectionMemberFrames.length < count) {

      const frame = document.createElement('div');

      frame.className = 'edit-selection-member-frame';

      frame.dataset.editorChrome = 'true';

      frame.setAttribute('aria-hidden', 'true');

      frame.style.cssText =

        'position:fixed;display:none;pointer-events:none;box-sizing:border-box;border:1px dashed #3FD0E8;' +

        'z-index:100;background:transparent;opacity:.98;border-radius:2px;' +

        'box-shadow:0 0 0 1px rgba(255,255,255,.78),0 0 0 2px rgba(11,18,32,.36);';

      document.body.appendChild(frame);

      selectionMemberFrames.push(frame);

    }

    selectionMemberFrames.forEach((frame, index) => {

      const rect = rects[index];

      if (!rect) {

        frame.style.display = 'none';

        return;

      }

      frame.style.left = rect.left + 'px';

      frame.style.top = rect.top + 'px';

      frame.style.width = rect.width + 'px';

      frame.style.height = rect.height + 'px';

      // Theme cases may use broad !important rules.  Selection chrome must

      // remain visible and interactive-state-only regardless of slide CSS.

      frame.style.setProperty('border', '1px dashed ' + color, 'important');

      frame.style.setProperty('pointer-events', 'none', 'important');

      frame.style.setProperty('box-shadow', '0 0 0 1px rgba(255,255,255,.78),0 0 0 2px rgba(11,18,32,.36)', 'important');

      frame.style.setProperty('opacity', '.98', 'important');

      frame.style.setProperty('display', 'block', 'important');

    });

  }



  function visualSelectionRect(el) {

    const elementRect = el.getBoundingClientRect();

    const generatedRoot = editableRoot(el);

    // Semantic modules own a real visual frame. Never collapse a card's

    // selection bounds to the union of its internal text layers.

    if (el.dataset && el.dataset.editStructure === 'module') return elementRect;

    // A composite can remain in the DOM with edit-group-state="ungrouped"
    // after an explicit restore.  It must still report the visible union when
    // a history snapshot or a pending interaction temporarily targets the
    // wrapper; otherwise the frame collapses to the stale wrapper width while
    // its child modules remain visible outside it.
    if (el === generatedRoot && isCompositeRoot(generatedRoot)
      && generatedRoot.dataset.editStructure !== 'module') {

      const memberRects = generatedGroupMembers(generatedRoot).map(visualSelectionRect);

      if (memberRects.length) {

        const left = Math.min.apply(null, memberRects.map((rect) => rect.left));

        const top = Math.min.apply(null, memberRects.map((rect) => rect.top));

        const right = Math.max.apply(null, memberRects.map((rect) => rect.right));

        const bottom = Math.max.apply(null, memberRects.map((rect) => rect.bottom));

        return { left: left, top: top, right: right, bottom: bottom, width: right - left, height: bottom - top };

      }

    }

    const editLayer = el.dataset ? el.dataset.editLayer : '';

    const usesTightTextBounds = !(el.dataset && (el.dataset.editFrameWidth === 'manual' || el.dataset.editFrameHeight === 'manual')) && (!!(el.dataset && el.dataset.editFit === 'text')

      || editLayer === 'text'

      || editLayer === 'metric');

    if (!usesTightTextBounds || !(el.textContent || '').trim()) return elementRect;

    const style = getComputedStyle(el);

    const borderWidth = ['borderLeftWidth', 'borderRightWidth', 'borderTopWidth', 'borderBottomWidth']

      .reduce((sum, key) => sum + (parseFloat(style[key]) || 0), 0);

    const background = String(style.backgroundColor || '');

    const decorated = borderWidth > 0.5

      || (style.backgroundImage && style.backgroundImage !== 'none')

      || (background && background !== 'transparent' && !/rgba?\([^)]*,\s*0(?:\.0+)?\s*\)$/.test(background));

    if (decorated) return elementRect;

    const range = document.createRange();

    range.selectNodeContents(el);

    const textRect = range.getBoundingClientRect();

    return textRect.width > 0.5 && textRect.height > 0.5 ? textRect : elementRect;

  }



  function currentSelectionMemberRects(targets) {

    const visibleTargets = (targets || []).filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!visibleTargets.length) return [];



    // A selected group must read as one object.  Its members become visible

    // again only after drilling in or ungrouping into a normal multi-selection.

    if (selectionPresentationMode(visibleTargets) === 'group') return [];



    if (visibleTargets.length > 1) return visibleTargets.map(visualSelectionRect);



    return [];

  }



  function selectionPresentationMode(targets) {

    const visibleTargets = (targets || []).filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!visibleTargets.length) return 'single';

    const primary = editableRoot(selectedEl) || editableRoot(visibleTargets[0]);

    const generatedGroupSelected = visibleTargets.length === 1

      && selectedEl === primary

      && isGeneratedGroup(primary);

    if (selectedGroupId || generatedGroupSelected) return 'group';

    if (visibleTargets.length > 1) return 'multi';

    return 'single';

  }



  function repositionHandles() {

    if (!selectedEl) {

      hideHandles();

      return;

    }

    if (textEditingEl) {

      const rect = visualSelectionRect(textEditingEl);

      const meta = currentToolMeta();

      hideResizeHandles();

      hideSelectionMemberFrames();

      if (selectionFrame) {

        selectionFrame.style.left = rect.left + 'px';

        selectionFrame.style.top = rect.top + 'px';

        selectionFrame.style.width = rect.width + 'px';

        selectionFrame.style.height = rect.height + 'px';

        selectionFrame.style.borderColor = meta.color;

        selectionFrame.style.borderStyle = 'solid';

        selectionFrame.style.borderWidth = '2px';

        selectionFrame.dataset.selectionMode = 'text-edit';

        selectionFrame.style.display = 'block';

      }

      updateSelectionBadge();

      syncHardBreakMarkers();

      updateTextEditAlignmentGuides(textEditingEl);

      return;

    }

    const targets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!targets.length) {

      hideHandles();

      return;

    }

    const rects = targets.map(visualSelectionRect);

    const meta = currentToolMeta();

    const presentationMode = selectionPresentationMode(targets);

    const memberRects = currentSelectionMemberRects(targets);

    syncSelectionMemberFrames(memberRects, meta.color);

    const left = Math.min.apply(null, rects.map((rect) => rect.left));

    const top = Math.min.apply(null, rects.map((rect) => rect.top));

    const right = Math.max.apply(null, rects.map((rect) => rect.right));

    const bottom = Math.max.apply(null, rects.map((rect) => rect.bottom));

    const rect = { left: left, top: top, right: right, bottom: bottom, width: right - left, height: bottom - top };

    if (selectionFrame) {

      selectionFrame.style.left = rect.left + 'px';

      selectionFrame.style.top = rect.top + 'px';

      selectionFrame.style.width = rect.width + 'px';

      selectionFrame.style.height = rect.height + 'px';

      selectionFrame.style.borderColor = meta.color;

      selectionFrame.style.borderStyle = presentationMode === 'multi' ? 'dashed' : 'solid';

      selectionFrame.style.borderWidth = presentationMode === 'group' ? '3px' : '2px';

      selectionFrame.dataset.selectionMode = presentationMode;

      selectionFrame.dataset.memberFrameCount = String(memberRects.length);

      selectionFrame.style.display = 'block';

    }

    const half = HANDLE_SIZE / 2;

    const points = {

      nw: [rect.left, rect.top],

      n: [rect.left + rect.width / 2, rect.top],

      ne: [rect.right, rect.top],

      e: [rect.right, rect.top + rect.height / 2],

      se: [rect.right, rect.bottom],

      s: [rect.left + rect.width / 2, rect.bottom],

      sw: [rect.left, rect.bottom],

      w: [rect.left, rect.top + rect.height / 2]

    };

    HANDLE_POSITIONS.forEach((pos) => {

      const point = points[pos];

      handles[pos].style.left = (point[0] - half) + 'px';

      handles[pos].style.top = (point[1] - half) + 'px';

    });

    showHandles();

    updateSelectionBadge();

    syncHardBreakMarkers();

  }



  function applyEditableState() {

    const active = document.querySelector('.slide.active');

    if (!active) return;

    const meta = currentToolMeta();

    const activeSelection = activeSelectedEls();

    const hasMultipleSelection = selectionPresentationMode(activeSelection) === 'multi';

    Array.from(stage.querySelectorAll('.slide')).forEach((slide) => {

      editableElements(slide).forEach((el) => {

        if (isTextEditableElement(el) && getComputedStyle(el).display !== 'none') {

          applyDeclaredVerticalAlignment(el);

          applyDeclaredHorizontalAlignment(el);

        }

        const isActive = slide === active;

        const isSelected = isActive && activeSelection.indexOf(el) >= 0;

        if (editMode && isActive) {

          // Only active multi-selection members receive an element outline.

          // Unselected roots used to expose renderer/container geometry as

          // dashed boxes, which is generation-time information rather than

          // author-facing editing chrome.  Text editing also suppresses the

          // browser's native focus ring because the editor owns the selection

          // frame and resize handles.

          if (textEditingEl === el) {

            el.style.setProperty('outline', 'none', 'important');

            el.style.removeProperty('outline-offset');

          } else if (isSelected && hasMultipleSelection) {

            el.style.setProperty('outline', '2px solid ' + meta.color, 'important');

            el.style.setProperty('outline-offset', '-2px', 'important');

          } else {

            el.style.removeProperty('outline');

            el.style.removeProperty('outline-offset');

          }

          el.style.boxShadow = '';

          el.style.cursor = textEditingEl === el ? 'text' : (currentTool === 'move' ? 'move' : (currentTool === 'text' ? 'text' : 'default'));

          if (textEditingEl !== el) el.removeAttribute('contenteditable');

        } else {

          el.style.outline = '';

          el.style.outlineOffset = '';

          el.style.cursor = '';

          el.style.boxShadow = '';

          el.removeAttribute('contenteditable');

        }

      });

    });

    updateSelectionBadge();

  }



  function selectElement(el, additive) {

    if (!additive && selectedEl === el && selectedEls.length <= 1) return;

    commitPendingChanges();

    if (textEditingEl && textEditingEl !== el) endTextEdit();

    currentTool = 'move';

    if (additive) {

      const existing = activeSelectedEls();

      if (existing.indexOf(el) >= 0) {

        setSelection(existing.filter((item) => item !== el), existing[0] === el ? existing[1] : selectedEl);

      } else {

        setSelection(existing.concat(el), selectedEl || el);

      }

    } else {

      setSelection([el], el);

    }

    applyEditableState();

    repositionHandles();

    updateSelectionBadge();

    restoreReadout();

  }



  function deselectElement() {

    commitPendingChanges();

    if (textEditingEl) endTextEdit();

    clearGroupEditScopes();

    if (!selectedEl && !selectedEls.length) return;

    setSelection([], null);

    currentTool = null;

    applyEditableState();

    hideHandles();

    updateSelectionBadge();

    restoreReadout();

  }



  let lastActiveSlide = stage.querySelector('.slide.active');

  const activeSlideObserver = new MutationObserver(() => {

    const nextActiveSlide = stage.querySelector('.slide.active');

    if (!nextActiveSlide || nextActiveSlide === lastActiveSlide) return;

    lastActiveSlide = nextActiveSlide;

    commitPendingChanges();

    if (textEditingEl) endTextEdit();

    clearGroupEditScopes();

    setSelection([], null);

    currentTool = null;

    hideHandles();

    applyEditableState();

    lastPaletteSignature = null;

    refreshColorSwatches();

    updateAppearanceControls();

    updateSelectionBadge();

    restoreReadout();

  });

  activeSlideObserver.observe(stage, { attributes: true, attributeFilter: ['class'], subtree: true });



  const selectionMutationObserver = new MutationObserver((mutations) => {

    if (!editMode || !selectedEl) return;

    const targets = selectedTargets();

    const affectsSelection = mutations.some((mutation) => {

      const node = mutation.target && mutation.target.nodeType === 1 ? mutation.target : mutation.target.parentElement;

      return targets.some((el) => el === node || (el.contains && el.contains(node)) || (node && node.contains && node.contains(el)));

    });

    if (affectsSelection) scheduleSelectionRefresh();

  });

  selectionMutationObserver.observe(stage, {

    attributes: true,

    attributeFilter: ['style', 'class', 'data-edit-group', 'data-edit-group-state', 'data-edit-frame-width'],

    characterData: true,

    childList: true,

    subtree: true

  });

  if (document.fonts && document.fonts.ready) document.fonts.ready.then(scheduleSelectionRefresh);



  function updateModePanel() {

    if (!modePanel) return;

    modePanel.style.display = 'none';

  }



  function setControlAvailability(control, available) {

    if (!control) return;

    control.disabled = !available;

    control.style.opacity = available ? '1' : '.35';

    control.setAttribute('aria-disabled', available ? 'false' : 'true');

  }



  function setToolbarRowAvailability(row, available) {

    if (!row) return;

    row.style.display = 'flex';

    row.style.opacity = available ? '1' : '.35';

    row.setAttribute('aria-disabled', available ? 'false' : 'true');

    row.querySelectorAll('button,input,select').forEach((control) => setControlAvailability(control, available));

  }



  function updateObjectAlignmentControls(targetCount, presentationMode) {

    if (!alignToolRow) return;

    const hasTargets = targetCount > 0;

    const alignAsOneObject = presentationMode === 'group' || targetCount === 1;

    const singleLabels = {

      left: M.alignSlideLeft,

      centerX: M.alignSlideCenterX,

      right: M.alignSlideRight,

      top: M.alignSlideTop,

      middle: M.alignSlideMiddle,

      bottom: M.alignSlideBottom

    };

    const multiLabels = {

      left: M.alignElsLeft,

      centerX: M.alignElsCenterX,

      right: M.alignElsRight,

      top: M.alignElsTop,

      middle: M.alignElsMiddle,

      bottom: M.alignElsBottom

    };

    setToolbarRowAvailability(alignToolRow, hasTargets);

    alignToolRow.querySelectorAll('[data-align-selection-mode]').forEach((button) => {

      const mode = button.dataset.alignSelectionMode;

      const label = (alignAsOneObject ? singleLabels : multiLabels)[mode];

      if (label) {

        button.title = label;

        button.setAttribute('aria-label', label);

      }

      setControlAvailability(button, hasTargets);

    });

    alignToolRow.querySelectorAll('[data-distribute-selection-axis]').forEach((button) => {

      setControlAvailability(button, presentationMode !== 'group' && targetCount >= 3);

    });

  }



  function updateTextStyleButtons(targets) {

    const first = targets && targets[0];

    const style = first ? getComputedStyle(first) : null;

    const states = {

      bold: !!style && parseInt(style.fontWeight, 10) >= 700,

      italic: !!style && ['italic', 'oblique'].includes(style.fontStyle),

      underline: !!style && String(style.textDecorationLine || '').includes('underline')

    };

    [[boldBtn, states.bold], [italicBtn, states.italic], [underlineBtn, states.underline]].forEach(([button, active]) => {

      if (!button) return;

      button.setAttribute('aria-pressed', String(active));

      button.style.background = active ? '#DCEFEB' : '#fff';

      button.style.borderColor = active ? '#0B7A75' : 'rgba(18,24,30,.14)';

    });

  }



  function updateSelectionBadge() {

    if (!selectionBadge) return;

    if (!editMode || !selectedEl) {

      selectionBadge.style.display = 'none';

      return;

    }

    const hasSelection = true;

    const meta = currentToolMeta();

    selectionBadge.style.display = 'flex';

    selectionBadge.style.borderColor = meta.soft;

    selectionBadge.style.boxShadow = '0 8px 24px rgba(0,0,0,.18), 0 0 0 1px ' + meta.soft;

    selectionBadge.style.background = 'rgba(255,255,255,.96)';

    const labelEl = selectionBadge.querySelector('[data-role="label"]');

    const hideMultiCount = selectionPresentationMode(selectedTargets()) === 'multi';

    labelEl.textContent = hideMultiCount ? '' : (hasSelection ? selectionLabel() : M.idleMode);

    labelEl.style.display = 'none';

    labelEl.style.color = meta.color;

    const capabilities = selectionCapabilities();

    setToolbarRowAvailability(textToolRow, hasSelection && capabilities.canUseTextTools);

    setToolbarRowAvailability(textAlignToolRow, hasSelection && capabilities.canUseTextTools);

    updateTextStyleButtons(capabilities.canUseTextTools ? capabilities.textTargets : []);

    setToolbarRowAvailability(colorControlRow, hasSelection && capabilities.canUseColor);

    setToolbarRowAvailability(backgroundColorControlRow, hasSelection && capabilities.canUseBackground);

    const alignmentTargets = selectedTargets()

      .filter((el) => el && getComputedStyle(el).display !== 'none');

    updateObjectAlignmentControls(

      alignmentTargets.length,

      selectionPresentationMode(alignmentTargets)

    );

    const verticalTargets = capabilities.allText ? capabilities.targets : [];

    const canAlignVertically = verticalTargets.length > 0 && verticalTargets.every(isVerticalTextBox);

    [verticalTopBtn, verticalCenterBtn, verticalBottomBtn].forEach((btn) => {

      if (btn) btn.style.display = 'inline-flex';

      setControlAvailability(btn, canAlignVertically);

    });

    if (canAlignVertically) {

      const verticalAlign = verticalAlignmentState(selectedEl);

      [

        [verticalTopBtn, verticalAlign === 'start'],

        [verticalCenterBtn, verticalAlign === 'center'],

        [verticalBottomBtn, verticalAlign === 'end']

      ].forEach((entry) => {

        entry[0].style.background = entry[1] ? meta.soft : '#fff';

        entry[0].style.borderColor = entry[1] ? meta.color : 'rgba(18,24,30,.14)';

      });

    }

    const paletteSignature = currentColorControlSignature(capabilities);

    if (paletteSignature !== lastPaletteSignature) {

      refreshColorSwatches();

    }

    setToolbarRowAvailability(colorControlRow, hasSelection && capabilities.canUseColor);

    setToolbarRowAvailability(backgroundColorControlRow, hasSelection && capabilities.canUseBackground);

    updateFontControls();

    updateGroupControls();

    applyPresetChromeTheme();

    updateSelectionBadgePosition();

  }



  function setSelectionBadgeDockMode(enabled) {

    if (!selectionBadge) return;

    selectionBadge.dataset.chromeDock = enabled ? 'true' : 'false';

    selectionBadge.style.padding = enabled ? '5px 8px' : '9px 12px';

    selectionBadge.style.gap = enabled ? '4px' : '7px';

    selectionBadge.style.borderRadius = enabled ? '10px' : '14px';

  }



  function updateSelectionBadgePosition() {

    if (!selectionBadge || selectionBadge.style.display === 'none') return;

    const targets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!targets.length) return;

    setSelectionBadgeDockMode(false);

    const rects = targets.map(visualSelectionRect);

    const selectionLeft = Math.min.apply(null, rects.map((rect) => rect.left));

    const selectionRight = Math.max.apply(null, rects.map((rect) => rect.right));

    const selectionTop = Math.min.apply(null, rects.map((rect) => rect.top));

    const selectionBottom = Math.max.apply(null, rects.map((rect) => rect.bottom));

    const selectionCenterX = (selectionLeft + selectionRight) / 2;

    const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;

    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;

    const bar = document.getElementById('bar');

    const barRect = editMode && bar ? bar.getBoundingClientRect() : null;

    const barBottom = barRect ? barRect.bottom : 0;

    const canvasBox = document.getElementById('canvasBox');

    const workspaceRect = canvasBox ? canvasBox.getBoundingClientRect() : null;

    const gap = 12;

    const emergencyGap = 2;

    const topLimit = Math.max(gap, Math.ceil(barBottom) + gap);

    const bottomLimit = viewportHeight - gap;

    let panelHeight = selectionBadge.offsetHeight;

    let panelWidth = selectionBadge.offsetWidth;

    const avoidsCanvas = (candidateTop, candidateHeight) => !workspaceRect

      || candidateTop + candidateHeight <= workspaceRect.top

      || candidateTop >= workspaceRect.bottom;



    const aboveTop = selectionTop - gap - panelHeight;

    const belowTop = selectionBottom + gap;

    const aboveViewportFits = aboveTop >= topLimit;

    const belowViewportFits = belowTop + panelHeight <= bottomLimit;

    const aboveCanvasFits = aboveViewportFits && avoidsCanvas(aboveTop, panelHeight);

    const belowCanvasFits = belowViewportFits && avoidsCanvas(belowTop, panelHeight);

    const spaceAbove = Math.max(0, selectionTop - gap - topLimit);

    const spaceBelow = Math.max(0, bottomLimit - gap - selectionBottom);

    const emergencyTopLimit = Math.max(0, Math.ceil(barBottom));

    const emergencyBottomLimit = viewportHeight;

    const emergencyAboveTop = selectionTop - emergencyGap - panelHeight;

    const emergencyBelowTop = selectionBottom + emergencyGap;

    const emergencyAboveFits = emergencyAboveTop >= emergencyTopLimit;

    const emergencyBelowFits = emergencyBelowTop + panelHeight <= emergencyBottomLimit;

    const chooseVerticalPlacement = (aboveAvailable, belowAvailable) => {

      if (aboveAvailable && belowAvailable) return spaceAbove >= spaceBelow ? 'above' : 'below';

      return aboveAvailable ? 'above' : 'below';

    };

    let placement;

    let top;

    if (aboveCanvasFits || belowCanvasFits) {

      // Prefer editor chrome outside the slide whenever that lane is available.

      placement = chooseVerticalPlacement(aboveCanvasFits, belowCanvasFits);

      top = placement === 'above' ? aboveTop : belowTop;

    } else if (aboveViewportFits || belowViewportFits) {

      // The canvas is not a forbidden zone: a panel inside it is safe when it

      // remains on the free side of the selected object.

      placement = chooseVerticalPlacement(aboveViewportFits, belowViewportFits);

      top = placement === 'above' ? aboveTop : belowTop;

    } else if (emergencyAboveFits || emergencyBelowFits) {

      placement = chooseVerticalPlacement(emergencyAboveFits, emergencyBelowFits);

      top = placement === 'above' ? emergencyAboveTop : emergencyBelowTop;

    } else {

      // Use the unused lane inside reserved editor chrome rather than

      // covering slide content when neither side can fit the panel.

      setSelectionBadgeDockMode(true);

      panelHeight = selectionBadge.offsetHeight;

      panelWidth = selectionBadge.offsetWidth;

      placement = 'chrome-dock';

      const toolbarIsBelowWorkspace = !!(barRect && barRect.top > viewportHeight / 2);

      top = toolbarIsBelowWorkspace

        ? Math.max(4, Math.floor(barRect.top - panelHeight - 6))

        : Math.max(4, Math.floor(barBottom + 6));

    }

    const workspaceLeft = Math.max(gap, workspaceRect ? workspaceRect.left + gap : gap);

    const workspaceRight = Math.min(viewportWidth - gap, workspaceRect ? workspaceRect.right - gap : viewportWidth - gap);

    const halfWidth = Math.min(panelWidth / 2, Math.max(0, (workspaceRight - workspaceLeft) / 2));

    const left = Math.min(

      Math.max(selectionCenterX, workspaceLeft + halfWidth),

      workspaceRight - halfWidth

    );

    selectionBadge.style.position = 'fixed';

    selectionBadge.style.left = left + 'px';

    selectionBadge.style.transform = 'translateX(-50%)';

    selectionBadge.style.top = top + 'px';

    selectionBadge.style.bottom = 'auto';

    selectionBadge.dataset.placement = placement;

  }



  function setTool(toolKey) {

    if (toolKey !== null && toolKey !== 'move' && toolKey !== 'text' && toolKey !== 'resize') return;

    const nextTool = currentTool === toolKey ? null : toolKey;

    currentTool = nextTool;

    if (textEditingEl && currentTool !== 'text') endTextEdit();

    applyEditableState();

    repositionHandles();

    updateModePanel();

    updateSelectionBadge();

    if (editMode) showTransientReadout(currentToolMeta().label + '｜' + currentToolMeta().hint, 1800);

  }



  function updateActionStates() {

    if (editBtn) {

      const editLabel = editBtn.querySelector('span');

      const actionLabel = editMode ? M.present : M.edit;

      const actionTitle = editMode ? M.presentMode : M.editMode;

      if (editLabel) editLabel.textContent = actionLabel + ' (E)';

      editBtn.title = actionTitle + ' (E)';

      editBtn.setAttribute('aria-label', actionTitle + ' (E)');

      editBtn.style.color = editMode ? currentToolMeta().color : '';

    }

    if (undoBtn) {

      undoBtn.disabled = !editMode || !undoStack.length;

      undoBtn.style.opacity = editMode && undoStack.length ? '1' : '.35';

    }

    if (redoBtn) {

      redoBtn.disabled = !editMode || !redoStack.length;

      redoBtn.style.opacity = editMode && redoStack.length ? '1' : '.35';

    }

    if (exportBtn) exportBtn.style.opacity = editMode ? '1' : '.35';

    if (exportPptxBtn) exportPptxBtn.style.opacity = editMode ? '1' : '.35';

    if (exportBtn) exportBtn.disabled = !editMode;

    if (exportPptxBtn) exportPptxBtn.disabled = !editMode;

    if (saveBtn) {

      saveBtn.disabled = !editMode;

      saveBtn.style.opacity = editMode ? '1' : '.35';

    }

    if (saveMenuToggle) {

      saveMenuToggle.disabled = !editMode;

      saveMenuToggle.style.opacity = editMode ? '1' : '.35';

    }

    if (insertBtn) insertBtn.style.opacity = editMode ? '1' : '.35';

    if (imageUploadBtn) imageUploadBtn.style.opacity = editMode ? '1' : '.35';

    [undoBtn, redoBtn, insertBtn, imageUploadBtn, appearanceBtn, saveBtn, saveMenuToggle].forEach((btn) => {

      if (btn) btn.style.display = editMode ? '' : 'none';

    });

    if (barInner) barInner.dataset.interactionMode = editMode ? 'edit' : 'presentation';

    if (hint) {

      if (!editMode) setReadout('');

    }

    updateModePanel();

    requestAnimationFrame(updateToolbarLayout);

  }



  function beginTextEdit(el) {

    if (!editMode || !isTextEditableElement(el)) return;

    if (textEditingEl === el) return;

    commitPendingChanges();

    if (textEditingEl) endTextEdit();

    currentTool = 'text';

    textEditingEl = el;

    textEditStartHtml = el.innerHTML;

    textEditStartState = snapshotElementState(el);

    textEditInputAnchor = captureTextHorizontalAnchor(el);

    if (!originalTexts.has(el)) originalTexts.set(el, textEditStartHtml);

    selectElement(el);

    currentTool = 'text';

    el.setAttribute('contenteditable', 'true');

    el.style.cursor = 'text';

    el.focus();

    placeCaretAtEnd(el);

    applyEditableState();

    scheduleSelectionRefresh();

    updateModePanel();

    restoreReadout();

  }



  function endTextEdit() {

    if (!textEditingEl) return;

    const el = textEditingEl;

    const beforeHtml = textEditStartHtml;

    const afterHtml = el.innerHTML;

    const beforeState = textEditStartState;

    const afterState = snapshotElementState(el);

    textEditingEl = null;

    textEditStartHtml = null;

    textEditStartState = null;

    textEditInputAnchor = null;

    hideGuides();

    currentTool = selectedEl ? 'move' : null;

    el.removeAttribute('contenteditable');

    if (document.activeElement === el) el.blur();

    applyEditableState();

    scheduleSelectionRefresh();

    if (beforeHtml !== null && beforeHtml !== afterHtml) {

      pushCommand({

        type: 'text',

        el: el,

        key: elementKey(el),

        before: beforeState || { html: beforeHtml },

        after: afterState || { html: afterHtml }

      });

      recordChange(el);

      scheduleDraftSave();

    }

    updateModePanel();

    restoreReadout();

  }



  function toggleEditMode(force) {

    editMode = force === undefined ? !editMode : force;

    commitPendingChanges();

    clearGroupEditScopes();

    if (!editMode) {

      cancelPendingInsert();

      endTextEdit();

      toggleAppearancePanel(false);

      toggleInsertPanel(false);

      currentTool = null;

      setSelection([], null);

      hideHandles();

    } else if (!force || force === true) {

      currentTool = null;

    }

    applyEditableState();

    if (!editMode) {

      setReadout('');

    } else {

      restoreReadout();

    }

    updateActionStates();

    updateSelectionBadge();

    document.dispatchEvent(new CustomEvent('editmodechange', { detail: { editMode: editMode } }));

  }



  async function returnToEditModeFromEscape() {

    if (editMode) return;

    if (document.fullscreenElement && document.exitFullscreen) {

      try {

        await document.exitFullscreen();

      } catch (err) {

        // Returning to edit mode must still work when the browser owns or

        // rejects the fullscreen transition.

      }

    }

    if (!editMode) toggleEditMode(true);

  }



  const TRACKED_STYLE_KEYS = ['fontFamily', 'fontWeight', 'fontStyle', 'textDecorationLine', 'textAlign', 'color', 'background', 'borderColor', 'zIndex', 'display', 'lineHeight', 'letterSpacing', 'textWrap', 'whiteSpace', 'wrapMode', 'alignContent', 'flexDirection', 'justifyContent', 'alignItems', 'verticalAlign', 'frameWidthMode', 'frameHeightMode', 'compositeGroupState', 'groupId', 'transform', 'transformOrigin', 'typographySignature'];



  function recordChange(el) {

    const origPos = originalPositions.get(el);

    const origSize = originalSizes.get(el);

    const origStyle = originalStyles.get(el);

    const state = measureElementState(el);

    const textChanged = originalTexts.has(el) && el.innerHTML !== originalTexts.get(el);

    const posChanged = !!origPos && (Math.abs(state.left - origPos.left) > 0.5 || Math.abs(state.top - origPos.top) > 0.5);

    const sizeChanged = !!origSize && (

      Math.abs(state.width - origSize.width) > 0.5 ||

      Math.abs(state.height - origSize.height) > 0.5 ||

      Math.abs(state.fontSize - origSize.fontSize) > 0.5

    );

    const styleChanged = !!origStyle && TRACKED_STYLE_KEYS.some((key) => origStyle[key] !== state[key]);

    const isClone = !!(el.dataset && el.dataset.editClone);

    if (textChanged) textDirty.add(el);

    else textDirty.delete(el);

    if (posChanged || sizeChanged || textChanged || styleChanged || isClone) {

      changedElements.add(el);

    } else {

      changedElements.delete(el);

    }

    updateActionStates();

    scheduleThumbnailRefresh();

  }



  function currentSlideOrder() {

    if (window.SlidePlayer && typeof window.SlidePlayer.getOrder === 'function') {

      return window.SlidePlayer.getOrder();

    }

    return Array.from(stage.querySelectorAll(':scope > .slide')).map((slide) => slide.id).filter(Boolean);

  }



  const DECK_FONT_PROPERTIES = ['--font-display', '--font-heading', '--font-body'];



  function deckFontState() {

    const rootStyle = document.documentElement.style;

    return DECK_FONT_PROPERTIES.reduce((state, property) => {

      state[property] = rootStyle.getPropertyValue(property).trim();

      return state;

    }, {});

  }



  function applyDeckFontState(state) {

    const rootStyle = document.documentElement.style;

    DECK_FONT_PROPERTIES.forEach((property) => {

      const value = state && typeof state[property] === 'string' ? state[property] : '';

      if (value) rootStyle.setProperty(property, value);

      else rootStyle.removeProperty(property);

    });

  }



  const DEFAULT_SLIDE_MASK_COLOR = '#000000';

  const DEFAULT_SLIDE_MASK_OPACITY = 0;

  const SLIDE_MASK_STYLE_ID = 'edit-slide-mask-style';



  function ensureSlideMaskStyle() {

    if (document.getElementById(SLIDE_MASK_STYLE_ID)) return;

    const style = document.createElement('style');

    style.id = SLIDE_MASK_STYLE_ID;

    style.textContent =
      'html body #stage > section.slide[data-editor-slide-mask="true"]::before{' +
      'content:"mask" !important;display:block !important;position:absolute;inset:0;z-index:0;' +
      'pointer-events:none;font-size:0;line-height:0;color:transparent;' +
      'background:var(--editor-slide-mask-color,#000);' +
      'opacity:var(--editor-slide-mask-opacity,0);}' ;

    document.head.appendChild(style);

  }



  function slideMaskOpacity(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) return DEFAULT_SLIDE_MASK_OPACITY;

    return Math.max(0, Math.min(1, Math.round(number * 100) / 100));

  }



  function slideMaskState(slide) {

    const node = slide || null;

    if (!node) return { color: DEFAULT_SLIDE_MASK_COLOR, opacity: DEFAULT_SLIDE_MASK_OPACITY };

    const colorValue = node.dataset.editorSlideMaskColor

      || node.style.getPropertyValue('--editor-slide-mask-color').trim()

      || DEFAULT_SLIDE_MASK_COLOR;

    const opacityValue = node.dataset.editorSlideMaskOpacity

      || node.style.getPropertyValue('--editor-slide-mask-opacity').trim()

      || DEFAULT_SLIDE_MASK_OPACITY;

    return {

      color: cssColorToHex(colorValue, DEFAULT_SLIDE_MASK_COLOR),

      opacity: slideMaskOpacity(opacityValue)

    };

  }



  function applySlideMaskState(slide, state) {

    if (!slide) return null;

    ensureSlideMaskStyle();

    const next = state || {};

    const color = cssColorToHex(next.color || DEFAULT_SLIDE_MASK_COLOR, DEFAULT_SLIDE_MASK_COLOR);

    const opacity = slideMaskOpacity(next.opacity);

    slide.dataset.editorSlideMaskColor = color;

    slide.dataset.editorSlideMaskOpacity = String(opacity);

    slide.style.setProperty('--editor-slide-mask-color', color);

    slide.style.setProperty('--editor-slide-mask-opacity', String(opacity));

    if (opacity > 0) slide.dataset.editorSlideMask = 'true';

    else slide.removeAttribute('data-editor-slide-mask');

    return { color: color, opacity: opacity };

  }



  function initializeSlideMasks() {

    ensureSlideMaskStyle();

    stage.querySelectorAll(':scope > .slide').forEach((slide) => {

      const hasSavedMask = slide.dataset.editorSlideMaskColor

        || slide.dataset.editorSlideMaskOpacity

        || slide.style.getPropertyValue('--editor-slide-mask-color')

        || slide.style.getPropertyValue('--editor-slide-mask-opacity');

      if (hasSavedMask) applySlideMaskState(slide, slideMaskState(slide));

    });

  }



  function slideMaskStates() {

    return Array.from(stage.querySelectorAll(':scope > .slide')).reduce((states, slide) => {

      if (slide.id) states[slide.id] = slideMaskState(slide);

      return states;

    }, {});

  }



  function slideBackgroundStates() {

    return Array.from(stage.querySelectorAll(':scope > .slide')).reduce((states, slide) => {

      if (slide.id) states[slide.id] = slide.style.backgroundColor || '';

      return states;

    }, {});

  }



  function appearanceStateChanged(before, after) {

    return JSON.stringify(before || null) !== JSON.stringify(after || null);

  }



  initializeSlideMasks();



  let savedSlideOrder = currentSlideOrder();

  let savedDeckFontState = deckFontState();

  let savedSlideBackgroundStates = slideBackgroundStates();

  let savedSlideMaskStates = slideMaskStates();



  function updateSlideOrderDirty() {

    slideOrderDirty = savedSlideOrder.join('|') !== currentSlideOrder().join('|');

  }



  function hasPendingChanges() {

    const currentDeckFontState = deckFontState();

    const deckFontDirty = appearanceStateChanged(savedDeckFontState, currentDeckFontState);

    const currentSlideBackgroundStates = slideBackgroundStates();

    const currentSlideMaskStates = slideMaskStates();

    const backgroundIds = new Set([

      ...Object.keys(savedSlideBackgroundStates || {}),

      ...Object.keys(currentSlideBackgroundStates || {})

    ]);

    const slideBackgroundDirty = Array.from(backgroundIds).some((slideId) => (

      (currentSlideBackgroundStates[slideId] || '') !== (savedSlideBackgroundStates[slideId] || '')

    ));

    const maskIds = new Set([

      ...Object.keys(savedSlideMaskStates || {}),

      ...Object.keys(currentSlideMaskStates || {})

    ]);

    const slideMaskDirty = Array.from(maskIds).some((slideId) => (

      appearanceStateChanged(currentSlideMaskStates[slideId], savedSlideMaskStates[slideId])

    ));

    const changedElementIsLive = Array.from(changedElements).some((el) => document.contains(el));

    return changedElementIsLive || slideOrderDirty || deckFontDirty || slideBackgroundDirty || slideMaskDirty;

  }



  function scheduleThumbnailRefresh() {

    if (!editMode || !window.SlidePlayer || typeof window.SlidePlayer.refreshSlides !== 'function') return;

    if (thumbnailRefreshTimer) clearTimeout(thumbnailRefreshTimer);

    thumbnailRefreshTimer = setTimeout(() => {

      thumbnailRefreshTimer = null;

      const active = document.querySelector('.slide.active');

      window.SlidePlayer.refreshSlides(active ? active.id : null);

    }, 180);

  }



  function applyFontScale(el, handlePos, newW, newH) {

    if (!resizeTypographyStart.length) return;

    const isCorner = handlePos.length === 2;

    if (!isCorner) return;

    const scale = newW / resizeStartW;

    resizeTypographyStart.forEach((item) => {

      setUserStyle(item.node, 'font-size', Math.max(1, item.fontSize * scale).toFixed(1) + 'px');

      if (item.lineHeight !== null) {

        setUserStyle(item.node, 'line-height', Math.max(1, item.lineHeight * scale).toFixed(1) + 'px');

      }

      if (item.letterSpacing !== null) {

        setUserStyle(item.node, 'letter-spacing', (item.letterSpacing * scale).toFixed(2) + 'px');

      }

    });

  }



  function measuredTextLineMetrics(node, computedStyle) {

    const parsed = parseFloat(computedStyle.lineHeight);

    const scale = getScale() || 1;

    const range = document.createRange();

    range.selectNodeContents(node);

    const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0 && rect.height > 0);

    if (rects.length) {

      const lineTops = [];

      rects.forEach((rect) => {

        if (!lineTops.some((top) => Math.abs(top - rect.top) <= 1)) lineTops.push(rect.top);

      });

      const lineCount = Math.max(1, lineTops.length);

      const top = Math.min.apply(null, rects.map((rect) => rect.top));

      const bottom = Math.max.apply(null, rects.map((rect) => rect.bottom));

      const visualHeight = (bottom - top) / scale;

      const visualLineHeight = visualHeight / lineCount;

      // The editable frame must never be shorter than the rendered glyph line.

      // A 1-2px mismatch here becomes very visible after proportional scaling.

      const lineHeight = Number.isNaN(parsed) ? visualLineHeight : Math.max(parsed, visualLineHeight);

      return { lineHeight: lineHeight, lineCount: lineCount, visualHeight: visualHeight };

    }

    const fallback = Number.isNaN(parsed) ? (parseFloat(computedStyle.fontSize) || 1) * 1.2 : parsed;

    return { lineHeight: fallback, lineCount: 1, visualHeight: fallback };

  }



  function measuredTextWrapMetrics(node, fallbackWidth) {

    const scale = getScale() || 1;

    const range = document.createRange();

    range.selectNodeContents(node);

    const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0 && rect.height > 0);

    if (!rects.length) {

      return {

        lineCount: 1,

        minimumLinePreservingWidth: Math.max(MIN_SIZE, fallbackWidth || MIN_SIZE)

      };

    }

    const lines = [];

    rects.forEach((rect) => {

      let line = lines.find((item) => Math.abs(item.top - rect.top) <= 1);

      if (!line) {

        line = { top: rect.top, left: rect.left, right: rect.right };

        lines.push(line);

      } else {

        line.left = Math.min(line.left, rect.left);

        line.right = Math.max(line.right, rect.right);

      }

    });

    const style = getComputedStyle(node);

    const horizontalInsets = (parseFloat(style.paddingLeft) || 0)

      + (parseFloat(style.paddingRight) || 0)

      + (parseFloat(style.borderLeftWidth) || 0)

      + (parseFloat(style.borderRightWidth) || 0);

    const widestLine = Math.max.apply(null, lines.map((line) => (line.right - line.left) / scale));

    return {

      lineCount: Math.max(1, lines.length),

      // Keep a tiny rounding allowance so a one-pixel drag does not create an

      // otherwise avoidable extra line.

      minimumLinePreservingWidth: Math.min(

        Math.max(MIN_SIZE, fallbackWidth || MIN_SIZE),

        Math.max(MIN_SIZE, widestLine + horizontalInsets + 2)

      )

    };

  }



  function captureTypographyStart(el) {

    return scalableTextNodes(el).map((node) => {

      // Keep the first user-visible typography as the ceiling for later
      // resize passes. Without this stable ceiling, a shrink followed by an
      // expand captures the already-shrunken type as its new baseline.
      ensureOriginalGeometry(node);
      const cs = getComputedStyle(node);

      const letterSpacing = parseFloat(cs.letterSpacing);

      const lineMetrics = measuredTextLineMetrics(node, cs);
      const originalSize = originalSizes.get(node);
      const originalStyle = originalStyles.get(node);

      return {

        node: node,

        fontSize: parseFloat(cs.fontSize) || 0,

        computedLineHeight: parseFloat(cs.lineHeight) || lineMetrics.lineHeight,
        originalFontSize: originalSize && originalSize.fontSize > 0
          ? originalSize.fontSize
          : (parseFloat(cs.fontSize) || 0),
        originalLineHeight: originalStyle && parseFloat(originalStyle.lineHeight) > 0
          ? parseFloat(originalStyle.lineHeight)
          : (parseFloat(cs.lineHeight) || lineMetrics.lineHeight),

        // Chrome may expose inherited `normal` instead of a pixel value.  If

        // we leave it implicit, resizing recomputes a fresh line box whose

        // center drifts away from the scaled selection box.  Freeze the

        // measured line height before scaling so both remain proportional.

        lineHeight: lineMetrics.lineHeight,

        lineCount: lineMetrics.lineCount,

        visualHeight: lineMetrics.visualHeight,

        letterSpacing: Number.isNaN(letterSpacing) ? null : letterSpacing

      };

    }).filter((item) => item.fontSize > 0);

  }



  function scaledOwnTextHeight(el, scale, fallbackHeight) {

    const own = resizeTypographyStart.find((item) => item.node === el);

    if (!own) return Math.max(MIN_SIZE, fallbackHeight * scale);

    const lineBoxHeight = own.lineHeight * Math.max(1, own.lineCount || 1);

    const tightHeight = Math.max(lineBoxHeight, own.visualHeight || 0);

    return Math.max(MIN_SIZE, Math.round(tightHeight * scale * 10) / 10);

  }



  function lockResizeAspect(handlePos, candidate, centerResize) {

    const horizontal = handlePos.indexOf('e') >= 0 || handlePos.indexOf('w') >= 0;

    const vertical = handlePos.indexOf('n') >= 0 || handlePos.indexOf('s') >= 0;

    const scaleW = candidate.width / resizeStartW;

    const scaleH = candidate.height / resizeStartH;

    let scale;

    if (horizontal && vertical) {

      scale = Math.abs(scaleW - 1) >= Math.abs(scaleH - 1) ? scaleW : scaleH;

    } else if (horizontal) {

      scale = scaleW;

    } else {

      scale = scaleH;

    }

    scale = Math.max(scale, MIN_SIZE / resizeStartW, MIN_SIZE / resizeStartH);

    const width = Math.round(resizeStartW * scale);

    const height = Math.round(resizeStartH * scale);

    let left = resizeStartLeft;

    let top = resizeStartTop;

    if (centerResize) {

      left = resizeStartLeft + (resizeStartW - width) / 2;

      top = resizeStartTop + (resizeStartH - height) / 2;

    } else {

      left = handlePos.indexOf('w') >= 0

        ? resizeStartLeft + resizeStartW - width

        : (handlePos.indexOf('e') >= 0 ? resizeStartLeft : resizeStartLeft + (resizeStartW - width) / 2);

      top = handlePos.indexOf('n') >= 0

        ? resizeStartTop + resizeStartH - height

        : (handlePos.indexOf('s') >= 0 ? resizeStartTop : resizeStartTop + (resizeStartH - height) / 2);

    }

    return {

      left: Math.round(left * 10) / 10,

      top: Math.round(top * 10) / 10,

      width: width,

      height: height,

      scale: scale

    };

  }



  function captureVisualTransformStart(el) {

    const computedStyle = getComputedStyle(el);

    const computed = computedStyle.transform;

    return {

      // A computed transform is normalized to matrix(...), while an inline

      // transform may contain a previous scale() function.  Prefer the

      // normalized form so repeated corner scaling never stacks functions.

      transform: computed && computed !== 'none' ? computed : (el.style.transform || ''),

      transformOrigin: el.style.transformOrigin || '',

      positioned: computedStyle.position !== 'static'

    };

  }



  function isEdgeAnchoredVisualLayer(el) {

    if (!el || !el.dataset || el.dataset.editLayer !== 'visual') return false;

    // New renderer output declares the relationship directly.  This keeps
    // the editor aligned with the design-system contract instead of making
    // every Theme/Preset repeat a CSS heuristic.
    const declaredAnchor = String(el.dataset.editAnchor || '').trim().toLowerCase();

    if (declaredAnchor === 'bottom') return true;

    if (declaredAnchor) return false;

    const style = getComputedStyle(el);

    const authoredTop = String(el.style.top || '').trim().toLowerCase();
    const authoredBottom = String(el.style.bottom || '').trim().toLowerCase();

    // Decorative rules such as card progress bars are authored with a
    // bottom anchor.  Their position should come from the parent frame after
    // a resize, not from an old transform left by an earlier resize.
    return style.position === 'absolute'

      && authoredBottom !== ''

      && authoredBottom !== 'auto'

      && (authoredTop === '' || authoredTop === 'auto');

  }



  function resetEdgeAnchoredVisualTransform(layer) {

    if (!layer || !isEdgeAnchoredVisualLayer(layer.el)) return;

    setUserStyle(layer.el, 'transform', '');

    setUserStyle(layer.el, 'transform-origin', '');

    // captureVisualTransformStart() records the computed transform so normal
    // visual scaling does not stack matrices. Once an anchored rule is
    // intentionally reattached to its parent edge, discard that old matrix
    // from the adaptive snapshot as well, otherwise the next zero-offset pass
    // would immediately put it back.
    if (layer.visual) {

      layer.visual.transform = '';

      layer.visual.transformOrigin = '';

    }

  }



  function applyVisualScale(el, start, scaleX, scaleY) {

    const x = Math.max(0.01, Math.round(scaleX * 1000000) / 1000000);

    const y = Math.max(0.01, Math.round(scaleY * 1000000) / 1000000);

    // Inline/flex text layers do not respond to left/top.  Scale those from

    // their own center; absolutely positioned slide objects keep a top-left

    // origin so their anchor can be adjusted explicitly.

    setUserStyle(el, 'transform-origin', start && start.transformOrigin

      ? start.transformOrigin

      : (start && start.positioned === false ? '50% 50%' : '0 0'));

    const base = start && start.transform && start.transform !== 'none' ? start.transform : '';

    if (!base && x === 1 && y === 1) {

      setUserStyle(el, 'transform', '');

      setUserStyle(el, 'transform-origin', start && start.transformOrigin ? start.transformOrigin : '');

      return;

    }

    try {

      const matrix = base ? new DOMMatrixReadOnly(base) : new DOMMatrixReadOnly();



      const scaled = matrix.scale(x, y);

      const clean = (value) => Math.abs(value) < 0.0000001 ? 0 : Math.round(value * 1000000) / 1000000;

      const transform = scaled.is2D

        ? 'matrix(' + [scaled.a, scaled.b, scaled.c, scaled.d, scaled.e, scaled.f].map(clean).join(',') + ')'

        : scaled.toString();

      setUserStyle(el, 'transform', transform);

    } catch (err) {

      const prefix = base ? base + ' ' : '';

      setUserStyle(el, 'transform', prefix + 'scale(' + x + ',' + y + ')');

    }

  }



  function applyVisualTranslation(el, start, deltaX, deltaY) {

    const x = Math.round((Number(deltaX) || 0) * 10) / 10;

    const y = Math.round((Number(deltaY) || 0) * 10) / 10;

    setUserStyle(el, 'transform-origin', start && start.transformOrigin

      ? start.transformOrigin

      : (start && start.positioned === false ? '50% 50%' : '0 0'));

    const base = start && start.transform && start.transform !== 'none' ? start.transform : '';

    if (!base && Math.abs(x) <= 0.05 && Math.abs(y) <= 0.05) {

      setUserStyle(el, 'transform', '');

      setUserStyle(el, 'transform-origin', start && start.transformOrigin ? start.transformOrigin : '');

      return;

    }

    const translation = 'translate(' + x + 'px,' + y + 'px)';

    setUserStyle(el, 'transform', base ? translation + ' ' + base : translation);

  }



  function adaptiveResizeLayerCandidates(root) {

    return Array.from(root.querySelectorAll('[data-edit-layer]')).filter((layer) => {

      if (layer.closest('.el') !== root) return false;

      if (getComputedStyle(layer).display === 'none') return false;

      const parentLayer = layer.parentElement && layer.parentElement.closest('[data-edit-layer]');

      return !parentLayer || !root.contains(parentLayer);

    });

  }



  function captureAdaptiveVerticalFlow(root, rootBox, layers) {

    const directChildren = Array.from(root.children).filter((child) => {

      if (getComputedStyle(child).display === 'none') return false;

      if (child.dataset && child.dataset.editLayer === 'background') return false;

      const box = stageBox(child);

      return box.width > 0.5 && box.height > 0.5;

    });

    // A structural wrapper (for example UL > LI > text layers) is the case the
    // layer-only fitter cannot represent: moving each nested glyph separately
    // leaves the wrapper, separators and nearby visual blocks behind. Only opt
    // into the flow solver when such a wrapper is present and the direct
    // children form a real, non-overlapping vertical stack.
    const hasStructuralWrapper = directChildren.some((child) => (

      !(child.dataset && child.dataset.editLayer)

      && !!child.querySelector('[data-edit-layer]')

    ));

    if (!hasStructuralWrapper || directChildren.length < 2) return null;

    const layerByElement = new Map((layers || []).map((layer) => [layer.el, layer]));

    const blocks = directChildren.map((child) => {

      const capturedLayer = layerByElement.get(child);

      return capturedLayer || {

        el: child,

        key: elementKey(child),

        before: measureElementState(child),

        box: stageBox(child),

        visual: captureVisualTransformStart(child),

        typography: captureTypographyStart(child),

        textFrame: isTextEditableElement(child)

      };

    }).sort((first, second) => first.box.top - second.box.top || first.box.left - second.box.left);

    for (let first = 0; first < blocks.length; first += 1) {

      for (let second = first + 1; second < blocks.length; second += 1) {

        const horizontalOverlap = Math.min(blocks[first].box.right, blocks[second].box.right)

          - Math.max(blocks[first].box.left, blocks[second].box.left);

        const verticalOverlap = Math.min(blocks[first].box.bottom, blocks[second].box.bottom)

          - Math.max(blocks[first].box.top, blocks[second].box.top);

        if (horizontalOverlap > 1 && verticalOverlap > 2) return null;

      }

    }

    const gaps = [Math.max(0, blocks[0].box.top - rootBox.top)];

    for (let index = 1; index < blocks.length; index += 1) {

      gaps.push(Math.max(0, blocks[index].box.top - blocks[index - 1].box.bottom));

    }

    gaps.push(Math.max(0, rootBox.bottom - blocks[blocks.length - 1].box.bottom));

    const rootStyle = getComputedStyle(root);

    const authoredMinGap = parseFloat(rootStyle.getPropertyValue('--edit-adaptive-min-gap'));

    const authoredMinInset = parseFloat(rootStyle.getPropertyValue('--edit-adaptive-min-inset'));

    const minimumGap = Number.isFinite(authoredMinGap) ? Math.max(0, authoredMinGap) : 4;

    // Edge insets also absorb font overhang beyond a measured line box. Keep a
    // slightly larger fallback than the inter-block clearance so CJK glyphs do
    // not paint outside the selected group at the spacing floor.
    const minimumInset = Number.isFinite(authoredMinInset) ? Math.max(0, authoredMinInset) : 12;

    const minimumGaps = gaps.map((gap, index) => (

      Math.min(gap, index === 0 || index === gaps.length - 1 ? minimumInset : minimumGap)

    ));

    const heightMetrics = [];

    const seenHeightNodes = new Set();

    blocks.forEach((block) => {

      [block.el].concat(Array.from(block.el.querySelectorAll(':scope > *'))).forEach((node) => {

        if (seenHeightNodes.has(node)) return;

        const kind = node.dataset && node.dataset.editLayer;

        const structural = !kind && !!node.querySelector('[data-edit-layer]');

        if (kind !== 'visual' && !structural) return;

        const box = stageBox(node);

        if (!(box.height > 0.5)) return;

        seenHeightNodes.add(node);

        heightMetrics.push({ el: node, height: box.height });

      });

    });

    return {

      blocks: blocks,

      gaps: gaps,

      minimumGaps: minimumGaps,

      originalContentHeight: blocks.reduce((total, block) => total + block.box.height, 0),

      minimumGapHeight: minimumGaps.reduce((total, gap) => total + gap, 0),

      heightMetrics: heightMetrics

    };

  }



  function applyAdaptiveAxisTypographyBaseline(root, rootBox, typography, axis) {

    if (axis !== 'horizontal' && axis !== 'vertical') return;

    const orthogonalSize = axis === 'vertical' ? rootBox.width : rootBox.height;

    const axisSize = axis === 'vertical' ? rootBox.height : rootBox.width;

    let baselines = adaptiveAxisTypographyBaselines.get(root);

    if (!baselines) {

      baselines = {};

      adaptiveAxisTypographyBaselines.set(root, baselines);

    }

    let baseline = baselines[axis];

    if (!baseline || Math.abs(baseline.orthogonalSize - orthogonalSize) > 1.5) {

      baseline = {

        orthogonalSize: orthogonalSize,

        axisSize: axisSize,

        typography: new WeakMap()

      };

      baselines[axis] = baseline;

    }

    const atBaselineExtent = Math.abs(baseline.axisSize - axisSize) <= 1.5;

    typography.forEach((metric) => {

      let ceiling = baseline.typography.get(metric.node);

      // Reaching the baseline extent means the prior axis edit has completed.
      // Refresh here so an intentional font edit becomes the next resize
      // ceiling, while an intermediate shrink still points back to its start.
      if (!ceiling || atBaselineExtent) {

        ceiling = {

          fontSize: metric.fontSize,

          lineHeight: metric.computedLineHeight || metric.lineHeight || metric.fontSize

        };

        baseline.typography.set(metric.node, ceiling);

      }

      metric.originalFontSize = ceiling.fontSize;

      metric.originalLineHeight = ceiling.lineHeight;

    });

  }



  function captureAdaptiveGroupResize(root, rootBox, axis) {

    const layers = adaptiveResizeLayerCandidates(root)

      .filter((layer) => !(layer.dataset && layer.dataset.editLayer === 'background'))

      .map((layer) => {

        const box = stageBox(layer);

        const textFrame = isTextEditableElement(layer);
        const horizontalAnchorMode = textFrame ? horizontalTextAnchorMode(layer) : 'center';
        const horizontalAnchorX = horizontalAnchorMode === 'left'
          ? box.left
          : (horizontalAnchorMode === 'right' ? box.right : box.left + box.width / 2);

        return {

          el: layer,

          key: elementKey(layer),

          before: measureElementState(layer),

          box: box,

          visual: captureVisualTransformStart(layer),

          typography: captureTypographyStart(layer),

          textFrame: textFrame,

          wrapMetrics: textFrame ? measuredTextWrapMetrics(layer, box.width) : null,

          centerRatioY: rootBox.height > 0

            ? ((box.top + box.height / 2) - rootBox.top) / rootBox.height

            : 0.5,

          centerRatioX: rootBox.width > 0

            ? ((box.left + box.width / 2) - rootBox.left) / rootBox.width

            : 0.5,
          horizontalAnchorMode: horizontalAnchorMode,
          horizontalAnchorRatioX: rootBox.width > 0
            ? (horizontalAnchorX - rootBox.left) / rootBox.width
            : 0.5

        };

      });

    const verticalFlow = captureAdaptiveVerticalFlow(root, rootBox, layers);

    const coveredTypography = new Set();

    layers.forEach((layer) => layer.typography.forEach((metric) => coveredTypography.add(metric.node)));

    const extraTypography = captureTypographyStart(root).filter((metric) => !coveredTypography.has(metric.node));

    const extraTextNodes = Array.from(new Set(extraTypography.map((metric) => metric.node))).filter((node, index, nodes) => {

      return !nodes.some((other, otherIndex) => otherIndex !== index && other.contains(node));

    });

    const layerTextBoxes = layers.filter((layer) => {

      const kind = layer.el.dataset && layer.el.dataset.editLayer;

      return layer.typography.length > 0 && kind !== 'visual' && kind !== 'background';

    }).map((layer) => layer.el);

    const typography = layers.reduce((items, layer) => items.concat(layer.typography), []).concat(extraTypography);

    applyAdaptiveAxisTypographyBaseline(root, rootBox, typography, axis);

    const minimumFontScale = typography.length

      ? AUTO_RESIZE_MIN_FONT_RATIO

      : 1;

    const textBoxes = Array.from(new Set(layerTextBoxes.concat(extraTextNodes)));

    let minimumContentHeight = textBoxes.reduce((requiredHeight, node) => {

      const rect = viewportRectToStageBox(adaptiveTextPaintRect(node));

      if (!(rect.height > 0.5) || !(rootBox.height > 0.5)) return requiredHeight;

      const centerRatio = Math.max(

        0.02,

        Math.min(0.98, ((rect.top + rect.height / 2) - rootBox.top) / rootBox.height)

      );

      const halfGlyphHeight = rect.height * minimumFontScale / 2 + 1;

      return Math.max(

        requiredHeight,

        halfGlyphHeight / centerRatio,

        halfGlyphHeight / (1 - centerRatio)

      );

    }, MIN_SIZE);

    const collisionGeometry = textBoxes.map((node) => {

      const rect = viewportRectToStageBox(adaptiveTextPaintRect(node));

      return {

        rect: rect,

        centerRatio: rootBox.height > 0.5

          ? ((rect.top + rect.height / 2) - rootBox.top) / rootBox.height

          : 0.5,

        halfGlyphHeight: rect.height * minimumFontScale / 2 + 1

      };

    });

    // Pairwise text-center separation is not a minimum frame height. It is a

    // description of the current authored spacing, and using it as a hard

    // clamp made a valid card refuse every inward group-height drag whenever

    // two text frames shared a horizontal span. The adaptive fitter below is

    // the collision authority: it first consumes spacing, then line-height and

    // type scale, while the group-level pass resolves collisions between

    // separate semantic modules. Keep the minimum here to independent edge

    // clearance only.

    // collisionGeometry remains captured for diagnostics and future scoring.

    // Keep only the independent edge-clearance floor. Pairwise text-center
    // separation is intentionally excluded so a normal inward drag can first
    // consume spacing and let the adaptive fitter shrink the content.
    const minimumVerticalScale = Math.min(
      1,
      Math.max(MIN_SIZE, minimumContentHeight) / Math.max(MIN_SIZE, rootBox.height)
    );

    const minimumLineHeightScale = typography.length

      ? Math.max(0.05, Math.min.apply(null, typography.map((metric) => {

        const baseLineHeight = metric.computedLineHeight || metric.lineHeight || metric.fontSize;

        const originalRatio = baseLineHeight / Math.max(1, metric.fontSize);

        const minimumRatio = Math.max(0.72, Math.min(originalRatio, 0.92));

        return Math.min(1, (metric.fontSize * minimumRatio) / Math.max(1, baseLineHeight));

      })))

      : 1;

    const style = getComputedStyle(root);

    const historyItems = [];

    const historyElements = new Set();

    const verticalHeightOwners = new Set(verticalFlow

      ? verticalFlow.heightMetrics.map((metric) => metric.el)

      : []);

    const addHistoryItem = (entry) => {

      if (!entry || !entry.el || entry.el === root || historyElements.has(entry.el)) return;

      historyElements.add(entry.el);

      historyItems.push({

        el: entry.el,

        key: elementKey(entry.el),

        before: entry.before || measureElementState(entry.el),

        verticalOwnsHeight: verticalHeightOwners.has(entry.el)

      });

    };

    layers.forEach(addHistoryItem);

    if (verticalFlow) {

      verticalFlow.blocks.forEach(addHistoryItem);

      verticalFlow.heightMetrics.forEach(addHistoryItem);

    }

    return {

      layers: layers,

      extraTypography: extraTypography,

      typography: typography,

      textBoxes: textBoxes,

      verticalFlow: verticalFlow,

      historyItems: historyItems,

      minimumFontScale: minimumFontScale,

      minimumLineHeightScale: minimumLineHeightScale,

      minimumVerticalScale: minimumVerticalScale,

      spacing: {

        paddingLeft: parseFloat(style.paddingLeft) || 0,

        paddingRight: parseFloat(style.paddingRight) || 0,

        paddingTop: parseFloat(style.paddingTop) || 0,

        paddingBottom: parseFloat(style.paddingBottom) || 0,

        rowGap: parseFloat(style.rowGap) || 0,

        columnGap: parseFloat(style.columnGap) || 0

      },

      appliedLineHeightScale: 1,

      appliedFontScale: 1

    };

  }



  function applyAdaptiveLayerOffset(layer, deltaX, deltaY) {

    const start = layer.visual || {};

    setUserStyle(layer.el, 'transform-origin', start.transformOrigin || (start.positioned === false ? '50% 50%' : '0 0'));

    const base = start.transform && start.transform !== 'none' ? start.transform : '';

    if (!base && Math.abs(deltaX) < 0.0000001 && Math.abs(deltaY) < 0.0000001) {

      setUserStyle(layer.el, 'transform', '');

      setUserStyle(layer.el, 'transform-origin', start.transformOrigin || '');

      return;

    }

    const clean = (value) => Math.abs(value) < 0.0000001 ? 0 : Math.round(value * 1000000) / 1000000;

    try {

      const matrix = base ? new DOMMatrixReadOnly(base) : new DOMMatrixReadOnly();

      if (matrix.is2D) {

        setUserStyle(layer.el, 'transform', 'matrix(' + [

          matrix.a, matrix.b, matrix.c, matrix.d, matrix.e + deltaX, matrix.f + deltaY

        ].map(clean).join(',') + ')');

      } else {

        setUserStyle(layer.el, 'transform', matrix.translate(deltaX, deltaY).toString());

      }

    } catch (err) {

      const prefix = base ? base + ' ' : '';

      setUserStyle(layer.el, 'transform', prefix + 'translate(' + clean(deltaX) + 'px,' + clean(deltaY) + 'px)');

    }

  }



  function applyAdaptiveTypographyMetrics(metrics, lineHeightScale, fontScale) {

    const spacingScale = Math.max(0.05, Math.min(lineHeightScale, 2));

    metrics.forEach((metric) => {

      const fontCeiling = metric.originalFontSize > 0 ? metric.originalFontSize : Infinity;
      const fontSize = Math.max(1, Math.min(fontCeiling, metric.fontSize * fontScale));

      const baseLineHeight = metric.computedLineHeight || metric.lineHeight || metric.fontSize;

      const originalRatio = baseLineHeight / Math.max(1, metric.fontSize);

      const minimumRatio = Math.max(0.72, Math.min(originalRatio, 0.92));

      let lineHeight = Math.max(

        fontSize * minimumRatio,

        baseLineHeight * spacingScale * fontScale

      );
      const recoveredFontCeiling = fontScale >= 1

        && Number.isFinite(fontCeiling)

        && fontSize >= fontCeiling - 0.01;

      if (metric.originalLineHeight > 0) {

        // Spacing-first shrink can reduce the line box more than the glyphs.
        // Once the axis-specific font ceiling is recovered, restore its paired
        // line height as one baseline instead of accumulating a tighter line
        // box on every shrink/expand round trip.
        lineHeight = recoveredFontCeiling

          ? metric.originalLineHeight

          : Math.min(metric.originalLineHeight, lineHeight);

      }

      setUserStyle(metric.node, 'font-size', (Math.round(fontSize * 100) / 100) + 'px');

      setUserStyle(metric.node, 'line-height', (Math.round(lineHeight * 100) / 100) + 'px');

    });

  }



  function adaptiveVerticalGapPlan(flow, targetGapHeight) {

    const originalTotal = flow.gaps.reduce((total, gap) => total + gap, 0);

    const minimumTotal = flow.minimumGapHeight;

    if (targetGapHeight <= originalTotal) {

      const available = Math.max(0, originalTotal - minimumTotal);

      const ratio = available > 0.01

        ? Math.max(0, Math.min(1, (targetGapHeight - minimumTotal) / available))

        : 0;

      return flow.gaps.map((gap, index) => (

        flow.minimumGaps[index] + (gap - flow.minimumGaps[index]) * ratio

      ));

    }

    const extra = targetGapHeight - originalTotal;

    const weights = flow.gaps.map((gap) => Math.max(1, gap));

    const totalWeight = weights.reduce((total, weight) => total + weight, 0);

    return flow.gaps.map((gap, index) => gap + extra * weights[index] / totalWeight);

  }



  function applyAdaptiveVerticalFlow(item, targetRootHeight) {

    const adaptive = item.adaptive;

    const flow = adaptive.verticalFlow;

    flow.blocks.forEach((block) => resetEdgeAnchoredVisualTransform(block));

    flow.blocks.forEach((block) => applyAdaptiveLayerOffset(block, 0, 0));

    let contentScale = targetRootHeight >= flow.originalContentHeight + flow.minimumGapHeight

      ? 1

      : Math.max(

        adaptive.minimumFontScale,

        Math.min(1, (targetRootHeight - flow.minimumGapHeight) / Math.max(1, flow.originalContentHeight))

      );

    let blockHeights = [];

    let gapHeight = 0;

    for (let attempt = 0; attempt < 3; attempt += 1) {

      applyAdaptiveTypographyMetrics(adaptive.typography, contentScale, contentScale);

      flow.heightMetrics.forEach((metric) => {

        setUserStyle(

          metric.el,

          'height',

          (Math.round(Math.max(MIN_SIZE, metric.height * contentScale) * 10) / 10) + 'px'

        );

      });

      blockHeights = flow.blocks.map((block) => stageBox(block.el).height);

      gapHeight = targetRootHeight - blockHeights.reduce((total, height) => total + height, 0);

      if (gapHeight >= flow.minimumGapHeight - 0.5 || contentScale <= adaptive.minimumFontScale + 0.0001) break;

      const availableContent = Math.max(MIN_SIZE, targetRootHeight - flow.minimumGapHeight);

      const measuredContent = Math.max(MIN_SIZE, blockHeights.reduce((total, height) => total + height, 0));

      contentScale = Math.max(

        adaptive.minimumFontScale,

        Math.min(contentScale, contentScale * availableContent / measuredContent)

      );

    }

    const gaps = adaptiveVerticalGapPlan(flow, Math.max(flow.minimumGapHeight, gapHeight));

    const rootBox = stageBox(item.el);

    const logicalHeight = Math.max(0.01, styleNumber(item.el, 'height', item.before.height));

    const rootVisualScaleY = Math.max(0.01, rootBox.height / logicalHeight);

    let cursor = rootBox.top + gaps[0];

    flow.blocks.forEach((block, index) => {

      const current = stageBox(block.el);

      applyAdaptiveLayerOffset(block, 0, (cursor - current.top) / rootVisualScaleY);

      const placed = stageBox(block.el);

      cursor = placed.bottom + gaps[index + 1];

    });

    adaptive.appliedLineHeightScale = contentScale;

    adaptive.appliedFontScale = contentScale;

    return contentScale;

  }



  function positionAdaptiveGroupLayersY(item) {

    const adaptive = item.adaptive;

    adaptive.layers.forEach((layer) => resetEdgeAnchoredVisualTransform(layer));

    adaptive.layers.forEach((layer) => applyAdaptiveLayerOffset(layer, 0, 0));

    const rootBox = stageBox(item.el);

    const logicalHeight = Math.max(0.01, styleNumber(item.el, 'height', item.before.height));

    const rootVisualScaleY = Math.max(0.01, rootBox.height / logicalHeight);

    // Absolute semantic layers keep their authored horizontal geometry, but
    // their vertical flow must re-resolve after a group-height edit. Position
    // the layers by their authored centers first, then push later text layers
    // below earlier layers when their painted boxes collide.
    const movableLayers = adaptive.layers

      .filter((layer) => {

        const kind = layer.el.dataset && layer.el.dataset.editLayer;

        return layer.textFrame || kind === 'text' || kind === 'metric';

      })

      .sort((a, b) => a.box.top - b.box.top || a.box.left - b.box.left);

    const placed = [];

    movableLayers.forEach((layer) => {

      const current = stageBox(layer.el);

      const desiredCenter = rootBox.top + layer.centerRatioY * rootBox.height;

      const currentCenter = current.top + current.height / 2;

      applyAdaptiveLayerOffset(layer, 0, (desiredCenter - currentCenter) / rootVisualScaleY);

      let box = stageBox(layer.el);

      let extraShift = 0;

      placed.forEach((previous) => {

        // Authored vertical overlap means both layers belong to one row.
        // A horizontal squeeze must not turn that row into a vertical stack.
        if (layer.box.top < previous.layer.box.bottom - 1) return;

        const horizontalOverlap = Math.min(previous.box.right, box.right)

          - Math.max(previous.box.left, box.left);

        if (horizontalOverlap > 1) {

          extraShift = Math.max(

            extraShift,

            previous.box.bottom + GROUP_COLLISION_CLEARANCE - (box.top + extraShift)

          );

        }

      });

      if (extraShift > 0) {

        applyAdaptiveLayerOffset(layer, 0, extraShift / rootVisualScaleY);

        box = stageBox(layer.el);

      }

      placed.push({ layer: layer, box: box });

    });

  }

  function positionAdaptiveGroupLayersX(item) {

    const adaptive = item.adaptive;

    adaptive.layers.forEach((layer) => resetEdgeAnchoredVisualTransform(layer));

    adaptive.layers.forEach((layer) => applyAdaptiveLayerOffset(layer, 0, 0));

    const rootBox = stageBox(item.el);

    const logicalWidth = Math.max(0.01, styleNumber(item.el, 'width', item.before.width));

    const rootVisualScaleX = Math.max(0.01, rootBox.width / logicalWidth);

    adaptive.layers.forEach((layer) => {

      const current = stageBox(layer.el);
      const mode = layer.horizontalAnchorMode || 'center';
      const ratio = Number.isFinite(layer.horizontalAnchorRatioX)
        ? layer.horizontalAnchorRatioX
        : layer.centerRatioX;
      const desiredAnchor = rootBox.left + ratio * rootBox.width;
      const currentAnchor = mode === 'left'
        ? current.left
        : (mode === 'right' ? current.right : current.left + current.width / 2);

      applyAdaptiveLayerOffset(layer, (desiredAnchor - currentAnchor) / rootVisualScaleX, 0);

    });

  }



  function adaptiveTextPaintRect(node) {

    const layoutRect = node.getBoundingClientRect();

    if (!(node.textContent || '').trim()) return layoutRect;

    const range = document.createRange();

    range.selectNodeContents(node);

    const glyphRect = range.getBoundingClientRect();

    return glyphRect.width > 0.5 && glyphRect.height > 0.5 ? glyphRect : layoutRect;

  }



  function adaptiveGroupTextFits(item) {

    const rootRect = item.el.getBoundingClientRect();

    const verticalFlow = item.adaptive.verticalFlow;

    if (verticalFlow) {

      const blockRects = verticalFlow.blocks.map((block) => block.el.getBoundingClientRect()).filter((rect) => (

        rect.width > 0.5 && rect.height > 0.5

      ));

      const blockTolerance = 0.75;

      if (blockRects.some((rect) => (

        rect.top < rootRect.top - blockTolerance

        || rect.bottom > rootRect.bottom + blockTolerance

      ))) return false;

      for (let first = 0; first < blockRects.length; first += 1) {

        for (let second = first + 1; second < blockRects.length; second += 1) {

          const horizontalOverlap = Math.min(blockRects[first].right, blockRects[second].right)

            - Math.max(blockRects[first].left, blockRects[second].left);

          const verticalOverlap = Math.min(blockRects[first].bottom, blockRects[second].bottom)

            - Math.max(blockRects[first].top, blockRects[second].top);

          if (horizontalOverlap > 1 && verticalOverlap > 0.8) return false;

        }

      }

    }

    const textEntries = item.adaptive.textBoxes.map((node) => ({

      node: node,

      rect: adaptiveTextPaintRect(node)

    })).filter((entry) => entry.rect.width > 0.5 && entry.rect.height > 0.5);

    const rects = textEntries.map((entry) => entry.rect);

    const flowBlockIndexes = verticalFlow ? textEntries.map((entry) => (

      verticalFlow.blocks.findIndex((block) => block.el === entry.node || block.el.contains(entry.node))

    )) : [];

    const edgeTolerance = 0.75;

    if (rects.some((rect) => (

      rect.left < rootRect.left - edgeTolerance

      || rect.right > rootRect.right + edgeTolerance

      || rect.top < rootRect.top - edgeTolerance

      || rect.bottom > rootRect.bottom + edgeTolerance

    ))) {

      return false;

    }

    for (let first = 0; first < rects.length; first += 1) {

      for (let second = first + 1; second < rects.length; second += 1) {

        // Separate vertical-flow blocks already have a stricter box-level
        // clearance check above. Font ranges can extend beyond their line box
        // (especially with local CJK fallbacks) and falsely report that two
        // visibly separated blocks collide. Keep glyph collision checks inside
        // the same structural block, where they still protect list rows and
        // nested text members.
        if (verticalFlow

          && flowBlockIndexes[first] >= 0

          && flowBlockIndexes[second] >= 0

          && flowBlockIndexes[first] !== flowBlockIndexes[second]) continue;

        const horizontalOverlap = Math.min(rects[first].right, rects[second].right)

          - Math.max(rects[first].left, rects[second].left);

        const verticalOverlap = Math.min(rects[first].bottom, rects[second].bottom)

          - Math.max(rects[first].top, rects[second].top);

        // Browser line boxes can touch by roughly one CSS pixel even when the

        // painted glyphs do not collide. Treat only material overlap as a

        // typography failure so sub-pixel rounding does not force type to 6px.

        if (horizontalOverlap > 1 && verticalOverlap > 2) return false;

      }

    }

    return true;

  }



  function applyAdaptiveHorizontalGroupResize(item, horizontalScale) {

    const adaptive = item.adaptive;

    const spacingScale = Math.max(0.05, Math.min(horizontalScale, 2));

    const targetRootWidth = Math.max(MIN_SIZE, item.before.width * horizontalScale);

    const contentLeft = adaptive.spacing.paddingLeft * spacingScale;

    const contentRight = targetRootWidth - adaptive.spacing.paddingRight * spacingScale;

    const columnPlans = adaptive.layers.filter((layer) => layer.before.width > 0.5).map((layer) => {
      const lineFloor = layer.textFrame && layer.wrapMetrics
        ? layer.wrapMetrics.minimumLinePreservingWidth
        : 0;
      const width = Math.max(
        MIN_SIZE,
        layer.textFrame && horizontalScale < 1
          ? Math.min(layer.before.width, Math.max(lineFloor, layer.before.width * horizontalScale))
          : layer.before.width * horizontalScale
      );
      const mode = layer.horizontalAnchorMode || 'center';
      const anchor = (Number.isFinite(layer.horizontalAnchorRatioX)
        ? layer.horizontalAnchorRatioX
        : layer.centerRatioX) * targetRootWidth;
      const left = mode === 'left' ? anchor : (mode === 'right' ? anchor - width : anchor - width / 2);
      return { layer: layer, mode: mode, anchor: anchor, width: width, left: left, right: left + width };
    });

    applyVisualScale(item.el, item.visual, 1, 1);

    setUserStyle(item.el, 'width', (Math.round(targetRootWidth * 10) / 10) + 'px');

    setUserStyle(item.el, 'padding-left', (Math.round(adaptive.spacing.paddingLeft * spacingScale * 100) / 100) + 'px');

    setUserStyle(item.el, 'padding-right', (Math.round(adaptive.spacing.paddingRight * spacingScale * 100) / 100) + 'px');

    // Natural wrapping needs vertical breathing room. Consume the authored
    // top/bottom inset before shrinking type so a narrower text frame can
    // become two lines without immediately failing the height check.
    setUserStyle(item.el, 'padding-top', (Math.round(adaptive.spacing.paddingTop * spacingScale * 100) / 100) + 'px');

    setUserStyle(item.el, 'padding-bottom', (Math.round(adaptive.spacing.paddingBottom * spacingScale * 100) / 100) + 'px');

    setUserStyle(item.el, 'column-gap', (Math.round(adaptive.spacing.columnGap * spacingScale * 100) / 100) + 'px');

    adaptive.layers.forEach((layer) => {

      if (layer.before.width > 0.5) {

        let nextWidth = layer.before.width * horizontalScale;

        if (layer.textFrame && horizontalScale < 1) {

          const lanePlans = columnPlans.filter((plan) => {
            if (plan.layer === layer) return true;
            return Math.min(plan.layer.box.bottom, layer.box.bottom)
              - Math.max(plan.layer.box.top, layer.box.top) > 1;
          }).sort((first, second) => first.left - second.left);
          const columnIndex = lanePlans.findIndex((plan) => plan.layer === layer);
          const plan = columnIndex >= 0 ? lanePlans[columnIndex] : null;
          const previous = columnIndex > 0 ? lanePlans[columnIndex - 1] : null;

          const next = columnIndex >= 0 && columnIndex < lanePlans.length - 1
            ? lanePlans[columnIndex + 1]
            : null;

          const leftLimit = previous
            ? Math.max(contentLeft, previous.right + 2)
            : contentLeft;

          const rightLimit = next
            ? Math.min(contentRight, next.left - 2)
            : contentRight;

          const mode = plan ? plan.mode : (layer.horizontalAnchorMode || 'center');
          const anchor = plan ? plan.anchor : layer.centerRatioX * targetRootWidth;
          const availableWidth = Math.max(MIN_SIZE, mode === 'left'
            ? rightLimit - Math.max(leftLimit, anchor)
            : (mode === 'right'
              ? Math.min(rightLimit, anchor) - leftLimit
              : 2 * Math.min(
                Math.max(0, anchor - leftLimit),
                Math.max(0, rightLimit - anchor)
              )));

          const lineFloor = layer.wrapMetrics

            ? layer.wrapMetrics.minimumLinePreservingWidth

            : layer.before.width;

          // Consume the existing left/right breathing room before narrowing a

          // text frame. While the available span can still hold the current

          // line count, a tiny inward drag must not cause an eager wrap.

          nextWidth = availableWidth >= lineFloor

            ? Math.min(layer.before.width, Math.max(lineFloor, availableWidth))

            : availableWidth;

        }

        setUserStyle(layer.el, 'width', (Math.round(Math.max(MIN_SIZE, nextWidth) * 10) / 10) + 'px');

      }

      if (layer.textFrame) setNaturalTextWrap(layer.el);

    });

    return fitAdaptiveTypography(item, positionAdaptiveGroupLayersX, horizontalScale);

  }



  function applyAdaptiveVerticalGroupResize(item, verticalScale) {

    const adaptive = item.adaptive;

    const spacingScale = Math.max(0.05, Math.min(verticalScale, 2));

    const targetRootHeight = Math.max(MIN_SIZE, item.before.height * verticalScale);

    applyVisualScale(item.el, item.visual, 1, 1);

    setUserStyle(item.el, 'height', (Math.round(targetRootHeight * 10) / 10) + 'px');

    setUserStyle(item.el, 'padding-top', (Math.round(adaptive.spacing.paddingTop * spacingScale * 100) / 100) + 'px');

    setUserStyle(item.el, 'padding-bottom', (Math.round(adaptive.spacing.paddingBottom * spacingScale * 100) / 100) + 'px');

    setUserStyle(item.el, 'row-gap', (Math.round(adaptive.spacing.rowGap * spacingScale * 100) / 100) + 'px');

    if (adaptive.verticalFlow) {

      // Structural stacks have real visual blocks in addition to text layers.
      // Repack those blocks first; only once every captured gap reaches its
      // minimum does the solver proportionally reduce type and block heights.
      return applyAdaptiveVerticalFlow(item, targetRootHeight);

    }

    // Side handles first consume padding, gaps and relative layer spacing.

    // Only after the text no longer fits do typography and line-height shrink

    // together. Geometry remains owned by the resize frame: typography may
    // make an inward drag stop at its last fitting size, but it must never
    // grow the module after the frame was already clamped.

    return fitAdaptiveTypography(item, positionAdaptiveGroupLayersY, verticalScale);

  }



  function adaptiveResizeItemsFit(items) {

    return (items || []).every((item) => adaptiveGroupTextFits(item));

  }



  function resolveAdaptiveAxisScale(items, requestedScale, axis) {

    const records = (items || []).filter((item) => item && item.el && item.adaptive);

    if (!records.length) return requestedScale;

    const sizeKey = axis === 'horizontal' ? 'width' : 'height';

    const geometryFloor = records.reduce((floor, item) => (

      Math.max(floor, MIN_SIZE / Math.max(MIN_SIZE, item.before[sizeKey]))

    ), 0);

    const requested = Math.max(geometryFloor, requestedScale);

    const apply = (scale) => {

      records.forEach((item) => {

        if (axis === 'horizontal') applyAdaptiveHorizontalGroupResize(item, scale);

        else applyAdaptiveVerticalGroupResize(item, scale);

      });

    };

    apply(requested);

    if (requested >= 1 || adaptiveResizeItemsFit(records)) return requested;

    // An inward side drag may ask for a frame that no longer contains the

    // minimum readable text. Search back toward the starting geometry and

    // stop at the smallest fitting scale. This keeps resizing monotonic: an

    // inward pointer move can clamp, but it can never make the group grow.

    apply(1);

    if (!adaptiveResizeItemsFit(records)) return 1;

    let invalid = requested;

    let valid = 1;

    for (let index = 0; index < 10; index += 1) {

      const candidate = (invalid + valid) / 2;

      apply(candidate);

      if (adaptiveResizeItemsFit(records)) valid = candidate;

      else invalid = candidate;

    }

    apply(valid);

    return valid;

  }



  function anchoredResizeAxisStart(start, size, nextSize, resizeEdge, centerResize) {

    if (centerResize) return start + (size - nextSize) / 2;

    if (resizeEdge === 'n' || resizeEdge === 'w') return start + size - nextSize;

    return start;

  }



  const GROUP_COLLISION_CLEARANCE = 4;



  function isSemanticGroupResizeItem(item) {

    return !!(item && item.el && item.el.dataset.editStructure === 'module');

  }



  function groupResizeItemsOverlapX(a, b) {

    const aRight = a.box.left + a.box.width;

    const bRight = b.box.left + b.box.width;

    return Math.min(aRight, bRight) - Math.max(a.box.left, b.box.left) > 1;

  }



  function scaledGroupMemberClearance(previous, current, scaleY) {

    const originalGap = current.box.top - (previous.box.top + previous.box.height);

    return Math.max(

      GROUP_COLLISION_CLEARANCE,

      originalGap > 0 ? originalGap * scaleY : 0

    );

  }



  function singleAdaptiveResizePeers(root) {

    const peers = [];

    const seen = new Set();

    const add = (candidate) => {

      if (!candidate || candidate === root || seen.has(candidate)) return;

      if (!candidate.matches || !candidate.matches('.el[data-edit-structure="module"]')) return;

      const style = getComputedStyle(candidate);

      if (style.display === 'none' || style.visibility === 'hidden' || !candidate.getClientRects().length) return;

      seen.add(candidate);

      peers.push(candidate);

    };

    const parent = root && root.parentElement;

    // Collision ownership follows the actual layout container, not a separate
    // repeat-linkage feature. Direct module siblings and modules in sibling
    // layout-only slots share the same resize boundary.
    if (parent) {

      const display = getComputedStyle(parent).display;

      const isLayoutHost = parent.dataset?.editLayoutOnly === 'true'

        || ['grid', 'inline-grid', 'flex', 'inline-flex'].includes(display);

      if (isLayoutHost) {

        Array.from(parent.children).forEach((child) => {

          add(child);

          if (child.dataset?.editLayoutOnly === 'true') Array.from(child.children).forEach(add);

        });

      } else if (parent.parentElement?.dataset?.editLayoutOnly === 'true') {

        Array.from(parent.parentElement.children).forEach((slot) => {

          add(slot);

          Array.from(slot.children || []).forEach(add);

        });

      }

    }

    return peers;

  }



  function clampSingleAdaptiveVerticalResize(item, newTop, newHeight, resizeEdge, centerResize) {

    const root = item && item.el;

    if (!root) return { top: newTop, height: newHeight };

    const startBox = item.box || stageBox(root);

    const content = root.closest('[data-content-area]');

    const contentBox = content ? stageBox(content) : null;

    let minTop = contentBox ? contentBox.top : -Infinity;

    let maxBottom = contentBox ? contentBox.bottom : Infinity;

    singleAdaptiveResizePeers(root).forEach((peer) => {

      const box = stageBox(peer);

      const horizontalOverlap = Math.min(startBox.right, box.right) - Math.max(startBox.left, box.left);

      if (horizontalOverlap <= 1) return;

      if (box.bottom <= startBox.top + 1) {

        minTop = Math.max(minTop, box.bottom + GROUP_COLLISION_CLEARANCE);

      } else if (box.top >= startBox.bottom - 1) {

        maxBottom = Math.min(maxBottom, box.top - GROUP_COLLISION_CLEARANCE);

      }

    });

    if (centerResize) {

      const requestedCenter = newTop + newHeight / 2;

      const requestedHalf = Math.max(MIN_SIZE / 2, newHeight / 2);

      const minCenter = minTop + requestedHalf;

      const maxCenter = maxBottom - requestedHalf;

      if (minCenter <= maxCenter) {

        const center = Math.max(minCenter, Math.min(maxCenter, requestedCenter));

        return { top: center - requestedHalf, height: requestedHalf * 2 };

      }

      const safeHeight = Math.max(MIN_SIZE, maxBottom - minTop);

      return { top: (minTop + maxBottom - safeHeight) / 2, height: safeHeight };

    }

    if (resizeEdge === 'n') {

      const bottom = Math.min(startBox.bottom, maxBottom);

      const top = Math.min(bottom - MIN_SIZE, Math.max(minTop, newTop));

      return { top: top, height: Math.max(MIN_SIZE, bottom - top) };

    }

    const top = Math.max(minTop, newTop);

    const bottom = Math.max(top + MIN_SIZE, Math.min(maxBottom, newTop + newHeight));

    return { top: top, height: Math.max(MIN_SIZE, bottom - top) };

  }



  function clampSingleAdaptiveHorizontalResize(item, newLeft, newWidth, resizeEdge, centerResize) {

    const root = item && item.el;

    if (!root) return { left: newLeft, width: newWidth };

    const startBox = item.box || stageBox(root);

    const content = root.closest('[data-content-area]');

    const contentBox = content ? stageBox(content) : null;

    let minLeft = contentBox ? contentBox.left : -Infinity;

    let maxRight = contentBox ? contentBox.right : Infinity;

    singleAdaptiveResizePeers(root).forEach((peer) => {

      const box = stageBox(peer);

      const verticalOverlap = Math.min(startBox.bottom, box.bottom) - Math.max(startBox.top, box.top);

      if (verticalOverlap <= 1) return;

      if (box.right <= startBox.left + 1) {

        minLeft = Math.max(minLeft, box.right + GROUP_COLLISION_CLEARANCE);

      } else if (box.left >= startBox.right - 1) {

        maxRight = Math.min(maxRight, box.left - GROUP_COLLISION_CLEARANCE);

      }

    });

    if (centerResize) {

      const requestedCenter = newLeft + newWidth / 2;

      const requestedHalf = Math.max(MIN_SIZE / 2, newWidth / 2);

      const minCenter = minLeft + requestedHalf;

      const maxCenter = maxRight - requestedHalf;

      if (minCenter <= maxCenter) {

        const center = Math.max(minCenter, Math.min(maxCenter, requestedCenter));

        return { left: center - requestedHalf, width: requestedHalf * 2 };

      }

      const safeWidth = Math.max(MIN_SIZE, maxRight - minLeft);

      return { left: (minLeft + maxRight - safeWidth) / 2, width: safeWidth };

    }

    if (resizeEdge === 'w') {

      const right = Math.min(startBox.right, maxRight);

      const left = Math.min(right - MIN_SIZE, Math.max(minLeft, newLeft));

      return { left: left, width: Math.max(MIN_SIZE, right - left) };

    }

    const left = Math.max(minLeft, newLeft);

    const right = Math.max(left + MIN_SIZE, Math.min(maxRight, newLeft + newWidth));

    return { left: left, width: Math.max(MIN_SIZE, right - left) };

  }


  function clampGroupResizeToContentArea(items, newLeft, newTop, newWidth, newHeight, resizeEdge, centerResize) {

    const first = items && items.length ? items[0].el : null;

    const content = first ? first.closest('[data-content-area]') : null;

    const contentBox = content ? stageBox(content) : null;

    if (!contentBox) return { left: newLeft, top: newTop, width: newWidth, height: newHeight };

    if (centerResize) {

      const centerX = newLeft + newWidth / 2;

      const centerY = newTop + newHeight / 2;

      const halfW = Math.min(newWidth / 2, contentBox.width / 2);

      const halfH = Math.min(newHeight / 2, contentBox.height / 2);

      const safeCenterX = Math.max(contentBox.left + halfW, Math.min(contentBox.right - halfW, centerX));

      const safeCenterY = Math.max(contentBox.top + halfH, Math.min(contentBox.bottom - halfH, centerY));

      return { left: safeCenterX - halfW, top: safeCenterY - halfH, width: halfW * 2, height: halfH * 2 };

    }

    let left = newLeft;

    let top = newTop;

    let width = newWidth;

    let height = newHeight;

    if (resizeEdge === 'w') {

      const right = Math.min(contentBox.right, newLeft + newWidth);

      left = Math.max(contentBox.left, Math.min(right - MIN_SIZE, newLeft));

      width = Math.max(MIN_SIZE, right - left);

    } else if (resizeEdge === 'e') {

      left = Math.max(contentBox.left, newLeft);

      width = Math.max(MIN_SIZE, Math.min(contentBox.right, newLeft + newWidth) - left);

    } else if (resizeEdge === 'n') {

      const bottom = Math.min(contentBox.bottom, newTop + newHeight);

      top = Math.max(contentBox.top, Math.min(bottom - MIN_SIZE, newTop));

      height = Math.max(MIN_SIZE, bottom - top);

    } else if (resizeEdge === 's') {

      top = Math.max(contentBox.top, newTop);

      height = Math.max(MIN_SIZE, Math.min(contentBox.bottom, newTop + newHeight) - top);

    }

    return { left: left, top: top, width: width, height: height };

  }


  function applyCollisionSafeVerticalGroupResize(items, newTop, newHeight, scaleY, resizeEdge, centerResize) {

    const records = items.map((item) => {

      const desiredTop = newTop + (item.box.top - resizeStartTop) * scaleY;

      setUserStyle(item.el, 'left', item.before.left + 'px');

      setUserStyle(item.el, 'top', (Math.round((item.before.top + desiredTop - item.box.top) * 10) / 10) + 'px');

      applyAdaptiveVerticalGroupResize(item, scaleY);

      return {

        item: item,

        desiredTop: desiredTop,

        top: desiredTop,

        height: stageBox(item.el).height,

        semantic: isSemanticGroupResizeItem(item)

      };

    });



    const semanticRecords = records

      .filter((record) => record.semantic)

      .sort((a, b) => a.item.box.top - b.item.box.top || a.item.box.left - b.item.box.left);



    semanticRecords.forEach((record, index) => {

      let resolvedTop = record.desiredTop;

      for (let priorIndex = 0; priorIndex < index; priorIndex += 1) {

        const previous = semanticRecords[priorIndex];

        if (!groupResizeItemsOverlapX(previous.item, record.item)) continue;

        resolvedTop = Math.max(

          resolvedTop,

          previous.top + previous.height + scaledGroupMemberClearance(previous.item, record.item, scaleY)

        );

      }

      record.top = resolvedTop;

    });



    if (semanticRecords.length > 1) {

      const semanticTop = Math.min.apply(null, semanticRecords.map((record) => record.top));

      const semanticBottom = Math.max.apply(null, semanticRecords.map((record) => record.top + record.height));

      const requestedBottom = newTop + newHeight;

      const requestedCenter = newTop + newHeight / 2;

      const resolvedCenter = (semanticTop + semanticBottom) / 2;

      const shift = centerResize

        ? requestedCenter - resolvedCenter

        : (resizeEdge === 'n' ? requestedBottom - semanticBottom : newTop - semanticTop);



      records.forEach((record) => {

        const resolvedTop = (record.semantic ? record.top : record.desiredTop) + shift;

        setUserStyle(record.item.el, 'top', (Math.round((record.item.before.top + resolvedTop - record.item.box.top) * 10) / 10) + 'px');

      });

    }



    let union = combinedStageBox(items.map((item) => item.el));
    const first = items.length ? items[0].el : null;
    const content = first ? first.closest('[data-content-area]') : null;
    const contentBox = content ? stageBox(content) : null;

    // Adaptive layout can move glyphs and layer centers after the pointer box
    // was clamped. Validate the visible union once more and translate the
    // whole group back inside the Content Area without changing its size.
    if (union && contentBox && union.height <= contentBox.height + 0.75) {
      let shift = 0;
      if (union.top < contentBox.top) shift = contentBox.top - union.top;
      if (union.bottom + shift > contentBox.bottom) shift += contentBox.bottom - (union.bottom + shift);
      if (Math.abs(shift) > 0.05) {
        records.forEach((record) => {
          const top = styleNumber(record.item.el, 'top', record.item.before.top);
          setUserStyle(record.item.el, 'top', (Math.round((top + shift) * 10) / 10) + 'px');
        });
        union = combinedStageBox(items.map((item) => item.el));
      }
    }

    return union;

  }

  function updatePeerAdvisory() {

    const summary = selectedFontSummary();

    if (!peerAdvisoryRow || summary.targets.length !== 1 || !summary.primary) {

      if (peerAdvisoryRow) peerAdvisoryRow.style.display = 'none';

      return;

    }

    const peers = findPeers(summary.primary);

    const current = Math.round(getCurrentFontSize(summary.primary));

    const mismatched = peers.filter((peer) => Math.round(getCurrentFontSize(peer)) !== current);

    if (!mismatched.length) {

      peerAdvisoryRow.style.display = 'none';

      return;

    }

    const sizes = Array.from(new Set(mismatched.map((peer) => Math.round(getCurrentFontSize(peer)) + 'px'))).join(' / ');

    peerAdvisoryText.textContent = t(M.fontPeerMismatch, {

      current: current,

      count: mismatched.length,

      sizes: sizes

    });

    peerAdvisoryRow.style.display = 'flex';

  }



  const FONT_FAMILY_CHOICES = [

    { label: '思源黑體 / Noto Sans TC', value: '"Noto Sans TC", "Microsoft JhengHei", system-ui, sans-serif', googleFamily: 'Noto Sans TC', googleWeights: '400;500;600;700;800;900' },

    { label: '思源宋體 / Noto Serif TC', value: '"Noto Serif TC", "PMingLiU", serif', googleFamily: 'Noto Serif TC', googleWeights: '400;500;600;700;800;900' },

    { label: 'Chiron GoRound TC', value: '"Chiron GoRound TC", "Noto Sans TC", sans-serif', googleFamily: 'Chiron GoRound TC', googleWeights: '200;300;400;500;600;700;800;900' }

  ];



  function primaryFontFamily(value) {

    return String(value || '').split(',')[0].trim().replace(/^['"]|['"]$/g, '').toLowerCase();

  }



  function matchingFontChoice(value) {

    const primary = primaryFontFamily(value);

    return FONT_FAMILY_CHOICES.find((choice) => primaryFontFamily(choice.value) === primary) || null;

  }



  const editorGoogleFontLinks = new Set();



  function ensureEditorGoogleFontLoaded(value) {

    const choice = matchingFontChoice(value);

    if (!choice || !choice.googleFamily || typeof document === 'undefined') return Promise.resolve();

    const key = choice.googleFamily;

    if (editorGoogleFontLinks.has(key)) return Promise.resolve();

    const link = document.createElement('link');

    const family = encodeURIComponent(choice.googleFamily).replace(/%20/g, '+');

    link.rel = 'stylesheet';

    link.href = 'https://fonts.googleapis.com/css2?family=' + family + ':wght@' + choice.googleWeights + '&display=swap';

    link.dataset.editorFontFamily = key;

    editorGoogleFontLinks.add(key);

    document.head.appendChild(link);

    return new Promise((resolve) => {

      let settled = false;

      const finish = () => {

        if (settled) return;

        settled = true;

        resolve();

      };

      link.addEventListener('load', finish, { once: true });

      link.addEventListener('error', finish, { once: true });

      window.setTimeout(finish, 1800);

    });

  }



  function populateFontFamilySelect(select, includePreset) {

    if (!select) return;

    select.innerHTML = '';

    const mixed = document.createElement('option');

    mixed.value = '__mixed__';

    mixed.textContent = M.fontFamilyMixed;

    mixed.disabled = true;

    mixed.hidden = true;

    select.appendChild(mixed);

    FONT_FAMILY_CHOICES.forEach((choice) => {

      const option = document.createElement('option');

      option.value = choice.value;

      option.textContent = choice.label;

      select.appendChild(option);

    });

  }



  function setFontFamilySelectValue(select, value, fallbackLabel) {

    if (!select) return;

    Array.from(select.querySelectorAll('option[data-dynamic-font]')).forEach((option) => option.remove());

    if (Array.from(select.options).some((option) => option.value === value)) {

      select.value = value;

      return;

    }

    const choice = matchingFontChoice(value);

    if (choice) {

      select.value = choice.value;

      return;

    }

    const mixedOption = Array.from(select.options).find((option) => option.value === '__mixed__');

    if (mixedOption) {

      select.value = '__mixed__';

      return;

    }

    select.value = FONT_FAMILY_CHOICES[0].value;

  }



  function selectedFontFamilySummary() {

    const targets = selectedTextTargets();

    const families = targets.map((el) => getComputedStyle(el).fontFamily || '');

    const unique = Array.from(new Set(families.map(primaryFontFamily)));

    return {

      targets: targets,

      family: families[0] || '',

      mixed: unique.length > 1,

      inherited: targets.length > 0 && targets.every((el) => !el.style.fontFamily)

    };

  }



  function queueFontReadyRefresh(value) {

    const primary = primaryFontFamily(value);

    const ready = ensureEditorGoogleFontLoaded(value).then(() => (

      document.fonts && primary

        ? document.fonts.load('16px "' + primary.replace(/"/g, '') + '"').catch(() => null)

        : null

    ));

    Promise.resolve(ready).then(() => {

      scheduleSelectionRefresh();

      scheduleThumbnailRefresh();

    });

  }



  function applySelectedFontFamily(value) {

    if (value === '__mixed__') return;

    const targets = selectedTextTargets();

    if (!targets.length || dragEl || resizeEl) return;

    const family = value === '__preset__' ? '' : value;

    if (runSnapshotBatch(M.fontFamilyChange, targets, (items) => {

      items.forEach((el) => setUserStyle(el, 'font-family', family));

    })) {

      queueFontReadyRefresh(family || getComputedStyle(targets[0]).fontFamily);

    }

  }



  function setDeckDefaultFont(value) {

    if (value === '__mixed__') return;

    commitPendingChanges();

    const before = deckFontState();

    const family = value === '__preset__' ? '' : value;

    const after = DECK_FONT_PROPERTIES.reduce((state, property) => {

      state[property] = family;

      return state;

    }, {});

    applyDeckFontState(after);

    pushCommand({ type: 'deck-font', label: M.defaultFontChange, before: before, after: deckFontState() });

    updateAppearanceControls();

    updateFontControls();

    scheduleDraftSave();

    scheduleThumbnailRefresh();

    queueFontReadyRefresh(family || getComputedStyle(document.body).fontFamily);

    showTransientReadout(M.defaultFontChange, 1200);

  }



  function setActiveSlideBackground(color) {

    const slide = document.querySelector('.slide.active');

    if (!slide || !slide.id) return;

    commitPendingChanges();

    const before = { backgroundColor: slide.style.backgroundColor || '' };

    if (color) slide.style.backgroundColor = color;

    else slide.style.removeProperty('background-color');

    const after = { backgroundColor: slide.style.backgroundColor || '' };

    pushCommand({

      type: 'slide-background',

      label: M.slideBackgroundChange,

      slideId: slide.id,

      before: before,

      after: after

    });

    lastPaletteSignature = null;

    updateAppearanceControls();

    refreshColorSwatches();

    scheduleDraftSave();

    scheduleThumbnailRefresh();

    showTransientReadout(M.slideBackgroundChange, 1200);

  }



  function beginPendingSlideMaskChange(slide) {

    if (!slide || !slide.id) return false;

    if (pendingSlideMaskCommand && pendingSlideMaskCommand.slideId !== slide.id) commitPendingChanges();

    if (!pendingSlideMaskCommand) {

      pendingSlideMaskCommand = {

        type: 'slide-mask',

        label: M.slideMaskChange,

        slideId: slide.id,

        before: slideMaskState(slide),

        after: null

      };

    }

    return true;

  }



  function updateSlideMaskFromControls(commit) {

    const slide = document.querySelector('.slide.active');

    if (!slide || !slide.id || !slideMaskColorInput || !slideMaskOpacityRange || !editMode) return;

    if (!beginPendingSlideMaskChange(slide)) return;

    const color = slideMaskColorInput.value || DEFAULT_SLIDE_MASK_COLOR;

    const opacity = slideMaskOpacity(Number(slideMaskOpacityRange.value) / 100);

    applySlideMaskState(slide, { color: color, opacity: opacity });

    if (slideMaskOpacityValue) slideMaskOpacityValue.textContent = Math.round(opacity * 100) + '%';

    scheduleDraftSave();

    scheduleThumbnailRefresh();

    if (commit) {

      commitPendingChanges();

      showTransientReadout(M.slideMaskChange, 1000);

    }

  }



  function resetActiveSlideMask() {

    const slide = document.querySelector('.slide.active');

    if (!slide || !slide.id || !editMode) return;

    commitPendingChanges();

    if (!beginPendingSlideMaskChange(slide)) return;

    applySlideMaskState(slide, { color: DEFAULT_SLIDE_MASK_COLOR, opacity: DEFAULT_SLIDE_MASK_OPACITY });

    commitPendingChanges();

    updateAppearanceControls();

    scheduleDraftSave();

    scheduleThumbnailRefresh();

    showTransientReadout(M.slideMaskReset, 1200);

  }



  function updateFontControls() {

    if (!fontControlRow) return;

    const summary = selectedFontSummary();

    const familySummary = selectedFontFamilySummary();

    const canEditFont = editMode && familySummary.targets.length > 0;

    const canEditSize = editMode && summary.targets.length > 0;

    fontControlRow.style.display = 'flex';

    if (!canEditFont) {

      setToolbarRowAvailability(fontControlRow, false);

      if (peerAdvisoryRow) peerAdvisoryRow.style.display = 'none';

      return;

    }

    setToolbarRowAvailability(fontControlRow, true);

    const busy = !!(dragEl || resizeEl);

    const size = summary.primary ? Math.round(getCurrentFontSize(summary.primary)) : 0;

    if (document.activeElement !== fontSizeInput) fontSizeInput.value = summary.primary ? String(size) + (summary.mixed ? '+' : '') : '';

    if (fontSizeRange && document.activeElement !== fontSizeRange) fontSizeRange.value = summary.primary && !summary.mixed ? String(Math.max(8, Math.min(240, size))) : '96';

    fontSizeInput.dataset.mixed = summary.mixed ? 'true' : 'false';

    fontSizeInput.disabled = busy || !canEditSize;

    if (fontSizeRange) fontSizeRange.disabled = busy || !canEditSize || summary.mixed;

    fontMinusBtn.disabled = busy || !canEditSize;

    fontPlusBtn.disabled = busy || !canEditSize;

    if (fontFamilySelect && document.activeElement !== fontFamilySelect) {

      if (familySummary.mixed) setFontFamilySelectValue(fontFamilySelect, '__mixed__');

      else if (familySummary.inherited) setFontFamilySelectValue(
        fontFamilySelect,
        familySummary.family || FONT_FAMILY_CHOICES[0].value,
        primaryFontFamily(familySummary.family) || FONT_FAMILY_CHOICES[0].label
      );

      else setFontFamilySelectValue(fontFamilySelect, familySummary.family, primaryFontFamily(familySummary.family));

    }

    if (fontFamilySelect) fontFamilySelect.disabled = busy;

    const cs = getComputedStyle(summary.primary || familySummary.targets[0]);

    const detailed = canEditSize && summary.targets.length === 1;

    if (lineHeightInput) {

      const lh = parseFloat(cs.lineHeight);

      if (document.activeElement !== lineHeightInput) lineHeightInput.value = Number.isNaN(lh) ? '' : String(Math.round(lh));

      if (lineHeightRange && document.activeElement !== lineHeightRange) lineHeightRange.value = Number.isNaN(lh) ? '104' : String(Math.max(24, Math.min(220, Math.round(lh))));

      lineHeightInput.disabled = busy || !detailed;

      if (lineHeightRange) lineHeightRange.disabled = busy || !detailed;

      lineHeightInput.style.display = '';

      lineHeightInput.style.opacity = detailed ? '1' : '.35';

      if (lineHeightInput.previousElementSibling) lineHeightInput.previousElementSibling.style.display = '';

    }

    if (letterSpacingInput) {

      const ls = parseFloat(cs.letterSpacing);

      if (document.activeElement !== letterSpacingInput) letterSpacingInput.value = String(Number.isNaN(ls) ? 0 : Math.round(ls * 10) / 10);

      if (letterSpacingRange && document.activeElement !== letterSpacingRange) letterSpacingRange.value = String(Number.isNaN(ls) ? 0 : Math.max(-20, Math.min(40, Math.round(ls * 10) / 10)));

      letterSpacingInput.disabled = busy || !detailed;

      if (letterSpacingRange) letterSpacingRange.disabled = busy || !detailed;

      letterSpacingInput.style.display = '';

      letterSpacingInput.style.opacity = detailed ? '1' : '.35';

      if (letterSpacingInput.previousElementSibling) letterSpacingInput.previousElementSibling.style.display = '';

    }

    fontControlRow.style.opacity = busy ? '.55' : '1';

    updatePeerAdvisory();

  }



  function commitPendingChanges() {

    if (nudgeTimer) {

      clearTimeout(nudgeTimer);

      nudgeTimer = null;

    }

    if (pendingNudgeCommand) {

      const command = pendingNudgeCommand;

      pendingNudgeCommand = null;

      command.items.forEach((item) => {

        item.after = measureElementState(item.el);

      });

      pushCommand(command);

    }

    if (pendingFontCommand) {

      pendingFontCommand.after = measureElementState(pendingFontCommand.el);

      pushCommand(pendingFontCommand);

      pendingFontCommand = null;

    }

    if (pendingFontBatchCommand) {

      const command = pendingFontBatchCommand;

      pendingFontBatchCommand = null;

      command.items.forEach((item) => {

        item.after = measureElementState(item.el);

      });

      pushCommand(command);

    }

    if (pendingSlideMaskCommand) {

      const command = pendingSlideMaskCommand;

      pendingSlideMaskCommand = null;

      const slide = command.slideId ? document.getElementById(command.slideId) : null;

      if (slide) {

        command.after = slideMaskState(slide);

        pushCommand(command);

      }

    }

  }



  function beginPendingFontChange(el) {

    if (pendingFontBatchCommand) commitPendingChanges();

    if (pendingFontCommand && (pendingFontCommand.el !== el || pendingFontCommand.type !== 'resize')) commitPendingChanges();

    if (!pendingFontCommand) {

      ensureOriginalGeometry(el);

      pendingFontCommand = {

        type: 'resize',

        el: el,

        key: elementKey(el),

        before: measureElementState(el),

        after: null

      };

    }

  }



  function beginPendingFontBatchChange(targets) {

    if (pendingFontCommand) commitPendingChanges();

    const roots = Array.from(new Set((targets || []).filter(Boolean)));

    if (pendingFontBatchCommand) {

      const same = pendingFontBatchCommand.items.length === roots.length &&

        pendingFontBatchCommand.items.every((item, index) => item.el === roots[index]);

      if (!same) commitPendingChanges();

    }

    if (!pendingFontBatchCommand) {

      roots.forEach(ensureOriginalGeometry);

      pendingFontBatchCommand = {

        type: 'batch',

        label: M.fontSizeLabel + ' ' + t(M.multiSelected, { count: roots.length }),

        itemType: 'resize',

        items: roots.map((el) => ({ type: 'resize', el: el, key: elementKey(el), before: measureElementState(el), after: null }))

      };

    }

  }



  function beginPendingStyleChange(el) {

    if (pendingFontBatchCommand) commitPendingChanges();

    if (pendingFontCommand && (pendingFontCommand.el !== el || pendingFontCommand.type !== 'style')) commitPendingChanges();

    if (!pendingFontCommand) {

      ensureOriginalGeometry(el);

      pendingFontCommand = {

        type: 'style',

        el: el,

        key: elementKey(el),

        before: measureElementState(el),

        after: null

      };

    }

  }



  function beginPendingNudge(targets) {

    if (pendingNudgeCommand) {

      const same = pendingNudgeCommand.items.length === targets.length &&

        pendingNudgeCommand.items.every((item, i) => item.el === targets[i]);

      if (!same) commitPendingChanges();

    }

    if (!pendingNudgeCommand) {

      pendingNudgeCommand = {

        type: 'batch',

        label: M.moveChange + ' ' + (targets.length > 1 ? t(M.multiSelected, { count: targets.length }) : elementLabel(targets[0])),

        itemType: 'move',

        items: targets.map((el) => ({

          type: 'move',

          el: el,

          key: elementKey(el),

          before: measureElementState(el),

          after: null

        }))

      };

    }

  }



  function nudgeSelection(key, step) {

    const targets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!targets.length) return;

    const dx = key === 'ArrowLeft' ? -step : (key === 'ArrowRight' ? step : 0);

    const dy = key === 'ArrowUp' ? -step : (key === 'ArrowDown' ? step : 0);

    beginPendingNudge(targets);

    targets.forEach((el) => {

      ensureOriginalGeometry(el);

      setUserStyle(el, 'left', (Math.round((styleNumber(el, 'left', el.offsetLeft) + dx) * 10) / 10) + 'px');

      setUserStyle(el, 'top', (Math.round((styleNumber(el, 'top', el.offsetTop) + dy) * 10) / 10) + 'px');

      recordChange(el);

    });

    repositionHandles();

    scheduleDraftSave();

    if (nudgeTimer) clearTimeout(nudgeTimer);

    nudgeTimer = setTimeout(commitPendingChanges, 700);

    if (selectedEl) {

      const state = measureElementState(selectedEl);

      showTransientReadout(elementLabel(selectedEl) + ' left ' + state.left + 'px, top ' + state.top + 'px', 1200);

    }

  }



  function setFontSizeKeepingLineHeight(el, size) {

    const currentBaseSize = getBaseFontSize(el);

    const visualScale = getElementVisualScale(el) || 1;

    const nextBaseSize = size / visualScale;

    const lh = parseFloat(getComputedStyle(el).lineHeight);

    setUserStyle(el, 'font-size', (Math.round(nextBaseSize * 10) / 10) + 'px');

    if (!Number.isNaN(lh) && currentBaseSize > 0) {

      setUserStyle(el, 'line-height', (Math.round((lh / currentBaseSize) * nextBaseSize * 10) / 10) + 'px');

    }

  }



  function fitTextFrameAfterFontChange(el, beforeState, previousFontSize, nextFontSize) {

    if (!el || !beforeState || !el.dataset || el.dataset.editFit !== 'text') return;

    if (el.dataset.editFrameWidth === 'manual') {

      fitManualFrameHeight(el);

      return;

    }

    const ratio = previousFontSize > 0 ? nextFontSize / previousFontSize : 1;

    if (!Number.isFinite(ratio) || ratio <= 0) return;

    const keepManualHeight = el.dataset.editFrameHeight === 'manual';

    const manualHeight = keepManualHeight ? beforeState.height : null;



    const activeSlide = el.closest('.slide');

    const contentArea = activeSlide && activeSlide.querySelector('[data-content-area]');

    const bounds = stageBox(contentArea || activeSlide || stage);

    const beforeBox = stageBox(el);

    const align = getComputedStyle(el).textAlign;

    const centered = align === 'center';

    const rightAnchored = align === 'right' || align === 'end';

    let availableWidth;

    if (centered) {

      const center = beforeBox.left + beforeBox.width / 2;

      availableWidth = Math.max(MIN_SIZE, 2 * Math.min(center - bounds.left, bounds.right - center));

    } else if (rightAnchored) {

      availableWidth = Math.max(MIN_SIZE, beforeBox.right - bounds.left);

    } else {

      availableWidth = Math.max(MIN_SIZE, bounds.right - beforeBox.left);

    }



    // Scaling the frame width by the same ratio as the font preserves the

    // current line structure.  Only the real Content Area boundary is allowed

    // to cap it; once capped, normal browser wrapping takes over.

    const desiredWidth = Math.max(MIN_SIZE, beforeState.width * ratio);

    const width = Math.min(desiredWidth, availableWidth);

    const delta = width - beforeState.width;

    let left = beforeState.left;

    if (centered) left -= delta / 2;

    else if (rightAnchored) left -= delta;



    setUserStyle(el, 'left', (Math.round(left * 10) / 10) + 'px');

    setUserStyle(el, 'width', (Math.round(width * 10) / 10) + 'px');

    setUserStyle(el, 'max-width', 'none');

    setUserStyle(el, 'height', 'auto');

    const cs = getComputedStyle(el);

    const metrics = measuredTextLineMetrics(el, cs);

    const paddingY = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);

    const height = Math.max(MIN_SIZE, Math.ceil(Math.max(metrics.visualHeight, metrics.lineHeight * metrics.lineCount) + paddingY));

    setUserStyle(el, 'height', (keepManualHeight ? manualHeight : height) + 'px');

  }



  function applyFontSizeValue(el, newSize, options) {

    if (!el || !hasOwnUniformFontSize(el)) return;

    const size = Math.max(1, parseFloat(newSize) || 1);

    if (options && options.mergeUndo) beginPendingFontChange(el);

    else ensureOriginalGeometry(el);

    const before = measureElementState(el);

    const previousSize = getCurrentFontSize(el);

    setFontSizeKeepingLineHeight(el, size);

    fitTextFrameAfterFontChange(el, before, previousSize, size);

    recordChange(el);

    if (selectedEl === el) repositionHandles();

    updateFontControls();

    scheduleDraftSave();

  }



  function applySelectedFontSizeValue(newSize, options) {

    const summary = selectedFontSummary();

    if (!summary.targets.length || dragEl || resizeEl) return;

    const delta = options && Number.isFinite(options.delta) ? options.delta : null;

    if (summary.targets.length > 1) beginPendingFontBatchChange(summary.targets);

    else if (options && options.mergeUndo) beginPendingFontChange(summary.targets[0]);

    summary.targets.forEach((el) => {

      ensureOriginalGeometry(el);

      const before = measureElementState(el);

      const previousSize = getCurrentFontSize(el);

      const size = delta === null ? Math.max(1, parseFloat(newSize) || 1) : Math.max(1, getCurrentFontSize(el) + delta);

      setFontSizeKeepingLineHeight(el, size);

      fitTextFrameAfterFontChange(el, before, previousSize, size);

      recordChange(el);

    });

    scheduleSelectionRefresh();

    updateFontControls();

    scheduleDraftSave();

  }



  function fitManualFrameHeight(el) {

    if (!el) return;

    setNaturalTextWrap(el);

    setUserStyle(el, 'max-width', 'none');

    if (el.dataset && el.dataset.editFrameHeight === 'manual') return;

    setUserStyle(el, 'height', 'auto');

    const range = document.createRange();

    range.selectNodeContents(el);

    const rect = range.getBoundingClientRect();

    const scale = getScale() || 1;

    const cs = getComputedStyle(el);

    const paddingY = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);

    const height = Math.max(MIN_SIZE, Math.ceil(rect.height / scale + paddingY));

    setUserStyle(el, 'height', height + 'px');

  }



  function adjustSelectedFont(delta) {

    const summary = selectedFontSummary();

    if (!summary.targets.length || dragEl || resizeEl) return;

    applySelectedFontSizeValue(null, { mergeUndo: true, delta: delta });

    const updated = selectedFontSummary();

    const size = updated.primary ? Math.round(getCurrentFontSize(updated.primary)) : 0;

    showTransientReadout(M.fontSizeLabel + ' ' + size + (updated.mixed ? '+' : '') + 'px', 900);

  }



  function applyFontToPeers() {

    if (!selectedEl || !isTextEditableElement(selectedEl) || !hasOwnUniformFontSize(selectedEl)) return;

    const peers = findPeers(selectedEl);

    const targetSize = getCurrentFontSize(selectedEl);

    let changedCount = 0;

    peers.forEach((peer) => {

      if (Math.abs(getCurrentFontSize(peer) - targetSize) <= 0.5) return;

      const before = measureElementState(peer);

      ensureOriginalGeometry(peer);

      const previousSize = getCurrentFontSize(peer);

      setFontSizeKeepingLineHeight(peer, targetSize);

      fitTextFrameAfterFontChange(peer, before, previousSize, targetSize);

      recordChange(peer);

      pushCommand({

        type: 'resize',

        el: peer,

        key: elementKey(peer),

        before: before,

        after: measureElementState(peer)

      });

      changedCount += 1;

    });

    updatePeerAdvisory();

    scheduleDraftSave();

    if (changedCount) showTransientReadout(t(M.fontPeerApplied, { count: changedCount }));

  }



  function pushBatch(label, itemType, mutator) {

    const targets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!targets.length) return;

    if (textEditingEl) endTextEdit();

    commitPendingChanges();

    targets.forEach((el) => ensureOriginalGeometry(el));

    const before = targets.map((el) => ({ type: itemType, el: el, key: elementKey(el), before: measureElementState(el) }));

    mutator(targets);

    const items = before.map((item) => {

      item.after = measureElementState(item.el);

      return item;

    });

    pushCommand({

      type: 'batch',

      label: label,

      itemType: itemType,

      items: items

    });

    targets.forEach((el) => recordChange(el));

    repositionHandles();

    updateSelectionBadge();

    scheduleDraftSave();

  }



  function pushStyleBatch(label, mutator) {

    pushBatch(label, 'style', mutator);

  }



  function runSnapshotBatch(label, elements, mutator) {

    const targets = Array.from(new Set(Array.from(elements || []).filter((el) => el && document.contains(el))));

    if (!targets.length || typeof mutator !== 'function') return false;

    if (textEditingEl) endTextEdit();

    commitPendingChanges();

    targets.forEach((el) => ensureOriginalGeometry(el));

    const items = targets.map((el) => ({

      type: 'snapshot',

      el: el,

      key: elementKey(el),

      before: measureSnapshotState(el)

    }));

    mutator(targets);

    items.forEach((item) => {

      item.after = measureSnapshotState(item.el);

    });

    pushCommand({

      type: 'batch',

      label: label || '重新套用 Layout',

      itemType: 'snapshot',

      items: items

    });

    targets.forEach((el) => recordChange(el));

    repositionHandles();

    updateSelectionBadge();

    scheduleDraftSave();

    return true;

  }



  function groupSelection() {

    clearGroupEditScopes();

    const rawTargets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    const selectionBefore = captureSelectionSnapshot();

    const historyDepthBefore = undoStack.length;

    const rawRoots = Array.from(new Set(rawTargets.map(editableRoot))).filter(Boolean);

    const generatedRoot = rawRoots.length === 1 && isCompositeRoot(rawRoots[0]) && !isGeneratedGroup(rawRoots[0])

      ? rawRoots[0]

      : null;

    if (generatedRoot) {

      setSelection([generatedRoot], generatedRoot);

      pushStyleBatch(M.groupChange, (els) => {

        els.forEach((el) => delete el.dataset.editGroupState);

      });

      setSelection([generatedRoot], generatedRoot);

      currentTool = 'move';

      attachSelectionHistoryTransition(historyDepthBefore, selectionBefore, captureSelectionSnapshot());

      applyEditableState();

      repositionHandles();

      showTransientReadout(t(M.generatedGroupRegrouped, { count: generatedGroupCount(generatedRoot) }));

      return;

    }

    const targets = Array.from(new Set(rawTargets.map(editableRoot))).filter((el) => el && getComputedStyle(el).display !== 'none');

    if (targets.length < 2) {

      showTransientReadout(M.needMultiSelect);

      return;

    }

    const slide = targets[0].closest('.slide');

    if (!slide || targets.some((el) => el.closest('.slide') !== slide)) return;

    const id = newGroupId();

    setSelection(targets, targets[0]);

    pushStyleBatch(M.groupChange, (els) => {

      els.forEach((el) => {

        setGroupPath(el, groupPath(el).concat(id));

      });

    });

    setSelection(targets, targets[0], id);

    currentTool = 'move';

    attachSelectionHistoryTransition(historyDepthBefore, selectionBefore, captureSelectionSnapshot());

    applyEditableState();

    repositionHandles();

    showTransientReadout(t(M.grouped, { count: targets.length }));

  }



  function editPrimaryGroupMember() {

    const primary = editableRoot(selectedEl) || activeSelectedEls().map(editableRoot).filter(Boolean)[0];

    const generatedSelected = !!(primary

      && selectedEl === primary

      && activeSelectedEls().length === 1

      && isGeneratedGroup(primary));

    const manualSelected = !!(primary && selectedGroupId);

    if (!generatedSelected && !manualSelected) {

      showTransientReadout(M.needGroup);

      return;

    }

    const currentScope = currentGroupEditScope();

    const alreadyEditingSelectedGroup = !!(currentScope && (

      (generatedSelected && currentScope.kind === 'generated' && currentScope.group === primary)

      || (manualSelected && currentScope.kind === 'manual' && currentScope.groupId === selectedGroupId)

    ));

    if (!alreadyEditingSelectedGroup) {

      groupEditScopes.push(generatedSelected

        ? { kind: 'generated', group: primary }

        : { kind: 'manual', primary: primary, groupId: selectedGroupId });

    }

    currentTool = 'move';

    applyEditableState();

    scheduleSelectionRefresh();

    showTransientReadout(M.groupMemberPickHint);

  }



  function selectWholeGroup() {

    const scope = currentGroupEditScope();

    if (!scope) {

      showTransientReadout(M.needGroup);

      return;

    }

    groupEditScopes.pop();

    if (scope.kind === 'generated') {

      setSelection([scope.group], scope.group);

    } else {

      const members = groupMembers(scope.primary, scope.groupId);

      setSelection(members, scope.primary, scope.groupId);

    }

    currentTool = 'move';

    applyEditableState();

    scheduleSelectionRefresh();

    showTransientReadout(M.groupHint);

  }



  function updateGroupControls() {

    if (!groupToolRow) return;

    const targets = activeSelectedEls().map(editableRoot).filter(Boolean);

    const primary = editableRoot(selectedEl);

    const hasSelectedGeneratedGroup = targets.length === 1 && selectedEl === primary && isGeneratedGroup(primary);

    const hasSelectedGroup = !!selectedGroupId || hasSelectedGeneratedGroup;

    const activeScope = currentGroupEditScope();

    const selectedGroupIsActiveScope = !!(activeScope && (

      (hasSelectedGeneratedGroup && activeScope.kind === 'generated' && activeScope.group === primary)

      || (selectedGroupId && activeScope.kind === 'manual' && activeScope.groupId === selectedGroupId)

    ));

    const canRegroupGenerated = targets.length === 1 && primary && isCompositeRoot(primary) && !isGeneratedGroup(primary);

    const canCreateGroup = targets.length > 1 || canRegroupGenerated;

    const canEditGroup = hasSelectedGroup && !selectedGroupIsActiveScope;

    const canSelectWhole = !!activeScope;

    groupToolRow.style.display = 'flex';

    [groupBtn, ungroupBtn, editGroupMemberBtn, selectWholeGroupBtn].forEach((btn) => {

      if (btn) btn.style.display = 'inline-flex';

    });

    setControlAvailability(groupBtn, canCreateGroup);

    setControlAvailability(ungroupBtn, hasSelectedGroup);

    setControlAvailability(editGroupMemberBtn, canEditGroup);

    setControlAvailability(selectWholeGroupBtn, canSelectWhole);

    groupToolRow.style.opacity = (hasSelectedGroup || canCreateGroup || canSelectWhole) ? '1' : '.35';

  }



  function ungroupSelection() {

    clearGroupEditScopes();

    const roots = Array.from(new Set(selectedTargets().map(editableRoot))).filter((el) => el && getComputedStyle(el).display !== 'none');

    const selectionBefore = captureSelectionSnapshot();

    const historyDepthBefore = undoStack.length;

    if (!roots.length) {

      showTransientReadout(M.needGroup);

      return;

    }

    let id = selectedGroupId;

    const generatedRoot = !id && roots.length === 1 && isGeneratedGroup(roots[0]) ? roots[0] : null;

    if (generatedRoot) {

      setSelection([generatedRoot], generatedRoot);

      const members = generatedGroupMembers(generatedRoot);

      runSnapshotBatch(M.ungroupChange, [generatedRoot].concat(members), () => {

        generatedRoot.dataset.editGroupState = 'ungrouped';

        materializeUngroupedLayerGeometry(generatedRoot, members);

      });

      const primaryMember = members.find((member) => {

        const layer = member.dataset ? member.dataset.editLayer : '';

        return layer === 'text' || layer === 'metric';

      }) || members[0] || null;

      setSelection(members, primaryMember, null, selectedGroupDepth);

      currentTool = 'move';

      attachSelectionHistoryTransition(historyDepthBefore, selectionBefore, captureSelectionSnapshot());

      applyEditableState();

      repositionHandles();

      showTransientReadout(t(M.ungrouped, { count: members.length || 1 }));

      return;

    }

    if (!id) {

      const firstPath = groupPath(roots[0]);

      const common = firstPath.filter((candidate) => roots.every((el) => groupPath(el).indexOf(candidate) >= 0));

      id = common.length ? common[common.length - 1] : '';

    }

    if (!id) {

      showTransientReadout(M.needGroup);

      return;

    }

    const depth = groupPath(roots[0]).indexOf(id);

    const members = groupMembers(roots[0], id);

    setSelection(members, members[0], id);

    pushStyleBatch(M.ungroupChange, (els) => {

      els.forEach((el) => setGroupPath(el, groupPath(el).filter((group) => group !== id)));

    });

    setSelection(members, members[0], null, Math.max(-1, depth - 1));

    currentTool = 'move';

    attachSelectionHistoryTransition(historyDepthBefore, selectionBefore, captureSelectionSnapshot());

    applyEditableState();

    repositionHandles();

    showTransientReadout(t(M.ungrouped, { count: members.length }));

  }



  function selectionCanUngroup() {

    const targets = activeSelectedEls().map(editableRoot).filter(Boolean);

    const primary = editableRoot(selectedEl);

    const hasSelectedGeneratedGroup =

      targets.length === 1 && selectedEl === primary && isGeneratedGroup(primary);

    return !!selectedGroupId || hasSelectedGeneratedGroup;

  }



  function selectionCanGroup() {

    const targets = activeSelectedEls().map(editableRoot).filter(Boolean);

    const primary = editableRoot(selectedEl);

    const canRegroupGenerated =

      targets.length === 1 && primary && isCompositeRoot(primary) && !isGeneratedGroup(primary);

    return targets.length > 1 || canRegroupGenerated;

  }



  function selectContextTarget(target) {

    const root = editableRoot(target);

    if (!root) return false;

    const selectedRoots = activeSelectedEls().map(editableRoot).filter(Boolean);

    // Right-clicking any member of the current selection must preserve the

    // whole multi-selection. Otherwise the context menu silently collapses

    // back to one object and "Group" can never become available.

    if (selectedRoots.indexOf(root) >= 0) return true;

    if (isGeneratedGroup(root)) {

      setSelection([root], root);

    } else {

      const path = groupPath(root);

      const id = path.length ? path[path.length - 1] : '';

      const members = id ? groupMembers(root, id) : [root];

      setSelection(members, root, id || null, id ? path.indexOf(id) : -1);

    }

    currentTool = 'move';

    applyEditableState();

    scheduleSelectionRefresh();

    return selectionCanUngroup();

  }



  function hideObjectContextMenu() {

    if (!objectContextMenu) return;

    objectContextMenu.style.display = 'none';

    objectContextMenu.setAttribute('aria-hidden', 'true');

  }



  function showObjectContextMenu(clientX, clientY) {

    if (!objectContextMenu) return;

    const hasSelection = selectedTargets().length > 0;

    [contextDuplicateBtn, contextBringFrontBtn, contextSendBackBtn, contextDeleteBtn].forEach((button) => {

      setControlAvailability(button, hasSelection);

    });

    if (contextUngroupBtn) {

      const canUngroup = selectionCanUngroup();

      contextUngroupBtn.style.display = canUngroup ? 'flex' : 'none';

      setControlAvailability(contextUngroupBtn, canUngroup);

    }

    if (contextGroupBtn) {

      const canGroup = selectionCanGroup();

      contextGroupBtn.style.display = canGroup ? 'flex' : 'none';

      setControlAvailability(contextGroupBtn, canGroup);

    }

    objectContextMenu.style.display = 'block';

    objectContextMenu.setAttribute('aria-hidden', 'false');

    objectContextMenu.style.left = '0px';

    objectContextMenu.style.top = '0px';

    const rect = objectContextMenu.getBoundingClientRect();

    const left = Math.max(8, Math.min(clientX, window.innerWidth - rect.width - 8));

    const top = Math.max(8, Math.min(clientY, window.innerHeight - rect.height - 8));

    objectContextMenu.style.left = Math.round(left) + 'px';

    objectContextMenu.style.top = Math.round(top) + 'px';

  }



  function alignSelection(mode) {

    const targets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!targets.length) return;

    const multiLabels = {

      left: M.alignElsLeft,

      centerX: M.alignElsCenterX,

      right: M.alignElsRight,

      top: M.alignElsTop,

      middle: M.alignElsMiddle,

      bottom: M.alignElsBottom

    };

    const singleLabels = {

      left: M.alignSlideLeft,

      centerX: M.alignSlideCenterX,

      right: M.alignSlideRight,

      top: M.alignSlideTop,

      middle: M.alignSlideMiddle,

      bottom: M.alignSlideBottom

    };

    const presentationMode = selectionPresentationMode(targets);

    const alignGroupAsOne = presentationMode === 'group';

    const alignToSlide = alignGroupAsOne || targets.length === 1;

    const activeSlide = targets[0].closest('.slide') || document.querySelector('.slide.active');

    const slideBox = stageBox(activeSlide || stage);

    const selectionBox = combinedStageBox(targets);

    const referenceBox = alignToSlide ? slideBox : selectionBox;

    if (!referenceBox || !selectionBox) return;

    const label = (alignToSlide ? singleLabels : multiLabels)[mode];

    let groupDx = 0;

    let groupDy = 0;

    if (alignGroupAsOne) {

      if (mode === 'left') groupDx = referenceBox.left - selectionBox.left;

      if (mode === 'centerX') groupDx = (referenceBox.left + referenceBox.width / 2)

        - (selectionBox.left + selectionBox.width / 2);

      if (mode === 'right') groupDx = referenceBox.right - selectionBox.right;

      if (mode === 'top') groupDy = referenceBox.top - selectionBox.top;

      if (mode === 'middle') groupDy = (referenceBox.top + referenceBox.height / 2)

        - (selectionBox.top + selectionBox.height / 2);

      if (mode === 'bottom') groupDy = referenceBox.bottom - selectionBox.bottom;

    }

    pushBatch(label, 'move', (els) => {

      els.forEach((el) => {

        const b = stageBox(el);

        let dx = alignGroupAsOne ? groupDx : 0;

        let dy = alignGroupAsOne ? groupDy : 0;

        if (!alignGroupAsOne && mode === 'left') dx = referenceBox.left - b.left;

        if (!alignGroupAsOne && mode === 'centerX') dx = (referenceBox.left + referenceBox.width / 2) - (b.left + b.width / 2);

        if (!alignGroupAsOne && mode === 'right') dx = referenceBox.right - b.right;

        if (!alignGroupAsOne && mode === 'top') dy = referenceBox.top - b.top;

        if (!alignGroupAsOne && mode === 'middle') dy = (referenceBox.top + referenceBox.height / 2) - (b.top + b.height / 2);

        if (!alignGroupAsOne && mode === 'bottom') dy = referenceBox.bottom - b.bottom;

        const parentScale = el.offsetParent && el.offsetParent !== stage

          ? (getElementVisualScale(el.offsetParent) || 1)

          : 1;

        if (dx) setUserStyle(el, 'left', (Math.round((styleNumber(el, 'left', el.offsetLeft) + dx / parentScale) * 10) / 10) + 'px');

        if (dy) setUserStyle(el, 'top', (Math.round((styleNumber(el, 'top', el.offsetTop) + dy / parentScale) * 10) / 10) + 'px');

      });

    });

    showTransientReadout(label, 1200);

  }



  function distributeSelection(axis) {

    const targets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    if (selectionPresentationMode(targets) === 'group') {

      showTransientReadout(M.needDistribute);

      return;

    }

    if (targets.length < 3) {

      showTransientReadout(M.needDistribute);

      return;

    }

    const label = axis === 'x' ? M.distributeH : M.distributeV;

    pushBatch(label, 'move', (els) => {

      const boxes = els.map((el) => ({ el: el, box: stageBox(el) }));

      boxes.sort((a, b) => (axis === 'x' ? a.box.left - b.box.left : a.box.top - b.box.top));

      const first = boxes[0].box;

      const last = boxes[boxes.length - 1].box;

      if (axis === 'x') {

        const span = last.right - first.left;

        const total = boxes.reduce((sum, item) => sum + item.box.width, 0);

        const gap = (span - total) / (boxes.length - 1);

        let cursor = first.left;

        boxes.forEach((item) => {

          const dx = cursor - item.box.left;

          if (Math.abs(dx) > 0.01) {

            setUserStyle(item.el, 'left', (Math.round((styleNumber(item.el, 'left', item.el.offsetLeft) + dx) * 10) / 10) + 'px');

          }

          cursor += item.box.width + gap;

        });

      } else {

        const span = last.bottom - first.top;

        const total = boxes.reduce((sum, item) => sum + item.box.height, 0);

        const gap = (span - total) / (boxes.length - 1);

        let cursor = first.top;

        boxes.forEach((item) => {

          const dy = cursor - item.box.top;

          if (Math.abs(dy) > 0.01) {

            setUserStyle(item.el, 'top', (Math.round((styleNumber(item.el, 'top', item.el.offsetTop) + dy) * 10) / 10) + 'px');

          }

          cursor += item.box.height + gap;

        });

      }

    });

    showTransientReadout(label, 1200);

  }



  function toggleBold() {

    const textTargets = selectedTextTargets();

    if (!textTargets.length) return;

    runSnapshotBatch(M.bold, textTargets, (targets) => {

      const first = targets[0];

      const isBold = parseInt(getComputedStyle(first).fontWeight, 10) >= 700;

      targets.forEach((el) => {

        setUserStyle(el, 'font-weight', isBold ? '400' : '900');

      });

    });

  }



  function toggleItalic() {

    const textTargets = selectedTextTargets();

    if (!textTargets.length) return;

    runSnapshotBatch(M.italic, textTargets, (targets) => {

      const first = targets[0];

      const isItalic = ['italic', 'oblique'].includes(getComputedStyle(first).fontStyle);

      targets.forEach((el) => setUserStyle(el, 'font-style', isItalic ? 'normal' : 'italic'));

    });

  }



  function toggleUnderline() {

    const textTargets = selectedTextTargets();

    if (!textTargets.length) return;

    runSnapshotBatch(M.underline, textTargets, (targets) => {

      const first = targets[0];

      const isUnderlined = String(getComputedStyle(first).textDecorationLine || '').includes('underline');

      targets.forEach((el) => setUserStyle(el, 'text-decoration-line', isUnderlined ? 'none' : 'underline'));

    });

  }



  function setAlignment(value) {

    const textTargets = selectedTextTargets();

    if (!textTargets.length) return;

    const label = value === 'left' ? M.alignLeft : (value === 'right' ? M.alignRight : M.alignCenter);

    runSnapshotBatch(label, textTargets, (targets) => {

      targets.forEach((el) => {

        if (isTextEditableElement(el)) setUserStyle(el, 'text-align', value);

      });

    });

  }



  function setVerticalAlignment(value) {

    const textTargets = selectedTextTargets();

    if (!textTargets.length) return;

    const labels = {

      start: M.verticalTop,

      center: M.verticalCenter,

      end: M.verticalBottom

    };

    runSnapshotBatch(labels[value], textTargets, (targets) => {

      targets.forEach((el) => {

        applyDeclaredVerticalAlignment(el, value);

      });

    });

  }



  function setTextColor(color) {

    const capabilities = selectionCapabilities();

    if (!capabilities.canUseColor) return;

    runSnapshotBatch(M.styleChange, capabilities.colorTargets, (targets) => {

      targets.forEach((el) => {

        if (isTextEditableElement(el)) setUserStyle(el, 'color', color);

        else setUserStyle(el, 'background', color);

      });

    });

  }



  function setTextBoxBackground(color) {

    const capabilities = selectionCapabilities();

    if (!capabilities.canUseBackground) return;

    runSnapshotBatch(M.textBoxBackgroundChange, capabilities.backgroundTargets, (targets) => {

      targets.forEach((el) => setUserStyle(el, 'background', color || ''));

    });

  }



  function visibleSlideElements() {

    const slide = selectedEl ? selectedEl.closest('.slide') : document.querySelector('.slide.active');

    if (!slide) return [];

    return Array.from(slide.querySelectorAll('.el')).filter((el) => getComputedStyle(el).display !== 'none');

  }



  function changeLayer(direction) {

    const label = direction > 0 ? M.bringFront : M.sendBack;

    pushStyleBatch(label, (targets) => {

      const all = visibleSlideElements();

      const zValues = all.map((el) => parseInt(getComputedStyle(el).zIndex, 10)).filter((n) => !Number.isNaN(n));

      const maxZ = zValues.length ? Math.max.apply(null, zValues) : 1;

      const minZ = zValues.length ? Math.min.apply(null, zValues) : 1;

      targets.forEach((el, index) => {

        setUserStyle(el, 'z-index', String(direction > 0 ? maxZ + index + 1 : minZ - index - 1));

      });

    });

  }



  function sanitizedElementHtml(el) {

    const clone = el.cloneNode(true);

    [clone].concat(Array.from(clone.querySelectorAll('[data-edit-layer]'))).forEach((node) => {

      node.removeAttribute('contenteditable');

      node.style.outline = '';

      node.style.boxShadow = '';

      node.style.cursor = '';

    });

    return clone.outerHTML;

  }



  function finalizeInsertedClones(clones, label) {

    setSelection(clones, clones[0]);

    currentTool = 'move';

    applyEditableState();

    repositionHandles();

    pushCommand({

      type: 'batch',

      label: label + ' ' + t(M.multiSelected, { count: clones.length }),

      itemType: 'style',

      items: clones.map((clone) => ({

        type: 'style',

        el: clone,

        key: elementKey(clone),

        before: Object.assign({}, measureElementState(clone), { display: 'none' }),

        after: measureElementState(clone)

      }))

    });

    clones.forEach((clone) => recordChange(clone));

    scheduleDraftSave();

  }



  function insertionContainer(slide) {

    if (!slide) return null;

    return slide.querySelector('[data-content-area]')

      || slide.querySelector('.content-layer')

      || slide;

  }



  function insertionThemeToken(slide, names, fallback) {

    const style = slide ? getComputedStyle(slide) : null;

    for (const name of names) {

      const value = style ? style.getPropertyValue(name).trim() : '';

      if (value && value !== 'initial' && value !== 'inherit') return value;

    }

    return fallback;

  }



  function nextUserObjectZ(slide) {

    const values = Array.from(slide ? slide.querySelectorAll('.el') : [])

      .map((el) => parseInt(getComputedStyle(el).zIndex, 10))

      .filter((value) => Number.isFinite(value));

    return (values.length ? Math.max.apply(null, values) : 0) + 1;

  }



  function insertDrawGeometry(event) {

    if (!insertDrawState || !insertDrawState.container) return null;

    const rect = insertDrawState.container.getBoundingClientRect();

    const scale = Math.max(getScale(), 0.0001);

    const leftPx = Math.min(insertDrawState.startX, event.clientX);

    const topPx = Math.min(insertDrawState.startY, event.clientY);

    const rightPx = Math.max(insertDrawState.startX, event.clientX);

    const bottomPx = Math.max(insertDrawState.startY, event.clientY);

    const parentWidth = Math.max(MIN_SIZE, insertDrawState.container.offsetWidth || rect.width / scale);

    const parentHeight = Math.max(MIN_SIZE, insertDrawState.container.offsetHeight || rect.height / scale);

    const rawLeft = (leftPx - rect.left) / scale;

    const rawTop = (topPx - rect.top) / scale;

    const rawRight = (rightPx - rect.left) / scale;

    const rawBottom = (bottomPx - rect.top) / scale;

    const left = Math.max(0, Math.min(parentWidth, rawLeft));

    const top = Math.max(0, Math.min(parentHeight, rawTop));

    const right = Math.max(left, Math.min(parentWidth, rawRight));

    const bottom = Math.max(top, Math.min(parentHeight, rawBottom));

    return {

      left: Math.round(left * 10) / 10,

      top: Math.round(top * 10) / 10,

      width: Math.max(MIN_SIZE, Math.round((right - left) * 10) / 10),

      height: Math.max(MIN_SIZE, Math.round((bottom - top) * 10) / 10)

    };

  }



  function updateInsertDrawPreview(event) {

    if (!insertDrawState || !insertDrawBox) return null;

    const moved = Math.abs(event.clientX - insertDrawState.startX) > DRAG_THRESHOLD

      || Math.abs(event.clientY - insertDrawState.startY) > DRAG_THRESHOLD;

    insertDrawState.moved = moved;

    if (!moved) {

      insertDrawBox.style.display = 'none';

      return null;

    }

    const left = Math.min(insertDrawState.startX, event.clientX);

    const top = Math.min(insertDrawState.startY, event.clientY);

    const width = Math.max(DRAG_THRESHOLD, Math.abs(event.clientX - insertDrawState.startX));

    const height = Math.max(DRAG_THRESHOLD, Math.abs(event.clientY - insertDrawState.startY));

    insertDrawBox.style.left = Math.round(left) + 'px';

    insertDrawBox.style.top = Math.round(top) + 'px';

    insertDrawBox.style.width = Math.round(width) + 'px';

    insertDrawBox.style.height = Math.round(height) + 'px';

    insertDrawBox.style.display = 'block';

    return insertDrawGeometry(event);

  }



  function isSupportedInsertImageFile(file) {

    if (!file) return false;

    const type = String(file.type || '').toLowerCase();

    const name = String(file.name || '').toLowerCase();

    return /^image\/(png|jpeg|webp|gif)$/.test(type)

      || ((!type || type === 'application/octet-stream') && /\.(png|jpe?g|webp|gif)$/i.test(name));

  }



  function readInsertImageFile(file) {

    if (!file || !isSupportedInsertImageFile(file)) {

      showTransientReadout(M.imageFileTypes, 1800);

      return;

    }

    const reader = new FileReader();

    reader.onload = () => {

      const dataUrl = String(reader.result || '');

      if (!dataUrl.startsWith('data:image/')) {

        showTransientReadout(M.imageReadFailed, 1800);

        return;

      }

      const probe = new Image();

      probe.onload = () => {

        insertEditorObject('image', null, null, {

          dataUrl: dataUrl,

          fileName: file.name || M.insertImage,

          naturalWidth: probe.naturalWidth || 1,

          naturalHeight: probe.naturalHeight || 1

        });

      };

      probe.onerror = () => showTransientReadout(M.imageReadFailed, 1800);

      probe.src = dataUrl;

    };

    reader.onerror = () => showTransientReadout(M.imageReadFailed, 1800);

    reader.readAsDataURL(file);

  }



  function chooseInsertImage() {

    if (!requireEditMode(M.insertImage) || !insertImageFileInput) return;

    cancelPendingInsert();

    insertImageFileInput.value = '';

    insertImageFileInput.click();

  }



  function cancelPendingInsert() {

    pendingInsertKind = null;

    insertDrawState = null;

    if (insertDrawBox) insertDrawBox.style.display = 'none';

    if (stage) stage.style.cursor = '';

    unlockPointerSelection();

    if (currentTool === 'insert') currentTool = selectedEl ? 'move' : null;

    applyEditableState();

    updateSelectionBadge();

  }



  function armInsertObject(kind, shape, asset) {

    if (!requireEditMode(kind === 'image' ? M.insertImage : M.insert)) return null;

    if (textEditingEl) endTextEdit();

    commitPendingChanges();

    pendingInsertKind = {

      kind: kind,

      shape: shape || (kind === 'text' || kind === 'image' ? null : 'rect'),

      asset: asset && asset.dataUrl ? asset : null

    };

    currentTool = 'insert';

    toggleInsertPanel(false);

    if (stage) stage.style.cursor = 'crosshair';

    applyEditableState();

    repositionHandles();

    updateSelectionBadge();

    showTransientReadout(M.insertDragHint, 3000);

    return pendingInsertKind;

  }



  function finishInsertDraw(event) {

    if (!insertDrawState || !pendingInsertKind) return;

    const state = insertDrawState;

    const geometry = state.moved ? insertDrawGeometry(event) : null;

    insertDrawState = null;

    if (insertDrawBox) insertDrawBox.style.display = 'none';

    unlockPointerSelection();

    if (!geometry || geometry.width < MIN_SIZE || geometry.height < MIN_SIZE) {

      showTransientReadout(M.insertDragHint, 2200);

      return;

    }

    const kind = pendingInsertKind.kind;

    const shape = pendingInsertKind.shape;

    const asset = pendingInsertKind.asset;

    pendingInsertKind = null;

    if (stage) stage.style.cursor = '';

    insertEditorObject(kind, shape, geometry, asset);

  }



  function insertEditorObject(kind, shape, geometry, asset) {

    if (!requireEditMode(kind === 'image' ? M.insertImage : M.insert)) return null;

    const slide = document.querySelector('.slide.active');

    const container = insertionContainer(slide);

    if (!slide || !container) {

      showTransientReadout(M.idleHint, 1800);

      return null;

    }

    if (textEditingEl) endTextEdit();

    commitPendingChanges();

    const isText = kind === 'text';

    const isImage = kind === 'image';

    if (isImage && (!asset || !String(asset.dataUrl || '').startsWith('data:image/'))) {

      showTransientReadout(M.imageReadFailed, 1800);

      return null;

    }

    const hasDrawGeometry = !!(geometry

      && Number.isFinite(geometry.left)

      && Number.isFinite(geometry.top)

      && Number.isFinite(geometry.width)

      && Number.isFinite(geometry.height));

    const parentWidth = Math.max(MIN_SIZE, container.offsetWidth || stageBox(container).width / Math.max(getScale(), 0.0001));

    const parentHeight = Math.max(MIN_SIZE, container.offsetHeight || stageBox(container).height / Math.max(getScale(), 0.0001));

    const imageRatio = isImage

      ? Math.max(0.1, Math.min(10, Number(asset?.naturalWidth || 0) / Math.max(1, Number(asset?.naturalHeight || 0)) || 1.5))

      : 1;

    const imageHeight = isImage

      ? Math.max(MIN_SIZE, Math.min(INSERT_IMAGE_HEIGHT, Math.max(MIN_SIZE, parentHeight - 48)))

      : 0;

    const imageWidth = isImage

      ? Math.max(MIN_SIZE, Math.min(INSERT_IMAGE_MAX_WIDTH, Math.max(MIN_SIZE, parentWidth - 48), imageHeight * imageRatio))

      : 0;

    const defaultWidth = isText ? 460 : (isImage ? imageWidth : 280);

    const defaultHeight = isText ? 132 : (isImage ? imageHeight : 220);

    const width = hasDrawGeometry

      ? Math.max(MIN_SIZE, Math.min(parentWidth, geometry.width))

      : Math.max(MIN_SIZE, Math.min(defaultWidth, parentWidth - 48));

    const height = hasDrawGeometry

      ? Math.max(MIN_SIZE, Math.min(parentHeight, geometry.height))

      : Math.max(MIN_SIZE, Math.min(defaultHeight, parentHeight - 48));

    const createdCount = slide.querySelectorAll('[data-edit-user-created="true"]').length;

    const gridCellWidth = 480;

    const gridCellHeight = 270;

    const gridColumns = Math.max(1, Math.floor((parentWidth - 48) / gridCellWidth));

    const gridColumn = createdCount % gridColumns;

    const gridRow = Math.floor(createdCount / gridColumns);

    const left = hasDrawGeometry

      ? Math.max(0, Math.min(parentWidth - width, geometry.left))

      : Math.max(

      24,

      Math.min(

        Math.max(24, parentWidth - width - 24),

        24 + gridColumn * gridCellWidth + Math.max(0, (gridCellWidth - width) / 2)

      )

    );

    const top = hasDrawGeometry

      ? Math.max(0, Math.min(parentHeight - height, geometry.top))

      : Math.max(

      24,

      Math.min(

        Math.max(24, parentHeight - height - 24),

        24 + gridRow * gridCellHeight + Math.max(0, (gridCellHeight - height) / 2)

      )

    );

    const el = document.createElement('div');

    el.className = 'el ' + (isText

      ? 'edit-user-text'

      : (isImage ? 'edit-user-image' : 'edit-user-shape edit-user-shape-' + shape));

    el.dataset.editKind = isText ? 'text' : 'visual';

    el.dataset.editObject = isText ? 'user-textbox' : (isImage ? 'user-image' : 'user-' + shape);

    el.dataset.pptxName = isText ? 'user-textbox' : (isImage ? 'user-image' : 'user-' + shape);

    el.dataset.editPosition = 'absolute';

    el.dataset.editUserCreated = 'true';

    el.dataset.editClone = '1';

    el.setAttribute('aria-label', isText

      ? M.insertTextBox

      : (isImage ? M.insertImage : (shape === 'ellipse' ? M.insertEllipse : (shape === 'round-rect' ? M.insertRoundRect : M.insertRect))));

    if (isText) {

      el.dataset.editFit = 'container';

      el.dataset.editVerticalAlign = 'center';

      el.textContent = '\u8f38\u5165\u6587\u5b57';

    }

    container.appendChild(el);

    const accent = insertionThemeToken(slide, ['--accent', '--brand', '--gold'], '#0F766E');

    const textColor = getComputedStyle(slide).color || insertionThemeToken(slide, ['--text', '--surface-text'], '#17201C');

    [

      ['position', 'absolute'],

      ['box-sizing', 'border-box'],

      ['left', left + 'px'],

      ['top', top + 'px'],

      ['width', width + 'px'],

      ['height', height + 'px'],

      ['z-index', nextUserObjectZ(slide)],

      ['pointer-events', 'auto']

    ].forEach(([property, value]) => setUserStyle(el, property, value));

    if (isText) {

      [

        ['font-family', 'var(--font-body)'],

        ['font-size', '36px'],

        ['font-weight', '500'],

        ['line-height', '1.25'],

        ['color', textColor],

        ['background', 'transparent'],

        ['border', '0'],

        ['border-radius', '0'],

        ['padding', '12px 16px'],

        ['text-align', 'left'],

        ['text-wrap', 'wrap'],

        ['white-space', 'normal'],

        ['overflow', 'visible']

      ].forEach(([property, value]) => setUserStyle(el, property, value));

    } else if (isImage) {

      [

        ['background', 'transparent'],

        ['border', '0'],

        ['overflow', 'hidden'],

        ['border-radius', '0']

      ].forEach(([property, value]) => setUserStyle(el, property, value));

      const image = document.createElement('img');

      image.src = asset.dataUrl;

      image.alt = asset.fileName || M.insertImage;

      image.draggable = false;

      image.dataset.editImage = 'true';

      image.dataset.editAssetName = asset.fileName || '';

      image.style.cssText = 'display:block;width:100%;height:100%;object-fit:contain;pointer-events:none;';

      el.appendChild(image);

    } else {

      [

        ['background', accent],

        ['border', '2px solid ' + accent],

        ['overflow', 'hidden']

      ].forEach(([property, value]) => setUserStyle(el, property, value));

      if (shape === 'round-rect') setUserStyle(el, 'border-radius', '20px');

      if (shape === 'ellipse') setUserStyle(el, 'border-radius', '50%');

    }

    finalizeInsertedClones([el], isText ? M.insertedTextBox : (isImage ? M.insertedImage : M.insertedShape));

    showTransientReadout(isText ? M.insertedTextBox : (isImage ? M.insertedImage : M.insertedShape), 1200);

    if (isText) beginTextEdit(el);

    return el;

  }



  function insertTextBox() {

    return insertEditorObject('text', null);

  }



  function insertShape(shape) {

    return insertEditorObject('shape', shape || 'rect');

  }



  function duplicateSelection() {

    const targets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!targets.length) return;

    if (textEditingEl) endTextEdit();

    commitPendingChanges();

    const clones = targets.map((el) => {

      const state = measureElementState(el);

      const wrap = document.createElement('div');

      wrap.innerHTML = sanitizedElementHtml(el);

      const clone = wrap.firstElementChild;

      clone.dataset.editClone = '1';

      setUserStyle(clone, 'left', (state.left + 24) + 'px');

      setUserStyle(clone, 'top', (state.top + 24) + 'px');

      el.parentNode.appendChild(clone);

      return clone;

    });

    remapCloneGroups(clones);

    finalizeInsertedClones(clones, M.duplicate);

  }



  function copySelection() {

    const targets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!targets.length) return;

    clipboardData = targets.map((el) => {

      const state = measureElementState(el);

      return { html: sanitizedElementHtml(el), left: state.left, top: state.top };

    });

    showTransientReadout(t(M.copiedEls, { count: clipboardData.length }));

  }



  function pasteClipboard() {

    if (!clipboardData || !clipboardData.length) return;

    const slide = (selectedEl && selectedEl.closest('.slide')) || document.querySelector('.slide.active');

    if (!slide) return;

    if (textEditingEl) endTextEdit();

    commitPendingChanges();

    const clones = clipboardData.map((entry) => {

      const wrap = document.createElement('div');

      wrap.innerHTML = entry.html;

      const clone = wrap.firstElementChild;

      clone.dataset.editClone = '1';

      entry.left += 24;

      entry.top += 24;

      setUserStyle(clone, 'left', entry.left + 'px');

      setUserStyle(clone, 'top', entry.top + 'px');

      slide.appendChild(clone);

      return clone;

    });

    remapCloneGroups(clones);

    finalizeInsertedClones(clones, M.paste);

    showTransientReadout(t(M.pastedEls, { count: clones.length }));

  }



  function deleteSelection() {

    clearGroupEditScopes();

    const targets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

    if (!targets.length) return;

    pushStyleBatch(M.delete, (els) => {

      els.forEach((el) => {

        setUserStyle(el, 'display', 'none');

      });

    });

    setSelection([], null);

    applyEditableState();

    hideHandles();

    updateSelectionBadge();

  }



  function viewportRectToStageBox(rect) {

    const stageRect = stage.getBoundingClientRect();

    const scale = getScale() || 1;

    return {

      left: (rect.left - stageRect.left) / scale,

      top: (rect.top - stageRect.top) / scale,

      right: (rect.right - stageRect.left) / scale,

      bottom: (rect.bottom - stageRect.top) / scale,

      width: rect.width / scale,

      height: rect.height / scale

    };

  }



  function stageBox(el) {

    return viewportRectToStageBox(el.getBoundingClientRect());

  }



  function combinedStageBox(els) {

    const boxes = els.filter((el) => el && getComputedStyle(el).display !== 'none').map(stageBox);

    if (!boxes.length) return null;

    const left = Math.min.apply(null, boxes.map((box) => box.left));

    const top = Math.min.apply(null, boxes.map((box) => box.top));

    const right = Math.max.apply(null, boxes.map((box) => box.right));

    const bottom = Math.max.apply(null, boxes.map((box) => box.bottom));

    return { left: left, top: top, right: right, bottom: bottom, width: right - left, height: bottom - top };

  }



  function showGuideLine(axis, value, source) {

    const stageRect = stage.getBoundingClientRect();

    const scale = getScale() || 1;

    const line = axis === 'x' ? guideX : guideY;

    if (!line) return;

    line.dataset.guideAxis = axis;

    line.dataset.guideSource = source || 'object';

    line.style.display = 'block';

    if (axis === 'x') {

      line.style.left = (stageRect.left + value * scale) + 'px';

      line.style.top = stageRect.top + 'px';

      line.style.width = '1px';

      line.style.height = stageRect.height + 'px';

    } else {

      line.style.left = stageRect.left + 'px';

      line.style.top = (stageRect.top + value * scale) + 'px';

      line.style.width = stageRect.width + 'px';

      line.style.height = '1px';

    }

  }



  function hideGuides() {

    [guideX, guideY].forEach((line) => {

      if (!line) return;

      line.style.display = 'none';

      delete line.dataset.guideSource;

    });

  }



  function alignmentGuideCandidates(els) {

    const selectedSet = new Set(els);

    const active = document.querySelector('.slide.active');

    const candidatesX = [{ value: 960, source: 'slide-center', anchor: 'center' }];

    const candidatesY = [{ value: 540, source: 'slide-center', anchor: 'middle' }];

    if (!active) return { candidatesX: candidatesX, candidatesY: candidatesY };



    const contentArea = active.querySelector('[data-content-area]');

    if (contentArea) {

      const content = stageBox(contentArea);

      candidatesX.push(

        { value: content.left, source: 'content-area', anchor: 'left' },

        { value: content.left + content.width / 2, source: 'content-area', anchor: 'center' },

        { value: content.right, source: 'content-area', anchor: 'right' }

      );

      candidatesY.push(

        { value: content.top, source: 'content-area', anchor: 'top' },

        { value: content.top + content.height / 2, source: 'content-area', anchor: 'middle' },

        { value: content.bottom, source: 'content-area', anchor: 'bottom' }

      );

    }



    active.querySelectorAll('.el').forEach((el) => {

      if (selectedSet.has(el) || getComputedStyle(el).display === 'none') return;

      const other = stageBox(el);

      candidatesX.push(

        { value: other.left, source: 'object', anchor: 'left' },

        { value: other.left + other.width / 2, source: 'object', anchor: 'center' },

        { value: other.right, source: 'object', anchor: 'right' }

      );

      candidatesY.push(

        { value: other.top, source: 'object', anchor: 'top' },

        { value: other.top + other.height / 2, source: 'object', anchor: 'middle' },

        { value: other.bottom, source: 'object', anchor: 'bottom' }

      );

    });

    return { candidatesX: candidatesX, candidatesY: candidatesY };

  }



  function findSnap(els, explicitBox) {

    const box = explicitBox || combinedStageBox(els);

    if (!box) return null;

    const candidates = alignmentGuideCandidates(els);

    const ownX = [box.left, box.left + box.width / 2, box.right];

    const ownY = [box.top, box.top + box.height / 2, box.bottom];

    let bestX = null;

    let bestY = null;

    candidates.candidatesX.forEach((candidate) => {

      ownX.forEach((value) => {

        const diff = Math.abs(candidate.value - value);

        if (diff <= GUIDE_THRESHOLD && (!bestX || diff < bestX.diff)) {

          bestX = { value: candidate.value, own: value, diff: diff, source: candidate.source, anchor: candidate.anchor };

        }

      });

    });

    candidates.candidatesY.forEach((candidate) => {

      ownY.forEach((value) => {

        const diff = Math.abs(candidate.value - value);

        if (diff <= GUIDE_THRESHOLD && (!bestY || diff < bestY.diff)) {

          bestY = { value: candidate.value, own: value, diff: diff, source: candidate.source, anchor: candidate.anchor };

        }

      });

    });

    return { bestX: bestX, bestY: bestY };

  }



  function updateTextEditAlignmentGuides(el) {

    if (!editMode || !el || textEditingEl !== el) {

      hideGuides();

      return;

    }

    const snap = findSnap([el], viewportRectToStageBox(visualSelectionRect(el)));

    if (!snap) {

      hideGuides();

      return;

    }

    if (snap.bestX) showGuideLine('x', snap.bestX.value, snap.bestX.source);

    else if (guideX) guideX.style.display = 'none';

    if (snap.bestY) showGuideLine('y', snap.bestY.value, snap.bestY.source);

    else if (guideY) guideY.style.display = 'none';

  }



  function updateAlignmentGuides(els) {

    const snap = findSnap(els);

    if (!snap) {

      hideGuides();

      return;

    }

    if (snap.bestX) showGuideLine('x', snap.bestX.value, snap.bestX.source);

    else if (guideX) guideX.style.display = 'none';

    if (snap.bestY) showGuideLine('y', snap.bestY.value, snap.bestY.source);

    else if (guideY) guideY.style.display = 'none';

  }



  function applySnap(els, disabled) {

    if (disabled) return;

    const snap = findSnap(els);

    if (!snap) return;

    const dx = snap.bestX ? snap.bestX.value - snap.bestX.own : 0;

    const dy = snap.bestY ? snap.bestY.value - snap.bestY.own : 0;

    if (!dx && !dy) return;

    els.forEach((el) => {

      if (dx) setUserStyle(el, 'left', (Math.round((styleNumber(el, 'left', el.offsetLeft) + dx) * 10) / 10) + 'px');

      if (dy) setUserStyle(el, 'top', (Math.round((styleNumber(el, 'top', el.offsetTop) + dy) * 10) / 10) + 'px');

    });

  }



  HANDLE_POSITIONS.forEach((pos) => {

    const handle = document.createElement('div');

    handle.className = 'edit-resize-handle';

    handle.dataset.handle = pos;

    handle.style.cssText =

      'position:fixed;width:' + HANDLE_SIZE + 'px;height:' + HANDLE_SIZE + 'px;' +

      'background:#3FD0E8;border:1px solid #0B1220;border-radius:2px;z-index:102;' +

      'display:none;cursor:' + HANDLE_CURSORS[pos] + ';';

    handle.addEventListener('mousedown', (e) => {

      if (!editMode || !selectedEl) return;

      e.preventDefault();

      e.stopPropagation();

      commitPendingChanges();

      currentTool = 'resize';

      resizeEl = selectedEl;

      resizeHandle = pos;

      resizeScale = getScale();

      const selectedResizeTargets = selectedTargets().filter((el) => el && getComputedStyle(el).display !== 'none');

      // A manual group is represented by a shared group path rather than a
      // wrapper node. Expand that path before capturing resize state so side
      // handles operate on the whole group and retain each member's offset.
      const manualGroupResizeTargets = selectedGroupId
        ? groupMembers(editableRoot(resizeEl) || resizeEl, selectedGroupId)
        : [];
      const resizeTargets = (manualGroupResizeTargets.length > 1
        ? manualGroupResizeTargets
        : selectedResizeTargets).filter((el) => el && getComputedStyle(el).display !== 'none');

      resizeGroupStartStates = null;

      resizeVisualStart = null;

      resizeAdaptiveStart = null;

      resizeMode = resolveResizeMode(resizeTargets, resizeEl, pos);

      resizeFrameWidthOnly = resizeMode === 'text-frame-width';

      resizeFrameHeightOnly = resizeMode === 'text-frame-height';

      const nestedGeneratedResizeTargets = resizeTargets.length === 1 && isCompositeRoot(resizeEl)

        ? groupResizeLeafTargets(resizeTargets)

        : [];

      // Manual regrouping may combine a generated content composite with a

      // sibling footer/caption. Resolve every selected root to the semantic

      // leaves that actually own geometry; otherwise only the composite shell

      // changes and the visible union makes the handle appear locked.

      const regroupedLeafResizeTargets = resizeTargets.length > 1

        ? groupResizeLeafTargets(resizeTargets)

        : [];

      const groupResizeTargets = regroupedLeafResizeTargets.length > 1

        ? regroupedLeafResizeTargets

        : (nestedGeneratedResizeTargets.length > 1 ? nestedGeneratedResizeTargets : []);

      if (groupResizeTargets.length > 1) {

        // Generated content groups with semantic modules reuse the formal

        // group contract: side handles extend content-aware frames; corners

        // scale visual units proportionally.

        const groupBox = combinedStageBox(groupResizeTargets);

        resizeStartState = null;

        resizeStartLeft = groupBox.left;

        resizeStartTop = groupBox.top;

        resizeStartW = groupBox.width;

        resizeStartH = groupBox.height;

        resizeStartFontSize = 0;

        resizeTypographyStart = [];

        resizeGroupStartStates = groupResizeTargets.map((item) => {

          ensureOriginalGeometry(item);

          const box = stageBox(item);

          const adaptive = captureAdaptiveGroupResize(

            item,

            box,

            pos === 'e' || pos === 'w' ? 'horizontal' : (pos === 'n' || pos === 's' ? 'vertical' : '')

          );

          return {

            el: item,

            key: elementKey(item),

            before: measureElementState(item),

            box: box,

            visual: captureVisualTransformStart(item),

            adaptive: adaptive,

            layers: adaptive.layers,

            verticalHistoryItems: adaptive.historyItems

          };

        });

      } else {

        resizeStartState = measureElementState(resizeEl);

        resizeStartLeft = resizeStartState.left;

        resizeStartTop = resizeStartState.top;

        resizeStartW = resizeStartState.width;

        resizeStartH = resizeStartState.height;

        resizeStartFontSize = parseFloat(getComputedStyle(resizeEl).fontSize) || 0;

        resizeTypographyStart = captureTypographyStart(resizeEl);

        if (resizeMode === 'composite-width' || resizeMode === 'composite-height') {

          const visualBox = stageBox(resizeEl);

          resizeStartLeft = visualBox.left;

          resizeStartTop = visualBox.top;

          resizeStartW = visualBox.width;

          resizeStartH = visualBox.height;

          const adaptive = captureAdaptiveGroupResize(

            resizeEl,

            visualBox,

            pos === 'e' || pos === 'w' ? 'horizontal' : (pos === 'n' || pos === 's' ? 'vertical' : '')

          );

          resizeAdaptiveStart = {

            el: resizeEl,

            key: elementKey(resizeEl),

            before: resizeStartState,

            box: visualBox,

            visual: captureVisualTransformStart(resizeEl),

            adaptive: adaptive,

            layers: adaptive.layers,

            verticalHistoryItems: adaptive.historyItems

          };

        } else if (resizeMode === 'composite-proportional' || resizeMode === 'text-proportional') {

          const visualBox = stageBox(resizeEl);

          resizeStartLeft = visualBox.left;

          resizeStartTop = visualBox.top;

          resizeStartW = visualBox.width;

          resizeStartH = visualBox.height;

          resizeVisualStart = captureVisualTransformStart(resizeEl);

        }

      }      resizeStartX = e.clientX;

      resizeStartY = e.clientY;

      if (!resizeGroupStartStates && !originalPositions.has(resizeEl)) {

        originalPositions.set(resizeEl, { left: resizeStartState.left, top: resizeStartState.top });

      }

      if (!resizeGroupStartStates && !originalSizes.has(resizeEl)) {

        originalSizes.set(resizeEl, {

          width: resizeStartState.width,

          height: resizeStartState.height,

          fontSize: resizeStartFontSize

        });

      }

    });

    document.body.appendChild(handle);

    handles[pos] = handle;

  });



  selectionFrame = document.createElement('div');

  selectionFrame.id = 'edit-selection-frame';

  selectionFrame.style.cssText =

    'position:fixed;display:none;pointer-events:none;box-sizing:border-box;border:2px solid #F6C35B;' +

    'z-index:101;background:transparent;';

  document.body.appendChild(selectionFrame);



  [guideX, guideY] = ['x', 'y'].map((axis) => {

    const guide = document.createElement('div');

    guide.className = 'edit-guide-line';

    guide.dataset.guideAxis = axis;

    guide.setAttribute('aria-hidden', 'true');

    guide.style.cssText =

      'position:fixed;z-index:101;display:none;pointer-events:none;background:#A855F7;' +

      'box-shadow:0 0 0 1px rgba(255,255,255,.86),0 0 8px rgba(168,85,247,.28);';

    document.body.appendChild(guide);

    return guide;

  });



  marqueeBox = document.createElement('div');

  marqueeBox.className = 'edit-marquee-box';

  marqueeBox.style.cssText =

    'position:fixed;z-index:101;display:none;pointer-events:none;' +

    'border:1px dashed #3FD0E8;background:rgba(63,208,232,.08);';

  document.body.appendChild(marqueeBox);



  insertDrawBox = document.createElement('div');

  insertDrawBox.className = 'edit-insert-draw-box';

  insertDrawBox.setAttribute('aria-hidden', 'true');

  insertDrawBox.style.cssText =

    'position:fixed;z-index:104;display:none;pointer-events:none;box-sizing:border-box;' +

    'border:2px dashed #3FD0E8;background:rgba(63,208,232,.14);';

  document.body.appendChild(insertDrawBox);



  modePanel = document.createElement('div');

  modePanel.id = 'edit-mode-panel';

  modePanel.style.cssText =

    'position:fixed;left:16px;bottom:96px;z-index:101;display:none;min-width:268px;' +

    'background:rgba(8,20,33,.94);color:#E6EAF0;border:1px solid rgba(63,208,232,.22);' +

    'border-radius:14px;padding:12px 12px 10px;';

  const modeTitle = document.createElement('div');

  modeTitle.textContent = M.modePanelTitle;

  modeTitle.style.cssText = 'font:600 11px/1.2 var(--font-body);letter-spacing:.16em;text-transform:uppercase;color:#87A9BD;margin-bottom:10px;';

  const modeRow = document.createElement('div');

  modeRow.style.cssText = 'display:flex;gap:8px;margin-bottom:10px;';

  const modeMeta = document.createElement('div');

  modeMeta.style.cssText = 'border-top:1px solid rgba(255,255,255,.08);padding-top:10px;';

  modeStatusLabel = document.createElement('div');

  modeStatusLabel.style.cssText = 'font:700 15px/1.2 var(--font-body);margin-bottom:4px;';

  modeStatusHint = document.createElement('div');

  modeStatusHint.style.cssText = 'font:500 12px/1.45 var(--font-body);color:#B7C9D6;margin-bottom:8px;';

  const modeShortcut = document.createElement('div');

  modeShortcut.textContent = M.modePanelHelp;

  modeShortcut.style.cssText = 'font:600 11px/1 var(--font-mono);color:#87A9BD;';

  modeMeta.append(modeStatusLabel, modeStatusHint, modeShortcut);



  function makeModeButton(key, label) {

    const btn = document.createElement('button');

    btn.type = 'button';

    btn.textContent = label;

    btn.style.cssText =

      'height:34px;padding:0 12px;border-radius:999px;border:1px solid rgba(255,255,255,.16);' +

      'background:transparent;color:#E6EAF0;cursor:pointer;font:700 12px/1 var(--font-body);';

    btn.onclick = (e) => {

      e.stopPropagation();

      if (!requireEditMode(label)) return;

      setTool(key);

    };

    modeButtons[key] = btn;

    return btn;

  }



  modeRow.append(

    makeModeButton('move', '\u79fb\u52d5'),

    makeModeButton('text', '\u6539\u5b57'),

    makeModeButton('resize', '\u7e2e\u653e')

  );

  modePanel.append(modeTitle, modeRow, modeMeta);

  document.body.appendChild(modePanel);



  selectionBadge = document.createElement('div');

  selectionBadge.id = 'edit-selection-badge';

  selectionBadge.style.cssText =

    'position:fixed;z-index:103;display:none;pointer-events:auto;left:50%;top:92px;transform:translateX(-50%);' +

    'width:max-content;max-width:calc(100vw - 32px);box-sizing:border-box;flex-direction:column;align-items:stretch;gap:7px;' +

    'white-space:nowrap;overflow-x:auto;background:rgba(255,255,255,.97);border:1px solid rgba(18,24,30,.12);border-radius:14px;' +

    'padding:9px 12px;color:#17201C;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);';

  const badgeLabel = document.createElement('div');

  badgeLabel.dataset.role = 'label';

  badgeLabel.style.cssText = 'font:700 12px/1 var(--font-body);padding:0 4px;';

  const badgeHint = document.createElement('div');

  badgeHint.dataset.role = 'hint';

  badgeHint.style.cssText = 'display:none;';

  fontControlRow = document.createElement('div');

  fontControlRow.style.cssText = 'display:none;align-items:center;gap:6px;pointer-events:auto;';

  const fontFamilyLabel = document.createElement('span');

  fontFamilyLabel.textContent = M.fontFamilyLabel;

  fontFamilyLabel.style.cssText = 'font:700 12px/1 var(--font-body);color:#5C6670;';

  fontFamilySelect = document.createElement('select');

  fontFamilySelect.id = 'edit-font-family-select';

  fontFamilySelect.title = M.fontFamilyLabel;

  fontFamilySelect.setAttribute('aria-label', M.fontFamilyLabel);

  fontFamilySelect.style.cssText =

    'height:26px;max-width:156px;padding:0 24px 0 8px;border:1px solid rgba(18,24,30,.16);' +

    'border-radius:6px;background:#fff;color:#182028;font:600 12px/1 var(--font-body);cursor:pointer;';

  populateFontFamilySelect(fontFamilySelect);

  fontFamilySelect.addEventListener('change', () => {

    applySelectedFontFamily(fontFamilySelect.value);

  });

  const fontLabel = document.createElement('span');

  fontLabel.textContent = M.fontSizeLabel;

  fontLabel.style.cssText = 'font:700 12px/1 var(--font-body);color:#5C6670;';

  fontMinusBtn = document.createElement('button');

  fontMinusBtn.type = 'button';

  fontMinusBtn.textContent = '-';

  fontMinusBtn.title = M.fontDecrease;

  fontPlusBtn = document.createElement('button');

  fontPlusBtn.type = 'button';

  fontPlusBtn.textContent = '+';

  fontPlusBtn.title = M.fontIncrease;

  [fontMinusBtn, fontPlusBtn].forEach((btn) => {

    btn.style.cssText =

      'width:28px;height:28px;border-radius:999px;border:1px solid rgba(18,24,30,.14);' +

      'background:#fff;color:#17201C;cursor:pointer;font:700 15px/1 var(--font-mono);';

  });

  const fontSizeButtons = document.createElement('div');

  fontSizeButtons.style.cssText = 'display:inline-flex;align-items:center;gap:3px;';

  fontSizeButtons.append(fontMinusBtn, fontPlusBtn);

  fontSizeInput = document.createElement('input');

  fontSizeInput.id = 'edit-font-size-input';

  fontSizeInput.type = 'text';

  fontSizeInput.inputMode = 'numeric';

  fontSizeInput.pattern = '[0-9.]*';

  fontSizeInput.style.cssText =

    'width:56px;height:28px;border-radius:8px;border:1px solid rgba(18,24,30,.14);' +

    'background:#fff;color:#17201C;text-align:center;font:700 12px/1 var(--font-mono);';

  fontSizeRange = document.createElement('input');

  fontSizeRange.type = 'range';

  fontSizeRange.min = '8';

  fontSizeRange.max = '240';

  fontSizeRange.step = '1';

  fontSizeRange.title = M.fontSizeLabel + '拉桿';

  fontSizeRange.setAttribute('aria-label', M.fontSizeLabel + '拉桿');

  fontSizeRange.style.cssText = 'width:86px;height:24px;accent-color:#0F766E;cursor:pointer;';

  const fontUnit = document.createElement('span');

  fontUnit.textContent = 'px';

  fontUnit.style.cssText = 'font:600 11px/1 var(--font-mono);color:#5C6670;';

  fontMinusBtn.onclick = (e) => {

    e.stopPropagation();

    adjustSelectedFont(-1);

  };

  fontPlusBtn.onclick = (e) => {

    e.stopPropagation();

    adjustSelectedFont(1);

  };

  fontSizeInput.addEventListener('input', (e) => {

    e.stopPropagation();

    const value = parseFloat(fontSizeInput.value);

    if (Number.isNaN(value)) return;

    applySelectedFontSizeValue(value, { mergeUndo: true });

  });

  fontSizeInput.addEventListener('keydown', (e) => {

    e.stopPropagation();

    if (e.key === 'Enter') {

      commitPendingChanges();

      fontSizeInput.blur();

    }

  });

  fontSizeInput.addEventListener('blur', commitPendingChanges);

  fontSizeRange.addEventListener('input', (e) => {

    e.stopPropagation();

    applySelectedFontSizeValue(parseFloat(fontSizeRange.value), { mergeUndo: true });

  });

  fontSizeRange.addEventListener('change', commitPendingChanges);

  fontControlRow.append(fontFamilyLabel, fontFamilySelect, fontLabel, fontSizeButtons, fontSizeInput, fontUnit, fontSizeRange);



  function makeCompactStyleInput(labelText, step, onApply) {

    const label = document.createElement('span');

    label.textContent = labelText;

    label.style.cssText = 'font:700 12px/1 var(--font-body);color:#5C6670;margin-left:4px;';

    const input = document.createElement('input');

    input.type = 'number';

    input.step = String(step);

    input.style.cssText =

      'width:52px;height:28px;border-radius:8px;border:1px solid rgba(18,24,30,.14);' +

      'background:#fff;color:#17201C;text-align:center;font:700 12px/1 var(--font-mono);';

    const range = document.createElement('input');

    range.type = 'range';

    range.min = labelText === M.lineHeightLabel ? '24' : '-20';

    range.max = labelText === M.lineHeightLabel ? '220' : '40';

    range.step = String(step);

    range.title = labelText + '拉桿';

    range.setAttribute('aria-label', labelText + '拉桿');

    range.style.cssText = 'width:78px;height:24px;accent-color:#0F766E;cursor:pointer;';

    input.addEventListener('input', (e) => {

      e.stopPropagation();

      if (!selectedEl) return;

      const value = parseFloat(input.value);

      if (Number.isNaN(value)) return;

      range.value = String(value);

      beginPendingStyleChange(selectedEl);

      onApply(selectedEl, value);

      recordChange(selectedEl);

      repositionHandles();

      scheduleDraftSave();

    });

    input.addEventListener('keydown', (e) => {

      e.stopPropagation();

      if (e.key === 'Enter') {

        commitPendingChanges();

        input.blur();

      }

    });

    input.addEventListener('blur', commitPendingChanges);

    range.addEventListener('input', (e) => {

      e.stopPropagation();

      if (!selectedEl) return;

      const value = parseFloat(range.value);

      if (Number.isNaN(value)) return;

      input.value = String(value);

      beginPendingStyleChange(selectedEl);

      onApply(selectedEl, value);

      recordChange(selectedEl);

      repositionHandles();

      scheduleDraftSave();

    });

    range.addEventListener('change', commitPendingChanges);

    fontControlRow.append(label, input, range);

    if (labelText === M.lineHeightLabel) lineHeightRange = range;

    if (labelText === M.letterSpacingLabel) letterSpacingRange = range;

    return input;

  }



  lineHeightInput = makeCompactStyleInput(M.lineHeightLabel, 1, (el, value) => {

    if (value > 0) setUserStyle(el, 'line-height', value + 'px');

  });

  letterSpacingInput = makeCompactStyleInput(M.letterSpacingLabel, 0.5, (el, value) => {

    setUserStyle(el, 'letter-spacing', value + 'px');

  });



  function makeSelectionToolButton(label, content, onClick) {

    const btn = document.createElement('button');

    btn.type = 'button';

    btn.title = label;

    btn.setAttribute('aria-label', label);

    btn.style.cssText =

      'width:28px;height:28px;border-radius:999px;border:1px solid rgba(18,24,30,.14);' +

      'background:#fff;color:#17201C;cursor:pointer;font:800 12px/1 var(--font-body);' +

      'display:inline-flex;align-items:center;justify-content:center;';

    if (content && content.indexOf('<svg') === 0) {

      btn.innerHTML = content;

      const svg = btn.querySelector('svg');

      if (svg) {

        svg.setAttribute('aria-hidden', 'true');

        svg.style.cssText = 'width:17px;height:17px;display:block;';

      }

    } else {

      btn.textContent = content;

    }

    btn.onclick = (e) => {

      e.stopPropagation();

      onClick();

    };

    return btn;

  }



  function makeTextSelectionButton(label, onClick, help) {

    const btn = document.createElement('button');

    btn.type = 'button';

    btn.textContent = label;

    btn.title = help || label;

    btn.setAttribute('aria-label', help || label);

    btn.style.cssText =

      'height:28px;padding:0 10px;border-radius:999px;border:1px solid rgba(18,24,30,.14);' +

      'background:#fff;color:#17201C;cursor:pointer;font:700 11px/1 var(--font-body);white-space:nowrap;' +

      'display:inline-flex;align-items:center;justify-content:center;';

    btn.onclick = (e) => {

      e.stopPropagation();

      onClick();

    };

    return btn;

  }



  function alignmentIcon(mode) {

    const positions = {

      left: [[4, 6, 16], [4, 10, 11], [4, 14, 16], [4, 18, 9]],

      center: [[4, 6, 16], [6.5, 10, 11], [4, 14, 16], [7.5, 18, 9]],

      right: [[4, 6, 16], [9, 10, 11], [4, 14, 16], [11, 18, 9]]

    }[mode];

    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round">' +

      positions.map((line) => '<path d="M' + line[0] + ' ' + line[1] + 'h' + line[2] + '"/>').join('') +

      '</svg>';

  }



  function verticalAlignmentIcon(mode) {

    const textY = mode === 'start' ? 9 : (mode === 'end' ? 18 : 13.5);

    const ruleY = mode === 'start' ? 4 : (mode === 'end' ? 21 : 12);

    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">' +

      '<path d="M4 ' + ruleY + 'h16"/>' +

      '<path d="M7 ' + textY + 'h10"/><path d="M9 ' + (textY + 3.5) + 'h6"/>' +

      '</svg>';

  }



  boldBtn = makeSelectionToolButton(M.bold, 'B', toggleBold);

  italicBtn = makeSelectionToolButton(M.italic, 'I', toggleItalic);

  italicBtn.style.fontStyle = 'italic';

  underlineBtn = makeSelectionToolButton(M.underline, 'U', toggleUnderline);

  underlineBtn.style.textDecoration = 'underline';

  alignLeftBtn = makeSelectionToolButton(M.alignLeft, alignmentIcon('left'), () => setAlignment('left'));

  alignCenterBtn = makeSelectionToolButton(M.alignCenter, alignmentIcon('center'), () => setAlignment('center'));

  alignRightBtn = makeSelectionToolButton(M.alignRight, alignmentIcon('right'), () => setAlignment('right'));

  verticalTopBtn = makeSelectionToolButton(M.verticalTop, verticalAlignmentIcon('start'), () => setVerticalAlignment('start'));

  verticalCenterBtn = makeSelectionToolButton(M.verticalCenter, verticalAlignmentIcon('center'), () => setVerticalAlignment('center'));

  verticalBottomBtn = makeSelectionToolButton(M.verticalBottom, verticalAlignmentIcon('end'), () => setVerticalAlignment('end'));

  groupBtn = makeTextSelectionButton(M.groupAction, groupSelection);

  groupBtn.dataset.action = 'group';

  editGroupMemberBtn = makeTextSelectionButton(M.editGroupMember, editPrimaryGroupMember, M.editGroupMemberHelp);

  editGroupMemberBtn.dataset.action = 'edit-group-member';

  selectWholeGroupBtn = makeTextSelectionButton(M.selectWholeGroup, selectWholeGroup, M.selectWholeGroupHelp);

  selectWholeGroupBtn.dataset.action = 'select-whole-group';



  colorControlRow = document.createElement('div');

  colorControlRow.id = 'edit-color-tools';

  colorControlRow.style.cssText = 'display:flex;align-items:center;gap:5px;border-left:1px solid rgba(18,24,30,.12);padding-left:10px;';

  backgroundColorControlRow = document.createElement('div');

  backgroundColorControlRow.id = 'edit-text-background-tools';

  backgroundColorControlRow.style.cssText = 'display:flex;align-items:center;gap:5px;border-left:1px solid rgba(18,24,30,.12);padding-left:10px;';



  const DEFAULT_SWATCHES = ['#17201C', '#0F766E', '#E85D3F', '#E8B23F', '#FFFFFF'];

  let cachedPresetPaletteKey = '';

  let cachedPresetPalette = null;



  // Editor chrome is application UI, not part of the active slide theme.
  // Keep it visually stable while the slide palette remains available to the
  // text/object color controls below.
  const EDITOR_CHROME_PALETTE = Object.freeze({

    surface: 'rgb(255, 255, 255)',

    ink: 'rgb(24, 32, 40)',

    muted: 'rgb(92, 102, 112)',

    accent: 'rgb(15, 118, 110)',

    border: 'rgba(18, 24, 30, .18)',

  });



  function resolveCssColor(value) {

    if (!value) return '';

    const probe = document.createElement('span');

    probe.style.color = value;

    if (!probe.style.color) return '';

    probe.style.cssText += ';position:fixed;left:-9999px;top:-9999px;pointer-events:none;';

    document.body.appendChild(probe);

    const color = getComputedStyle(probe).color;

    probe.remove();

    return color || '';

  }



  function cssColorChannels(value) {

    const resolved = resolveCssColor(value);

    const match = resolved.match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i);

    if (!match) return null;

    return [Number(match[1]), Number(match[2]), Number(match[3])];

  }



  function cssColorToHex(value, fallback) {

    const channels = cssColorChannels(value);

    if (!channels) return fallback || '#ffffff';

    return '#' + channels.map((channel) => Math.max(0, Math.min(255, Math.round(channel))).toString(16).padStart(2, '0')).join('');

  }



  function colorLuminance(value) {

    const channels = cssColorChannels(value);

    if (!channels) return null;

    const linear = channels.map((channel) => {

      const normalized = channel / 255;

      return normalized <= 0.03928 ? normalized / 12.92 : Math.pow((normalized + 0.055) / 1.055, 2.4);

    });

    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];

  }



  function readableInk(background, preferred) {

    const bg = colorLuminance(background);

    const ink = colorLuminance(preferred);

    if (bg !== null && ink !== null) {

      const ratio = (Math.max(bg, ink) + 0.05) / (Math.min(bg, ink) + 0.05);

      if (ratio >= 4.5) return resolveCssColor(preferred);

    }

    return bg !== null && bg < 0.42 ? 'rgb(255, 255, 255)' : 'rgb(18, 24, 30)';

  }



  function presetPalette() {

    const rootStyle = getComputedStyle(document.documentElement);

    const paletteProperties = [

      '--bg', '--background', '--surface', '--text', '--primary', '--ink', '--muted', '--secondary',

      '--accent', '--support-accent', '--support', '--surface-text', '--accent-ink', '--accent-text',

      '--surface-accent-ink'

    ];

    const paletteKey = paletteProperties.map((property) => rootStyle.getPropertyValue(property).trim()).join('|');

    if (cachedPresetPalette && cachedPresetPaletteKey === paletteKey) return cachedPresetPalette;

    const read = (...properties) => {

      for (let index = 0; index < properties.length; index += 1) {

        const raw = rootStyle.getPropertyValue(properties[index]).trim();

        const resolved = resolveCssColor(raw);

        if (resolved) return resolved;

      }

      return '';

    };

    cachedPresetPaletteKey = paletteKey;

    cachedPresetPalette = {

      bg: read('--bg', '--background'),

      surface: read('--surface'),

      text: read('--text', '--primary', '--ink'),

      muted: read('--muted', '--secondary'),

      accent: read('--accent'),

      support: read('--support-accent', '--support'),

      surfaceText: read('--surface-text', '--text', '--primary', '--ink'),

      accentInk: read('--accent-ink', '--accent-text'),

      surfaceAccentInk: read('--surface-accent-ink', '--accent-ink', '--accent-text')

    };

    return cachedPresetPalette;

  }



  function currentPaletteSignature() {

    const root = document.documentElement;

    const slide = document.querySelector('.slide.active');

    const palette = presetPalette();

    return [

      root.dataset.presetTheme || '',

      root.dataset.themeId || '',

      slide ? slide.id : '',

      slide ? slide.style.backgroundColor || '' : '',

      ...Object.keys(palette).map((key) => palette[key])

    ].join('|');

  }



  function currentColorControlSignature(capabilities) {

    return currentPaletteSignature() + '|'

      + (capabilities && capabilities.wholeGroup ? 'group-surface' : 'object-background');

  }



  function applyPresetChromeTheme() {

    const { surface, ink, muted, accent, border } = EDITOR_CHROME_PALETTE;

    [selectionBadge, appearancePanel].filter(Boolean).forEach((panel) => {

      panel.style.setProperty('--edit-panel-bg', surface);

      panel.style.setProperty('--edit-ink', ink);

      panel.style.setProperty('--edit-muted', muted);

      panel.style.setProperty('--edit-accent', accent);

      panel.style.setProperty('--edit-border', border);

      panel.style.background = surface;

      panel.style.color = ink;

      panel.style.borderColor = border;

    });

    if (selectionBadge) {

      selectionBadge.querySelectorAll('span').forEach((label) => { label.style.color = muted; });

      const label = selectionBadge.querySelector('[data-role="label"]');

      if (label) label.style.color = ink;

    }

    [fontFamilySelect, fontSizeInput, fontSizeRange, lineHeightInput, lineHeightRange, letterSpacingInput, letterSpacingRange, deckFontSelect].filter(Boolean).forEach((control) => {

      control.style.background = surface;

      control.style.color = ink;

      control.style.borderColor = border;

    });

  }



  function makeColorSwatch(color, onChoose, role) {

    const swatch = document.createElement('button');

    swatch.type = 'button';

    swatch.title = color;

    swatch.setAttribute('aria-label', color);

    swatch.dataset.presetRole = role || 'custom';

    swatch.dataset.colorSwatch = 'true';

    swatch.style.cssText =

      'width:22px;height:22px;border-radius:999px;border:1px solid rgba(18,24,30,.18);cursor:pointer;' +

      'background:' + color + ';';

    swatch.onclick = (e) => {

      e.stopPropagation();

      (onChoose || setTextColor)(color);

    };

    return swatch;

  }



  function slidePaletteColors() {

    const slide = document.querySelector('.slide.active');

    if (!slide) return [];

    const seen = new Set();

    const colors = [];

    const palette = presetPalette();

    [palette.text, palette.muted, palette.accent, palette.support, palette.surface, palette.bg].forEach((color) => {

      const key = String(color || '').toLowerCase();

      if (!color || seen.has(key)) return;

      seen.add(key);

      colors.push(color);

    });

    slide.querySelectorAll('.el').forEach((el) => {

      [el].concat(Array.from(el.children || [])).forEach((node) => {

        if (colors.length >= 6) return;

        if (!node.textContent || !node.textContent.trim()) return;

        const color = getComputedStyle(node).color;

        const key = String(color || '').toLowerCase();

        if (!color || seen.has(key)) return;

        seen.add(key);

        colors.push(color);

      });

    });

    DEFAULT_SWATCHES.forEach((color) => {

      if (colors.length >= 6) return;

      const resolved = resolveCssColor(color);

      const key = resolved.toLowerCase();

      if (!resolved || seen.has(key)) return;

      seen.add(key);

      colors.push(resolved);

    });

    return colors.slice(0, 6);

  }



  function textBoxBackgroundColors() {

    const seen = new Set();

    const colors = [];

    const palette = presetPalette();

    const targets = selectionCapabilities().backgroundTargets || [];

    targets.forEach((target) => {

      const current = getComputedStyle(target).backgroundColor;

      const key = String(current || '').toLowerCase();

      if (!current || key === 'rgba(0, 0, 0, 0)' || seen.has(key)) return;

      seen.add(key);

      colors.push(current);

    });

    [palette.surface, palette.bg, palette.accent, palette.support, '#FFFFFF'].forEach((color) => {

      const resolved = resolveCssColor(color);

      const key = String(resolved || '').toLowerCase();

      if (!resolved || seen.has(key)) return;

      seen.add(key);

      colors.push(resolved);

    });

    return colors.slice(0, 6);

  }



  function populateColorControlRow(row, labelText, colors, onChoose, clearLabel) {

    if (!row) return;

    if (typeof row._closeColorPopover === 'function') row._closeColorPopover();

    row.innerHTML = '';

    const label = document.createElement('span');

    label.textContent = labelText;

    label.style.cssText = 'font:700 11px/1 var(--font-body);white-space:nowrap;';

    row.appendChild(label);

    colors.forEach((color, index) => row.appendChild(makeColorSwatch(color, onChoose, 'palette-' + index)));

    const custom = document.createElement('button');

    custom.type = 'button';

    custom.title = M.customColor;

    custom.setAttribute('aria-label', labelText + ' ' + M.customColor);

    custom.style.cssText =

      'width:26px;height:26px;padding:0;border:1px solid rgba(18,24,30,.18);border-radius:6px;' +

      'cursor:pointer;';

    let customHex = cssColorToHex(colors[0], '#ffffff');

    const popover = document.createElement('div');

    popover.id = 'edit-color-popover';

    popover.dataset.editorChrome = 'true';

    popover.setAttribute('role', 'dialog');

    popover.setAttribute('aria-label', labelText + ' RGB');

    popover.style.cssText =

      'display:none;position:fixed;z-index:2147483646;width:286px;padding:14px;border:1px solid rgba(18,24,30,.16);' +

      'border-radius:12px;background:#fff;color:#182028;box-shadow:0 18px 46px rgba(0,0,0,.28);font:600 12px/1.2 var(--font-body);';

    const popoverTitle = document.createElement('strong');

    popoverTitle.textContent = labelText;

    popoverTitle.style.cssText = 'display:block;margin-bottom:10px;font:800 12px/1 var(--font-body);';

    const preview = document.createElement('div');

    preview.style.cssText = 'height:28px;margin-bottom:10px;border:1px solid rgba(18,24,30,.18);border-radius:6px;';

    const pickerArea = document.createElement('div');

    pickerArea.style.cssText =

      'position:relative;height:132px;margin-bottom:9px;border-radius:7px;overflow:hidden;cursor:crosshair;' +

      'background:linear-gradient(to top,#000,transparent),linear-gradient(to right,#fff,hsl(0 100% 50%));';

    const pickerCursor = document.createElement('span');

    pickerCursor.style.cssText =

      'position:absolute;left:100%;top:0;width:16px;height:16px;box-sizing:border-box;border:2px solid #fff;' +

      'border-radius:50%;transform:translate(-50%,-50%);box-shadow:0 0 0 1px rgba(18,24,30,.72);pointer-events:none;';

    pickerArea.appendChild(pickerCursor);

    const hueInput = document.createElement('input');

    hueInput.type = 'range';

    hueInput.min = '0';

    hueInput.max = '360';

    hueInput.step = '1';

    hueInput.title = '色相';

    hueInput.setAttribute('aria-label', labelText + ' 色相');

    hueInput.style.cssText =

      'display:block;width:100%;height:18px;margin:0 0 11px;accent-color:#0F766E;cursor:pointer;' +

      'background:linear-gradient(to right,#f00,#ff0,#0f0,#0ff,#00f,#f0f,#f00);border-radius:99px;';

    const rgbRow = document.createElement('div');

    rgbRow.style.cssText = 'display:grid;grid-template-columns:repeat(3,1fr);gap:6px;';

    const channelInputs = ['R', 'G', 'B'].map((channel) => {

      const field = document.createElement('label');

      field.textContent = channel;

      field.style.cssText = 'display:grid;gap:4px;color:#5C6670;font:700 10px/1 var(--font-body);';

      const input = document.createElement('input');

      input.type = 'number';

      input.min = '0';

      input.max = '255';

      input.step = '1';

      input.inputMode = 'numeric';

      input.style.cssText = 'width:100%;height:30px;box-sizing:border-box;border:1px solid rgba(18,24,30,.18);border-radius:6px;padding:0 6px;text-align:center;font:700 12px/1 var(--font-mono);color:#182028;background:#fff;';

      field.appendChild(input);

      rgbRow.appendChild(field);

      return input;

    });

    const hexToHsv = (hex) => {

      const normalized = cssColorToHex(hex, '#000000').slice(1);

      const rgb = normalized.match(/.{2}/g).map((part) => parseInt(part, 16) / 255);

      const max = Math.max(...rgb);

      const min = Math.min(...rgb);

      const delta = max - min;

      let hue = 0;

      if (delta) {

        if (max === rgb[0]) hue = 60 * (((rgb[1] - rgb[2]) / delta) % 6);

        else if (max === rgb[1]) hue = 60 * ((rgb[2] - rgb[0]) / delta + 2);

        else hue = 60 * ((rgb[0] - rgb[1]) / delta + 4);

      }

      if (hue < 0) hue += 360;

      return { h: hue, s: max ? delta / max : 0, v: max };

    };

    const hsvToHex = (h, s, v) => {

      const hue = ((Number(h) % 360) + 360) % 360;

      const saturation = Math.max(0, Math.min(1, Number(s) || 0));

      const value = Math.max(0, Math.min(1, Number(v) || 0));

      const chroma = value * saturation;

      const x = chroma * (1 - Math.abs((hue / 60) % 2 - 1));

      const match = value - chroma;

      let rgb = [0, 0, 0];

      if (hue < 60) rgb = [chroma, x, 0];

      else if (hue < 120) rgb = [x, chroma, 0];

      else if (hue < 180) rgb = [0, chroma, x];

      else if (hue < 240) rgb = [0, x, chroma];

      else if (hue < 300) rgb = [x, 0, chroma];

      else rgb = [chroma, 0, x];

      return '#' + rgb.map((channel) => Math.round((channel + match) * 255).toString(16).padStart(2, '0')).join('');

    };

    const popoverActions = document.createElement('div');

    popoverActions.style.cssText = 'display:flex;justify-content:flex-end;gap:6px;margin-top:10px;';

    const apply = document.createElement('button');

    apply.type = 'button';

    apply.textContent = '套用';

    apply.title = '選色後套用到目前選取';

    apply.setAttribute('aria-label', labelText + ' 套用');

    apply.style.cssText = 'height:28px;padding:0 12px;border:1px solid rgba(18,24,30,.18);border-radius:6px;background:rgba(15,118,110,.08);font:700 11px/1 var(--font-body);cursor:pointer;';

    popoverActions.appendChild(apply);

    popover.append(popoverTitle, preview, pickerArea, hueInput, rgbRow, popoverActions);

    const readChannels = () => channelInputs.map((input) => Math.max(0, Math.min(255, Number(input.value) || 0)));

    const channelsToHex = () => '#' + readChannels().map((channel) => Math.round(channel).toString(16).padStart(2, '0')).join('');

    const syncPopover = (hex) => {

      const normalized = cssColorToHex(hex, customHex);

      customHex = normalized;

      const channels = normalized.slice(1).match(/.{2}/g).map((part) => parseInt(part, 16));

      const hsv = hexToHsv(normalized);

      channelInputs.forEach((input, index) => { input.value = String(channels[index]); });

      hueInput.value = String(Math.round(hsv.h));

      pickerArea.style.background =

        'linear-gradient(to top,#000,transparent),linear-gradient(to right,#fff,hsl(' + Math.round(hsv.h) + ' 100% 50%))';

      pickerCursor.style.left = (hsv.s * 100) + '%';

      pickerCursor.style.top = ((1 - hsv.v) * 100) + '%';

      custom.style.background = normalized;

      preview.style.background = normalized;

    };

    const closePopover = () => {

      popover.style.display = 'none';

      if (popover.parentNode) popover.remove();

      document.removeEventListener('mousedown', outsideClose, true);

      document.removeEventListener('keydown', escapeClose, true);

    };

    const outsideClose = (event) => {

      if (event.target === custom || popover.contains(event.target)) return;

      closePopover();

    };

    const escapeClose = (event) => {

      if (event.key === 'Escape') closePopover();

    };

    const openPopover = () => {

      if (popover.style.display !== 'none') {

        closePopover();

        return;

      }

      syncPopover(customHex);

      document.body.appendChild(popover);

      const rect = custom.getBoundingClientRect();

      const left = Math.max(8, Math.min(window.innerWidth - 302, rect.left));

      const top = Math.max(8, Math.min(window.innerHeight - 390, rect.bottom + 8));

      popover.style.left = Math.round(left) + 'px';

      popover.style.top = Math.round(top) + 'px';

      popover.style.display = 'block';

      document.addEventListener('mousedown', outsideClose, true);

      document.addEventListener('keydown', escapeClose, true);

    };

    row._closeColorPopover = closePopover;

    custom.addEventListener('click', (event) => { event.stopPropagation(); openPopover(); });

    custom.addEventListener('mousedown', (event) => event.stopPropagation());

    const pickFromPointer = (event) => {

      const rect = pickerArea.getBoundingClientRect();

      const saturation = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));

      const value = Math.max(0, Math.min(1, 1 - (event.clientY - rect.top) / rect.height));

      syncPopover(hsvToHex(Number(hueInput.value), saturation, value));

    };

    pickerArea.addEventListener('pointerdown', (event) => {

      event.preventDefault();

      event.stopPropagation();

      pickerArea.setPointerCapture?.(event.pointerId);

      pickFromPointer(event);

    });

    pickerArea.addEventListener('pointermove', (event) => {

      if (event.buttons) pickFromPointer(event);

    });

    pickerArea.addEventListener('mousedown', (event) => event.stopPropagation());

    hueInput.addEventListener('input', (event) => {

      event.stopPropagation();

      const hsv = hexToHsv(customHex);

      syncPopover(hsvToHex(Number(hueInput.value), hsv.s, hsv.v));

    });

    hueInput.addEventListener('mousedown', (event) => event.stopPropagation());

    channelInputs.forEach((input) => input.addEventListener('input', () => {

      customHex = channelsToHex();

      syncPopover(customHex);

    }));

    apply.addEventListener('mousedown', (e) => e.stopPropagation());

    apply.addEventListener('click', (e) => {

      e.stopPropagation();

      onChoose(customHex);

      apply.textContent = '已套用';

      apply.style.background = 'rgba(34,197,94,.16)';

      window.setTimeout(() => {

        if (!apply.isConnected) return;

        apply.textContent = '套用';

        apply.style.background = 'rgba(15,118,110,.08)';

      }, 900);

    });

    syncPopover(customHex);

    row.appendChild(custom);

    if (clearLabel) {

      const clear = document.createElement('button');

      clear.type = 'button';

      clear.textContent = '×';

      clear.title = clearLabel;

      clear.setAttribute('aria-label', clearLabel);

      clear.style.cssText = 'width:24px;height:24px;border:1px solid rgba(18,24,30,.18);border-radius:6px;background:transparent;font:800 16px/1 var(--font-body);cursor:pointer;';

      clear.addEventListener('click', (e) => {

        e.stopPropagation();

        onChoose('');

      });

      row.appendChild(clear);

    }

  }



  function refreshColorSwatches() {

    if (!colorControlRow) return;

    const capabilities = selectionCapabilities();

    populateColorControlRow(colorControlRow, M.textColor, slidePaletteColors(), setTextColor, '');

    populateColorControlRow(

      backgroundColorControlRow,

      M.textBoxBackground,

      textBoxBackgroundColors(),

      setTextBoxBackground,

      M.clearTextBoxBackground

    );

    lastPaletteSignature = currentColorControlSignature(capabilities);

    applyPresetChromeTheme();

  }



  function updateAppearanceControls() {

    if (deckFontSelect) {

      const state = deckFontState();

      const values = DECK_FONT_PROPERTIES.map((property) => state[property] || '');

      const unique = Array.from(new Set(values));

      if (unique.length > 1) setFontFamilySelectValue(deckFontSelect, '__mixed__');

      else if (!unique[0]) setFontFamilySelectValue(deckFontSelect, FONT_FAMILY_CHOICES[0].value);

      else setFontFamilySelectValue(deckFontSelect, unique[0], primaryFontFamily(unique[0]));

    }

    if (deckFontSelect) deckFontSelect.disabled = !editMode;

    const activeSlide = document.querySelector('.slide.active');

    const activeSlideMask = slideMaskState(activeSlide);

    if (slideMaskColorInput && document.activeElement !== slideMaskColorInput) {

      slideMaskColorInput.value = activeSlideMask.color;

    }

    if (slideMaskOpacityRange && document.activeElement !== slideMaskOpacityRange) {

      slideMaskOpacityRange.value = String(Math.round(activeSlideMask.opacity * 100));

    }

    if (slideMaskOpacityValue) slideMaskOpacityValue.textContent = Math.round(activeSlideMask.opacity * 100) + '%';

    if (slideMaskColorInput) slideMaskColorInput.disabled = !editMode || !activeSlide;

    if (slideMaskOpacityRange) slideMaskOpacityRange.disabled = !editMode || !activeSlide;

    if (slideMaskResetButton) {

      slideMaskResetButton.disabled = !editMode || !activeSlide || (

        activeSlideMask.color === DEFAULT_SLIDE_MASK_COLOR

        && activeSlideMask.opacity === DEFAULT_SLIDE_MASK_OPACITY

      );

    }

    applyPresetChromeTheme();

    if (appearancePanel) {

      const ink = appearancePanel.style.getPropertyValue('--edit-ink') || '#182028';

      const accent = appearancePanel.style.getPropertyValue('--edit-accent') || '#0f766e';

      appearancePanel.querySelectorAll('label,strong,span').forEach((node) => { node.style.color = ink; });

      appearancePanel.querySelectorAll('button:not([data-color-swatch])').forEach((button) => {

        button.style.color = ink;

        button.style.borderColor = accent;

      });

    }

  }



  function positionAppearancePanel() {

    if (!appearancePanel || !appearanceBtn || appearancePanel.style.display === 'none') return;

    const buttonRect = appearanceBtn.getBoundingClientRect();

    const viewportPadding = 10;

    const panelRect = appearancePanel.getBoundingClientRect();

    const panelWidth = panelRect.width || 360;

    const panelHeight = panelRect.height || 180;

    const left = Math.min(

      Math.max(viewportPadding, buttonRect.left),

      Math.max(viewportPadding, window.innerWidth - panelWidth - viewportPadding)

    );

    let top = buttonRect.bottom + 8;

    if (top + panelHeight > window.innerHeight - viewportPadding && buttonRect.top - panelHeight - 8 >= viewportPadding) {

      top = buttonRect.top - panelHeight - 8;

    }

    appearancePanel.style.left = Math.round(left) + 'px';

    appearancePanel.style.top = Math.round(top) + 'px';

  }



  function positionInsertPanel() {

    if (!insertPanel || !insertBtn || insertPanel.style.display === 'none') return;

    const buttonRect = insertBtn.getBoundingClientRect();

    const viewportPadding = 10;

    const panelRect = insertPanel.getBoundingClientRect();

    const panelWidth = panelRect.width || 268;

    const panelHeight = panelRect.height || 180;

    const left = Math.min(

      Math.max(viewportPadding, buttonRect.left),

      Math.max(viewportPadding, window.innerWidth - panelWidth - viewportPadding)

    );

    let top = buttonRect.bottom + 8;

    if (top + panelHeight > window.innerHeight - viewportPadding && buttonRect.top - panelHeight - 8 >= viewportPadding) {

      top = buttonRect.top - panelHeight - 8;

    }

    insertPanel.style.left = Math.round(left) + 'px';

    insertPanel.style.top = Math.round(top) + 'px';

  }



  function positionSaveMenu() {

    if (!saveMenu || !saveMenuToggle || saveMenu.style.display === 'none') return;

    const buttonRect = saveMenuToggle.getBoundingClientRect();

    const viewportPadding = 10;

    const panelRect = saveMenu.getBoundingClientRect();

    const panelWidth = panelRect.width || 190;

    const panelHeight = panelRect.height || 100;

    const left = Math.min(

      Math.max(viewportPadding, buttonRect.right - panelWidth),

      Math.max(viewportPadding, window.innerWidth - panelWidth - viewportPadding)

    );

    let top = buttonRect.bottom + 8;

    if (top + panelHeight > window.innerHeight - viewportPadding && buttonRect.top - panelHeight - 8 >= viewportPadding) {

      top = buttonRect.top - panelHeight - 8;

    }

    saveMenu.style.left = Math.round(left) + 'px';

    saveMenu.style.top = Math.round(top) + 'px';

  }



  function toggleSaveMenu(force) {

    if (!saveMenu) return;

    const shouldOpen = force === undefined

      ? saveMenu.style.display === 'none'

      : !!force;

    if (shouldOpen && !editMode) return;

    if (shouldOpen) {

      toggleAppearancePanel(false);

      toggleInsertPanel(false);

    }

    saveMenu.style.display = shouldOpen ? 'flex' : 'none';

    saveMenu.setAttribute('aria-hidden', shouldOpen ? 'false' : 'true');

    if (saveMenuToggle) saveMenuToggle.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');

    if (shouldOpen) {

      positionSaveMenu();

      requestAnimationFrame(positionSaveMenu);

    }

  }



  function toggleInsertPanel(force) {

    if (!insertPanel) return;

    const shouldOpen = force === undefined

      ? insertPanel.style.display === 'none'

      : !!force;

    if (shouldOpen && !editMode) return;

    if (shouldOpen) {

      toggleAppearancePanel(false);

      toggleSaveMenu(false);

    }

    insertPanel.style.display = shouldOpen ? 'flex' : 'none';

    insertPanel.setAttribute('aria-hidden', shouldOpen ? 'false' : 'true');

    if (insertBtn) insertBtn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');

    if (shouldOpen) {

      positionInsertPanel();

      requestAnimationFrame(positionInsertPanel);

    }

  }



  function toggleAppearancePanel(force) {

    if (!appearancePanel) return;

    const shouldOpen = force === undefined

      ? appearancePanel.style.display === 'none'

      : !!force;

    if (shouldOpen && !editMode) return;

    appearancePanel.style.display = shouldOpen ? 'flex' : 'none';

    appearancePanel.setAttribute('aria-hidden', shouldOpen ? 'false' : 'true');

    if (appearanceBtn) appearanceBtn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');

    if (shouldOpen) {

      updateAppearanceControls();

      positionAppearancePanel();

      requestAnimationFrame(positionAppearancePanel);

    }

  }



  refreshColorSwatches();



  appearancePanel = document.createElement('div');

  appearancePanel.id = 'edit-slide-style-panel';

  appearancePanel.dataset.editorChrome = 'true';

  appearancePanel.setAttribute('role', 'dialog');

  appearancePanel.setAttribute('aria-label', M.presentationStyle);

  appearancePanel.setAttribute('aria-hidden', 'true');

  appearancePanel.style.cssText =

    'position:fixed;left:0;top:0;transform:none;z-index:103;display:none;' +

    'width:min(360px,calc(100vw - 20px));max-height:calc(100vh - 20px);overflow:auto;box-sizing:border-box;flex-direction:column;gap:12px;' +

    'padding:14px 16px;border:1px solid rgba(18,24,30,.18);border-radius:14px;' +

    'box-shadow:0 16px 42px rgba(0,0,0,.28);font-family:var(--font-body);pointer-events:auto;';

  const appearanceTitle = document.createElement('strong');

  appearanceTitle.textContent = M.presentationStyle;

  appearanceTitle.style.cssText = 'font:800 14px/1.2 var(--font-body);';

  const deckFontRow = document.createElement('label');

  deckFontRow.style.cssText = 'display:grid;grid-template-columns:96px 1fr;align-items:center;gap:10px;font:700 12px/1 var(--font-body);';

  const deckFontLabel = document.createElement('span');

  deckFontLabel.textContent = M.defaultFont;

  deckFontSelect = document.createElement('select');

  deckFontSelect.id = 'edit-deck-font-family-select';

  deckFontSelect.setAttribute('aria-label', M.defaultFont);

  deckFontSelect.style.cssText = 'height:34px;min-width:0;padding:0 28px 0 10px;border:1px solid rgba(18,24,30,.18);border-radius:8px;font:600 13px/1 var(--font-body);';

  populateFontFamilySelect(deckFontSelect);

  deckFontSelect.addEventListener('change', () => {

    setDeckDefaultFont(deckFontSelect.value);

  });

  const deckFontControl = document.createElement('div');

  deckFontControl.style.cssText = 'display:flex;align-items:center;gap:8px;min-width:0;';

  deckFontControl.append(deckFontSelect);

  deckFontRow.append(deckFontLabel, deckFontControl);

  const slideMaskSection = document.createElement('section');

  slideMaskSection.id = 'edit-slide-mask-controls';

  slideMaskSection.dataset.slideMaskControls = 'true';

  slideMaskSection.style.cssText = 'display:flex;flex-direction:column;gap:8px;padding-top:12px;border-top:1px solid rgba(18,24,30,.12);';

  const slideMaskTitle = document.createElement('strong');

  slideMaskTitle.textContent = M.slideMask;

  slideMaskTitle.style.cssText = 'font:800 12px/1.2 var(--font-body);';

  const slideMaskHelp = document.createElement('span');

  slideMaskHelp.textContent = M.slideMaskHelp;

  slideMaskHelp.style.cssText = 'font:500 11px/1.35 var(--font-body);opacity:.72;';

  const slideMaskColorRow = document.createElement('label');

  slideMaskColorRow.style.cssText = 'display:grid;grid-template-columns:96px 1fr;align-items:center;gap:10px;font:700 12px/1 var(--font-body);';

  const slideMaskColorLabel = document.createElement('span');

  slideMaskColorLabel.textContent = M.slideMaskColor;

  slideMaskColorInput = document.createElement('input');

  slideMaskColorInput.id = 'edit-slide-mask-color';

  slideMaskColorInput.dataset.slideMaskColor = 'true';

  slideMaskColorInput.type = 'color';

  slideMaskColorInput.value = DEFAULT_SLIDE_MASK_COLOR;

  slideMaskColorInput.style.cssText = 'width:52px;height:30px;padding:2px;border:1px solid rgba(18,24,30,.18);border-radius:7px;background:transparent;cursor:pointer;';

  slideMaskColorInput.addEventListener('input', (event) => {

    event.stopPropagation();

    updateSlideMaskFromControls(false);

  });

  slideMaskColorInput.addEventListener('change', (event) => {

    event.stopPropagation();

    updateSlideMaskFromControls(true);

  });

  slideMaskColorRow.append(slideMaskColorLabel, slideMaskColorInput);

  const slideMaskOpacityRow = document.createElement('label');

  slideMaskOpacityRow.style.cssText = 'display:grid;grid-template-columns:96px 1fr auto;align-items:center;gap:10px;font:700 12px/1 var(--font-body);';

  const slideMaskOpacityLabel = document.createElement('span');

  slideMaskOpacityLabel.textContent = M.slideMaskOpacity;

  slideMaskOpacityRange = document.createElement('input');

  slideMaskOpacityRange.id = 'edit-slide-mask-opacity';

  slideMaskOpacityRange.dataset.slideMaskOpacity = 'true';

  slideMaskOpacityRange.type = 'range';

  slideMaskOpacityRange.min = '0';

  slideMaskOpacityRange.max = '100';

  slideMaskOpacityRange.step = '1';

  slideMaskOpacityRange.value = '0';

  slideMaskOpacityRange.style.cssText = 'width:100%;min-width:0;accent-color:var(--edit-accent,#0f766e);cursor:pointer;';

  slideMaskOpacityRange.addEventListener('input', (event) => {

    event.stopPropagation();

    updateSlideMaskFromControls(false);

  });

  slideMaskOpacityRange.addEventListener('change', (event) => {

    event.stopPropagation();

    updateSlideMaskFromControls(true);

  });

  slideMaskOpacityValue = document.createElement('span');

  slideMaskOpacityValue.dataset.slideMaskOpacityValue = 'true';

  slideMaskOpacityValue.textContent = '0%';

  slideMaskOpacityValue.style.cssText = 'min-width:34px;text-align:right;font:800 11px/1 var(--font-mono);';

  slideMaskOpacityRow.append(slideMaskOpacityLabel, slideMaskOpacityRange, slideMaskOpacityValue);

  slideMaskResetButton = document.createElement('button');

  slideMaskResetButton.id = 'edit-slide-mask-reset';

  slideMaskResetButton.dataset.slideMaskReset = 'true';

  slideMaskResetButton.type = 'button';

  slideMaskResetButton.textContent = M.slideMaskReset;

  slideMaskResetButton.style.cssText = 'align-self:flex-start;height:28px;padding:0 9px;border:1px solid rgba(18,24,30,.18);border-radius:7px;background:transparent;font:700 11px/1 var(--font-body);cursor:pointer;';

  slideMaskResetButton.addEventListener('click', (event) => {

    event.stopPropagation();

    resetActiveSlideMask();

  });

  slideMaskSection.append(slideMaskTitle, slideMaskHelp, slideMaskColorRow, slideMaskOpacityRow, slideMaskResetButton);

  appearancePanel.append(appearanceTitle, deckFontRow, slideMaskSection);

  appearancePanel.addEventListener('mousedown', (event) => event.stopPropagation());

  appearancePanel.addEventListener('click', (event) => event.stopPropagation());

  document.body.appendChild(appearancePanel);
  insertImageFileInput = document.createElement('input');

  insertImageFileInput.type = 'file';

  insertImageFileInput.accept = 'image/png,image/jpeg,image/webp,image/gif';

  insertImageFileInput.hidden = true;

  insertImageFileInput.dataset.editorChrome = 'true';

  insertImageFileInput.addEventListener('change', () => {

    readInsertImageFile(insertImageFileInput.files && insertImageFileInput.files[0]);

  });

  document.body.appendChild(insertImageFileInput);

  insertPanel = document.createElement('div');

  insertPanel.id = 'edit-insert-panel';

  insertPanel.dataset.editorChrome = 'true';

  insertPanel.setAttribute('role', 'menu');

  insertPanel.setAttribute('aria-label', M.insertPanelTitle);

  insertPanel.setAttribute('aria-hidden', 'true');

  insertPanel.style.cssText =

    'position:fixed;left:0;top:0;transform:none;z-index:105;display:none;' +

    'width:min(268px,calc(100vw - 20px));box-sizing:border-box;flex-direction:column;gap:8px;' +

    'padding:14px 14px 12px;border:1px solid rgba(18,24,30,.18);border-radius:14px;' +

    'background:rgba(255,255,255,.96);color:#182028;backdrop-filter:blur(14px);' +

    '-webkit-backdrop-filter:blur(14px);box-shadow:0 16px 42px rgba(0,0,0,.28);' +

    'font-family:var(--font-body);pointer-events:auto;';

  const insertTitle = document.createElement('strong');

  insertTitle.textContent = M.insertPanelTitle;

  insertTitle.style.cssText = 'font:800 14px/1.2 var(--font-body);';

  const insertHelp = document.createElement('span');

  insertHelp.textContent = M.insertPanelHelp;

  insertHelp.style.cssText = 'font:500 11px/1.4 var(--font-body);opacity:.72;';

  function makeInsertMenuButton(key, label, glyph, onClick) {

    const button = document.createElement('button');

    button.type = 'button';

    button.dataset.insertObject = key;

    button.setAttribute('role', 'menuitem');

    button.setAttribute('aria-label', label);

    button.style.cssText =

      'display:flex;align-items:center;gap:10px;width:100%;min-height:42px;padding:7px 9px;' +

      'border:1px solid rgba(18,24,30,.14);border-radius:9px;background:rgba(255,255,255,.58);' +

      'color:inherit;text-align:left;cursor:pointer;font:700 12px/1.2 var(--font-body);';

    const glyphNode = document.createElement('span');

    glyphNode.textContent = glyph;

    glyphNode.setAttribute('aria-hidden', 'true');

    glyphNode.style.cssText = 'display:inline-grid;place-items:center;width:24px;height:24px;border-radius:6px;background:rgba(15,118,110,.12);font:800 14px/1 var(--font-mono);';

    const labelNode = document.createElement('span');

    labelNode.textContent = label;

    button.append(glyphNode, labelNode);

    button.addEventListener('click', (event) => {

      event.stopPropagation();

      toggleInsertPanel(false);

      onClick();

    });

    return button;

  }

  insertPanel.append(

    insertTitle,

    insertHelp,

    makeInsertMenuButton('text', M.insertTextBox, 'T', () => armInsertObject('text', null)),

    makeInsertMenuButton('rect', M.insertRect, '□', () => armInsertObject('shape', 'rect')),

    makeInsertMenuButton('round-rect', M.insertRoundRect, '▢', () => armInsertObject('shape', 'round-rect')),

    makeInsertMenuButton('ellipse', M.insertEllipse, '○', () => armInsertObject('shape', 'ellipse'))

  );

  insertPanel.addEventListener('mousedown', (event) => event.stopPropagation());

  insertPanel.addEventListener('click', (event) => event.stopPropagation());

  document.body.appendChild(insertPanel);



  document.addEventListener('mousedown', (event) => {

    if (!editMode || !pendingInsertKind || event.button !== 0) return;

    if (isEditorChromeTarget(event.target)) return;

    const slide = document.querySelector('.slide.active');

    const container = insertionContainer(slide);

    if (!slide || !container || !slide.contains(event.target)) return;

    if (textEditingEl) endTextEdit();

    insertDrawState = {

      slide: slide,

      container: container,

      startX: event.clientX,

      startY: event.clientY,

      moved: false

    };

    event.preventDefault();

    event.stopImmediatePropagation();

    lockPointerSelection();

  }, true);

  const presetThemeObserver = new MutationObserver(() => {

    cachedPresetPaletteKey = '';

    cachedPresetPalette = null;

    lastPaletteSignature = null;

    refreshColorSwatches();

    updateAppearanceControls();

    if (selectedEl) updateSelectionBadge();

  });

  presetThemeObserver.observe(document.documentElement, {

    attributes: true,

    attributeFilter: ['style', 'class', 'data-preset-theme', 'data-theme-id', 'data-theme-kind']

  });

  document.addEventListener('mousedown', (event) => {

    if (!appearancePanel || appearancePanel.style.display === 'none') return;

    if (appearancePanel.contains(event.target) || (appearanceBtn && appearanceBtn.contains(event.target))) return;

    toggleAppearancePanel(false);

  });

  document.addEventListener('mousedown', (event) => {

    if (!insertPanel || insertPanel.style.display === 'none') return;

    if (insertPanel.contains(event.target) || (insertBtn && insertBtn.contains(event.target))) return;

    toggleInsertPanel(false);

  });

  document.addEventListener('keydown', (event) => {

    if (event.key === 'Escape' && appearancePanel && appearancePanel.style.display !== 'none') {

      toggleAppearancePanel(false);

    }

  });

  document.addEventListener('keydown', (event) => {

    if (event.key === 'Escape' && insertPanel && insertPanel.style.display !== 'none') {

      toggleInsertPanel(false);

    }

  });

  window.addEventListener('resize', positionAppearancePanel);

  window.addEventListener('resize', positionInsertPanel);

  window.addEventListener('scroll', positionAppearancePanel, true);

  window.addEventListener('scroll', positionInsertPanel, true);

  updateAppearanceControls();



  textToolRow = document.createElement('div');

  textToolRow.id = 'edit-text-tools';

  textToolRow.style.cssText = 'display:flex;align-items:center;gap:5px;padding-left:0;';

  textToolRow.append(boldBtn, italicBtn, underlineBtn);

  textAlignToolRow = document.createElement('div');

  textAlignToolRow.id = 'edit-text-align-tools';

  textAlignToolRow.style.cssText = 'display:flex;align-items:center;gap:5px;border-left:1px solid rgba(18,24,30,.12);padding-left:10px;';

  textAlignToolRow.append(alignLeftBtn, alignCenterBtn, alignRightBtn, verticalTopBtn, verticalCenterBtn, verticalBottomBtn);



  groupToolRow = document.createElement('div');

  groupToolRow.id = 'edit-group-tools';

  groupToolRow.style.cssText = 'display:none;align-items:center;gap:5px;border-left:1px solid rgba(18,24,30,.12);padding-left:10px;';

  groupToolRow.append(groupBtn, editGroupMemberBtn, selectWholeGroupBtn);

  function alignElsIcon(mode) {

    const shapes = {

      left: '<path d="M4 3v18"/><path d="M7 6.5h11v3.5H7z"/><path d="M7 14h7v3.5H7z"/>',

      centerX: '<path d="M12 3v18"/><path d="M5 6.5h14v3.5H5z"/><path d="M8 14h8v3.5H8z"/>',

      right: '<path d="M20 3v18"/><path d="M6 6.5h11v3.5H6z"/><path d="M10 14h7v3.5h-7z"/>',

      top: '<path d="M3 4h18"/><path d="M6.5 7h3.5v11H6.5z"/><path d="M14 7h3.5v7H14z"/>',

      middle: '<path d="M3 12h18"/><path d="M6.5 5h3.5v14H6.5z"/><path d="M14 8h3.5v8H14z"/>',

      bottom: '<path d="M3 20h18"/><path d="M6.5 6h3.5v11H6.5z"/><path d="M14 10h3.5v7H14z"/>',

      distH: '<path d="M4 3v18"/><path d="M20 3v18"/><path d="M9 8h6v8H9z"/>',

      distV: '<path d="M3 4h18"/><path d="M3 20h18"/><path d="M8 9h8v6H8z"/>'

    }[mode];

    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' +

      shapes + '</svg>';

  }



  alignToolRow = document.createElement('div');

  alignToolRow.style.cssText = 'display:none;align-items:center;gap:5px;border-left:1px solid rgba(18,24,30,.12);padding-left:10px;';

  [

    ['left', M.alignElsLeft],

    ['centerX', M.alignElsCenterX],

    ['right', M.alignElsRight],

    ['top', M.alignElsTop],

    ['middle', M.alignElsMiddle],

    ['bottom', M.alignElsBottom]

  ].forEach((entry) => {

    const button = makeSelectionToolButton(entry[1], alignElsIcon(entry[0]), () => alignSelection(entry[0]));

    button.dataset.alignSelectionMode = entry[0];

    alignToolRow.append(button);

  });

  [

    ['x', M.distributeH, 'distH'],

    ['y', M.distributeV, 'distV']

  ].forEach((entry) => {

    const button = makeSelectionToolButton(entry[1], alignElsIcon(entry[2]), () => distributeSelection(entry[0]));

    button.dataset.distributeSelectionAxis = entry[0];

    alignToolRow.append(button);

  });



  peerAdvisoryRow = document.createElement('div');

  peerAdvisoryRow.style.cssText =

    'display:none;align-items:center;gap:8px;border-left:1px solid rgba(18,24,30,.12);padding-left:10px;';

  peerAdvisoryText = document.createElement('div');

  peerAdvisoryText.style.cssText = 'display:none;';

  peerApplyBtn = document.createElement('button');

  peerApplyBtn.type = 'button';

  peerApplyBtn.textContent = M.fontPeerApply;

  peerApplyBtn.style.cssText =

    'height:28px;padding:0 10px;border-radius:999px;border:0;background:#17201C;color:#fff;' +

    'font:700 11px/1 var(--font-body);cursor:pointer;white-space:nowrap;';

  peerApplyBtn.onclick = (e) => {

    e.stopPropagation();

    commitPendingChanges();

    applyFontToPeers();

  };

  peerAdvisoryRow.append(peerAdvisoryText, peerApplyBtn);

  [fontControlRow, colorControlRow, backgroundColorControlRow, peerAdvisoryRow, groupToolRow, textAlignToolRow].forEach((row) => {

    row.addEventListener('mousedown', (e) => e.stopPropagation());

    row.addEventListener('click', (e) => e.stopPropagation());

  });

  const badgeTextRow = document.createElement('div');

  badgeTextRow.dataset.role = 'text-tools-row';

  badgeTextRow.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:nowrap;min-height:28px;';

  const badgeColorRow = document.createElement('div');

  badgeColorRow.dataset.role = 'color-tools-row';

  badgeColorRow.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:nowrap;min-height:28px;';

  const badgeGroupRow = document.createElement('div');

  badgeGroupRow.dataset.role = 'group-tools-row';

  badgeGroupRow.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:nowrap;min-height:28px;';

  badgeTextRow.append(badgeLabel, fontControlRow);

  badgeColorRow.append(textToolRow, colorControlRow, backgroundColorControlRow);

  badgeGroupRow.append(groupToolRow, textAlignToolRow, alignToolRow, peerAdvisoryRow);

  selectionBadge.append(badgeHint, badgeTextRow, badgeColorRow, badgeGroupRow);

  selectionBadge.addEventListener('mousedown', (e) => e.stopPropagation());

  selectionBadge.addEventListener('click', (e) => e.stopPropagation());

  document.body.appendChild(selectionBadge);



  objectContextMenu = document.createElement('div');

  objectContextMenu.id = 'edit-object-context-menu';

  objectContextMenu.dataset.editorChrome = 'true';

  objectContextMenu.setAttribute('role', 'menu');

  objectContextMenu.setAttribute('aria-label', M.objectActions);

  objectContextMenu.setAttribute('aria-hidden', 'true');

  objectContextMenu.style.cssText =

    'display:none;position:fixed;z-index:2147483646;min-width:190px;padding:6px;' +

    'border:1px solid rgba(18,24,30,.14);border-radius:12px;background:rgba(255,255,255,.98);' +

    'box-shadow:0 16px 42px rgba(18,24,30,.22);backdrop-filter:blur(14px);';



  function makeContextMenuButton(label, shortcut, action, actionId, danger) {

    const button = document.createElement('button');

    button.type = 'button';

    button.dataset.action = actionId;

    button.setAttribute('role', 'menuitem');

    button.style.cssText =

      'width:100%;height:36px;padding:0 10px;border:0;border-radius:8px;background:transparent;' +

      'color:' + (danger ? '#B42318' : '#17201C') + ';font:700 13px/1 var(--font-body);cursor:pointer;display:flex;' +

      'align-items:center;justify-content:space-between;gap:18px;text-align:left;';

    const labelEl = document.createElement('span');

    labelEl.textContent = label;

    button.appendChild(labelEl);

    if (shortcut) {

      const shortcutEl = document.createElement('span');

      shortcutEl.textContent = shortcut;

      shortcutEl.style.cssText = 'color:rgba(18,24,30,.46);font-weight:600;font-size:11px;';

      button.appendChild(shortcutEl);

    }

    button.addEventListener('mouseenter', () => {

      if (!button.disabled) button.style.background = danger ? 'rgba(180,35,24,.08)' : 'rgba(15,118,110,.10)';

    });

    button.addEventListener('mouseleave', () => {

      button.style.background = 'transparent';

    });

    button.addEventListener('click', (e) => {

      e.preventDefault();

      e.stopPropagation();

      if (button.disabled) return;

      commitPendingChanges();

      hideObjectContextMenu();

      action();

    });

    return button;

  }



  contextDuplicateBtn = makeContextMenuButton(M.duplicate, 'Ctrl+D', duplicateSelection, 'context-duplicate', false);

  contextBringFrontBtn = makeContextMenuButton(M.bringFront, '', () => changeLayer(1), 'context-bring-front', false);

  contextSendBackBtn = makeContextMenuButton(M.sendBack, '', () => changeLayer(-1), 'context-send-back', false);

  contextGroupBtn = makeContextMenuButton(M.contextGroupAction, 'Ctrl+G', groupSelection, 'context-group', false);

  contextUngroupBtn = makeContextMenuButton(M.ungroupChange, 'Ctrl+Shift+G', ungroupSelection, 'context-ungroup', false);

  contextDeleteBtn = makeContextMenuButton(M.delete, 'Delete', deleteSelection, 'context-delete', true);

  objectContextMenu.append(

    contextDuplicateBtn,

    contextBringFrontBtn,

    contextSendBackBtn,

    contextGroupBtn,

    contextUngroupBtn,

    contextDeleteBtn

  );

  objectContextMenu.addEventListener('mousedown', (e) => e.stopPropagation());

  objectContextMenu.addEventListener('contextmenu', (e) => e.preventDefault());

  document.body.appendChild(objectContextMenu);



  document.addEventListener('contextmenu', (e) => {

    if (!editMode || isEditorChromeTarget(e.target)) {

      hideObjectContextMenu();

      return;

    }

    const el = resolvePointerTarget(e.target, e.clientX, e.clientY, e.isTrusted, e.shiftKey);

    if (!el) {

      hideObjectContextMenu();

      return;

    }

    e.preventDefault();

    e.stopPropagation();

    commitPendingChanges();

    selectContextTarget(el);

    showObjectContextMenu(e.clientX, e.clientY);

  }, true);



  document.addEventListener('mousedown', (e) => {

    if (objectContextMenu && !objectContextMenu.contains(e.target)) hideObjectContextMenu();

  }, true);

  window.addEventListener('resize', hideObjectContextMenu);

  window.addEventListener('scroll', hideObjectContextMenu, true);



  document.addEventListener('mousedown', (e) => {

    if (!editMode) return;

    const target = e.target;

    if (isEditorChromeTarget(target)) {

      pointerDownSelectedEl = null;

      pointerDownWasSelected = false;

      pendingTextEditEl = null;

      return;

    }

    if (e.button === 2) return;

    const directGroupSelection = e.ctrlKey || e.metaKey;

    const el = resolvePointerTarget(
      target,
      e.clientX,
      e.clientY,
      e.isTrusted,
      e.shiftKey,
      directGroupSelection
    );

    commitPendingChanges();

    pointerDownSelectedEl = el;

    pointerDownWasSelected = !!(pointerDownSelectedEl

      && selectedEl === pointerDownSelectedEl

      && activeSelectedEls().length === 1);

    pointerInteractionMoved = false;

    pendingTextEditEl = !e.shiftKey && el && isTextEditableElement(el)
      && (directGroupSelection || pointerDownWasSelected)
      ? el
      : null;

    if (textEditingEl && (!el || el !== textEditingEl)) endTextEdit();

    if (el) {

      const root = editableRoot(el);

      const path = groupPath(root);

      const isLayer = el.hasAttribute && el.hasAttribute('data-edit-layer');

      const editScope = currentGroupEditScope();

      if (directGroupSelection) {

        // The modifier is a temporary bypass, not an ungroup or a persistent
        // drill-in mode. Ctrl/Cmd+Shift keeps Shift's additive-selection role.
        selectElement(el, e.shiftKey);

      } else if (!e.shiftKey && editScope && editScope.kind === 'manual'

        && path.indexOf(editScope.groupId) >= 0) {

        const scopeDepth = path.indexOf(editScope.groupId);

        const childGroupId = scopeDepth > 0 ? path[scopeDepth - 1] : '';

        if (childGroupId) {

          const members = groupMembers(root, childGroupId);

          setSelection(members, root, childGroupId);

          currentTool = 'move';

          pendingTextEditEl = null;

          applyEditableState();

          repositionHandles();

          updateSelectionBadge();

          showTransientReadout(M.groupHint);

        } else {

          selectElement(root, false);

        }

      } else if (e.shiftKey && (!isLayer || isGeneratedGroup(root))) {

        const depth = selectedGroupDepth >= 0 ? Math.min(selectedGroupDepth, path.length - 1) : path.length - 1;

        const id = depth >= 0 ? path[depth] : '';

        const members = id ? groupMembers(root, id) : [root];

        const existing = activeSelectedEls();

        const remove = members.every((member) => existing.indexOf(member) >= 0);

        const next = remove

          ? existing.filter((item) => members.indexOf(item) < 0)

          : Array.from(new Set(existing.concat(members)));

        setSelection(next, next[0] || null, null, depth);

        currentTool = next.length ? 'move' : null;

        pendingTextEditEl = null;

        applyEditableState();

        repositionHandles();

        updateSelectionBadge();

      } else if (!e.shiftKey && activeSelectedEls().length > 1 && activeSelectedEls().indexOf(el) >= 0) {

        // A multi-selection is already a temporary operation group. Preserve

        // it on pointer-down so the drag initializer can snapshot and move

        // every selected element together, even before Ctrl+G is used.

        currentTool = 'move';

        pendingTextEditEl = null;

        applyEditableState();

        repositionHandles();

        updateSelectionBadge();

      } else if (!e.shiftKey && !isLayer && selectedGroupId && activeSelectedEls().indexOf(root) >= 0) {

        // A formal manual group is atomic during ordinary interaction. The

        // selected member is only a drag anchor; it must not become a drill-in

        // target unless the user explicitly enters edit-single mode.

        currentTool = 'move';

        pendingTextEditEl = null;

        applyEditableState();

        repositionHandles();

        updateSelectionBadge();

        showTransientReadout(M.groupHint);

      } else if (!e.shiftKey && !isLayer && path.length) {

        const id = path[path.length - 1];

        const members = groupMembers(root, id);

        setSelection(members, root, id);

        currentTool = 'move';

        pendingTextEditEl = null;

        applyEditableState();

        repositionHandles();

        updateSelectionBadge();

        showTransientReadout(M.groupHint);



      } else {

        selectElement(el, e.shiftKey);

      }

    } else {

      const editScope = currentGroupEditScope();

      if (editScope && groupEditScopeContainsPoint(editScope, e.clientX, e.clientY)) return;

      clearGroupEditScopes();

      deselectElement();

    }

  });



  document.addEventListener('mousedown', (e) => {

    if (!editMode) return;

    const el = pointerDownSelectedEl;

    if (!el) return;

    if (textEditingEl === el || (textEditingEl && textEditingEl.contains(e.target))) return;

    if (isTypingContext()) return;

    e.preventDefault();

    dragCandidateEl = el;

    dragCandidateStartX = e.clientX;

    dragCandidateStartY = e.clientY;

    dragScale = getScale();

    dragStartState = measureElementState(el);

    elStartLeft = dragStartState.left;

    elStartTop = dragStartState.top;

    const group = activeSelectedEls();

    dragGroupStartStates = group.indexOf(el) >= 0 && group.length > 1

      ? group.map((item) => ({

          el: item,

          key: elementKey(item),

          before: measureElementState(item),

          visual: captureVisualTransformStart(item)

        }))

      : null;

    dragGrabOffsetX = 0;

    dragGrabOffsetY = 0;

  });



  document.addEventListener('mousedown', (e) => {

    if (!editMode || textEditingEl) return;

    const target = e.target;

    if (e.button !== 0 || pointerDownSelectedEl) return;

    if (isEditorChromeTarget(target)) return;

    if (!(player && player.contains(target))) return;

    marqueeCandidate = true;

    marqueeStartX = e.clientX;

    marqueeStartY = e.clientY;

  });



  window.addEventListener('mousemove', (e) => {

    if (!editMode) return;



    if (insertDrawState) {

      e.preventDefault();

      updateInsertDrawPreview(e);

      return;

    }



    if (marqueeCandidate && !dragEl && !resizeEl) {

      const moved =

        Math.abs(e.clientX - marqueeStartX) > DRAG_THRESHOLD ||

        Math.abs(e.clientY - marqueeStartY) > DRAG_THRESHOLD;

      if (moved && !marqueeActive) {

        marqueeActive = true;

        lockPointerSelection();

        marqueeBox.style.display = 'block';

      }

      if (marqueeActive) {

        e.preventDefault();

        marqueeBox.style.left = Math.min(marqueeStartX, e.clientX) + 'px';

        marqueeBox.style.top = Math.min(marqueeStartY, e.clientY) + 'px';

        marqueeBox.style.width = Math.abs(e.clientX - marqueeStartX) + 'px';

        marqueeBox.style.height = Math.abs(e.clientY - marqueeStartY) + 'px';

      }

    }



    if (dragCandidateEl && !dragEl) {

      const moved =

        Math.abs(e.clientX - dragCandidateStartX) > DRAG_THRESHOLD ||

        Math.abs(e.clientY - dragCandidateStartY) > DRAG_THRESHOLD;

      if (moved) {

        pointerInteractionMoved = true;

        e.preventDefault();

        dragEl = dragCandidateEl;

        dragStartX = dragCandidateStartX;

        dragStartY = dragCandidateStartY;

        currentTool = 'move';

        lockPointerSelection();

        if (!originalPositions.has(dragEl)) {

          originalPositions.set(dragEl, { left: elStartLeft, top: elStartTop });

        }

        (dragGroupStartStates || []).forEach((item) => {

          if (!originalPositions.has(item.el)) {

            originalPositions.set(item.el, { left: item.before.left, top: item.before.top });

          }

        });

        const dragTargets = dragGroupStartStates && dragGroupStartStates.length

          ? dragGroupStartStates.map((item) => item.el)

          : [dragEl];

        const promotableModules = dragTargets.filter((item) => (

          item

          && item.dataset

          && item.dataset.editStructure === 'module'

        ));

        if (promotableModules.length) {

          const slide = promotableModules[0].closest('.slide');

          const zValues = slide

            ? Array.from(slide.querySelectorAll('.el[data-edit-structure="module"]'))

                .map((item) => parseInt(getComputedStyle(item).zIndex, 10))

                .filter((value) => !Number.isNaN(value))

            : [];

          const maxZ = zValues.length ? Math.max.apply(null, zValues) : 1;

          promotableModules.forEach((item, index) => {

            setUserStyle(item, 'z-index', String(maxZ + index + 1));

          });

        }

      }

    }



    if (dragEl) {

      const newLeft = Math.round((elStartLeft + (e.clientX - dragStartX) / dragScale) * 10) / 10;

      const newTop = Math.round((elStartTop + (e.clientY - dragStartY) / dragScale) * 10) / 10;

      if (dragGroupStartStates && dragGroupStartStates.length) {

        const dx = newLeft - dragStartState.left;

        const dy = newTop - dragStartState.top;

        dragGroupStartStates.forEach((item) => applyVisualTranslation(item.el, item.visual, dx, dy));

      } else {

        setUserStyle(dragEl, 'left', newLeft + 'px');

        setUserStyle(dragEl, 'top', newTop + 'px');

      }

      const movedEls = dragGroupStartStates && dragGroupStartStates.length ? dragGroupStartStates.map((item) => item.el) : [dragEl];

      if (!(dragGroupStartStates && dragGroupStartStates.length)) applySnap(movedEls, e.altKey);

      const movedBox = combinedStageBox(movedEls);

      setReadout(elementLabel(dragEl) + ' left ' + Math.round(movedBox.left) + 'px, top ' + Math.round(movedBox.top) + 'px');

      if (movedEls.indexOf(selectedEl) >= 0) repositionHandles();

      updateAlignmentGuides(movedEls);

    }



    if (!resizeEl) return;

    pointerInteractionMoved = true;

    const dx = (e.clientX - resizeStartX) / resizeScale;

    const dy = (e.clientY - resizeStartY) / resizeScale;

    let newLeft = resizeStartLeft;

    let newTop = resizeStartTop;

    let newW = resizeStartW;

    let newH = resizeStartH;

    const isCorner = resizeHandle.length === 2;



    const centerResize = e.ctrlKey || e.metaKey;

    const resizeFactor = centerResize ? 2 : 1;



    if (isCorner) {

      const proposedW =

        resizeStartW +

        (resizeHandle.indexOf('e') >= 0 ? dx * resizeFactor : (resizeHandle.indexOf('w') >= 0 ? -dx * resizeFactor : 0));

      const proposedH =

        resizeStartH +

        (resizeHandle.indexOf('s') >= 0 ? dy * resizeFactor : (resizeHandle.indexOf('n') >= 0 ? -dy * resizeFactor : 0));

      const scaleW = proposedW / resizeStartW;

      const scaleH = proposedH / resizeStartH;

      let scale = Math.abs(scaleW - 1) >= Math.abs(scaleH - 1) ? scaleW : scaleH;

      scale = Math.max(scale, MIN_SIZE / resizeStartW, MIN_SIZE / resizeStartH);

      newW = Math.round(resizeStartW * scale);

      newH = Math.round(resizeStartH * scale);

      if (centerResize) {

        newLeft = Math.round((resizeStartLeft + (resizeStartW - newW) / 2) * 10) / 10;

        newTop = Math.round((resizeStartTop + (resizeStartH - newH) / 2) * 10) / 10;

      } else {

        if (resizeHandle.indexOf('w') >= 0) newLeft = Math.round(resizeStartLeft + (resizeStartW - newW));

        if (resizeHandle.indexOf('n') >= 0) newTop = Math.round(resizeStartTop + (resizeStartH - newH));

      }

    } else {

      if (resizeHandle === 'e') newW = Math.max(MIN_SIZE, Math.round(resizeStartW + dx * resizeFactor));

      if (resizeHandle === 'w') {

        newW = Math.max(MIN_SIZE, Math.round(resizeStartW - dx * resizeFactor));

      }

      if (resizeHandle === 's') newH = Math.max(MIN_SIZE, Math.round(resizeStartH + dy * resizeFactor));

      if (resizeHandle === 'n') {

        newH = Math.max(MIN_SIZE, Math.round(resizeStartH - dy * resizeFactor));

      }

      if (centerResize) {

        if (resizeHandle === 'e' || resizeHandle === 'w') newLeft = Math.round((resizeStartLeft + (resizeStartW - newW) / 2) * 10) / 10;

        if (resizeHandle === 'n' || resizeHandle === 's') newTop = Math.round((resizeStartTop + (resizeStartH - newH) / 2) * 10) / 10;

      } else {

        if (resizeHandle === 'w') newLeft = Math.round(resizeStartLeft + (resizeStartW - newW));

        if (resizeHandle === 'n') newTop = Math.round(resizeStartTop + (resizeStartH - newH));

      }

    }



    const hasGroupResize = !!(resizeGroupStartStates && resizeGroupStartStates.length);

    let lockedAspectScale = null;

    const aspectLockedResize = resizeMode.endsWith('-proportional');

    if (aspectLockedResize) {

      const locked = lockResizeAspect(resizeHandle, {

        width: newW,

        height: newH

      }, centerResize);

      newLeft = locked.left;

      newTop = locked.top;

      newW = locked.width;

      newH = locked.height;

      lockedAspectScale = locked.scale;

    }



    if (hasGroupResize && !aspectLockedResize) {

      const bounded = clampGroupResizeToContentArea(

        resizeGroupStartStates, newLeft, newTop, newW, newH, resizeHandle, centerResize

      );

      newLeft = bounded.left;

      newTop = bounded.top;

      newW = bounded.width;

      newH = bounded.height;


    }



    if (hasGroupResize) {
      // Side handles edit layout frames. Horizontal resizing changes member

      // and layer widths without distorting glyphs; vertical resizing consumes

      // spacing and line height before reducing type at collision.

      const horizontalAxis = resizeHandle === 'e' || resizeHandle === 'w';

      const verticalAxis = resizeHandle === 'n' || resizeHandle === 's';

      let scaleX = lockedAspectScale || (horizontalAxis ? newW / resizeStartW : 1);

      let scaleY = lockedAspectScale || (verticalAxis ? newH / resizeStartH : 1);

      if (verticalAxis && !lockedAspectScale) {

        scaleY = resolveAdaptiveAxisScale(resizeGroupStartStates, scaleY, 'vertical');
        newH = resizeStartH * scaleY;
        newTop = anchoredResizeAxisStart(
          resizeStartTop, resizeStartH, newH, resizeHandle, centerResize
        );
        const bounded = clampGroupResizeToContentArea(
          resizeGroupStartStates, newLeft, newTop, newW, newH, resizeHandle, centerResize
        );
        newTop = bounded.top;
        newH = bounded.height;
        scaleY = newH / resizeStartH;

        const collisionSafeBox = applyCollisionSafeVerticalGroupResize(

          resizeGroupStartStates, newTop, newH, scaleY, resizeHandle, centerResize

        );

        newTop = collisionSafeBox.top;

        newH = collisionSafeBox.height;

        scaleY = newH / resizeStartH;

      } else if (horizontalAxis && !lockedAspectScale) {

        scaleX = resolveAdaptiveAxisScale(resizeGroupStartStates, scaleX, 'horizontal');
        newW = resizeStartW * scaleX;
        newLeft = anchoredResizeAxisStart(
          resizeStartLeft, resizeStartW, newW, resizeHandle, centerResize
        );
        const bounded = clampGroupResizeToContentArea(
          resizeGroupStartStates, newLeft, newTop, newW, newH, resizeHandle, centerResize
        );
        newLeft = bounded.left;
        newW = bounded.width;
        scaleX = newW / resizeStartW;

        resizeGroupStartStates.forEach((item) => {

          const targetLeft = newLeft + (item.box.left - resizeStartLeft) * scaleX;

          setUserStyle(item.el, 'left', (Math.round((item.before.left + targetLeft - item.box.left) * 10) / 10) + 'px');

          setUserStyle(item.el, 'top', item.before.top + 'px');

          applyAdaptiveHorizontalGroupResize(item, scaleX);

        });

      } else {

        resizeGroupStartStates.forEach((item) => {

          const targetLeft = newLeft + (item.box.left - resizeStartLeft) * scaleX;

          const targetTop = newTop + (item.box.top - resizeStartTop) * scaleY;

          setUserStyle(item.el, 'left', (Math.round((item.before.left + targetLeft - item.box.left) * 10) / 10) + 'px');

          setUserStyle(item.el, 'top', (Math.round((item.before.top + targetTop - item.box.top) * 10) / 10) + 'px');

          applyVisualScale(item.el, item.visual, scaleX, scaleY);

        });

      }

      repositionHandles();

      updateAlignmentGuides(resizeGroupStartStates.map((item) => item.el));

      setReadout(t(M.multiSelected, { count: resizeGroupStartStates.length }) + ' width ' + Math.round(newW) + 'px, height ' + Math.round(newH) + 'px');

    } else {

      if (resizeAdaptiveStart) {

        if (resizeMode === 'composite-height') {

          // The adaptive vertical pass owns the content floor. Do not clamp

          // the requested frame before it can consume spacing and typography.

        }

        if (resizeAdaptiveStart.visual.positioned !== false) {

          setUserStyle(resizeEl, 'left', (Math.round((resizeStartState.left + newLeft - resizeStartLeft) * 10) / 10) + 'px');

          setUserStyle(resizeEl, 'top', (Math.round((resizeStartState.top + newTop - resizeStartTop) * 10) / 10) + 'px');

        }

        if (resizeMode === 'composite-width') {

          let bounded = clampSingleAdaptiveHorizontalResize(

            resizeAdaptiveStart, newLeft, newW, resizeHandle, centerResize

          );

          newLeft = bounded.left;

          newW = bounded.width;

          const safeScale = resolveAdaptiveAxisScale(
            [resizeAdaptiveStart], newW / resizeStartW, 'horizontal'
          );
          newW = resizeStartW * safeScale;
          newLeft = anchoredResizeAxisStart(
            resizeStartLeft, resizeStartW, newW, resizeHandle, centerResize
          );
          bounded = clampSingleAdaptiveHorizontalResize(
            resizeAdaptiveStart, newLeft, newW, resizeHandle, centerResize
          );
          newLeft = bounded.left;
          newW = bounded.width;

          setUserStyle(resizeEl, 'left', (Math.round((resizeStartState.left + newLeft - resizeStartLeft) * 10) / 10) + 'px');

          applyAdaptiveHorizontalGroupResize(resizeAdaptiveStart, newW / resizeStartW);

        } else {

          let bounded = clampSingleAdaptiveVerticalResize(

            resizeAdaptiveStart, newTop, newH, resizeHandle, centerResize

          );

          newTop = bounded.top;

          newH = bounded.height;

          const safeScale = resolveAdaptiveAxisScale(
            [resizeAdaptiveStart], newH / resizeStartH, 'vertical'
          );
          newH = resizeStartH * safeScale;
          newTop = anchoredResizeAxisStart(
            resizeStartTop, resizeStartH, newH, resizeHandle, centerResize
          );
          bounded = clampSingleAdaptiveVerticalResize(
            resizeAdaptiveStart, newTop, newH, resizeHandle, centerResize
          );
          newTop = bounded.top;
          newH = bounded.height;


          setUserStyle(resizeEl, 'top', (Math.round((resizeStartState.top + newTop - resizeStartTop) * 10) / 10) + 'px');

          applyAdaptiveVerticalGroupResize(resizeAdaptiveStart, newH / resizeStartH);

        }

      } else if (resizeVisualStart) {

        if (resizeVisualStart.positioned !== false) {

          setUserStyle(resizeEl, 'left', (Math.round((resizeStartState.left + newLeft - resizeStartLeft) * 10) / 10) + 'px');

          setUserStyle(resizeEl, 'top', (Math.round((resizeStartState.top + newTop - resizeStartTop) * 10) / 10) + 'px');

        }

        const scaleX = lockedAspectScale || newW / resizeStartW;

        const scaleY = lockedAspectScale || newH / resizeStartH;

        applyVisualScale(resizeEl, resizeVisualStart, scaleX, scaleY);

      } else {

        setUserStyle(resizeEl, 'left', newLeft + 'px');

        setUserStyle(resizeEl, 'top', newTop + 'px');

        if (resizeFrameWidthOnly) {

          setUserStyle(resizeEl, 'width', newW + 'px');

          resizeEl.dataset.editFrameWidth = 'manual';

          resizeEl.dataset.editUserSized = '1';



        } else if (resizeFrameHeightOnly) {

          setUserStyle(resizeEl, 'height', newH + 'px');

          resizeEl.dataset.editFrameHeight = 'manual';

          resizeEl.dataset.editUserSized = '1';

        } else {

          setUserStyle(resizeEl, 'width', newW + 'px');

          setUserStyle(resizeEl, 'height', newH + 'px');

          applyFontScale(resizeEl, resizeHandle, newW, newH);

        }

      }

      repositionHandles();

      updateAlignmentGuides([resizeEl]);

      setReadout(resizeFrameWidthOnly

        ? M.frameWidthLabel + ' ' + newW + 'px'

        : (resizeFrameHeightOnly

          ? elementLabel(resizeEl) + ' height ' + newH + 'px'

          : elementLabel(resizeEl) + ' width ' + newW + 'px, height ' + newH + 'px, font ' + Math.round(getCurrentFontSize(resizeEl)) + 'px'));

    }

    updateFontControls();

  });



  window.addEventListener('mouseup', (e) => {

    if (insertDrawState) {

      e.preventDefault();

      finishInsertDraw(e);

      return;

    }

    if (marqueeActive) {

      marqueeBox.style.display = 'none';

      const left = Math.min(marqueeStartX, e.clientX);

      const top = Math.min(marqueeStartY, e.clientY);

      const right = Math.max(marqueeStartX, e.clientX);

      const bottom = Math.max(marqueeStartY, e.clientY);

      const slide = document.querySelector('.slide.active');

      const hits = slide ? marqueeSelectionTargets(slide).filter((el) => {

        const rect = visualSelectionRect(el);

        return !(rect.right < left || rect.left > right || rect.bottom < top || rect.top > bottom);

      }) : [];

      if (hits.length) {

        setSelection(hits, hits[0]);

        currentTool = 'move';

        applyEditableState();

        repositionHandles();

        updateSelectionBadge();

        restoreReadout();

        if (hits.length > 1) showTransientReadout(t(M.multiSelected, { count: hits.length }));

      }

      unlockPointerSelection();

    }

    marqueeActive = false;

    marqueeCandidate = false;



    if (dragEl) {

      if (dragGroupStartStates && dragGroupStartStates.length) {

        pushCommand({

          type: 'batch',

          label: M.moveChange + ' ' + t(M.multiSelected, { count: dragGroupStartStates.length }),

          itemType: 'move',

          items: dragGroupStartStates.map((item) => ({

            type: 'move',

            el: item.el,

            key: item.key,

            before: item.before,

            after: measureElementState(item.el)

          }))

        });

        dragGroupStartStates.forEach((item) => recordChange(item.el));

      } else {

        pushCommand({

          type: 'move',

          el: dragEl,

          key: elementKey(dragEl),

          before: dragStartState,

          after: measureElementState(dragEl)

        });

        recordChange(dragEl);

      }

      currentTool = selectedEl ? 'move' : null;

      restoreReadout();

      scheduleDraftSave();

    }

    dragEl = null;

    dragCandidateEl = null;

    dragStartState = null;

    dragGroupStartStates = null;

    hideGuides();

    unlockPointerSelection();



    if (resizeEl) {

      if (resizeEl.dataset && resizeEl.dataset.editFit === 'text') resizeEl.dataset.editUserSized = '1';

      const verticalResize = resizeHandle === 'n' || resizeHandle === 's';

      if (resizeGroupStartStates && resizeGroupStartStates.length) {

        const items = [];

        resizeGroupStartStates.forEach((item) => {

          items.push({

            type: 'resize',

            axis: verticalResize ? 'vertical' : '',

            verticalOwnsHeight: verticalResize,

            el: item.el,

            key: item.key,

            before: item.before,

            after: measureElementState(item.el)

          });

          const historyLayers = resizeHandle === 'n' || resizeHandle === 's'

            ? (item.verticalHistoryItems || item.layers || [])

            : (item.layers || []);

          historyLayers.forEach((layer) => {

            items.push({

              type: 'resize',

              axis: verticalResize ? 'vertical' : '',

              verticalOwnsHeight: verticalResize && !!layer.verticalOwnsHeight,

              el: layer.el,

              key: elementKey(layer.el),

              before: layer.before,

              after: measureElementState(layer.el)

            });

          });

        });

        pushCommand({ type: 'batch', label: M.resizeChange + ' ' + t(M.multiSelected, { count: resizeGroupStartStates.length }), itemType: 'resize', items: items });

        items.forEach((item) => recordChange(item.el));

      } else if (resizeAdaptiveStart) {

        const items = [

          {

            type: 'resize',

            axis: verticalResize ? 'vertical' : '',

            verticalOwnsHeight: verticalResize,

            el: resizeEl,

            key: elementKey(resizeEl),

            before: resizeStartState,

            after: measureElementState(resizeEl)

          }

        ];

        const historyLayers = resizeHandle === 'n' || resizeHandle === 's'

          ? (resizeAdaptiveStart.verticalHistoryItems || resizeAdaptiveStart.layers || [])

          : (resizeAdaptiveStart.layers || []);

        historyLayers.forEach((layer) => {

          items.push({

            type: 'resize',

            axis: verticalResize ? 'vertical' : '',

            verticalOwnsHeight: verticalResize && !!layer.verticalOwnsHeight,

            el: layer.el,

            key: elementKey(layer.el),

            before: layer.before,

            after: measureElementState(layer.el)

          });

        });

        pushCommand({ type: 'batch', label: M.resizeChange + ' ' + elementLabel(resizeEl), itemType: 'resize', items: items });

        items.forEach((item) => recordChange(item.el));

      } else {

        pushCommand({

          type: 'resize',

          axis: verticalResize ? 'vertical' : '',

          verticalOwnsHeight: verticalResize,

          el: resizeEl,

          key: elementKey(resizeEl),

          before: resizeStartState,

          after: measureElementState(resizeEl)

        });

        recordChange(resizeEl);

      }

      currentTool = selectedEl ? 'move' : null;

      restoreReadout();

      scheduleDraftSave();

      resizeEl = null;

      resizeHandle = null;

      resizeStartState = null;

      resizeGroupStartStates = null;

      resizeVisualStart = null;

      resizeAdaptiveStart = null;

      resizeMode = 'none';

      resizeFrameWidthOnly = false;

      resizeFrameHeightOnly = false;

      resizeTypographyStart = [];

      hideGuides();

      repositionHandles();

      updateSelectionBadge();

    }
    if (pendingTextEditEl && !pointerInteractionMoved && !textEditingEl) {

      beginTextEdit(pendingTextEditEl);

    }

    pendingTextEditEl = null;

  });



  document.addEventListener('slidesreordered', (event) => {

    const before = Array.isArray(event.detail && event.detail.before) ? event.detail.before.slice() : [];

    const after = Array.isArray(event.detail && event.detail.after) ? event.detail.after.slice() : [];

    if (!before.length || !after.length || before.join('|') === after.join('|')) return;

    updateSlideOrderDirty();

    pushCommand({ type: 'slide-order', label: M.slideOrderChange, before: before, after: after });

    scheduleDraftSave();

  });



  document.addEventListener('slidechange', () => {

    if (!editMode) return;

    if (pendingInsertKind || insertDrawState) cancelPendingInsert();

    if (textEditingEl) endTextEdit();

    clearGroupEditScopes();

    setSelection([], null);

    currentTool = null;

    hideHandles();

    updateModePanel();

    lastPaletteSignature = null;

    refreshColorSwatches();

    updateAppearanceControls();

    updateSelectionBadge();

  });



  window.addEventListener('resize', () => {

    if (selectedEl) repositionHandles();

    updateToolbarLayout();

    updateSelectionBadge();

  });



  document.addEventListener('beforeinput', (e) => {

    if (!editMode || !textEditingEl) return;

    const el = e.target.closest ? e.target.closest('[data-edit-layer],.el') : null;

    if (!el || textEditingEl !== el) return;

    textEditInputAnchor = captureTextHorizontalAnchor(el);

  });



  document.addEventListener('input', (e) => {

    if (!editMode) return;

    const el = e.target.closest ? e.target.closest('[data-edit-layer],.el') : null;

    if (!el || textEditingEl !== el) return;

    const anchor = textEditInputAnchor || captureTextHorizontalAnchor(el);

    fitTextElementToContent(el);

    restoreTextHorizontalAnchor(el, anchor);

    textEditInputAnchor = null;

    if (!originalTexts.has(el)) originalTexts.set(el, textEditStartHtml || el.innerHTML);

    textDirty.add(el);

    changedElements.add(el);

    updateActionStates();

    scheduleDraftSave();

    scheduleSelectionRefresh();

  });



  function sanitizedClone() {

    const clone = document.documentElement.cloneNode(true);

    clone.querySelectorAll('.el,[data-edit-layer]').forEach((el) => {

      el.removeAttribute('contenteditable');

      el.style.outline = '';

      el.style.outlineOffset = '';

      el.style.cursor = '';

      el.style.boxShadow = '';

      if (!el.style.cssText) el.removeAttribute('style');

    });

    ['#edit-draft-prompt', '#edit-help-panel', '#edit-mode-panel', '#edit-slide-style-panel', '#edit-selection-badge', '#edit-selection-frame', '#edit-color-popover'].forEach((selector) => {

      const node = clone.querySelector(selector);

      if (node) node.remove();

    });

    clone.querySelectorAll('.edit-resize-handle,.edit-guide-line,.edit-marquee-box,.edit-selection-member-frame,.edit-hard-break-marker').forEach((node) => node.remove());

    // Floating editor chrome is recreated on load.  The slide rail is the
    // structural editor shell, however, and must remain in a saved HTML
    // payload; removing it makes the deck reopen with only the active slide
    // visible and no thumbnail navigation.
    clone.querySelectorAll('[data-editor-chrome="true"]').forEach((node) => {

      if (node.id === 'slideRail' || node.closest?.('#slideRail')) return;

      node.remove();

    });

    clone.querySelectorAll(

      'read-frog,read-frog-selection,.read-frog-react-shadow-host,' +

      '[data-read-frog-react-shadow-css-key],[wxt-shadow-root-document-styles]'

    ).forEach((node) => node.remove());

    clone.querySelectorAll('[data-edit-clone]').forEach((node) => node.removeAttribute('data-edit-clone'));

    const clonedOverview = clone.querySelector('#overview');

    if (clonedOverview) {

      clonedOverview.innerHTML = '';

      clonedOverview.classList.remove('show');

    }

    const clonedCanvasBox = clone.querySelector('#canvasBox');

    if (clonedCanvasBox) clonedCanvasBox.removeAttribute('style');

    const clonedThumbList = clone.querySelector('#slideThumbList');

    if (clonedThumbList) clonedThumbList.innerHTML = '';

    const clonedPlayer = clone.querySelector('#player');

    if (clonedPlayer) {

      clonedPlayer.classList.add('editor-shell');

      clonedPlayer.classList.remove('rail-collapsed');

    }

    const clonedStage = clone.querySelector('#stage');

    if (clonedStage) {

      clonedStage.removeAttribute('style');

      const clonedSlides = Array.from(clonedStage.children).filter((node) => node.classList.contains('slide'));

      clonedSlides.forEach((slide, index) => slide.classList.toggle('active', index === 0));

    }

    const clonedProgress = clone.querySelector('#progress');

    if (clonedProgress) clonedProgress.classList.remove('show');

    const clonedProgressFill = clone.querySelector('#progressFill');

    if (clonedProgressFill) clonedProgressFill.removeAttribute('style');

    const clonedBar = clone.querySelector('#bar');

    if (clonedBar) clonedBar.classList.remove('show');

    const clonedBlackout = clone.querySelector('#blackout');

    if (clonedBlackout) clonedBlackout.classList.remove('show');

    const clonedBarInner = clone.querySelector('#barInner');

    if (clonedBarInner) {

      clonedBarInner.innerHTML = '';

      clonedBarInner.removeAttribute('style');

    }

    const clonedHint = clone.querySelector('#hint');

    if (clonedHint) {

      clonedHint.textContent = originalHintText;

      clonedHint.classList.remove('hide');

    }

    if (clone.body) {

      clone.body.removeAttribute('style');

      clone.body.removeAttribute('class');

    }

    return clone;

  }



  async function exportHtml() {

    try {

      const result = await saveViaFilePicker({ purpose: 'export' });

      if (result) {

        document.dispatchEvent(new CustomEvent('edithtmlexported', { detail: result }));

      }

      return result;

    } catch (err) {

      showTransientReadout(M.exportFailed, 2600);

      return null;

    }

  }



  function pptxHexByte(value) {

    return Math.round(Math.max(0, Math.min(255, value))).toString(16).padStart(2, '0').toUpperCase();

  }



  function pptxColor(value, opacityMultiplier) {

    const raw = String(value || '').trim();

    const multiplier = Number.isFinite(opacityMultiplier) ? opacityMultiplier : 1;

    if (!raw || raw === 'transparent') return '#00000000';

    const shortHex = raw.match(/^#([0-9a-f]{3,4})$/i);

    if (shortHex) {

      const chars = shortHex[1].split('');

      const alpha = chars[3] ? parseInt(chars[3] + chars[3], 16) / 255 : 1;

      return '#' + chars.slice(0, 3).map((char) => (char + char).toUpperCase()).join('') +

        pptxHexByte(alpha * multiplier * 255);

    }

    const longHex = raw.match(/^#([0-9a-f]{6})([0-9a-f]{2})?$/i);

    if (longHex) {

      const alpha = longHex[2] ? parseInt(longHex[2], 16) / 255 : 1;

      return '#' + longHex[1].toUpperCase() + pptxHexByte(alpha * multiplier * 255);

    }

    const rgb = raw.match(/rgba?\(\s*([+-]?[\d.]+)[,\s]+([+-]?[\d.]+)[,\s]+([+-]?[\d.]+)(?:\s*[,/]\s*([+-]?[\d.]+%?))?\s*\)/i);

    if (rgb) {

      const alphaValue = rgb[4]

        ? (rgb[4].endsWith('%') ? parseFloat(rgb[4]) / 100 : parseFloat(rgb[4]))

        : 1;

      return '#' + pptxHexByte(parseFloat(rgb[1])) + pptxHexByte(parseFloat(rgb[2])) +

        pptxHexByte(parseFloat(rgb[3])) + pptxHexByte(alphaValue * multiplier * 255);

    }

    const srgb = raw.match(/color\(\s*srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?\s*\)/i);

    if (srgb) {

      const alpha = srgb[4] ? parseFloat(srgb[4]) : 1;

      return '#' + pptxHexByte(parseFloat(srgb[1]) * 255) + pptxHexByte(parseFloat(srgb[2]) * 255) +

        pptxHexByte(parseFloat(srgb[3]) * 255) + pptxHexByte(alpha * multiplier * 255);

    }

    return '#00000000';

  }



  function pptxColorVisible(value) {

    return /^#[0-9A-F]{8}$/i.test(value || '') && String(value).slice(7, 9).toUpperCase() !== '00';

  }



  function pptxElementOpacity(el, slide) {

    let opacity = 1;

    let current = el;

    while (current && current !== slide) {

      const value = parseFloat(getComputedStyle(current).opacity);

      if (Number.isFinite(value)) opacity *= value;

      current = current.parentElement;

    }

    return Math.max(0, Math.min(1, opacity));

  }



  function pptxVisualScale(el, slide) {

    let scale = 1;

    let current = el;

    while (current && current !== slide) {

      const transform = getComputedStyle(current).transform;

      if (transform && transform !== 'none' && typeof DOMMatrixReadOnly === 'function') {

        try {

          const matrix = new DOMMatrixReadOnly(transform);

          const localScale = Math.sqrt(matrix.a * matrix.a + matrix.b * matrix.b);

          if (Number.isFinite(localScale) && localScale > 0) scale *= localScale;

        } catch (err) {

          // Keep the untransformed font size when the browser cannot parse a matrix.

        }

      }

      current = current.parentElement;

    }

    return scale;

  }



  function pptxResolvedFontFamily(value) {

    const candidates = String(value || '').split(',').map((item) => item.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean);

    const generics = new Set(['serif', 'sans-serif', 'monospace', 'system-ui', 'ui-serif', 'ui-sans-serif', 'ui-monospace']);

    const canvas = pptxResolvedFontFamily.canvas || (pptxResolvedFontFamily.canvas = document.createElement('canvas'));

    const context = canvas.getContext && canvas.getContext('2d');

    if (!context) return candidates[0] || 'Noto Sans TC';

    const probe = 'mmmmmmmmmmlliWW@@##中文';

    const width = (family) => {

      context.font = '72px ' + family;

      return context.measureText(probe).width;

    };

    const monoWidth = width('monospace');

    const serifWidth = width('serif');

    for (const candidate of candidates) {

      if (generics.has(candidate.toLowerCase())) continue;

      const escaped = candidate.replace(/"/g, '\\"');

      const measured = width('"' + escaped + '", monospace');

      if (Math.abs(measured - monoWidth) > 0.1 && Math.abs(measured - serifWidth) > 0.1) return candidate;

    }

    const generic = candidates.find((candidate) => generics.has(candidate.toLowerCase()));

    if (generic && /mono/i.test(generic)) return 'Consolas';

    return candidates.find((candidate) => !generics.has(candidate.toLowerCase())) || 'Noto Sans TC';

  }

  function pptxRotation(el) {

    const transform = getComputedStyle(el).transform;

    if (!transform || transform === 'none' || typeof DOMMatrixReadOnly !== 'function') return 0;

    try {

      const matrix = new DOMMatrixReadOnly(transform);

      return Math.atan2(matrix.b, matrix.a) * 180 / Math.PI;

    } catch (err) {

      return 0;

    }

  }



  function pptxApproxBackground(style) {

    const direct = pptxColor(style.backgroundColor, 1);

    if (pptxColorVisible(direct)) return style.backgroundColor;

    const image = String(style.backgroundImage || '');

    const colorMatch = image.match(/rgba?\([^)]*\)|color\(\s*srgb[^)]*\)|#[0-9a-f]{3,8}/i);

    return colorMatch ? colorMatch[0] : 'transparent';

  }



  function pptxDirectText(el) {

    const semantic = el.hasAttribute && el.hasAttribute('data-edit-layer');

    if (semantic) return (el.innerText || el.textContent || '').trim();

    const elementChildren = Array.from(el.children || []).filter((child) => !['BR', 'WBR'].includes(child.tagName));

    if (!elementChildren.length) return (el.innerText || el.textContent || '').trim();

    const direct = Array.from(el.childNodes || []).map((node) => {

      if (node.nodeType === Node.TEXT_NODE) return node.textContent || '';

      if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'BR') return '\n';

      return '';

    }).join('').replace(/\u00a0/g, ' ').trim();

    return direct;

  }



  function pptxOwnVisual(style) {

    const background = pptxColor(pptxApproxBackground(style), 1);

    const borderWidth = Math.max(

      parseFloat(style.borderTopWidth) || 0,

      parseFloat(style.borderRightWidth) || 0,

      parseFloat(style.borderBottomWidth) || 0,

      parseFloat(style.borderLeftWidth) || 0

    );

    return pptxColorVisible(background) || borderWidth > 0 || (style.backgroundImage && style.backgroundImage !== 'none');

  }



  function pptxCollectNodes(slide) {

    const roots = Array.from(slide.querySelectorAll('.el')).filter((node) => {

      const parentRoot = node.parentElement && node.parentElement.closest

        ? node.parentElement.closest('.el')

        : null;

      return !parentRoot || !slide.contains(parentRoot);

    });

    const extras = Array.from(slide.querySelectorAll('[data-edit-layer],img,svg')).filter((node) => {

      const parentRoot = node.closest && node.closest('.el');

      return !parentRoot;

    });

    const nodes = [];

    const seen = new Set();

    const visit = (node) => {

      if (!node || seen.has(node) || !node.getBoundingClientRect) return;

      if (node.matches && node.matches('[data-edit-layout-only="true"],[data-editor-chrome="true"],.edit-resize-handle,.edit-guide-line,.edit-marquee-box,.edit-selection-member-frame,.edit-hard-break-marker')) return;

      seen.add(node);

      const style = getComputedStyle(node);

      const rect = node.getBoundingClientRect();

      if (style.display === 'none' || style.visibility === 'hidden' || rect.width < 0.5 || rect.height < 0.5) return;

      const children = Array.from(node.children || []);

      const semantic = node.hasAttribute && node.hasAttribute('data-edit-layer');

      const terminal = ['IMG', 'SVG'].includes(String(node.tagName || '').toUpperCase());

      const text = terminal ? '' : pptxDirectText(node);

      const delegatesBackground = !semantic && children.some((child) => (

        child.matches && child.matches('[data-edit-layer="background"]')

      ));

      const ownVisual = pptxOwnVisual(style) && !delegatesBackground;

      const hasVisualChildren = children.some((child) => {

        if (!child || !child.getBoundingClientRect) return false;

        const childStyle = getComputedStyle(child);

        const childRect = child.getBoundingClientRect();

        if (childStyle.display === 'none' || childStyle.visibility === 'hidden' || childRect.width < 0.5 || childRect.height < 0.5) return false;

        return ['IMG', 'SVG'].includes(String(child.tagName || '').toUpperCase()) || Boolean(pptxDirectText(child)) || pptxOwnVisual(childStyle);

      });

      const delegateVisualToChildren = semantic && !terminal && !text && hasVisualChildren;

      if ((semantic || terminal || text || ownVisual) && !delegateVisualToChildren) {

        nodes.push({ node: node, text: text, style: style, ownVisual: ownVisual });

      }

      if (terminal) return;

      if (semantic && (text || ownVisual) && !delegateVisualToChildren) return;

      children.forEach(visit);

    };

    roots.concat(extras).forEach(visit);

    return nodes;

  }



  function pptxElementName(node, slideIndex, elementIndex) {

    const role = node.dataset && (node.dataset.editRole || node.dataset.editLayer || node.dataset.editKind);

    const classes = node.classList ? Array.from(node.classList).filter((name) => name !== 'el').slice(0, 3) : [];

    const source = (node.dataset && node.dataset.pptxName) || node.id || role || classes.join('-') || node.tagName.toLowerCase();

    return ('s' + (slideIndex + 1) + '-' + source + '-' + (elementIndex + 1))

      .normalize('NFKC')

      .replace(/[^\p{L}\p{N}_-]+/gu, '-')

      .replace(/^-+|-+$/g, '')

      .slice(0, 100);

  }



  function pptxElementRole(node) {

    const classes = node.classList ? Array.from(node.classList).join(' ') : '';

    return (node.dataset && (node.dataset.editRole || node.dataset.editLayer || node.dataset.editKind || node.dataset.editComposite))

      || classes

      || node.tagName.toLowerCase();

  }



  function pptxElementPosition(node, slideRect) {

    const rect = node.getBoundingClientRect();

    const slide = node.closest && node.closest('.slide');

    const scaleX = slideRect.width / 1920 || 1;

    const scaleY = slideRect.height / 1080 || scaleX;

    const rotation = pptxRotation(node);

    let left = (rect.left - slideRect.left) / scaleX;

    let top = (rect.top - slideRect.top) / scaleY;

    let width = rect.width / scaleX;

    let height = rect.height / scaleY;

    if (Math.abs(rotation) > 0.01 && slide) {

      const centerX = left + width / 2;

      const centerY = top + height / 2;

      const visualScale = pptxVisualScale(node, slide);

      const logicalWidth = Math.max(1, (node.offsetWidth || width) * visualScale);

      const logicalHeight = Math.max(1, (node.offsetHeight || height) * visualScale);

      left = centerX - logicalWidth / 2;

      top = centerY - logicalHeight / 2;

      width = logicalWidth;

      height = logicalHeight;

    }

    return {

      left: pptxRound(left),

      top: pptxRound(top),

      width: pptxRound(width),

      height: pptxRound(height),

      rotation: pptxRound(rotation)

    };

  }

  function pptxWritingModePosition(position, style) {

    const mode = String(style && style.writingMode || '').toLowerCase();

    if (mode !== 'vertical-rl' && mode !== 'vertical-lr') return position;

    const logicalWidth = Math.max(1, position.height);

    const logicalHeight = Math.max(1, position.width);

    const centerX = position.left + position.width / 2;

    const centerY = position.top + position.height / 2;

    return {

      left: pptxRound(centerX - logicalWidth / 2),

      top: pptxRound(centerY - logicalHeight / 2),

      width: pptxRound(logicalWidth),

      height: pptxRound(logicalHeight),

      rotation: mode === 'vertical-rl' ? 90 : -90

    };

  }

  function pptxRenderedLineCount(node, style) {

    if (!node || !node.ownerDocument || !node.ownerDocument.createRange) return 1;

    const range = node.ownerDocument.createRange();

    try {

      range.selectNodeContents(node);

      const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0.5 && rect.height > 0.5);

      if (!rects.length) return 1;

      const verticalWriting = /^vertical-/i.test(String(style && style.writingMode || ''));

      const coordinates = rects

        .map((rect) => verticalWriting ? rect.left : rect.top)

        .sort((a, b) => a - b);

      let lines = 0;

      let previous = null;

      coordinates.forEach((coordinate) => {

        if (previous === null || Math.abs(coordinate - previous) > 1.5) {

          lines += 1;

          previous = coordinate;

        }

      });

      return Math.max(1, lines);

    } finally {

      range.detach();

    }

  }

  function pptxNativeShape(position, radiusValue, clipPoints) {

    if (clipPoints) return 'custom';

    const radius = parseFloat(radiusValue) || 0;

    const minimumSide = Math.max(1, Math.min(position.width, position.height));

    const maximumSide = Math.max(position.width, position.height);

    if (radius < minimumSide * 0.45) return 'rect';

    const percentageRadius = /%/.test(String(radiusValue || '')) && radius >= 45;

    const nearCircle = maximumSide / minimumSide <= 1.15;

    // CSS border-radius:999px is commonly a capsule. Mapping a wide capsule

    // to a PowerPoint ellipse makes the ellipse's narrower internal text area

    // wrap short labels. Preserve true percentage ellipses and near-circles;

    // let the exporter use a rounded rectangle for wide pixel-radius pills.

    return percentageRadius || nearCircle ? 'ellipse' : 'roundRect';

  }

  function pptxBorders(style, opacity) {

    return {

      top: {

        width: parseFloat(style.borderTopWidth) || 0,

        color: pptxColor(style.borderTopColor, opacity)

      },

      right: {

        width: parseFloat(style.borderRightWidth) || 0,

        color: pptxColor(style.borderRightColor, opacity)

      },

      bottom: {

        width: parseFloat(style.borderBottomWidth) || 0,

        color: pptxColor(style.borderBottomColor, opacity)

      },

      left: {

        width: parseFloat(style.borderLeftWidth) || 0,

        color: pptxColor(style.borderLeftColor, opacity)

      }

    };

  }



  function pptxBorder(style, opacity) {

    const sides = [

      [parseFloat(style.borderTopWidth) || 0, style.borderTopColor],

      [parseFloat(style.borderRightWidth) || 0, style.borderRightColor],

      [parseFloat(style.borderBottomWidth) || 0, style.borderBottomColor],

      [parseFloat(style.borderLeftWidth) || 0, style.borderLeftColor]

    ].sort((a, b) => b[0] - a[0]);

    return {

      width: sides[0][0],

      color: pptxColor(sides[0][1], opacity)

    };

  }



  function pptxDataUrlFromBlob(blob) {

    return new Promise((resolve, reject) => {

      const reader = new FileReader();

      reader.onload = () => resolve(reader.result);

      reader.onerror = () => reject(reader.error || new Error('Unable to read image'));

      reader.readAsDataURL(blob);

    });

  }



  function pptxDataUrlFromImageSource(source) {

    return new Promise((resolve) => {

      const image = new Image();

      image.onload = () => {

        try {

          const canvas = document.createElement('canvas');

          canvas.width = image.naturalWidth || image.width || 1;

          canvas.height = image.naturalHeight || image.height || 1;

          const context = canvas.getContext('2d');

          if (!context) {

            resolve(null);

            return;

          }

          context.drawImage(image, 0, 0);

          resolve(canvas.toDataURL('image/png'));

        } catch (err) {

          resolve(null);

        }

      };

      image.onerror = () => resolve(null);

      try {

        image.src = new URL(source, location.href).href;

      } catch (err) {

        resolve(null);

      }

    });

  }



  function pptxWithTimeout(promise, timeoutMs, fallbackValue) {

    let timeoutId = 0;

    return Promise.race([

      Promise.resolve(promise),

      new Promise((resolve) => {

        timeoutId = window.setTimeout(() => resolve(fallbackValue), timeoutMs);

      })

    ]).finally(() => {

      if (timeoutId) window.clearTimeout(timeoutId);

    });

  }



  async function pptxFetchDataUrl(source) {

    if (!source) return null;

    if (source.startsWith('data:image/')) return source;

    const controller = typeof AbortController === 'function' ? new AbortController() : null;

    const abortTimer = controller ? window.setTimeout(() => controller.abort(), 5000) : 0;

    let fetchedDataUrl = null;

    try {

      const response = await fetch(new URL(source, location.href).href, {

        credentials: 'same-origin',

        signal: controller ? controller.signal : undefined

      });

      if (response.ok) fetchedDataUrl = await pptxDataUrlFromBlob(await response.blob());

    } catch (err) {

    } finally {

      if (abortTimer) window.clearTimeout(abortTimer);

    }

    return fetchedDataUrl || await pptxDataUrlFromImageSource(source);

  }



  function pptxBackgroundImageUrl(style, slide = null) {

    const embedded = String(slide?.dataset?.pptxBackgroundImageData || '').trim();

    if (embedded.startsWith('data:image/')) return embedded;

    const match = String(style.backgroundImage || '').match(/url\((['"]?)(.*?)\1\)/i);

    return match ? match[2] : '';

  }



  function pptxRound(value) {

    return Math.round((Number(value) || 0) * 1000) / 1000;

  }



  function pptxClipPathPoints(style, position) {

    const match = String(style.clipPath || '').match(/^polygon\((.*)\)$/i);

    if (!match) return null;

    const points = match[1].split(',').map((pair) => {

      const values = pair.trim().split(/\s+/).filter(Boolean);

      if (values.length < 2) return null;

      const resolve = (value, size) => value.endsWith('%')

        ? parseFloat(value) / 100 * size

        : parseFloat(value);

      const x = resolve(values[0], position.width);

      const y = resolve(values[1], position.height);

      if (!Number.isFinite(x) || !Number.isFinite(y)) return null;

      return {

        x: pptxRound(position.left + x),

        y: pptxRound(position.top + y)

      };

    }).filter(Boolean);

    return points.length >= 3 ? points : null;

  }



  function pptxSvgViewBox(svg) {

    const raw = String(svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);

    if (raw.length === 4 && raw.every(Number.isFinite) && raw[2] > 0 && raw[3] > 0) {

      return { x: raw[0], y: raw[1], width: raw[2], height: raw[3] };

    }

    return {

      x: 0,

      y: 0,

      width: Math.max(1, parseFloat(svg.getAttribute('width')) || svg.clientWidth || 1),

      height: Math.max(1, parseFloat(svg.getAttribute('height')) || svg.clientHeight || 1)

    };

  }



  function pptxSvgPoint(position, viewBox, x, y) {

    return {

      x: pptxRound(position.left + (Number(x) - viewBox.x) / viewBox.width * position.width),

      y: pptxRound(position.top + (Number(y) - viewBox.y) / viewBox.height * position.height)

    };

  }



  function pptxSvgPointsAttribute(value) {

    const values = String(value || '').trim().split(/[\s,]+/).map(Number).filter(Number.isFinite);

    const points = [];

    for (let index = 0; index + 1 < values.length; index += 2) {

      points.push({ x: values[index], y: values[index + 1] });

    }

    return points;

  }



  function pptxSvgPathPoints(path) {

    try {

      const length = path.getTotalLength();

      if (!Number.isFinite(length) || length <= 0) return [];

      const samples = Math.min(64, Math.max(2, Math.ceil(length / 48) + 1));

      const points = [];

      for (let index = 0; index < samples; index += 1) {

        const point = path.getPointAtLength(length * index / (samples - 1));

        points.push({ x: point.x, y: point.y });

      }

      return points;

    } catch (err) {

      return [];

    }

  }



  function pptxCustomGeometryElement(base, points, closed, style, opacity, nameSuffix) {

    if (!Array.isArray(points) || points.length < 2) return null;

    const minX = Math.min(...points.map((point) => point.x));

    const minY = Math.min(...points.map((point) => point.y));

    const maxX = Math.max(...points.map((point) => point.x));

    const maxY = Math.max(...points.map((point) => point.y));

    const strokeWidth = parseFloat(style.strokeWidth) || 0;

    return {

      ...base,

      name: (base.name + '-' + nameSuffix).slice(0, 100),

      kind: 'custom',

      position: {

        left: pptxRound(minX),

        top: pptxRound(minY),

        width: pptxRound(Math.max(1, maxX - minX)),

        height: pptxRound(Math.max(1, maxY - minY)),

        rotation: 0

      },

      points: points.map((point) => ({ x: pptxRound(point.x), y: pptxRound(point.y) })),

      closed: Boolean(closed),

      fill: pptxColor(style.fill, opacity),

      lineColor: pptxColor(style.stroke, opacity),

      lineWidth: strokeWidth,

      endArrowType: style.markerEnd && style.markerEnd !== 'none' ? 'triangle' : 'none',

      startArrowType: style.markerStart && style.markerStart !== 'none' ? 'triangle' : 'none',

      lineDash: style.strokeDasharray && style.strokeDasharray !== 'none' ? 'dash' : 'solid'

    };

  }



  function pptxSvgManifestElements(svg, position, slide, slideIndex, elementIndex) {

    const viewBox = pptxSvgViewBox(svg);

    const baseName = pptxElementName(svg, slideIndex, elementIndex);

    const role = pptxElementRole(svg);

    const output = [];

    const nodes = Array.from(svg.querySelectorAll('line,rect,circle,ellipse,polyline,polygon,path,text'))

      .filter((node) => !node.closest('defs'));

    nodes.forEach((node, childIndex) => {

      const style = getComputedStyle(node);

      if (style.display === 'none' || style.visibility === 'hidden') return;

      const opacity = pptxElementOpacity(node, slide);

      const base = {

        name: baseName,

        role: role + '-svg-' + (childIndex + 1),

        fill: pptxColor(style.fill, opacity),

        lineColor: pptxColor(style.stroke, opacity),

        lineWidth: (parseFloat(style.strokeWidth) || 0) * ((position.width / viewBox.width + position.height / viewBox.height) / 2),

        borders: null,

        borderRadius: 0,

        shape: 'rect',

        hasShadow: false,

        zIndex: 0

      };

      const tag = String(node.tagName || '').toLowerCase();

      if (tag === 'text') {

        const textPosition = pptxElementPosition(node, slide.getBoundingClientRect());

        output.push({

          ...base,

          name: (baseName + '-text-' + (childIndex + 1)).slice(0, 100),

          kind: 'text',

          text: String(node.textContent || '').trim(),

          position: textPosition,

          fill: '#00000000',

          color: pptxColor(style.fill || style.color, opacity),

          fontSizePt: Math.max(1, (parseFloat(style.fontSize) || 16) * 0.5),

          fontFamily: pptxResolvedFontFamily(style.fontFamily),

          bold: (parseInt(style.fontWeight, 10) || 400) >= 600,

          italic: style.fontStyle === 'italic' || style.fontStyle === 'oblique',

          textDirection: 'horz',

          textAlign: style.textAnchor === 'middle' ? 'center' : style.textAnchor === 'end' ? 'right' : 'left',

          verticalAlign: 'middle',

          lineHeightPt: (parseFloat(style.lineHeight) || parseFloat(style.fontSize) || 16) * 0.5,

          charSpacingPt: (parseFloat(style.letterSpacing) || 0) * 0.5,

          pptxMarginPt: 0

        });

        return;

      }

      if (tag === 'rect') {

        const topLeft = pptxSvgPoint(position, viewBox, parseFloat(node.getAttribute('x')) || 0, parseFloat(node.getAttribute('y')) || 0);

        const width = (parseFloat(node.getAttribute('width')) || 0) / viewBox.width * position.width;

        const height = (parseFloat(node.getAttribute('height')) || 0) / viewBox.height * position.height;

        output.push({

          ...base,

          name: (baseName + '-rect-' + (childIndex + 1)).slice(0, 100),

          kind: 'shape',

          position: { left: topLeft.x, top: topLeft.y, width: pptxRound(width), height: pptxRound(height), rotation: 0 },

          borderRadius: Math.max(parseFloat(node.getAttribute('rx')) || 0, parseFloat(node.getAttribute('ry')) || 0)

        });

        return;

      }

      if (tag === 'circle' || tag === 'ellipse') {

        const cx = parseFloat(node.getAttribute('cx')) || 0;

        const cy = parseFloat(node.getAttribute('cy')) || 0;

        const rx = tag === 'circle' ? (parseFloat(node.getAttribute('r')) || 0) : (parseFloat(node.getAttribute('rx')) || 0);

        const ry = tag === 'circle' ? rx : (parseFloat(node.getAttribute('ry')) || 0);

        const topLeft = pptxSvgPoint(position, viewBox, cx - rx, cy - ry);

        output.push({

          ...base,

          name: (baseName + '-ellipse-' + (childIndex + 1)).slice(0, 100),

          kind: 'shape',

          shape: 'ellipse',

          position: {

            left: topLeft.x,

            top: topLeft.y,

            width: pptxRound(rx * 2 / viewBox.width * position.width),

            height: pptxRound(ry * 2 / viewBox.height * position.height),

            rotation: 0

          }

        });

        return;

      }

      let rawPoints = [];

      let closed = false;

      if (tag === 'line') {

        rawPoints = [

          { x: parseFloat(node.getAttribute('x1')) || 0, y: parseFloat(node.getAttribute('y1')) || 0 },

          { x: parseFloat(node.getAttribute('x2')) || 0, y: parseFloat(node.getAttribute('y2')) || 0 }

        ];

      } else if (tag === 'polyline' || tag === 'polygon') {

        rawPoints = pptxSvgPointsAttribute(node.getAttribute('points'));

        closed = tag === 'polygon';

      } else if (tag === 'path') {

        rawPoints = pptxSvgPathPoints(node);

        closed = /[zZ]\s*$/.test(String(node.getAttribute('d') || ''));

      }

      const points = rawPoints.map((point) => pptxSvgPoint(position, viewBox, point.x, point.y));

      const geometry = pptxCustomGeometryElement(base, points, closed, style, opacity, tag + '-' + (childIndex + 1));

      if (geometry) {

        geometry.lineWidth = base.lineWidth;

        output.push(geometry);

      }

    });

    return output;

  }

  function pptxHorizontalGradientBands(style, base) {

    const layer = pptxSplitCssLayers(style && style.backgroundImage)[0] || '';

    if (!/^linear-gradient\(90deg/i.test(layer)) return [];

    const stops = [];

    const pattern = /(rgba?\([^)]*\)|#[0-9a-f]{3,8})\s+([\d.]+)%/ig;

    let match = null;

    while ((match = pattern.exec(layer))) {

      stops.push({ fill: pptxColor(match[1], 1), percent: parseFloat(match[2]) });

    }

    const bands = [];

    for (let index = 0; index < stops.length - 1; index += 1) {

      const first = stops[index];

      const second = stops[index + 1];

      if (first.fill !== second.fill || !pptxColorVisible(first.fill) || second.percent <= first.percent) continue;

      bands.push({

        ...base,

        name: (base.name + '-gradient-' + (bands.length + 1)).slice(0, 100),

        kind: 'shape',

        position: {

          left: pptxRound(base.position.left + first.percent / 100 * base.position.width),

          top: base.position.top,

          width: pptxRound((second.percent - first.percent) / 100 * base.position.width),

          height: base.position.height,

          rotation: base.position.rotation || 0

        },

        fill: first.fill,

        lineColor: '#00000000',

        borders: null,

        lineWidth: 0,

        borderRadius: 0,

        shape: 'rect',

        points: null,

        closed: false

      });

    }

    return bands;

  }

  async function pptxManifestElements(entry, slide, slideRect, slideIndex, elementIndex) {

    const node = entry.node;

    const style = entry.style;

    const opacity = pptxElementOpacity(node, slide);

    const position = pptxWritingModePosition(pptxElementPosition(node, slideRect), style);

    const borders = pptxBorders(style, opacity);

    const border = pptxBorder(style, opacity);

    const radiusValue = style.borderTopLeftRadius;

    const radius = parseFloat(radiusValue) || 0;

    const clipPoints = pptxClipPathPoints(style, position);

    const base = {

      name: pptxElementName(node, slideIndex, elementIndex),

      role: pptxElementRole(node),

      position: position,

      fill: pptxColor(pptxApproxBackground(style), opacity),

      lineColor: border.color,

      borders: borders,

      lineWidth: border.width,

      borderRadius: radius,

      shape: pptxNativeShape(position, radiusValue, clipPoints),

      points: clipPoints,

      closed: Boolean(clipPoints),

      hasShadow: Boolean(style.boxShadow && style.boxShadow !== 'none'),

      zIndex: Number.isFinite(parseInt(style.zIndex, 10)) ? parseInt(style.zIndex, 10) : 0

    };

    if (String(node.tagName || '').toUpperCase() === 'SVG') {

      return pptxSvgManifestElements(node, position, slide, slideIndex, elementIndex);

    }

    let dataUrl = null;

    if (String(node.tagName || '').toUpperCase() === 'IMG') {

      dataUrl = await pptxFetchDataUrl(node.currentSrc || node.src);

    } else {

      dataUrl = await pptxFetchDataUrl(pptxBackgroundImageUrl(style));

    }

    const elements = [];

    const gradientBands = pptxHorizontalGradientBands(style, base);

    if (dataUrl) {

      elements.push({

        ...base,

        kind: 'image',

        dataUrl: dataUrl,

        alt: node.getAttribute('alt') || base.name,

        fit: style.objectFit === 'contain' || style.backgroundSize === 'contain' ? 'contain' : 'cover'

      });

    }

    if (entry.text) {

      const fontScale = pptxVisualScale(node, slide);

      const vertical = (node.dataset && node.dataset.editVerticalAlign)

        || (style.justifyContent === 'center' ? 'middle' : style.justifyContent === 'flex-end' ? 'bottom' : 'top');

      const lineHeightPx = parseFloat(style.lineHeight);

      const letterSpacingPx = parseFloat(style.letterSpacing);

      const verticalWriting = /^vertical-/i.test(String(style.writingMode || ''));

      const renderedLineCount = pptxRenderedLineCount(node, style);

      const singleLine = !verticalWriting && renderedLineCount === 1 && !entry.text.includes('\n');

      // PowerPoint and browsers use slightly different glyph metrics even

      // when the same font is installed. Reserve 4% on authored single-line

      // labels so a one-line DOM title does not gain a trailing orphan line.

      const textMetricScale = singleLine ? 0.96 : 1;

      if (gradientBands.length) elements.push(...gradientBands);

      elements.push({

        ...base,

        kind: 'text',

        text: entry.text,

        singleLine: singleLine,

        renderedLineCount: renderedLineCount,

        fill: dataUrl || gradientBands.length ? '#00000000' : base.fill,

        fontSizePt: Math.max(1, (parseFloat(style.fontSize) || 16) * fontScale * textMetricScale * 0.5),

        fontFamily: pptxResolvedFontFamily(style.fontFamily),

        color: pptxColor(style.color, opacity),

        bold: (parseInt(style.fontWeight, 10) || 400) >= 600 || style.fontWeight === 'bold',

        italic: style.fontStyle === 'italic' || style.fontStyle === 'oblique',

        underline: String(style.textDecorationLine || '').includes('underline'),

        textDirection: 'horz',

        textAlign: ['left', 'center', 'right', 'justify'].includes(style.textAlign) ? style.textAlign : 'left',

        verticalAlign: vertical,

        lineHeightPt: Number.isFinite(lineHeightPx) ? Math.max(1, lineHeightPx * fontScale * 0.5) : null,

        charSpacingPt: verticalWriting ? 0 : (Number.isFinite(letterSpacingPx) ? letterSpacingPx * fontScale * 0.5 * (letterSpacingPx > 0 ? 0.75 : 1) : 0),

        pptxMarginPt: [

          (parseFloat(style.paddingLeft) || 0) * fontScale * 0.5,

          (parseFloat(style.paddingRight) || 0) * fontScale * 0.5,

          (parseFloat(style.paddingBottom) || 0) * fontScale * 0.5,

          (parseFloat(style.paddingTop) || 0) * fontScale * 0.5

        ]

      });

    } else if (!dataUrl) {

      if (gradientBands.length) elements.push(...gradientBands);

      else elements.push({ ...base, kind: clipPoints ? 'custom' : 'shape' });

    }

    return elements;

  }

  function pptxSplitCssLayers(value) {

    const layers = [];

    let start = 0;

    let depth = 0;

    const text = String(value || '');

    for (let index = 0; index < text.length; index += 1) {

      const char = text[index];

      if (char === '(') depth += 1;

      else if (char === ')') depth = Math.max(0, depth - 1);

      else if (char === ',' && depth === 0) {

        layers.push(text.slice(start, index).trim());

        start = index + 1;

      }

    }

    if (text.slice(start).trim()) layers.push(text.slice(start).trim());

    return layers;

  }



  function pptxSlideDecorElement(name, position, fill, shape) {

    return {

      name: name,

      role: 'slide-background-decoration',

      kind: 'shape',

      position: position,

      fill: fill,

      lineColor: '#00000000',

      borders: null,

      lineWidth: 0,

      borderRadius: 0,

      shape: shape || 'rect',

      points: null,

      closed: false,

      hasShadow: false,

      zIndex: -1000

    };

  }

  function pptxGradientColorToken(value) {
    const match = String(value || '').trim().match(/^(transparent|rgba?\([^)]*\)|color\(\s*srgb\s+[^)]*\)|#[0-9a-f]{3,8})/i);
    return match ? match[1] : '';
  }

  function pptxGradientStops(parts) {
    return parts.map((part) => {
      const colorToken = pptxGradientColorToken(part);
      if (!colorToken) return null;
      const remainder = String(part).slice(colorToken.length).trim();
      const positionMatch = remainder.match(/^(-?[\d.]+)(px|%)/i);
      return {
        color: pptxColor(colorToken, 1),
        position: positionMatch ? { value: parseFloat(positionMatch[1]), unit: positionMatch[2].toLowerCase() } : null
      };
    }).filter(Boolean);
  }

  function pptxResolveGradientStops(stops, size) {
    if (!stops.length) return [];
    const resolved = stops.map((stop) => ({
      ...stop,
      offset: stop.position
        ? (stop.position.unit === '%' ? stop.position.value / 100 * size : stop.position.value)
        : null
    }));
    if (resolved[0].offset === null) resolved[0].offset = 0;
    if (resolved[resolved.length - 1].offset === null) resolved[resolved.length - 1].offset = size;
    let previousKnown = 0;
    for (let index = 1; index < resolved.length; index += 1) {
      if (resolved[index].offset === null) continue;
      const start = resolved[previousKnown].offset;
      const end = resolved[index].offset;
      const gap = index - previousKnown;
      for (let inner = 1; inner < gap; inner += 1) {
        resolved[previousKnown + inner].offset = start + (end - start) * inner / gap;
      }
      previousKnown = index;
    }
    for (let index = previousKnown + 1; index < resolved.length; index += 1) {
      resolved[index].offset = resolved[previousKnown].offset;
    }
    return resolved;
  }

  function pptxGradientDirection(layer) {
    const match = String(layer || '').match(/^linear-gradient\(\s*([^,]+),/i);
    const direction = match ? match[1].trim().toLowerCase() : '';
    if (/^90deg$/.test(direction) || /^to\s+(left|right)\b/.test(direction)) return 'horizontal';
    return 'vertical';
  }

  function pptxLinearGradientDecorElements(layer, prefix, layerIndex) {
    const inner = String(layer || '').replace(/^linear-gradient\(\s*/i, '').replace(/\)\s*$/, '');
    const parts = pptxSplitCssLayers(inner);
    if (!parts.length) return [];
    const direction = pptxGradientDirection(layer);
    if (/^[-\d.]+deg\s*,/i.test(inner) || /^to\s+[^,]+\s*,/i.test(inner)) parts.shift();
    const size = direction === 'horizontal' ? 1920 : 1080;
    const stops = pptxResolveGradientStops(pptxGradientStops(parts), size);
    const output = [];
    for (let index = 0; index < stops.length - 1; index += 1) {
      const first = stops[index];
      const second = stops[index + 1];
      const start = Math.max(0, Math.min(size, first.offset));
      const end = Math.max(0, Math.min(size, second.offset));
      if (end <= start) continue;
      const fill = pptxColorVisible(second.color) ? second.color : first.color;
      if (!pptxColorVisible(fill)) continue;
      output.push(pptxSlideDecorElement(
        prefix + 'linear-' + layerIndex + '-' + index,
        direction === 'horizontal'
          ? { left: pptxRound(start), top: 0, width: pptxRound(end - start), height: 1080, rotation: 0 }
          : { left: 0, top: pptxRound(start), width: 1920, height: pptxRound(end - start), rotation: 0 },
        fill
      ));
    }
    return output;
  }

  function pptxAlphaScaled(color, multiplier) {
    const raw = String(color || '').toUpperCase();
    if (!/^#[0-9A-F]{8}$/.test(raw)) return raw;
    const alpha = parseInt(raw.slice(7, 9), 16) / 255;
    return raw.slice(0, 7) + pptxHexByte(alpha * multiplier * 255);
  }

  function pptxRadialGradientDecorElements(layer, prefix, layerIndex) {
    const inner = String(layer || '').replace(/^radial-gradient\(\s*/i, '').replace(/\)\s*$/, '');
    const parts = pptxSplitCssLayers(inner);
    if (parts.length < 2) return [];
    const header = parts.shift();
    const centerMatch = String(header).match(/\bat\s+([-\d.]+%|[-\d.]+px)\s+([-\d.]+%|[-\d.]+px)/i);
    const resolveCoordinate = (value, size, fallback) => {
      if (!value) return fallback;
      return /%$/.test(value) ? parseFloat(value) / 100 * size : parseFloat(value);
    };
    const centerX = resolveCoordinate(centerMatch && centerMatch[1], 1920, 960);
    const centerY = resolveCoordinate(centerMatch && centerMatch[2], 1080, 540);
    const stops = pptxGradientStops(parts);
    const sourceColor = stops.find((stop) => pptxColorVisible(stop.color));
    if (!sourceColor) return [];
    const radiusStop = [...stops].reverse().find((stop) => stop.position);
    const radius = radiusStop
      ? (radiusStop.position.unit === '%'
        ? Math.max(1920, 1080) * radiusStop.position.value / 100
        : radiusStop.position.value)
      : Math.max(1920, 1080) * 0.35;
    const output = [];
    const steps = 7;
    for (let index = steps; index >= 1; index -= 1) {
      const ratio = index / steps;
      const size = Math.max(1, radius * 2 * ratio);
      const fill = pptxAlphaScaled(sourceColor.color, 0.18 + (1 - ratio) * 0.82);
      output.push(pptxSlideDecorElement(
        prefix + 'radial-' + layerIndex + '-' + index,
        { left: pptxRound(centerX - size / 2), top: pptxRound(centerY - size / 2), width: pptxRound(size), height: pptxRound(size), rotation: 0 },
        fill,
        'ellipse'
      ));
    }
    return output;
  }



  function pptxSlideDecorElements(style, slideIndex) {

    const output = [];

    const prefix = 's' + (slideIndex + 1) + '-slide-bg-';

    const layers = pptxSplitCssLayers(style.backgroundImage);

    const sizes = pptxSplitCssLayers(style.backgroundSize);

    for (let layerIndex = layers.length - 1; layerIndex >= 0; layerIndex -= 1) {

      const layer = layers[layerIndex];

      if (!/^(?:linear|radial)-gradient\(/i.test(layer)) continue;

      const sizeMatch = String(sizes[layerIndex] || '').match(/([\d.]+)px\s+([\d.]+)px/i);

      const pixelStop = layer.match(/(rgba?\([^)]*\)|#[0-9a-f]{3,8})\s+1px\s*,\s*rgba?\([^)]*,\s*0\)\s+1px/i);

      if (sizeMatch && pixelStop) {

        const stepX = Math.max(1, parseFloat(sizeMatch[1]) || 64);

        const stepY = Math.max(1, parseFloat(sizeMatch[2]) || 64);

        const fill = pptxColor(pixelStop[1], 1);

        const vertical = /^linear-gradient\(90deg/i.test(layer);

        const limit = vertical ? 1920 : 1080;

        const step = vertical ? stepX : stepY;

        for (let offset = 0, lineIndex = 0; offset < limit; offset += step, lineIndex += 1) {

          output.push(pptxSlideDecorElement(

            prefix + 'grid-' + (vertical ? 'v-' : 'h-') + lineIndex,

            vertical

              ? { left: pptxRound(offset), top: 0, width: 1, height: 1080, rotation: 0 }

              : { left: 0, top: pptxRound(offset), width: 1920, height: 1, rotation: 0 },

            fill

          ));

        }

        continue;

      }

      if (/^linear-gradient\(/i.test(layer)) output.push(...pptxLinearGradientDecorElements(layer, prefix, layerIndex));

      else if (/^radial-gradient\(/i.test(layer)) output.push(...pptxRadialGradientDecorElements(layer, prefix, layerIndex));

    }

    const inset = String(style.boxShadow || '').match(/(rgba?\([^)]*\)|#[0-9a-f]{3,8})\s+([\d.]+)px\s+0px\s+0px\s+0px\s+inset/i);

    if (inset && parseFloat(inset[2]) > 0) {

      output.push(pptxSlideDecorElement(

        prefix + 'inset-left',

        { left: 0, top: 0, width: pptxRound(parseFloat(inset[2])), height: 1080, rotation: 0 },

        pptxColor(inset[1], 1)

      ));

    }

    return output;

  }

  function pptxSuggestedFileName() {

    const htmlName = suggestedFileName().replace(/\.html?$/i, '');

    return (htmlName || 'edited-presentation') + '.pptx';

  }



  async function buildPptxManifest() {

    if (document.fonts && document.fonts.ready) {

      try {

        await pptxWithTimeout(document.fonts.ready, 1500, null);

      } catch (err) {

        // The computed fallback font is still a valid export input.

      }

    }

    if (textEditingEl) endTextEdit();

    const themeId = document.documentElement.dataset.themeId

      || document.documentElement.dataset.theme

      || document.documentElement.dataset.styleCase

      || 'html-edited';

    const slides = Array.from(stage.children).filter((node) => node.classList.contains('slide'));

    const slideManifests = [];

    const activeStates = slides.map((slide) => slide.classList.contains('active'));

    const stageInlineOpacity = stage.style.opacity;

    const stageInlinePointerEvents = stage.style.pointerEvents;

    stage.style.opacity = '0';

    stage.style.pointerEvents = 'none';

    slides.forEach((slide) => slide.classList.add('active'));

    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));

    try {

      for (const [slideIndex, slide] of slides.entries()) {

        const slideRect = slide.getBoundingClientRect();

        const slideStyle = getComputedStyle(slide);

        const backgroundSource = pptxBackgroundImageUrl(slideStyle, slide);

        const backgroundSourcePath = slide.dataset.pptxBackgroundImageSrc || backgroundSource;

        const backgroundDataUrl = backgroundSource

          ? await pptxFetchDataUrl(backgroundSource)

          : null;

        const entries = pptxCollectNodes(slide);

        const elements = pptxSlideDecorElements(slideStyle, slideIndex);

        for (const [elementIndex, entry] of entries.entries()) {

          const converted = await pptxManifestElements(entry, slide, slideRect, slideIndex, elementIndex);

          elements.push(...converted);

        }

        // pptxCollectNodes walks the DOM in paint order. A global z-index sort

        // breaks CSS stacking contexts and can move a parent's background above

        // all of its own text. Preserve traversal order; z-index remains

        // diagnostic metadata for the manifest.

        slideManifests.push({

          id: slide.id || 'slide-' + (slideIndex + 1),

          layoutId: slide.dataset.layoutId || slide.dataset.productionFamily || slide.id || 'slide-' + (slideIndex + 1),

          themeId: slide.dataset.themeId || themeId,

          backgroundColor: pptxColor(pptxApproxBackground(slideStyle), 1),

          backgroundImage: backgroundDataUrl ? {

            dataUrl: backgroundDataUrl,

            source: backgroundSourcePath,

            fit: String(slideStyle.backgroundSize || '').trim().toLowerCase() === 'contain' ? 'contain' : 'cover',

            role: slide.dataset.pptxBackgroundImage === 'true' ? 'generated-slide-background' : 'css-raster-background'

          } : null,

          elements: elements

        });

      }

    } finally {

      slides.forEach((slide, index) => slide.classList.toggle('active', activeStates[index]));

      stage.style.opacity = stageInlineOpacity;

      stage.style.pointerEvents = stageInlinePointerEvents;

    }

    return {

      schemaVersion: 4,

      exportMode: 'native-editable',

      backgroundPolicy: 'raster-slide-background-on-child-layout',

      title: document.title || 'HTML presentation',

      fileName: pptxSuggestedFileName(),

      themeId: themeId,

      sourcePath: currentFilePath(),

      canvas: { width: 1920, height: 1080 },

      coordinateSystem: {

        unit: 'css-pixel',

        width: 1920,

        height: 1080,

        powerPointWidthIn: 13.333333,

        powerPointHeightIn: 7.5

      },

      slides: slideManifests

    };

  }



  async function exportPptx() {

    if (exportPptxBtn) exportPptxBtn.disabled = true;

    showTransientReadout(M.pptxExporting, 120000);

    try {

      const manifest = await buildPptxManifest();

      const browserExporter = window.PptxBrowserExport && window.PptxBrowserExport.exportManifest;

      if (typeof window.PptxGenJS === 'function' && typeof browserExporter === 'function') {

        const result = await browserExporter(manifest, { fileName: manifest.fileName });

        showTransientReadout(M.pptxExportDone + '\uff1a' + result.fileName, 3600);

        document.dispatchEvent(new CustomEvent('editpptxexported', { detail: result }));

        return {

          exported: true,

          ...result

        };

      }

      if (!isWritableDevServer()) {

        showTransientReadout(M.pptxRuntimeMissing, 5200);

        return { exported: false, method: 'browser-runtime-missing' };

      }

      const response = await fetch('/__export-pptx', {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify(manifest)

      });

      if (!response.ok) {

        let reason = 'HTTP ' + response.status;

        try {

          const data = await response.json();

          if (data && data.error) reason = data.error;

        } catch (err) {

          // Keep the HTTP status when the response is not JSON.

        }

        throw new Error(reason);

      }

      const blob = await response.blob();

      const url = URL.createObjectURL(blob);

      const link = document.createElement('a');

      link.href = url;

      link.download = manifest.fileName;

      document.body.appendChild(link);

      link.click();

      link.remove();

      setTimeout(() => URL.revokeObjectURL(url), 2000);

      showTransientReadout(M.pptxExportDone + '\uff1a' + manifest.fileName, 3600);

      document.dispatchEvent(new CustomEvent('editpptxexported', {

        detail: {

          fileName: manifest.fileName,

          bytes: blob.size,

          slides: manifest.slides.length

        }

      }));

      return {

        exported: true,

        fileName: manifest.fileName,

        bytes: blob.size,

        slides: manifest.slides.length,

        method: 'artifact-tool-local-server'

      };

    } catch (err) {

      const reason = err && err.message ? err.message : 'unknown error';

      showTransientReadout(M.pptxExportFailed + reason, 5600);

      const failure = {

        exported: false,

        method: typeof window.PptxGenJS === 'function' ? 'pptxgenjs-browser' : 'artifact-tool-local-server',

        error: reason

      };

      document.dispatchEvent(new CustomEvent('editpptxexportfailed', { detail: failure }));

      return failure;

    } finally {

      if (exportPptxBtn) exportPptxBtn.disabled = false;

    }

  }



  function elementKey(el) {

    const slide = el.closest('.slide');

    if (!slide || !slide.id) return null;

    const root = editableRoot(el);

    const els = slide.querySelectorAll('.el');

    const idx = Array.prototype.indexOf.call(els, root);

    if (idx < 0) {

      const systemEls = slide.querySelectorAll('[data-auto-layout],[data-visual-balance]');

      const systemIdx = Array.prototype.indexOf.call(systemEls, el);

      return systemIdx < 0 ? null : slide.id + '::system::' + systemIdx;

    }

    if (el === root) return slide.id + '::' + idx;

    const layers = root.querySelectorAll('[data-edit-layer]');

    const layerIdx = Array.prototype.indexOf.call(layers, el);

    return layerIdx < 0 ? null : slide.id + '::' + idx + '::' + layerIdx;

  }



  function elementByKey(key) {

    const parts = key.split('::');

    const slide = document.getElementById(parts[0]);

    if (!slide) return null;

    if (parts[1] === 'system') {

      const systemIdx = parseInt(parts[2], 10);

      if (Number.isNaN(systemIdx)) return null;

      return slide.querySelectorAll('[data-auto-layout],[data-visual-balance]')[systemIdx] || null;

    }

    const idx = parseInt(parts[1], 10);

    if (Number.isNaN(idx)) return null;

    const root = slide.querySelectorAll('.el')[idx] || null;

    if (!root || parts.length < 3) return root;

    const layerIdx = parseInt(parts[2], 10);

    if (Number.isNaN(layerIdx)) return null;

    return root.querySelectorAll('[data-edit-layer]')[layerIdx] || null;

  }



  function deckRevision() {

    return document.documentElement.dataset.deckRevision ||

      document.documentElement.dataset.randomSeed ||

      'legacy';

  }



  function legacyDraftKey() {

    return 'edit-draft:' + location.pathname;

  }



  function draftKey() {

    return 'edit-draft:v' + DRAFT_SCHEMA_VERSION + ':' + location.pathname + ':' + deckRevision();

  }



  function operationLogKey() {

    return 'edit-operation-log:' + location.pathname + ':' + deckRevision();

  }



  function storageGet(key) {

    try {

      return window.localStorage ? window.localStorage.getItem(key) : null;

    } catch (err) {

      return null;

    }

  }



  function storageSet(key, value) {

    try {

      if (!window.localStorage) return false;

      window.localStorage.setItem(key, value);

      return true;

    } catch (err) {

      return false;

    }

  }



  function storageRemove(key) {

    try {

      if (!window.localStorage) return false;

      window.localStorage.removeItem(key);

      return true;

    } catch (err) {

      return false;

    }

  }



  function clearDraft() {

    storageRemove(draftKey());

    storageRemove(legacyDraftKey());

  }



  function syncSavedElementBaselines() {

    changedElements.forEach((el) => {

      if (!el || !document.contains(el)) return;

      const state = measureElementState(el);

      originalPositions.set(el, { left: state.left, top: state.top });

      originalSizes.set(el, {

        width: state.width,

        height: state.height,

        fontSize: state.fontSize

      });

      const styleBaseline = originalStyles.get(el);

      if (styleBaseline) {

        Object.keys(styleBaseline).forEach((key) => {

          if (Object.prototype.hasOwnProperty.call(state, key)) styleBaseline[key] = state[key];

        });

      } else {

        originalStyles.set(el, {

          fontFamily: state.fontFamily,

          fontWeight: state.fontWeight,

          fontStyle: state.fontStyle,

          textDecorationLine: state.textDecorationLine,

          textAlign: state.textAlign,

          color: state.color,

          background: state.background,

          borderColor: state.borderColor,

          zIndex: state.zIndex,

          display: state.display,

          lineHeight: state.lineHeight,

          letterSpacing: state.letterSpacing,

          paddingLeft: state.paddingLeft,

          paddingRight: state.paddingRight,

          textWrap: state.textWrap,

          whiteSpace: state.whiteSpace,

          columnGap: state.columnGap,

          wrapMode: state.wrapMode,

          alignContent: state.alignContent,

          flexDirection: state.flexDirection,

          justifyContent: state.justifyContent,

          alignItems: state.alignItems,

          verticalAlign: state.verticalAlign,

          frameWidthMode: state.frameWidthMode,

          frameHeightMode: state.frameHeightMode,

          compositeGroupState: state.compositeGroupState,

          groupId: state.groupId,

          transform: state.transform,

          transformOrigin: state.transformOrigin,

          typographySignature: state.typographySignature

        });

      }

      if (originalTexts.has(el) || textDirty.has(el)) originalTexts.set(el, el.innerHTML);

    });

  }



  function markCurrentDocumentSaved() {

    if (draftTimer) clearTimeout(draftTimer);

    draftTimer = null;

    if (autoSaveTimer) clearTimeout(autoSaveTimer);

    autoSaveTimer = null;

    autoSaveQueued = false;

    autoSaveLastSavedAt = Date.now();

    autoSaveLastError = '';

    setAutoSaveState('saved');

    syncSavedElementBaselines();

    changedElements.clear();

    savedSlideOrder = currentSlideOrder();

    slideOrderDirty = false;

    savedDeckFontState = deckFontState();

    savedSlideBackgroundStates = slideBackgroundStates();

    savedSlideMaskStates = slideMaskStates();

    clearDraft();

    document.getElementById('edit-draft-prompt')?.remove();

  }



  function compactGeometryState(state) {

    if (!state) return null;

    return {

      left: state.left,

      top: state.top,

      width: state.width,

      height: state.height,

      fontSize: state.fontSize,

      transform: state.transform || ''

    };

  }



  function commandDiagnostic(command) {

    if (!command) return null;

    const rawItems = command.type === 'batch' ? (command.items || []) : [command];

    return {

      type: command.type || 'unknown',

      label: commandLabel(command),

      itemCount: rawItems.length,

      items: rawItems.slice(0, 24).map((item) => ({

        key: item.key || (item.el ? elementKey(item.el) : null),

        type: item.type || command.itemType || command.type || 'unknown',

        before: compactGeometryState(item.before),

        after: compactGeometryState(item.after)

      }))

    };

  }



  function loadOperationLog() {

    if (operationLog) return operationLog;

    const raw = storageGet(operationLogKey());

    if (!raw) {

      operationLog = [];

      return operationLog;

    }

    try {

      const parsed = JSON.parse(raw);

      operationLog = Array.isArray(parsed) ? parsed.slice(-OPERATION_LOG_LIMIT) : [];

    } catch (err) {

      operationLog = [];

      storageRemove(operationLogKey());

    }

    return operationLog;

  }



  function appendOperationLog(action, command) {

    const detail = commandDiagnostic(command);

    if (!detail) return;

    const entries = loadOperationLog();

    entries.push({

      timestamp: Date.now(),

      action: action,

      command: detail

    });

    if (entries.length > OPERATION_LOG_LIMIT) {

      entries.splice(0, entries.length - OPERATION_LOG_LIMIT);

    }

    storageSet(operationLogKey(), JSON.stringify(entries));

  }



  function operationDiagnostics() {

    return {

      schemaVersion: DRAFT_SCHEMA_VERSION,

      revision: deckRevision(),

      draftKey: draftKey(),

      operationLogKey: operationLogKey(),

      undoDepth: undoStack.length,

      redoDepth: redoStack.length,

      autoSave: {

        enabled: isWritableDevServer(),

        state: autoSaveState,

        pending: hasPendingChanges(),

        inFlight: Boolean(activeSavePromise),

        lastSavedAt: autoSaveLastSavedAt,

        lastError: autoSaveLastError || null

      },

      entries: loadOperationLog().slice()

    };

  }



  function saveDraftNow() {

    const entries = [];

    const currentDeckFontState = deckFontState();

    const currentSlideBackgroundStates = slideBackgroundStates();

    const currentSlideMaskStates = slideMaskStates();

    const deckFontDirty = appearanceStateChanged(savedDeckFontState, currentDeckFontState);

    const slideBackgroundEntries = Object.keys(currentSlideBackgroundStates).filter((slideId) => (

      currentSlideBackgroundStates[slideId] !== (savedSlideBackgroundStates[slideId] || '')

    )).map((slideId) => ({

      slideId: slideId,

      backgroundColor: currentSlideBackgroundStates[slideId]

    }));

    const maskIds = new Set([

      ...Object.keys(savedSlideMaskStates || {}),

      ...Object.keys(currentSlideMaskStates || {})

    ]);

    const slideMaskEntries = Array.from(maskIds).filter((slideId) => (

      appearanceStateChanged(currentSlideMaskStates[slideId], savedSlideMaskStates[slideId])

    )).map((slideId) => ({

      slideId: slideId,

      color: currentSlideMaskStates[slideId] ? currentSlideMaskStates[slideId].color : DEFAULT_SLIDE_MASK_COLOR,

      opacity: currentSlideMaskStates[slideId] ? currentSlideMaskStates[slideId].opacity : DEFAULT_SLIDE_MASK_OPACITY

    }));

    stage.querySelectorAll(':scope > .slide').forEach((slide) => {

      editableElements(slide).forEach((el) => {

        if (!changedElements.has(el)) return;

        if (el.dataset && el.dataset.editClone) {

          if (getComputedStyle(el).display === 'none') return;

          if (slide.id) entries.push({ clone: true, slide: slide.id, html: sanitizedElementHtml(el) });

          return;

        }

        const state = measureElementState(el);

        entries.push({

          key: elementKey(el),

          left: state.left + 'px',

          top: state.top + 'px',

          width: state.width + 'px',

          height: state.height + 'px',

          fontSize: state.fontSize + 'px',

          fontFamily: state.fontFamily,

          fontWeight: state.fontWeight || null,

          fontStyle: state.fontStyle || null,

          textDecorationLine: state.textDecorationLine || null,

          textAlign: state.textAlign || null,

          color: state.color || null,

          background: state.background || null,

          borderColor: state.borderColor || null,

          zIndex: state.zIndex || null,

          display: state.display || null,

          lineHeight: state.lineHeight || null,

          letterSpacing: state.letterSpacing || null,

          textWrap: state.textWrap || null,

          whiteSpace: state.whiteSpace || null,

          wrapMode: state.wrapMode || null,

          alignContent: state.alignContent || null,

          flexDirection: state.flexDirection || null,

          justifyContent: state.justifyContent || null,

          alignItems: state.alignItems || null,

          verticalAlign: state.verticalAlign || null,

          compositeGroupState: state.compositeGroupState || null,

          groupId: groupId(el) || null,

          transform: state.transform || null,

          transformOrigin: state.transformOrigin || null,

          typography: serializeInlineTypography(el),

          text: textDirty.has(el) ? el.innerHTML : null

        });

      });

    });

    if (entries.length === 0 && !slideOrderDirty && !deckFontDirty && slideBackgroundEntries.length === 0 && slideMaskEntries.length === 0) {

      clearDraft();

      return false;

    }

    return storageSet(draftKey(), JSON.stringify({

      schemaVersion: DRAFT_SCHEMA_VERSION,

      revision: deckRevision(),

      savedAt: Date.now(),

      entries: entries,

      slideOrder: slideOrderDirty ? currentSlideOrder() : null,

      deckFont: deckFontDirty ? currentDeckFontState : null,

      slideBackgrounds: slideBackgroundEntries.length ? slideBackgroundEntries : null,

      slideMasks: slideMaskEntries.length ? slideMaskEntries : null

    }));

  }



  function scheduleAutomaticSave(delay) {

    if (autoSaveTimer) clearTimeout(autoSaveTimer);

    if (!isWritableDevServer()) {

      setAutoSaveState('draft-only');

      autoSaveTimer = null;

      return;

    }

    autoSaveTimer = setTimeout(() => {

      autoSaveTimer = null;

      void saveAutomatically();

    }, delay === undefined ? AUTO_SAVE_DELAY_MS : delay);

  }



  function scheduleDraftSave() {

    documentChangeVersion += 1;

    if (draftTimer) clearTimeout(draftTimer);

    draftTimer = setTimeout(() => {

      draftTimer = null;

      saveDraftNow();

    }, AUTO_SAVE_DELAY_MS);

    scheduleAutomaticSave();

    setAutoSaveState(isWritableDevServer() ? 'pending' : 'draft-only');

  }



  function applyDraft(entries, slideOrder, deckFont, slideBackgrounds, slideMasks) {

    const beforeOrder = currentSlideOrder();

    if (Array.isArray(slideOrder) && slideOrder.length && window.SlidePlayer && typeof window.SlidePlayer.reorderSlides === 'function') {

      window.SlidePlayer.reorderSlides(slideOrder, { notify: false });

      updateSlideOrderDirty();

    }

    const items = [];

    if (deckFont && typeof deckFont === 'object') {

      const before = deckFontState();

      applyDeckFontState(deckFont);

      items.push({ type: 'deck-font', label: M.defaultFontChange, before: before, after: deckFontState() });

    }

    (Array.isArray(slideBackgrounds) ? slideBackgrounds : []).forEach((entry) => {

      const slide = entry && entry.slideId ? document.getElementById(entry.slideId) : null;

      if (!slide) return;

      const before = { backgroundColor: slide.style.backgroundColor || '' };

      if (entry.backgroundColor) slide.style.backgroundColor = entry.backgroundColor;

      else slide.style.removeProperty('background-color');

      items.push({

        type: 'slide-background',

        label: M.slideBackgroundChange,

        slideId: slide.id,

        before: before,

        after: { backgroundColor: slide.style.backgroundColor || '' }

      });

    });

    (Array.isArray(slideMasks) ? slideMasks : []).forEach((entry) => {

      const slide = entry && entry.slideId ? document.getElementById(entry.slideId) : null;

      if (!slide) return;

      const before = slideMaskState(slide);

      const after = applySlideMaskState(slide, {

        color: entry.color,

        opacity: entry.opacity

      });

      items.push({

        type: 'slide-mask',

        label: M.slideMaskChange,

        slideId: slide.id,

        before: before,

        after: after

      });

    });

    entries.forEach((entry) => {

      if (entry.clone) {

        const slide = document.getElementById(entry.slide);

        if (!slide) return;

        const wrap = document.createElement('div');

        wrap.innerHTML = entry.html;

        const node = wrap.firstElementChild;

        if (!node) return;

        slide.appendChild(node);

        const after = snapshotElementState(node);

        items.push({

          el: node,

          key: elementKey(node),

          type: 'snapshot',

          before: Object.assign({}, after, { display: 'none' }),

          after: after

        });

        changedElements.add(node);

        return;

      }

      const el = elementByKey(entry.key);

      if (!el) return;

      const before = snapshotElementState(el);

      if (entry.left) setUserStyle(el, 'left', entry.left);

      if (entry.top) setUserStyle(el, 'top', entry.top);

      if (entry.width) setUserStyle(el, 'width', entry.width);

      if (entry.height) setUserStyle(el, 'height', entry.height);

      if (entry.fontSize) setUserStyle(el, 'font-size', entry.fontSize);

      if (Object.prototype.hasOwnProperty.call(entry, 'fontFamily')) setUserStyle(el, 'font-family', entry.fontFamily || '');

      if (entry.fontWeight) setUserStyle(el, 'font-weight', entry.fontWeight);

      if (entry.fontStyle) setUserStyle(el, 'font-style', entry.fontStyle);

      if (entry.textDecorationLine) setUserStyle(el, 'text-decoration-line', entry.textDecorationLine);

      if (entry.textAlign) setUserStyle(el, 'text-align', entry.textAlign);

      if (entry.color) setUserStyle(el, 'color', entry.color);

      if (entry.background) setUserStyle(el, 'background', entry.background);

      if (entry.borderColor) setUserStyle(el, 'border-color', entry.borderColor);

      if (entry.zIndex) setUserStyle(el, 'z-index', entry.zIndex);

      if (entry.display) setUserStyle(el, 'display', entry.display);

      if (entry.lineHeight) setUserStyle(el, 'line-height', entry.lineHeight);

      if (entry.letterSpacing) setUserStyle(el, 'letter-spacing', entry.letterSpacing);

      if (entry.textWrap) setUserStyle(el, 'text-wrap', entry.textWrap);

      if (entry.whiteSpace) setUserStyle(el, 'white-space', entry.whiteSpace);

      if (entry.wrapMode) el.dataset.editWrapMode = entry.wrapMode;

      if (entry.alignContent) setUserStyle(el, 'align-content', entry.alignContent);

      if (entry.flexDirection) setUserStyle(el, 'flex-direction', entry.flexDirection);

      if (entry.justifyContent) setUserStyle(el, 'justify-content', entry.justifyContent);

      if (entry.alignItems) setUserStyle(el, 'align-items', entry.alignItems);

      if (entry.verticalAlign) el.dataset.editVerticalAlign = entry.verticalAlign;

      if (Object.prototype.hasOwnProperty.call(entry, 'compositeGroupState')) {

        if (entry.compositeGroupState) el.dataset.editGroupState = entry.compositeGroupState;

        else delete el.dataset.editGroupState;

      }

      if (Object.prototype.hasOwnProperty.call(entry, 'groupId')) {

        if (entry.groupId) el.dataset.editGroup = entry.groupId;

        else delete el.dataset.editGroup;

      }

      if (entry.transform) setUserStyle(el, 'transform', entry.transform);

      if (entry.transformOrigin) setUserStyle(el, 'transform-origin', entry.transformOrigin);

      if (entry.typography) applyInlineTypography(el, entry.typography);

      if (entry.text !== null && entry.text !== undefined) {

        el.innerHTML = entry.text;

        textDirty.add(el);

      }

      const after = snapshotElementState(el);

      items.push({ el: el, key: entry.key, type: 'snapshot', before: before, after: after });

      changedElements.add(el);

    });

    const afterOrder = currentSlideOrder();

    if (beforeOrder.join('|') !== afterOrder.join('|')) {

      items.push({ type: 'slide-order', label: M.slideOrderChange, before: beforeOrder, after: afterOrder });

    }

    // Restoring a draft is one user action.  Text, geometry and slide order

    // therefore share one undo step instead of requiring repeated Ctrl+Z.

    if (items.length) pushCommand({ type: 'batch', label: M.draftRestoreChange, itemType: 'snapshot', items: items });

    lastPaletteSignature = null;

    refreshColorSwatches();

    updateAppearanceControls();

    updateActionStates();

  }



  function checkDraftOnLoad() {

    // A regenerated deck may keep the same file path while its Theme/Layout and

    // materialized geometry have changed.  Never replay the path-only legacy

    // draft into a new revision.

    storageRemove(legacyDraftKey());

    const raw = storageGet(draftKey());

    if (!raw) return;

    let draft;

    try {

      draft = JSON.parse(raw);

    } catch (err) {

      storageRemove(draftKey());

      return;

    }

    if (draft.schemaVersion !== DRAFT_SCHEMA_VERSION || draft.revision !== deckRevision()) {

      storageRemove(draftKey());

      return;

    }



    const prompt = document.createElement('div');

    prompt.id = 'edit-draft-prompt';

    prompt.style.cssText =

      'position:fixed;left:50%;top:16px;transform:translateX(-50%);z-index:103;' +

      'background:rgba(10,14,20,.95);color:#E6EAF0;font:13px var(--font-mono);' +

      'padding:10px 16px;border-radius:8px;display:flex;gap:12px;align-items:center;' +

      'border:1px solid rgba(63,208,232,.3);box-shadow:0 12px 32px rgba(0,0,0,.5);';



    const text = document.createElement('span');

    text.textContent = M.draftFound + ' ' + new Date(draft.savedAt).toLocaleString();



    const restoreBtn = document.createElement('button');

    restoreBtn.textContent = M.restore;

    restoreBtn.style.cssText =

      'background:#3FD0E8;color:#0B1220;border:0;border-radius:6px;padding:4px 10px;font-weight:700;cursor:pointer;';

    restoreBtn.onclick = () => {

      applyDraft(draft.entries || [], draft.slideOrder || null, draft.deckFont || null, draft.slideBackgrounds || null, draft.slideMasks || null);

      prompt.remove();

    };



    const discardBtn = document.createElement('button');

    discardBtn.textContent = M.discard;

    discardBtn.style.cssText =

      'background:transparent;color:#E6EAF0;border:1px solid rgba(255,255,255,.3);border-radius:6px;padding:4px 10px;cursor:pointer;';

    discardBtn.onclick = () => {

      clearDraft();

      prompt.remove();

    };



    prompt.append(text, restoreBtn, discardBtn);

    document.body.appendChild(prompt);

  }



  function currentFilePath() {

    let value = location.pathname || '';

    try {

      value = decodeURIComponent(value);

    } catch (err) {

      value = location.pathname || '';

    }

    value = value.replace(/\\/g, '/');

    if (value.endsWith('/')) value += 'index.html';

    value = value.replace(/^\/+/, '');

    if (location.protocol === 'file:') value = value.split('/').pop() || 'presentation.html';

    return value || 'index.html';

  }



  function suggestedFileName() {

    let name = currentFilePath().split('/').pop() || 'presentation.html';

    if (name.toLowerCase() === 'index.html') {

      const themeId = document.documentElement.dataset.themeId

        || document.documentElement.dataset.theme

        || '';

      if (themeId) name = themeId.replace(/[^a-z0-9_-]+/gi, '-') + '-edited.html';

    }

    return /\.html?$/i.test(name) ? name : name + '.html';

  }



  function suggestedExportFileName() {

    const name = suggestedFileName();

    return name.replace(/\.html?$/i, '') + '-edited.html';

  }



  // Persist the file handle against an identity embedded in the saved HTML,
  // not against location.href. Keep the legacy database name so existing
  // bindings continue to work after this behavior becomes the formal contract.
  const FILE_HANDLE_DB_NAME = 'html-editor-file-handle-pilot-v2';

  const FILE_HANDLE_STORE_NAME = 'handles';

  const FILE_HANDLE_DB_VERSION = 1;

  const FILE_HANDLE_ID_ATTRIBUTE = 'data-editor-file-handle-id';

  const SAVE_BINDING_STATE_BOUND = 'bound';

  const SAVE_BINDING_STATE_UNBOUND = 'unbound';

  let activeFileHandle = null;

  let activeFileHandleId = document.documentElement

    ? document.documentElement.getAttribute(FILE_HANDLE_ID_ATTRIBUTE)

    : null;

  let saveBindingState = SAVE_BINDING_STATE_UNBOUND;

  let saveBindingFileName = '';



  function setSaveButtonBindingState(state, fileName, reason) {

    const readOnlyPreview = isReadOnlyPreview();

    saveBindingState = state === SAVE_BINDING_STATE_BOUND

      ? SAVE_BINDING_STATE_BOUND

      : SAVE_BINDING_STATE_UNBOUND;

    saveBindingFileName = fileName || '';

    if (!saveBtn) return;

    const bound = saveBindingState === SAVE_BINDING_STATE_BOUND;

    const label = saveBtn.querySelector('span');

    const buttonText = bound ? M.saveProgress : M.saveStart;

    const detail = readOnlyPreview

      ? M.previewReadOnly

      : bound && saveBindingFileName

      ? M.saveDirectTo + saveBindingFileName + '（' + M.saveVerified + '）'

      : (reason || M.saveBindingMissing);

    if (label) label.textContent = buttonText;

    saveBtn.dataset.saveBindingState = saveBindingState;

    saveBtn.dataset.saveBindingVerified = bound ? 'true' : 'false';

    saveBtn.dataset.saveBindingMethod = readOnlyPreview

      ? 'read-only-preview'

      : bound

      ? (isWritableDevServer() ? 'dev-server' : 'file-handle')

      : 'none';

    saveBtn.dataset.autoSaveState = autoSaveState;

    saveBtn.dataset.autoSaveEnabled = isWritableDevServer() ? 'true' : 'draft-only';

    if (saveBindingFileName) {

      saveBtn.dataset.saveBoundFile = saveBindingFileName;

    } else {

      delete saveBtn.dataset.saveBoundFile;

    }

    saveBtn.title = buttonText + ' (Ctrl+S)\uff5c' + detail;

    saveBtn.setAttribute('aria-label', buttonText + ' (Ctrl+S)');

    saveBtn.setAttribute('aria-disabled', readOnlyPreview ? 'true' : 'false');

    saveBtn.style.background = bound ? 'rgba(34,197,94,.18)' : 'rgba(245,158,11,.18)';

    saveBtn.style.color = bound ? '#A7F3D0' : '#FFD08A';

    saveBtn.style.boxShadow = bound

      ? 'inset 0 0 0 1px rgba(74,222,128,.52)'

      : 'inset 0 0 0 1px rgba(251,191,36,.55)';

  }



  async function refreshSaveButtonBindingState() {

    if (isReadOnlyPreview()) {

      setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND, '', M.previewReadOnly);

      return;

    }

    if (isWritableDevServer()) {

      setSaveButtonBindingState(SAVE_BINDING_STATE_BOUND, suggestedFileName());

      return;

    }

    if (!activeFileHandleId) {

      setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND);

      return;

    }

    const handle = await getRememberedFileHandle(activeFileHandleId);

    if (!handle) {

      setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND, '', M.saveBindingUnavailable);

      return;

    }

    if (typeof handle.queryPermission === 'function') {

      try {

        const permission = await handle.queryPermission({ mode: 'readwrite' });

        if (permission === 'denied') {

          setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND, '', M.saveBindingUnavailable);

          return;

        }

      } catch (err) {

        setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND, '', M.saveBindingUnavailable);

        return;

      }

    }

    setSaveButtonBindingState(SAVE_BINDING_STATE_BOUND, handle.name || suggestedFileName());

  }



  function createFileHandleId() {

    if (window.crypto && typeof window.crypto.randomUUID === 'function') {

      return window.crypto.randomUUID();

    }

    return 'fh-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);

  }



  function setActiveFileHandleId(id) {

    activeFileHandleId = id || null;

    if (activeFileHandleId && document.documentElement) {

      document.documentElement.setAttribute(FILE_HANDLE_ID_ATTRIBUTE, activeFileHandleId);

    }

  }



  function fileHandleStorageKey(id) {

    return id || activeFileHandleId || null;

  }



  function openFileHandleDatabase() {

    return new Promise((resolve, reject) => {

      if (!window.indexedDB) {

        reject(new Error('IndexedDB unavailable'));

        return;

      }

      let request;

      try {

        request = window.indexedDB.open(FILE_HANDLE_DB_NAME, FILE_HANDLE_DB_VERSION);

      } catch (err) {

        reject(err);

        return;

      }

      request.onupgradeneeded = () => {

        const db = request.result;

        if (!db.objectStoreNames.contains(FILE_HANDLE_STORE_NAME)) {

          db.createObjectStore(FILE_HANDLE_STORE_NAME);

        }

      };

      request.onsuccess = () => resolve(request.result);

      request.onerror = () => reject(request.error || new Error('IndexedDB open failed'));

      request.onblocked = () => reject(new Error('IndexedDB open blocked'));

    });

  }



  async function getRememberedFileHandle(id) {

    const storageKey = fileHandleStorageKey(id);

    if (!storageKey) return null;

    if (activeFileHandle && activeFileHandleId === storageKey) return activeFileHandle;

    let db = null;

    try {

      db = await openFileHandleDatabase();

      return await new Promise((resolve, reject) => {

        const request = db.transaction(FILE_HANDLE_STORE_NAME, 'readonly')

          .objectStore(FILE_HANDLE_STORE_NAME)

          .get(storageKey);

        request.onsuccess = () => {

          activeFileHandle = request.result || null;

          if (activeFileHandle) activeFileHandleId = storageKey;

          resolve(activeFileHandle);

        };

        request.onerror = () => reject(request.error || new Error('File handle read failed'));

      });

    } catch (err) {

      return null;

    } finally {

      if (db) db.close();

    }

  }



  async function rememberFileHandle(handle, id) {

    const storageKey = fileHandleStorageKey(id) || createFileHandleId();

    activeFileHandle = handle;

    activeFileHandleId = storageKey;

    let db = null;

    try {

      db = await openFileHandleDatabase();

      await new Promise((resolve, reject) => {

        const tx = db.transaction(FILE_HANDLE_STORE_NAME, 'readwrite');

        tx.oncomplete = () => resolve();

        tx.onerror = () => reject(tx.error || new Error('File handle write failed'));

        tx.onabort = () => reject(tx.error || new Error('File handle write aborted'));

        tx.objectStore(FILE_HANDLE_STORE_NAME).put(handle, storageKey);

      });

      return true;

    } catch (err) {

      return false;

    } finally {

      if (db) db.close();

    }

  }



  async function ensureFileHandleWritePermission(handle) {

    if (!handle || typeof handle.createWritable !== 'function') return false;

    try {

      let permission = typeof handle.queryPermission === 'function'

        ? await handle.queryPermission({ mode: 'readwrite' })

        : 'prompt';

      if (permission !== 'granted' && typeof handle.requestPermission === 'function') {

        permission = await handle.requestPermission({ mode: 'readwrite' });

      }

      return permission === 'granted';

    } catch (err) {

      return false;

    }

  }



  async function writeHtmlToFileHandle(handle, html) {

    const writable = await handle.createWritable();

    try {

      await writable.write(html);

      await writable.close();

    } catch (err) {

      try {

        if (typeof writable.abort === 'function') await writable.abort();

      } catch (abortErr) {

        // The original write error is more useful to the user.

      }

      throw err;

    }

  }



  async function saveViaRememberedFileHandle() {

    if (typeof window.showSaveFilePicker !== 'function') {

      setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND);

      return saveViaFilePicker();

    }

    const handle = await getRememberedFileHandle(activeFileHandleId);

    if (handle && await ensureFileHandleWritePermission(handle)) {

      try {

        const payload = savePayload(activeFileHandleId);

        await writeHtmlToFileHandle(handle, payload.html);

        markCurrentDocumentSaved();

        setSaveButtonBindingState(SAVE_BINDING_STATE_BOUND, handle.name || suggestedFileName());

        showTransientReadout(M.savedViaHandle + handle.name, 2600);

        return { saved: true, path: handle.name, fileName: handle.name, method: 'file-handle', verified: true };

      } catch (err) {

        // A stale handle falls through to a fresh one-time picker.

        setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND, '', M.saveBindingUnavailable);

      }

    } else if (handle) {

      setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND, '', M.saveBindingUnavailable);

    }

    return saveViaFilePicker();

  }



  function savePayload(fileHandleId) {

    const id = fileHandleId || activeFileHandleId || createFileHandleId();

    const clone = sanitizedClone();

    if (clone && typeof clone.setAttribute === 'function') {

      clone.setAttribute(FILE_HANDLE_ID_ATTRIBUTE, id);

    }

    return {

      path: currentFilePath(),

      fileHandleId: id,

      html: '<!DOCTYPE html>\n' + clone.outerHTML

    };

  }



  function saveViaBrowserDownload(options) {

    const purpose = options && options.purpose === 'export' ? 'export' : 'save';

    if (purpose !== 'export') setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND);

    const payload = savePayload();

    const blob = new Blob([payload.html], { type: 'text/html' });

    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');

    link.href = url;

    link.download = purpose === 'export' ? suggestedExportFileName() : suggestedFileName();

    document.body.appendChild(link);

    link.click();

    link.remove();

    setTimeout(() => URL.revokeObjectURL(url), 0);

    showTransientReadout(M.saveAsOpened, 4200);

    return { saved: false, path: link.download, fileName: link.download, method: 'browser-save-as', pending: true };

  }



  async function saveViaFilePicker(options) {

    const purpose = options && options.purpose === 'export' ? 'export' : 'save';

    try {

      if (typeof window.showSaveFilePicker !== 'function') return saveViaBrowserDownload({ purpose: purpose });

      const handle = await window.showSaveFilePicker({

        suggestedName: purpose === 'export' ? suggestedExportFileName() : suggestedFileName(),

        types: [{ description: 'HTML', accept: { 'text/html': ['.html'] } }]

      });

      const fileHandleId = createFileHandleId();

      const payload = savePayload(fileHandleId);

      await writeHtmlToFileHandle(handle, payload.html);

      const remembered = await rememberFileHandle(handle, fileHandleId);

      setActiveFileHandleId(fileHandleId);

      markCurrentDocumentSaved();

      setSaveButtonBindingState(SAVE_BINDING_STATE_BOUND, handle.name || suggestedFileName());

      showTransientReadout(

        (purpose === 'export' ? M.exportDone + '\uff1a' : M.savedViaPicker) + handle.name,

        2600

      );

      return {

        saved: true,

        path: handle.name,

        fileName: handle.name,

        method: purpose === 'export'

          ? (remembered ? 'file-handle-export' : 'file-export')

          : (remembered ? 'file-handle-picker' : 'file-picker'),

        verified: Boolean(remembered || activeFileHandle === handle),

        fileHandleId

      };

    } catch (err) {

      if (err && err.name === 'AbortError') {

        if (purpose !== 'export') setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND);

        showTransientReadout(M.saveCanceled, 2200);

        return { saved: false, method: purpose === 'export' ? 'file-export' : 'file-picker', canceled: true };

      }

      const reason = err && err.message ? err.message : 'unknown error';

      if (purpose !== 'export') setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND, '', reason);

      showTransientReadout(M.saveUnavailable + ' ' + reason, 4200);

      return { saved: false, method: purpose === 'export' ? 'file-export' : 'file-picker', error: reason };

    }

  }



  async function postToWritableDevServer(payload) {

    const res = await fetch('/__save', {

      method: 'POST',

      headers: { 'Content-Type': 'application/json' },

      body: JSON.stringify(payload)

    });

    const raw = await res.text();

    let data = {};

    try {

      data = raw ? JSON.parse(raw) : {};

    } catch (err) {

      data = {};

    }

    if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));

    return data;

  }



  function reconcileAfterPersist(saveVersion) {

    const current = saveVersion === documentChangeVersion;

    if (current) {

      markCurrentDocumentSaved();

    } else {

      // The request serialized an older DOM. Keep the newer edits dirty and
      // refresh the local recovery draft before scheduling the next save.
      saveDraftNow();

      setAutoSaveState('pending');

      scheduleAutomaticSave();

    }

    return current;

  }



  async function saveAutomatically() {

    if (!isWritableDevServer()) {

      setAutoSaveState('draft-only');

      return { saved: false, automatic: true, method: 'draft-only' };

    }

    commitPendingChanges();

    if (!hasPendingChanges()) {

      return { saved: false, automatic: true, method: 'no-changes' };

    }

    if (activeSavePromise) {

      autoSaveQueued = true;

      return { saved: false, automatic: true, pending: true, method: 'queued' };

    }

    const payload = savePayload();

    const saveVersion = documentChangeVersion;

    setAutoSaveState('saving');

    showTransientReadout(M.autoSaving, 120000);

    const request = (async () => {

      try {

        const data = await postToWritableDevServer(payload);

        const current = reconcileAfterPersist(saveVersion);

        autoSaveLastSavedAt = Date.now();

        autoSaveLastError = '';

        if (!current) setAutoSaveState('pending');

        else setAutoSaveState('saved');

        showTransientReadout(current ? M.autoSaved + payload.path : M.autoSaveQueued, 2600);

        return {

          ...data,

          saved: true,

          automatic: true,

          stale: !current,

          path: payload.path,

          method: 'auto-overwrite'

        };

      } catch (err) {

        const reason = err && err.message ? err.message : 'unknown error';

        autoSaveLastError = reason;

        setAutoSaveState('error', reason);

        showTransientReadout(M.autoSaveFailed + reason, 4200);

        return {

          saved: false,

          automatic: true,

          path: payload.path,

          method: 'auto-overwrite',

          error: reason

        };

      } finally {

        if (activeSavePromise === request) activeSavePromise = null;

        if (autoSaveQueued) {

          autoSaveQueued = false;

          if (hasPendingChanges()) scheduleAutomaticSave();

        }

      }

    })();

    activeSavePromise = request;

    return request;

  }



  async function saveToServer() {

    if (isReadOnlyPreview()) {

      setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND, '', M.previewReadOnly);

      showTransientReadout(M.previewReadOnly, 3200);

      return { saved: false, method: 'read-only-preview' };

    }

    commitPendingChanges();

    if (activeSavePromise) {

      const pendingSave = activeSavePromise;

      try {

        await pendingSave;

      } catch (err) {

        // The active save reports its own failure and leaves the draft dirty.

      }

      if (!hasPendingChanges()) return pendingSave;

    }

    if (autoSaveTimer) clearTimeout(autoSaveTimer);

    autoSaveTimer = null;

    const payload = savePayload();

    if (!isWritableDevServer()) {

      return saveViaRememberedFileHandle();

    }



    const saveVersion = documentChangeVersion;

    setAutoSaveState('saving');

    const request = (async () => {

      try {

        const data = await postToWritableDevServer(payload);

        const current = reconcileAfterPersist(saveVersion);

        setSaveButtonBindingState(SAVE_BINDING_STATE_BOUND, suggestedFileName());

        showTransientReadout(M.savedAt + payload.path, 3200);

        return {

          ...data,

          saved: true,

          stale: !current,

          path: payload.path,

          method: 'overwrite'

        };

      } catch (err) {

        const reason = err && err.message ? err.message : 'unknown error';

        const pickerResult = await saveViaRememberedFileHandle();

        if (pickerResult.saved || pickerResult.canceled) return pickerResult;

        setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND, '', M.saveFailed + reason);

        setAutoSaveState('error', reason);

        showTransientReadout(M.saveFailed + reason, 4200);

        if (hasPendingChanges()) saveDraftNow();

        return {

          ...pickerResult,

          path: payload.path,

          method: 'overwrite-or-file-picker',

          serverError: reason

        };

      } finally {

        if (activeSavePromise === request) activeSavePromise = null;

        if (autoSaveQueued) {

          autoSaveQueued = false;

          if (hasPendingChanges()) scheduleAutomaticSave();

        }

      }

    })();

    activeSavePromise = request;

    return request;

  }



  if (canvasBox) {

    document.addEventListener('click', (e) => {

      if (editMode && canvasBox.contains(e.target)) e.stopPropagation();

    }, true);

  }



  window.addEventListener('keydown', (e) => {

    if (e.key === 'Escape' && objectContextMenu && objectContextMenu.style.display !== 'none') {

      e.preventDefault();

      e.stopImmediatePropagation();

      hideObjectContextMenu();

      return;

    }

    if ((e.key === 'e' || e.key === 'E') && !e.ctrlKey && !e.metaKey && !e.altKey && !isTypingContext()) {

      e.preventDefault();

      e.stopImmediatePropagation();

      toggleEditMode();

      return;

    }

    if (!(e.ctrlKey || e.metaKey)) return;

    const key = e.key.toLowerCase();

    const wantsUndo = key === 'z' && !e.shiftKey;

    const wantsRedo = key === 'y' || (key === 'z' && e.shiftKey);

    if (wantsUndo || wantsRedo) {

      if (textEditingEl && isTypingContext()) return;

      e.preventDefault();

      e.stopPropagation();

      if (!requireEditMode(wantsUndo ? M.undoLabel : M.redoLabel)) return;

      if (wantsUndo) undo();

      else redo();

      return;

    }

    if (!editMode || isTypingContext()) return;

    if (key === 'g') {

      e.preventDefault();

      e.stopPropagation();

      if (e.shiftKey) ungroupSelection();

      else groupSelection();

      return;

    }

    if (key === 'd') {

      if (!selectedTargets().length) return;

      e.preventDefault();

      e.stopPropagation();

      duplicateSelection();

      return;

    }

    if (key === 'c') {

      const sel = window.getSelection && window.getSelection();

      if (sel && sel.toString()) return;

      if (!selectedTargets().length) return;

      e.preventDefault();

      e.stopPropagation();

      copySelection();

      return;

    }

    if (key === 'v') {

      if (!clipboardData || !clipboardData.length) return;

      e.preventDefault();

      e.stopPropagation();

      pasteClipboard();

    }

  }, true);



  window.addEventListener('keydown', (e) => {

    if (!editMode) return;

    if (isTypingContext()) {

      const typingNavKeys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' ', 'PageUp', 'PageDown', 'Home', 'End'];

      if (typingNavKeys.indexOf(e.key) >= 0) e.stopPropagation();

      return;

    }

    const arrowKeys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'];

    if (arrowKeys.indexOf(e.key) >= 0 && selectedEl && !textEditingEl && !e.ctrlKey && !e.metaKey && !e.altKey) {

      e.preventDefault();

      e.stopImmediatePropagation();

      nudgeSelection(e.key, e.shiftKey ? 10 : 1);

      return;

    }

    const deleteKey = e.key === 'Delete'

      || e.key === 'Backspace'

      || e.code === 'Delete'

      || e.code === 'Backspace'

      || e.keyCode === 46

      || e.keyCode === 8;

    if (deleteKey && selectedTargets().length && !textEditingEl) {

      e.preventDefault();

      e.stopImmediatePropagation();

      deleteSelection();

      return;

    }

    const navKeys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' ', 'PageUp', 'PageDown', 'Home', 'End'];

    if (navKeys.indexOf(e.key) === -1) return;

    const hasActiveEditingTarget = !!(selectedEl || textEditingEl || dragEl || resizeEl);

    if (!hasActiveEditingTarget) return;

    e.stopPropagation();

    e.preventDefault();

  }, true);



  window.addEventListener('keydown', (e) => {

    if (e.key === 'Escape' && !editMode) {

      e.preventDefault();

      e.stopImmediatePropagation();

      returnToEditModeFromEscape();

      return;

    }

    if (e.key === 'Escape' && textEditingEl) {

      endTextEdit();

      return;

    }

    if (e.key === 'Escape' && editMode) {

      if (saveMenu && saveMenu.style.display !== 'none') {

        toggleSaveMenu(false);

        return;

      }

      if (pendingInsertKind || insertDrawState) {

        cancelPendingInsert();

        return;

      }

      deselectElement();

      return;

    }

    if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {

      e.preventDefault();

      if (requireEditMode(M.saveShortcut)) saveToServer();

      return;

    }

    if (isTypingContext()) return;

    if (editMode && selectedEl && (e.key === '[' || e.key === ']')) {

      e.preventDefault();

      const magnitude = e.shiftKey ? 5 : 1;

      adjustSelectedFont(e.key === ']' ? magnitude : -magnitude);

      return;

    }

    if (e.key === ' ' && editMode) {

      deselectElement();

    }

    if (e.key === 'x' || e.key === 'X') {

      if (requireEditMode(M.export)) exportHtml();

    }

  });



  function makeDivider() {

    const divider = document.createElement('span');

    divider.className = 'divider';

    return divider;

  }



  function makeLabeledBtn(svgIcon, shortLabel, fullLabel, onClick) {

    const btn = document.createElement('button');

    const label = document.createElement('span');

    label.textContent = shortLabel;

    label.style.cssText = 'font-size:12px;white-space:nowrap;';

    btn.title = fullLabel;

    btn.setAttribute('aria-label', fullLabel);

    btn.innerHTML =

      '<svg viewBox="0 0 24 24" style="width:15px;height:15px;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round;stroke-linejoin:round;flex-shrink:0;">' +

      svgIcon +

      '</svg>';

    btn.appendChild(label);

    btn.style.cssText =

      'height:32px;padding:0 10px;border:0;background:transparent;cursor:pointer;' +

      'color:inherit;border-radius:999px;display:inline-flex;align-items:center;gap:5px;' +

      'width:auto;min-width:32px;flex:0 0 auto;';

    btn.onclick = (ev) => {

      ev.stopPropagation();

      onClick();

    };

    labeledToolbarBtns.push({ button: btn, label: label });

    return btn;

  }



  function makeSaveMenuItem(svgIcon, shortLabel, fullLabel, onClick) {

    const btn = document.createElement('button');

    const label = document.createElement('span');

    btn.type = 'button';

    btn.dataset.editorChrome = 'true';

    btn.setAttribute('role', 'menuitem');

    btn.setAttribute('aria-label', fullLabel);

    btn.title = fullLabel;

    label.textContent = shortLabel;

    label.style.cssText = 'font:700 12px/1.2 var(--font-body);white-space:nowrap;';

    btn.innerHTML =

      '<svg viewBox="0 0 24 24" aria-hidden="true" style="width:15px;height:15px;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round;stroke-linejoin:round;flex-shrink:0;">' +

      svgIcon +

      '</svg>';

    btn.appendChild(label);

    btn.style.cssText =

      'display:flex;align-items:center;gap:8px;width:100%;min-height:36px;padding:8px 10px;' +

      'border:0;border-radius:7px;background:transparent;color:#182028;text-align:left;' +

      'cursor:pointer;font:700 12px/1.2 var(--font-body);';

    btn.addEventListener('click', (event) => {

      event.preventDefault();

      event.stopPropagation();

      if (btn.disabled) return;

      toggleSaveMenu(false);

      onClick();

    });

    return btn;

  }



  function updateToolbarLayout() {

    barInner.style.gap = '4px';

    barInner.style.padding = '0 8px';

    if (editModeLabel) editModeLabel.style.display = editMode ? '' : 'none';

    const editOnlyButtons = [undoBtn, redoBtn, insertBtn, imageUploadBtn, appearanceBtn, saveGroup];

    editOnlyButtons.forEach((btn) => {

      if (btn) btn.style.display = editMode ? '' : 'none';

    });

    labeledToolbarBtns.forEach(({ button, label }) => {

      // Keep the action name visible so the compact toolbar never leaves
      // icon-only controls for the primary editing actions.
      label.style.display = editMode || button === editBtn ? '' : 'none';

      button.style.padding = '0 10px';

    });



    if (!editMode) return;



    barInner.style.overflowX = 'hidden';

    barInner.style.flexWrap = 'nowrap';

  }



  const ICON_EDIT = '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>';

  const ICON_UNDO = '<path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-15-6.7L3 13"/>';

  const ICON_REDO = '<path d="M21 7v6h-6"/><path d="M3 17a9 9 0 0 1 15-6.7L21 13"/>';

  const ICON_INSERT = '<path d="M12 5v14"/><path d="M5 12h14"/>';

  const ICON_IMAGE_UPLOAD = '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m3 16 4-4 3 3 3-3 8 6"/><path d="M12 2v7"/><path d="m9 6 3 3 3-3"/>';

  const ICON_APPEARANCE = '<path d="M12 3a9 9 0 1 0 0 18h1.2a1.8 1.8 0 0 0 0-3.6h-1.1a1.7 1.7 0 0 1 0-3.4H15a6 6 0 0 0 0-12Z"/><circle cx="7.5" cy="10" r=".8"/><circle cx="9" cy="6.5" r=".8"/><circle cx="14" cy="6" r=".8"/>';

  const ICON_EXPORT = '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>';

  const ICON_PPTX = '<path d="M6 2h9l4 4v16H6Z"/><path d="M15 2v5h5"/><path d="M9 11h4a2 2 0 0 1 0 4H9Z"/><path d="M9 11v8"/>';

  const ICON_SAVE = '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>';



  editBtn = makeLabeledBtn(ICON_EDIT, M.edit + ' (E)', M.editMode + ' (E)', () => toggleEditMode());

  editBtn.classList.add('mode-toggle');

  editModeLabel = document.createElement('span');

  editModeLabel.className = 'edit-mode-label edit-only';

  editModeLabel.textContent = M.editMode;

  undoBtn = makeLabeledBtn(ICON_UNDO, M.undo + ' (Ctrl+Z)', M.undoLabel + ' (Ctrl+Z)', () => {

    if (requireEditMode(M.undoLabel)) undo();

  });

  redoBtn = makeLabeledBtn(ICON_REDO, M.redo + ' (Ctrl+Y)', M.redoLabel + ' (Ctrl+Y)', () => {

    if (requireEditMode(M.redoLabel)) redo();

  });

  insertBtn = makeLabeledBtn(ICON_INSERT, M.insert, M.insertHelp, () => toggleInsertPanel());

  insertBtn.id = 'edit-insert-button';

  insertBtn.dataset.dropdownTrigger = 'true';

  insertBtn.setAttribute('aria-haspopup', 'menu');

  insertBtn.setAttribute('aria-controls', 'edit-insert-panel');

  insertBtn.setAttribute('aria-expanded', 'false');

  imageUploadBtn = makeLabeledBtn(
    ICON_IMAGE_UPLOAD,
    M.insertImageUpload,
    M.insertImageUpload + '｜' + M.insertImageHelp,
    chooseInsertImage
  );

  imageUploadBtn.id = 'edit-upload-image-button';

  imageUploadBtn.dataset.editorChrome = 'true';

  imageUploadBtn.dataset.editorAction = 'upload-image';

  imageUploadBtn.classList.add('image-upload-action');

  imageUploadBtn.style.background = 'rgba(15,118,110,.16)';

  imageUploadBtn.style.border = '1px solid rgba(15,118,110,.42)';

  imageUploadBtn.style.color = '#8BE7DE';

  appearanceBtn = makeLabeledBtn(ICON_APPEARANCE, M.presentationStyle, M.presentationStyle, () => toggleAppearancePanel());

  appearanceBtn.id = 'edit-slide-style-button';

  appearanceBtn.dataset.dropdownTrigger = 'true';

  const appearanceChevron = document.createElement('span');

  appearanceChevron.textContent = '▾';

  appearanceChevron.setAttribute('aria-hidden', 'true');

  appearanceChevron.style.cssText = 'font-size:11px;line-height:1;opacity:.72;';

  appearanceBtn.appendChild(appearanceChevron);

  appearanceBtn.setAttribute('aria-haspopup', 'dialog');

  appearanceBtn.setAttribute('aria-controls', 'edit-slide-style-panel');

  appearanceBtn.setAttribute('aria-expanded', 'false');

  exportBtn = makeSaveMenuItem(ICON_EXPORT, M.exportAs, M.exportHtml, () => {

    if (requireEditMode(M.export)) exportHtml();

  });

  exportPptxBtn = makeSaveMenuItem(ICON_PPTX, 'PPTX', M.exportPptxFull, () => {

    if (requireEditMode(M.exportPptx)) exportPptx();

  });

  saveBtn = makeLabeledBtn(ICON_SAVE, M.saveStart, M.saveStart + ' (Ctrl+S)', () => {

    if (requireEditMode(M.save)) saveToServer();

  });

  saveBtn.id = 'edit-save-button';

  saveBtn.style.borderRadius = '999px 0 0 999px';

  saveMenuToggle = document.createElement('button');

  saveMenuToggle.type = 'button';

  saveMenuToggle.id = 'edit-save-menu-toggle';

  saveMenuToggle.dataset.editorChrome = 'true';

  saveMenuToggle.dataset.dropdownTrigger = 'true';

  saveMenuToggle.setAttribute('aria-label', M.export + ' ' + M.save);

  saveMenuToggle.setAttribute('aria-haspopup', 'menu');

  saveMenuToggle.setAttribute('aria-controls', 'edit-save-menu');

  saveMenuToggle.setAttribute('aria-expanded', 'false');

  saveMenuToggle.innerHTML = '<span aria-hidden="true">▾</span>';

  saveMenuToggle.style.cssText =

    'height:32px;min-width:25px;padding:0 7px;border:0;border-left:1px solid rgba(255,255,255,.22);' +

    'background:transparent;color:inherit;border-radius:0 999px 999px 0;cursor:pointer;' +

    'display:inline-flex;align-items:center;justify-content:center;font:800 12px/1 var(--font-body);';

  saveMenuToggle.addEventListener('click', (event) => {

    event.preventDefault();

    event.stopPropagation();

    if (!saveMenuToggle.disabled) toggleSaveMenu();

  });

  saveGroup = document.createElement('span');

  saveGroup.id = 'edit-save-group';

  saveGroup.dataset.editorChrome = 'true';

  saveGroup.className = 'edit-only';

  saveGroup.style.cssText =

    'display:inline-flex;align-items:center;flex:0 0 auto;border-radius:999px;' +

    'background:rgba(34,197,94,.10);';

  saveGroup.append(saveBtn, saveMenuToggle);

  saveMenu = document.createElement('div');

  saveMenu.id = 'edit-save-menu';

  saveMenu.dataset.editorChrome = 'true';

  saveMenu.setAttribute('role', 'menu');

  saveMenu.setAttribute('aria-label', M.export + ' ' + M.save);

  saveMenu.setAttribute('aria-hidden', 'true');

  saveMenu.style.cssText =

    'position:fixed;left:0;top:0;z-index:106;display:none;min-width:172px;box-sizing:border-box;' +

    'flex-direction:column;gap:3px;padding:6px;background:rgba(255,255,255,.97);' +

    'color:#182028;border:1px solid rgba(18,24,30,.18);border-radius:10px;' +

    'box-shadow:0 14px 34px rgba(0,0,0,.26);font-family:var(--font-body);pointer-events:auto;';

  saveMenu.append(exportBtn, exportPptxBtn);

  saveMenu.addEventListener('mousedown', (event) => event.stopPropagation());

  saveMenu.addEventListener('click', (event) => event.stopPropagation());

  document.body.appendChild(saveMenu);

  document.addEventListener('mousedown', (event) => {

    if (!saveMenu || saveMenu.style.display === 'none') return;

    if (saveMenu.contains(event.target) || (saveMenuToggle && saveMenuToggle.contains(event.target))) return;

    toggleSaveMenu(false);

  }, true);

  window.addEventListener('resize', () => {

    toggleSaveMenu(false);

  });

  window.addEventListener('scroll', () => {

    toggleSaveMenu(false);

  }, true);

  actionStatus = document.createElement('span');

  actionStatus.id = 'edit-action-status';

  actionStatus.dataset.editorChrome = 'true';

  actionStatus.setAttribute('role', 'status');

  actionStatus.setAttribute('aria-live', 'polite');

  actionStatus.setAttribute('aria-hidden', 'true');

  actionStatus.style.cssText =

    'display:none;min-width:0;max-width:360px;margin-left:auto;padding:6px 10px;border-radius:7px;' +

    'background:rgba(63,208,232,.12);color:#A7F3FF;font:700 11px/1.3 var(--font-body);' +

    'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:0 1 auto;';

  [undoBtn, redoBtn, insertBtn, imageUploadBtn, appearanceBtn, saveBtn, saveMenuToggle].forEach((button) => button.classList.add('edit-only'));

  const editDivider = makeDivider();

  editDivider.classList.add('edit-only');

  barInner.append(editModeLabel, undoBtn, redoBtn, editDivider, insertBtn, imageUploadBtn, appearanceBtn, saveGroup, actionStatus, editBtn);

 setSaveButtonBindingState(SAVE_BINDING_STATE_UNBOUND);

  setAutoSaveState(isWritableDevServer() ? 'idle' : 'draft-only');

  void refreshSaveButtonBindingState();

  window.addEventListener('focus', () => { void refreshSaveButtonBindingState(); });

  document.addEventListener('visibilitychange', () => {

    if (!document.hidden) void refreshSaveButtonBindingState();

  });

  toggleEditMode(true);

  requestAnimationFrame(updateToolbarLayout);



  checkDraftOnLoad();



  window.EditMode = {

    toggle: toggleEditMode,

    export: exportHtml,

    exportPptx: exportPptx,

    buildPptxManifest: buildPptxManifest,

    undo: undo,

    redo: redo,

    deselect: deselectElement,

    save: saveToServer,

    saveToFile: saveViaFilePicker,

    group: groupSelection,

    ungroup: ungroupSelection,

    runSnapshotBatch: runSnapshotBatch,

    historyLimit: UNDO_LIMIT,

    diagnostics: operationDiagnostics,

    operationLog: () => operationDiagnostics().entries

  };

})();
