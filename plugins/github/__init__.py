"""Github 信息监控插件"""

import logging

log = logging.getLogger("uvicorn")

__plugin_meta__  = {
    "name": "Github 信息监控",
    "description": "Github 信息监控",
    "author": "yeying-xingchen",
    "version": "0.0.1",
    "events": ["message", "request"]  # 添加需要订阅的事件
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
    if parts[0] == "/github":
        sub_command = raw[len("/github "):]
        if sub_command.startswith("add "):
            repo = sub_command[len("add "):]
            group_name = info.get("group_name", "未知群")
            group_id = info.get("group_id", "未知ID")
            reply = (
                f"已绑定仓库 {repo} 到 {group_name} "
                f"群号 {group_id}"
            )
            return {"reply": reply}
    else:
        pass
