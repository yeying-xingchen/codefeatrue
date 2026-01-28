"""华中科大食堂信息插件"""

import logging
from datetime import datetime
from .format import format_remaining_time, format_canteen_detail
from .data import CanteenDataManager, get_next_meal_end

log = logging.getLogger("uvicorn")

__plugin_meta__ = {
    "name": "HUST 食堂信息",
    "description": "查询华中科技大学各食堂营业时间等。",
    "author": "yeying-xingchen",
    "version": "0.2.0",
    "events": ["message"]  # 只监听消息事件
}

canteen_data = CanteenDataManager().get_data()


def on_event(_event_type: str, info: dict):
    """
    处理接收到的消息事件
    """
    raw = info.get("raw_message", "").strip()
    if not raw.startswith("/hust-eat"):
        return None

    parts = raw.split(maxsplit=1)
    if len(parts) == 1:
        # 只显示食堂名称 + 还能吃多久
        now = datetime.now()
        lines = []
        for idx, c in enumerate(canteen_data, start=1):
            name = c.get('name').replace('食堂', '') or f"食堂{idx}"
            remaining = format_remaining_time(get_next_meal_end(c, now))
            lines.append(f"{idx}. {name} —— {remaining}")

        reply = "华科食堂列表 \n发送 /hust-eat 序号 \n 查看具体信息\n" + "\n".join(lines)
        return {"reply": reply}

    # 具体信息
    query = parts[1].strip()
    target = None

    # 尝试按序号匹配
    if query.isdigit():
        idx = int(query)
        if 1 <= idx <= len(canteen_data):
            target = canteen_data[idx - 1]
    else:
        return {"reply": "没有这个食堂"}

    detail = format_canteen_detail(target)
    return {"reply": detail}
