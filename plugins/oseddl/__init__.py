import requests
import yaml

def on_command(info: dict):
    sub_command = info["raw_message"].replace("/oseddl ","")
    sub_command = info["raw_message"].replace("/oseddl","")
    commands = sub_command.split()
    if sub_command == "":
        message = """Oseddl 功能使用帮助
/oseddl activites 查看活动列表
/oseddl competitions 查看比赛列表
/oseddl conferences 查看会议列表
"""
        return {"reply": message}
    elif commands[0] == "help":
        message = """Oseddl 功能使用帮助
/oseddl activites 查看活动列表
/oseddl competitions 查看比赛列表
/oseddl conferences 查看会议列表
"""
        return {"reply": message}
    resp = requests.get(f"https://github.com/hust-open-atom-club/open-source-deadlines/raw/refs/heads/main/data/{commands[0]}.yml")
    resp_info = yaml.load(resp.text, Loader=yaml.CLoader)
    message=""
    try:
        a = int(commands[1])-1
        active_list = []
        for active_info in resp_info:
            active_list.append(active_info)
        message = f"""标题：{active_list[a]["title"]}
介绍：{active_list[a]["description"]}
下一个事件：
  名称：{active_list[a]["events"][0]["timeline"][0]["comment"]}
  时间：{active_list[a]["events"][0]["timeline"][0]["deadline"]}
  链接：{active_list[a]["events"][0]["link"]}"""
        return {"reply": message}
    except IndexError:
        id = 1
        for active_info in resp_info:
            message = message+str(id)+"："+active_info["title"]+"\n"
            id+=1
        return {"reply": message+"\n您可以发送/oseddl "+commands[0]+" 序号查看该活动的具体信息"}