"""
回复生成模块
根据弹幕内容 + 主播风格，用本地 LLM（Ollama）生成主播风格回复
"""
import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger("generator")

# 回复生成 prompt 模板（含情绪判断）
REPLY_PROMPT_TEMPLATE = """你是一位B站主播，以下是你的说话风格：

{style_summary}

以下是过去你面对类似弹幕时的真实回复示例（供参考语气风格）：
{examples}

现在直播间里，观众「{username}」发了一条弹幕：
「{danmaku}」

请用你的风格回复这条弹幕，并判断回复时的情绪。

要求：
- 回复要口语化、自然，像直播时随口说的
- 控制在{max_length}字以内
- 情绪只能从以下选择：开心/温柔/惊讶/无奈/慵懒/傲娇/默认

以 JSON 格式输出，不要其他文字：
{{"reply": "你的回复内容", "emotion": "情绪"}}"""


class ReplyGenerator:
    """使用本地 Ollama LLM 生成主播风格的弹幕回复"""

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "qwen2.5:3b",
                 temperature: float = 0.7,
                 max_tokens: int = 80,
                 top_p: float = 0.9):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self._client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, prompt: str, num_gpu: int = -1) -> str:
        """调用 Ollama 生成文本"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "top_p": self.top_p,
            }
        }
        # 如果指定了 GPU 层数，限制 GPU 使用
        if num_gpu >= 0:
            payload["options"]["num_gpu"] = num_gpu
        try:
            resp = await self._client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.error(f"LLM 调用失败 ({type(e).__name__}): {e}")
            return ""

    def build_prompt(self, danmaku: str, username: str,
                     style_profile: dict,
                     examples: list[dict] = None,
                     max_length: int = 50) -> str:
        """构建完整的 prompt"""
        # 风格摘要文本
        style_summary = style_profile.get("summary", "")
        extra_style = ""
        if catchphrases := style_profile.get("catchphrases", []):
            extra_style += f"常用口头禅：{'、'.join(catchphrases)}\n"
        if interaction := style_profile.get("interaction_style", ""):
            extra_style += f"互动习惯：{interaction}\n"
        if tone := style_profile.get("tone", ""):
            extra_style += f"语气：{tone}\n"

        full_style = f"{style_summary}\n{extra_style}".strip()

        # 示例文本
        examples_text = ""
        if examples:
            lines = []
            for ex in examples[:5]:  # 最多5条示例
                d = ex.get("danmaku", "")
                r = ex.get("reply", "")
                lines.append(f"  观众：「{d}」→ 你：「{r}」")
            examples_text = "\n".join(lines)

        return REPLY_PROMPT_TEMPLATE.format(
            style_summary=full_style,
            examples=examples_text or "（暂无历史示例，按风格自由发挥）",
            username=username,
            danmaku=danmaku,
            max_length=max_length,
        )

    async def generate(self, danmaku: str, username: str,
                       style_profile: dict,
                       examples: Optional[list[dict]] = None) -> tuple[str, str]:
        """生成一条回复和对应的情绪，返回 (reply, emotion)"""
        prompt = self.build_prompt(
            danmaku, username, style_profile, examples,
            max_length=50
        )
        response = await self.chat(prompt)
        reply = ""
        emotion = "默认"

        if response:
            # 尝试解析 JSON
            try:
                start = response.index("{")
                end = response.rindex("}") + 1
                data = json.loads(response[start:end])
                reply = data.get("reply", "").strip()
                emotion = data.get("emotion", "默认")
                # 验证情绪有效性
                valid_emotions = {"开心", "温柔", "惊讶", "无奈", "慵懒", "傲娇", "默认"}
                if emotion not in valid_emotions:
                    emotion = "默认"
            except (ValueError, json.JSONDecodeError):
                # 解析失败，整段作为回复
                reply = response

        if not reply:
            reply = self._fallback_reply(danmaku, style_profile)

        # 清理
        reply = reply.replace("主播回复：", "").replace("主播:", "").replace("回复：", "").strip()
        logger.info(f"弹幕: 「{danmaku}」→ 回复: 「{reply}」[{emotion}]")
        return reply, emotion

    def _fallback_reply(self, danmaku: str, style_profile: dict) -> str:
        """LLM 失效时的保底回复"""
        catchphrases = style_profile.get("catchphrases", [])
        prefix = catchphrases[0] if catchphrases else "哈哈"
        return f"{prefix} {danmaku[:10]} 可以的"

    async def close(self):
        """关闭 HTTP 客户端"""
        await self._client.aclose()
