"""生成预录人声：content/voice-lines.json → audio/<file>.mp3（edge-tts，英式女声 Sonia，rate -10%）。
用法：python3 gen-voice.py          已存在的档不重录；要重录就先把旧档移到 ~/Documents/待删除/。
改了词表要同步改 content/voice-lines.json，并确认 app.js 的 allVoiceLines() 与它一致（test-e2e.py 会比对）。"""
import asyncio, json, os
import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, 'audio')
os.makedirs(AUDIO, exist_ok=True)
cfg = json.load(open(os.path.join(HERE, 'content', 'voice-lines.json'), encoding='utf-8'))

async def one(sem, l):
    out = os.path.join(AUDIO, l['file'] + '.mp3')
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return 'skip'
    async with sem:
        err = None
        for _ in range(3):
            try:
                await edge_tts.Communicate(l['text'], cfg['voice'], rate=cfg['rate']).save(out)
                return 'new'
            except Exception as e:  # 网络偶尔失败，重试
                err = e
                await asyncio.sleep(1.5)
        raise err

async def main():
    sem = asyncio.Semaphore(5)
    res = await asyncio.gather(*(one(sem, l) for l in cfg['lines']))
    print(f"句子 {len(cfg['lines'])} 句：新录 {res.count('new')}，已存在 {res.count('skip')}")

asyncio.run(main())
want = {l['file'] for l in cfg['lines']}
extra = sorted(n for n in os.listdir(AUDIO) if n.endswith('.mp3') and n[:-4] not in want)
if extra:
    print('audio/ 里有不再使用的音档：', extra)
