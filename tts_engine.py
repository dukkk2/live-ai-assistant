"""
语音合成与播放模块
基于 Edge-TTS + 情绪后期处理
"""
import asyncio
import logging
import os
import subprocess
from typing import Optional

import numpy as np

logger = logging.getLogger("tts_engine")

try:
    import edge_tts
except ImportError:
    raise

# 情绪 → 音色/处理参数 映射
EMOTION_CONFIG = {
    "开心": {"voice": "zh-CN-XiaoyiNeural",  "pitch": 0, "speed": 1.0, "lowpass": 99999, "volume": 0.90},
    "温柔": {"voice": "zh-CN-XiaoyiNeural",  "pitch": 0, "speed": 1.0, "lowpass": 99999, "volume": 0.80},
    "惊讶": {"voice": "zh-CN-XiaoyiNeural",  "pitch": 0, "speed": 1.0, "lowpass": 99999, "volume": 0.95},
    "无奈": {"voice": "zh-CN-XiaoyiNeural",  "pitch": 0, "speed": 1.0, "lowpass": 99999, "volume": 0.80},
    "慵懒": {"voice": "zh-CN-XiaoyiNeural",  "pitch": 0, "speed": 1.0, "lowpass": 99999, "volume": 0.78},
    "傲娇": {"voice": "zh-CN-XiaoyiNeural",  "pitch": 0, "speed": 1.0, "lowpass": 99999, "volume": 0.88},
    "默认": {"voice": "zh-CN-XiaoyiNeural",  "pitch": 0, "speed": 1.0, "lowpass": 99999, "volume": 0.85},
}


class TTSEngine:
    """基于 Edge-TTS 的语音合成引擎（支持情绪）"""

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural",
                 device: Optional[str] = None,
                 sample_rate: int = 24000):
        self.default_voice = voice
        self.device = device
        self.sample_rate = sample_rate
        self._ffmpeg_path = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str:
        for c in ["ffmpeg", r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"]:
            if os.system(f"{c} -version > nul 2>&1") == 0:
                return c
        return "ffmpeg"

    async def speak(self, text: str, emotion: str = "默认") -> bool:
        """合成语音并播放"""
        audio = await self._synthesize(text, emotion)
        if audio is None:
            return False
        await self._play_audio(audio)
        return True

    async def save(self, text: str, output_path: str, emotion: str = "默认") -> bool:
        """合成语音并保存"""
        audio = await self._synthesize(text, emotion)
        if audio is None:
            return False
        import soundfile as sf
        sf.write(output_path, audio, self.sample_rate)
        return True

    async def _synthesize(self, text: str, emotion: str) -> Optional[np.ndarray]:
        """完整合成链路：Edge-TTS → 情绪后期处理"""
        cfg = EMOTION_CONFIG.get(emotion, EMOTION_CONFIG["默认"])
        voice = cfg["voice"]

        # 1. Edge-TTS 合成 MP3
        try:
            communicate = edge_tts.Communicate(text, voice)
            mp3_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_data.extend(chunk["data"])
            if not mp3_data:
                logger.error("Edge-TTS 返回空")
                return None
        except Exception as e:
            logger.error(f"Edge-TTS 失败: {e}")
            return None

        # 2. MP3 → PCM
        pcm = await self._decode_mp3(bytes(mp3_data))
        if pcm is None:
            return None

        # 3. 情绪后期处理
        pcm = self._apply_emotion(pcm, cfg)

        logger.info(f"TTS [{emotion}] {len(pcm)/self.sample_rate:.1f}s")
        return pcm

    async def _decode_mp3(self, mp3_bytes: bytes) -> Optional[np.ndarray]:
        """MP3 → float32 numpy array"""
        try:
            proc = await asyncio.create_subprocess_exec(
                self._ffmpeg_path,
                "-i", "pipe:0",
                "-f", "s16le", "-acodec", "pcm_s16le",
                "-ar", str(self.sample_rate), "-ac", "1",
                "-loglevel", "error", "pipe:1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            pcm_data, _ = await proc.communicate(input=mp3_bytes)
            if proc.returncode != 0:
                return None
            return np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception as e:
            logger.error(f"解码失败: {e}")
            return None

    def _apply_emotion(self, audio: np.ndarray, cfg: dict) -> np.ndarray:
        """后期处理实现情绪变化"""
        import librosa
        from scipy import signal
        y = audio.copy()

        # 音调偏移
        if cfg["pitch"] != 0:
            y = librosa.effects.pitch_shift(y=y, sr=self.sample_rate, n_steps=cfg["pitch"])

        # 语速调整
        if cfg["speed"] != 1.0:
            y = librosa.effects.time_stretch(y=y, rate=cfg["speed"])

        # 低通滤波
        cutoff = cfg["lowpass"] / (self.sample_rate / 2)
        if cutoff < 0.95:
            b, a = signal.butter(4, cutoff, btype='low')
            y = signal.filtfilt(b, a, y)

        # 柔和压缩
        y = np.sign(y) * (np.abs(y) ** 0.8)
        y = y / (np.max(np.abs(y)) + 1e-8) * cfg["volume"]
        return y

    async def _play_audio(self, audio: np.ndarray):
        import sounddevice as sd
        sd.play(audio, samplerate=self.sample_rate)
        sd.wait()

    async def close(self):
        pass
