"""Oseddl 数据查询插件"""

from datetime import datetime
import requests
import yaml
import config

__plugin_meta__  = {
    "name": "Github 信息监控",
    "description": "Github 信息监控",
    "author": "yeying-xingchen",
    "version": "0.0.1",
    "events": ["message"]  # 添加需要订阅的事件
}

# 常量定义
HELP_MESSAGE = """Oseddl 功能使用帮助
/oseddl activities 查看活动列表
/oseddl competitions 查看比赛列表
/oseddl conferences 查看会议列表
"""
BASE_URL = config.get("oseddl", "oseddl_base_url")
VALID_COMMANDS = {"activities", "competitions", "conferences"}


def _fetch_data(command: str) -> list:
    """从远程获取 YAML 数据并解析为列表。"""
    try:
        resp = requests.get(f"{BASE_URL}/{command}.yml", timeout=15)
        resp.raise_for_status()
        data = yaml.safe_load(resp.text)
        return data if isinstance(data, list) else []
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"获取数据失败：{e}") from e
    except yaml.YAMLError as e:
        raise RuntimeError(f"解析数据失败：{e}") from e


def _format_list_view(data: list, command: str) -> str:
    """格式化列表视图消息。"""
    items = "\n".join(f"{i + 1}：{item.get('title', '无标题')}" for i, item in enumerate(data))
    return f"{items}\n\n您可以发送 /oseddl {command} 序号 查看该活动的具体信息"


def _format_detail_view(item: dict) -> str:
    """格式化详情视图消息。"""
    events = item.get("events", [])

    timeline_list = events[0]["timeline"]
    current_time = datetime.now()

    # 获取当前正在进行的事件
    current_event = None
    next_event = None

    for _i, evt in enumerate(timeline_list):
        evt_time = datetime.fromisoformat(evt["deadline"].replace("Z", "+00:00"))
        if evt_time < current_time:
            current_event = evt
        else:
            next_event = evt
            break

    # 如果没找到当前事件（活动已结束），则默认取第一个作为当前事件
    if not current_event and timeline_list:
        current_event = timeline_list[0]
        next_event = timeline_list[1] if len(timeline_list) > 1 else None

    if events[0]["year"]:
        return f"""标题：{item.get('title', '无')} {events[0]["year"]}
介绍：{item.get('description', '无')}
时间：{events[0].get('date', '无')}
当前事件：
- 名称：{current_event.get('comment', '无')}
- 时间：{current_event.get('deadline', '无').replace("T", " ")}
至 {next_event.get('deadline', '无').replace("T", " ") if next_event else '无'}
- 链接：{events[0].get('link', '无')}"""

    return f"""标题：{item.get('title', '无')}
介绍：{item.get('description', '无')}
时间：{events[0].get('date', '无')}
当前事件：
- 名称：{current_event.get('comment', '无')}
- 时间：{current_event.get('deadline', '无').replace("T", " ")}
至 {next_event.get('deadline', '无').replace("T", " ") if next_event else '无'}
- 链接：{events[0].get('link', '无')}"""


def on_event(_event_type: str, info: dict):
    """
    处理 /oseddl 命令。

    :param message_type: 消息类型
    :param info: 包含 raw_message 的字典
    :return: 回复字典或空字典
    """

    raw_message = info.get("raw_message", "").strip()
    parts = raw_message.split()

    if parts[0] == "/oseddl":
        if not parts:
            return {"reply": "无效的命令格式"}

        sub_parts = parts[1:]

        if not sub_parts or sub_parts[0] == "help":
            return {"reply": HELP_MESSAGE}

        main_cmd = sub_parts[0]
        if main_cmd not in VALID_COMMANDS:
            return {"reply": f"无效的命令，请使用以下有效命令：{', '.join(VALID_COMMANDS)}"}

        return _handle_detail_query(main_cmd, sub_parts)
    else:
        pass

def _handle_detail_query(main_cmd, sub_parts):
    try:
        data = _fetch_data(main_cmd)
        if not data:
            return {"reply": "未找到相关数据"}
        if len(sub_parts) >= 2:
            try:
                idx = int(sub_parts[1]) - 1
                if not 0 <= idx < len(data):
                    raise ValueError(f"序号无效，请在 1-{len(data)} 范围内选择")
                detail_msg = _format_detail_view(data[idx])
                return {"reply": detail_msg}
            except (ValueError, KeyError, IndexError) as e:
                msg = str(e) if "无效" in str(e) else "无效的序号格式"
                return {"reply": f"查询失败：{msg}"}
        list_msg = _format_list_view(data, main_cmd)
        return {"reply": list_msg}

    except RuntimeError as e:
        return {"reply": str(e)}
