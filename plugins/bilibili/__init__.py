"""BiliBili解析插件"""

from urllib.parse import urlparse
import json
import requests

__plugin_meta__  = {
    "name": "BiliBili解析",
    "description": "解析Bilibili分享卡片",
    "author": "yeying-xingchen",
    "version": "0.0.1",
    "events": ["message"]  # 添加需要订阅的事件
}

def on_event(_message_type: str, info: dict):
    """
    处理接收到的命令

    :param message_type: 消息类型
    :type message_type: str
    :param info: 信息
    :type info: dict
    """
    if info["message"][0]["type"] == "json":
        try:
            card_info = json.loads(str(info["message"][0]["data"]["data"]))
            meta = card_info.get("meta", {})
            detail = meta.get("detail_1", {})

            if detail.get("title") == "哔哩哔哩":
                qqdocurl = detail.get("qqdocurl")
                if not qqdocurl:
                    return {}

                resp = requests.get(qqdocurl, timeout=15)

                parsed_url = urlparse(resp.url)
                bv = parsed_url.path.strip("/").replace("video", "")
                bv = bv.replace("/", "")
                url = f"{parsed_url.netloc}{parsed_url.path}"
                message = f"""检测到Bilibili分享卡片！
视频标题：{detail.get("desc", "未知")}
BV号：{bv}
视频链接：{url}
分享人：{detail.get("host", {}).get("uin", "未知")}"""
                return {"reply": message}
        except (KeyError, json.JSONDecodeError) as e:
            return {"reply": "error:" + str(e)}
    return None
