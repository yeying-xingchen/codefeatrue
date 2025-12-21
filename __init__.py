"""程序总入口"""

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
    log.error(f"配置文件未找到: {config_path}")
    raise
except Exception as e:
    log.error(f"配置文件加载失败: {e}")
    raise

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
            plugin = importlib.import_module("plugins."+plugin_name)
            loaded_plugins[plugin_name] = plugin
            print(f"插件 {plugin_name} 加载成功")
            log.info(str(loaded_plugins))
            plugin.on_enable(application)
        except AttributeError as ae:
            log.warning(f"插件 {plugin_name} 缺少必要的函数: {ae}")
        except Exception as e:
            log.error(f"插件 {plugin_name} 启动失败: {e}")
        except Exception as e:
            print(f"插件 {plugin_name} 启动失败: {e}")
    yield
    print("CodeFeatrue-破晓之码 正在退出")

app = FastAPI(lifespan=lifespan)

@app.post("/")
def main(info: dict):
    """
    处理接收到的消息
    
    :param info: Onebot实现端传入的信息
    :type info: dict
    """
    post_type = info["post_type"]
    if post_type == "message":
        # 验证必要字段存在
        if not info.get("message") or not info.get("raw_message"):
            log.warning("消息数据不完整")
            return {"error": "消息数据不完整"}            
        message_type = info["message"][0].get("type", "text")
        raw_message = info["raw_message"]
        # 私聊/群 均传递
        if raw_message.startswith("/oseddl"):
            plugin = loaded_plugins.get("oseddl")
            if plugin and hasattr(plugin, 'on_command'):
                return plugin.on_command(message_type, info)
        elif info.get("message_type") == "group":
            # 仅群
            if raw_message.startswith("/github"):
                plugin = loaded_plugins.get("github")
                if plugin and hasattr(plugin, 'on_command'):
                    return plugin.on_command(message_type, info)
            elif info["message"][0].get("type") == "json":
                # Type == card
                plugin = loaded_plugins.get("bilibili")
                if plugin and hasattr(plugin, 'on_command'):
                    return plugin.on_command(message_type, info)
    elif post_type == "request":
        plugin = loaded_plugins.get("invite")
        if plugin and hasattr(plugin, 'on_invite'):
            return plugin.on_invite(info)
    return {}
