import lark_oapi as lark
from lark_oapi.api.im.v1 import *
import json
import tomllib
import importlib
import logging
import os

log = logging.getLogger("LarkAdapter")

# 加载配置文件
config_path = os.path.join(os.getcwd(), "config.toml")
try:
    with open(config_path, "rb") as f:
        _config_data = tomllib.load(f)
except FileNotFoundError:
    log.error("配置文件未找到: %s", config_path)
    raise

# 插件管理
loaded_plugins = {}

# 初始化插件
def initialize_plugins():
    """初始化所有插件"""
    global loaded_plugins
    event_subscriptions = {}
    
    for plugin_name in _config_data["main"]["plugins"]:
        # 初始化插件
        try:
            try:
                plugin = importlib.import_module(plugin_name)
            except ImportError:
                plugin = importlib.import_module("plugins." + plugin_name)  # 尝试从plugins目录中加载插件
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
                # Lark adapter passes None since it doesn't have a FastAPI app like OneBot11
                # Plugins should handle the case where app is None appropriately
                plugin.on_enable(None)
        except AttributeError as ae:
            log.warning("插件 %s 缺少必要的函数: %s", plugin_name, ae)
    
    log.info("Lark 适配器插件加载完成，事件订阅: %s", event_subscriptions)
    return event_subscriptions

# 加载插件
event_subscriptions = initialize_plugins()

# 注册接收消息事件，处理接收到的消息。
def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
    # 首先尝试让插件处理消息
    # 构造事件数据
    message_data = {
        "message_type": "private" if data.event.message.chat_type == "p2p" else "group",
        "sub_type": "friend" if data.event.message.chat_type == "p2p" else "normal",
        "message_id": data.event.message.message_id,
        "user_id": data.event.sender.sender_id.user_id,
        "time": int(data.event.message.create_time),
        "self_id": lark.APP_ID,
        "post_type": "message",
        "raw_message": "",
        "font": 0,
        "sender": {
            "user_id": data.event.sender.sender_id.user_id,
            "nickname": getattr(data.event.sender.sender_id, 'name', 'Unknown'),
        }
    }

    # 解析消息内容
    if data.event.message.message_type == "text":
        content_json = json.loads(data.event.message.content)
        message_data["raw_message"] = content_json.get("text", "")
        message_data["message"] = content_json.get("text", "")
    else:
        message_data["raw_message"] = f"[未知消息类型: {data.event.message.message_type}]"
        message_data["message"] = f"[未知消息类型: {data.event.message.message_type}]"

    # 通知订阅了消息事件的所有插件
    if "message" in event_subscriptions:
        for plugin_name in event_subscriptions["message"]:
            plugin = loaded_plugins.get(plugin_name)
            if plugin and hasattr(plugin, 'on_event'):
                try:
                    result = plugin.on_event("message", message_data)
                    if result:
                        # 如果插件返回了结果，可以进行相应处理（如发送回复）
                        handle_plugin_response(data, result)
                except Exception as e:
                    log.error(f"插件 {plugin_name} 处理消息时出错: {e}")




def handle_plugin_response(data, result):
    """处理插件的响应"""
    if isinstance(result, dict) and "reply" in result:
        reply_content = result["reply"]
        
        # 确保回复内容是字符串
        if isinstance(reply_content, str):
            content = json.dumps({"text": reply_content})
            
            if data.event.message.chat_type == "p2p":
                request = (
                    CreateMessageRequest.builder()
                    .receive_id_type("chat_id")
                    .request_body(
                        CreateMessageRequestBody.builder()
                        .receive_id(data.event.message.chat_id)
                        .msg_type("text")
                        .content(content)
                        .build()
                    )
                    .build()
                )
                response = client.im.v1.message.create(request)
                
                if not response.success():
                    raise Exception(
                        f"client.im.v1.message.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
                    )
            else:
                request: ReplyMessageRequest = (
                    ReplyMessageRequest.builder()
                    .message_id(data.event.message.message_id)
                    .request_body(
                        ReplyMessageRequestBody.builder()
                        .content(content)
                        .msg_type("text")
                        .build()
                    )
                    .build()
                )
                response: ReplyMessageResponse = client.im.v1.message.reply(request)
                if not response.success():
                    raise Exception(
                        f"client.im.v1.message.reply failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
                    )


# 注册事件回调
event_handler = (
    lark.EventDispatcherHandler.builder("", "")
    .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
    .build()
)


# 创建 LarkClient 对象，用于请求OpenAPI, 并创建 LarkWSClient 对象，用于使用长连接接收事件。
client = lark.Client.builder().app_id(_config_data["adapter"]["app_id"]).app_secret(_config_data["adapter"]["app_secret"]).build()
wsClient = lark.ws.Client(
    _config_data["adapter"]["app_id"],
    _config_data["adapter"]["app_secret"],
    event_handler=event_handler,
    log_level=lark.LogLevel.DEBUG,
)