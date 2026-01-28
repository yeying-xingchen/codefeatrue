"""插件包"""

import asyncio
import json
import logging
from typing import Dict, Optional
import websockets
import threading

log = logging.getLogger("uvicorn")

class OneBotV11Client:
    """
    OneBot v11 协议客户端，用于发送消息和其他操作
    """
    
    def __init__(self, ws_url: str):
        """
        初始化OneBot客户端
        
        Args:
            ws_url: WebSocket连接地址
        """
        self.ws_url = ws_url
        self.websocket = None
        self.connected = False
        self._lock = asyncio.Lock()
        
    async def connect(self):
        """建立WebSocket连接"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.connected = True
            log.info(f"OneBot v11 客户端已连接到 {self.ws_url}")
            
            # 启动消息接收循环
            asyncio.create_task(self._receive_messages())
        except Exception as e:
            log.error(f"连接 OneBot v11 服务失败: {e}")
            self.connected = False
    
    async def disconnect(self):
        """断开WebSocket连接"""
        self.connected = False
        if self.websocket:
            await self.websocket.close()
            log.info("OneBot v11 客户端已断开连接")
    
    async def _receive_messages(self):
        """接收来自OneBot的消息"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                log.debug(f"收到OneBot消息: {data}")
                # 处理接收到的消息
        except websockets.exceptions.ConnectionClosed:
            log.warning("OneBot WebSocket 连接已关闭")
        except Exception as e:
            log.error(f"接收OneBot消息时出现错误: {e}")
    
    async def send_group_msg(self, group_id: int, message: str, auto_escape: bool = False):
        """
        发送群消息
        
        Args:
            group_id: 群号
            message: 消息内容
            auto_escape: 是否自动转义
        """
        if not self.connected or not self.websocket:
            log.error("OneBot客户端未连接，无法发送消息")
            return None
            
        data = {
            "action": "send_group_msg",
            "params": {
                "group_id": group_id,
                "message": message,
                "auto_escape": auto_escape
            }
        }
        
        try:
            await self.websocket.send(json.dumps(data))
            log.info(f"已发送群消息到群 {group_id}: {message[:50]}...")
            return True
        except Exception as e:
            log.error(f"发送群消息失败: {e}")
            return False
    
    async def send_private_msg(self, user_id: int, message: str, auto_escape: bool = False):
        """
        发送私聊消息
        
        Args:
            user_id: 用户ID
            message: 消息内容
            auto_escape: 是否自动转义
        """
        if not self.connected or not self.websocket:
            log.error("OneBot客户端未连接，无法发送消息")
            return None
            
        data = {
            "action": "send_private_msg",
            "params": {
                "user_id": user_id,
                "message": message,
                "auto_escape": auto_escape
            }
        }
        
        try:
            await self.websocket.send(json.dumps(data))
            log.info(f"已发送私聊消息给用户 {user_id}: {message[:50]}...")
            return True
        except Exception as e:
            log.error(f"发送私聊消息失败: {e}")
            return False


# 全局OneBot客户端实例
_bot_client: Optional[OneBotV11Client] = None


def init_bot_client(ws_url: str):
    """
    初始化OneBot客户端
    
    Args:
        ws_url: WebSocket连接地址
    """
    global _bot_client
    _bot_client = OneBotV11Client(ws_url)
    
    # 在后台任务中连接
    async def connect_and_run():
        await _bot_client.connect()
    
    # 确保在正确的事件循环中运行
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(connect_and_run())
    except RuntimeError:
        # 如果没有运行的事件循环，则创建一个新的
        def run_in_thread():
            asyncio.run(connect_and_run())
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()


async def send_group_msg(group_id: int, message: str, auto_escape: bool = False):
    """
    发送群消息的便捷函数
    
    Args:
        group_id: 群号
        message: 消息内容
        auto_escape: 是否自动转义
    """
    if _bot_client and _bot_client.connected:
        return await _bot_client.send_group_msg(group_id, message, auto_escape)
    else:
        log.error("OneBot客户端未初始化或未连接")
        return False


async def send_private_msg(user_id: int, message: str, auto_escape: bool = False):
    """
    发送私聊消息的便捷函数
    
    Args:
        user_id: 用户ID
        message: 消息内容
        auto_escape: 是否自动转义
    """
    if _bot_client and _bot_client.connected:
        return await _bot_client.send_private_msg(user_id, message, auto_escape)
    else:
        log.error("OneBot客户端未初始化或未连接")
        return False