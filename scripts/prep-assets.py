"""素材预处理（可重跑）：assets/src/*.png（白底原图）→ assets/*.webp（透明底、裁边、缩放）。

做法：本机没有 PIL／ImageMagick，所以开 Playwright 浏览器，用 canvas 处理：
  1. 从四边做洪水填充，去掉白底（衣服内部的白色因为被描边围住，不会被填到）
  2. 把贴着背景的近白色「光晕」再吃掉 2 像素，避免白边
  3. 夹克：把敞开的内里（拉链之间的灰色里布）也挖空，让里面的 T 恤露出来
  4. 袜子：原图是一对，另外拆成左右两只（socks-l / socks-r），穿在卡比巴拉两条腿上
  5. 裁掉多余边、等比缩放、导出 webp（带 alpha）

用法：python3 scripts/prep-assets.py            （输出 assets/*.webp）
      python3 scripts/prep-assets.py --check    （另存一张深色底检查图到 .playwright-output/prep-check.png）
"""
import base64, functools, http.server, json, os, sys, threading
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'assets')
CHECK = '--check' in sys.argv

# 名称 -> 最大边长（像素）
# 每件的去底参数：洪水阈值 T、光晕吃几圈 passes、光晕最低亮度 fringeMin
PARAMS = {'capybara': (224, 4, 212), 'shoes': (250, 9, 214)}
DEFAULT_PARAMS = (250, 2, 225)
TARGET = {'capybara': 1000, 'cap': 560, 'tshirt': 560, 'jacket': 640, 'trousers': 560, 'socks': 560, 'shoes': 560}

JS = r"""
async ({name, maxSide, hollowJacket, splitSocks, T, passes, fringeMin}) => {
  const im = new Image(); im.src = '/assets/src/' + name + '.png'; await im.decode();
  const W = im.width, H = im.height;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d', {willReadFrequently: true}); x.drawImage(im, 0, 0);
  const img = x.getImageData(0, 0, W, H), d = img.data;
  const N = W * H;
  const minc = i => Math.min(d[i*4], d[i*4+1], d[i*4+2]);
  // 1. 洪水填充背景（4 邻域，min(r,g,b) >= 250）
  const bg = new Uint8Array(N); const stack = [];
  const push = i => { if (!bg[i] && minc(i) >= T) { bg[i] = 1; stack.push(i); } };
  for (let a = 0; a < W; a++) { push(a); push((H-1)*W + a); }
  for (let b = 0; b < H; b++) { push(b*W); push(b*W + W-1); }
  while (stack.length) {
    const i = stack.pop(), px = i % W, py = (i / W) | 0;
    if (px > 0) push(i-1); if (px < W-1) push(i+1); if (py > 0) push(i-W); if (py < H-1) push(i+W);
  }
  // 2. 吃掉贴着背景的近白光晕 2 圈
  for (let pass = 0; pass < passes; pass++) {
    const mark = [];
    for (let i = 0; i < N; i++) {
      if (bg[i] || minc(i) < fringeMin) continue;
      const px = i % W, py = (i / W) | 0;
      if ((px > 0 && bg[i-1]) || (px < W-1 && bg[i+1]) || (py > 0 && bg[i-W]) || (py < H-1 && bg[i+W])) mark.push(i);
    }
    for (const i of mark) bg[i] = 1;
  }
  // 3. 夹克内里：从拉链之间的灰色种子点填充（容差小，被拉链线挡住）
  const hole = new Uint8Array(N);
  if (hollowJacket) {
    const seeds = [[650, 420], [655, 300], [640, 560]];
    const lum = i => (d[i*4] + d[i*4+1] + d[i*4+2]) / 3;
    const s0 = lum(seeds[0][1]*W + seeds[0][0]);
    const st = [];
    for (const [sx, sy] of seeds) { const i = sy*W + sx; if (Math.abs(lum(i) - s0) < 22 && !hole[i]) { hole[i] = 1; st.push(i); } }
    while (st.length) {
      const i = st.pop(), px = i % W, py = (i / W) | 0;
      for (const j of [px > 0 ? i-1 : -1, px < W-1 ? i+1 : -1, py > 0 ? i-W : -1, py < H-1 ? i+W : -1]) {
        if (j < 0 || hole[j] || bg[j]) continue;
        if (Math.abs(lum(j) - s0) < 22 && minc(j) < 247) { hole[j] = 1; st.push(j); }
      }
    }
    // 向内收 2 像素，留下拉链边
    for (let pass = 0; pass < 2; pass++) {
      const rm = [];
      for (let i = 0; i < N; i++) if (hole[i]) {
        const px = i % W, py = (i / W) | 0;
        if ((px > 0 && !hole[i-1]) || (px < W-1 && !hole[i+1]) || (py > 0 && !hole[i-W]) || (py < H-1 && !hole[i+W])) rm.push(i);
      }
      for (const i of rm) hole[i] = 0;
    }
  }
  let holeCount = 0;
  for (let i = 0; i < N; i++) { if (hole[i]) holeCount++; d[i*4+3] = (bg[i] || hole[i]) ? 0 : 255; }
  // 4. 袜子拆左右（连通块）
  let parts = {'': null};
  const label = new Int32Array(N); let nl = 0; const sizes = [];
  if (splitSocks) {
    for (let i = 0; i < N; i++) {
      if (d[i*4+3] === 0 || label[i]) continue;
      nl++; let cnt = 0; const st = [i]; label[i] = nl;
      while (st.length) {
        const k = st.pop(); cnt++;
        const px = k % W, py = (k / W) | 0;
        for (const j of [px > 0 ? k-1 : -1, px < W-1 ? k+1 : -1, py > 0 ? k-W : -1, py < H-1 ? k+W : -1]) {
          if (j >= 0 && !label[j] && d[j*4+3] !== 0) { label[j] = nl; st.push(j); }
        }
      }
      sizes.push([cnt, nl]);
    }
    sizes.sort((a, b) => b[0] - a[0]);
  }
  x.putImageData(img, 0, 0);
  const exportCanvas = (src, mask) => {
    // 裁边
    let x0 = W, y0 = H, x1 = -1, y1 = -1;
    const dd = mask ? null : d;
    for (let i = 0; i < N; i++) {
      const on = mask ? mask(i) : d[i*4+3] > 8;
      if (!on) continue;
      const px = i % W, py = (i / W) | 0;
      if (px < x0) x0 = px; if (px > x1) x1 = px; if (py < y0) y0 = py; if (py > y1) y1 = py;
    }
    x0 = Math.max(0, x0 - 3); y0 = Math.max(0, y0 - 3); x1 = Math.min(W-1, x1 + 3); y1 = Math.min(H-1, y1 + 3);
    const cw = x1 - x0 + 1, ch = y1 - y0 + 1;
    const k = Math.min(1, maxSide / Math.max(cw, ch));
    // 分步缩小，画质比一步到位好
    let cur = document.createElement('canvas'); cur.width = cw; cur.height = ch;
    const cx = cur.getContext('2d');
    if (mask) {
      const sub = x.getImageData(x0, y0, cw, ch);
      for (let yy = 0; yy < ch; yy++) for (let xx = 0; xx < cw; xx++) {
        const i = (y0 + yy) * W + (x0 + xx);
        if (!mask(i)) sub.data[(yy*cw + xx)*4 + 3] = 0;
      }
      cx.putImageData(sub, 0, 0);
    } else cx.drawImage(c, x0, y0, cw, ch, 0, 0, cw, ch);
    let tw = cw, th = ch;
    const fw = Math.max(1, Math.round(cw * k)), fh = Math.max(1, Math.round(ch * k));
    while (tw > fw * 2) {
      const nw = Math.round(tw / 2), nh = Math.round(th / 2);
      const nc = document.createElement('canvas'); nc.width = nw; nc.height = nh;
      const nx = nc.getContext('2d'); nx.imageSmoothingQuality = 'high'; nx.drawImage(cur, 0, 0, nw, nh);
      cur = nc; tw = nw; th = nh;
    }
    const fc = document.createElement('canvas'); fc.width = fw; fc.height = fh;
    const fx = fc.getContext('2d'); fx.imageSmoothingQuality = 'high'; fx.drawImage(cur, 0, 0, fw, fh);
    return { url: fc.toDataURL('image/webp', 0.95), w: fw, h: fh };
  };
  const out = {}; out[name] = exportCanvas();
  out._holeCount = holeCount;
  if (splitSocks && sizes.length >= 2) {
    const [a, b] = [sizes[0][1], sizes[1][1]];
    // 左右按质心 x 区分
    const cxOf = id => { let s = 0, n = 0; for (let i = 0; i < N; i++) if (label[i] === id) { s += i % W; n++; } return s / n; };
    const [L, R] = cxOf(a) < cxOf(b) ? [a, b] : [b, a];
    out['socks-l'] = exportCanvas(null, i => label[i] === L);
    out['socks-r'] = exportCanvas(null, i => label[i] === R);
    out._socksComponents = sizes.length;
  }
  return out;
}
"""

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

def main():
    handler = functools.partial(QuietHandler, directory=HERE)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    results = {}
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page()
        pg.goto(f'http://127.0.0.1:{port}/fonts/')
        for name, side in TARGET.items():
            r = pg.evaluate(JS, {'name': name, 'maxSide': side, 'hollowJacket': False, 'splitSocks': name == 'socks', **dict(zip(('T', 'passes', 'fringeMin'), PARAMS.get(name, DEFAULT_PARAMS)))})
            for k, v in r.items():
                if k.startswith('_'):
                    print(f'  {name}: {k} = {v}'); continue
                results[k] = v
        br.close()
    srv.shutdown()
    os.makedirs(OUT, exist_ok=True)
    for k, v in results.items():
        data = base64.b64decode(v['url'].split(',', 1)[1])
        with open(os.path.join(OUT, k + '.webp'), 'wb') as f:
            f.write(data)
        print(f"  assets/{k}.webp  {v['w']}x{v['h']}  {len(data)//1024} KB")
    if CHECK:
        html = '<body style="margin:0;background:#2a2a2a;display:flex;flex-wrap:wrap;gap:8px;padding:8px">' + ''.join(
            f'<div style="background:repeating-conic-gradient(#555 0 25%,#333 0 50%) 0 0/20px 20px"><img src="/assets/{k}.webp" style="height:{360 if k=="capybara" else 240}px"></div>' for k in results) + '</body>'
        os.makedirs(os.path.join(HERE, '.playwright-output'), exist_ok=True)
        with open(os.path.join(HERE, '.playwright-output', 'prep-check.html'), 'w') as f:
            f.write(html)
        handler2 = functools.partial(QuietHandler, directory=HERE)
        srv2 = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler2)
        threading.Thread(target=srv2.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            br = p.chromium.launch(); pg = br.new_page(viewport={'width': 1500, 'height': 800})
            pg.goto(f'http://127.0.0.1:{srv2.server_address[1]}/.playwright-output/prep-check.html'); pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(HERE, '.playwright-output', 'prep-check.png'))
            br.close()
        srv2.shutdown()

main()
