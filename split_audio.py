"""
从长音频中按静音分割提取语音片段
"""
import subprocess
import re
import json
from pathlib import Path

INPUT_WAV = "data/citlali_raw.wav"
OUTPUT_DIR = Path("data/segments")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. 运行 silencedetect 获取时间点
print("[1/3] 检测静音段...")
cmd = [
    "ffmpeg", "-i", INPUT_WAV,
    "-af", "silencedetect=noise=-30dB:d=0.4",
    "-f", "null", "-"
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
output = result.stderr

# 2. 解析时间戳
silence_starts = []
silence_ends = []

for line in output.split("\n"):
    m = re.search(r"silence_start: ([\d.]+)", line)
    if m:
        silence_starts.append(float(m.group(1)))
    m = re.search(r"silence_end: ([\d.]+)", line)
    if m:
        silence_ends.append(float(m.group(1)))

print(f"   找到 {len(silence_starts)} 个静音起点，{len(silence_ends)} 个静音终点")

# 3. 计算语音段 (非静音区间)
segments = []
for i in range(len(silence_ends) - 1):
    start = silence_ends[i]
    end = silence_starts[i + 1]
    duration = end - start
    if duration >= 1.0 and duration <= 20.0:  # 过滤太短或太长的
        segments.append((start, end, duration))

print(f"\n[2/3] 提取 {len(segments)} 个语音片段...")

# 4. 导出每个片段
segment_info = []
for i, (start, end, dur) in enumerate(segments):
    outpath = OUTPUT_DIR / f"seg_{i:04d}.wav"
    cmd = [
        "ffmpeg", "-y",
        "-i", INPUT_WAV,
        "-ss", str(start),
        "-to", str(end),
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "1",
        str(outpath),
        "-loglevel", "quiet"
    ]
    subprocess.run(cmd, timeout=30)
    size = outpath.stat().st_size
    segment_info.append({
        "index": i,
        "start": round(start, 2),
        "end": round(end, 2),
        "duration": round(dur, 2),
        "file": f"seg_{i:04d}.wav",
        "size_kb": size // 1024
    })
    if (i + 1) % 20 == 0:
        print(f"   ...已导出 {i + 1}/{len(segments)}")

# 5. 输出摘要
print(f"\n[3/3] 完成！共导出 {len(segment_info)} 个片段")

# 按时长排序，显示最长的 15 个
sorted_segs = sorted(segment_info, key=lambda x: x["duration"], reverse=True)
print(f"\n最长片段 Top 15：")
for s in sorted_segs[:15]:
    print(f"  seg_{s['index']:04d}.wav  {s['duration']:.1f}s  {s['size_kb']}KB")

# 统计
total_dur = sum(s["duration"] for s in segment_info)
print(f"\n语音总时长: {total_dur:.1f}s ({total_dur/60:.1f}min)")
print(f"平均时长: {total_dur/len(segment_info):.1f}s")
print(f"输出目录: {OUTPUT_DIR}")

# 保存元数据
meta_path = OUTPUT_DIR / "metadata.json"
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(segment_info, f, ensure_ascii=False, indent=2)
print(f"元数据已保存: {meta_path}")
