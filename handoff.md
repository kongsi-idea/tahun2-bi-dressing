# The Dressing Game · 交接

## 目前做到哪
功能与视觉已按 SPEC.md 实作完成，`test-e2e.py` 通过（见 `.playwright-output/test-output.txt`）。尚未：git init／commit／部署／进 Hub 登记。

## 目前状态
- 课本出处：待补（页码／单元）
- DSKP 对照：4.3.2（二年级英文「引导写作中准确拼写一定范围熟悉高频词」）**待核对官方 PDF**，不要写进 Hub 的 dskp-index
- 文件：`index.html` `styles.css` `app.js`；素材 `assets/*.webp`（由 `scripts/prep-assets.py` 从 `assets/src/*.png` 生成，可重跑）；音档 `audio/`（`gen-voice.py` 从 `content/voice-lines.json` 生成）
- 着色总览：`python3 scripts/tinted-overview.py` → `.playwright-output/tinted-18.png`
- 测试：`python3 test-e2e.py`（FAST=1 跳过随机转盘，约省 90 秒）

## 下一步
1. 老师试玩（尤其是平板触控、学校 Windows＋Chrome 的实体键盘）。
2. 课本出处、DSKP 核对后补进本档。
3. 老师点头后：git init、部署、Hub（kongsi-idea）上架登记（`tahun[1-6]-*` 工具已授权手动生产部署）。

## 注意事项
- 本机测试：`python3 -m http.server 8791 --bind 127.0.0.1`，开 http://127.0.0.1:8791（8765 常被 Hub 本机服务占用）
- 改了词表要同步改：`app.js` 的 RAW/TYPES、`content/voice-lines.json`，再跑 `gen-voice.py`。
- 卡比巴拉的衣服位置在 `app.js` 的 `SLOTS`（百分比）；改素材后要重跑 `prep-assets.py`，位置可能要微调。
- `window.__dressing.debugWear()` 只给截图用。

## 最后更新
2026-10-11
