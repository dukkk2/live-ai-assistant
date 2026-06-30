"""
B站直播AI互动助手 - 配置模块
所有可自定义的配置项集中管理
"""

# ============ 直播平台配置 ============
# 平台: bilibili（当前可用）/ douyin（待开发）
PLATFORM = "bilibili"

# B站直播间房间号
BILIBILI_ROOM_ID = 123456

# ============ LLM 配置 ============
# Ollama 本地地址（默认端口 11434）
OLLAMA_BASE_URL = "http://localhost:11434"

# 使用的模型名称（先用 ollama pull qwen2.5:3b）
OLLAMA_MODEL = "qwen2.5:3b"

# GPU 层数（0 = 全部用 CPU，-1 = 全部用 GPU）
# 显存不够时设为 0，把 GPU 留给 CosyVoice TTS
OLLAMA_NUM_GPU = 0

# LLM 请求参数
LLM_TEMPERATURE = 0.7      # 创造性 0~1
LLM_MAX_TOKENS=80       # 回复最大长度（直播短句）
LLM_TOP_P = 0.9

# ============ TTS 配置 ============
# Edge-TTS 发音人
# 中文女声: zh-CN-XiaoxiaoNeural, zh-CN-XiaoyiNeural
# 中文男声: zh-CN-YunxiNeural, zh-CN-YunjianNeural
TTS_VOICE = "zh-CN-XiaoyiNeural"

# 语速 (+/- 50%), 音量 (+/- 50%)
TTS_RATE = "+0%"
TTS_VOLUME = "+0%"

# ============ 互动行为配置 ============
# 处理弹幕的最小间隔（秒），避免刷屏时重复回复
MIN_INTERVAL = 3.0

# 同一个人连续弹幕的冷却（秒）
USER_COOLDOWN = 10.0

# 每次回复中包含的历史示例数量
NUM_EXAMPLES = 5

# 最大回复字数
MAX_REPLY_LENGTH = 50

# ============ 风格配置文件路径 ============
STYLE_PROFILE_PATH = "style_profile.json"
STYLE_EXAMPLES_DIR = "style_examples"

# ============ CosyVoice 声音克隆配置 ============
# 参考音频路径（用于声音克隆）
COSYVOICE_PROMPT_AUDIO = "data/segments/seg_0136.wav"
# 参考音频对应的文本
COSYVOICE_PROMPT_TEXT = "希望你以后能够做的比我还好呦。"

# ============ 音频播放配置 ============
# 输出设备（None = 默认扬声器）
# 装 VB-CABLE 后可设为 "CABLE Input (VB-Audio Virtual Cable)"
AUDIO_DEVICE = None
AUDIO_SAMPLE_RATE = 24000
