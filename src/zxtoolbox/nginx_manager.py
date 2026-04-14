"""Nginx 配置管理模块。

提供以下功能：
1. 检查 Nginx 是否可用及配置目录
2. 根据 zxtool.toml 中的项目配置生成 Nginx 站点配置
3. 批量更新 Nginx 配置（基于配置文件）
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import tomllib

from zxtoolbox.config_manager import load_config, DEFAULT_CONFIG_PATH


# Nginx 配置模板（静态站点 + HTTPS）
NGINX_SITE_TEMPLATE = """\
# Nginx 配置 - 由 zxtool 自动生成
# 站点: {server_name}

# HTTP -> HTTPS 重定向
server {{
    listen 80;
    listen [::]:80;
    server_name {server_name};

    # Let's Encrypt ACME 验证路径
    location ^~ /.well-known/acme-challenge/ {{
        root {webroot};
    }}

    location / {{
        return 301 https://$host$request_uri;
    }}
}}

# HTTPS 站点
server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {server_name};

    # SSL 证书路径
    ssl_certificate {ssl_certificate};
    ssl_certificate_key {ssl_certificate_key};

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE+AESGCM:EDH+AESGCM;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头部
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 站点根目录
    root {root};
    index index.html;

    # 静态资源缓存
    location ~* \\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2)$ {{
        expires 30d;
        add_header Cache-Control "public";
    }}

    # Let's Encrypt ACME 验证路径
    location ^~ /.well-known/acme-challenge/ {{
        root {webroot};
    }}

    # 站点路由
    location / {{
        try_files $uri $uri/ =404;
    }}

    # 禁止访问隐藏文件
    location ~ /\\.(?!well-known).* {{
        deny all;
    }}
}}
"""

# Nginx 配置模板（仅 HTTP，无 SSL）
NGINX_HTTP_ONLY_TEMPLATE = """\
# Nginx 配置 - 由 zxtool 自动生成
# 站点: {server_name}

server {{
    listen 80;
    listen [::]:80;
    server_name {server_name};

    # 站点根目录
    root {root};
    index index.html;

    # Let's Encrypt ACME 验证路径
    location ^~ /.well-known/acme-challenge/ {{
        root {webroot};
    }}

    # 静态资源缓存
    location ~* \\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2)$ {{
        expires 30d;
        add_header Cache-Control "public";
    }}

    # 站点路由
    location / {{
        try_files $uri $uri/ =404;
    }}

    # 禁止访问隐藏文件
    location ~ /\\.(?!well-known).* {{
        deny all;
    }}
}}
"""


def check_nginx() -> dict[str, Any]:
    """检查 Nginx 是否可用及配置目录。

    Returns:
        包含 Nginx 状态信息的字典：
            - available: Nginx 是否已安装
            - version: Nginx 版本号
            - nginx_path: Nginx 可执行文件路径
            - config_dir: Nginx 配置目录
            - sites_available: sites-available 目录
            - sites_enabled: sites-enabled 目录
            - conf_d: conf.d 目录
    """
    result: dict[str, Any] = {
        "available": False,
        "version": None,
        "nginx_path": None,
        "config_dir": None,
        "sites_available": None,
        "sites_enabled": None,
        "conf_d": None,
    }

    # 查找 nginx 可执行文件
    nginx_path = shutil.which("nginx")
    if not nginx_path:
        return result

    result["available"] = True
    result["nginx_path"] = nginx_path

    # 获取版本号
    try:
        version_result = subprocess.run(
            [nginx_path, "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
        # nginx -v 输出到 stderr
        version_output = version_result.stderr.strip()
        if version_output.startswith("nginx version:"):
            result["version"] = version_output.replace("nginx version:", "").strip().strip("/")
    except Exception:
        pass

    # 获取配置目录
    try:
        prefix_result = subprocess.run(
            [nginx_path, "-V"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = prefix_result.stderr + prefix_result.stdout
        for line in output.splitlines():
            if "--conf-path=" in line:
                conf_path = line.split("--conf-path=")[1].split()[0].strip("'\"")
                result["config_dir"] = str(Path(conf_path).parent)
            elif "conf-path" in line:
                # 处理空格分隔的参数
                for part in line.split():
                    if part.startswith("--conf-path="):
                        conf_path = part.split("=", 1)[1].strip("'\"")
                        result["config_dir"] = str(Path(conf_path).parent)
    except Exception:
        pass

    # 如果没有从 -V 获取到配置目录，使用常见默认路径
    if not result["config_dir"]:
        common_paths = [
            "/etc/nginx",
            "/usr/local/nginx/conf",
        ]
        for path in common_paths:
            if Path(path).exists():
                result["config_dir"] = path
                break

    if result["config_dir"]:
        config_dir = Path(result["config_dir"])
        sites_available = config_dir / "sites-available"
        sites_enabled = config_dir / "sites-enabled"
        conf_d = config_dir / "conf.d"

        result["sites_available"] = str(sites_available) if sites_available.exists() else None
        result["sites_enabled"] = str(sites_enabled) if sites_enabled.exists() else None
        result["conf_d"] = str(conf_d) if conf_d.exists() else None

    return result


def _find_config_dir() -> Path | None:
    """查找 Nginx 配置目录。

    Returns:
        Nginx 配置目录路径，如果未找到则返回 None
    """
    info = check_nginx()
    config_dir = info.get("config_dir")
    if config_dir:
        return Path(config_dir)

    # 回退到常见路径
    common_paths = ["/etc/nginx", "/usr/local/nginx/conf"]
    for path in common_paths:
        if Path(path).exists():
            return Path(path)
    return None


def _find_sites_dir() -> tuple[Path | None, Path | None]:
    """查找 sites-available 和 sites-enabled 目录。

    Returns:
        (sites_available, sites_enabled) 元组
    """
    config_dir = _find_config_dir()
    if not config_dir:
        return None, None

    sites_available = config_dir / "sites-available"
    sites_enabled = config_dir / "sites-enabled"

    if sites_available.exists() and sites_enabled.exists():
        return sites_available, sites_enabled

    # 如果 sites-available 不存在，尝试使用 conf.d
    conf_d = config_dir / "conf.d"
    if conf_d.exists():
        return conf_d, conf_d

    return None, None


def _domain_to_filename(domain: str) -> str:
    """将域名转换为安全的文件名。

    Args:
        domain: 域名，如 example.com 或 *.example.com

    Returns:
        安全的文件名，如 example.com 或 wildcard.example.com
    """
    if domain.startswith("*."):
        return f"wildcard.{domain[2:]}"
    return domain


def _resolve_cert_paths(
    domain: str,
    le_config: dict[str, Any],
) -> tuple[str, str] | None:
    """根据域名和 LE 配置解析证书路径。

    Args:
        domain: 域名
        le_config: Let's Encrypt 配置字典

    Returns:
        (ssl_certificate, ssl_certificate_key) 元组，如果无法解析则返回 None
    """
    output_dir = le_config.get("output_dir", "out_le")
    if not output_dir:
        output_dir = "out_le"

    output_path = Path(output_dir).resolve()

    # 域名标签用于目录名
    domain_label = domain.replace("*.", "").replace(".", "_")
    cert_dir = output_path / f"cert_{domain_label}"

    # 构建证书路径
    # Let's Encrypt 证书文件命名格式: <domain>.fullchain.crt, <domain>.key.pem
    primary_domain = domain.lstrip("*.")
    fullchain_path = cert_dir / f"{domain}.fullchain.crt"
    key_path = cert_dir / f"{domain}.key.pem"

    # 尝试不带通配符前缀的路径
    if not fullchain_path.exists():
        fullchain_path = cert_dir / f"{primary_domain}.fullchain.crt"
        key_path = cert_dir / f"{primary_domain}.key.pem"

    if fullchain_path.exists() and key_path.exists():
        return str(fullchain_path), str(key_path)

    return None


def generate_site_config(
    domain: str,
    root: str,
    ssl_certificate: str | None = None,
    ssl_certificate_key: str | None = None,
    server_name: str | None = None,
    webroot: str | None = None,
) -> str:
    """生成单个站点的 Nginx 配置。

    Args:
        domain: 站点域名
        root: 站点根目录（MkDocs 构建输出目录）
        ssl_certificate: SSL 证书路径（fullchain）
        ssl_certificate_key: SSL 私钥路径
        server_name: Nginx server_name 指令值，默认与 domain 相同
        webroot: ACME 验证目录，默认与 root 相同

    Returns:
        生成的 Nginx 配置内容
    """
    if server_name is None:
        server_name = domain
    if webroot is None:
        webroot = root

    if ssl_certificate and ssl_certificate_key:
        return NGINX_SITE_TEMPLATE.format(
            server_name=server_name,
            root=root,
            ssl_certificate=ssl_certificate,
            ssl_certificate_key=ssl_certificate_key,
            webroot=webroot,
        )
    else:
        return NGINX_HTTP_ONLY_TEMPLATE.format(
            server_name=server_name,
            root=root,
            webroot=webroot,
        )


def write_site_config(
    domain: str,
    config_content: str,
    output_dir: str | Path | None = None,
) -> Path:
    """将 Nginx 站点配置写入文件。

    如果未指定输出目录，则自动检测 Nginx 的 sites-available 目录。
    如果 sites-available 不存在，则回退到 conf.d 目录。
    如果都不存在，则写入当前目录。

    Args:
        domain: 站点域名（用于文件命名）
        config_content: 配置内容
        output_dir: 输出目录，默认自动检测

    Returns:
        写入的配置文件路径
    """
    filename = f"{_domain_to_filename(domain)}.conf"

    if output_dir:
        output_path = Path(output_dir).resolve()
    else:
        sites_available, _ = _find_sites_dir()
        if sites_available:
            output_path = sites_available
        else:
            # 回退到当前目录
            output_path = Path.cwd()

    output_path.mkdir(parents=True, exist_ok=True)
    config_file = output_path / filename
    config_file.write_text(config_content, encoding="utf-8")

    print(f"[OK] Nginx 配置已写入: {config_file}")
    return config_file


def generate_from_config(
    config_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, str]:
    """根据 zxtool.toml 配置文件批量生成 Nginx 站点配置。

    读取配置文件中带有 domain 和 project_dir 的项目，为每个项目生成
    对应的 Nginx 站点配置文件。如果项目配置了 SSL 证书路径或 Let's Encrypt
    证书存在，则生成 HTTPS 配置；否则生成仅 HTTP 配置。

    Args:
        config_path: zxtool.toml 配置文件路径，默认为 ~/.config/zxtool.toml
        output_dir: 配置文件输出目录，默认自动检测或使用当前目录
        dry_run: 仅打印计划，不实际写入文件

    Returns:
        每个域名的配置内容 {domain: config_content}
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = Path(config_path)

    try:
        data = load_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        return {}

    projects = data.get("projects", [])
    if not projects:
        print("[ERROR] 配置文件中未找到 [[projects]] 条目")
        return {}

    # 读取 Let's Encrypt 全局配置
    le_section = data.get("letsencrypt", {})
    le_config = {
        "provider": le_section.get("provider", "manual"),
        "output_dir": le_section.get("output_dir", "out_le"),
        "staging": le_section.get("staging", True),
        "email": le_section.get("email", ""),
        "provider_config": le_section.get("provider_config", {}),
    }

    # 筛选配置了 domain 的项目
    domain_projects = [p for p in projects if p.get("domain")]

    if not domain_projects:
        print("[INFO] 配置文件中没有配置 domain 的项目。")
        print("提示: 在 [[projects]] 中添加 domain 字段，例如:")
        print('  domain = "example.com"')
        print('  domain = "*.example.com"')
        return {}

    print(f"加载配置文件: {config_path}")
    print(f"共 {len(domain_projects)} 个域名待生成配置\n")

    if dry_run:
        print("=== 生成计划（dry-run）===")
        for i, proj in enumerate(domain_projects, 1):
            domain = proj["domain"]
            project_dir = proj.get("project_dir", "?")
            output_dir_proj = proj.get("output_dir", "")
            print(f"  {i}. 域名: {domain}")
            print(f"     项目目录: {project_dir}")
            print(f"     输出目录: {output_dir_proj or '默认'}")
        print()
        return {
            p.get("domain", f"domain_{i}"): ""
            for i, p in enumerate(domain_projects, 1)
        }

    results: dict[str, str] = {}

    for i, proj in enumerate(domain_projects, 1):
        domain = proj["domain"]
        project_dir = proj.get("project_dir", "")
        mkdocs_output = proj.get("output_dir", "")

        print(f"\n--- [{i}/{len(domain_projects)}] {domain} ---")

        # 确定站点根目录
        if mkdocs_output:
            root = str(Path(mkdocs_output).resolve())
        elif project_dir:
            root = str(Path(project_dir).resolve() / "site")
        else:
            root = "/var/www/html"

        # 尝试解析 SSL 证书路径
        ssl_cert = None
        ssl_key = None

        cert_paths = _resolve_cert_paths(domain, le_config)
        if cert_paths:
            ssl_cert, ssl_key = cert_paths
            print(f"  SSL 证书: {ssl_cert}")
            print(f"  SSL 私钥: {ssl_key}")
        else:
            print(f"  [WARN] 未找到 SSL 证书，将生成仅 HTTP 配置")

        # 生成配置
        config_content = generate_site_config(
            domain=domain,
            root=root,
            ssl_certificate=ssl_cert,
            ssl_certificate_key=ssl_key,
            webroot=root,
        )

        # 写入文件
        config_file = write_site_config(domain, config_content, output_dir)
        results[domain] = config_content

    # 汇总
    print(f"\n{'=' * 40}")
    print(f"Nginx 配置生成完成: {len(results)}/{len(domain_projects)} 个站点")
    print(f"{'=' * 40}")

    for domain, _ in results.items():
        print(f"  [OK] {domain}")

    return results


def enable_site(domain: str) -> bool:
    """启用 Nginx 站点配置（创建符号链接）。

    仅适用于 Debian/Ubuntu 系统的 sites-available/sites-enabled 模式。

    Args:
        domain: 站点域名

    Returns:
        是否成功启用
    """
    sites_available, sites_enabled = _find_sites_dir()

    if not sites_available or not sites_enabled:
        print("[ERROR] 未找到 sites-available/sites-enabled 目录")
        print("提示: 仅支持 Debian/Ubuntu 系统的 Nginx 配置模式")
        return False

    filename = f"{_domain_to_filename(domain)}.conf"
    source = sites_available / filename
    target = sites_enabled / filename

    if not source.exists():
        print(f"[ERROR] 站点配置不存在: {source}")
        return False

    if target.exists():
        print(f"[WARN] 站点已启用: {target}")
        return True

    try:
        target.symlink_to(source)
        print(f"[OK] 站点已启用: {target} -> {source}")
        return True
    except OSError as e:
        print(f"[ERROR] 创建符号链接失败: {e}")
        print("提示: 可能需要 sudo 权限")
        return False


def disable_site(domain: str) -> bool:
    """禁用 Nginx 站点配置（移除符号链接）。

    仅适用于 Debian/Ubuntu 系统的 sites-available/sites-enabled 模式。

    Args:
        domain: 站点域名

    Returns:
        是否成功禁用
    """
    _, sites_enabled = _find_sites_dir()

    if not sites_enabled:
        print("[ERROR] 未找到 sites-enabled 目录")
        print("提示: 仅支持 Debian/Ubuntu 系统的 Nginx 配置模式")
        return False

    filename = f"{_domain_to_filename(domain)}.conf"
    target = sites_enabled / filename

    if not target.exists():
        print(f"[WARN] 站点未启用: {target}")
        return True

    try:
        target.unlink()
        print(f"[OK] 站点已禁用: {target}")
        return True
    except OSError as e:
        print(f"[ERROR] 移除符号链接失败: {e}")
        print("提示: 可能需要 sudo 权限")
        return False


def reload_nginx() -> bool:
    """重载 Nginx 配置。

    执行 nginx -s reload 来重载配置，这不会中断现有连接。

    Returns:
        是否成功重载
    """
    nginx_path = shutil.which("nginx")
    if not nginx_path:
        print("[ERROR] nginx 未安装")
        return False

    try:
        result = subprocess.run(
            [nginx_path, "-s", "reload"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("[OK] Nginx 配置已重载")
            return True
        else:
            print(f"[ERROR] Nginx 重载失败 (exit code: {result.returncode})")
            if result.stderr.strip():
                print(f"错误信息: {result.stderr}")
            return False
    except FileNotFoundError:
        print("[ERROR] nginx 未安装")
        return False
    except Exception as e:
        print(f"[ERROR] Nginx 重载异常: {e}")
        return False