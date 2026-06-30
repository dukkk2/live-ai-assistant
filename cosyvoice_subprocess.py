"""
CosyVoice TTS 客户端 - 通过持久化工作进程合成语音
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cosyvoice")


class CosyVoiceSubprocessTTS:
    def __init__(self, prompt_audio: str = None,
                 prompt_text: str = "希望你以后能够做的比我还好呦。"):
        self.prompt_audio = str(Path(prompt_audio or "data/segments/seg_0136.wav").resolve())
        self.prompt_text = prompt_text
        self._proc: Optional[subprocess.Popen] = None
        self._req_id = 0

    async def _ensure_worker(self):
        if self._proc is not None and self._proc.poll() is None:
            return

        worker_script = Path(__file__).parent / "cosyvoice_worker_persist.py"
        # 用干净环境启动
        worker_env = os.environ.copy()
        worker_env["CUDA_VISIBLE_DEVICES"] = ""
        
        self._proc = subprocess.Popen(
            [sys.executable, str(worker_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, bufsize=1,
            env=worker_env,
            encoding='utf-8', errors='replace',
        )

        init_msg = json.dumps({
            "prompt_audio": self.prompt_audio,
            "prompt_text": self.prompt_text,
        })
        self._proc.stdin.write(init_msg + "\n")
        self._proc.stdin.flush()

        t0 = time.time()
        while time.time() - t0 < 120:
            line = self._proc.stderr.readline()
            if line:
                logger.info(f"[worker] {line.strip()}")
                if "就绪" in line:
                    return
            await asyncio.sleep(0.1)
        raise RuntimeError("工作进程启动超时")

    async def speak(self, text: str, emotion: str = "默认") -> bool:
        import soundfile as sf, sounddevice as sd
        result = await self._request(text, emotion)
        if result and result.get("status") == "ok":
            try:
                data, sr = sf.read(result["file"])
                sd.play(data, samplerate=sr)
                sd.wait()
                return True
            except Exception as e:
                logger.error(f"播放失败: {e}")
        return False

    async def save(self, text: str, output_path: str, emotion: str = "默认") -> bool:
        result = await self._request(text, emotion)
        if result and result.get("status") == "ok":
            import shutil
            shutil.copy(result["file"], output_path)
            return True
        return False

    async def _request(self, text: str, emotion: str) -> Optional[dict]:
        try:
            await self._ensure_worker()
        except Exception as e:
            logger.error(f"工作进程: {e}")
            return None

        self._req_id += 1
        req = json.dumps({"id": self._req_id, "text": text, "emotion": emotion})
        t0 = time.time()
        self._proc.stdin.write(req + "\n")
        self._proc.stdin.flush()

        while time.time() - t0 < 180:
            line = self._proc.stdout.readline()
            if not line:
                break
            try:
                result = json.loads(line.strip())
                if result.get("id") == self._req_id:
                    logger.info(f"TTS [{emotion}]: {time.time()-t0:.1f}s")
                    return result
            except json.JSONDecodeError:
                continue
        return None

    async def close(self):
        if self._proc and self._proc.poll() is None:
            self._proc.stdin.close()
            self._proc.terminate()
