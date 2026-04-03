import argparse
import zxtoolbox.computer_info as cpi
import zxtoolbox.git_branch_file as gbf
import zxtoolbox.pyopt_2fa as opt2fa
import zxtoolbox.video_download as vd
import zxtoolbox.mkdocs_nav_generator as mng
import zxtoolbox.ssl_cert as ssl


def main():
    parser = argparse.ArgumentParser(description="ZX Toolbox CLI")

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

    args = parser.parse_args()

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
