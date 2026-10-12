"""The Dressing Game 端到端测试（改版后：左转盘/答题 5 + 右收藏 7，字母块开关，固定 +5 星，3 套奖励）。
用法：python3 test-e2e.py            （自己开本机静态服务器）
      TARGET=http://127.0.0.1:8791 python3 test-e2e.py   （改测已开着的服务器／线上）
      FAST=1 python3 test-e2e.py     （第 2、3 套和 18 件全收集改用 localStorage 预置，省约 90 秒）
track-use.js（外部统计）在测试里用空脚本代替，只记录「有被请求」。
截图 → ~/Documents/my-agent/playwright-to-delete/dressing-test/。"""
import functools, http.server, os, threading
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.expanduser('~/Documents/my-agent/playwright-to-delete/dressing-test')
os.makedirs(SHOTS, exist_ok=True)
FAST = os.environ.get('FAST') == '1'
KEY = 'tahun2-bi-dressing:v1'

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

TARGET = os.environ.get('TARGET')
if not TARGET:
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory=HERE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    TARGET = f'http://127.0.0.1:{srv.server_address[1]}'
URL = TARGET.rstrip('/') + '/index.html'
HOST = TARGET.split('//', 1)[1].split('/')[0]

fails = 0; total = 0
def check(name, ok, extra=''):
    global fails, total
    total += 1
    print(('  PASS ' if ok else '  FAIL ') + name + (f' — {extra}' if extra else ''), flush=True)
    if not ok: fails += 1

INIT = """
window.__aud = [];
(() => { const A = window.Audio;
  window.Audio = function (src) { window.__aud.push(String(src)); return new A(src); };
  window.Audio.prototype = A.prototype; })();
window.__mx = 0;
setInterval(() => { window.__mx = Math.max(window.__mx, window.scrollY || 0); }, 16);
addEventListener('scroll', () => { window.__mx = Math.max(window.__mx, window.scrollY || 0); }, true);
"""

def new_page(br, w=1366, h=768, touch=False):
    ctx = br.new_context(viewport={'width': w, 'height': h}, has_touch=touch)
    page = ctx.new_page()
    page.errors = []; page.reqs = []; page.dialogs = []; page.areqs = []
    page.add_init_script(INIT)
    page.on('pageerror', lambda e: page.errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: m.type == 'error' and page.errors.append('console: ' + m.text))
    page.on('dialog', lambda d: (page.dialogs.append(d.type), d.dismiss()))
    page.on('request', lambda r: '/audio/' in r.url and page.areqs.append(r.url))
    page.on('response', lambda r: page.reqs.append((r.url, r.status)))
    page.route('**/track-use.js', lambda r: (page.reqs.append((r.request.url, 'mocked')), r.fulfill(status=200, content_type='text/javascript', body='')))
    return page

def open_game(page, preset=None):
    page.goto(URL)
    if preset is not None:
        page.evaluate("([k, p]) => localStorage.setItem(k, JSON.stringify(p))", [KEY, preset])
        page.reload()
    page.wait_for_selector('body[data-ready]'); page.wait_for_timeout(300)

def st(page): return page.evaluate('() => window.__dressing.state()')
def aud(page): return page.evaluate('() => window.__aud.slice()')
def ITEMS(page): return {i['id']: i for i in page.evaluate('() => window.__dressing.items')}
def set_of(page, iid):
    for k, s in enumerate(page.evaluate('() => window.__dressing.sets')):
        if any(i['id'] == iid for i in s): return k
def words(it):
    cloth = it['phrase'].split(' ', 1)[1]
    return it['color'], cloth, cloth.replace('-', '')
def shot(page, name):
    page.wait_for_timeout(350)
    path = os.path.join(SHOTS, name + '.png'); page.screenshot(path=path); return path

def spin(page, how='wheel', iid=None):
    """转一次，返回 (毫秒, 转的过程中的音档数增量)"""
    if iid: page.evaluate('id => window.__dressing.forceNext(id)', iid)
    n0 = len(aud(page))
    if how == 'wheel':
        b = page.eval_on_selector('#wheelWrap', 'e => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }')
        page.mouse.click(b[0] + b[2] * 0.2, b[1] + b[3] * 0.5)
    elif how == 'btn': page.evaluate("document.getElementById('btnSpin').click()")
    elif how == 'space': page.keyboard.press('Space')
    page.wait_for_selector('body[data-phase=answer]', timeout=9000)
    ms = int(page.evaluate("() => document.getElementById('wheelWrap').dataset.lastSpinMs"))
    return ms, len(aud(page)) - n0

def wait_stage(page, stage):
    page.wait_for_function("s => window.__dressing.state().stage === s", arg=stage, timeout=6000)

def type_word(page, text, how='kb'):
    if how == 'kb': page.keyboard.type(text, delay=25)
    else:
        for ch in text:
            page.click(f'#tiles .tile-btn:not([disabled])[data-ch="{ch}"]')

def finish(page, it, how='kb', wait_done=True):
    col, cloth, letters = words(it)
    type_word(page, col, how); wait_stage(page, 'cloth')
    type_word(page, letters, how)
    if wait_done: page.wait_for_selector('body[data-phase=done]', timeout=6000)

def counts(page):
    return page.evaluate("""() => ({
      cc: document.getElementById('colCount').textContent, sub: document.getElementById('colSub').textContent,
      got: document.querySelectorAll('#shelf .tile.got').length, lock: document.querySelectorAll('#shelf .tile.lock').length,
      st: window.__dressing.state().collected.length, stars: document.getElementById('starTotal').textContent })""")

def check_counts(page, label):
    c = counts(page); n = c['st']
    check(f'{label}：#colCount / #colSub / .tile.got / state().collected 四者相等（{n}）',
          c['cc'] == f'{n}/18' and c['sub'] == f'{n} of 18' and c['got'] == n and c['lock'] == 18 - n, str(c))

def check_locked_clean(page, label):
    bad = page.evaluate("""() => { const w = ['brown','red','blue','grey','black','green','orange','pink','purple','yellow','cap','shirt','jacket','trousers','socks','shoes'];
      return [...document.querySelectorAll('#shelf .tile.lock')].filter(t => {
        const s = (t.textContent + ' ' + (t.getAttribute('aria-label')||'') + ' ' + [...t.querySelectorAll('img')].map(i => i.alt).join(' ')).toLowerCase();
        return t.textContent.trim() !== 'Locked' || w.some(x => s.includes(x)); }).length; }""")
    check(f'{label}：锁定格文字只有 "Locked"，没有衣服名', bad == 0, f'违规格 {bad}')

def new_item_on_shelf(page, it):
    t = page.evaluate("id => { const e = document.querySelector(`#shelf .tile.got[data-id='${id}']`); return e ? e.textContent.trim() : null }", it['id'])
    return t is not None and it['phrase'].lower() in t.lower()

def layout_ok(page):
    return page.evaluate("""() => { const q = s => document.querySelector(s).getBoundingClientRect();
      const p = q('#panel'), c = q('#collection');
      const xs = new Set([...document.querySelectorAll('#shelf .tile')].map(t => Math.round(t.getBoundingClientRect().x)));
      const ys = new Set([...document.querySelectorAll('#shelf .tile')].map(t => Math.round(t.getBoundingClientRect().y)));
      return { ph: p.height, ch: c.height, pw: p.width, cw: c.width, ratio: p.width / (p.width + c.width), cols: xs.size, rows: ys.size,
               sh: document.documentElement.scrollHeight, ih: innerHeight, sw: document.documentElement.scrollWidth, iw: innerWidth,
               shelfBottom: q('#shelf').bottom, colBottom: c.bottom }; }""")

def contained(page):
    """答题视图里的内容（字母块、键盘、格子）没超出面板"""
    return page.evaluate("""() => { const P = document.getElementById('panel').getBoundingClientRect(); const out = [];
      for (const e of document.querySelectorAll('#viewAnswer .tile-btn, #viewAnswer .key, #viewAnswer .cell, #viewAnswer .ask-head, #viewAnswer .words, #viewAnswer #tiles, #viewAnswer #kb')) {
        if (e.offsetParent === null) continue;
        const r = e.getBoundingClientRect();
        if (r.left < P.left - 1 || r.right > P.right + 1 || r.top < P.top - 1 || r.bottom > P.bottom + 1) out.push(e.id || e.className); }
      return out; }""")

def wait_back(page, timeout=9000):
    page.wait_for_selector('body[data-phase=idle], body[data-phase=reward], body[data-phase=final]', timeout=timeout)

with sync_playwright() as p:
    br = p.chromium.launch()

    # ═════ A 冷启动、请求、布局 ═════
    print('A  冷启动／请求／布局 1366×768')
    page = new_page(br)
    open_game(page)
    check('冷启动无控制台 error／页面错误', page.errors == [], str(page.errors))
    ext = [u for u, s in page.reqs if HOST not in u and 'kongsi-idea.vercel.app/data/track-use.js' not in u]
    check('除 track-use.js 外无外部请求', ext == [], str(ext))
    check('track-use.js 有被请求（已用空脚本代替）', any('track-use.js' in u for u, s in page.reqs))
    local = [(u, s) for u, s in page.reqs if HOST in u]
    fonts = [(u, s) for u, s in local if u.endswith('.woff2')]
    check('本地字体已请求且 200', len(fonts) >= 1 and all(s == 200 for u, s in fonts), str([u.split('/')[-1] for u, s in fonts]))
    check('冷启动期间本地请求全部 200', all(s == 200 for u, s in local), str([(u.split('/')[-1], s) for u, s in local if s != 200]))
    check('冷启动不请求任何音档', page.areqs == [] and aud(page) == [], str(page.areqs))
    L = layout_ok(page)
    check('1366×768 页面无纵向滚动（scrollHeight <= innerHeight）', L['sh'] <= L['ih'], f"{L['sh']} vs {L['ih']}")
    check('左卡≈5/12、右卡≈7/12', abs(L['ratio'] - 5 / 12) < 0.04, f"左占 {L['ratio']:.3f}")
    check('左右两卡同高', abs(L['ph'] - L['ch']) <= 2, f"{L['ph']:.0f} vs {L['ch']:.0f}")
    check('收藏 6 列 × 3 排共 18 格', L['cols'] == 6 and L['rows'] == 3 and counts(page)['lock'] == 18, f"cols={L['cols']} rows={L['rows']}")
    check('收藏整体在视口内', L['colBottom'] <= L['ih'] + 1, f"bottom {L['colBottom']:.0f}")
    check('初始 0/18、0 of 18、0 星', counts(page)['cc'] == '0/18' and counts(page)['sub'] == '0 of 18' and counts(page)['stars'] == '0')
    check_locked_clean(page, '初始')
    check('词表：18 件、3 套×6、每套 6 种衣服', len(ITEMS(page)) == 18 and all(len(s) == 6 and len({i['type'] for i in s}) == 6 for s in page.evaluate('() => window.__dressing.sets')))
    check('字母块默认 On：#btnTilesOn aria-pressed=true', page.get_attribute('#btnTilesOn', 'aria-pressed') == 'true' and page.get_attribute('#btnTilesOff', 'aria-pressed') == 'false')
    shot(page, 'desktop-1-idle')
    IT = ITEMS(page)
    stars = 0; played = []

    # ═════ B 第 1 件 brown-cap：点转盘转、字母块、喇叭、不论错几次 +5 ═════
    print('B  brown-cap：点转盘 / 字母块 / 喇叭')
    page.evaluate('window.__mx = 0')
    ms, da = spin(page, 'wheel', 'brown-cap')
    check('点转盘转完进入 answer 阶段', st(page)['phase'] == 'answer')
    check('转盘时长 2.8–3.3 秒', 2800 <= ms <= 3300, f'{ms}ms；__dressing.lastSpinMs()={page.evaluate("() => window.__dressing.lastSpinMs()"):.0f}')
    check('落点后不自动读音（转盘→开始答题 0 次 Audio/请求）', da == 0 and page.areqs == [], f'Audio 增量 {da}, 请求 {page.areqs}')
    check('落点 = 指定的 brown-cap', st(page)['current'] == 'brown-cap')
    check('字母块 On：#tiles 可见、#kb 隐藏', page.is_visible('#tiles') and not page.is_visible('#kb'))
    tiles = page.eval_on_selector_all('#tiles .tile-btn', 'els => els.map(e => e.dataset.ch)')
    check('字母块 = brown 的 5 个字母（打乱）', sorted(tiles) == sorted('brown') and len(tiles) == 5, ''.join(tiles))
    check('颜色格 5 个、衣服格 3 个（先拼颜色）', len(page.query_selector_all('#cellsColour .cell')) == 5 and len(page.query_selector_all('#cellsCloth .cell')) == 3 and page.evaluate("document.getElementById('rowColour').classList.contains('active')"))
    shot(page, 'desktop-2-answer-tiles')
    Lc = layout_ok(page)
    check('答题中（字母块）页面无纵向滚动', Lc['sh'] <= Lc['ih'], f"{Lc['sh']} vs {Lc['ih']}")
    check('答题中（字母块）内容没超出面板', contained(page) == [], str(contained(page)))
    check('答题中右侧收藏仍可见且同高', page.is_visible('#shelf') and abs(Lc['ph'] - Lc['ch']) <= 2)
    # 点一个字母块 → 填入 + .used
    page.click(f'#tiles .tile-btn[data-ch="{"brown"[0]}"]')
    check('点字母块 b：格子填入 b、该块 .used', page.inner_text('#cellsColour .cell:nth-child(1)') == 'b' and page.evaluate("document.querySelector('#tiles .tile-btn[data-ch=\"b\"]').classList.contains('used')"))
    # 喇叭
    n0 = len(page.areqs)
    page.click('#btnSay'); page.wait_for_timeout(500)
    check('点 #btnSay 才请求 audio/*.mp3', len(page.areqs) == n0 + 1 and page.areqs[-1].endswith('.mp3'), str(page.areqs[-1:]))
    type_word(page, 'rown', 'tiles'); wait_stage(page, 'cloth')
    check('颜色拼对：.locked 变绿的格子 5 个', len(page.query_selector_all('#cellsColour .cell.locked')) == 5)
    tiles2 = page.eval_on_selector_all('#tiles .tile-btn', 'els => els.map(e => e.dataset.ch)')
    check('衣服阶段字母块换成 cap 的 3 个字母', sorted(tiles2) == sorted('cap'), ''.join(tiles2))
    na = len(aud(page))
    type_word(page, 'cap', 'tiles')
    page.wait_for_selector('body[data-phase=done]', timeout=6000)
    stars += 5; played.append('brown-cap')
    check('brown-cap 完成：+5 星（用字母块＋点喇叭）', st(page)['stars'] == 5 and page.inner_text('#starTotal') == '5', str(st(page)['stars']))
    check('立刻出现在右侧 #shelf：.tile.got 写 "brown cap"', new_item_on_shelf(page, IT['brown-cap']))
    check_counts(page, 'brown-cap 后'); check_locked_clean(page, 'brown-cap 后')
    page.wait_for_timeout(700)
    check('拼完整件读一次 phrase 音（brown-cap.mp3）', len(aud(page)) == na + 1 and aud(page)[-1].endswith('brown-cap.mp3'), str(aud(page)[-2:]))
    wait_back(page)
    check('第一件期间 scrollY 始终为 0（桌面）', page.evaluate('window.__mx') == 0, str(page.evaluate('window.__mx')))
    shot(page, 'desktop-3-after-one')

    # ═════ C 第 2 件 red-t-shirt：空白键转、屏幕键盘、大小写、错两次仍 +5 ═════
    print('C  red-t-shirt：空白键 / 屏幕键盘 / 大小写 / 错两次')
    page.click('#btnTilesOff')
    check('字母块 Off：#tiles 隐藏、#kb 显示、aria-pressed 切换', not page.is_visible('#tiles') and page.get_attribute('#btnTilesOff', 'aria-pressed') == 'true' and page.get_attribute('#btnTilesOn', 'aria-pressed') == 'false')
    check('Off 选择存进 localStorage（tiles=false）', page.evaluate("k => JSON.parse(localStorage.getItem(k)).tiles", KEY) is False)
    # 点完开关按钮后（焦点还在按钮上）直接按空白键，应该能转（学生常这样操作）
    page.evaluate("window.__dressing.forceNext('red-t-shirt')")
    page.keyboard.press('Space'); page.wait_for_timeout(600)
    check('点完 #btnTilesOff 后直接按空白键能转（焦点在开关按钮上）', st(page)['phase'] in ('spinning', 'answer'), f"phase={st(page)['phase']} tiles={st(page)['tiles']}（空白键被按钮吃掉）")
    if st(page)['phase'] == 'idle':
        page.evaluate('document.activeElement && document.activeElement.blur()')
        if st(page)['tiles']: page.click('#btnTilesOff'); page.evaluate('document.activeElement.blur()')
    ms, da = spin(page, 'space', 'red-t-shirt') if st(page)['phase'] == 'idle' else (int(page.evaluate("document.getElementById('wheelWrap').dataset.lastSpinMs || 0")) if page.wait_for_selector('body[data-phase=answer]', timeout=9000) else 0, 0)
    check('空白键可转，2.8–3.3 秒、无自动读音', 2800 <= ms <= 3300 and da == 0, f'{ms}ms 音档增量 {da}')
    check('字母块 Off：#kb 显示、#tiles 隐藏', page.is_visible('#kb') and not page.is_visible('#tiles'))
    kb = page.evaluate("""() => ({ rows: [...document.querySelectorAll('#kb .kb-row')].map(r => [...r.querySelectorAll('.key:not(.key-shift):not(.key-del)')].map(k => k.textContent.trim()).join('')),
      shift: !!document.querySelector('#kb .key-shift'), del: !!document.querySelector('#kb .key-del') })""")
    check('屏幕键盘 qwerty 三排小写＋Shift＋Delete', kb['rows'] == ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'] and kb['shift'] and kb['del'], str(kb))
    shot(page, 'desktop-4-answer-keyboard')
    Lc = layout_ok(page)
    check('答题中（屏幕键盘）无纵向滚动、内容没超出面板', Lc['sh'] <= Lc['ih'] and contained(page) == [], f"{Lc['sh']}/{Lc['ih']} {contained(page)}")
    # 错的颜色：5 格 → wrong → 清空
    page.keyboard.type('xxx', delay=20)
    check('颜色 red 打 "xxx"：3 格 .wrong', len(page.query_selector_all('#cellsColour .cell.wrong')) == 3)
    page.wait_for_timeout(900)
    check('红格后清空、可重打', all(c == '' for c in page.eval_on_selector_all('#cellsColour .cell', 'e => e.map(x => x.textContent)')) and not page.query_selector('#cellsColour .cell.wrong'))
    page.keyboard.type('red', delay=20); wait_stage(page, 'cloth')
    cells = page.evaluate("[...document.querySelectorAll('#cellsCloth .cell')].map(c => ({fixed: c.classList.contains('fixed'), t: c.textContent}))")
    check('T-shirt 7 格，第 2 格是预填连字号', len(cells) == 7 and cells[1]['fixed'] and cells[1]['t'] == '-', str(cells))
    # 小写 t 作首字母判错（连打 tshirt：只有第一格错）
    page.keyboard.type('tshirt', delay=20)
    w = page.evaluate("[...document.querySelectorAll('#cellsCloth .cell')].map(c => c.className)")
    check('小写 t 作 T-shirt 首字母 → 第 1 格 .wrong（红）、其余 5 格 .locked', 'wrong' in w[0] and sum('locked' in c for c in w) == 5, str(w))
    page.wait_for_timeout(900)
    check('错格清空，其余保持', page.inner_text('#cellsCloth .cell:nth-child(1)') == '' and len(page.query_selector_all('#cellsCloth .cell.locked')) == 5)
    page.keyboard.press('t'); page.wait_for_timeout(100)
    check('第二次打小写 t 仍判错', 'wrong' in page.get_attribute('#cellsCloth .cell:nth-child(1)', 'class'))
    page.wait_for_timeout(900)
    page.keyboard.press('Shift+T')
    page.wait_for_selector('body[data-phase=done]', timeout=6000)
    stars += 5; played.append('red-t-shirt')
    check('实体键盘 Shift+t 判对；错了 3 次仍只 +5（共 10）', st(page)['stars'] == 10 and page.inner_text('#starTotal') == '10', str(st(page)['stars']))
    check('red T-shirt 立刻出现在收藏', new_item_on_shelf(page, IT['red-t-shirt']))
    check_counts(page, 'red-t-shirt 后'); check_locked_clean(page, 'red-t-shirt 后')
    wait_back(page)

    # ═════ D 第 3 件 orange-t-shirt（第 2 套）：按钮转、屏幕键盘 Shift+t ═════
    print('D  orange-t-shirt：#btnSpin / 屏幕键盘 Shift')
    ms, da = spin(page, 'btn', 'orange-t-shirt')
    check('#btnSpin 可转，2.8–3.3 秒', 2800 <= ms <= 3300, f'{ms}ms')
    page.keyboard.type('orange', delay=20); wait_stage(page, 'cloth')
    for ch in 'tshirt': page.click(f'#kb .key[data-k="{ch}"]')
    page.wait_for_timeout(100)
    check('屏幕键盘不按 Shift 点 t（tshirt 全小写）→ 首格判错', 'wrong' in page.get_attribute('#cellsCloth .cell:nth-child(1)', 'class'))
    page.wait_for_timeout(900)
    page.click('#kb .key-shift')
    check('点 Shift 后 aria-pressed=true', page.get_attribute('#kb .key-shift', 'aria-pressed') == 'true')
    page.click('#kb .key[data-k="t"]')
    check('Shift 后点 t → 填入大写 T，Shift 自动弹起', page.inner_text('#cellsCloth .cell:nth-child(1)') == 'T' and page.get_attribute('#kb .key-shift', 'aria-pressed') == 'false')
    for ch in 'shirt': page.click(f'#kb .key[data-k="{ch}"]')
    page.wait_for_selector('body[data-phase=done]', timeout=6000)
    stars += 5; played.append('orange-t-shirt')
    check('屏幕键盘拼完 +5（共 15）', st(page)['stars'] == 15 and page.inner_text('#starTotal') == '15')
    check_counts(page, 'orange-t-shirt 后')
    wait_back(page)

    # ═════ E 连续随机转：落点永远在第 1 套没收集过的几件里 ═════
    print('E  随机落点 + 第 1 套凑满奖励')
    page.click('#btnTilesOn')
    check('切回 On：aria-pressed 切换', page.get_attribute('#btnTilesOn', 'aria-pressed') == 'true')
    set0 = {i['id'] for i in page.evaluate('() => window.__dressing.sets[0]')}
    while True:
        s0 = st(page)
        todo = set0 - set(s0['collected'])
        if not todo: break
        spin(page, 'wheel')
        cur = st(page)['current']
        ok = cur in todo
        check(f'随机落点 {cur} 属于第 1 套且未收集过', ok, f'待收集 {sorted(todo)}')
        if not page.is_visible('#tiles'): check('字母块 On 时答题中 #tiles 可见', False)
        finish(page, IT[cur], 'tiles' if len(todo) % 2 else 'kb')
        stars += 5; played.append(cur)
        check_counts(page, f'{cur} 后')
        check(f'{cur} 立刻出现在收藏', new_item_on_shelf(page, IT[cur]))
        if len(todo) > 1:
            wait_back(page)
    # 现在 6 件齐 → 奖励
    page.wait_for_selector('body[data-phase=reward]', timeout=6000)
    check('第 1 套凑满 → 显示奖励视图 #viewReward', page.is_visible('#viewReward') and not page.is_visible('#viewAnswer'))
    page.wait_for_timeout(700)
    img_vis = page.is_visible('#rewardImg')
    grid_n = page.eval_on_selector_all('#rewardGrid img', 'e => e.length') if page.is_visible('#rewardGrid') else 0
    check('奖励：#rewardImg 可见，或 #rewardGrid 兜底显示 6 件衣服', img_vis or grid_n == 6, f'rewardImg可见={img_vis} grid={grid_n}（图未生成时兜底属正常）')
    check('state().rewarded 含第 1 套(0)', 0 in st(page)['rewarded'], str(st(page)['rewarded']))
    check('星星 = 已拼件数 × 5（固定 +5）', st(page)['stars'] == stars == 5 * len(played), f"{st(page)['stars']} vs {stars}")
    shot(page, 'desktop-5-reward')
    page.click('#btnReward')
    check('按 #btnReward 回到转盘', st(page)['phase'] == 'idle' and page.is_visible('#viewIdle') and not page.is_visible('#viewReward'))
    check_counts(page, '第 1 套后')
    # 刷新保留
    before = st(page)
    page.reload(); page.wait_for_selector('body[data-ready]'); page.wait_for_timeout(300)
    after = st(page)
    check('刷新后收集、星星、套奖励仍在', after['collected'] == before['collected'] and after['stars'] == before['stars'] and after['rewarded'] == before['rewarded'])
    check('刷新后字母块选择保留（On）', after['tiles'] is True and page.get_attribute('#btnTilesOn', 'aria-pressed') == 'true')
    page.click('#btnTilesOff'); page.reload(); page.wait_for_selector('body[data-ready]')
    check('字母块 Off 刷新后保留', st(page)['tiles'] is False and page.get_attribute('#btnTilesOff', 'aria-pressed') == 'true')
    page.click('#btnTilesOn')
    shot(page, 'desktop-6-collection-set1')
    # 不自动滚动整局统计
    check('整局桌面页面无纵向滚动', layout_ok(page)['sh'] <= 768)
    check('桌面整局 scrollY 始终为 0', page.evaluate('window.__mx') == 0, str(page.evaluate('window.__mx')))

    # ═════ F 第 2、3 套 & 全 18 件 ═════
    if FAST:
        print('F  第 2/3 套与 18 件（FAST：localStorage 预置）')
        sets = page.evaluate('() => window.__dressing.sets'); ids = [[i['id'] for i in s] for s in sets]
        page.close()
        page = new_page(br)
        open_game(page, {'collected': ids[0], 'rewarded': [0], 'stars': 30, 'muted': True, 'tiles': True})
        spin(page, 'wheel'); cur = st(page)['current']
        check('第 1 套已凑满时，落点落在第 2 套', set_of(page, cur) == 1, cur)
        finish(page, IT[cur]); wait_back(page)
        check_counts(page, '第 2 套第一件后')
        page.close()
        page = new_page(br)
        open_game(page, {'collected': ids[0] + ids[1][:5], 'rewarded': [0], 'stars': 55, 'muted': True, 'tiles': True})
        spin(page, 'wheel'); cur = st(page)['current']
        check('第 2 套差 1 件时，落点就是那 1 件', cur == ids[1][5], cur)
        finish(page, IT[cur])
        page.wait_for_selector('body[data-phase=reward]', timeout=6000)
        check('第 2 套凑满 → 奖励视图，rewarded 含 1', page.is_visible('#viewReward') and 1 in st(page)['rewarded'], str(st(page)['rewarded']))
        page.click('#btnReward')
        page.close()
        page = new_page(br)
        open_game(page, {'collected': ids[0] + ids[1] + ids[2][:3], 'rewarded': [0, 1], 'stars': 45 + 15 + 30 - 45, 'muted': True, 'tiles': True})
        spin(page, 'wheel'); cur = st(page)['current']
        check('前两套满时，落点落在第 3 套没收集过的', cur in ids[2][3:], cur)
        page.close()
        # 17 件预置 → 最后一件 → finale
        page = new_page(br)
        last = ids[2][5]
        open_game(page, {'collected': ids[0] + ids[1] + ids[2][:5], 'rewarded': [0, 1], 'stars': 85, 'muted': True, 'tiles': True})
        check('预置 17 件：#colCount 17/18、17 个 .tile.got', counts(page)['cc'] == '17/18' and counts(page)['got'] == 17)
        check_counts(page, '预置 17 件'); check_locked_clean(page, '预置 17 件')
        spin(page, 'wheel'); check('只剩 1 件时落点就是它', st(page)['current'] == last, st(page)['current'])
        finish(page, IT[last])
        page.wait_for_selector('body[data-phase=reward]', timeout=6000)
        check('第 3 套凑满 → 奖励；按钮 "See my stars"', page.is_visible('#viewReward') and page.inner_text('#btnReward').strip() == 'See my stars')
        check('18 件收集', counts(page)['cc'] == '18/18' and counts(page)['lock'] == 0)
    else:
        print('F  第 2、3 套全程随机实玩（完整 18 件）')
        for k in (1, 2):
            setk = {i['id'] for i in page.evaluate(f'() => window.__dressing.sets[{k}]')}
            while True:
                todo = setk - set(st(page)['collected'])
                if not todo: break
                spin(page, 'wheel'); cur = st(page)['current']
                check(f'随机落点 {cur} 属于第 {k+1} 套且未收集', cur in todo and set_of(page, cur) == k, f'待 {sorted(todo)}')
                finish(page, IT[cur]); stars += 5
                check_counts(page, f'{cur} 后')
                if len(todo) > 1: wait_back(page)
            page.wait_for_selector('body[data-phase=reward]', timeout=6000)
            check(f'第 {k+1} 套凑满 → 奖励视图', page.is_visible('#viewReward') and k in st(page)['rewarded'])
            if k == 1: page.click('#btnReward')
    # finale
    if not FAST: pass
    check('按奖励钮（See my stars）→ 弹出 #finale', (page.click('#btnReward') or True) and page.is_visible('#finale'))
    check('#finale 显示 18 张图与星星数', len(page.query_selector_all('#finaleGrid img')) == 18 and page.inner_text('#finaleStars').strip().isdigit())
    shot(page, 'desktop-7-finale')
    check('18 件：state().collected=18、rewarded 含 0,1,2', len(st(page)['collected']) == 18 and set(st(page)['rewarded']) == {0, 1, 2}, str(st(page)['rewarded']))
    page.reload(); page.wait_for_selector('body[data-ready]'); page.wait_for_timeout(300)
    check('刷新后 18 件全集仍在、finale 重新弹出', len(st(page)['collected']) == 18 and page.is_visible('#finale'))
    page.click('#btnAgain'); page.wait_for_timeout(300)
    s = st(page); c = counts(page)
    check('#btnAgain 清空：0/18、0 星、finale 关闭、回到转盘', s['collected'] == [] and s['stars'] == 0 and s['rewarded'] == [] and c['cc'] == '0/18' and c['got'] == 0 and not page.is_visible('#finale') and s['phase'] == 'idle', str(s))
    check_locked_clean(page, '重玩后')
    check('桌面全程没有 alert/confirm/prompt', page.dialogs == [], str(page.dialogs))
    miss = [u for u, s_ in page.reqs if s_ == 404]
    other = [e for e in page.errors if '404' not in e]
    check('桌面全程无控制台 error（outfit-N.webp 尚未生成的 404 不算）', not other and all('outfit-' in u for u in miss), f'{other} 404={[u.split("/")[-1] for u in miss]}')
    check('桌面全程请求只在本机（除 track-use.js）', not [u for u, s_ in page.reqs if HOST not in u and 'track-use.js' not in u])
    page.close()

    # ═════ G 手机直立 390×844 ═════
    print('G  手机直立 390×844')
    page = new_page(br, 390, 844, touch=True)
    open_game(page)
    check('手机冷启动无 error', page.errors == [], str(page.errors))
    check('手机无横向滚动（idle）', layout_ok(page)['sw'] <= 390, str(layout_ok(page)['sw']))
    shot(page, 'mobile-1-idle')
    page.evaluate('window.__mx = 0')
    ms, da = spin(page, 'wheel', 'blue-jacket')
    check('手机点转盘：2.8–3.3 秒、无自动读音', 2800 <= ms <= 3300 and da == 0, f'{ms}ms 音档增量 {da}')
    check('手机答题（字母块）内容没超出面板', contained(page) == [], str(contained(page)))
    check('手机答题无横向滚动', layout_ok(page)['sw'] <= 390, str(layout_ok(page)['sw']))
    shot(page, 'mobile-2-answer-tiles')
    page.evaluate("document.getElementById('btnTilesOff').click()"); page.wait_for_timeout(200)
    check('手机答题（屏幕键盘）内容没超出面板', contained(page) == [], str(contained(page)))
    check('手机答题（屏幕键盘）无横向滚动', layout_ok(page)['sw'] <= 390, str(layout_ok(page)['sw']))
    shot(page, 'mobile-3-answer-keyboard')
    page.keyboard.type('blue', delay=30); wait_stage(page, 'cloth')
    page.keyboard.type('jacket', delay=30)
    page.wait_for_selector('body[data-phase=done]', timeout=6000); wait_back(page)
    check('手机：blue jacket 收进收藏，计数一致', new_item_on_shelf(page, IT['blue-jacket']))
    check_counts(page, '手机 blue-jacket 后')
    mx = page.evaluate('window.__mx')
    check('手机：从点转盘到答完，scrollY 始终为 0', mx == 0, f'最大 scrollY = {mx}')
    sh_ = page.evaluate("document.documentElement.scrollHeight"); ih_ = page.evaluate("innerHeight")
    page.evaluate("document.getElementById('collection').scrollIntoView()"); page.wait_for_timeout(200)
    shot(page, 'mobile-4-collection')
    check('手机：收藏在转盘面板下方（可纵向滚动，预期）', page.evaluate("document.getElementById('collection').getBoundingClientRect().top >= 0 || scrollY > 0") and sh_ >= ih_, f'scrollHeight {sh_} / {ih_}')
    wide = page.evaluate("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => (e.id || (e.className.baseVal ?? e.className)) + ':' + Math.round(e.getBoundingClientRect().right))")
    check('手机无横向滚动（收藏）', layout_ok(page)['sw'] <= 390, f"scrollWidth={layout_ok(page)['sw']} 超宽元素 {wide}")
    check('手机收藏 18 格、每格独立（报告实际列×排；手机不强求 6×3）', layout_ok(page)['cols'] * layout_ok(page)['rows'] == 18, f"{layout_ok(page)['cols']} 列 × {layout_ok(page)['rows']} 排")
    check('手机无 dialog／error', page.dialogs == [] and page.errors == [], str(page.errors))
    page.close()

    # ═════ H iPad 横屏 1180×820 ═════
    print('H  iPad 横屏 1180×820')
    page = new_page(br, 1180, 820, touch=True)
    open_game(page)
    shot(page, 'ipad-1-idle')
    L = layout_ok(page)
    check('iPad 无横向滚动', L['sw'] <= 1180, str(L['sw']))
    check('iPad 页面无纵向滚动', L['sh'] <= L['ih'], f"{L['sh']} vs {L['ih']}")
    check('iPad 左右同高', abs(L['ph'] - L['ch']) <= 2, f"{L['ph']:.0f} vs {L['ch']:.0f}")
    page.evaluate('window.__mx = 0')
    spin(page, 'wheel', 'grey-trousers')
    check('iPad 答题（字母块）没超出面板、无横向滚动', contained(page) == [] and layout_ok(page)['sw'] <= 1180, str(contained(page)))
    check('iPad 答题无纵向滚动', layout_ok(page)['sh'] <= layout_ok(page)['ih'], str(layout_ok(page)['sh']))
    shot(page, 'ipad-2-answer-tiles')
    page.evaluate("document.getElementById('btnTilesOff').click()"); page.wait_for_timeout(200)
    check('iPad 答题（屏幕键盘）没超出面板', contained(page) == [], str(contained(page)))
    shot(page, 'ipad-3-answer-keyboard')
    page.keyboard.type('grey', delay=30); wait_stage(page, 'cloth'); page.keyboard.type('trousers', delay=30)
    page.wait_for_selector('body[data-phase=done]', timeout=6000); wait_back(page)
    check('iPad：grey trousers 收进收藏，计数一致', new_item_on_shelf(page, IT['grey-trousers']))
    check_counts(page, 'iPad grey-trousers 后')
    check('iPad：scrollY 始终为 0', page.evaluate('window.__mx') == 0, str(page.evaluate('window.__mx')))
    shot(page, 'ipad-4-collection')
    check('iPad 无 dialog／error', page.dialogs == [] and page.errors == [], str(page.errors))
    page.close()
    br.close()

print(f'\n共 {total} 项，通过 {total - fails}，失败 {fails}')
raise SystemExit(1 if fails else 0)
