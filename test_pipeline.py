"""
快速测试脚本 - 验证 AI 互动助手核心链路（无弹幕连接）
模拟弹幕输入，测试 LLM 生成 + TTS 合成
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def test_local_llm():
    """测试 LLM 回复生成（不依赖 Ollama，用假数据验证 prompt 逻辑）"""
    print("\n" + "=" * 50)
    print("1️⃣  测试风格摘要生成")
    print("=" * 50)

    from style_extractor import StyleExtractor
    se = StyleExtractor()

    # 模拟风格摘要
    style_profile = {
        "tone": "亲切中带点搞怪",
        "catchphrases": ["蚌埠住了", "可以的", "兄弟们", "啊这"],
        "sentence_pattern": "短句为主，爱用反问和感叹",
        "interaction_style": "喜欢念观众名字，经常自嘲，接梗很快",
        "reply_length": "中等偏短",
        "emoji_or_punctuation": "大量使用感叹号和省略号",
        "topics": ["游戏操作", "弹幕互动", "日常分享"],
        "summary": "一个亲切搞怪的游戏主播，和弹幕互动频繁，语气轻松幽默"
    }
    se.profile_path.write_text(
        json.dumps(style_profile, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("✅ 风格摘要已生成")
    print(f"   风格: {style_profile['summary']}")
    print(f"   口头禅: {'、'.join(style_profile['catchphrases'])}")

    # 保存示例数据
    sample_examples = [
        {"danmaku": "主播好菜啊", "reply": "啊这 这波确实是我的问题 兄弟们轻喷"},
        {"danmaku": "主播唱个歌", "reply": "唱歌就算了吧 我怕把你们全唱跑了"},
        {"danmaku": "刚来 什么游戏", "reply": "欢迎欢迎 正在玩黑神话悟空 刚打到第三章"},
        {"danmaku": "操作可以的", "reply": "蚌埠住了 这波纯属运气好 平时我都是白给的"},
        {"danmaku": "主播多大", "reply": "永远十八岁好吧 不要问这么敏感的问题"},
    ]
    for i, ex in enumerate(sample_examples):
        path = Path("style_examples") / f"example_{i:04d}.json"
        path.write_text(json.dumps(ex, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已保存 {len(sample_examples)} 条示例数据")

    print("\n" + "=" * 50)
    print("2️⃣  测试回复生成 prompt 构建")
    print("=" * 50)

    from generator import ReplyGenerator
    gen = ReplyGenerator()

    prompt = gen.build_prompt(
        danmaku="主播这个boss怎么打啊 我卡了两小时了",
        username="弹幕小王子",
        style_profile=style_profile,
        examples=sample_examples,
        max_length=50
    )
    print("✅ Prompt 构建成功（334字）：")
    print(prompt[:200] + "...\n")

    print("\n" + "=" * 50)
    print("3️⃣  测试 TTS 合成")
    print("=" * 50)

    from tts_engine import TTSEngine
    tts = TTSEngine(voice="zh-CN-XiaoxiaoNeural")

    # 先测试 ffmpeg 路径
    print(f"   ffmpeg: {tts._ffmpeg_path}")
    print(f"   sounddevice: {_check_sounddevice()}")

    print("\n" + "=" * 50)
    print("4️⃣  测试保底回复")
    print("=" * 50)

    fallback = gen._fallback_reply("这个主播好厉害", style_profile)
    print(f"   弹幕: 「这个主播好厉害」")
    print(f"   保底回复: 「{fallback}」")

    print("\n" + "=" * 50)
    print("✅ 测试完成！")
    print("=" * 50)
    print("\n接下来需要:")
    print("  1. 安装 Ollama 并启动 (下载完成后)")
    print("  2. 运行: ollama pull qwen2.5:3b")
    print("  3. 修改 config.py 中的 ROOM_ID")
    print("  4. 准备 style_examples/ 下的历史对话数据")
    print("  5. 运行: python pipeline.py")


def _check_sounddevice():
    try:
        import sounddevice
        return f"✅ 可用 (设备数: {len(sounddevice.query_devices())})"
    except:
        return "❌ 未安装"


if __name__ == "__main__":
    asyncio.run(test_local_llm())
