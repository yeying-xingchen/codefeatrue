"""程序总入口"""

from asyncio import CancelledError
import tomllib
from contextlib import asynccontextmanager
import importlib
import logging
from pathlib import Path
from fastapi import FastAPI

log = logging.getLogger("uvicorn")

loaded_plugins = {}

# 使用绝对路径加载配置文件
config_path = Path(__file__).parent / "config.toml"
try:
    with open(config_path, "rb") as f:
        _config_data = tomllib.load(f)
except FileNotFoundError:
    log.error("配置文件未找到: %s", config_path)
    raise

@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    应用生命周期管理
    
    :param application: FastAPI应用实例
    :type application: FastAPI
    """
    try:
        log.info("CodeFeatrue-破晓之码 正在启动")
        # 存储插件事件映射
        event_subscriptions = {}
        for plugin_name in _config_data["main"]["plugins"]:
            # 初始化插件
            try:
                plugin = importlib.import_module("plugins." + plugin_name)
                loaded_plugins[plugin_name] = plugin
                plugin_meta = getattr(plugin, '__plugin_meta__', {})
                events = plugin_meta.get('events', [])    
                # 订阅事件
                for event in events:
                    if event not in event_subscriptions:
                        event_subscriptions[event] = []
                    event_subscriptions[event].append(plugin_name)           
                log.info("插件 %s 加载成功", plugin_name)
                # 调用插件启用函数
                if hasattr(plugin, 'on_enable'):
                    plugin.on_enable(application)
            except AttributeError as ae:
                log.warning("插件 %s 缺少必要的函数: %s", plugin_name, ae)
        # 将事件订阅信息存储到应用状态中
        application.state.event_subscriptions = event_subscriptions
        log.info("事件订阅: %s", event_subscriptions)
        yield
        log.info("CodeFeatrue-破晓之码 正在退出")
    except (CancelledError, KeyboardInterrupt) as e:
        log.error("CodeFeatrue-破晓之码 启动失败: 在启动过程中被用户手动关闭。%s", e)
        raise

app = FastAPI(lifespan=lifespan)

@app.post("/")
def main(info: dict):
    """
    处理接收到的消息
    
    :param info: Onebot实现端传入的信息
    :type info: dict
    """
    post_type = info["post_type"]
    # 通知订阅了该事件的所有插件
    event_subscriptions = app.state.event_subscriptions
    if post_type in event_subscriptions:
        for plugin_name in event_subscriptions[post_type]:
            plugin = loaded_plugins.get(plugin_name)
            if plugin and hasattr(plugin, 'on_event'):
                return_info = plugin.on_event(post_type, info)
                if return_info:
                    return return_info
                else:
                    log.info("插件 %s 未处理事件 %s", plugin_name, post_type)
    return { }
