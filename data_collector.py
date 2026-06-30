"""
数据收集工具 - 从 B站直播录像/回放中提取训练数据

用法:
  手动准备 data/history_examples.json 格式:
  [
    {"danmaku": "观众弹幕", "reply": "主播回复"},
    ...
  ]
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("data_collector")

# 模拟数据生成器（用于测试，替换为真实数据）
SAMPLE_DATA = [
    {"danmaku": "主播好菜啊", "reply": "啊这 这波确实是我的问题 兄弟们轻喷"},
    {"danmaku": "主播唱个歌", "reply": "唱歌就算了吧 我怕把你们全唱跑了"},
    {"danmaku": "刚来 什么游戏", "reply": "欢迎欢迎 正在玩黑神话悟空 刚打到第三章"},
    {"danmaku": "操作可以的", "reply": "蚌埠住了 这波纯属运气好 平时我都是白给的"},
    {"danmaku": "主播多大", "reply": "永远十八岁好吧 不要问这么敏感的问题"},
    {"danmaku": "这boss怎么打", "reply": "这个boss要等他出完招再打 别贪刀"},
    {"danmaku": "主播加油", "reply": "谢谢兄弟 这把必过！"},
    {"danmaku": "有没有福利", "reply": "福利？我这张帅脸就是最大的福利好吧"},
    {"danmaku": "好菜啊这操作", "reply": "你行你上啊 来 弹幕发个房号 等你"},
    {"danmaku": "主播声音好听", "reply": "那是 也不看看我是谁 声控福利懂不懂"},
    {"danmaku": "这个游戏好玩吗", "reply": "好玩 就是有点费肝 我已经肝了50小时了"},
    {"danmaku": "主播咋不说话", "reply": "我在认真打呢 这波操作需要集中注意力"},
    {"danmaku": "打卡", "reply": "欢迎打卡 今天也是元气满满的一天"},
    {"danmaku": "有没有女朋友", "reply": "女朋友？我有游戏就够了 游戏才是真爱"},
    {"danmaku": "求带", "reply": "带你可以 但你要听话 别乱跑"},
    {"danmaku": "主播别浪", "reply": "不浪那还是我吗 看我表演就完事了"},
]


def generate_sample_data(output_path: str = "data/history_examples.json"):
    """生成样本数据文件"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(SAMPLE_DATA, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ 样本数据已保存到 {path}")
    print(f"   共 {len(SAMPLE_DATA)} 条 (弹幕→回复) 示例")


if __name__ == "__main__":
    generate_sample_data()
