"""程序总入口"""

import tomllib
import logging
import os
from adapter.onebot11 import app as ob11_app
from adapter.lark import wsClient as lark_app

log = logging.getLogger("uvicorn")

loaded_plugins = {}

# 使用加载配置文件
config_path = os.path.join(os.getcwd(), "config.toml")
try:
    with open(config_path, "rb") as f:
        _config_data = tomllib.load(f)
except FileNotFoundError:
    log.error("配置文件未找到: %s", config_path)
    raise


if __name__ == "__main__":
    if _config_data["main"]["adapter"] == "onebot11":
        log.info("使用 OneBot 11 适配器")
        import uvicorn
        uvicorn.run(ob11_app, host="0.0.0.0", port=_config_data["main"]["port"])
    elif _config_data["main"]["adapter"] == "lark":
        log.info("使用 Lark 适配器")
        lark_app.start()