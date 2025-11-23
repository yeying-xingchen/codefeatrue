def on_command(info: dict):
    sub_command = info["raw_message"].replace("/github ","")
    if sub_command.startswith("add"):

        return {
            "reply":"已绑定仓库"+sub_command.replace("add ", "")+"到 "+info["group_name"]+" 群号"+str(info["group_id"])
            }