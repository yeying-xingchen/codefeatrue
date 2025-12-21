"""程序总入口"""

import tomllib
from contextlib import asynccontextmanager
import importlib
import logging
from fastapi import FastAPI

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
    for plugin_name in _config_data["main"]["plugins"]:
        # 初始化插件
        try:
            plugin = importlib.import_module(plugin_name)
            loaded_plugins[plugin_name] = plugin
            log.info(str(loaded_plugins))
            plugin.on_enable(application)
        except AttributeError:
            pass
        except Exception as e:
            print(f"插件 {plugin_name} 启动失败: {e}")
    yield
    print("CodeFeatrue-破晓之码 正在退出")

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
            return loaded_plugins["oseddl"].on_command(message_type, info)
        elif info["message_type"] == "group":
        # 仅群
            if info["raw_message"].startswith("/github"):
                return loaded_plugins["github"].on_command(message_type, info)
            elif info["message"][0]["type"] == "json":
                # Type == card
                return  loaded_plugins["bilibili"].on_command(message_type, info)
    if info["post_type"]=="request":
        return loaded_plugins["invite"].on_invite(info)
    return {}
