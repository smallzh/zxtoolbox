"""Git 仓库配置管理模块。

检查和填充 Git 仓库的 .git/config 中的 user.name 和 user.email。
支持从 ~/.config/zxtool.toml 的 [[git.user]] 节点读取默认配置。
支持从远程仓库拉取更新（git pull）。
"""

import configparser
import os
import subprocess
import sys
from pathlib import Path


def find_git_dir(start_path: str | None = None) -> Path | None:
    """从指定路径向上查找 .git 目录。

    Args:
        start_path: 起始搜索路径，默认为当前工作目录。

    Returns:
        .git 目录的 Path，如果未找到则返回 None。
    """
    if start_path is None:
        start_path = os.getcwd()

    current = Path(start_path).resolve()
    while True:
        git_dir = current / ".git"
        if git_dir.is_dir():
            return git_dir
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def read_git_config(git_dir: Path) -> configparser.ConfigParser | None:
    """读取 .git/config 文件。

    Args:
        git_dir: .git 目录路径。

    Returns:
        解析后的 ConfigParser 对象，如果文件不存在则返回 None。
    """
    config_file = git_dir / "config"
    if not config_file.exists():
        return None

    config = configparser.ConfigParser(strict=False)
    config.read(str(config_file))
    return config


def get_user_info(config: configparser.ConfigParser) -> dict[str, str]:
    """从 git config 中获取 user.name 和 user.email。

    Args:
        config: 已解析的 git config 对象。

    Returns:
        包含 name 和 email 的字典，键不存在时值为空字符串。
    """
    if "user" not in config:
        return {"name": "", "email": ""}

    return {
        "name": config.get("user", "name", fallback=""),
        "email": config.get("user", "email", fallback=""),
    }


def set_user_info(config: configparser.ConfigParser, name: str, email: str) -> None:
    """在 git config 中设置 user.name 和 user.email。

    Args:
        config: 已解析的 git config 对象。
        name: 用户名。
        email: 用户邮箱。
    """
    if "user" not in config:
        config.add_section("user")
    config.set("user", "name", name)
    config.set("user", "email", email)


def write_git_config(git_dir: Path, config: configparser.ConfigParser) -> None:
    """将配置写回 .git/config 文件。

    Args:
        git_dir: .git 目录路径。
        config: 要写入的 ConfigParser 对象。
    """
    config_file = git_dir / "config"
    with open(config_file, "w", encoding="utf-8") as f:
        config.write(f)


def load_zxtool_config(config_path: str | None = None) -> list[dict[str, str]]:
    """从 zxtool.toml 配置文件中读取 [[git.user]] 节点。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。

    Returns:
        git.user 配置列表，每个元素包含 name 和 email。
    """
    if config_path is None:
        config_path = os.path.expanduser("~/.config/zxtool.toml")

    config_file = Path(config_path)
    if not config_file.exists():
        return []

    try:
        import tomllib
    except ImportError:
        print("错误: 需要 Python 3.11+ 以支持 tomllib 模块")
        return []

    with open(config_file, "rb") as f:
        data = tomllib.load(f)

    git_users = data.get("git", {}).get("user", [])
    if not isinstance(git_users, list):
        return []

    return [
        {"name": u.get("name", ""), "email": u.get("email", "")}
        for u in git_users
        if isinstance(u, dict)
    ]


def check_git_config(project_dir: str | None = None) -> dict | None:
    """检查指定项目的 git user 配置。

    Args:
        project_dir: 项目目录路径，默认为当前工作目录。

    Returns:
        如果找到 user 配置，返回 {name, email} 字典；
        如果未找到 user 配置，返回 None。
    """
    git_dir = find_git_dir(project_dir)
    if git_dir is None:
        print(f"错误: 未找到 Git 仓库 ({project_dir or os.getcwd()})")
        return None

    config = read_git_config(git_dir)
    if config is None:
        print(f"错误: 未找到 .git/config 文件 ({git_dir})")
        return None

    user_info = get_user_info(config)
    if user_info["name"] and user_info["email"]:
        return user_info

    return None


def fill_git_config(
    project_dir: str | None = None,
    config_file: str | None = None,
    name: str | None = None,
    email: str | None = None,
) -> bool:
    """填充项目的 git user 配置。

    优先级：
    1. 命令行指定的 --name 和 --email
    2. 交互式输入
    3. 从 zxtool.toml 配置文件读取

    Args:
        project_dir: 项目目录路径。
        config_file: zxtool.toml 配置文件路径。
        name: 指定的用户名。
        email: 指定的用户邮箱。

    Returns:
        是否成功填充配置。
    """
    git_dir = find_git_dir(project_dir)
    if git_dir is None:
        print(f"错误: 未找到 Git 仓库 ({project_dir or os.getcwd()})")
        return False

    config = read_git_config(git_dir)
    if config is None:
        print(f"错误: 未找到 .git/config 文件 ({git_dir})")
        return False

    user_info = get_user_info(config)

    # 如果已有完整配置，直接返回
    if user_info["name"] and user_info["email"]:
        print(f"项目已配置 git user:")
        print(f"  name:  {user_info['name']}")
        print(f"  email: {user_info['email']}")
        return True

    # 确定要使用的 name 和 email
    final_name = name
    final_email = email

    # 如果命令行未指定，尝试从配置文件读取
    if not final_name or not final_email:
        zxtool_users = load_zxtool_config(config_file)
        if zxtool_users:
            # 使用第一个可用的 user 配置
            user_config = zxtool_users[0]
            if not final_name:
                final_name = user_config.get("name", "")
            if not final_email:
                final_email = user_config.get("email", "")

    # 如果配置文件也没有，提示用户输入
    if not final_name:
        try:
            final_name = input("请输入 git user.name: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n取消操作")
            return False

    if not final_email:
        try:
            final_email = input("请输入 git user.email: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n取消操作")
            return False

    if not final_name or not final_email:
        print("错误: name 和 email 不能为空")
        return False

    # 写入配置
    set_user_info(config, final_name, final_email)
    write_git_config(git_dir, config)

    print(f"已配置 git user:")
    print(f"  name:  {final_name}")
    print(f"  email: {final_email}")
    print(f"  仓库:  {git_dir.parent}")
    return True


def git_pull(project_dir: str | None = None, remote: str | None = None, branch: str | None = None) -> bool:
    """从远程仓库拉取更新（git pull）。

    Args:
        project_dir: 项目目录路径，默认为当前工作目录。
        remote: 远程仓库名称（默认使用仓库配置的 upstream）。
        branch: 分支名称（默认使用当前分支）。

    Returns:
        是否成功拉取更新。
    """
    if project_dir is None:
        project_dir = os.getcwd()

    project_path = Path(project_dir).resolve()
    git_dir = find_git_dir(str(project_path))
    if git_dir is None:
        print(f"错误: 未找到 Git 仓库 ({project_path})")
        return False

    # 构建 git pull 命令
    cmd = ["git", "pull"]
    if remote:
        cmd.append(remote)
        if branch:
            cmd.append(branch)

    try:
        result = subprocess.run(
            cmd,
            cwd=str(git_dir.parent),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
        if result.returncode != 0:
            print(f"错误: git pull 失败 (退出码 {result.returncode})")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("错误: git pull 超时（120 秒）")
        return False
    except FileNotFoundError:
        print("错误: 未找到 git 命令，请确认 git 已安装并在 PATH 中")
        return False


def main() -> None:
    """Git 配置管理的入口函数。"""
    print("Git 配置管理")
    print(
        "用法: zxtool git config [项目路径] [--config 配置文件] [--name 名称] [--email 邮箱]"
    )
    print("")
    print("子命令:")
    print("  check   检查项目的 git user 配置")
    print("  fill    填充项目的 git user 配置")
    print("")
    print("示例:")
    print("  zxtool git config check                    # 检查当前目录")
    print("  zxtool git config fill                     # 填充当前目录")
    print("  zxtool git config check /path/to/project   # 检查指定项目")
    print("  zxtool git config fill --name 'John' --email 'john@example.com'")
    print("  zxtool git config fill --config ~/.config/zxtool.toml")
