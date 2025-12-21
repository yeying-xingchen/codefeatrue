"""程序总入口"""

import tomllib
from contextlib import asynccontextmanager
import importlib
import logging
from fastapi import FastAPI

from plugins import oseddl, github, bilibili, invite

app = FastAPI()

log = logging.getLogger("uvicorn")

loaded_plugins = {}

with open("config.toml", "rb") as f:
    _config_data = tomllib.load(f)

@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    应用生命周期管理
    
    :param application: FastAPI应用实例
    :type application: FastAPI
    """
    log.info("CodeFeatrue-破晓之码 正在启动")
    
    # 加载插件
    for plugin_name in _config_data["main"]["plugins"]:
        try:
            plugin = importlib.import_module(plugin_name)
            loaded_plugins[plugin_name] = plugin
            print(f"插件 {plugin_name} 加载成功")
            log.info("已加载插件: %s", list(loaded_plugins.keys()))
            
            # 调用插件启用方法
            if hasattr(plugin, 'on_enable'):
                plugin.on_enable(application)
                
        except AttributeError as e:
            print(f"插件 {plugin_name} 缺少必要方法: {e}")
    
    try:
        yield
    finally:
        # 清理资源
        print("CodeFeatrue-破晓之码 正在退出")
        # 如果插件有 on_disable 方法，则调用它
        for plugin_name, plugin in loaded_plugins.items():
            try:
                if hasattr(plugin, 'on_disable'):
                    plugin.on_disable()
            except Exception as e:
                print(f"插件 {plugin_name} 禁用时出错: {e}")

@app.post("/")
def main(info: dict):
    """
    处理接收到的消息
    
    :param info: Onebot实现端传入的信息
    :type info: dict
    """
    if info["post_type"]=="message" or info["post_type"]=="message_sent":
        message_type = info["message"][0]["type"]
        # 私聊/群 均传递
        if info["raw_message"].startswith("/oseddl"):
            return oseddl.on_command(message_type, info)
        elif info["message_type"] == "group":
        # 仅群
            if info["raw_message"].startswith("/github"):
                return github.on_command(message_type, info)
            elif info["message"][0]["type"] == "json":
                # Type == card
                return  bilibili.on_command(message_type, info)
    if info["post_type"]=="request":
        return invite.on_invite(info)
    return {}
