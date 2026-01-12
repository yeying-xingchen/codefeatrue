"""入群邀请，好友申请自动同意"""

import json

__plugin_meta__  = {
    "name": "邀请信息",
    "description": "自动通过邀请",
    "author": "yeying-xingchen",
    "version": "0.0.1",
    "events": ["notice"]  # 添加需要订阅的事件
}

def on_invite(_message_type: str, info: dict):
    """
    处理接收到的入群邀请，好友申请

    :param message_type: 消息类型
    :type message_type: str
    :param info: 信息
    :type info: dict
    """
    if info["request_type"] == "group":
        return { "approve" : True }
    if info["notice_type"] == "group_increase":

        return { "approve" : True }
    if info["request_type"] == "friend":
        with open("/data/user.json", "r", encoding="utf-8") as f:
            user_list = json.load(f)
        user_list.append({
            "platform": "onebot",
            "id": user_list[-1]["id"] + 1,
            "platform_id": info["user_id"],
        })
        with open("/data/user.json", "w", encoding="utf-8") as f:
            json.dump(user_list, f, ensure_ascii=False)
        return { "approve" : True }
    return {}
