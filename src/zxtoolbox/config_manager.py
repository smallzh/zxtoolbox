"""zxtool.toml 配置文件管理模块。

生成和管理 ~/.config/zxtool.toml 配置文件，支持 MkDocs 和 Git 配置。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# 默认配置文件路径
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "zxtool.toml"


def _escape_toml_string(value: str) -> str:
    """转义 TOML 字符串中的特殊字符。

    Args:
        value: 原始字符串。

    Returns:
        转义后的 TOML 安全字符串。
    """
    # 如果字符串包含特殊字符，使用双引号包裹并转义内部字符
    special_chars = {'"', "\\", "\n", "\t", "\r"}
    if any(c in value for c in special_chars):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        escaped = escaped.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
        return f'"{escaped}"'
    return f'"{value}"'


def _generate_mkdocs_section(projects: list[dict]) -> str:
    """生成 MkDocs 配置部分。

    Args:
        projects: 项目配置列表，每个元素包含 project_dir, output_dir 等。

    Returns:
        TOML 格式的 MkDocs 配置字符串。
    """
    if not projects:
        return ""

    lines = [
        "# ============================================",
        "# MkDocs 批量构建配置",
        "# ============================================",
        "",
    ]

    for proj in projects:
        lines.append("[[projects]]")
        lines.append(
            f"project_dir = {_escape_toml_string(proj.get('project_dir', ''))}"
        )

        if proj.get("output_dir"):
            lines.append(f"output_dir = {_escape_toml_string(proj['output_dir'])}")

        if proj.get("config_file"):
            lines.append(f"config_file = {_escape_toml_string(proj['config_file'])}")

        if proj.get("strict"):
            lines.append("strict = true")

        lines.append("")

    return "\n".join(lines)


def _generate_git_section(users: list[dict]) -> str:
    """生成 Git 配置部分。

    Args:
        users: 用户配置列表，每个元素包含 name 和 email。

    Returns:
        TOML 格式的 Git 配置字符串。
    """
    if not users:
        return ""

    lines = [
        "# ============================================",
        "# Git 仓库用户配置",
        "# ============================================",
        "",
    ]
    lines.append("[git]")
    lines.append("")

    for user in users:
        lines.append("[[git.user]]")
        if user.get("name"):
            lines.append(f"name = {_escape_toml_string(user['name'])}")
        if user.get("email"):
            lines.append(f"email = {_escape_toml_string(user['email'])}")
        lines.append("")

    return "\n".join(lines)


def generate_config_content(
    mkdocs_projects: list[dict] | None = None,
    git_users: list[dict] | None = None,
) -> str:
    """生成完整的 zxtool.toml 配置文件内容。

    Args:
        mkdocs_projects: MkDocs 项目配置列表。
        git_users: Git 用户配置列表。

    Returns:
        完整的 TOML 配置文件内容。
    """
    parts = []

    # 文件头
    parts.append("# zxtool 全局配置文件")
    parts.append("# 路径: ~/.config/zxtool.toml")
    parts.append("#")
    parts.append("# 用法:")
    parts.append("#   zxtool mkdocs batch          # 批量构建 MkDocs 项目")
    parts.append("#   zxtool git config fill       # 填充 Git 仓库 user 配置")
    parts.append("")

    # MkDocs 配置
    mkdocs_section = _generate_mkdocs_section(mkdocs_projects or [])
    if mkdocs_section:
        parts.append(mkdocs_section)

    # Git 配置
    git_section = _generate_git_section(git_users or [])
    if git_section:
        parts.append(git_section)

    # 如果没有任何配置，添加注释说明
    if not mkdocs_projects and not git_users:
        parts.append("# 暂无配置项")
        parts.append("# 运行 'zxtool config init' 交互式生成配置")
        parts.append("")

    return "\n".join(parts)


def write_config(
    config_path: str | Path | None = None,
    mkdocs_projects: list[dict] | None = None,
    git_users: list[dict] | None = None,
    force: bool = False,
) -> bool:
    """写入 zxtool.toml 配置文件。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。
        mkdocs_projects: MkDocs 项目配置列表。
        git_users: Git 用户配置列表。
        force: 是否覆盖已存在的文件。

    Returns:
        是否写入成功。
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = Path(config_path).resolve()

    # 检查文件是否已存在
    if config_path.exists() and not force:
        print(f"[WARN] 配置文件已存在: {config_path}")
        print("使用 --force 覆盖，或先备份现有文件。")
        return False

    # 确保目录存在
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成配置内容
    content = generate_config_content(
        mkdocs_projects=mkdocs_projects,
        git_users=git_users,
    )

    # 写入文件
    config_path.write_text(content, encoding="utf-8")
    print(f"[OK] 配置文件已创建: {config_path}")
    return True


def interactive_init(
    config_path: str | Path | None = None, force: bool = False
) -> bool:
    """交互式初始化 zxtool.toml 配置文件。

    通过命令行向导收集用户输入，生成配置文件。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。
        force: 是否覆盖已存在的文件。

    Returns:
        是否初始化成功。
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = Path(config_path).resolve()

    print("=" * 50)
    print("  zxtool.toml 配置初始化向导")
    print("=" * 50)
    print(f"\n配置文件路径: {config_path}\n")

    if config_path.exists() and not force:
        print(f"[WARN] 文件已存在: {config_path}")
        try:
            answer = input("是否覆盖? (y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n取消操作")
            return False
        if answer not in ("y", "yes"):
            print("取消操作")
            return False

    mkdocs_projects = []
    git_users = []

    # --- MkDocs 配置 ---
    print("\n--- MkDocs 批量构建配置 ---")
    print("添加需要批量构建的 MkDocs 项目（留空跳过）")

    while True:
        try:
            project_dir = input(f"\n项目路径 [{len(mkdocs_projects) + 1}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not project_dir:
            break

        project = {"project_dir": project_dir}

        output_dir = input("  输出目录 [默认 site]: ").strip()
        if output_dir:
            project["output_dir"] = output_dir

        config_file = input("  自定义配置文件 [默认 mkdocs.yml]: ").strip()
        if config_file:
            project["config_file"] = config_file

        strict = input("  启用严格模式? (y/N): ").strip().lower()
        if strict in ("y", "yes"):
            project["strict"] = True

        mkdocs_projects.append(project)
        print(f"  [OK] 已添加项目: {project_dir}")

    # --- Git 配置 ---
    print("\n--- Git 仓库用户配置 ---")
    print("添加 Git user.name 和 user.email（留空跳过）")

    while True:
        try:
            name = input(f"\ngit user.name [{len(git_users) + 1}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not name:
            break

        try:
            email = input("git user.email: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n取消操作")
            return False

        if not email:
            print("  [WARN] email 不能为空，跳过")
            continue

        git_users.append({"name": name, "email": email})
        print(f"  [OK] 已添加用户: {name} <{email}>")

    # --- 确认并写入 ---
    print("\n" + "=" * 50)
    print("  配置摘要")
    print("=" * 50)

    if mkdocs_projects:
        print(f"\nMkDocs 项目: {len(mkdocs_projects)} 个")
        for proj in mkdocs_projects:
            print(f"  - {proj['project_dir']}")
            if proj.get("output_dir"):
                print(f"    输出: {proj['output_dir']}")
    else:
        print("\nMkDocs 项目: 无")

    if git_users:
        print(f"\nGit 用户: {len(git_users)} 个")
        for user in git_users:
            print(f"  - {user['name']} <{user['email']}>")
    else:
        print("\nGit 用户: 无")

    print()

    try:
        answer = input("确认生成配置文件? (Y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n取消操作")
        return False

    if answer in ("n", "no"):
        print("取消操作")
        return False

    success = write_config(
        config_path=config_path,
        mkdocs_projects=mkdocs_projects if mkdocs_projects else None,
        git_users=git_users if git_users else None,
        force=True,
    )

    if success:
        print("\n[OK] 配置初始化完成!")
        print(f"\n查看配置: cat {config_path}")
        print(f"\n使用方式:")
        print(f"  zxtool mkdocs batch              # 批量构建 MkDocs")
        print(f"  zxtool git config fill           # 填充 Git user 配置")

    return success


def show_config(config_path: str | Path | None = None) -> None:
    """显示当前配置文件内容。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = Path(config_path).resolve()

    if not config_path.exists():
        print(f"[WARN] 配置文件不存在: {config_path}")
        print("运行 'zxtool config init' 初始化配置。")
        return

    print(f"配置文件: {config_path}")
    print("-" * 40)
    print(config_path.read_text(encoding="utf-8"))


def main() -> None:
    """配置文件管理的入口函数。"""
    print("配置文件管理")
    print("")
    print("用法: zxtool config <子命令> [选项]")
    print("")
    print("子命令:")
    print("  init      交互式初始化配置文件")
    print("  show      显示当前配置内容")
    print("")
    print("示例:")
    print("  zxtool config init                  # 交互式生成配置")
    print("  zxtool config init --force          # 覆盖已有配置")
    print("  zxtool config show                  # 查看当前配置")
    print("  zxtool config show --path ./my.toml # 查看指定配置")
