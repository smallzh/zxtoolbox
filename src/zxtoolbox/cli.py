import argparse
import zxtoolbox.computer_info as cpi
import zxtoolbox.git_branch_file as gbf
import zxtoolbox.pyopt_2fa as opt2fa
import zxtoolbox.video_download as vd
import zxtoolbox.mkdocs_nav_generator as mng


def main():
    parser = argparse.ArgumentParser(description="ZX Toolbox CLI")

    # 计算机信息参数组
    computer_group = parser.add_argument_group("Computer Info", "计算机信息相关功能")
    computer_group.add_argument("-c", "--computer", action="store_true", help="激活计算机信息显示功能")
    computer_group.add_argument("-s", "--short", action="store_true", help="打印简短信息")
    computer_group.add_argument("-a", "--all", action="store_true", help="打印详细信息")


    # TOTP解析参数组
    totp_group = parser.add_argument_group("TOTP", "TOTP双因素认证解析功能")
    totp_group.add_argument("-t", "--totp", action="store_true", help="激活totp解析功能")
    totp_group.add_argument("-k", "--key", type=str, help="totp待解析的key")

    # 视频下载参数组
    video_group = parser.add_argument_group("Video Download", "在线视频下载功能")
    video_group.add_argument("-v", "--video", action="store_true", help="激活视频下载功能")
    video_group.add_argument("-u", "--url", type=str, help="视频URL地址")
    video_group.add_argument("--vo", "--video-output", dest="video_output", type=str, help="视频输出路径")


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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
