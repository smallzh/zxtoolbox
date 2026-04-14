"""MkDocs 项目管理模块。

提供以下功能：
1. 创建新的 MkDocs 项目
2. 构建 MkDocs 项目到指定目录
3. 批量构建多个 MkDocs 项目（基于 TOML 配置文件）
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import tomllib


# 默认配置文件路径
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "zxtool.toml"


# MkDocs 新项目默认模板
DEFAULT_MKDOCS_YML = """site_name: My Docs
theme:
  name: mkdocs
"""

DEFAULT_INDEX_MD = """# Welcome to MkDocs

For full documentation visit [mkdocs.org](https://www.mkdocs.org).

## Commands

* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs -h` - Print help message and exit.
"""


def create_project(project_dir: str | Path, site_name: str | None = None) -> Path:
    """创建一个新的 MkDocs 项目。

    Args:
        project_dir: 项目目录路径（不存在则创建，存在则复用）
        site_name: 站点名称，默认使用目录名

    Returns:
        创建的项目目录路径
    """
    project_path = Path(project_dir).resolve()
    project_path.mkdir(parents=True, exist_ok=True)

    # 创建 docs 目录
    docs_dir = project_path / "docs"
    docs_dir.mkdir(exist_ok=True)

    # 生成 mkdocs.yml
    mkdocs_yml = project_path / "mkdocs.yml"
    if not mkdocs_yml.exists():
        name = site_name or project_path.name
        content = f"site_name: {name}\n{DEFAULT_MKDOCS_YML.split(chr(10), 1)[1]}"
        mkdocs_yml.write_text(content, encoding="utf-8")
        print(f"[OK] 创建配置文件: {mkdocs_yml}")
    else:
        print(f"[WARN] 配置文件已存在，跳过: {mkdocs_yml}")

    # 生成 docs/index.md
    index_md = docs_dir / "index.md"
    if not index_md.exists():
        index_md.write_text(DEFAULT_INDEX_MD, encoding="utf-8")
        print(f"[OK] 创建文档首页: {index_md}")
    else:
        print(f"[WARN] 文档首页已存在，跳过: {index_md}")

    print(f"\n[OK] MkDocs 项目创建成功: {project_path}")
    return project_path


def build_project(
    project_dir: str | Path,
    output_dir: str | Path | None = None,
    config_file: str | Path | None = None,
    strict: bool = False,
) -> bool:
    """构建单个 MkDocs 项目到指定输出目录。

    Args:
        project_dir: MkDocs 项目目录（包含 mkdocs.yml）
        output_dir: 输出目录，默认使用 mkdocs.yml 中的 site_dir 配置
        config_file: 配置文件路径（相对或绝对路径），默认使用项目目录下的 mkdocs.yml
        strict: 是否启用严格模式（警告视为错误）

    Returns:
        构建是否成功
    """
    project_path = Path(project_dir).resolve()

    # 确定配置文件路径
    if config_file:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = project_path / config_path
    else:
        config_path = project_path / "mkdocs.yml"

    if not config_path.exists():
        print(f"[ERROR] 配置文件不存在: {config_path}")
        return False

    # 检查 mkdocs 是否已安装
    if importlib.util.find_spec("mkdocs") is None:
        print(
            "[ERROR] mkdocs 未安装，请运行: pip install mkdocs 或 uv sync"
        )
        return False

    # 构建命令
    cmd = [sys.executable, "-m", "mkdocs", "build", "-f", str(config_path)]

    resolved_output_dir: str | None = None
    if output_dir:
        resolved_output_dir = str(Path(output_dir).resolve())
        cmd.extend(["-d", resolved_output_dir])

    if strict:
        cmd.append("--strict")

    print(f"构建项目: {project_path}")
    print(f"配置文件: {config_path}")
    if resolved_output_dir:
        print(f"输出目录: {resolved_output_dir}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            out_dir = output_dir or (project_path / "site")
            print(f"[OK] 构建成功: {out_dir}")
            if result.stdout.strip():
                print(result.stdout)
            return True
        else:
            print(f"[ERROR] 构建失败 (exit code: {result.returncode})")
            if result.stderr.strip():
                print(f"错误信息: {result.stderr}")
            return False

    except FileNotFoundError:
        print(
            "[ERROR] mkdocs 未安装，请运行: pip install mkdocs 或 uv sync"
        )
        return False
    except Exception as e:
        print(f"[ERROR] 构建异常: {e}")
        return False


def serve_project(
    project_dir: str | Path,
    dev_addr: str | None = None,
    config_file: str | Path | None = None,
    no_livereload: bool = False,
) -> None:
    """启动 MkDocs 开发服务器进行预览。

    本质是运行 ``mkdocs serve``，启动一个带热重载功能的本地开发服务器，
    用于在编写文档时实时预览效果。

    Args:
        project_dir: MkDocs 项目目录（包含 mkdocs.yml）
        dev_addr: 开发服务器地址，格式为 IP:PORT（默认 127.0.0.1:8000）
        config_file: 配置文件路径（相对或绝对路径），默认使用项目目录下的 mkdocs.yml
        no_livereload: 是否禁用热重载功能
    """
    project_path = Path(project_dir).resolve()

    # 确定配置文件路径
    if config_file:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = project_path / config_path
    else:
        config_path = project_path / "mkdocs.yml"

    if not config_path.exists():
        print(f"[ERROR] 配置文件不存在: {config_path}")
        return

    # 检查 mkdocs 是否已安装
    if importlib.util.find_spec("mkdocs") is None:
        print(
            "[ERROR] mkdocs 未安装，请运行: pip install mkdocs 或 uv sync"
        )
        return

    # 构建命令
    cmd = [sys.executable, "-m", "mkdocs", "serve", "-f", str(config_path)]

    if dev_addr:
        cmd.extend(["--dev-addr", dev_addr])

    if no_livereload:
        cmd.append("--no-livereload")

    print(f"启动开发服务器: {project_path}")
    print(f"配置文件: {config_path}")
    if dev_addr:
        print(f"服务地址: {dev_addr}")
    else:
        print("服务地址: 127.0.0.1:8000 (默认)")
    print()

    try:
        subprocess.run(cmd, cwd=str(project_path), check=False)
    except FileNotFoundError:
        print(
            "[ERROR] mkdocs 未安装，请运行: pip install mkdocs 或 uv sync"
        )
    except KeyboardInterrupt:
        print("\n[OK] 开发服务器已停止")


def _load_batch_config(config_path: str | Path) -> list[dict[str, Any]]:
    """加载批量构建配置文件（TOML 格式）。

    配置文件格式示例：

    ```toml
    [[projects]]
    project_dir = "/path/to/project1"
    output_dir = "/path/to/output1"

    [[projects]]
    project_dir = "/path/to/project2"
    output_dir = "/path/to/output2"
    config_file = "custom-mkdocs.yml"  # 可选
    strict = true                       # 可选
    ```

    Args:
        config_path: TOML 配置文件路径

    Returns:
        项目配置列表
    """
    config_path = Path(config_path).resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    projects = data.get("projects", [])
    if not projects:
        raise ValueError("配置文件中未找到 [[projects]] 条目")

    return projects


def batch_build(
    config_path: str | Path | None = None, dry_run: bool = False
) -> dict[str, bool]:
    """根据配置文件批量构建多个 MkDocs 项目。

    Args:
        config_path: TOML 配置文件路径，默认为 ~/.config/zxtool.toml
        dry_run: 仅打印计划，不实际执行

    Returns:
        每个项目的构建结果 {project_dir: success}
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = Path(config_path)
    try:
        projects = _load_batch_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        return {}

    print(f"加载配置文件: {config_path}")
    print(f"共 {len(projects)} 个项目待构建\n")

    if dry_run:
        print("=== 构建计划（dry-run）===")
        for i, proj in enumerate(projects, 1):
            print(f"  {i}. {proj.get('project_dir', '?')}")
            print(f"     输出: {proj.get('output_dir', '默认')}")
            if proj.get("config_file"):
                print(f"     配置: {proj['config_file']}")
            if proj.get("strict"):
                print(f"     模式: strict")
        print()
        return {
            p.get("project_dir", f"project_{i}"): True
            for i, p in enumerate(projects, 1)
        }

    results = {}
    success_count = 0

    for i, proj in enumerate(projects, 1):
        project_dir = proj.get("project_dir")
        if not project_dir:
            print(f"[{i}/{len(projects)}] [ERROR] 缺少 project_dir 配置，跳过")
            continue

        output_dir = proj.get("output_dir")
        config_file = proj.get("config_file")
        strict = proj.get("strict", False)

        print(f"\n--- [{i}/{len(projects)}] ---")
        success = build_project(
            project_dir=project_dir,
            output_dir=output_dir,
            config_file=config_file,
            strict=strict,
        )

        results[project_dir] = success
        if success:
            success_count += 1

    # 汇总
    print(f"\n{'=' * 40}")
    print(f"批量构建完成: {success_count}/{len(projects)} 成功")
    print(f"{'=' * 40}")

    for proj_dir, success in results.items():
        status = "[OK]" if success else "[ERROR]"
        print(f"  {status} {proj_dir}")

    return results
