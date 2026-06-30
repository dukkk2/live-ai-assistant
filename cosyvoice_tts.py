"""
CosyVoice 语音合成引擎 + 情绪处理
使用 CosyVoice-300M 声音克隆 + 后期音频处理实现情绪变化
"""
import logging
import os
import sys
import time
from typing import Optional

import numpy as np

logger = logging.getLogger("cosyvoice_tts")

COSYVOICE_DIR = os.path.join(os.path.dirname(__file__), "CosyVoice")
sys.path.insert(0, COSYVOICE_DIR)
sys.path.insert(0, os.path.join(COSYVOICE_DIR, "third_party", "Matcha-TTS"))

# 强制 CosyVoice 走 CPU（4GB 显存不够两个模型共享）
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# 情绪参数配置
EMOTION_CONFIG = {
    "开心😄": {"pitch_shift": 2.0, "speed": 1.08, "lowpass": 8000, "volume": 0.95},
    "温柔😊": {"pitch_shift": 0.0, "speed": 0.92, "lowpass": 3500, "volume": 0.80},
    "惊讶😲": {"pitch_shift": 3.0, "speed": 1.10, "lowpass": 9000, "volume": 1.00},
    "无奈😅": {"pitch_shift": -0.5, "speed": 0.88, "lowpass": 4500, "volume": 0.78},
    "慵懒😴": {"pitch_shift": -1.0, "speed": 0.85, "lowpass": 4000, "volume": 0.75},
    "傲娇😏": {"pitch_shift": 1.5, "speed": 1.00, "lowpass": 7000, "volume": 0.85},
    "默认":   {"pitch_shift": 0.0, "speed": 1.00, "lowpass": 5000, "volume": 0.85},
}


class CosyVoiceTTS:
    """基于 CosyVoice 的声音克隆 TTS 引擎（支持情绪处理）"""

    def __init__(self, model_dir: str = None,
                 prompt_audio: str = None,
                 prompt_text: str = "希望你以后能够做的比我还好呦。",
                 device: Optional[str] = None,
                 sample_rate: int = 22050):
        if model_dir is None:
            model_dir = os.path.join(os.path.dirname(__file__),
                                     "pretrained_models/iic/CosyVoice-300M")
        self.model_dir = model_dir
        self.prompt_text = prompt_text
        self.sample_rate = sample_rate
        self._model = None
        self._device = device

    def _load_model(self):
        if self._model is not None:
            return
        import torch
        from cosyvoice.cli.cosyvoice import CosyVoice
        logger.info("正在加载 CosyVoice 模型...")
        t0 = time.time()
        self._model = CosyVoice(self.model_dir)
        logger.info(f"模型加载完成 ({time.time()-t0:.1f}s)")
        self._device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"使用设备: {self._device}")

    def set_prompt(self, audio_path: str, text: str = None):
        self.prompt_audio = audio_path
        if text:
            self.prompt_text = text

    def _apply_emotion(self, audio: np.ndarray, emotion: str) -> np.ndarray:
        """根据情绪参数处理音频"""
        import librosa
        from scipy import signal

        config = EMOTION_CONFIG.get(emotion, EMOTION_CONFIG["默认"])
        
        y = audio.copy()
        
        # 1. 音调偏移
        if config["pitch_shift"] != 0:
            y = librosa.effects.pitch_shift(y=y, sr=self.sample_rate,
                                            n_steps=config["pitch_shift"])
        
        # 2. 语速调整
        if config["speed"] != 1.0:
            y = librosa.effects.time_stretch(y=y, rate=config["speed"])
        
        # 3. 低通滤波（软化或明亮）
        cutoff = config["lowpass"] / (self.sample_rate / 2)
        if cutoff < 0.95:
            b, a = signal.butter(4, cutoff, btype='low')
            y = signal.filtfilt(b, a, y)
        
        # 4. 柔和压缩（让声音温暖）
        y = np.sign(y) * (np.abs(y) ** 0.8)
        
        # 5. 音量
        y = y / (np.max(np.abs(y)) + 1e-8) * config["volume"]
        
        return y

    async def speak(self, text: str, emotion: str = "默认") -> bool:
        """合成语音并播放，支持情绪选择"""
        if not text.strip():
            return False
        try:
            self._load_model()
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            return False
        if not hasattr(self, 'prompt_audio') or not self.prompt_audio:
            logger.error("未设置参考音频")
            return False

        import soundfile as sf
        t0 = time.time()
        try:
            output = self._model.inference_zero_shot(
                text, self.prompt_text, self.prompt_audio
            )
            for j in output:
                speech_np = j['tts_speech'].squeeze().cpu().numpy()
                # 应用情绪处理
                speech_np = self._apply_emotion(speech_np, emotion)
                dur = len(speech_np) / self.sample_rate
                logger.info(f"TTS [{emotion}]: {dur:.1f}s ({time.time()-t0:.1f}s)")
                await self._play_audio(speech_np)
                del j
            return True
        except Exception as e:
            logger.error(f"合成失败: {e}")
            return False

    async def _play_audio(self, audio_array: np.ndarray):
        import sounddevice as sd
        sd.play(audio_array, samplerate=self.sample_rate)
        sd.wait()

    async def save(self, text: str, output_path: str, emotion: str = "默认") -> bool:
        """合成语音并保存到文件"""
        if not text.strip():
            return False
        try:
            self._load_model()
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            return False
        if not hasattr(self, 'prompt_audio') or not self.prompt_audio:
            logger.error("未设置参考音频")
            return False

        import soundfile as sf
        try:
            output = self._model.inference_zero_shot(
                text, self.prompt_text, self.prompt_audio
            )
            for j in output:
                speech_np = j['tts_speech'].squeeze().cpu().numpy()
                speech_np = self._apply_emotion(speech_np, emotion)
                sf.write(output_path, speech_np, self.sample_rate)
                logger.info(f"已保存 [{emotion}]: {output_path}")
                del j
            return True
        except Exception as e:
            logger.error(f"保存失败: {e}")
            return False

    async def close(self):
        self._model = None
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
