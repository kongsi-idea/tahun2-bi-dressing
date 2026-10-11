/* The Dressing Game · Tahun 2 English · Get Dressed!
   纯静态：转盘（3 秒）→ 拼颜色 → 拼衣服 → 卡比巴拉穿上。 */
(() => {
'use strict';

/* ════════════════ 数据 ════════════════ */
const COLORS = { brown: '#8B5A2B', red: '#D62828', blue: '#1E6FD9', grey: '#8E949B', black: '#2B2B2E',
                 green: '#2E9E4F', orange: '#F28C1B', pink: '#F27AB0', purple: '#7B3FBF', yellow: '#F6C90E' };
const COLOUR_WORDS = ['brown', 'red', 'blue', 'grey', 'black', 'green', 'orange', 'pink', 'purple', 'yellow'];
// 衣服类型：img = 素材名；word = 显示的词；letters = 要打的字母；file = 音档名
const TYPES = [
  { id: 'cap',      word: 'cap',      letters: 'cap',     file: 'cap' },
  { id: 'tshirt',   word: 'T-shirt',  letters: 'tshirt',  file: 't-shirt' },
  { id: 'jacket',   word: 'jacket',   letters: 'jacket',  file: 'jacket' },
  { id: 'trousers', word: 'trousers', letters: 'trousers', file: 'trousers' },
  { id: 'socks',    word: 'socks',    letters: 'socks',   file: 'socks' },
  { id: 'shoes',    word: 'shoes',    letters: 'shoes',   file: 'shoes' },
];
const TYPE = Object.fromEntries(TYPES.map(t => [t.id, t]));
// 18 件：课本转盘顺序（从 Start 顺时针），bg = 课本扇形底色
const RAW = [
  ['brown', 'cap', '#FDE047'], ['red', 'tshirt', '#93C5FD'], ['blue', 'jacket', '#F87171'],
  ['grey', 'trousers', '#C084FC'], ['black', 'socks', '#FDBA74'], ['red', 'shoes', '#86EFAC'],
  ['green', 'jacket', '#F87171'], ['orange', 'tshirt', '#FDE047'], ['pink', 'cap', '#FDBA74'],
  ['black', 'trousers', '#FDE047'], ['purple', 'socks', '#86EFAC'], ['yellow', 'shoes', '#C084FC'],
  ['grey', 'cap', '#93C5FD'], ['blue', 'tshirt', '#F472B6'], ['brown', 'jacket', '#A3E635'],
  ['blue', 'trousers', '#F87171'], ['red', 'socks', '#86EFAC'], ['green', 'shoes', '#FFEDD5'],
];
const ITEMS = RAW.map(([color, type, bg], i) => ({
  n: i + 1, color, type, bg,
  id: `${color}-${TYPE[type].file}`,          // 例：red-t-shirt（同时是音档名）
  phrase: `${color} ${TYPE[type].word}`,       // 例：red T-shirt
}));
const BY_ID = Object.fromEntries(ITEMS.map(it => [it.id, it]));
const ITEM_COUNT = 18, SET_SIZE = 6;

// 卡比巴拉身上的 7 个图层（袜子左右各一）从下到上；位置用百分比（相对卡比巴拉图）
// cx/cy = 图层中心点占卡比巴拉图宽/高的 %，w/h = 图层宽/高占其宽/高的 %，rot = 旋转角度
const LAYERS = ['socks-l', 'socks-r', 'shoes', 'trousers', 'tshirt', 'jacket', 'cap'];
const SLOTS = {
  'socks-l':  { cx: 34, cy: 84,  w: 21, h: 24 },
  'socks-r':  { cx: 66, cy: 84,  w: 21, h: 24 },
  'shoes':    { cx: 49, cy: 95,  w: 57, h: 14 },
  'trousers': { cx: 50, cy: 69,  w: 58, h: 44 },
  'tshirt':   { cx: 50, cy: 52,  w: 62, h: 33 },
  'jacket':   { cx: 50, cy: 48,  w: 96, h: 39 },
  'cap':      { cx: 49, cy: -2,  w: 40, h: 19.5, rot: 16 },
};

const SPIN_MS = 3000;
const KB_ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'];
const SAVE_KEY = 'tahun2-bi-dressing:v1';

/* ════════════════ 小工具 ════════════════ */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const REDUCED = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
const rnd = n => Math.floor(Math.random() * n);
const pickOne = a => a[rnd(a.length)];
const STAR_SVG = '<svg class="ico ico-star" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-star"/></svg>';
const starsHTML = (n, total = 3) => Array.from({ length: total }, (_, i) =>
  `<span class="st ${i < n ? 'on' : 'off'}">${STAR_SVG}</span>`).join('');

let epoch = 0;                               // 重置／换局时自增，让过期的计时器自动作废
function later(ms, fn) { const e = epoch; return setTimeout(() => { if (e === epoch) fn(); }, ms); }

/* ════════════════ 存档 ════════════════ */
function freshState() { return { collected: [], worn: {}, stars: 0, colourOK: 0, clothOK: 0, sets: 0, muted: false }; }
function loadState() {
  let s = freshState();
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (raw) {
      const o = JSON.parse(raw);
      s.collected = Array.isArray(o.collected) ? o.collected.filter(id => BY_ID[id]) : [];
      s.collected = [...new Set(s.collected)];
      s.worn = {};
      if (o.worn && typeof o.worn === 'object') for (const [t, id] of Object.entries(o.worn)) if (TYPE[t] && BY_ID[id] && BY_ID[id].type === t) s.worn[t] = id;
      for (const k of ['stars', 'colourOK', 'clothOK', 'sets']) s[k] = Math.max(0, Number(o[k]) || 0);
      s.muted = !!o.muted;
    }
  } catch (e) { /* 存档读不到就当新玩家 */ }
  // 上次关页面时正好穿满一套 → 已经存进收藏，穿着清掉
  if (Object.keys(s.worn).length >= SET_SIZE) { for (const id of Object.values(s.worn)) if (!s.collected.includes(id)) s.collected.push(id); s.worn = {}; }
  return s;
}
let S = loadState();
function save() { try { localStorage.setItem(SAVE_KEY, JSON.stringify(S)); } catch (e) { /* 存不了也不能卡住 */ } }

/* ════════════════ 图片、着色 ════════════════ */
const IMG = {};
const IMG_NAMES = ['capybara', 'cap', 'tshirt', 'jacket', 'trousers', 'socks', 'socks-l', 'socks-r', 'shoes'];
function loadImages() {
  return Promise.all(IMG_NAMES.map(n => new Promise(res => {
    const im = new Image(); im.onload = () => res(); im.onerror = () => res(); im.src = `assets/${n}.webp`; IMG[n] = im;
  })));
}
function hex2rgb(h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }

// 着色：按原图亮度保留明暗；比平均亮的地方（高光）提亮，比平均暗的地方（褶皱、描边）压暗。
// 深色（黑、深蓝、紫、棕）高光增益更大，否则褶皱会糊成一片。
const TINT_CACHE = new Map();
function tinted(imgName, colorName) {
  const key = imgName + '|' + colorName;
  if (TINT_CACHE.has(key)) return TINT_CACHE.get(key);
  const img = IMG[imgName];
  const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
  const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(img, 0, 0);
  const id = x.getImageData(0, 0, c.width, c.height), d = id.data;
  const col = hex2rgb(COLORS[colorName]);
  const lumC = (0.299 * col[0] + 0.587 * col[1] + 0.114 * col[2]) / 255;
  const dark = lumC < 0.32 ? 1 : (lumC < 0.5 ? 0.5 : 0);
  const M = 0.943, hiGain = 3 + 4 * dark;
  for (let i = 0; i < d.length; i += 4) {
    if (!d[i + 3]) continue;
    const dev = (0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]) / 255 - M;
    for (let k = 0; k < 3; k++) {
      const v = col[k];
      const o = dev < 0 ? v * Math.max(0.28, 1 + dev * 4.2) : v + (255 - v) * Math.min(1, dev * hiGain);
      d[i + k] = o < 0 ? 0 : o > 255 ? 255 : o;
    }
  }
  x.putImageData(id, 0, 0);
  TINT_CACHE.set(key, c);
  return c;
}
const URL_CACHE = new Map();
function tintedURL(imgName, colorName) {
  const key = imgName + '|' + colorName;
  if (!URL_CACHE.has(key)) URL_CACHE.set(key, tinted(imgName, colorName).toDataURL('image/png'));
  return URL_CACHE.get(key);
}
function silhouetteURL(typeId) {              // 未收集的灰色剪影
  const key = 'sil|' + typeId;
  if (!URL_CACHE.has(key)) {
    const im = IMG[typeId];
    const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
    const x = c.getContext('2d'); x.drawImage(im, 0, 0);
    x.globalCompositeOperation = 'source-in'; x.fillStyle = '#C9B79A'; x.fillRect(0, 0, c.width, c.height);
    URL_CACHE.set(key, c.toDataURL('image/png'));
  }
  return URL_CACHE.get(key);
}
function downscale(src, w, h) {                // 分步缩小，小图才不会发糊／锯齿
  let cur = src, cw = src.width, ch = src.height;
  while (cw > w * 2) {
    const nw = Math.round(cw / 2), nh = Math.round(ch / 2);
    const c = document.createElement('canvas'); c.width = nw; c.height = nh;
    const x = c.getContext('2d'); x.imageSmoothingQuality = 'high'; x.drawImage(cur, 0, 0, nw, nh);
    cur = c; cw = nw; ch = nh;
  }
  const out = document.createElement('canvas'); out.width = w; out.height = h;
  const ox = out.getContext('2d'); ox.imageSmoothingQuality = 'high'; ox.drawImage(cur, 0, 0, w, h);
  return out;
}
// 转盘上的小图：缩到 box×box 以内，外加一圈白色贴纸边
const ICON_CACHE = new Map();
function wheelIcon(item, box) {
  const key = item.id + '|' + box;
  if (ICON_CACHE.has(key)) return ICON_CACHE.get(key);
  const t = tinted(item.type, item.color);
  const k = box / Math.max(t.width, t.height);
  const w = Math.max(2, Math.round(t.width * k)), h = Math.max(2, Math.round(t.height * k));
  const small = downscale(t, w, h);
  const pad = Math.max(2, Math.round(box * 0.045));
  const c = document.createElement('canvas'); c.width = w + pad * 2; c.height = h + pad * 2;
  const x = c.getContext('2d');
  const sil = document.createElement('canvas'); sil.width = w; sil.height = h;
  const sx = sil.getContext('2d'); sx.drawImage(small, 0, 0); sx.globalCompositeOperation = 'source-in'; sx.fillStyle = '#FFFDF6'; sx.fillRect(0, 0, w, h);
  for (let a = 0; a < 16; a++) {
    const ang = a / 16 * Math.PI * 2;
    x.drawImage(sil, pad + Math.cos(ang) * pad, pad + Math.sin(ang) * pad);
  }
  x.drawImage(small, pad, pad);
  ICON_CACHE.set(key, c);
  return c;
}

/* ════════════════ 声音（预录 mp3，失败一律静默） ════════════════ */
let acted = false;                               // 首次交互后才播放（浏览器自动播放限制）
let audioEl = null, audioToken = 0;
function playOne(file, tok) {
  return new Promise(res => {
    let done = false;
    const fin = () => { if (!done) { done = true; res(); } };
    try {
      const a = new Audio(`audio/${file}.mp3`);
      audioEl = a;
      a.addEventListener('ended', fin); a.addEventListener('error', fin);
      setTimeout(fin, 4500);
      const p = a.play(); if (p && p.catch) p.catch(fin);
    } catch (e) { fin(); }
  });
}
function say(files) {
  if (!acted || S.muted) return Promise.resolve();
  const tok = ++audioToken;
  try { if (audioEl) audioEl.pause(); } catch (e) { /* ignore */ }
  const list = Array.isArray(files) ? files : [files];
  return list.reduce((p, f) => p.then(() => (tok === audioToken ? playOne(f, tok) : null)), Promise.resolve()).catch(() => {});
}
function allVoiceLines() {
  const L = [];
  for (const c of COLOUR_WORDS) L.push({ file: c, text: c });
  for (const t of TYPES) L.push({ file: t.file, text: t.word });
  for (const it of ITEMS) L.push({ file: it.id, text: it.phrase });
  L.push({ file: 'great', text: 'Great!' }, { file: 'try-again', text: 'Try again' },
         { file: 'well-done', text: 'Well done!' }, { file: 'you-collected-all-18', text: 'You collected all 18!' });
  return L;
}

/* ════════════════ 转盘（画布） ════════════════ */
const SECTORS = 20, SEC_DEG = 360 / SECTORS;
const wBase = $('#wBase'), wRot = $('#wRot'), wTop = $('#wTop');
const wrap = $('#wheelWrap');
const CX = 640, CY = 640, RR = 640;
const R_RIM_IN = 0.90 * RR, R_HUB = 0.58 * RR;

function woodGrain(x, cx, cy, r0, r1, seed) {
  let s = seed; const rand = () => (s = (s * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 70; i++) {                 // 手绘年轮：圆心微偏、半径递减
    const r = r0 + (r1 - r0) * rand();
    x.beginPath();
    x.strokeStyle = rand() > 0.5 ? 'rgba(67,40,19,0.10)' : 'rgba(255,236,200,0.10)';
    x.lineWidth = 1 + rand() * 2.5;
    const a0 = rand() * 6.28, span = 0.8 + rand() * 3.4;
    x.arc(cx + (rand() - .5) * 10, cy + (rand() - .5) * 10, r, a0, a0 + span);
    x.stroke();
  }
}
function paintNoise(x, clip, alpha, seed, n) {
  let s = seed; const rand = () => (s = (s * 16807) % 2147483647) / 2147483647;
  x.save(); clip();
  for (let i = 0; i < n; i++) {
    x.fillStyle = rand() > 0.5 ? `rgba(0,0,0,${alpha})` : `rgba(255,255,255,${alpha})`;
    x.fillRect(rand() * 1280, rand() * 1280, 2 + rand() * 3, 2 + rand() * 3);
  }
  x.restore();
}
function drawBase() {
  const x = wBase.getContext('2d');
  x.clearRect(0, 0, 1280, 1280);
  // 外圈木框（浅枫木，左上亮、右下暗）
  let g = x.createRadialGradient(CX - 200, CY - 240, 60, CX, CY, RR);
  g.addColorStop(0, '#F2D3A6'); g.addColorStop(.55, '#D9A468'); g.addColorStop(1, '#9A6532');
  x.fillStyle = g; x.beginPath(); x.arc(CX, CY, RR - 2, 0, 7); x.fill();
  woodGrain(x, CX, CY, R_RIM_IN, RR - 6, 77);
  paintNoise(x, () => { x.beginPath(); x.arc(CX, CY, RR - 2, 0, 7); x.arc(CX, CY, R_RIM_IN, 0, 7, true); x.clip('evenodd'); }, 0.035, 11, 2400);
  // 外缘细高光＋深色收边（双线）
  x.lineWidth = 5; x.strokeStyle = 'rgba(255,244,222,.65)'; x.beginPath(); x.arc(CX, CY, RR - 9, Math.PI * .95, Math.PI * 1.6); x.stroke();
  x.lineWidth = 4; x.strokeStyle = 'rgba(67,40,19,.55)'; x.beginPath(); x.arc(CX, CY, RR - 2, 0, 7); x.stroke();
  // 轮胎内沿的凹槽
  x.lineWidth = 10; x.strokeStyle = 'rgba(67,40,19,.5)'; x.beginPath(); x.arc(CX, CY, R_RIM_IN + 4, 0, 7); x.stroke();
  // 中心舞台（暖奶油地台）
  g = x.createRadialGradient(CX - 120, CY - 150, 20, CX, CY, R_HUB);
  g.addColorStop(0, '#FFFBF0'); g.addColorStop(.7, '#FDEBCB'); g.addColorStop(1, '#F1D3A1');
  x.fillStyle = g; x.beginPath(); x.arc(CX, CY, R_HUB + 4, 0, 7); x.fill();
  // 舞台地板：圆弧底下一圈淡木色，卡比巴拉像站在台上
  const fl = x.createLinearGradient(0, CY + R_HUB * .55, 0, CY + R_HUB);
  fl.addColorStop(0, 'rgba(176,120,64,0)'); fl.addColorStop(1, 'rgba(176,120,64,.38)');
  x.fillStyle = fl; x.beginPath(); x.arc(CX, CY, R_HUB + 4, 0, 7); x.fill();
  paintNoise(x, () => { x.beginPath(); x.arc(CX, CY, R_HUB, 0, 7); x.clip(); }, 0.03, 5, 1800);
}
function wedgePath(x, i, r0, r1) {
  const a0 = (-90 + i * SEC_DEG) * Math.PI / 180, a1 = (-90 + (i + 1) * SEC_DEG) * Math.PI / 180;
  x.beginPath(); x.arc(CX, CY, r1, a0, a1); x.arc(CX, CY, r0, a1, a0, true); x.closePath();
}
function drawStartIcon(x, size) {
  // 小旗：旗杆＋三角旗（装饰，不写字）
  x.save();
  x.lineCap = 'round'; x.lineJoin = 'round';
  x.strokeStyle = '#FFFDF6'; x.lineWidth = size * .16; x.beginPath(); x.moveTo(-size * .22, size * .42); x.lineTo(-size * .22, -size * .42); x.stroke();
  x.fillStyle = '#FFFDF6'; x.beginPath(); x.moveTo(-size * .22, -size * .42); x.lineTo(size * .42, -size * .18); x.lineTo(-size * .22, size * .06); x.closePath(); x.fill();
  x.strokeStyle = '#FFFDF6'; x.lineWidth = size * .09; x.stroke();
  x.fillStyle = '#E4503C'; x.beginPath(); x.moveTo(-size * .17, -size * .34); x.lineTo(size * .28, -size * .18); x.lineTo(-size * .17, -size * .02); x.closePath(); x.fill();
  x.restore();
}
function drawFinishIcon(x, size) {
  x.save();
  x.lineCap = 'round';
  x.strokeStyle = '#FFFDF6'; x.lineWidth = size * .16; x.beginPath(); x.moveTo(-size * .3, size * .42); x.lineTo(-size * .3, -size * .42); x.stroke();
  const n = 4, cs = size * .17, ox = -size * .24, oy = -size * .42;
  x.fillStyle = '#FFFDF6'; x.fillRect(ox - 3, oy - 3, cs * n + 6, cs * 3 + 6);
  for (let r = 0; r < 3; r++) for (let c = 0; c < n; c++) { x.fillStyle = (r + c) % 2 ? '#fff' : '#2B2B2E'; x.fillRect(ox + c * cs, oy + r * cs, cs, cs); }
  x.restore();
}
function drawRot() {
  const x = wRot.getContext('2d');
  x.clearRect(0, 0, 1280, 1280);
  const rIcon = (R_HUB + R_RIM_IN) / 2 + 4;
  const box = Math.round(0.215 * RR * 1.0);
  const sectorBg = i => i === 0 ? '#5CC07B' : i === SECTORS - 1 ? '#EDE3D2' : ITEMS[i - 1].bg;
  for (let i = 0; i < SECTORS; i++) {
    wedgePath(x, i, R_HUB, R_RIM_IN);
    x.fillStyle = sectorBg(i); x.fill();
    // 1–2 阶渐层：内侧提亮，外侧略暗（禁止纯色平涂）
    const g = x.createRadialGradient(CX, CY, R_HUB, CX, CY, R_RIM_IN);
    g.addColorStop(0, 'rgba(255,255,255,.26)'); g.addColorStop(.55, 'rgba(255,255,255,.04)'); g.addColorStop(1, 'rgba(60,30,10,.12)');
    x.fillStyle = g; wedgePath(x, i, R_HUB, R_RIM_IN); x.fill();
  }
  // Finish 格：黑白方格底
  x.save(); wedgePath(x, SECTORS - 1, R_HUB, R_RIM_IN); x.clip();
  const mid = (-90 + (SECTORS - 0.5) * SEC_DEG) * Math.PI / 180;
  x.translate(CX, CY); x.rotate(mid + Math.PI / 2);
  const cs = 34;
  for (let r = -2; r < 12; r++) for (let c = -4; c < 4; c++) { x.fillStyle = (r + c) & 1 ? 'rgba(43,43,46,.88)' : 'rgba(255,253,246,.95)'; x.fillRect(c * cs, -(R_RIM_IN) + r * cs, cs, cs); }
  x.restore();
  // 分隔线：深线＋亮线双线
  for (let i = 0; i < SECTORS; i++) {
    const a = (-90 + i * SEC_DEG) * Math.PI / 180, ca = Math.cos(a), sa = Math.sin(a);
    x.lineCap = 'round';
    x.strokeStyle = 'rgba(67,40,19,.55)'; x.lineWidth = 6;
    x.beginPath(); x.moveTo(CX + ca * R_HUB, CY + sa * R_HUB); x.lineTo(CX + ca * R_RIM_IN, CY + sa * R_RIM_IN); x.stroke();
    x.strokeStyle = 'rgba(255,247,230,.85)'; x.lineWidth = 2.6;
    x.beginPath(); x.moveTo(CX + ca * R_HUB, CY + sa * R_HUB); x.lineTo(CX + ca * R_RIM_IN, CY + sa * R_RIM_IN); x.stroke();
  }
  // 图标（沿半径方向，朝外为上）
  for (let i = 0; i < SECTORS; i++) {
    const ang = (i + 0.5) * SEC_DEG * Math.PI / 180;
    const px = CX + Math.sin(ang) * rIcon, py = CY - Math.cos(ang) * rIcon;
    x.save(); x.translate(px, py); x.rotate(ang);
    if (i === 0) drawStartIcon(x, box * 1.05);
    else if (i === SECTORS - 1) drawFinishIcon(x, box * 1.05);
    else {
      const ic = wheelIcon(ITEMS[i - 1], box);
      x.shadowColor = 'rgba(67,40,19,.32)'; x.shadowBlur = 9; x.shadowOffsetY = 3;
      x.drawImage(ic, -ic.width / 2, -ic.height / 2);
    }
    x.restore();
  }
  // 外圈黄铜钉（每个分隔线一颗）
  for (let i = 0; i < SECTORS; i++) {
    const a = (-90 + i * SEC_DEG) * Math.PI / 180, r = (R_RIM_IN + RR) / 2 + 2;
    const px = CX + Math.cos(a) * r, py = CY + Math.sin(a) * r;
    x.fillStyle = 'rgba(40,20,5,.38)'; x.beginPath(); x.arc(px + 3, py + 4, 17, 0, 7); x.fill();
    const g = x.createRadialGradient(px - 5, py - 6, 2, px, py, 18);
    g.addColorStop(0, '#FFF3C2'); g.addColorStop(.5, '#E8B23D'); g.addColorStop(1, '#A5731F');
    x.fillStyle = g; x.beginPath(); x.arc(px, py, 16, 0, 7); x.fill();
    x.strokeStyle = 'rgba(100,60,10,.6)'; x.lineWidth = 2; x.stroke();
  }
}
function drawTop() {
  const x = wTop.getContext('2d');
  x.clearRect(0, 0, 1280, 1280);
  // 凹陷感：转盘与外框、与中心台交界处叠一圈模糊深色（环境光遮蔽）
  let g = x.createRadialGradient(CX, CY, R_RIM_IN - 36, CX, CY, R_RIM_IN + 2);
  g.addColorStop(0, 'rgba(67,40,19,0)'); g.addColorStop(1, 'rgba(67,40,19,.45)');
  x.fillStyle = g; x.beginPath(); x.arc(CX, CY, R_RIM_IN + 2, 0, 7); x.arc(CX, CY, R_HUB, 0, 7, true); x.fill('evenodd');
  g = x.createRadialGradient(CX, CY, R_HUB, CX, CY, R_HUB + 34);
  g.addColorStop(0, 'rgba(67,40,19,.5)'); g.addColorStop(1, 'rgba(67,40,19,0)');
  x.fillStyle = g; x.beginPath(); x.arc(CX, CY, R_HUB + 34, 0, 7); x.arc(CX, CY, R_HUB, 0, 7, true); x.fill('evenodd');
  // 中心台边缘：左上高光＋右下暗边
  x.lineWidth = 8; x.strokeStyle = 'rgba(255,248,230,.8)'; x.beginPath(); x.arc(CX, CY, R_HUB - 3, Math.PI * .95, Math.PI * 1.55); x.stroke();
  x.lineWidth = 8; x.strokeStyle = 'rgba(120,72,30,.45)'; x.beginPath(); x.arc(CX, CY, R_HUB - 3, Math.PI * -0.05, Math.PI * .55); x.stroke();
  // 玻璃般的整体高光（左上）
  g = x.createRadialGradient(CX - 260, CY - 300, 20, CX - 200, CY - 240, 520);
  g.addColorStop(0, 'rgba(255,255,255,.20)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g; x.beginPath(); x.arc(CX, CY, R_RIM_IN, 0, 7); x.arc(CX, CY, R_HUB, 0, 7, true); x.fill('evenodd');
}

let wheelRot = 0, spinning = false;
function setWheelRot(deg) { wheelRot = deg; wRot.style.transform = `rotate(${deg}deg)`; }
let lastSpinMs = 0;
function spinTo(item, done) {
  const idx = item.n;                                     // 扇形序号：Start = 0，物品 1..18，Finish = 19
  const jitter = (Math.random() - 0.5) * (SEC_DEG * 0.56);
  const target = (((-(idx + 0.5) * SEC_DEG - jitter) % 360) + 360) % 360;   // 要停在的角度（模 360）
  const cur = ((wheelRot % 360) + 360) % 360;
  const delta = 360 * 4 + ((target - cur + 360) % 360);              // 4–5 圈
  const start = wheelRot, t0 = performance.now();
  spinning = true; wrap.dataset.spinning = '1';
  const step = now => {
    const p = Math.min(1, (now - t0) / SPIN_MS);
    const e = 1 - Math.pow(1 - p, 3.4);                   // ease-out：先快后慢，最后一格慢慢停
    setWheelRot(start + delta * e);
    if (p < 1) { requestAnimationFrame(step); return; }
    spinning = false; delete wrap.dataset.spinning;
    lastSpinMs = performance.now() - t0;
    wrap.dataset.lastSpinMs = String(Math.round(lastSpinMs));
    done();
  };
  requestAnimationFrame(step);
}

/* ════════════════ 卡比巴拉穿衣 ════════════════ */
const capy = $('#capy');
const layerEls = Object.fromEntries(LAYERS.map(L => [L, $(`[data-layer="${L}"]`)]));
function placeLayers() {
  for (const L of LAYERS) {
    const s = SLOTS[L], el = layerEls[L];
    el.style.left = s.cx + '%'; el.style.top = s.cy + '%';
    el.style.width = s.w + '%'; el.style.height = s.h + '%';
    el.style.setProperty('--rot', (s.rot || 0) + 'deg');
  }
}
function renderDress(animate) {
  for (const L of LAYERS) {
    const type = L.replace(/-[lr]$/, ''), id = S.worn[type], el = layerEls[L];
    if (id) {
      const it = BY_ID[id];
      if (el.hidden || el.dataset.id !== id) {
        el.src = tintedURL(L, it.color); el.dataset.id = id; el.hidden = false; el.classList.remove('off');
        if (animate && !REDUCED) { el.classList.remove('pop'); void el.offsetWidth; el.classList.add('pop'); }
      }
    } else if (!el.hidden) {
      if (animate && !REDUCED) { el.classList.add('off'); const e = epoch; setTimeout(() => { if (!S.worn[type]) { el.hidden = true; el.classList.remove('off', 'pop'); delete el.dataset.id; } }, 460); }
      else { el.hidden = true; el.classList.remove('off', 'pop'); delete el.dataset.id; }
    }
  }
}

/* ════════════════ 顶栏、这套的小格子、收藏 ════════════════ */
function wornCount() { return Object.keys(S.worn).length; }
function renderHeader() {
  $('#starTotal').textContent = S.stars;
  $('#wornCount').textContent = `${wornCount()}/${SET_SIZE}`;
  $('#colCount').textContent = `${S.collected.length}/${ITEM_COUNT}`;
  $('#setDots').innerHTML = TYPES.map(t => `<i class="${S.worn[t.id] ? 'on' : ''}"></i>`).join('');
  $('#okColour').textContent = S.colourOK; $('#okCloth').textContent = S.clothOK;
  $('#idleHint').textContent = wornCount() === 0 ? `Set ${S.sets + 1}: spin the wheel!` : 'Spin again!';
  const snd = $('#btnSound');
  snd.setAttribute('aria-pressed', String(S.muted));
  snd.setAttribute('aria-label', S.muted ? 'Sound off' : 'Sound on');
  snd.querySelector('use').setAttribute('href', S.muted ? '#i-mute' : '#i-speaker');
  renderStrip();
}
function renderStrip() {
  $('#strip').innerHTML = TYPES.map(t => {
    const id = S.worn[t.id];
    const src = id ? tintedURL(t.id, BY_ID[id].color) : silhouetteURL(t.id);
    return `<div class="slot ${id ? 'got' : ''}" data-type="${t.id}"><img src="${src}" alt="${id ? BY_ID[id].phrase : t.word + ' not yet'}" draggable="false">${id ? `<svg class="tick" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-check"/></svg>` : ''}</div>`;
  }).join('');
}
function renderCollection() {
  const sub = `${S.collected.length} of ${ITEM_COUNT}`;
  $('#colSub').textContent = sub;
  const cols = TYPES.map(t => ITEMS.filter(it => it.type === t.id));
  let html = '';
  for (let r = 0; r < 3; r++) for (let c = 0; c < TYPES.length; c++) {
    const it = cols[c][r], got = S.collected.includes(it.id);
    html += got
      ? `<button type="button" class="tile got" data-id="${it.id}" style="--tile:${it.bg}" aria-label="${it.phrase}, listen"><img src="${tintedURL(it.type, it.color)}" alt="" draggable="false"><span class="cap">${it.phrase}</span></button>`
      : `<div class="tile lock" aria-label="Not collected yet"><img src="${silhouetteURL(it.type)}" alt="" draggable="false"><span class="q">?</span></div>`;
  }
  $('#shelf').innerHTML = html;
}

/* ════════════════ 流程 ════════════════ */
let phase = 'idle';                 // idle | spinning | answer | done | celebrate | final
function setPhase(p) { phase = p; document.body.dataset.phase = p; }
let forcedId = null;
let round = null;                   // 当前这一件

function showView(name) {
  $('#viewIdle').hidden = name !== 'idle';
  $('#viewAnswer').hidden = name !== 'answer';
  $('#viewDone').hidden = name !== 'done';
}
function setScreen(v) {
  document.body.dataset.view = v;
  if (v === 'collection') renderCollection();
  $('#btnPlay').setAttribute('aria-current', v === 'play' ? 'page' : 'false');
  $('#btnCollection').setAttribute('aria-current', v === 'collection' ? 'page' : 'false');
}

function pickItem() {
  if (forcedId) { const it = BY_ID[forcedId]; forcedId = null; if (it) return it; }
  const wornTypes = new Set(Object.keys(S.worn));
  const cands = ITEMS.filter(it => !wornTypes.has(it.type));      // 只抽这套还没穿的类型
  const fresh = cands.filter(it => !S.collected.includes(it.id)); // 优先没收集过的
  return pickOne(fresh.length ? fresh : cands);
}

function spin() {
  if (phase !== 'idle' || document.body.dataset.view !== 'play') return;
  acted = true;
  const item = pickItem();
  setPhase('spinning');
  spinTo(item, () => {
    wrap.classList.remove('thump'); void wrap.offsetWidth; wrap.classList.add('thump');
    later(480, () => startRound(item));
  });
}

function makeWord(text, letters, upperFirst) {
  const cells = [];
  let li = 0;
  for (const ch of text) {
    if (ch === '-') cells.push({ fixed: true, ch: '-', val: '', want: '', state: 'fixed' });
    else { cells.push({ fixed: false, want: letters[li], val: '', state: '', upper: upperFirst && li === 0 }); li++; }
  }
  return { text, cells, help: 0, errors: 0 };
}
function startRound(item) {
  const t = TYPE[item.type];
  round = {
    item, stage: 'colour', busy: false, helps: 0, errors: 0,
    colour: makeWord(item.color, item.color, false),
    cloth: makeWord(t.word, t.letters, t.word[0] === 'T'),
  };
  // 答题面板：大图（带颜色）+ 喇叭
  const pic = $('#itemPic'), px = pic.getContext('2d');
  px.clearRect(0, 0, pic.width, pic.height);
  const tc = tinted(item.type, item.color);
  const k = Math.min(pic.width * 0.92 / tc.width, pic.height * 0.92 / tc.height);
  const sm = downscale(tc, Math.round(tc.width * k), Math.round(tc.height * k));
  px.drawImage(sm, (pic.width - sm.width) / 2, (pic.height - sm.height) / 2);
  $('#itemTag').style.setProperty('--tag', item.bg);
  $('#msg').textContent = ''; $('#msg').className = 'msg';
  renderAsk();
  showView('answer'); setPhase('answer');
  say(item.id);
  // 手机直立：面板比屏幕高时，只滚到刚好看见键盘，转盘留在上方
  requestAnimationFrame(() => { const r = $('#panel').getBoundingClientRect(); if (r.bottom > innerHeight - 4) window.scrollBy({ top: r.bottom - innerHeight + 12, behavior: REDUCED ? 'auto' : 'smooth' }); });
}
function curWord() { return round.stage === 'colour' ? round.colour : round.cloth; }
function stars() { const pen = round.helps + round.errors; return pen === 0 ? 3 : pen <= 2 ? 2 : 1; }

function renderWord(W, el, active) {
  const firstEmpty = active ? W.cells.findIndex(c => !c.fixed && c.state !== 'locked' && !c.val) : -1;
  el.innerHTML = W.cells.map((c, i) => {
    if (c.fixed) return `<span class="cell fixed" aria-hidden="true">-</span>`;
    const txt = c.val ? (c.upper ? c.val.toUpperCase() : c.val) : '';
    const cls = ['cell', c.state, i === firstEmpty ? 'next' : '', c.bounce ? 'bounce' : ''].filter(Boolean).join(' ');
    return `<span class="${cls}" data-i="${i}" data-ch="${c.val}" style="--d:${i * 70}ms">${txt}</span>`;
  }).join('');
}
function renderAsk() {
  const R = round;
  renderWord(R.colour, $('#cellsColour'), R.stage === 'colour');
  renderWord(R.cloth, $('#cellsCloth'), R.stage === 'cloth');
  $('#rowColour').classList.toggle('active', R.stage === 'colour');
  $('#rowCloth').classList.toggle('active', R.stage === 'cloth');
  $('#rowColour').classList.toggle('done', R.colour.cells.every(c => c.fixed || c.state === 'locked'));
  $('#stepLine').innerHTML = R.stage === 'colour' ? 'Spell the <b>colour</b>' : 'Now spell the <b>clothes</b>';
  $('#itemStars').innerHTML = starsHTML(stars());
  const W = curWord();
  const lbl = ['Hear it', 'First letter', 'Peek', 'That is all'][W.help];
  $('#helpLbl').textContent = 'Help · ' + lbl;
  $$('#helpPips i').forEach((p, i) => p.classList.toggle('on', i < W.help));
  $('#btnHelp').disabled = W.help >= 3 || R.busy;
}

function typeLetter(ch) {
  if (phase !== 'answer' || !round || round.busy) return;
  const W = curWord();
  const c = W.cells.find(x => !x.fixed && x.state !== 'locked' && !x.val);
  if (!c) return;
  c.val = ch;
  renderAsk();
  checkWord();
}
function backspace() {
  if (phase !== 'answer' || !round || round.busy) return;
  const W = curWord();
  for (let i = W.cells.length - 1; i >= 0; i--) {
    const c = W.cells[i];
    if (!c.fixed && c.state !== 'locked' && c.val) { c.val = ''; break; }
  }
  renderAsk();
}
function checkWord() {
  const W = curWord();
  const open = W.cells.filter(c => !c.fixed && c.state !== 'locked');
  if (open.some(c => !c.val)) return;               // 还没打满
  let bad = 0;
  for (const c of open) { if (c.val === c.want) c.state = 'locked'; else { c.state = 'wrong'; bad++; } }
  if (bad) {
    W.errors += bad; round.errors += bad; round.busy = true;
    renderAsk();
    const msg = $('#msg'); msg.textContent = 'Try again'; msg.className = 'msg try';
    say('try-again');
    later(560, () => {
      for (const c of W.cells) if (c.state === 'wrong') { c.state = ''; c.val = ''; }
      round.busy = false; renderAsk();
    });
    return;
  }
  wordDone();
}
function wordDone() {
  const W = curWord();
  round.busy = true;
  W.cells.forEach(c => { if (!c.fixed) c.bounce = true; });
  renderAsk();
  $('#msg').textContent = ''; $('#msg').className = 'msg';
  if (round.stage === 'colour') {
    say(round.item.color);
    later(950, () => {
      W.cells.forEach(c => { c.bounce = false; });
      round.stage = 'cloth'; round.busy = false;
      $('#msg').textContent = 'Great!'; $('#msg').className = 'msg ok';
      renderAsk();
    });
  } else {
    say(TYPE[round.item.type].file);
    later(950, finishItem);
  }
}

function helpClick() {
  if (phase !== 'answer' || !round || round.busy) return;
  const W = curWord();
  if (W.help >= 3) return;
  W.help++; round.helps++;
  const el = round.stage === 'colour' ? 'Colour' : 'Cloth';
  if (W.help === 1) {
    say(round.stage === 'colour' ? round.item.color : TYPE[round.item.type].file);
  } else if (W.help === 2) {
    const c = W.cells.find(x => !x.fixed && x.state !== 'locked');
    if (c) { c.val = c.want; c.state = 'locked hint'; }
    renderAsk(); checkWord();
    return;
  } else {
    const peek = $('#peek' + el);
    peek.textContent = W.text; peek.classList.add('show');
    const e = epoch;
    setTimeout(() => { peek.classList.remove('show'); }, 3000);
  }
  renderAsk();
}

function finishItem() {
  const R = round, it = R.item;
  const earned = stars();
  S.stars += earned;
  if (R.colour.errors === 0 && R.colour.help === 0) S.colourOK++;
  if (R.cloth.errors === 0 && R.cloth.help === 0) S.clothOK++;
  S.worn[it.type] = it.id;
  save();
  renderDress(true); renderHeader();
  // 完成卡
  setPhase('done'); showView('done');
  $('#doneTitle').textContent = 'Great!';
  $('#donePic').innerHTML = `<img src="${tintedURL(it.type, it.color)}" alt="" draggable="false">`;
  $('#donePic').style.setProperty('--tag', it.bg);
  $('#doneStars').innerHTML = starsHTML(earned);
  $('#btnNextSet').hidden = true;
  say([it.id, 'great']);
  round = null;
  later(1900, () => { wornCount() >= SET_SIZE ? setComplete() : backToIdle(); });
}
function backToIdle() { setPhase('idle'); showView('idle'); renderHeader(); if (window.scrollY > 0) window.scrollTo({ top: 0, behavior: REDUCED ? 'auto' : 'smooth' }); }

function setComplete() {
  const items = Object.values(S.worn);
  for (const id of items) if (!S.collected.includes(id)) S.collected.push(id);
  S.sets++; save(); renderHeader();
  if (S.collected.length >= ITEM_COUNT) { showFinale(); return; }
  setPhase('celebrate'); showView('done');
  $('#doneTitle').textContent = 'Well done!';
  $('#donePic').innerHTML = items.map(id => `<img src="${tintedURL(BY_ID[id].type, BY_ID[id].color)}" alt="" draggable="false">`).join('');
  $('#donePic').classList.add('set');
  $('#doneStars').innerHTML = `<span class="saved">Set ${S.sets} is in your Collection</span>`;
  $('#btnNextSet').hidden = false;
  capy.classList.add('dance');
  confetti(3400);
  say('well-done');
  later(3800, nextSet);
}
function nextSet() {
  if (phase !== 'celebrate') return;
  epoch++;                                         // 取消还在排队的 later(nextSet)
  capy.classList.remove('dance');
  S.worn = {}; save();
  renderDress(true);
  $('#donePic').classList.remove('set');
  backToIdle();
}

function showFinale() {
  setPhase('final'); showView('idle');
  $('#finaleStars').textContent = S.stars;
  $('#finaleGrid').innerHTML = ITEMS.map(it => `<img src="${tintedURL(it.type, it.color)}" alt="${it.phrase}" style="--tile:${it.bg}" draggable="false">`).join('');
  $('#finale').hidden = false;
  capy.classList.add('dance');
  confetti(5200);
  say('you-collected-all-18');
}
function playAgain() {
  epoch++;
  $('#finale').hidden = true; capy.classList.remove('dance');
  const muted = S.muted;
  S = freshState(); S.muted = muted; save();
  renderDress(true); renderHeader(); renderCollection();
  round = null; setScreen('play'); backToIdle();
}
function doReset() {
  epoch++;
  $('#confirm').hidden = true; $('#finale').hidden = true; capy.classList.remove('dance');
  const muted = S.muted;
  S = freshState(); S.muted = muted; save();
  round = null; audioToken++;
  try { if (audioEl) audioEl.pause(); } catch (e) { /* ignore */ }
  renderDress(false); renderHeader(); renderCollection();
  setScreen('play'); showView('idle'); setPhase('idle');
}

/* ════════════════ 彩带 ════════════════ */
const cfCanvas = $('#confetti');
let cfRun = 0;
function confetti(ms) {
  if (REDUCED) return;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const W = cfCanvas.width = innerWidth * dpr, H = cfCanvas.height = innerHeight * dpr;
  const x = cfCanvas.getContext('2d');
  const pal = ['#E4503C', '#F5B52B', '#1C9C93', '#7B3FBF', '#2E86DE', '#F27AB0', '#4CAF60'];
  const ps = Array.from({ length: 150 }, () => ({
    x: Math.random() * W, y: -Math.random() * H * 0.6, vx: (Math.random() - .5) * 3 * dpr, vy: (2 + Math.random() * 4) * dpr,
    w: (7 + Math.random() * 9) * dpr, h: (4 + Math.random() * 6) * dpr, r: Math.random() * 6.28, vr: (Math.random() - .5) * .3,
    c: pickOne(pal),
  }));
  const id = ++cfRun, t0 = performance.now();
  const step = now => {
    if (id !== cfRun) return;
    x.clearRect(0, 0, W, H);
    const age = now - t0;
    let alive = 0;
    for (const p of ps) {
      p.x += p.vx; p.y += p.vy; p.vy += 0.04 * dpr; p.r += p.vr;
      if (p.y < H + 30 && age < ms + 2500) alive++;
      x.save(); x.translate(p.x, p.y); x.rotate(p.r); x.fillStyle = p.c; x.globalAlpha = Math.max(0, Math.min(1, 1 - (age - ms) / 2000));
      x.fillRect(-p.w / 2, -p.h / 2, p.w, p.h); x.restore();
    }
    if (alive && age < ms + 2500) requestAnimationFrame(step); else x.clearRect(0, 0, W, H);
  };
  requestAnimationFrame(step);
}

/* ════════════════ 屏幕键盘 + 事件 ════════════════ */
function buildKeyboard() {
  const kb = $('#kb');
  kb.innerHTML = KB_ROWS.map((row, ri) => `<div class="kb-row r${ri}">${[...row].map(k => `<button type="button" class="key" data-k="${k}" aria-label="${k}">${k.toUpperCase()}</button>`).join('')}${ri === 2 ? '<button type="button" class="key key-del" data-k="Backspace" aria-label="Delete"><svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-bksp"/></svg></button>' : ''}</div>`).join('');
  kb.addEventListener('pointerdown', e => { if (e.target.closest('.key')) e.preventDefault(); });   // 不抢焦点
  kb.addEventListener('click', e => {
    const b = e.target.closest('.key'); if (!b) return;
    acted = true;
    const k = b.dataset.k;
    if (k === 'Backspace') backspace(); else typeLetter(k);
  });
}
function flashKey(k) {
  const b = $(`.key[data-k="${k}"]`); if (!b) return;
  b.classList.add('lit'); setTimeout(() => b.classList.remove('lit'), 220);
}
document.addEventListener('keydown', e => {
  acted = true;
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (!$('#confirm').hidden || !$('#finale').hidden) return;
  if (document.body.dataset.view !== 'play') return;
  if (e.key === ' ' || e.code === 'Space') {
    const ae = document.activeElement;
    if (phase === 'idle' && (!ae || ae === document.body || ae.id === 'btnSpin')) { e.preventDefault(); spin(); }
    return;
  }
  if (phase !== 'answer') return;
  if (e.key === 'Backspace') { e.preventDefault(); flashKey('Backspace'); backspace(); return; }
  if (/^[a-zA-Z]$/.test(e.key)) { e.preventDefault(); const k = e.key.toLowerCase(); flashKey(k); typeLetter(k); }
});
document.addEventListener('pointerdown', () => { acted = true; }, { capture: true });

$('#btnSpin').addEventListener('click', spin);
$('#btnSay').addEventListener('click', () => { acted = true; if (round) say(round.item.id); });
$('#btnHelp').addEventListener('click', () => { acted = true; helpClick(); });
$('#btnPlay').addEventListener('click', () => setScreen('play'));
$('#btnCollection').addEventListener('click', () => setScreen('collection'));
$('#btnNextSet').addEventListener('click', nextSet);
$('#btnSound').addEventListener('click', () => { S.muted = !S.muted; if (S.muted) { audioToken++; try { if (audioEl) audioEl.pause(); } catch (e) { /* ignore */ } } save(); renderHeader(); });
$('#btnReset').addEventListener('click', () => { $('#confirm').hidden = false; $('#btnConfirmNo').focus(); });
$('#btnConfirmNo').addEventListener('click', () => { $('#confirm').hidden = true; });
$('#btnConfirmYes').addEventListener('click', doReset);
$('#btnAgain').addEventListener('click', playAgain);
$('#btnSeeCol').addEventListener('click', () => { $('#finale').hidden = true; setScreen('collection'); });
$('#shelf').addEventListener('click', e => {
  const t = e.target.closest('.tile.got'); if (!t) return;
  acted = true; say(t.dataset.id);
  t.classList.remove('bump'); void t.offsetWidth; t.classList.add('bump');
});

/* ════════════════ 启动 ════════════════ */
async function init() {
  buildKeyboard();
  placeLayers();
  drawBase();
  await loadImages();
  drawRot(); drawTop();
  setWheelRot(0);
  renderDress(false);
  renderHeader(); renderCollection();
  setScreen('play'); showView('idle'); setPhase('idle');
  if (S.collected.length >= ITEM_COUNT) showFinale();
  document.body.dataset.ready = '1';
}

window.__dressing = {
  forceNext(id) { const it = typeof id === 'number' ? ITEMS[id - 1] : (BY_ID[id] || ITEMS.find(x => x.phrase.toLowerCase() === String(id).toLowerCase() || x.id === String(id).replace(/\s+/g, '-').toLowerCase())); if (!it) throw new Error('unknown item ' + id); forcedId = it.id; return it.id; },
  state() { return { collected: [...S.collected], worn: { ...S.worn }, wornCount: wornCount(), stars: S.stars, colourOK: S.colourOK, clothOK: S.clothOK, sets: S.sets, phase, muted: S.muted, current: round ? round.item.id : null, stage: round ? round.stage : null }; },
  allVoiceLines,
  items: ITEMS,
  lastSpinMs: () => lastSpinMs,
  tinted, wheelIcon,
  skipCelebration: nextSet,
  debugWear(map) { S.worn = { ...map }; renderDress(false); renderHeader(); },   // 只给截图／调位置用
};

init();
})();
