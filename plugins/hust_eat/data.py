"""
获取数据
"""

import logging
import re
from datetime import timedelta, datetime
from typing import Optional, Dict, List
import requests
from bs4 import BeautifulSoup

# 全局缓存食堂数据，避免重复抓取
_LAST_FETCH_TIME: float = 0.0
_CACHE_EXPIRE_SECONDS = 3600  # 缓存1小时

log = logging.getLogger("uvicorn")

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

def _parse_time(time_str: str) -> Optional[datetime.time]:
    """将 'HH:MM' 字符串转为 time 对象"""
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return None


def get_next_meal_end(canteen: Dict, now: datetime) -> Optional[timedelta]:
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
