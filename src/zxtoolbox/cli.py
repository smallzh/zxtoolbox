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

    # Git分支管理参数组
    git_group = parser.add_argument_group("Git Branch", "Git分支相关功能")
    git_group.add_argument("-g", "--git", action="store_true", help="激活git分支相关功能")
    git_group.add_argument("--summary", action="store_true", help="汇总当前分支文件信息")
    git_group.add_argument("-e", "--export", action="store_true", help="导出分支差异文件")
    git_group.add_argument("--copy", action="store_true", help="复制差异文件到对应目录")
    git_group.add_argument("-i", "--include", help="包含检测的文件列表(txt文件)")
    git_group.add_argument("-o", "--output", help="输出目录")
    git_group.add_argument("-f", "--file", help="参考文件路径(JSON文件)")
    git_group.add_argument("-p", "--project", help="项目根目录路径（默认为当前目录）")

    # TOTP解析参数组
    totp_group = parser.add_argument_group("TOTP", "TOTP双因素认证解析功能")
    totp_group.add_argument("-t", "--totp", action="store_true", help="激活totp解析功能")
    totp_group.add_argument("-k", "--key", type=str, help="totp待解析的key")

    # 视频下载参数组
    video_group = parser.add_argument_group("Video Download", "在线视频下载功能")
    video_group.add_argument("-v", "--video", action="store_true", help="激活视频下载功能")
    video_group.add_argument("-u", "--url", type=str, help="视频URL地址")
    video_group.add_argument("--vo", "--video-output", dest="video_output", type=str, help="视频输出路径")

    # Mkdocs参数组
    mkdocs_group = parser.add_argument_group("Mkdocs", "Mkdocs文档导航生成功能")
    mkdocs_group.add_argument("-m", "--mkdocs", action="store_true", help="激活mkdocs相关功能")
    mkdocs_group.add_argument("-d", "--doc", type=str, default="doc", help="文档目录名称（默认为doc）")

    args = parser.parse_args()

    if args.computer:
        # 调用计算机信息功能
        if args.short:
            cpi.summary_info()
        elif args.all:
            cpi.detailed_info()
        else:
            cpi.get_all_info()
    elif args.git:
        # 调用git分支文件功能
        if args.summary:
            if not args.include or not args.output:
                print("Error: -i and -o parameters are required for summary function")
                return
            gbf.summary_branch_files(args.include, args.output, args.project)
        elif args.export:
            if not args.file or not args.output:
                print("Error: -f and -o parameters are required for export diff function")
                return
            gbf.export_diff_files(args.file, args.output, args.project)
        elif args.copy:
            if not args.file:
                print("Error: -f parameter is required for copy function")
                return
            gbf.copy_diff_files(args.file, args.project)
        else:
            print("Please specify a git function: --summary, -e (export), or --copy")
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
    elif args.mkdocs:
        # 处理Mkdocs导航生成
        mng.generate_nav(args.doc)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
