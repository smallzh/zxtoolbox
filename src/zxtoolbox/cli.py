"""ZX Toolbox CLI 入口。

子命令结构：
    zxtool ci [options]           - 计算机信息（默认显示简短信息）
    zxtool le <subcommand>        - Let's Encrypt 证书管理
    zxtool ssl <subcommand>       - 自签 SSL 证书生成
    zxtool totp -k <key>          - TOTP 双因素认证解析
    zxtool video -u <url>          - 在线视频下载
    zxtool mkdocs <subcommand>    - MkDocs 项目管理
    zxtool config <subcommand>    - 配置文件管理
    zxtool git <subcommand>       - Git 仓库管理（config/pull）
"""

import argparse
import json
import sys
from pathlib import Path

from zxtoolbox import __version__

import zxtoolbox.computer_info as cpi
import zxtoolbox.pyopt_2fa as opt2fa
import zxtoolbox.video_download as vd
import zxtoolbox.ssl_cert as ssl
import zxtoolbox.git_config as gc
import zxtoolbox.config_manager as cm


def main():
    parser = argparse.ArgumentParser(
        description="ZX Toolbox - 跨平台工具集合",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=f"zxtoolbox {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ========== ci 子命令 - 计算机信息 ==========
    ci_parser = subparsers.add_parser("ci", help="显示计算机信息（默认简短信息）")
    ci_parser.add_argument(
        "-a", "--all", action="store_true", help="显示详细信息"
    )

    # ========== totp 子命令 - TOTP 解析 ==========
    totp_parser = subparsers.add_parser("totp", help="TOTP 双因素认证解析")
    totp_parser.add_argument(
        "-k", "--key", type=str, required=True, help="TOTP 待解析的 key"
    )

    # ========== video 子命令 - 视频下载 ==========
    video_parser = subparsers.add_parser("video", help="在线视频下载")
    video_parser.add_argument(
        "-u", "--url", type=str, required=True, help="视频 URL 地址"
    )
    video_parser.add_argument(
        "-o", "--output", type=str, default=None, help="视频输出路径"
    )

    # ========== ssl 子命令 - SSL 证书生成 ==========
    ssl_parser = subparsers.add_parser("ssl", help="自签泛域名 SSL 证书生成")
    ssl_subparsers = ssl_parser.add_subparsers(dest="ssl_command", help="SSL 子命令")

    # ssl init
    ssl_init_parser = ssl_subparsers.add_parser("init", help="初始化输出目录结构")
    ssl_init_parser.add_argument(
        "--output", type=str, default=None, help="输出目录路径（默认: ./out）"
    )

    # ssl root
    ssl_root_parser = ssl_subparsers.add_parser("root", help="生成 Root CA 证书")
    ssl_root_parser.add_argument(
        "--output", type=str, default=None, help="输出目录路径（默认: ./out）"
    )
    ssl_root_parser.add_argument(
        "--force", action="store_true", help="强制重新生成（覆盖已有证书）"
    )

    # ssl cert
    ssl_cert_parser = ssl_subparsers.add_parser("cert", help="生成域名证书")
    ssl_cert_parser.add_argument(
        "-d", "--domain", nargs="+", required=True,
        help="域名列表，如 example.dev another.dev"
    )
    ssl_cert_parser.add_argument(
        "--output", type=str, default=None, help="输出目录路径（默认: ./out）"
    )

    # ========== mkdocs 子命令 ==========
    mkdocs_parser = subparsers.add_parser("mkdocs", help="MkDocs 项目管理")
    mkdocs_subparsers = mkdocs_parser.add_subparsers(
        dest="mkdocs_command", help="MkDocs 子命令"
    )

    # mkdocs create
    mkdocs_create_parser = mkdocs_subparsers.add_parser("create", help="创建新的 MkDocs 项目")
    mkdocs_create_parser.add_argument("project_dir", help="项目目录路径")
    mkdocs_create_parser.add_argument(
        "--name", type=str, default=None, help="站点名称（默认使用目录名）"
    )

    # mkdocs build
    mkdocs_build_parser = mkdocs_subparsers.add_parser(
        "build", help="构建 MkDocs 项目到指定目录"
    )
    mkdocs_build_parser.add_argument("project_dir", help="MkDocs 项目目录")
    mkdocs_build_parser.add_argument("-o", "--output", type=str, default=None, help="输出目录")
    mkdocs_build_parser.add_argument(
        "-c", "--config", type=str, default=None, help="配置文件路径（相对或绝对）"
    )
    mkdocs_build_parser.add_argument(
        "--strict", action="store_true", help="严格模式（警告视为错误）"
    )

    # mkdocs batch
    mkdocs_batch_parser = mkdocs_subparsers.add_parser(
        "batch", help="批量构建多个 MkDocs 项目"
    )
    mkdocs_batch_parser.add_argument(
        "config_file",
        nargs="?",
        default=None,
        help="TOML 配置文件路径（默认: ~/.config/zxtool.toml）",
    )
    mkdocs_batch_parser.add_argument(
        "--dry-run", action="store_true", help="仅打印构建计划，不实际执行"
    )

    # mkdocs serve
    mkdocs_serve_parser = mkdocs_subparsers.add_parser(
        "serve", help="启动 MkDocs 开发服务器预览文档"
    )
    mkdocs_serve_parser.add_argument("project_dir", help="MkDocs 项目目录")
    mkdocs_serve_parser.add_argument(
        "-a", "--dev-addr", type=str, default=None,
        help="开发服务器地址（格式: IP:PORT，默认 127.0.0.1:8000）"
    )
    mkdocs_serve_parser.add_argument(
        "-c", "--config", type=str, default=None,
        help="配置文件路径（相对或绝对）"
    )
    mkdocs_serve_parser.add_argument(
        "--no-livereload", action="store_true",
        help="禁用热重载功能"
    )

    # ========== nginx 子命令 ==========
    nginx_parser = subparsers.add_parser("nginx", help="Nginx 站点配置管理")
    nginx_subparsers = nginx_parser.add_subparsers(
        dest="nginx_command", help="Nginx 子命令"
    )

    # nginx check
    nginx_check_parser = nginx_subparsers.add_parser(
        "check", help="检查 Nginx 是否可用及配置目录"
    )

    # nginx generate
    nginx_generate_parser = nginx_subparsers.add_parser(
        "generate", help="根据配置文件生成 Nginx 站点配置"
    )
    nginx_generate_parser.add_argument(
        "--config", type=str, default=None,
        help="zxtool.toml 配置文件路径（默认: ~/.config/zxtool.toml）"
    )
    nginx_generate_parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="配置文件输出目录"
    )
    nginx_generate_parser.add_argument(
        "--dry-run", action="store_true",
        help="仅打印生成计划，不实际写入文件"
    )

    # nginx enable
    nginx_enable_parser = nginx_subparsers.add_parser(
        "enable", help="启用 Nginx 站点配置（创建符号链接）"
    )
    nginx_enable_parser.add_argument("domain", help="站点域名")

    # nginx disable
    nginx_disable_parser = nginx_subparsers.add_parser(
        "disable", help="禁用 Nginx 站点配置（移除符号链接）"
    )
    nginx_disable_parser.add_argument("domain", help="站点域名")

    # nginx reload
    nginx_reload_parser = nginx_subparsers.add_parser(
        "reload", help="重载 Nginx 配置"
    )

    # ========== config 子命令 ==========
    config_parser = subparsers.add_parser("config", help="配置文件管理")
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="配置子命令"
    )

    # config init
    config_init_parser = config_subparsers.add_parser(
        "init", help="交互式初始化配置文件"
    )
    config_init_parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="配置文件路径（默认 ~/.config/zxtool.toml）",
    )
    config_init_parser.add_argument(
        "--force", action="store_true", help="覆盖已存在的配置文件"
    )

    # config show
    config_show_parser = config_subparsers.add_parser("show", help="显示当前配置内容")
    config_show_parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="配置文件路径（默认 ~/.config/zxtool.toml）",
    )

    # ========== git 子命令 ==========
    git_parser = subparsers.add_parser("git", help="Git 仓库配置管理")
    git_subparsers = git_parser.add_subparsers(dest="git_command", help="Git 子命令")

    # git config
    gc_config_parser = git_subparsers.add_parser("config", help="管理 Git 仓库 user 配置")
    gc_config_parser.add_argument(
        "config_command",
        nargs="?",
        default=None,
        help="子命令: check (检查) / fill (填充)",
    )
    gc_config_parser.add_argument(
        "project_dir",
        nargs="?",
        default=None,
        help="项目目录路径（默认当前目录）",
    )
    gc_config_parser.add_argument(
        "--config", type=str, default=None, help="zxtool.toml 配置文件路径"
    )
    gc_config_parser.add_argument("--name", type=str, default=None, help="git user.name")
    gc_config_parser.add_argument("--email", type=str, default=None, help="git user.email")

    # git pull
    git_pull_parser = git_subparsers.add_parser("pull", help="从远程仓库拉取更新")
    git_pull_parser.add_argument(
        "project_dir",
        nargs="?",
        default=None,
        help="项目目录路径（默认当前目录）",
    )
    git_pull_parser.add_argument(
        "--remote", type=str, default=None, help="远程仓库名称（默认使用仓库配置的 upstream）"
    )
    git_pull_parser.add_argument(
        "--branch", type=str, default=None, help="分支名称（默认使用当前分支）"
    )

    # ========== le 子命令 - Let's Encrypt ==========
    le_parser = subparsers.add_parser("le", help="Let's Encrypt ACME v2 证书管理")
    le_subparsers = le_parser.add_subparsers(dest="le_command", help="LE 子命令")

    # le issue - 签发证书
    le_issue_parser = le_subparsers.add_parser("issue", help="签发新证书")
    le_issue_parser.add_argument(
        "-d", "--domain", nargs="+", required=True, help="域名列表"
    )
    le_issue_parser.add_argument(
        "--provider", default="manual", help="DNS 提供商 (manual/cloudflare/aliyun)"
    )
    le_issue_parser.add_argument(
        "--provider-config", type=str, default=None, help="提供商配置 (JSON 字符串)"
    )
    le_issue_parser.add_argument(
        "--production", action="store_true", help="使用生产环境（默认测试环境）"
    )
    le_issue_parser.add_argument("--email", default="", help="联系邮箱")
    le_issue_parser.add_argument(
        "--key-size", type=int, default=2048, choices=[2048, 4096], help="RSA 密钥长度"
    )
    le_issue_parser.add_argument("--output", type=str, default=None, help="输出目录")

    # le renew - 续签
    le_renew_parser = le_subparsers.add_parser("renew", help="续签即将到期的证书")
    le_renew_parser.add_argument(
        "--dry-run", action="store_true", help="仅检查，不执行续签"
    )
    le_renew_parser.add_argument(
        "--provider-config", type=str, default=None, help="提供商配置 (JSON 字符串)"
    )
    le_renew_parser.add_argument("--output", type=str, default=None, help="输出目录")

    # le batch - 根据配置文件批量签发/续签证书
    le_batch_parser = le_subparsers.add_parser(
        "batch", help="根据配置文件批量签发/续签证书"
    )
    le_batch_parser.add_argument(
        "--le-config", type=str, default=None,
        help="zxtool.toml 配置文件路径（默认: ~/.config/zxtool.toml）"
    )
    le_batch_parser.add_argument(
        "--dry-run", action="store_true", help="仅打印计划，不实际执行"
    )

    # le status - 查看状态
    le_status_parser = le_subparsers.add_parser("status", help="查看证书状态")
    le_status_parser.add_argument("--output", type=str, default=None, help="输出目录")

    # le revoke - 吊销
    le_revoke_parser = le_subparsers.add_parser("revoke", help="吊销证书")
    le_revoke_parser.add_argument("-d", "--domain", required=True, help="要吊销的域名")
    le_revoke_parser.add_argument("--provider", default="manual", help="DNS 提供商")
    le_revoke_parser.add_argument(
        "--provider-config", type=str, default=None, help="提供商配置 (JSON 字符串)"
    )
    le_revoke_parser.add_argument("--output", type=str, default=None, help="输出目录")

    # le init - 初始化
    le_init_parser = le_subparsers.add_parser("init", help="初始化输出目录")
    le_init_parser.add_argument("--output", type=str, default=None, help="输出目录")

    # ========== 解析参数 ==========
    args = parser.parse_args()

    # ========== ci 子命令分发 ==========
    if args.command == "ci":
        if args.all:
            cpi.detailed_info()
        else:
            cpi.summary_info()
        return

    # ========== totp 子命令分发 ==========
    if args.command == "totp":
        opt2fa.parseTotpCdoe(args.key)
        return

    # ========== video 子命令分发 ==========
    if args.command == "video":
        vd.download_with_progress(args.url, args.output)
        return

    # ========== ssl 子命令分发 ==========
    if args.command == "ssl":
        ssl_cmd = getattr(args, "ssl_command", None)
        if ssl_cmd == "init":
            out_dir = Path(args.output).resolve() if args.output else Path("out").resolve()
            ssl.init(out_dir)
        elif ssl_cmd == "root":
            out_dir = Path(args.output).resolve() if args.output else Path("out").resolve()
            ssl.generate_root(out_dir, force=args.force)
        elif ssl_cmd == "cert":
            out_dir = Path(args.output).resolve() if args.output else Path("out").resolve()
            ssl.generate_cert(out_dir, args.domain)
        else:
            ssl_parser.print_help()
        return

    # ========== mkdocs 子命令分发 ==========
    if args.command == "mkdocs":
        import zxtoolbox.mkdocs_manager as mdm

        mkdocs_cmd = getattr(args, "mkdocs_command", None)

        if mkdocs_cmd == "create":
            mdm.create_project(args.project_dir, site_name=args.name)
        elif mkdocs_cmd == "build":
            mdm.build_project(
                project_dir=args.project_dir,
                output_dir=args.output,
                config_file=args.config,
                strict=args.strict,
            )
        elif mkdocs_cmd == "batch":
            mdm.batch_build(
                config_path=args.config_file,
                dry_run=args.dry_run,
            )
        elif mkdocs_cmd == "serve":
            mdm.serve_project(
                project_dir=args.project_dir,
                dev_addr=args.dev_addr,
                config_file=args.config,
                no_livereload=args.no_livereload,
            )
        else:
            mkdocs_parser.print_help()
        return

    # ========== nginx 子命令分发 ==========
    if args.command == "nginx":
        import zxtoolbox.nginx_manager as ngm

        nginx_cmd = getattr(args, "nginx_command", None)

        if nginx_cmd == "check":
            info = ngm.check_nginx()
            if info["available"]:
                print(f"Nginx 版本:      {info.get('version', '未知')}")
                print(f"Nginx 路径:      {info.get('nginx_path', '未知')}")
                print(f"配置目录:        {info.get('config_dir', '未知')}")
                print(f"sites-available: {info.get('sites_available', '不存在')}")
                print(f"sites-enabled:   {info.get('sites_enabled', '不存在')}")
                print(f"conf.d:          {info.get('conf_d', '不存在')}")
            else:
                print("[ERROR] Nginx 未安装")
                print("提示: 请先安装 Nginx")
        elif nginx_cmd == "generate":
            ngm.generate_from_config(
                config_path=args.config,
                output_dir=args.output,
                dry_run=args.dry_run,
            )
        elif nginx_cmd == "enable":
            ngm.enable_site(args.domain)
        elif nginx_cmd == "disable":
            ngm.disable_site(args.domain)
        elif nginx_cmd == "reload":
            ngm.reload_nginx()
        else:
            nginx_parser.print_help()
        return

    # ========== config 子命令分发 ==========
    if args.command == "config":
        config_cmd = getattr(args, "config_command", None)

        if config_cmd == "init":
            cm.interactive_init(config_path=args.path, force=args.force)
        elif config_cmd == "show":
            cm.show_config(config_path=args.path)
        else:
            config_parser.print_help()
        return

    # ========== git 子命令分发 ==========
    if args.command == "git":
        git_cmd = getattr(args, "git_command", None)

        if git_cmd == "config":
            config_cmd = getattr(args, "config_command", None)
            if config_cmd == "check":
                result = gc.check_git_config(args.project_dir)
                if result:
                    print(f"name:  {result['name']}")
                    print(f"email: {result['email']}")
            elif config_cmd == "fill":
                gc.fill_git_config(
                    project_dir=args.project_dir,
                    config_file=args.config,
                    name=args.name,
                    email=args.email,
                )
            else:
                gc_config_parser.print_help()
        elif git_cmd == "pull":
            gc.git_pull(
                project_dir=args.project_dir,
                remote=args.remote,
                branch=args.branch,
            )
        else:
            git_parser.print_help()
        return

    # ========== le 子命令分发 ==========
    if args.command == "le":
        import zxtoolbox.letsencrypt as le

        le_cmd = getattr(args, "le_command", None)

        provider_config = None
        if getattr(args, "provider_config", None):
            try:
                provider_config = json.loads(args.provider_config)
            except json.JSONDecodeError as e:
                print(f"错误: --provider-config 必须是有效的 JSON: {e}")
                return

        out_dir = (
            Path(args.output).resolve()
            if getattr(args, "output", None)
            else Path("out_le").resolve()
        )

        if le_cmd == "issue":
            le.obtain_cert(
                out_dir=out_dir,
                domains=args.domain,
                provider=args.provider,
                provider_config=provider_config,
                staging=not args.production,
                email=args.email,
                key_size=args.key_size,
            )
        elif le_cmd == "renew":
            le.renew_certs(
                out_dir=out_dir,
                provider_config=provider_config,
                dry_run=args.dry_run,
            )
        elif le_cmd == "batch":
            le.batch_obtain_certs(
                config_path=args.le_config,
                dry_run=args.dry_run,
            )
        elif le_cmd == "status":
            le.show_status(out_dir)
        elif le_cmd == "revoke":
            le.revoke_cert(
                out_dir=out_dir,
                domain=args.domain,
                provider=args.provider,
                provider_config=provider_config,
            )
        elif le_cmd == "init":
            le.init(out_dir)
        else:
            le_parser.print_help()
        return

    # 无子命令时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()