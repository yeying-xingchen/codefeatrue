"""
格式化数据
"""

from datetime import timedelta
from typing import Optional, Dict

def format_remaining_time(delta: Optional[timedelta]) -> str:
    """格式化剩余时间"""
    if delta is None:
        return "今日已打烊"
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "今日已打烊"
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"还能吃 {hours} 小时 {minutes} 分钟"
    return f"还能吃 {minutes} 分钟"


def format_canteen_detail(target: Dict) -> str:
    """格式化食堂详细信息"""
    name = target.get('name')
    pos = target.get('position')
    contact = target.get('contact')

    def fmt_time(t):
        if t:
            return f"{t['begin']} - {t['end']}"
        return "未提供"

    bf = fmt_time(target.get('breakfast'))
    ln = fmt_time(target.get('lunch'))
    dn = fmt_time(target.get('dinner'))

    detail = (
        f"【{name}】\n"
        f"📍 地址：{pos}\n"
        f"🍳 早餐：{bf}\n"
        f"🍲 午餐：{ln}\n"
        f"🍛 晚餐：{dn}"
        + (f"\n📞 电话：{contact}" if contact else "")
    )
    return detail
