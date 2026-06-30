"""
B站弹幕监听模块
基于 blivedm WebSocket 协议实时接收弹幕
"""
import asyncio
import logging
from typing import AsyncGenerator, Callable, Optional

logger = logging.getLogger("danmaku")

try:
    from blivedm import BLiveClient
    from blivedm.models import DanmakuMessage
except ImportError:
    logger.warning("blivedm 未安装，请执行: pip install blivedm")
    raise


class DanmakuHandler:
    """弹幕监听器，连接到 B站直播间并推送弹幕事件"""

    def __init__(self, room_id: int):
        self.room_id = room_id
        self._client: Optional[BLiveClient] = None
        self._callbacks: list[Callable] = []

    def on_danmaku(self, callback: Callable):
        """注册弹幕回调函数"""
        self._callbacks.append(callback)

    async def _handle_danmaku(self, message: DanmakuMessage):
        """内部处理弹幕，分发给所有回调"""
        data = {
            "uid": message.uid,
            "username": message.uname,
            "text": message.msg,
            "medal_name": message.medal_name or "",
            "medal_level": message.medal_level or 0,
            "timestamp": message.timestamp,
        }
        for cb in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(data)
                else:
                    cb(data)
            except Exception as e:
                logger.error(f"弹幕回调异常: {e}")

    async def listen(self):
        """启动监听（持续运行）"""
        client = BLiveClient(self.room_id)
        self._client = client

        @client.on("DANMU_MSG")
        async def on_danmaku(message: DanmakuMessage):
            await self._handle_danmaku(message)

        logger.info(f"正在连接直播间 {self.room_id} ...")
        try:
            await client.start()
        except asyncio.CancelledError:
            logger.info("弹幕监听已停止")
        finally:
            await client.stop()
            self._client = None

    def stop(self):
        """停止监听"""
        if self._client:
            self._client.stop()
