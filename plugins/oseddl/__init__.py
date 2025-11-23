import requests
import yaml
import config

# 常量定义
TOKEN = config.get("oseddl", "oseddl_github_token")
HELP_MESSAGE = """Oseddl 功能使用帮助
/oseddl activities 查看活动列表
/oseddl competitions 查看比赛列表
/oseddl conferences 查看会议列表
"""
BASE_URL = config.get("oseddl", "oseddl_base_url")
VALID_COMMANDS = {"activities", "competitions", "conferences"}

def on_command(info: dict):
    # 提取并清理命令
    raw_message = info.get("raw_message", "").strip()
    command_parts = raw_message.split()
    
    # 检查命令格式
    if len(command_parts) < 1 or command_parts[0] != "/oseddl":
        return {"reply": "无效的命令格式"}
    
    # 提取子命令
    sub_command_parts = command_parts[1:]
    
    # 处理空命令和help命令
    if not sub_command_parts or sub_command_parts[0] == "help":
        return {"reply": HELP_MESSAGE}
    
    main_command = sub_command_parts[0]
    
    # 验证主命令
    if main_command not in VALID_COMMANDS:
        return {"reply": f"无效的命令，请使用以下有效命令：{', '.join(VALID_COMMANDS)}"}
    
    # 获取数据
    try:
        if TOKEN != "":
            headers = {"Authorization": "Bearer "+TOKEN}
            resp = requests.get(f"{BASE_URL}/{main_command}.yml", timeout=15, headers=headers)
        else:
            resp = requests.get(f"{BASE_URL}/{main_command}.yml", timeout=15)
        resp.raise_for_status()
        resp_info = yaml.safe_load(resp.text)
        
        if not resp_info:
            return {"reply": "未找到相关数据"}
            
    except requests.exceptions.RequestException as e:
        return {"reply": f"获取数据失败：{str(e)}"}
    except yaml.YAMLError as e:
        return {"reply": f"解析数据失败：{str(e)}"}
    
    # 具体条目查询
    if len(sub_command_parts) >= 2:
        try:
            index = int(sub_command_parts[1]) - 1
            if index < 0 or index >= len(resp_info):
                return {"reply": f"序号无效，请在 1-{len(resp_info)} 范围内选择"}
            
            active_info = resp_info[index]
            events = active_info.get("events", [])
            
            if not events or not events[0].get("timeline"):
                return {"reply": "该活动暂无事件信息"}
            
            timeline = events[0]["timeline"][0]
            message = f"""标题：{active_info.get('title', '无')}
介绍：{active_info.get('description', '无')}
下一个事件：
  名称：{timeline.get('comment', '无')}
  时间：{timeline.get('deadline', '无')}
  链接：{events[0].get('link', '无')}"""
            
            return {"reply": message}
            
        except (ValueError, IndexError):
            return {"reply": "无效的序号格式"}
    else:
        message = "\n".join(f"{i+1}：{item['title']}" for i, item in enumerate(resp_info))
        return {"reply": f"{message}\n\n您可以发送 /oseddl {main_command} 序号 查看该活动的具体信息"}