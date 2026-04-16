"""zxtool.toml 配置文件管理模块。

生成和管理 ~/.config/zxtool.toml 配置文件，支持 MkDocs 项目、
Git 用户、Let's Encrypt 证书、Nginx 站点和日志配置。

配置文件结构::

    # Let's Encrypt 全局配置
    [letsencrypt]
    provider = "cloudflare"
    output_dir = "/path/to/certs"
    staging = true
    email = "admin@example.com"

    [letsencrypt.provider_config]
    api_token = "xxx"
    zone_id = "yyy"

    # Nginx 全局配置
    [nginx]
    http_port = 80
    https_port = 443

    # 日志配置
    [logging]
    log_dir = "/path/to/logs"
    log_level = "INFO"

    # 项目配置
    [[projects]]
    name = "myblog"
    project_dir = "/path/to/project1"
    domain = "example.com"
    output_dir = "/output"
    git_repository = "https://github.com/user/myblog.git"
    listen_port = 8080

    # Git 用户配置
    [git]

    [[git.user]]
    name = "John"
    email = "john@example.com"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import tomllib


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


def _generate_projects_section(projects: list[dict]) -> str:
    """生成项目配置部分（包含 MkDocs 和域名配置）。

    Args:
        projects: 项目配置列表，每个元素可包含：
            - name: 项目唯一名称（可选）
            - project_dir: 项目目录（必填）
            - output_dir: MkDocs 输出目录
            - config_file: MkDocs 配置文件
            - strict: 是否启用严格模式
            - domain: 项目的域名（单个字符串，支持泛域名如 *.example.com）
            - git_repository: 远程 Git 仓库地址（可选）
            - listen_port: Nginx 监听端口（可选）

    Returns:
        TOML 格式的项目配置字符串。
    """
    if not projects:
        return ""

    lines = [
        "# ============================================",
        "# 项目配置",
        "# ============================================",
        "",
    ]

    for proj in projects:
        lines.append("[[projects]]")

        # name 字段（项目唯一标识）
        if proj.get("name"):
            lines.append(f"name = {_escape_toml_string(proj['name'])}")

        lines.append(
            f"project_dir = {_escape_toml_string(proj.get('project_dir', ''))}"
        )

        # MkDocs 字段
        if proj.get("output_dir"):
            lines.append(f"output_dir = {_escape_toml_string(proj['output_dir'])}")

        if proj.get("config_file"):
            lines.append(f"config_file = {_escape_toml_string(proj['config_file'])}")

        if proj.get("strict"):
            lines.append("strict = true")

        # 域名字段（单个字符串）
        if proj.get("domain"):
            lines.append(f"domain = {_escape_toml_string(proj['domain'])}")

        # git_repository 字段（远程 Git 仓库地址）
        if proj.get("git_repository"):
            lines.append(f"git_repository = {_escape_toml_string(proj['git_repository'])}")

        # listen_port 字段（Nginx 监听端口）
        if proj.get("listen_port"):
            lines.append(f"listen_port = {proj['listen_port']}")

        lines.append("")

    return "\n".join(lines)


def _generate_letsencrypt_section(
    provider: str = "manual",
    output_dir: str = "",
    staging: bool = True,
    email: str = "",
    provider_config: dict[str, str] | None = None,
    challenge_type: str = "dns-01",
) -> str:
    """生成 Let's Encrypt 全局配置部分。

    Args:
        provider: 验证提供商名称。
            DNS-01: "manual", "cloudflare", "aliyun"
            HTTP-01: "webroot", "standalone"
        output_dir: 证书输出目录路径。
        staging: 是否使用测试环境。
        email: 联系邮箱。
        provider_config: 验证提供商配置字典。
        challenge_type: 验证方式 ("dns-01" 或 "http-01")。

    Returns:
        TOML 格式的 Let's Encrypt 配置字符串。
    """
    lines = [
        "# ============================================",
        "# Let's Encrypt 证书配置",
        "# ============================================",
        "",
        "[letsencrypt]",
    ]

    lines.append(f"provider = {_escape_toml_string(provider)}")
    lines.append(f"challenge_type = {_escape_toml_string(challenge_type)}")

    if output_dir:
        lines.append(f"output_dir = {_escape_toml_string(output_dir)}")
    else:
        lines.append(f"output_dir = {_escape_toml_string('out_le')}")

    lines.append(f"staging = {str(staging).lower()}")

    if email:
        lines.append(f"email = {_escape_toml_string(email)}")

    # provider_config 作为子表
    if provider_config and isinstance(provider_config, dict):
        lines.append("")
        lines.append("[letsencrypt.provider_config]")
        for key, value in provider_config.items():
            lines.append(f"{key} = {_escape_toml_string(str(value))}")

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


def _generate_nginx_section(
    http_port: int = 80,
    https_port: int = 443,
) -> str:
    """生成 Nginx 全局配置部分。

    Args:
        http_port: HTTP 监听端口（默认 80）。
        https_port: HTTPS 监听端口（默认 443）。

    Returns:
        TOML 格式的 Nginx 配置字符串。
    """
    lines = [
        "# ============================================",
        "# Nginx 站点配置",
        "# ============================================",
        "",
        "[nginx]",
    ]

    lines.append(f"http_port = {http_port}")
    lines.append(f"https_port = {https_port}")
    lines.append("")
    return "\n".join(lines)


def _generate_logging_section(
    log_dir: str = "",
    log_level: str = "INFO",
) -> str:
    """生成日志配置部分。

    Args:
        log_dir: 日志文件存放目录路径。
        log_level: 日志级别（默认 INFO）。

    Returns:
        TOML 格式的日志配置字符串。
    """
    lines = [
        "# ============================================",
        "# 日志配置",
        "# ============================================",
        "",
        "[logging]",
    ]

    if log_dir:
        lines.append(f"log_dir = {_escape_toml_string(log_dir)}")
    else:
        lines.append(f"log_dir = {_escape_toml_string(str(Path.home() / '.config' / 'zxtool_logs'))}")

    lines.append(f"log_level = {_escape_toml_string(log_level.upper())}")
    lines.append("")
    return "\n".join(lines)


def generate_config_content(
    mkdocs_projects: list[dict] | None = None,
    git_users: list[dict] | None = None,
    letsencrypt_config: dict[str, Any] | None = None,
    nginx_config: dict[str, Any] | None = None,
    logging_config: dict[str, Any] | None = None,
) -> str:
    """生成完整的 zxtool.toml 配置文件内容。

    Args:
        mkdocs_projects: 项目配置列表。每个项目可包含 project_dir、
            output_dir、config_file、strict、domain、listen_port 等字段。
        git_users: Git 用户配置列表。
        letsencrypt_config: Let's Encrypt 全局配置字典，可包含：
            - provider: DNS 提供商名称
            - output_dir: 证书输出目录
            - staging: 是否使用测试环境
            - email: 联系邮箱
            - provider_config: DNS 提供商配置
        nginx_config: Nginx 全局配置字典，可包含：
            - http_port: HTTP 监听端口（默认 80）
            - https_port: HTTPS 监听端口（默认 443）
        logging_config: 日志配置字典，可包含：
            - log_dir: 日志文件存放目录
            - log_level: 日志级别（默认 INFO）

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
    parts.append("#   zxtool le batch               # 根据配置批量申请/续签证书")
    parts.append("#   zxtool nginx generate         # 根据 Nginx 配置生成站点配置")
    parts.append("")

    # Let's Encrypt 配置
    if letsencrypt_config:
        le_section = _generate_letsencrypt_section(
            provider=letsencrypt_config.get("provider", "manual"),
            output_dir=letsencrypt_config.get("output_dir", "out_le"),
            staging=letsencrypt_config.get("staging", True),
            email=letsencrypt_config.get("email", ""),
            provider_config=letsencrypt_config.get("provider_config"),
            challenge_type=letsencrypt_config.get("challenge_type", "dns-01"),
        )
        parts.append(le_section)

    # Nginx 配置
    if nginx_config:
        nginx_section = _generate_nginx_section(
            http_port=nginx_config.get("http_port", 80),
            https_port=nginx_config.get("https_port", 443),
        )
        parts.append(nginx_section)

    # 日志配置
    if logging_config:
        logging_section = _generate_logging_section(
            log_dir=logging_config.get("log_dir", ""),
            log_level=logging_config.get("log_level", "INFO"),
        )
        parts.append(logging_section)

    # 项目配置
    projects_section = _generate_projects_section(mkdocs_projects or [])
    if projects_section:
        parts.append(projects_section)

    # Git 配置
    git_section = _generate_git_section(git_users or [])
    if git_section:
        parts.append(git_section)

    # 如果没有任何配置，添加注释说明
    if not mkdocs_projects and not git_users and not letsencrypt_config and not nginx_config and not logging_config:
        parts.append("# 暂无配置项")
        parts.append("# 运行 'zxtool config init' 交互式生成配置")
        parts.append("")

    return "\n".join(parts)


def write_config(
    config_path: str | Path | None = None,
    mkdocs_projects: list[dict] | None = None,
    git_users: list[dict] | None = None,
    letsencrypt_config: dict[str, Any] | None = None,
    nginx_config: dict[str, Any] | None = None,
    logging_config: dict[str, Any] | None = None,
    force: bool = False,
) -> bool:
    """写入 zxtool.toml 配置文件。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。
        mkdocs_projects: 项目配置列表。每个项目可包含 domain 字段。
        git_users: Git 用户配置列表。
        letsencrypt_config: Let's Encrypt 全局配置字典。
        nginx_config: Nginx 全局配置字典，可包含：
            - http_port: HTTP 监听端口（默认 80）
            - https_port: HTTPS 监听端口（默认 443）
        logging_config: 日志配置字典，可包含：
            - log_dir: 日志文件存放目录
            - log_level: 日志级别（默认 INFO）
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
        letsencrypt_config=letsencrypt_config,
        nginx_config=nginx_config,
        logging_config=logging_config,
    )

    # 写入文件
    config_path.write_text(content, encoding="utf-8")
    print(f"[OK] 配置文件已创建: {config_path}")
    return True


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """加载 zxtool.toml 配置文件。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。

    Returns:
        解析后的配置字典，结构如下::

            {
                "letsencrypt": {
                    "provider": "cloudflare",
                    "output_dir": "out_le",
                    "staging": True,
                    "email": "admin@example.com",
                    "provider_config": {"api_token": "xxx", "zone_id": "yyy"},
                },
                "projects": [
                    {"project_dir": "...", "domain": "example.com", ...},
                    ...
                ],
                "git": {
                    "user": [{"name": "...", "email": "..."}, ...]
                },
            }

    Raises:
        FileNotFoundError: 配置文件不存在时。
        ValueError: 配置文件格式错误时。
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = Path(config_path).resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    return data


def load_le_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """加载 Let's Encrypt 全局配置。

    从 zxtool.toml 的 [letsencrypt] 节点读取配置。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。

    Returns:
        Let's Encrypt 配置字典，包含:
            - provider: 验证提供商名称 (默认 "manual")
            - output_dir: 证书输出目录 (默认 "out_le")
            - staging: 是否使用测试环境 (默认 True)
            - email: 联系邮箱 (默认 "")
            - provider_config: 验证提供商配置字典 (默认 {})
            - challenge_type: 验证方式 (默认 "dns-01")

    Raises:
        FileNotFoundError: 配置文件不存在时。
    """
    data = load_config(config_path)
    le = data.get("letsencrypt", {})
    return {
        "provider": le.get("provider", "manual"),
        "output_dir": le.get("output_dir", "out_le"),
        "staging": le.get("staging", True),
        "email": le.get("email", ""),
        "provider_config": le.get("provider_config", {}),
        "challenge_type": le.get("challenge_type", "dns-01"),
    }


def load_nginx_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """加载 Nginx 全局配置。

    从 zxtool.toml 的 [nginx] 节点读取配置。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。

    Returns:
        Nginx 配置字典，包含:
            - http_port: HTTP 监听端口 (默认 80)
            - https_port: HTTPS 监听端口 (默认 443)

    Raises:
        FileNotFoundError: 配置文件不存在时。
    """
    data = load_config(config_path)
    nginx = data.get("nginx", {})
    return {
        "http_port": nginx.get("http_port", 80),
        "https_port": nginx.get("https_port", 443),
    }


def load_logging_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """加载日志全局配置。

    从 zxtool.toml 的 [logging] 节点读取配置。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。

    Returns:
        日志配置字典，包含:
            - log_dir: 日志文件存放目录 (默认 ~/.config/zxtool_logs)
            - log_level: 日志级别 (默认 INFO)

    Raises:
        FileNotFoundError: 配置文件不存在时。
    """
    data = load_config(config_path)
    logging_sec = data.get("logging", {})
    return {
        "log_dir": logging_sec.get("log_dir", str(Path.home() / ".config" / "zxtool_logs")),
        "log_level": logging_sec.get("log_level", "INFO"),
    }


def load_projects_with_domain(
    config_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """加载包含域名配置的项目列表。

    从 zxtool.toml 的 [[projects]] 节点中筛选出配置了 domain 字段的项目。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。

    Returns:
        包含 domain 字段的项目列表，每个元素额外附带 Let's Encrypt 全局配置::

            [
                {
                    "project_dir": "/path/to/project",
                    "domain": "example.com",
                    "_le": {
                        "provider": "cloudflare",
                        "output_dir": "out_le",
                        "staging": True,
                        "email": "admin@example.com",
                        "provider_config": {...},
                    },
                },
                ...
            ]

    Raises:
        FileNotFoundError: 配置文件不存在时。
    """
    data = load_config(config_path)
    projects = data.get("projects", [])

    le_config = {
        "provider": "manual",
        "output_dir": "out_le",
        "staging": True,
        "email": "",
        "provider_config": {},
        "challenge_type": "dns-01",
    }
    if "letsencrypt" in data:
        le_sec = data["letsencrypt"]
        le_config = {
            "provider": le_sec.get("provider", "manual"),
            "output_dir": le_sec.get("output_dir", "out_le"),
            "staging": le_sec.get("staging", True),
            "email": le_sec.get("email", ""),
            "provider_config": le_sec.get("provider_config", {}),
            "challenge_type": le_sec.get("challenge_type", "dns-01"),
        }

    result = []
    for proj in projects:
        if proj.get("domain"):
            # 合并项目配置和全局 LE 配置
            entry = dict(proj)
            entry["_le"] = dict(le_config)
            result.append(entry)

    return result


def load_project_by_name(
    name: str, config_path: str | Path | None = None
) -> dict[str, Any] | None:
    """根据 name 查找项目配置。

    从 zxtool.toml 的 [[projects]] 节点中查找匹配 name 的项目。

    Args:
        name: 项目名称（唯一标识）。
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。

    Returns:
        匹配的项目配置字典，未找到则返回 None。

    Raises:
        FileNotFoundError: 配置文件不存在时。
    """
    data = load_config(config_path)
    projects = data.get("projects", [])

    for proj in projects:
        if proj.get("name") == name:
            return dict(proj)

    return None


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
    letsencrypt_config = None
    nginx_config = None
    logging_config = None

    # --- Let's Encrypt 配置 ---
    print("\n--- Let's Encrypt 证书配置 ---")
    try:
        setup_le = input("配置 Let's Encrypt? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n")
        setup_le = "n"

    if setup_le in ("y", "yes"):
        letsencrypt_config = {}
        try:
            challenge_type = input(
                "  验证方式 [dns-01/http-01, 默认 dns-01]: "
            ).strip().lower()
            challenge_type = challenge_type if challenge_type in ("dns-01", "http-01") else "dns-01"
            letsencrypt_config["challenge_type"] = challenge_type

            # 根据验证方式选择提供商
            if challenge_type == "http-01":
                provider = input(
                    "  HTTP-01 提供商 [webroot/standalone, 默认 standalone]: "
                ).strip().lower()
                letsencrypt_config["provider"] = provider if provider in ("webroot", "standalone") else "standalone"
            else:
                provider = input(
                    "  DNS 提供商 [manual/cloudflare/aliyun, 默认 manual]: "
                ).strip().lower()
                letsencrypt_config["provider"] = provider if provider else "manual"

            output_dir = input("  证书输出目录 [默认 out_le]: ").strip()
            letsencrypt_config["output_dir"] = output_dir if output_dir else "out_le"

            email = input("  联系邮箱: ").strip()
            letsencrypt_config["email"] = email

            staging = input("  使用测试环境? [Y/n]: ").strip().lower()
            letsencrypt_config["staging"] = staging not in ("n", "no")

            # 验证提供商配置
            provider_name = letsencrypt_config["provider"]
            provider_config = {}
            if challenge_type == "http-01":
                if provider_name == "webroot":
                    webroot = input("  Webroot 路径 (如 /var/www/html): ").strip()
                    provider_config["webroot"] = webroot
                # standalone 无需额外配置
            elif provider_name == "cloudflare":
                api_token = input("  Cloudflare API Token: ").strip()
                zone_id = input("  Cloudflare Zone ID: ").strip()
                provider_config["api_token"] = api_token
                provider_config["zone_id"] = zone_id
            elif provider_name == "aliyun":
                access_key_id = input("  阿里云 AccessKey ID: ").strip()
                access_key_secret = input("  阿里云 AccessKey Secret: ").strip()
                provider_config["access_key_id"] = access_key_id
                provider_config["access_key_secret"] = access_key_secret

            if provider_config:
                letsencrypt_config["provider_config"] = provider_config

            print("  [OK] Let's Encrypt 配置已添加")
        except (EOFError, KeyboardInterrupt):
            print("\n")
            letsencrypt_config = None

    # --- Nginx 配置 ---
    print("\n--- Nginx 站点配置 ---")
    try:
        setup_nginx = input("配置 Nginx 站点端口? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n")
        setup_nginx = "n"

    if setup_nginx in ("y", "yes"):
        nginx_config = {}
        try:
            http_port_str = input("  HTTP 端口 [默认 80]: ").strip()
            nginx_config["http_port"] = int(http_port_str) if http_port_str else 80

            https_port_str = input("  HTTPS 端口 [默认 443]: ").strip()
            nginx_config["https_port"] = int(https_port_str) if https_port_str else 443

            print("  [OK] Nginx 配置已添加")
        except (EOFError, KeyboardInterrupt):
            print("\n")
            nginx_config = None
        except ValueError:
            print("  [WARN] 端口格式无效，使用默认值")
            nginx_config = {"http_port": 80, "https_port": 443}

    # --- 日志配置 ---
    print("\n--- 日志配置 ---")
    try:
        setup_logging = input("配置日志目录? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n")
        setup_logging = "n"

    if setup_logging in ("y", "yes"):
        logging_config = {}
        try:
            default_log_dir = str(Path.home() / ".config" / "zxtool_logs")
            log_dir = input(f"  日志目录 [默认 {default_log_dir}]: ").strip()
            logging_config["log_dir"] = log_dir if log_dir else default_log_dir

            log_level = input("  日志级别 [DEBUG/INFO/WARNING/ERROR, 默认 INFO]: ").strip().upper()
            if log_level in ("DEBUG", "INFO", "WARNING", "ERROR"):
                logging_config["log_level"] = log_level
            else:
                logging_config["log_level"] = "INFO"

            print("  [OK] 日志配置已添加")
        except (EOFError, KeyboardInterrupt):
            print("\n")
            logging_config = None

    # --- MkDocs / 项目配置 ---
    print("\n--- 项目配置 ---")
    print("添加项目（可配置 MkDocs 构建和域名，留空跳过）")

    while True:
        try:
            project_dir = input(f"\n项目路径 [{len(mkdocs_projects) + 1}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not project_dir:
            break

        project: dict[str, Any] = {"project_dir": project_dir}

        project_name = input("  项目名称 [唯一标识]: ").strip()
        if project_name:
            project["name"] = project_name

        output_dir = input("  MkDocs 输出目录 [默认 site]: ").strip()
        if output_dir:
            project["output_dir"] = output_dir

        config_file = input("  自定义配置文件 [默认 mkdocs.yml]: ").strip()
        if config_file:
            project["config_file"] = config_file

        strict = input("  启用严格模式? (y/N): ").strip().lower()
        if strict in ("y", "yes"):
            project["strict"] = True

        domain = input("  项目域名（用于 Let's Encrypt 证书，如 example.com）: ").strip()
        if domain:
            project["domain"] = domain

        git_repo = input("  Git 仓库地址（如 https://github.com/user/repo.git）: ").strip()
        if git_repo:
            project["git_repository"] = git_repo

        listen_port_str = input("  Nginx 监听端口 [默认使用全局配置]: ").strip()
        if listen_port_str:
            try:
                project["listen_port"] = int(listen_port_str)
            except ValueError:
                print("  [WARN] 端口格式无效，跳过")

        mkdocs_projects.append(project)
        summary = f"{project_dir}"
        if project.get("name"):
            summary += f" (名称: {project['name']})"
        if domain:
            summary += f" (域名: {domain})"
        print(f"  [OK] 已添加项目: {summary}")

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

    if letsencrypt_config:
        print(f"\nLet's Encrypt:")
        print(f"  验证方式:   {letsencrypt_config.get('challenge_type', 'dns-01')}")
        print(f"  提供商:     {letsencrypt_config.get('provider', 'manual')}")
        print(f"  输出目录:   {letsencrypt_config.get('output_dir', 'out_le')}")
        print(f"  环境:       {'测试' if letsencrypt_config.get('staging', True) else '生产'}")
        if letsencrypt_config.get("email"):
            print(f"  联系邮箱:   {letsencrypt_config['email']}")
    else:
        print("\nLet's Encrypt: 未配置")

    if nginx_config:
        print(f"\nNginx:")
        print(f"  HTTP 端口:  {nginx_config.get('http_port', 80)}")
        print(f"  HTTPS 端口: {nginx_config.get('https_port', 443)}")
    else:
        print("\nNginx: 未配置")

    if logging_config:
        print(f"\n日志:")
        print(f"  日志目录:   {logging_config.get('log_dir', '~/.config/zxtool_logs')}")
        print(f"  日志级别:   {logging_config.get('log_level', 'INFO')}")
    else:
        print("\n日志: 未配置")

    if mkdocs_projects:
        print(f"\n项目: {len(mkdocs_projects)} 个")
        for proj in mkdocs_projects:
            detail = f"  - {proj['project_dir']}"
            if proj.get("domain"):
                detail += f" (域名: {proj['domain']})"
            print(detail)
    else:
        print("\n项目: 无")

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
        letsencrypt_config=letsencrypt_config,
        nginx_config=nginx_config,
        logging_config=logging_config,
        force=True,
    )

    if success:
        print("\n[OK] 配置初始化完成!")
        print(f"\n查看配置: cat {config_path}")
        print(f"\n使用方式:")
        print(f"  zxtool mkdocs batch              # 批量构建 MkDocs")
        print(f"  zxtool git config fill           # 填充 Git user 配置")
        print(f"  zxtool le batch                  # 根据配置批量申请/续签证书")
        print(f"  zxtool nginx generate            # 根据 Nginx 配置生成站点配置")

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