# The Dressing Game · 交接

## ⏯️ 目前做到哪
v1.0 已上线 https://tahun2-bi-dressing.vercel.app ，Hub 已上架（2026-10-11）。push main 即自动部署。

## 🚦 目前状态
- 玩法：课本转盘（3 秒）→ 拼颜色词 → 拼衣服词 → 卡比巴拉穿上；一套 6 件，18 件全收集。规格见 `SPEC.md`。
- 测试：`FAST=1 python3 test-e2e.py`（81 项通过）。
- 课本出处：页码待补。DSKP：BI 4.3.2，未核对官方 PDF，未进 dskp-index。

## ➡️ 下一步
1. 老师本机试玩反馈（声音、实体键盘手感、3 秒转盘节奏）。
2. 手机直立屏幕键盘键宽 34px（<44px）；收集页深色模式没看过。
3. 长裤贴在卡比巴拉身上腿部较短，必要时用生图重画穿长裤的底图。

## ⚠️ 注意事项
- 衣服是白底图（`assets/src/`），`scripts/prep-assets.py` 去底，运行时着色；改素材后重跑。
- 音档：改 `content/voice-lines.json` 后跑 `gen-voice.py`。
- 本机测试：`python3 -m http.server 8791 --bind 127.0.0.1`

## 🕐 最后更新
2026-10-11 · Claude Sonnet 5.5 @ Mac · Git：✅ 已推（工具仓库 `cd065bb` 之后无新变动；Hub `aed0358`）

## 💰 开发用量与费用（2026-10-11）
首次开发上线：116 轮，输入 242、输出约 5.5 万（下限）、缓存写约 107 万、缓存读约 1,787 万 token。**实际花费 US$8.24**（Claude Code 状态栏，API 等价金额，老师走订阅额度）；脚本估算 $6.60 偏低。逐笔与总花费见 `../COST-LOG.md`，以后每次调整都要再记一笔。
