"""调试 CosyVoice 加载"""
import sys
sys.path.insert(0, 'CosyVoice')
sys.path.insert(0, 'CosyVoice/third_party/Matcha-TTS')

import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OLLAMA_NUM_GPU"] = "0"

import warnings
warnings.filterwarnings('ignore')

print("step1: import")
from cosyvoice.cli.cosyvoice import CosyVoice
print("step2: creating model")

try:
    m = CosyVoice('pretrained_models/iic/CosyVoice-300M')
    print("✅ 成功")
except Exception as e:
    print(f"❌ 失败: {type(e).__name__}: {e}")
