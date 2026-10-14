# The Dressing Game（tahun2-bi-dressing）

Tahun 2 英文 Get Dressed! 单元拼写游戏。线上 https://tahun2-bi-dressing.vercel.app ，push main 即自动部署。规格见 `SPEC.md`，现况见 `handoff.md`，共用规则见 `../agents.md`。纯静态（无 build），界面全英文，不接班级名单，进度只存本机。

## 关键决定（代码看不出来的）
- **以老师的 Gemini 原版概念为准（2026-10-13 改版，细节见 `SPEC.md` 顶部）**：纯拼写、点转盘就转、左 5／右 7 同高、收藏一件件解锁（未拼写 Locked）、字母块自选且**不扣星**、星星每件固定 +5、全小写只有 T-shirt 的 T 大写、默认不读音（学生自己点喇叭）。第一版踩雷的原因：没读老师聊天记录、自己假设了 Help 扣星与读音。**以后改动前先对照 SPEC 顶部 12 条。**
- **卡比巴拉＝奖励画面，不是穿衣系统**：课本转盘 18 件每 6 件刚好是一整套 → 3 套 → 3 张整图（`assets/outfit-N.webp`）。老师否决了「分层叠图、运行时真的穿上」（对位生图难、不同屏幕跑位）。
- **卡比巴拉也否决了「穿搭组合生图」「运行时着色换装」**：组合爆炸、技术工作对老师开工具不实际；最终只要 3 张整套图（颜色固定，不可调）。2026-10-13 老师拍板。
- **转盘不改成翻牌**：老师要转盘，课本就是转盘；转 3 秒（`SPIN_MS`）。转盘只画图不写字，学生自己认颜色。Start／Finish 两格只作装饰，指针永不落在上面。
- **判定整词打满才检查**，错的格子红抖清空、对的锁绿（不做逐字母即时拒绝，避免靠试错猜）。
- **衣服是生图白底图运行时着色**（`assets/src/` → `scripts/prep-assets.py` 去底 → canvas 着色），颜色才一定准。
- **视觉**：「试衣间舞台」（STYLES.md 07 实体教具），字体 Andika（识字用单层 a/g）。
- **音档**：edge-tts `en-GB-SoniaNeural` −10%，改词表后跑 `gen-voice.py`。
- **iCloud**：Documents 会逐出文件，读不出来（Errno 60）先 `brctl download <绝对路径>`。
- **界面、Hub 缩略图一律写 Year 2，不写 Tahun 2**（2026-10-14 老师纠正）：英文工具对学生是英文环境。Hub 的缩略图是截图，**每次改版都要整组重拍**（页脚、玩法会过期；10-14 就因为只换了封面，老师还看到旧图的 Tahun）。封面 `v1-0-cover` 的牌子字是在生图上用 Andika 补写的，不是重新生图。
- **夹克内里不抠空**（10-14 老师：「jacket 里部变透明，应该是保留颜色」）：`prep-assets.py` 的 hollowJacket 已关；原来抠空是为了让旧穿衣系统露出里面的 T 恤，该系统已废。
- **Hub（kongsi-idea）推送后不会自动部署**，要手动 `vercel --prod`（授权名单内）；改完要拿线上文件 md5 对本地，别只看 push 成功。
- 范围外：班级名单、排行榜、Supabase、任何 API、`alert/confirm`、Help 分档、扣星。
- DSKP 对照 BI 4.3.2 **未核对官方 PDF**，不进 Hub 的 dskp-index；课本页码待补。
- **新域名 DNS 坑**：`*.vercel.app` 新项目域名刚建时，家用路由器 DNS 可能缓存「查无此域名」，Safari 报 Can't Find the Server，但网站其实在线（8.8.8.8 可解析）。先清 DNS 缓存／换流量／等，别误判成部署失败。
