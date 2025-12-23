"""华中科大食堂信息插件"""

import logging
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

log = logging.getLogger("uvicorn")

# 全局缓存食堂数据，避免重复抓取
_CANTEEN_DATA: List[Dict] = []
_LAST_FETCH_TIME: float = 0.0
_CACHE_EXPIRE_SECONDS = 3600  # 缓存1小时

__plugin_meta__ = {
    "name": "HUST 食堂信息",
    "description": "查询华中科技大学各食堂营业时间等。",
    "author": "yeying-xingchen",
    "version": "0.2.0",
    "events": ["message"]  # 只监听消息事件
}


def _fetch_canteen_data() -> List[Dict]:
    """从官网抓取食堂信息"""
    url = 'http://hq.hust.edu.cn/ysfw/stfw.htm'
    headers = {'User-Agent': 'Mozilla/5.0 (HUST Canteen Plugin)'}

    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    resp.encoding = 'utf-8'

    soup = BeautifulSoup(resp.text, 'html.parser')
    wznr = soup.select_one('.wznr')
    if not wznr:
        log.warning("HTML structure changed: .wznr not found")
        return []

    result = []

    for tr in wznr.select('tr'):
        tds = tr.find_all('td')
        if len(tds) < 2:
            continue

        second_td = tds[1]

        # 清理内联标签
        for inline in second_td.select('span, strong, a, b, i'):
            inline.replace_with(inline.get_text())

        # 提取所有段落文本
        fragments = [p.get_text().strip() for p in second_td.select('p') if p.get_text().strip()]
        if not fragments:
            # 若无 <p>，尝试按换行分割
            full_text = second_td.get_text()
            fragments = [line.strip() for line in full_text.splitlines() if line.strip()]

        info = _parse_fragments(fragments)
        if info.get("name"):
            result.append(info)

    return result


def _parse_fragments(fragments: List[str]) -> Dict:
    info = {
        'name': None,
        'position': None,
        'breakfast': None,
        'lunch': None,
        'dinner': None,
        'contact': None,
    }

    for text in fragments:
        text = text.strip()
        if not text:
            continue

        if re.match(r'^食堂地址[：:\s]*(.*)', text, re.IGNORECASE):
            info['position'] = re.sub(r'^食堂地址[：:\s]*', '', text).strip()
            continue

        time_match = re.search(r'(\d{1,2}[:：]\d{2})\s*[-–—至]+\s*(\d{1,2}[:：]\d{2})', text)
        if time_match:
            begin, end = time_match.groups()
            # 统一格式为 HH:MM
            begin = begin.replace('：', ':').zfill(5)
            end = end.replace('：', ':').zfill(5)
            times = {'begin': begin, 'end': end}
            if re.search(r'早|早餐', text):
                info['breakfast'] = times
            elif re.search(r'午|中午|午餐', text):
                info['lunch'] = times
            elif re.search(r'晚|晚餐', text):
                info['dinner'] = times
            continue

        phone_match = re.search(r'\b(\d{3,4}[-\s]?\d{7,8})\b', text)
        if phone_match:
            info['contact'] = phone_match.group(1).replace(' ', '-')
            continue

        clean_text = re.sub(r'^\d+[、.]?', '', text).strip()
        if clean_text and not info['name']:
            info['name'] = clean_text

    return info


class CanteenDataManager:
    """管理食堂数据，并缓存数据，避免重复抓取"""
    def __init__(self):
        self._data: List[Dict] = []
        self._last_fetch_time: float = 0.0

    def _is_expired(self) -> bool:
        return datetime.now().timestamp() - self._last_fetch_time > _CACHE_EXPIRE_SECONDS

    def get_data(self) -> List[Dict]:
        """获取食堂数据"""
        if not self._data or self._is_expired():
            log.info("Loading canteen data from HUST official website...")
            self._data = _fetch_canteen_data()
            self._last_fetch_time = datetime.now().timestamp()
            if not self._data:
                self._data = [
                    {"name": "数据加载失败", "position": "请稍后再试或联系管理员"}
                ]
        return self._data

    def clear_cache(self) -> None:
        """清空缓存数据"""
        self._data = []
        self._last_fetch_time = 0.0


# 实例化管理器
_canteen_manager = CanteenDataManager()

def _ensure_data_loaded():
    """确保食堂数据已加载"""
    # 直接从管理器获取数据，避免使用global
    global _CANTEEN_DATA
    _CANTEEN_DATA = _canteen_manager.get_data()


def _parse_time(time_str: str) -> Optional[datetime.time]:
    """将 'HH:MM' 字符串转为 time 对象"""
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return None


def _get_next_meal_end(canteen: Dict, now: datetime) -> Optional[timedelta]:
    """
    返回距离当前时间最近且仍在营业的餐次的剩余时间（timedelta）
    如果所有餐都已结束，返回 None
    """
    meals = []
    for meal_key in ['breakfast', 'lunch', 'dinner']:
        meal = canteen.get(meal_key)
        if not meal:
            continue
        begin = _parse_time(meal['begin'])
        end = _parse_time(meal['end'])
        if not begin or not end:
            continue
        meals.append((begin, end, meal_key))

    current_time = now.time()
    today = now.date()

    # 按开始时间排序
    meals.sort(key=lambda x: x[0])

    # 查找当前正在营业的餐
    for begin, end, _ in meals:
        if begin <= current_time <= end:
            end_dt = datetime.combine(today, end)
            return end_dt - now

    # 如果没有正在营业的，找今天之后最早开始的一餐（通常不会发生，但兜底）
    for begin, end, _ in meals:
        if current_time < begin:
            end_dt = datetime.combine(today, end)
            return end_dt - now

    # 所有餐都结束了
    return None


def _format_remaining_time(delta: Optional[timedelta]) -> str:
    if delta is None:
        return "今日已打烊"
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "今日已打烊"
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"还能吃 {hours} 小时 {minutes} 分钟"
    else:
        return f"还能吃 {minutes} 分钟"


def _format_canteen_detail(target: Dict) -> str:
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


def on_enable(_app):
    """插件启用时调用（可选初始化）"""
    # 可以添加实际初始化逻辑


def on_event(_event_type: str, info: dict):
    """
    处理接收到的消息事件
    """
    raw = info.get("raw_message", "").strip()
    if not raw.startswith("/hust-eat"):
        return {"reply": None}  # 不处理其他命令，保持一致的返回格式

    _ensure_data_loaded()

    parts = raw.split(maxsplit=1)
    if len(parts) == 1:
        # 只显示食堂名称 + 还能吃多久
        now = datetime.now()
        lines = []
        for idx, c in enumerate(_CANTEEN_DATA, start=1):
            name = c.get('name').replace('食堂', '') or f"食堂{idx}"
            remaining = _format_remaining_time(_get_next_meal_end(c, now))
            lines.append(f"{idx}. {name} —— {remaining}")

        reply = "华科食堂列表 \n发送 /hust-eat 序号/名称 \n 查看具体信息\n" + "\n".join(lines)
        return {"reply": reply}

    # 具体信息
    query = parts[1].strip()
    target = None

    # 尝试按序号匹配
    if query.isdigit():
        idx = int(query)
        if 1 <= idx <= len(_CANTEEN_DATA):
            target = _CANTEEN_DATA[idx - 1]
    else:
        # 按名称模糊匹配（忽略空格和大小写）
        query_norm = query.lower().replace(" ", "")
        for c in _CANTEEN_DATA:
            name_norm = (c.get('name') or "").lower().replace(" ", "")
            if query_norm in name_norm or name_norm in query_norm:
                target = c
                break

    if not target:
        return {"reply": "没有这个食堂"}

    detail = _format_canteen_detail(target)
    return {"reply": detail}
