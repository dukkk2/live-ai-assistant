"""
B站直播AI互动助手 - 主控流程

完整链路：
  弹幕监听 → 风格匹配 → LLM生成回复 → TTS语音合成 → 音频播放

使用方式：
  1. 先安装依赖: pip install -r requirements.txt
  2. 确保 Ollama 已运行: ollama pull qwen2.5:3b
  3. 修改 config.py 中的 ROOM_ID 为主播房间号
  4. 运行: python pipeline.py

首次运行时会要求提供历史对话以提取风格特征
后续运行自动加载风格配置
"""
import asyncio
import json
import logging
import os
import time
import sys
from datetime import datetime
from pathlib import Path

import config
from generator import ReplyGenerator
from style_extractor import StyleExtractor
from tts_engine import TTSEngine

# 根据平台选择弹幕监听模块
if config.PLATFORM == "bilibili":
    from danmaku_capture import DanmakuHandler
    ROOM_ID = config.BILIBILI_ROOM_ID
elif config.PLATFORM == "douyin":
    from danmaku_douyin import DouyinDanmakuHandler as DanmakuHandler
    ROOM_ID = getattr(config, 'DOUYIN_ROOM_ID', '')
else:
    raise ValueError(f"不支持的平台: {config.PLATFORM}")

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


class StreamerAI:
    """AI 主播互动助手主控制器"""

    def __init__(self):
        self.room_id = ROOM_ID
        self.min_interval = config.MIN_INTERVAL
        self.user_cooldown = config.USER_COOLDOWN

        # 子模块
        self.danmaku = DanmakuHandler(self.room_id)
        self.style_extractor = StyleExtractor(
            examples_dir=config.STYLE_EXAMPLES_DIR,
            profile_path=config.STYLE_PROFILE_PATH,
        )
        self.generator = ReplyGenerator(
            base_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            top_p=config.LLM_TOP_P,
        )
        self.tts = TTSEngine(
            voice=config.TTS_VOICE,
            device=config.AUDIO_DEVICE,
        )

        # 运行时状态
        self.style_profile: dict = {}
        self.examples: list[dict] = []
        self._last_reply_time = 0.0
        self._user_last_reply: dict[str, float] = {}

    # ── 初始化 ──────────────────────────────

    async def initialize(self):
        """加载风格配置 / 引导首次设置"""
        # 1. 尝试加载风格摘要
        self.style_profile = self.style_extractor.load_profile() or {}

        # 2. 加载历史示例
        self.examples = self.style_extractor.load_all_examples()
        logger.info(f"已加载 {len(self.examples)} 条历史示例")

        # 3. 如果没有风格，引导用户首次设置
        if not self.style_profile:
            logger.info("=" * 50)
            logger.info("首次运行，需要提取主播风格！")
            logger.info("=" * 50)
            if not await self._first_time_setup():
                logger.warning("跳过风格提取，使用默认配置")
                self.style_profile = {
                    "tone": "亲切",
                    "catchphrases": ["哈哈", "可以的", "兄弟们"],
                    "sentence_pattern": "短句为主",
                    "interaction_style": "友好互动",
                    "reply_length": "短",
                    "emoji_or_punctuation": "常用感叹号",
                    "topics": ["游戏", "日常"],
                    "summary": "一位亲切友好的主播，喜欢和观众聊天互动"
                }

        logger.info("初始化完成，等待弹幕...")
        self._print_banner()

    async def _first_time_setup(self) -> bool:
        """引导用户提供历史对话以提取风格"""
        setup_file = Path("data/history_examples.json")

        if not setup_file.exists():
            logger.info(
                "请准备主播的历史对话记录，格式如下：\n"
                "[\n"
                '  {"danmaku": "观众弹幕内容", "reply": "主播回复内容"},\n'
                '  {"danmaku": "另一个弹幕", "reply": "主播回复"}\n'
                "]\n"
                f"保存到: {setup_file.resolve()}\n"
                "至少提供 10 条以上效果更好。\n"
            )
            logger.info("准备好后按 Enter 继续...")
            # 在非交互式环境跳过
            return False

        try:
            examples = json.loads(setup_file.read_text(encoding="utf-8"))
            if not isinstance(examples, list) or len(examples) < 3:
                logger.warning("示例数据不足（至少3条）")
                return False
            self.examples = examples
            self.style_profile = await self.style_extractor.analyze_style(
                examples, self.generator.chat
            )
            # 同时也保存到 style_examples 目录
            for ex in examples:
                self.style_extractor.save_example(ex.get("danmaku", ""), ex.get("reply", ""))
            return True
        except Exception as e:
            logger.error(f"读取历史对话失败: {e}")
            return False

    def _print_banner(self):
        """打印启动信息"""
        print("\n" + "=" * 55)
        print(f"  平台: {config.PLATFORM}")
        print(f"  直播间: {self.room_id}")
        print(f"  LLM: {config.OLLAMA_MODEL}")
        print(f"  TTS: 晓伊")
        print(f"  冷却间隔: {self.min_interval}s")
        summary = self.style_profile.get("summary", "（未设置）")
        print(f"  风格: {summary}")
        print("=" * 55 + "\n")

    # ── 弹幕处理 ────────────────────────────

    async def on_danmaku(self, data: dict):
        """收到弹幕后的处理入口"""
        now = time.time()

        # 1. 冷却检查：全局
        if now - self.last_reply_time < self.min_interval:
            return

        # 2. 冷却检查：同一个人
        uid = str(data["uid"])
        last_user = self._user_last_reply.get(uid, 0.0)
        if now - last_user < self.user_cooldown:
            return

        danmaku = data["text"].strip()
        username = data["username"]

        if not danmaku:
            return

        # 3. 生成回复（含情绪）
        logger.info(f"→ [{username}] {danmaku}")
        reply, emotion = await self.generator.generate(
            danmaku=danmaku,
            username=username,
            style_profile=self.style_profile,
            examples=self.examples,
        )

        if not reply:
            return

        # 4. 保存为新示例（增量学习）
        self.examples.append({"danmaku": danmaku, "reply": reply})
        if len(self.examples) % 10 == 0:
            self.style_extractor.save_example(danmaku, reply)

        # 5. TTS 播放（带情绪）
        logger.info(f"← 回复: {reply} [{emotion}]")
        await self.tts.speak(reply, emotion=emotion)

        # 6. 更新状态
        self._last_reply_time = now
        self._user_last_reply[uid] = now

    @property
    def last_reply_time(self) -> float:
        return self._last_reply_time

    # ── 主循环 ──────────────────────────────

    async def run(self):
        """启动完整链路"""
        try:
            await self.initialize()
            self.danmaku.on_danmaku(self.on_danmaku)
            await self.danmaku.listen()
        except asyncio.CancelledError:
            logger.info("正在关闭...")
        except KeyboardInterrupt:
            logger.info("收到退出信号")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """清理资源"""
        await self.generator.close()
        await self.tts.close()
        logger.info("AI 互动助手已停止")


def main():
    """入口函数"""
    # 检查 Ollama 是否运行
    import httpx
    try:
        resp = httpx.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3.0)
        models = resp.json().get("models", [])
        model_names = [m["name"] for m in models]
        if config.OLLAMA_MODEL not in model_names:
            logger.warning(
                f"模型 {config.OLLAMA_MODEL} 未找到，可用模型: {model_names}\n"
                f"请执行: ollama pull {config.OLLAMA_MODEL}"
            )
            sys.exit(1)
        logger.info(f"Ollama 已连接，模型 {config.OLLAMA_MODEL} 就绪")
    except Exception as e:
        logger.error(f"Ollama 连接失败: {e}")
        logger.error("请确保已安装并启动 Ollama: https://ollama.com")
        sys.exit(1)

    asyncio.run(StreamerAI().run())


if __name__ == "__main__":
    main()
