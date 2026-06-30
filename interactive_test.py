"""
互动测试 - 手动输入弹幕，测试完整 AI 回复 + 语音
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

# 加路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "CosyVoice"))
sys.path.insert(0, str(BASE_DIR / "CosyVoice/third_party/Matcha-TTS"))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("test")

from generator import ReplyGenerator
from tts_engine import TTSEngine


async def main():
    print("=" * 50)
    print("  B站直播 AI 互动助手 - 离线测试")
    print("  输入弹幕看 AI 回复并语音播放")
    print("  输入 q 退出")
    print("=" * 50)

    # 加载 LLM
    print("\n[1/3] 加载 LLM...")
    gen = ReplyGenerator()
    profile = json.loads(open(BASE_DIR / "style_profile.json").read())
    examples = json.loads(open(BASE_DIR / "data/history_examples.json").read())
    print("  ✅ LLM 就绪")

    # 预热 LLM（第一次慢，先跑一条）
    print("\n[2/3] 预热 LLM...")
    await gen.generate("测试", "system", profile, examples)
    print("  ✅ 预热完成")

    # 加载 TTS
    print("\n[3/3] 加载 TTS...")
    tts = TTSEngine()
    await tts.save("语音引擎就绪", BASE_DIR / "data/warmup.wav", "默认")
    print("  ✅ TTS 就绪\n")

    # 交互循环
    while True:
        try:
            danmaku = input("\n💬 输入弹幕 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not danmaku:
            continue
        if danmaku.lower() == "q":
            break

        # LLM 生成回复 + 情绪
        reply, emotion = await gen.generate(danmaku, "弹幕观众", profile, examples)

        # TTS 合成 + 播放
        print(f"   📢 「{reply}」[{emotion}]")
        ok = await tts.speak(reply, emotion=emotion)
        if not ok:
            print("   ❌ 播放失败")

    await gen.close()
    await tts.close()
    print("\n  已退出。")


if __name__ == "__main__":
    asyncio.run(main())
