"""BiliBili解析插件"""

from urllib.parse import urlparse
import json
import requests
from urllib.parse import urlparse


def on_command(message_type: str, info: dict):
    """
    处理接收到的命令

    :param message_type: 消息类型
    :type message_type: str
    :param info: 信息
    :type info: dict
    """
    if message_type == "json":
        try:
            card_info = json.loads(str(info["message"][0]["data"]["data"]))
            meta = card_info.get("meta", {})
            detail = meta.get("detail_1", {})

            if detail.get("title") == "哔哩哔哩":
                qqdocurl = detail.get("qqdocurl")
                if not qqdocurl:
                    return {}

                resp = requests.get(qqdocurl, timeout=15)
                resp.raise_for_status()

                parsed_url = urlparse(resp.url)
                bv = parsed_url.path.strip("/").replace("video", "")
                url = f"{parsed_url.netloc}{parsed_url.path}"

                message = f"""检测到Bilibili分享卡片！
视频标题：{detail.get("desc", "未知")}
BV号：{bv}
视频链接：{url}
分享人：{detail.get("host", {}).get("uin", "未知")}"""
                return {"reply": message}
        except (KeyError, json.JSONDecodeError, requests.RequestException):
            pass

    return {}
