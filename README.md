# CodeFeatrue

## 介绍

CodeFeatrue 是一个基于Python 开发的帮助开发的聊天机器人。他能帮助开发者查询活动信息，提醒issue信息等。

## 部署

### 安装依赖

执行以下命令，安装必要依赖：

```bash
uv sync
```

### 填写配置文件

根据需要填写配置文件（config.toml），您可以在配置文件中修改oseddl_base_url加快数据获取。

### 启动

执行以下命令，启动机器人：

```bash
uv run uvicorn main:app --port 8000 --host 0.0.0.0
```

您可以修改 '--port' 后面的数字设置端口。

### 修改

您可以在遵循开源协议的情况下根据您的需求修改，添加插件。
插件文件存放在 plugins 目录下，每个插件是一个 Python 包，文件夹名即为插件包名。
