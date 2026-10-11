"""着色总览图：18 件缩到转盘上的大小（70px）画在课本扇形底色上，另一排放在中性底色上，
输出 .playwright-output/tinted-18.png，用来肉眼检查 grey/black/brown、pink/red/orange 分不分得清。
用法：python3 scripts/tinted-overview.py"""
import functools, http.server, os, threading
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, '.playwright-output', 'tinted-18.png')

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

JS = """() => {
  const D = window.__dressing, items = D.items;
  const cv = document.createElement('canvas'); cv.id = 'ov'; cv.width = 1020; cv.height = 560;
  cv.style.cssText = 'position:fixed;left:0;top:0;z-index:9999;width:1020px;height:560px';
  document.body.appendChild(cv);
  const x = cv.getContext('2d');
  x.fillStyle = '#fff'; x.fillRect(0, 0, 1020, 560);
  x.font = '700 15px Andika, sans-serif'; x.fillStyle = '#222';
  x.fillText('18 items at wheel size (70px icon) on the textbook sector colours', 12, 22);
  x.fillText('Same icons on a neutral cream background (colour only)', 12, 312);
  items.forEach((it, i) => {
    const col = i % 9, row = Math.floor(i / 9);
    const ic = D.wheelIcon(it, 70);
    // 第一排：扇形底色
    const bx = 12 + col * 111, by = 34 + row * 138;
    x.fillStyle = it.bg; x.fillRect(bx, by, 100, 100);
    x.drawImage(ic, bx + 50 - ic.width / 2, by + 50 - ic.height / 2);
    x.fillStyle = '#222'; x.font = '13px Andika, sans-serif'; x.fillText(it.phrase, bx, by + 118);
    // 第二排：中性底
    const by2 = 324 + row * 112;
    x.fillStyle = '#FFF3DC'; x.fillRect(bx, by2, 100, 100);
    x.drawImage(ic, bx + 50 - ic.width / 2, by2 + 50 - ic.height / 2);
  });
}"""

def main():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory=HERE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={'width': 1100, 'height': 600})
        pg.route('**/track-use.js', lambda r: r.fulfill(status=200, content_type='text/javascript', body=''))
        pg.goto(f'http://127.0.0.1:{srv.server_address[1]}/index.html'); pg.wait_for_selector('body[data-ready]')
        pg.evaluate(JS); pg.wait_for_timeout(200)
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        pg.locator('#ov').screenshot(path=OUT)
        br.close()
    srv.shutdown()
    print('saved', OUT)

main()
