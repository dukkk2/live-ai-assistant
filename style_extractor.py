"""
主播风格提取模块
从历史直播对话中提取主播的说话风格，生成结构化风格档案
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("style_extractor")

# 风格分析 prompt（给 LLM 用的）
STYLE_ANALYSIS_PROMPT = """你是一位直播风格分析师。请分析以下主播和观众的对话记录，提取主播的说话风格特征。

对话记录（格式：观众弹幕 → 主播回复）：
{examples}

请从以下维度分析并输出 JSON 格式的风格摘要：
1. tone: 语气风格（如亲切、毒舌、搞怪、温柔、热血、冷静等）
2. catchphrases: 常用口头禅/语气词列表
3. sentence_pattern: 典型句式特征（如爱用反问、喜欢重复、常用短句等）
4. interaction_style: 互动习惯（如念粉丝名、接梗、自嘲、夸赞、怼人等）
5. reply_length: 回复长度倾向（极短/短/中等/较长）
6. emoji_or_punctuation: 标点/表情使用习惯
7. topics: 常聊话题方向
8. summary: 一段简洁的风格总结（50字以内）

只输出 JSON，不要其他文字。"""


class StyleExtractor:
    """从主播历史对话中提取风格特征"""

    def __init__(self, examples_dir: str = "style_examples",
                 profile_path: str = "style_profile.json"):
        self.examples_dir = Path(examples_dir)
        self.profile_path = Path(profile_path)
        self.examples_dir.mkdir(parents=True, exist_ok=True)

    def load_all_examples(self) -> list[dict]:
        """加载所有历史示例"""
        examples = []
        if not self.examples_dir.exists():
            return examples
        for f in sorted(self.examples_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    examples.extend(data)
                else:
                    examples.append(data)
            except Exception as e:
                logger.warning(f"读取 {f} 失败: {e}")
        return examples

    def format_examples_for_prompt(self, examples: list[dict],
                                   max_pairs: int = 30) -> str:
        """格式化示例用于 prompt"""
        lines = []
        for ex in examples[:max_pairs]:
            danmaku = ex.get("danmaku", ex.get("观众弹幕", ""))
            reply = ex.get("reply", ex.get("主播回复", ""))
            lines.append(f"观众说：「{danmaku}」→ 主播回复：「{reply}」")
        return "\n".join(lines)

    async def analyze_style(self, examples: list[dict],
                            llm_generate_fn) -> dict:
        """
        用 LLM 分析示例，生成风格摘要

        Args:
            examples: [(danmaku, reply), ...]
            llm_generate_fn: async (prompt) -> str  用于调用 LLM

        Returns:
            dict: 风格摘要
        """
        formatted = self.format_examples_for_prompt(examples)
        prompt = STYLE_ANALYSIS_PROMPT.format(examples=formatted)

        logger.info("正在分析主播风格...")
        response = await llm_generate_fn(prompt)

        # 尝试解析 JSON
        try:
            # 找第一个 { 和最后一个 }
            start = response.index("{")
            end = response.rindex("}") + 1
            style = json.loads(response[start:end])
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"风格解析失败: {e}, 原始响应: {response[:200]}")
            style = {
                "tone": "未知",
                "catchphrases": [],
                "sentence_pattern": "未知",
                "interaction_style": "未知",
                "reply_length": "中等",
                "emoji_or_punctuation": "未知",
                "topics": [],
                "summary": "尚未提取风格特征"
            }

        # 缓存到文件
        self.profile_path.write_text(
            json.dumps(style, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"风格摘要已保存到 {self.profile_path}")
        return style

    def load_profile(self) -> Optional[dict]:
        """加载已缓存的风格摘要"""
        if self.profile_path.exists():
            return json.loads(self.profile_path.read_text(encoding="utf-8"))
        return None

    def save_example(self, danmaku: str, reply: str):
        """保存一条新的(弹幕→回复)示例"""
        filepath = self.examples_dir / f"example_{len(list(self.examples_dir.glob('*.json'))):04d}.json"
        data = {"danmaku": danmaku, "reply": reply}
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"示例已保存: {filepath}")
