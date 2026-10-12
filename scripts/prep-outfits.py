"""把 cx 生成的 3 张「卡比巴拉穿整套」白底原图 → assets/outfit-1/2/3.webp（透明底、裁边、缩到 620 宽）。
原图在 assets/src/outfits/；文件序号≠套号（生成顺序是 1、3、2），所以按内容映射：
  套1 brown cap…→ -1.png；套2 pink cap…→ -3.png；套3 grey cap…→ -2.png
用法：python3 scripts/prep-outfits.py
"""
import base64, os
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, 'assets', 'src', 'outfits')
MAP = {1: 'outfit-20261013-031600-1.png', 2: 'outfit-20261013-031600-3.png', 3: 'outfit-20261013-031600-2.png'}
JS = r"""
async ({b64, width}) => {
  const im = new Image(); im.src = 'data:image/png;base64,' + b64; await im.decode();
  const W = im.width, H = im.height;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d', {willReadFrequently: true}); x.drawImage(im, 0, 0);
  const id = x.getImageData(0, 0, W, H), d = id.data;
  const bg = new Uint8Array(W * H), q = [];
  const isBg = p => Math.min(d[p*4], d[p*4+1], d[p*4+2]) > 236;
  const push = p => { if (!bg[p] && isBg(p)) { bg[p] = 1; q.push(p); } };
  for (let i = 0; i < W; i++) { push(i); push((H-1)*W + i); }
  for (let j = 0; j < H; j++) { push(j*W); push(j*W + W-1); }
  while (q.length) { const p = q.pop(), px = p % W, py = (p / W) | 0;
    if (px > 0) push(p-1); if (px < W-1) push(p+1); if (py > 0) push(p-W); if (py < H-1) push(p+W); }
  // 边缘光晕：贴着背景、仍偏亮的像素半透明，避免白边
  let minX = W, minY = H, maxX = 0, maxY = 0;
  for (let p = 0; p < W*H; p++) {
    if (bg[p]) { d[p*4+3] = 0; continue; }
    const px = p % W, py = (p / W) | 0;
    let near = false;
    for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1]]) { const nx = px+dx, ny = py+dy; if (nx>=0&&nx<W&&ny>=0&&ny<H&&bg[ny*W+nx]) { near = true; break; } }
    if (near) { const m = Math.min(d[p*4], d[p*4+1], d[p*4+2]); if (m > 205) d[p*4+3] = Math.max(0, 255 - (m - 205) * 5); }
    if (d[p*4+3] > 20) { if (px<minX) minX=px; if (px>maxX) maxX=px; if (py<minY) minY=py; if (py>maxY) maxY=py; }
  }
  x.putImageData(id, 0, 0);
  const cw = maxX-minX+1, ch = maxY-minY+1, k = width / cw;
  const o = document.createElement('canvas'); o.width = width; o.height = Math.round(ch * k);
  const ox = o.getContext('2d'); ox.imageSmoothingQuality = 'high'; ox.drawImage(c, minX, minY, cw, ch, 0, 0, o.width, o.height);
  const blob = await new Promise(r => o.toBlob(r, 'image/webp', 0.9));
  const buf = new Uint8Array(await blob.arrayBuffer()); let s = ''; for (const b of buf) s += String.fromCharCode(b);
  return {b64: btoa(s), w: o.width, h: o.height};
}
"""
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(); pg.goto('about:blank')
    for n, f in MAP.items():
        b64 = base64.b64encode(open(os.path.join(SRC, f), 'rb').read()).decode()
        r = pg.evaluate(JS, {'b64': b64, 'width': 620})
        out = os.path.join(HERE, 'assets', f'outfit-{n}.webp')
        open(out, 'wb').write(base64.b64decode(r['b64']))
        print(out, r['w'], 'x', r['h'], os.path.getsize(out) // 1024, 'KB')
    br.close()
