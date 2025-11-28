"""程序总入口"""

from fastapi import FastAPI
from plugins import github, oseddl, bilibili

app = FastAPI()

@app.post("/")
def main(info: dict):
    """
    处理接收到的消息
    
    :param info: Onebot实现端传入的信息
    :type info: dict
    """
    if info["post_type"]=="message":
        message_type = info["message"][0]["type"]
        # 私聊/群 均传递
        if info["raw_message"].startswith("/oseddl"):
            return oseddl.on_command(message_type, info)
        if info["message_type"] == "group":
        # 仅群
            if info["raw_message"].startswith("/github"):
                return github.on_command(message_type, info)
            if info["message"][0]["type"] == "json":
                # Type == card
                return  bilibili.on_command(message_type, info)
    return {}
