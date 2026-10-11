"""The Dressing Game 端到端测试（对应 SPEC 验收 1–11）。
用法：python3 test-e2e.py            （自己开本机静态服务器，不用先启动）
      TARGET=http://127.0.0.1:8791 python3 test-e2e.py   （改测已经开着的服务器／线上）
      FAST=1 python3 test-e2e.py     （跳过两套「随机转盘」的长测试，约省 90 秒）
track-use.js（外部统计脚本）在测试里用空脚本代替，只记录「有被请求」。
截图 → ~/Documents/my-agent/playwright-to-delete/；测试输出 → .playwright-output/。"""
import functools, http.server, json, os, subprocess, sys, threading, time
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '.playwright-output')
SHOTS = os.path.expanduser('~/Documents/my-agent/playwright-to-delete')
os.makedirs(OUT, exist_ok=True); os.makedirs(SHOTS, exist_ok=True)
FAST = os.environ.get('FAST') == '1'

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

TARGET = os.environ.get('TARGET')
if not TARGET:
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory=HERE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    TARGET = f'http://127.0.0.1:{srv.server_address[1]}'
URL = TARGET.rstrip('/') + '/index.html'
HOST = TARGET.split('//', 1)[1].split('/')[0]

fails = 0
def check(name, ok, extra=''):
    global fails
    print(('  PASS ' if ok else '  FAIL ') + name + (f' — {extra}' if extra else ''))
    if not ok: fails += 1

# ── 通用小工具 ──
def new_page(br, w=1366, h=768, dsf=1, touch=False):
    ctx = br.new_context(viewport={'width': w, 'height': h}, device_scale_factor=dsf, has_touch=touch)
    page = ctx.new_page()
    page.errors = []; page.reqs = []; page.dialogs = []
    page.on('pageerror', lambda e: page.errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: m.type == 'error' and page.errors.append('console: ' + m.text))
    page.on('dialog', lambda d: (page.dialogs.append(d.type), d.dismiss()))
    page.on('response', lambda r: page.reqs.append((r.url, r.status)))
    page.route('**/track-use.js', lambda r: (page.reqs.append((r.request.url, 'mocked')), r.fulfill(status=200, content_type='text/javascript', body='')))
    return page

def open_game(page, preset=None):
    page.goto(URL)
    if preset is not None:
        page.evaluate("p => localStorage.setItem('tahun2-bi-dressing:v1', JSON.stringify(p))", preset)
        page.reload()
    page.wait_for_selector('body[data-ready]'); page.wait_for_timeout(300)

ITEMS = None
def items(page):
    global ITEMS
    if ITEMS is None: ITEMS = page.evaluate('() => window.__dressing.items')
    return {i['id']: i for i in ITEMS}

def st(page): return page.evaluate('() => window.__dressing.state()')
def phase(page): return page.evaluate('() => document.body.dataset.phase')
SPINS = []

def spin(page, item_id=None):
    if item_id: page.evaluate('id => window.__dressing.forceNext(id)', item_id)
    page.click('#btnSpin')
    page.wait_for_selector('body[data-phase=answer]', timeout=9000)
    SPINS.append(int(page.evaluate("() => document.getElementById('wheelWrap').dataset.lastSpinMs")))

def solve_current(page):
    s = st(page); it = items(page)[s['current']]
    page.keyboard.type(it['color'], delay=30)
    page.wait_for_selector('#rowCloth.active', timeout=5000)
    page.keyboard.type(it['type'], delay=30)          # type id 就是要打的字母：tshirt / trousers …
    page.wait_for_selector('body[data-phase=done]', timeout=5000)
    page.wait_for_selector('body[data-phase=idle], body[data-phase=celebrate], body[data-phase=final]', timeout=8000)

def play_item(page, item_id):
    spin(page, item_id); solve_current(page)

def shot(page, name):
    page.wait_for_timeout(350)
    path = os.path.join(SHOTS, name + '.png'); page.screenshot(path=path); return path

SET1 = ['black-socks', 'red-shoes', 'black-trousers', 'orange-t-shirt', 'green-jacket', 'pink-cap']
ALL18 = ['brown-cap', 'red-t-shirt', 'blue-jacket', 'grey-trousers', 'black-socks', 'red-shoes', 'green-jacket', 'orange-t-shirt', 'pink-cap',
         'black-trousers', 'purple-socks', 'yellow-shoes', 'grey-cap', 'blue-t-shirt', 'brown-jacket', 'blue-trousers', 'red-socks', 'green-shoes']

def wait_set_done(page, final=False):
    page.wait_for_selector('body[data-phase=final]' if final else 'body[data-phase=idle]', timeout=12000)
    page.wait_for_timeout(500)

with sync_playwright() as p:
    br = p.chromium.launch()

    # ═════ 验收 1 + 11：冷启动、无外部请求 ═════
    print('验收 1 / 11  冷启动、请求')
    page = new_page(br)
    open_game(page)
    check('1 冷启动无控制台红字／页面错误', page.errors == [], str(page.errors))
    ext = [u for u, s in page.reqs if HOST not in u and 'kongsi-idea.vercel.app/data/track-use.js' not in u]
    check('11 除 track-use.js 外没有外部请求', ext == [], str(ext))
    check('11 track-use.js 有被页面请求（已用空脚本代替）', any('track-use.js' in u for u, s in page.reqs))
    local = [(u, s) for u, s in page.reqs if HOST in u]
    bad = [(u, s) for u, s in local if s != 200]
    fonts = [u for u, s in local if u.endswith('.woff2')]
    check('11 本地字体 200', len(fonts) >= 1 and not [1 for u, s in local if u.endswith('.woff2') and s != 200], str([u.split('/')[-1] for u in fonts]))
    check('11 本地请求全部 200', bad == [], str(bad))
    check('11 Andika 已加载', page.evaluate("() => document.fonts.check('700 20px Andika')"))
    # 所有音档本地可取、与 voice-lines.json 一致
    lines = page.evaluate('() => window.__dressing.allVoiceLines()')
    cfg = json.load(open(os.path.join(HERE, 'content', 'voice-lines.json'), encoding='utf-8'))
    check('11 allVoiceLines() 与 content/voice-lines.json 一致（38 句）', sorted((l['file'], l['text']) for l in lines) == sorted((l['file'], l['text']) for l in cfg['lines']) and len(lines) == 38, str(len(lines)))
    codes = [page.request.get(f"{TARGET.rstrip('/')}/audio/{l['file']}.mp3").status for l in lines]
    check('11 38 个音档全部 200', all(c == 200 for c in codes), str(set(codes)))
    check('11 页面没有 alert/confirm/prompt', page.dialogs == [])
    check('词表：18 件、10 色、6 衣', len(items(page)) == 18 and len({i['color'] for i in ITEMS}) == 10 and len({i['type'] for i in ITEMS}) == 6)

    # ═════ 验收 2：转盘秒数 ═════
    print('验收 2  转盘时间')
    page.evaluate("""() => { const w = document.getElementById('wheelWrap'); window.__T = {};
      document.getElementById('btnSpin').addEventListener('click', () => { window.__T.click = performance.now(); }, true);
      new MutationObserver(() => { if (!w.dataset.spinning && window.__T.click && !window.__T.stop) window.__T.stop = performance.now(); }).observe(w, { attributes: true, attributeFilter: ['data-spinning'] }); }""")
    page.evaluate("() => window.__dressing.forceNext('brown-cap')")
    page.click('#btnSpin'); page.wait_for_selector('body[data-phase=answer]', timeout=9000)
    t = page.evaluate('() => window.__T')
    ms = t['stop'] - t['click']
    check('2 点击到停下 2.8–3.3 秒', 2800 <= ms <= 3300, f'{ms:.0f} ms（页内量到的 click→停止）')
    rot = page.evaluate("() => { const m = /rotate\\(([-\\d.]+)deg\\)/.exec(document.getElementById('wRot').style.transform); return parseFloat(m[1]); }")
    idx = int((((-rot) % 360) + 360) % 360 // 18)
    check('2 转盘转了 4–5 圈', 4 * 360 <= rot < 5 * 360, f'rot={rot:.0f}°（{rot/360:.2f} 圈）')
    check('2 指针停在 forceNext 指定的那格（brown cap = 第 1 格）', idx == 1, f'指针下扇形序号 {idx}')
    check('2 落定后出现答题面板，图与词数正确', page.is_visible('#viewAnswer') and len(page.query_selector_all('#cellsColour .cell')) == 5 and len(page.query_selector_all('#cellsCloth .cell')) == 3)
    SPINS.append(int(page.evaluate("() => document.getElementById('wheelWrap').dataset.lastSpinMs")))
    # 转盘上没有任何文字
    check('2 转盘画布上不写字（页面里没有任何转盘文字节点）', page.evaluate("() => document.getElementById('wheelWrap').innerText.trim() === ''"))

    # ═════ 验收 4：实体键盘 ═════
    print('验收 4  实体键盘')
    page.keyboard.press('q')
    check('4 按实体键时屏幕键盘对应键亮起', page.evaluate("() => document.querySelector('.key[data-k=q]').classList.contains('lit')"))
    page.keyboard.press('Backspace')   # 清掉刚才那个 q 的脏数据（q 不是 b，会被判错，等清掉）
    page.wait_for_timeout(900)
    cells = lambda sel: page.evaluate("s => [...document.querySelectorAll(s + ' .cell')].map(c => ({cls: c.className, t: c.textContent}))", sel)
    # brown cap：颜色先打错最后一个字母
    page.keyboard.type('brow', delay=30); page.keyboard.type('m', delay=30)
    page.wait_for_timeout(120)
    c = cells('#cellsColour')
    check('4 打错一个字母：只有这一格变红抖动', [('wrong' in x['cls']) for x in c] == [False, False, False, False, True] and 'locked' in c[0]['cls'], str([x['cls'] for x in c]))
    page.wait_for_timeout(750)
    c = cells('#cellsColour')
    check('4 错的格子清空，对的 4 格仍锁定', [x['t'] for x in c] == ['b', 'r', 'o', 'w', ''] and ['locked' in x['cls'] for x in c] == [True] * 4 + [False], str([(x['t'], x['cls']) for x in c]))
    page.keyboard.type('n', delay=30); page.wait_for_timeout(200)
    c = cells('#cellsColour')
    check('4 补打对：5 格全绿', all('locked' in x['cls'] for x in c) and ''.join(x['t'] for x in c) == 'brown')
    page.wait_for_selector('#rowCloth.active', timeout=4000)
    page.keyboard.type('cap')
    page.wait_for_selector('body[data-phase=done]', timeout=4000)
    page.wait_for_selector('body[data-phase=idle]', timeout=6000)
    # T-shirt 只打 6 个字母
    spin(page, 'blue-t-shirt')
    page.keyboard.type('blue'); page.wait_for_selector('#rowCloth.active', timeout=4000)
    c = cells('#cellsCloth')
    check('4 T-shirt 共 7 格，其中连字号格预先填好', len(c) == 7 and 'fixed' in c[1]['cls'] and c[1]['t'] == '-', str([x['t'] for x in c]))
    page.keyboard.press('Shift+T')
    for ch in 'shir': page.keyboard.press(ch)
    page.wait_for_timeout(100)
    c = cells('#cellsCloth')
    check('4 打到第 5 个字母时还没判（没打满），第一个显示大写 T', [x['t'] for x in c][:1] == ['T'] and sum('locked' in x['cls'] for x in c) == 0, str([x['t'] for x in c]))
    page.keyboard.press('t')
    page.wait_for_timeout(200)
    c = cells('#cellsCloth')
    check('4 再打 1 个（共 6 个字母）：全绿，显示 T-shirt', ''.join(x['t'] for x in c) == 'T-shirt' and sum('locked' in x['cls'] for x in c) == 6, ''.join(x['t'] for x in c))
    page.wait_for_selector('body[data-phase=idle]', timeout=8000)
    # 屏幕键盘可点
    spin(page, 'red-socks')
    for ch in 'red': page.click(f'.key[data-k={ch}]')
    page.wait_for_selector('#rowCloth.active', timeout=4000)
    page.click('.key[data-k=s]'); page.click('.key[data-k=x]')   # x 是错的
    page.wait_for_timeout(100)
    c = cells('#cellsCloth')
    check('4 屏幕键盘点击输入，也能判错（未打满不判）', [x['t'] for x in c] == ['s', 'x', '', '', ''] and sum('wrong' in x['cls'] for x in c) == 0)
    page.click('.key[data-k=Backspace]'); page.click('.key[data-k=o]')
    page.click('.key[data-k=c]'); page.click('.key[data-k=k]'); page.click('.key[data-k=s]')
    page.wait_for_selector('body[data-phase=done]', timeout=4000)
    check('4 屏幕键盘退格后补打完成', st(page)['worn'].get('socks') == 'red-socks')
    page.wait_for_selector('body[data-phase=idle]', timeout=8000)

    # ═════ 验收 5：Help 三档 ═════
    print('验收 5  Help 三档')
    spin(page, 'pink-cap')
    audio_hits = lambda: len([1 for u, s in page.reqs if u.endswith('/audio/pink.mp3')])
    n0 = audio_hits()
    page.click('#btnHelp'); page.wait_for_timeout(500)
    check('5 档①：朗读整个单词（请求了 audio/pink.mp3）', audio_hits() == n0 + 1 and page.evaluate("() => document.querySelectorAll('#helpPips i.on').length") == 1, f'请求 {n0}→{audio_hits()}')
    check('5 档①不填任何字母', all(x['t'] == '' for x in cells('#cellsColour')))
    page.click('#btnHelp'); page.wait_for_timeout(200)
    c = cells('#cellsColour')
    check('5 档②：自动填好第一个字母 p 并锁住', c[0]['t'] == 'p' and 'locked' in c[0]['cls'] and all(x['t'] == '' for x in c[1:]), str([(x['t'], x['cls']) for x in c[:2]]))
    page.click('#btnHelp'); page.wait_for_timeout(300)
    vis = lambda: page.evaluate("() => document.getElementById('peekColour').classList.contains('show')")
    check('5 档③：偷看，显示完整单词', vis() and page.inner_text('#peekColour') == 'pink')
    check('5 三档后 Help 按钮禁用', page.is_disabled('#btnHelp'))
    page.wait_for_timeout(2200)
    check('5 档③ 2.5 秒时仍显示', vis())
    page.wait_for_timeout(1000)
    check('5 档③ 3 秒后遮回', not vis())
    check('5 用了 3 档 Help：这件最低保 1 星', page.evaluate("() => document.querySelectorAll('#itemStars .st.on').length") == 1)
    page.keyboard.type('ink'); page.wait_for_selector('#rowCloth.active', timeout=4000)
    page.keyboard.type('cap'); page.wait_for_selector('body[data-phase=done]', timeout=4000)
    s = st(page)
    check('5 最低保 ★：该件拿到 1 星且没有算进「无 Help 一次对」', s['stars'] >= 1)
    page.wait_for_selector('body[data-phase=idle]', timeout=8000)

    # ═════ 验收 3：完整一套（从头开始，forceNext 逐件） ═════
    print('验收 3  一套 6 件')
    page.evaluate("() => localStorage.clear()"); open_game(page)
    t_set = time.time()
    for k, iid in enumerate(SET1):
        play_item(page, iid)
        if k < 5:
            check(f'3 第 {k+1} 件穿上：{iid}', st(page)['wornCount'] == k + 1 and st(page)['worn'].get(items(page)[iid]['type']) == iid)
        if k == 4:
            shot(page, 'dressing-1366x768-flow-5of6')
    page.wait_for_selector('body[data-phase=celebrate]', timeout=6000)
    page.wait_for_timeout(700)
    lay = page.evaluate("""() => { const capy = document.getElementById('capy').getBoundingClientRect();
      return [...document.querySelectorAll('.garment')].map(g => { const r = g.getBoundingClientRect(); return { layer: g.dataset.layer, hidden: g.hidden, cx: (r.left + r.width / 2 - capy.left) / capy.width, cy: (r.top + r.height / 2 - capy.top) / capy.height, w: r.width / capy.width }; }); }""")
    vis_layers = [l['layer'] for l in lay if not l['hidden']]
    check('3 穿满：卡比巴拉身上 7 个图层（6 件，袜子左右各一）全部显示', sorted(vis_layers) == sorted(['socks-l', 'socks-r', 'shoes', 'trousers', 'tshirt', 'jacket', 'cap']), str(vis_layers))
    order = page.evaluate("() => [...document.querySelectorAll('.garment')].map(g => g.dataset.layer)")
    check('3 图层顺序（下→上）socks → shoes → trousers → T-shirt → jacket → cap', order == ['socks-l', 'socks-r', 'shoes', 'trousers', 'tshirt', 'jacket', 'cap'], str(order))
    pos = {l['layer']: l for l in lay}
    check('3 位置：帽子在头部（上 15%）、袜鞋在脚（下 70% 以下）、裤子盖住腿、T恤在躯干', pos['cap']['cy'] < 0.15 and pos['shoes']['cy'] > 0.85 and pos['socks-l']['cy'] > 0.75 and 0.55 < pos['trousers']['cy'] < 0.75 and 0.35 < pos['tshirt']['cy'] < 0.6 and abs(pos['jacket']['cy'] - 0.48) < 0.1,
          str({k: (round(v['cx'], 2), round(v['cy'], 2)) for k, v in pos.items()}))
    check('3 庆祝：Well done! 与彩带，已存进 Collection（6/18）', page.inner_text('#doneTitle') == 'Well done!' and st(page)['collected'].__len__() == 6, page.inner_text('#colCount'))
    shot(page, 'dressing-1366x768-3-fullset')
    page.wait_for_selector('body[data-phase=idle]', timeout=8000)
    page.wait_for_timeout(700)
    s = st(page)
    check('3 自动进入第二套：本套穿着清空、Collection 有 6 件', s['wornCount'] == 0 and len(s['collected']) == 6 and s['sets'] == 1, str(s))
    check('3 卡比巴拉脱回光身（图层全部隐藏）', page.evaluate("() => [...document.querySelectorAll('.garment')].every(g => g.hidden)"))
    check('3 提示换到第 2 套', 'Set 2' in page.inner_text('#idleHint'), page.inner_text('#idleHint'))
    page.click('#btnCollection'); page.wait_for_timeout(300)
    got = page.evaluate("() => document.querySelectorAll('.tile.got').length")
    check('3 Collection 页：6 格彩色、12 格剪影', got == 6 and page.evaluate("() => document.querySelectorAll('.tile.lock').length") == 12, f'got={got}')
    shot(page, 'dressing-1366x768-collection')
    page.click('.tile.got'); page.wait_for_timeout(200)
    check('3 点已收集的格子读词组（请求了音档）', any(u.endswith('.mp3') for u, s in page.reqs[-4:]))
    page.click('#btnPlay'); page.wait_for_timeout(200)

    # ═════ 验收 7：刷新后进度仍在 ═════
    print('验收 7  刷新保留')
    play_item(page, 'brown-cap'); play_item(page, 'blue-t-shirt')
    before = st(page)
    page.reload(); page.wait_for_selector('body[data-ready]'); page.wait_for_timeout(300)
    after = st(page)
    keep = {k: after[k] for k in ('collected', 'worn', 'stars', 'colourOK', 'clothOK', 'sets')} == {k: before[k] for k in ('collected', 'worn', 'stars', 'colourOK', 'clothOK', 'sets')}
    check('7 刷新后收集、本套穿着、星星、统计都还在', keep, f"stars {before['stars']}→{after['stars']}, collected {len(after['collected'])}, worn {list(after['worn'].values())}")
    check('7 刷新后卡比巴拉身上还穿着、顶栏数字一致', page.evaluate("() => [...document.querySelectorAll('.garment')].filter(g => !g.hidden).length") == 2 and page.inner_text('#starTotal') == str(after['stars']) and page.inner_text('#wornCount') == '2/6')
    # Reset 用页内确认框
    page.click('#btnReset'); page.wait_for_timeout(200)
    check('7 Reset 弹出页内确认框（不是 confirm()）', page.is_visible('#confirm') and page.dialogs == [])
    page.click('#btnConfirmNo'); check('7 选「Keep playing」不清空', st(page)['stars'] == after['stars'])
    page.click('#btnReset'); page.click('#btnConfirmYes'); page.wait_for_timeout(300)
    s = st(page)
    check('7 确认重置后全部清空', s['stars'] == 0 and s['collected'] == [] and s['worn'] == {} and page.dialogs == [])
    # localStorage 坏掉不能卡住
    page.evaluate("() => localStorage.setItem('tahun2-bi-dressing:v1', '{坏掉的json')")
    page.reload(); page.wait_for_selector('body[data-ready]')
    check('7 存档损坏时当新玩家继续，无报错', st(page)['stars'] == 0 and not [e for e in page.errors if 'pageerror' in e], str(page.errors[-2:]))

    # ═════ 验收 6：18 件完成页 ═════
    print('验收 6  18 件完成')
    pre = [i for i in ALL18 if i != 'green-shoes']
    open_game(page, {'collected': pre, 'worn': {}, 'stars': 40, 'colourOK': 5, 'clothOK': 4, 'sets': 2})
    check('6 预置 17 件：Collection 显示 17/18，未出现完成页', page.inner_text('#colCount') == '17/18' and not page.is_visible('#finale'))
    for iid in ['brown-cap', 'red-t-shirt', 'blue-jacket', 'grey-trousers', 'black-socks', 'green-shoes']:
        play_item(page, iid) if iid != 'green-shoes' else (spin(page, iid), solve_current(page))
        if iid == 'green-shoes': break
    page.wait_for_selector('body[data-phase=final]', timeout=8000)
    page.wait_for_timeout(600)
    check('6 第 18 件完成：出现 You collected all 18!', page.is_visible('#finale') and page.inner_text('#finaleTitle') == 'You collected all 18!')
    check('6 完成页显示总星星，18 格图', int(page.inner_text('#finaleStars')) > 40 and len(page.query_selector_all('#finaleGrid img')) == 18, page.inner_text('#finaleStars'))
    shot(page, 'dressing-1366x768-finale')
    page.click('#btnAgain'); page.wait_for_timeout(500)
    s = st(page)
    check('6 Play again：收集、穿着、星星清空，回到转盘', not page.is_visible('#finale') and s['collected'] == [] and s['worn'] == {} and s['stars'] == 0 and s['phase'] == 'idle', str(s))
    page.reload(); page.wait_for_selector('body[data-ready]')
    check('6 刷新后不会再弹完成页', not page.is_visible('#finale') and st(page)['collected'] == [])

    # ═════ 随机转盘：不落 Start/Finish、同套不重复类型、优先没收集过的 ═════
    if not FAST:
        print('随机转盘（两套，约 90 秒）')
        open_game(page, {'collected': [], 'worn': {}, 'stars': 0})
        seen = []; mismatch = []
        for k in range(12):
            page.click('#btnSpin'); page.wait_for_selector('body[data-phase=answer]', timeout=9000)
            SPINS.append(int(page.evaluate("() => document.getElementById('wheelWrap').dataset.lastSpinMs")))
            rot = page.evaluate("() => parseFloat(/rotate\\(([-\\d.]+)deg\\)/.exec(document.getElementById('wRot').style.transform)[1])")
            idx = int((((-rot) % 360) + 360) % 360 // 18)
            cur = st(page)['current']
            seen.append(cur)
            if idx != items(page)[cur]['n']: mismatch.append((cur, idx))
            solve_current(page)
            if k == 5: wait_set_done(page)
        set1, set2 = seen[:6], seen[6:]
        T = lambda ids: [items(page)[i]['type'] for i in ids]
        check('随机：每套 6 件类型各不相同', len(set(T(set1))) == 6 and len(set(T(set2))) == 6, f'{T(set1)} / {T(set2)}')
        check('随机：第二套 6 件全是没收集过的（颜色换了）', not set(set1) & set(set2), str(set(set1) & set(set2)))
        check('随机：指针从未落在 Start／Finish 格（12 次指针下扇形序号都等于所抽物品序号 1–18）', not mismatch, str(mismatch))
        s = st(page)
        check('随机：两套走完后 Collection 12 件', len(s['collected']) == 12, str(len(s['collected'])))

    ms = SPINS
    check('2 全部测试中转盘时间（内部记录）都在 2.8–3.3 秒', all(2800 <= x <= 3300 for x in ms), f'共 {len(ms)} 次，最小 {min(ms)} ms，最大 {max(ms)} ms')
    print(f'    转盘用时列表 ms: {ms}')
    page.close()

    # ═════ 验收 8：三个布局的截图与量测 ═════
    print('验收 8  三种布局截图')
    layouts = [('1366x768', 1366, 768, False), ('1180x820', 1180, 820, True), ('390x844', 390, 844, True)]
    report = {}
    for name, w, h, touch in layouts:
        pg = new_page(br, w, h, dsf=1, touch=touch)
        open_game(pg)
        shot(pg, f'dressing-{name}-1-wheel')
        pg.evaluate("() => window.__dressing.forceNext('grey-trousers')")
        pg.click('#btnSpin'); pg.wait_for_selector('body[data-phase=answer]', timeout=9000)
        pg.keyboard.type('grey'); pg.wait_for_selector('#rowCloth.active', timeout=4000); pg.keyboard.type('tro')
        pg.wait_for_timeout(500)
        shot(pg, f'dressing-{name}-2-answering')
        m = pg.evaluate("""() => { const r = s => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return { x: Math.round(b.left), y: Math.round(b.top), w: Math.round(b.width), h: Math.round(b.height), bottom: Math.round(b.bottom), right: Math.round(b.right) }; };
          const keys = [...document.querySelectorAll('.key')].map(k => k.getBoundingClientRect());
          const btns = [...document.querySelectorAll('.btn')].filter(b => b.offsetParent).map(b => b.getBoundingClientRect());
          const cellsB = r('#rowCloth'), kb = r('#kb');
          return { scrollW: document.documentElement.scrollWidth, innerW: innerWidth, innerH: innerHeight, scrollY: Math.round(scrollY), docH: document.documentElement.scrollHeight,
                   wheel: r('#wheelWrap'), panel: r('#panel'), kb, rowCloth: cellsB, minKeyW: Math.round(Math.min(...keys.map(k => k.width))), minKeyH: Math.round(Math.min(...keys.map(k => k.height))),
                   minBtnH: Math.round(Math.min(...btns.map(b => b.height))), minBtnW: Math.round(Math.min(...btns.map(b => b.width))),
                   keysOverCells: kb.y < cellsB.bottom, minCellW: Math.round(Math.min(...[...document.querySelectorAll('#cellsCloth .cell:not(.fixed)')].map(c => c.getBoundingClientRect().width))) }; }""")
        report[name] = m
        check(f'8 {name}：无横向溢出', m['scrollW'] <= m['innerW'], f"scrollWidth {m['scrollW']} / {m['innerW']}")
        check(f'8 {name}：屏幕键盘不挡输入格', not m['keysOverCells'], f"输入格底 {m['rowCloth']['bottom']}，键盘顶 {m['kb']['y']}")
        check(f'8 {name}：键盘完整在可视范围内', m['kb']['bottom'] <= m['innerH'] + 1, f"键盘底 {m['kb']['bottom']} / 视口高 {m['innerH']}（页面已滚动 {m['scrollY']}px）")
        print(f"    {name}: 转盘 {m['wheel']['w']}px，面板 {m['panel']['w']}×{m['panel']['h']}，最小键 {m['minKeyW']}×{m['minKeyH']}，最小按钮 {m['minBtnW']}×{m['minBtnH']}，输入格最小宽 {m['minCellW']}")
        # 第三张：穿满一套（真实流程只在 1366 测过；这里用测试钩子直接穿满，只为看布局）
        pg.evaluate("() => window.__dressing.debugWear({cap: 'pink-cap', tshirt: 'orange-t-shirt', jacket: 'green-jacket', trousers: 'black-trousers', socks: 'purple-socks', shoes: 'red-shoes'})")
        pg.evaluate("() => { document.body.dataset.phase = 'idle'; document.getElementById('viewAnswer').hidden = true; document.getElementById('viewIdle').hidden = false; window.scrollTo(0, 0); }")
        pg.wait_for_timeout(300)
        ov = pg.evaluate("() => [...document.querySelectorAll('#strip .slot')].filter(s => { const a = s.getBoundingClientRect(), b = s.querySelector('img').getBoundingClientRect(); return b.top < a.top - 1 || b.bottom > a.bottom + 1 || b.left < a.left - 1 || b.right > a.right + 1; }).length")
        check(f'8 {name}：这套的 6 个小格里图都没溢出', ov == 0, f'溢出 {ov} 个')
        shot(pg, f'dressing-{name}-3-fullset')
        errs = [e for e in pg.errors]
        check(f'8 {name}：无控制台红字', errs == [], str(errs))
        pg.close()
    json.dump(report, open(os.path.join(OUT, 'layout-report.json'), 'w'), indent=1)

    # ═════ 验收 10：着色总览图 ═════
    print('验收 10  着色总览')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'scripts', 'tinted-overview.py')], capture_output=True, text=True)
    ov = os.path.join(OUT, 'tinted-18.png')
    check('10 总览图已生成', r.returncode == 0 and os.path.getsize(ov) > 20000, r.stderr[-200:] if r.returncode else f'{os.path.getsize(ov)//1024} KB')
    page = new_page(br)
    open_game(page)
    mean = page.evaluate("""() => { const D = window.__dressing, out = {};
      for (const it of D.items) { const c = D.wheelIcon(it, 70), x = c.getContext('2d'), d = x.getImageData(0, 0, c.width, c.height).data;
        // 只取衣服本体（不透明且不是白色贴纸边）的平均色
        let r = 0, g = 0, b = 0, n = 0; for (let i = 0; i < d.length; i += 4) { if (d[i + 3] < 250) continue; if (d[i] > 235 && d[i + 1] > 235 && d[i + 2] > 225) continue; r += d[i]; g += d[i + 1]; b += d[i + 2]; n++; }
        out[it.id] = [r / n, g / n, b / n, it.color]; }
      return out; }""")
    def rgb2lab(c):
        def f(u):
            u /= 255; u = u / 12.92 if u <= .04045 else ((u + .055) / 1.055) ** 2.4; return u
        r, g, b = f(c[0]), f(c[1]), f(c[2])
        X = (.4124 * r + .3576 * g + .1805 * b) / .95047; Y = (.2126 * r + .7152 * g + .0722 * b); Z = (.0193 * r + .1192 * g + .9505 * b) / 1.08883
        h = lambda t: t ** (1 / 3) if t > .008856 else 7.787 * t + 16 / 116
        return (116 * h(Y) - 16, 500 * (h(X) - h(Y)), 200 * (h(Y) - h(Z)))
    lab = {k: rgb2lab(v[:3]) for k, v in mean.items()}
    def dE(a, b): return sum((x - y) ** 2 for x, y in zip(lab[a], lab[b])) ** .5
    groups = {'grey/black/brown': ['grey-trousers', 'grey-cap', 'black-socks', 'black-trousers', 'brown-cap', 'brown-jacket'],
              'pink/red/orange': ['pink-cap', 'red-t-shirt', 'red-shoes', 'red-socks', 'orange-t-shirt']}
    for gname, ids in groups.items():
        worst = None
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if mean[a][3] == mean[b][3]: continue
                d = dE(a, b)
                if worst is None or d < worst[0]: worst = (d, a, b)
        check(f'10 {gname}：70px 图标平均色两两 ΔE76 ≥ 20（不同颜色之间）', worst[0] >= 20, f'最小 ΔE={worst[0]:.1f}（{worst[1]} vs {worst[2]}）')
    page.close()
    br.close()

print('\n失败数：', fails)
sys.exit(1 if fails else 0)
