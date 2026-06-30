# Live AI Assistant 🎙️

直播 AI 互动助手——监听直播间弹幕 → AI 按主播风格生成回复 → 语音合成播放。

## 系统架构

```
弹幕监听 → LLM 情绪判断 → Edge-TTS 晓伊原声播放
  blivedm    qwen2.5:3b      自动匹配情绪标签
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 Ollama 并拉取模型
ollama pull qwen2.5:3b

# 3. 修改配置
#    编辑 config.py，设置 BILIBILI_ROOM_ID 为你的直播间号

# 4. 运行
python pipeline.py
```

## 核心功能

- **弹幕监听**：B站直播间 WebSocket 实时接收（blivedm）
- **风格蒸馏**：从历史对话提取主播说话风格（口头禅、语气、句式）
- **情绪判断**：LLM 自动识别弹幕情感，回复时匹配相应情绪
- **语音合成**：Edge-TTS 晓伊音色，原生人声，无后期处理

## 配置说明

编辑 `config.py`：

| 配置项 | 说明 |
|--------|------|
| `PLATFORM` | 直播平台（当前仅 bilibili） |
| `BILIBILI_ROOM_ID` | B站直播间号 |
| `OLLAMA_MODEL` | LLM 模型（默认 qwen2.5:3b） |

## 风格定制

1. 准备历史对话数据 `data/history_examples.json`，格式：
```json
[
  {"danmaku": "观众弹幕", "reply": "主播回复"},
  ...
]
```
2. 首次运行 `python pipeline.py` 时自动分析并提取风格特征

## 后续计划

- [ ] **抖音平台支持**：抖音弹幕协议需要字节跳动签名服务，目前 WebSocket/HTTP API 直连方案均受阻，后续计划使用 Chrome DevTools 协议或等待第三方库更新后接入
- [ ] **声音克隆**：CosyVoice 已测试通过，限于 4GB 显存暂未集成，换用更大显存显卡后可启用
- [ ] **更多情绪表现**：预留了音频 DSP 处理接口（音调偏移、语速调整、滤波），可按需开启

## 技术栈

| 模块 | 技术 |
|------|------|
| 弹幕监听 | blivedm (B站 WebSocket) |
| LLM | Ollama + qwen2.5:3b (GPU) |
| TTS | Edge-TTS (zh-CN-XiaoyiNeural) |
| 音频播放 | sounddevice |
| 框架 | Python asyncio |
