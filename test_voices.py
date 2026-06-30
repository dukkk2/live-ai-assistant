"""
TTS 音色测试 - 轮流播放不同发音人
"""
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")

# 候选发音人
VOICES = [
    ("zh-CN-XiaoxiaoNeural",  "晓晓（温暖女声）"),
    ("zh-CN-XiaoyiNeural",    "晓伊（活泼可爱）"),
    ("zh-CN-YunxiNeural",     "云希（阳光男声）"),
    ("zh-CN-YunjianNeural",   "云健（沉稳男声）"),
]

TEST_TEXT = "蚌埠住了兄弟们 欢迎来到直播间 今天带大家打黑神话悟空"


async def test_voices():
    # 动态导入（避免 test 环境没有安装）
    sys.path.insert(0, str(Path(__file__).parent))
    from tts_engine import TTSEngine

    print("=" * 55)
    print("  TTS 音色试听")
    print("  测试文本: 「" + TEST_TEXT + "」")
    print("=" * 55)

    for i, (voice_id, voice_name) in enumerate(VOICES, 1):
        print(f"\n[{i}/{len(VOICES)}] 🎤 {voice_name} ({voice_id})")
        print(f"   正在合成并播放...")
        
        tts = TTSEngine(
            voice=voice_id,
            rate="+0%",
            volume="+0%",
        )
        
        try:
            success = await tts.speak(TEST_TEXT)
            if success:
                print(f"   ✅ 播放完成")
            else:
                print(f"   ❌ 播放失败")
        except Exception as e:
            print(f"   ❌ 出错: {e}")
        
        # 每个音色之间留 1 秒间隔
        if i < len(VOICES):
            await asyncio.sleep(1)

    print("\n" + "=" * 55)
    print("  试听结束！")
    print("  去 config.py 改 TTS_VOICE 选你喜欢的")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(test_voices())
