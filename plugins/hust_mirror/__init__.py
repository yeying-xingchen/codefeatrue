"""华科镜像站监控插件"""

import logging
import requests

log = logging.getLogger("uvicorn")

__plugin_meta__  = {
    "name": "HUST Mirror",
    "description": "华中科技大学开源镜像站监控插件",
    "author": "yeying-xingchen",
    "version": "0.0.1",
    "events": ["message"]  # 添加需要订阅的事件
}

def on_enable(_app):
    """
    插件启用时调用
    
    :param app: FastAPI应用实例
    """

def on_event(_event_type: str, info: dict):
    """
    处理接收到的命令

    :param message_type: 消息类型
    :type message_type: str
    :param info: 信息
    :type info: dict
    """

    raw = info.get("raw_message", "")
    raw_message = raw.strip()
    parts = raw_message.split()
    if parts[0] == "/hust_mirror":
        sub_command = raw[len("/hust-mirror "):]
        if sub_command.startswith("status"):
            try:
                resp = requests.get("https://mirrors.hust.edu.cn/status.json", timeout=10)
                resp_info = resp.json()
                reply = "华中科技大学开源镜像站监控插件\n"
                for item in resp_info:
                    reply += f"{item['name']} 镜像状态: {item['status']}\n"
            except requests.exceptions.RequestException as e:
                reply = f"获取镜像站状态失败: {str(e)}"
            except ValueError as e:
                reply = f"解析响应数据失败: {str(e)}"
            return {"reply": reply}
    return None
