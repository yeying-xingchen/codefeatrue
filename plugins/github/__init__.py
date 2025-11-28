"""Github 信息监控插件"""


def on_command(message_type: str, info: dict):
    """
    处理接收到的命令

    :param message_type: 消息类型
    :type message_type: str
    :param info: 信息
    :type info: dict
    """
    if message_type == "text":
        raw = info.get("raw_message", "")
        if raw.startswith("/github "):
            sub_command = raw[len("/github "):]
            if sub_command.startswith("add "):
                repo = sub_command[len("add "):]
                group_name = info.get("group_name", "未知群")
                group_id = info.get("group_id", "未知ID")
                reply = (
                    f"已绑定仓库 {repo} 到 {group_name} "
                    f"群号 {group_id}"
                )
                return {"reply": reply}
    return {}
