import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp
import threading
import tomllib
import json
from pathlib import Path
from .. import send_group_msg  # 导入通用消息发送函数

log = logging.getLogger("uvicorn")

# --- 插件元信息 ---
__plugin_meta__ = {
    "name": "Github 信息监控",
    "description": "监控 GitHub 仓库的 Star, Issue, PR, Commit 变化，并发送通知",
    "author": "yeying-xingchen",
    "version": "0.1.0",  # 更新版本号
    "events": ["message"]  # 添加需要订阅的事件
}

repo_status_storage: Dict[str, Dict[str, Dict]] = {}

# 存储每个仓库的轮询任务
polling_tasks: Dict[str, asyncio.Task] = {}

# 用于控制轮询频率的锁
poll_locks: Dict[str, asyncio.Lock] = {}

# 轮询间隔（秒）- 默认5分钟
DEFAULT_POLL_INTERVAL = 1 * 10

CONFIG_FILE_PATH = Path("config.toml")

def load_config():
    """从 config.toml 加载 GitHub 监控配置"""
    try:
        with open(CONFIG_FILE_PATH, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        log.warning(f"配置文件 {CONFIG_FILE_PATH} 不存在，使用默认配置")
        return {"github": {}}
    except tomllib.TOMLDecodeError as e:
        log.error(f"配置文件 {CONFIG_FILE_PATH} 格式错误: {e}")
        return {"github": {}}

def save_storage_to_config():
    """将当前存储状态保存到配置文件"""
    # 读取现有配置
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    
    # 解析现有配置
    if content.strip():
        try:
            existing_config = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            existing_config = {}
    else:
        existing_config = {}
    
    # 更新 GitHub 监控数据
    github_section = existing_config.get("github", {})
    github_section["monitoring_data"] = repo_status_storage
    existing_config["github"] = github_section
    
    # 重新构建 TOML 内容
    toml_content = _generate_toml_string(existing_config)
    
    # 写回配置文件
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(toml_content)
    
    return True

def _generate_toml_string(data, indent_level=0):
    """将 Python 字典转换为 TOML 格式的字符串"""
    toml_lines = []
    indent = "  " * indent_level
    
    for key, value in data.items():
        if isinstance(value, dict):
            # 如果值是字典，处理嵌套表
            if indent_level == 0:
                toml_lines.append(f"[{key}]")
                toml_lines.extend(_generate_toml_string(value, indent_level + 1).splitlines()[1:])
            else:
                toml_lines.append(f"{indent}[[{key}]]")
                toml_lines.extend(_generate_toml_string(value, indent_level + 1).splitlines()[1:])
        elif isinstance(value, list):
            # 如果值是列表，处理数组
            if value and isinstance(value[0], dict):
                # 列表元素是字典，按内联表格式处理
                toml_lines.append(f'{indent}{key} = [')
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        inline_table = ", ".join([
                            f'{k} = {json.dumps(v) if isinstance(v, (list, dict)) else f"\"{v}\"" if isinstance(v, str) else v}'
                            for k, v in item.items()
                        ])
                        toml_lines.append(f"  {indent}{{ {inline_table} }}" + ("," if i < len(value) - 1 else ""))
                    else:
                        toml_lines.append(f"  {indent}{json.dumps(item)}" + ("," if i < len(value) - 1 else ""))
                toml_lines.append(f"{indent}]")
            else:
                # 简单值列表
                formatted_values = [
                    f'"{v}"' if isinstance(v, str) else str(v) for v in value
                ]
                toml_lines.append(f'{indent}{key} = [{", ".join(formatted_values)}]')
        elif isinstance(value, str):
            toml_lines.append(f'{indent}{key} = "{value}"')
        elif isinstance(value, bool):
            toml_lines.append(f'{indent}{key} = {str(value).lower()}')
        elif isinstance(value, int) or isinstance(value, float):
            toml_lines.append(f'{indent}{key} = {value}')
        elif value is None:
            toml_lines.append(f'{indent}{key} = ""')  # TOML 中没有 null，用空字符串代替
    
    return "\n".join(toml_lines)

def initialize_storage_from_config():
    """从配置文件初始化存储状态"""
    global repo_status_storage
    config = load_config()
    github_config = config.get("github", {})
    monitoring_data = github_config.get("monitoring_data", {})
    repo_status_storage = monitoring_data

def get_repo_key(owner: str, name: str) -> str:
    """生成仓库的唯一标识键"""
    return f"{owner}/{name}"

async def fetch_github_data(session: aiohttp.ClientSession, url: str, headers: Dict[str, str]) -> Optional[Any]:
    """通用的 GitHub API 异步请求函数"""
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                log.warning(f"GitHub API 请求失败: {response.status}, URL: {url}")
                return None
    except Exception as e:
        log.error(f"请求 GitHub API 时出错: {e}, URL: {url}")
        return None

async def poll_repository(group_id: str, repo_owner: str, repo_name: str, token: Optional[str] = None):
    """轮询指定仓库并比较状态，发现变化则发送通知"""
    repo_key = get_repo_key(repo_owner, repo_name)
    lock_key = f"{group_id}:{repo_key}"
    
    if lock_key not in poll_locks:
        poll_locks[lock_key] = asyncio.Lock()

    async with poll_locks[lock_key]: # 确保同一时间只有一个任务在检查这个仓库
        log.info(f"开始轮询仓库 {repo_key} (群组 {group_id})")
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        async with aiohttp.ClientSession() as session:
            # 1. 获取仓库基本信息 (stars)
            repo_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
            repo_info = await fetch_github_data(session, repo_url, headers)
            if not repo_info:
                log.error(f"无法获取仓库信息: {repo_key}")
                return

            current_stars = repo_info.get('stargazers_count', 0)
            
            # 2. 获取 Issues (不含 PR)
            issues_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues?state=open&pulls=false"
            issues_list = await fetch_github_data(session, issues_url, headers)
            # Filter out null values and ensure we only get actual issues
            current_issues = [issue for issue in issues_list if issue and not issue.get('pull_request')] if issues_list else []
            
            # 3. 获取 PRs
            prs_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls?state=open"
            prs_list = await fetch_github_data(session, prs_url, headers)
            current_prs = [pr for pr in prs_list if pr] if prs_list else [] # PRs are already filtered by pulls=true
            
            # 4. 获取 Commits (默认分支)
            commits_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"
            commits_list = await fetch_github_data(session, commits_url, headers)
            current_commits = [commit for commit in commits_list if commit] if commits_list else []

            # --- 检查状态变化 ---
            storage_key = f"{group_id}:{repo_key}"
            if storage_key not in repo_status_storage:
                repo_status_storage[storage_key] = {
                    "last_stars": current_stars,
                    "last_issues": current_issues,
                    "last_prs": current_prs,
                    "last_commits": current_commits,
                }
                # 保存到配置文件
                save_storage_to_config()
                log.info(f"首次记录仓库 {repo_key} 的初始状态。")
                return # 首次记录，不发送通知

            stored_state = repo_status_storage[storage_key]
            notifications = []

            # Star 变化检查
            if current_stars > stored_state["last_stars"]:
                diff = current_stars - stored_state["last_stars"]
                notifications.append(f"🎉 {repo_key} 新增 {diff} 个 Star! (总计: {current_stars})")
                stored_state["last_stars"] = current_stars

            # Issue 变化检查
            current_issue_ids = {issue['id'] for issue in current_issues}
            stored_issue_ids = {issue['id'] for issue in stored_state["last_issues"]}
            new_issues = [issue for issue in current_issues if issue['id'] not in stored_issue_ids]

            for issue in new_issues:
                notifications.append(f"🆕 Issue #{issue['number']} 创建: '{issue['title']}' by @{issue['user']['login']}")

            stored_state["last_issues"] = current_issues

            # PR 变化检查
            current_pr_ids = {pr['id'] for pr in current_prs}
            stored_pr_ids = {pr['id'] for pr in stored_state["last_prs"]}
            new_prs = [pr for pr in current_prs if pr['id'] not in stored_pr_ids]

            for pr in new_prs:
                notifications.append(f"🔄 PR #{pr['number']} 创建: '{pr['title']}' by @{pr['user']['login']}")

            stored_state["last_prs"] = current_prs

            # Commit 变化检查
            # Note: Commits have 'sha' which is unique. Also checking 'commit.message' might be more robust against force-pushes.
            current_commit_shas = {commit['sha'] for commit in current_commits}
            stored_commit_shas = {commit['sha'] for commit in stored_state["last_commits"]}
            new_commits = [commit for commit in current_commits if commit['sha'] not in stored_commit_shas]

            for commit in new_commits:
                author_login = commit.get('author', {}).get('login', 'unknown')
                message = commit['commit'].get('message', 'no message')
                # Truncate long messages
                message = (message[:50] + "...") if len(message) > 50 else message
                notifications.append(f"📝 Commit: '{message}' by @{author_login}")

            stored_state["last_commits"] = current_commits

            # 发送通知
            if notifications:
                # 构造要发送的消息
                full_notification = f"【GitHub 监控】{repo_key}\n" + "\n".join(notifications)
                
                try:
                    # 使用通用的消息发送接口发送消息到群组
                    await send_group_msg(group_id=int(group_id), message=full_notification)
                    log.info(f"成功发送通知到群组 {group_id}")
                except Exception as e:
                    log.error(f"发送消息到群组 {group_id} 失败: {e}")
                    
            # 如果有变化，保存到配置文件
            if notifications:
                save_storage_to_config()


def start_polling(group_id: str, repo_owner: str, repo_name: str, token: Optional[str] = None):
    """启动对特定仓库的轮询任务"""
    task_key = f"{group_id}:{get_repo_key(repo_owner, repo_name)}"
    if task_key in polling_tasks and not polling_tasks[task_key].done():
        log.info(f"轮询任务 {task_key} 已存在，无需重复启动。")
        return

    async def run_task():
        while True:
            try:
                await poll_repository(group_id, repo_owner, repo_name, token)
            except asyncio.CancelledError:
                log.info(f"轮询任务 {task_key} 被取消。")
                break
            except Exception as e:
                log.error(f"轮询任务 {task_key} 出现未处理异常: {e}")
                # 避免因为异常导致任务退出，等待一段时间后重试
                await asyncio.sleep(DEFAULT_POLL_INTERVAL)
            # 等待设定的时间后再次检查
            await asyncio.sleep(DEFAULT_POLL_INTERVAL)

    # 确保在正确的事件循环中运行
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(run_task())
    except RuntimeError:
        # 如果没有运行的事件循环，则创建一个新任务并等待它
        async def run_in_new_loop():
            task = asyncio.create_task(run_task())
            polling_tasks[task_key] = task
            try:
                await task
            except asyncio.CancelledError:
                pass
        # 在新线程中运行事件循环
        thread = threading.Thread(target=lambda: asyncio.run(run_in_new_loop()), daemon=True)
        thread.start()
        return

    polling_tasks[task_key] = task
    log.info(f"已为群组 {group_id} 启动对仓库 {get_repo_key(repo_owner, repo_name)} 的轮询任务。")

def stop_polling(group_id: str, repo_owner: str, repo_name: str):
    """停止对特定仓库的轮询任务"""
    task_key = f"{group_id}:{get_repo_key(repo_owner, repo_name)}"
    if task_key in polling_tasks:
        task = polling_tasks[task_key]
        if not task.done():
            task.cancel()
            log.info(f"已取消群组 {group_id} 对仓库 {get_repo_key(repo_owner, repo_name)} 的轮询任务。")
        del polling_tasks[task_key]
        # 清理存储状态
        storage_key = f"{group_id}:{get_repo_key(repo_owner, repo_name)}"
        if storage_key in repo_status_storage:
            del repo_status_storage[storage_key]
            # 保存更改到配置文件
            save_storage_to_config()
        return True
    return False

# --- 插件主函数 ---

def on_enable(app):
    """
    插件启用时调用
    :param app: FastAPI应用实例 (或机器人框架实例)
    """
    global _app
    _app = app # 存储 app 实例以便后续使用 (例如发送消息)
    # 从配置文件初始化存储状态
    initialize_storage_from_config()
    log.info("Github 信息监控插件已启用。")

# 创建全局事件循环用于启动任务
loop = None

def on_event(event_type: str, info: dict):
    """
    处理接收到的命令
    :param event_type: 事件类型
    :type event_type: str
    :param info: 事件信息
    :type info: dict
    """
    global loop
    # 这里假设事件信息包含 'message_type' 和 'raw_message' 等字段
    # 请根据你实际使用的机器人框架调整字段名
    message_type = info.get("message_type") 
    if message_type != "group": # 假设只在群聊中生效
        return None

    raw = info.get("raw_message", "")
    raw_message = raw.strip()
    parts = raw_message.split()
    if not parts or parts[0] != "/github":
        return None

    # 获取群ID和发送者ID等信息
    group_id = info.get("group_id", "未知群ID")
    user_id = info.get("user_id", "未知用户ID")

    sub_command = raw[len("/github "):].strip()
    sub_parts = sub_command.split()

    if not sub_parts:
        help_text = (
            "【GitHub 监控插件】\n"
            "用法:\n"
            "/github add <owner/repo> [token] - 绑定仓库监控\n"
            "/github remove <owner/repo> - 移除仓库监控\n"
            "/github list - 查看当前群绑定的仓库\n"
        )
        return {"reply": help_text}

    command = sub_parts[0]
    repo_arg = sub_parts[1] if len(sub_parts) > 1 else None

    if command == "add":
        if not repo_arg:
            return {"reply": "请提供要添加的仓库路径，格式: /github add owner/repo"}

        # 解析 owner/repo
        try:
            owner, name = repo_arg.split("/")
        except ValueError:
            return {"reply": "仓库路径格式错误，请使用 'owner/repo' 格式。"}

        # 尝试获取 token (如果有提供)
        token = sub_parts[2] if len(sub_parts) > 2 else None 

        # 确保事件循环可用
        try:
            # 获取当前事件循环
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有运行的事件循环，则创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 启动轮询
        try:
            # 直接调用 start_polling，它现在是同步函数
            start_polling(str(group_id), owner, name, token)
        except Exception as e:
            log.error(f"启动轮询任务失败: {e}")
            return {"reply": "启动监控任务失败，请查看后台日志。"}

        reply = f"已开始监控仓库 {owner}/{name}，并将通知发送到此群聊。"
        return {"reply": reply}

    elif command == "remove":
        if not repo_arg:
            return {"reply": "请提供要移除的仓库路径，格式: /github remove owner/repo"}

        try:
            owner, name = repo_arg.split("/")
        except ValueError:
            return {"reply": "仓库路径格式错误，请使用 'owner/repo' 格式。"}

        success = stop_polling(str(group_id), owner, name)
        if success:
            reply = f"已停止监控仓库 {owner}/{name}。"
        else:
            reply = f"未找到对仓库 {owner}/{name} 的监控任务。"
        return {"reply": reply}

    elif command == "list":
        # 查找当前群组监控的所有仓库
        monitored_repos = []
        for key in repo_status_storage:
            if key.startswith(f"{group_id}:"):
                repo_path = key.split(":", 1)[1] # Remove "group_id:"
                monitored_repos.append(repo_path)
        
        if monitored_repos:
            reply = f"当前群 ({group_id}) 监控的仓库有:\n" + "\n".join([f"- {repo}" for repo in monitored_repos])
        else:
            reply = f"当前群 ({group_id}) 没有监控任何仓库。"
        return {"reply": reply}

    else:
        return {"reply": f"未知子命令: {command}。请输入 '/github' 查看帮助。"}

    return None