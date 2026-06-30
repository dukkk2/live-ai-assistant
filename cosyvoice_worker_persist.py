"""
CosyVoice 常驻工作进程（通过 CMD 启动，环境隔离）
"""
import json
import os
import sys
import time
from pathlib import Path

# 在 CUDA 相关的库加载前设置环境变量
os.environ["CUDA_VISIBLE_DEVICES"] = ""
for var in ["TMPDIR", "TEMP", "TMP"]:
    os.environ[var] = "E:/streamer-ai/tmp"
os.makedirs("E:/streamer-ai/tmp", exist_ok=True)

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "CosyVoice"))
sys.path.insert(0, str(BASE_DIR / "CosyVoice/third_party/Matcha-TTS"))

import torch
import numpy as np
import soundfile as sf
from cosyvoice.cli.cosyvoice import CosyVoice

# 情绪配置
EMO_CFG = {
    "开心": {"pitch": 2.0, "speed": 1.08, "lowpass": 8000, "volume": 0.95},
    "温柔": {"pitch": 0.0, "speed": 0.92, "lowpass": 3500, "volume": 0.80},
    "无奈": {"pitch": -0.5, "speed": 0.88, "lowpass": 4500, "volume": 0.78},
    "慵懒": {"pitch": -1.0, "speed": 0.85, "lowpass": 4000, "volume": 0.75},
    "傲娇": {"pitch": 1.5, "speed": 1.00, "lowpass": 7000, "volume": 0.85},
}


def apply_emotion(y, emotion, sr):
    import librosa
    from scipy import signal
    cfg = EMO_CFG.get(emotion, {"pitch": 0, "speed": 1.0, "lowpass": 5000, "volume": 0.85})
    if cfg["pitch"]:
        y = librosa.effects.pitch_shift(y=y, sr=sr, n_steps=cfg["pitch"])
    if cfg["speed"] != 1.0:
        y = librosa.effects.time_stretch(y=y, rate=cfg["speed"])
    cutoff = cfg["lowpass"] / (sr / 2)
    if cutoff < 0.95:
        b, a = signal.butter(4, cutoff, btype='low')
        y = signal.filtfilt(b, a, y)
    y = np.sign(y) * (np.abs(y) ** 0.8)
    y = y / (np.max(np.abs(y)) + 1e-8) * cfg["volume"]
    return y


def main():
    model_dir = str(BASE_DIR / "pretrained_models/iic/CosyVoice-300M")
    sys.stderr.write("[worker] 加载模型...\n")
    sys.stderr.flush()
    t0 = time.time()
    cosyvoice = CosyVoice(model_dir)
    sys.stderr.write(f"[worker] 模型就绪 ({time.time()-t0:.1f}s)\n")
    sys.stderr.flush()

    init = json.loads(sys.stdin.readline())
    prompt_audio = init["prompt_audio"]
    prompt_text = init["prompt_text"]
    sys.stderr.write(f"[worker] 就绪\n")
    sys.stderr.flush()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        req = json.loads(line)
        text = req["text"]
        emotion = req.get("emotion", "默认")
        rid = req["id"]

        try:
            output = cosyvoice.inference_zero_shot(text, prompt_text, prompt_audio)
            for j in output:
                speech = j['tts_speech'].squeeze().cpu().numpy()
                speech = apply_emotion(speech, emotion, cosyvoice.sample_rate)
                out = f"E:/streamer-ai/data/tts_{rid}.wav"
                sf.write(out, speech, cosyvoice.sample_rate)
                result = {"id": rid, "status": "ok", "file": out}
                sys.stdout.write(json.dumps(result) + "\n")
                sys.stdout.flush()
                del j
        except Exception as e:
            sys.stdout.write(json.dumps({"id": rid, "status": "error", "msg": str(e)}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
