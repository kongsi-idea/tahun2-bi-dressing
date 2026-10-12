# The Dressing Game · 交接

## ⏯️ 目前做到哪
**v2.0（2026-10-13）**：照老师的 Gemini 原版概念重做玩法（第一版概念不对，老师说「太怪、原版比较好」）。线上 https://tahun2-bi-dressing.vercel.app ，push main 即自动部署。规格见 `SPEC.md` 顶部 12 条（**改动前先对照**）。

## 🚦 目前状态
- 玩法：左转盘 5／右收藏 7 同高一屏；点转盘就转 → 拼颜色 → 拼衣服 → 解锁进收藏（一件件，未拼写 Locked）。字母块 On／Off 学生自选、不扣星；星星每件 +5；全小写只有 T-shirt 的 T 大写；默认不读音（学生自己点喇叭，拼完读一次）。
- 卡比巴拉：一整套（课本每 6 格＝一套，共 3 套）凑满时出现整图 `assets/outfit-1/2/3.webp`（cx-draw 生成，原稿在 `assets/src/outfits/`，未入 git；`scripts/prep-outfits.py` 去底转 webp）。
- 测试：`FAST=1 python3 test-e2e.py`（126 项通过）；不加 FAST 约多 90 秒（实玩 18 件）。

## ➡️ 下一步
1. 老师试玩 v2，重点看：①「电脑版 keyboard layout 不对」到底指哪里（现为 qwerty 三排小写＋Shift＋退格，未确认，请他给截图）②拼完整件会自动读一次 phrase——若他要「完全只在点了才读」，改 `finishItem` 里的 `say(it.id)` 一行。
2. 手机直立收藏是 3 列×6 排（窄屏放不下 6 列），电脑／平板是 6×3。
3. 课本页码待补；DSKP 4.3.2 未核对官方 PDF。
4. `assets/capybara.webp`、`socks-l/r.webp` 已不用（旧穿衣系统），可搬去 `~/Documents/待删除/`。

## ⚠️ 注意事项
- 老师否决了「卡比巴拉分层叠图／真的穿上」（对位难、屏幕跑位）——别再提；只做整套整图。
- 程序不得自己滚动页面（老师点名「荧幕摇晃」）。
- Documents 在 iCloud 会逐出文件：读不出来先 `brctl download <绝对路径>`（git、app.js 都碰过）。
- 本机测试：`python3 -m http.server 8791 --bind 127.0.0.1`

## 🕐 最后更新
2026-10-13 · Claude Sonnet 5.5 @ Mac · Git：见下方提交

## 💰 开发用量与费用
首次开发（10-11）实际 US$8.24。v2 改版（10-13）未取得状态栏金额，待补进 `../COST-LOG.md`。
