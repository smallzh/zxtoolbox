import argparse
import sys
import zxtoolbox.computer_info as cpi
import zxtoolbox.pyopt_2fa as opt2fa
import zxtoolbox.video_download as vd
import zxtoolbox.ssl_cert as ssl
import zxtoolbox.git_config as gc
import zxtoolbox.config_manager as cm


def main():
    parser = argparse.ArgumentParser(description="ZX Toolbox CLI")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ========== MkDocs 子命令 ==========
    mkdocs_parser = subparsers.add_parser("mkdocs", help="MkDocs 项目管理")
    mkdocs_subparsers = mkdocs_parser.add_subparsers(
        dest="mkdocs_command", help="MkDocs 子命令"
    )

    # mkdocs create
    create_parser = mkdocs_subparsers.add_parser("create", help="创建新的 MkDocs 项目")
    create_parser.add_argument("project_dir", help="项目目录路径")
    create_parser.add_argument(
        "--name", type=str, default=None, help="站点名称（默认使用目录名）"
    )

    # mkdocs build
    build_parser = mkdocs_subparsers.add_parser(
        "build", help="构建 MkDocs 项目到指定目录"
    )
    build_parser.add_argument("project_dir", help="MkDocs 项目目录")
    build_parser.add_argument("-o", "--output", type=str, default=None, help="输出目录")
    build_parser.add_argument(
        "-c", "--config", type=str, default=None, help="配置文件路径（相对或绝对）"
    )
    build_parser.add_argument(
        "--strict", action="store_true", help="严格模式（警告视为错误）"
    )

    # mkdocs batch
    batch_parser = mkdocs_subparsers.add_parser(
        "batch", help="批量构建多个 MkDocs 项目"
    )
    batch_parser.add_argument(
        "config_file",
        nargs="?",
        default=None,
        help="TOML 配置文件路径（默认: ~/.config/zxtool.toml）",
    )
    batch_parser.add_argument(
        "--dry-run", action="store_true", help="仅打印构建计划，不实际执行"
    )

    # 计算机信息参数组
    computer_group = parser.add_argument_group("Computer Info", "计算机信息相关功能")
    computer_group.add_argument(
        "-c", "--computer", action="store_true", help="激活计算机信息显示功能"
    )
    computer_group.add_argument(
        "-s", "--short", action="store_true", help="打印简短信息"
    )
    computer_group.add_argument("-a", "--all", action="store_true", help="打印详细信息")

    # TOTP解析参数组
    totp_group = parser.add_argument_group("TOTP", "TOTP双因素认证解析功能")
    totp_group.add_argument(
        "-t", "--totp", action="store_true", help="激活totp解析功能"
    )
    totp_group.add_argument("-k", "--key", type=str, help="totp待解析的key")

    # 视频下载参数组
    video_group = parser.add_argument_group("Video Download", "在线视频下载功能")
    video_group.add_argument(
        "-v", "--video", action="store_true", help="激活视频下载功能"
    )
    video_group.add_argument("-u", "--url", type=str, help="视频URL地址")
    video_group.add_argument(
        "--vo", "--video-output", dest="video_output", type=str, help="视频输出路径"
    )

    # SSL证书参数组
    ssl_group = parser.add_argument_group("SSL", "自签泛域名SSL证书生成")
    ssl_group.add_argument("--ssl", action="store_true", help="激活SSL证书生成功能")
    ssl_group.add_argument(
        "-d", "--domain", nargs="+", help="域名列表，如 example.dev another.dev"
    )
    ssl_group.add_argument(
        "--ssl-init", action="store_true", help="仅初始化输出目录结构"
    )
    ssl_group.add_argument("--gen-root", action="store_true", help="仅生成Root CA证书")
    ssl_group.add_argument("--flush", action="store_true", help="清空所有历史证书")
    ssl_group.add_argument(
        "--force", action="store_true", help="强制重新生成（覆盖已有证书）"
    )
    ssl_group.add_argument(
        "--output", type=str, default=None, help="输出目录路径（默认: ./out）"
    )

    # ========== Config 子命令 ==========
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

    # ========== Git 子命令 ==========
    git_parser = subparsers.add_parser("git", help="Git 仓库配置管理")
    git_subparsers = git_parser.add_subparsers(dest="git_command", help="Git 子命令")

    # git config
    config_parser = git_subparsers.add_parser("config", help="管理 Git 仓库 user 配置")
    config_parser.add_argument(
        "config_command",
        nargs="?",
        default=None,
        help="子命令: check (检查) / fill (填充)",
    )
    config_parser.add_argument(
        "project_dir",
        nargs="?",
        default=None,
        help="项目目录路径（默认当前目录）",
    )
    config_parser.add_argument(
        "--config", type=str, default=None, help="zxtool.toml 配置文件路径"
    )
    config_parser.add_argument("--name", type=str, default=None, help="git user.name")
    config_parser.add_argument("--email", type=str, default=None, help="git user.email")

    # Let's Encrypt 证书管理参数组
    le_group = parser.add_argument_group(
        "Let's Encrypt", "Let's Encrypt ACME v2 证书管理"
    )
    le_group.add_argument(
        "--le", action="store_true", help="激活 Let's Encrypt 证书管理"
    )
    le_group.add_argument(
        "le_command",
        nargs="?",
        default=None,
        help="子命令: issue / renew / status / revoke / init",
    )
    le_group.add_argument("--le-domain", nargs="+", help="域名列表")
    le_group.add_argument(
        "--provider", default="manual", help="DNS 提供商 (manual/cloudflare/aliyun)"
    )
    le_group.add_argument(
        "--provider-config", type=str, default=None, help="提供商配置 (JSON)"
    )
    le_group.add_argument("--production", action="store_true", help="使用生产环境")
    le_group.add_argument("--email", default="", help="联系邮箱")
    le_group.add_argument(
        "--key-size", type=int, default=2048, choices=[2048, 4096], help="RSA 密钥长度"
    )
    le_group.add_argument("--dry-run", action="store_true", help="仅检查，不执行续签")
    le_group.add_argument(
        "--le-output", type=str, default=None, help="输出目录路径（默认: ./out_le）"
    )

    args = parser.parse_args()

    # ========== MkDocs 子命令分发 ==========
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
        else:
            mkdocs_parser.print_help()
        return

    # ========== Config 子命令分发 ==========
    if args.command == "config":
        config_cmd = getattr(args, "config_command", None)

        if config_cmd == "init":
            cm.interactive_init(config_path=args.path, force=args.force)
        elif config_cmd == "show":
            cm.show_config(config_path=args.path)
        else:
            config_parser.print_help()
        return

    # ========== Git 子命令分发 ==========
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
                config_parser.print_help()
        else:
            git_parser.print_help()
        return

    if args.computer:
        # 调用计算机信息功能
        if args.short:
            cpi.summary_info()
        elif args.all:
            cpi.detailed_info()
        else:
            cpi.get_all_info()
    elif args.totp:
        # 处理 opt解析
        if not args.key:
            print("Error: -k parameters is required for totp function")
            return
        opt2fa.parseTotpCdoe(args.key)
    elif args.video:
        # 处理视频下载
        if not args.url:
            print("Error: -u/--url parameter is required for video download function")
            return
        vd.download_with_progress(args.url, args.video_output)
    elif args.ssl:
        # 处理SSL 证书生成
        from pathlib import Path

        out_dir = Path(args.output).resolve() if args.output else Path("out").resolve()

        if args.flush:
            ssl.init(out_dir)
        elif args.ssl_init:
            ssl.init(out_dir)
        elif args.gen_root:
            ssl.generate_root(out_dir, force=args.force)
        elif args.domain:
            ssl.generate_cert(out_dir, args.domain)
        else:
            print("Error: --domain is required to generate certificates.")
            print("Usage: zxtool --ssl --domain example.dev [another.dev ...]")
    elif args.le:
        # 处理 Let's Encrypt 证书管理
        import json
        from pathlib import Path

        import zxtoolbox.letsencrypt as le

        provider_config = None
        if args.provider_config:
            try:
                provider_config = json.loads(args.provider_config)
            except json.JSONDecodeError as e:
                print(f"错误: --provider-config 必须是有效的 JSON: {e}")
                return

        out_dir = (
            Path(args.le_output).resolve()
            if args.le_output
            else Path("out_le").resolve()
        )
        cmd = args.le_command

        if cmd == "issue":
            if not args.le_domain:
                print("错误: --domain 是必需的")
                return
            le.obtain_cert(
                out_dir=out_dir,
                domains=args.le_domain,
                provider=args.provider,
                provider_config=provider_config,
                staging=not args.production,
                email=args.email,
                key_size=args.key_size,
            )
        elif cmd == "renew":
            le.renew_certs(
                out_dir=out_dir,
                provider_config=provider_config,
                dry_run=args.dry_run,
            )
        elif cmd == "status":
            le.show_status(out_dir)
        elif cmd == "revoke":
            if not args.le_domain:
                print("错误: --domain 是必需的")
                return
            le.revoke_cert(
                out_dir=out_dir,
                domain=args.le_domain[0],
                provider=args.provider,
                provider_config=provider_config,
            )
        elif cmd == "init":
            le.init(out_dir)
        else:
            # 无子命令时显示帮助
            le.main()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
