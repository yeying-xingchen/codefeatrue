"""配置管理模块，用于加载和读取 config.toml 中的插件配置。"""

import tomllib
from typing import Any


# 全局加载配置（模块级初始化）
with open("config.toml", "rb") as f:
    _config_data = tomllib.load(f)


def get(plugin: str, path: str) -> Any:
    """
    从配置文件中获取指定插件的配置项值。

    :param plugin: 插件名称（对应 TOML 中的表名）
    :param path: 配置项键名
    :return: 配置值；若插件为 'main' 则返回空字符串（特殊约定）
    :raises KeyError: 当 plugin 或 path 不存在且非 'main' 插件时
    """
    if plugin == "main":
        return ""

    # 安全访问嵌套字典
    try:
        return _config_data[plugin][path]
    except KeyError as e:
        raise KeyError(f"配置项缺失: plugin='{plugin}', path='{path}'") from e
