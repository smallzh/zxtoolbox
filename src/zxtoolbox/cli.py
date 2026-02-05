import argparse
import zxtoolbox.computer_info as cpi
import zxtoolbox.git_branch_file as gbf
import zxtoolbox.pyopt_2fa as opt2fa


def main():
    parser = argparse.ArgumentParser(description="ZX Toolbox CLI")

    # 计算机信息相关功能
    parser.add_argument("-c", "--computer", action="store_true", help="激活计算机信息显示功能")
    parser.add_argument("-s", "--short", action="store_true", help="打印简短信息")
    parser.add_argument("-a", "--all", action="store_true", help="打印详细信息")

    # git分支相关功能
    parser.add_argument("-g", "--git", action="store_true", help="激活git分支相关功能")
    parser.add_argument("-e", "--export", action="store_true", help="导出分支差异文件")
    parser.add_argument("-i", "--include", help="包含检测的文件列表(txt文件)")
    parser.add_argument("-o", "--output", help="输出目录")
    parser.add_argument("-f", "--file", help="参考文件路径(JSON文件)")

    # opt解析
    parser.add_argument("-t", "--totp", action="store_true", help="激活totp解析功能")
    parser.add_argument("-k", "--key", type=str, help="totp待解析的key")

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
            gbf.summary_branch_files(args.include, args.output)
        elif args.export:
            if not args.file or not args.output:
                print("Error: -f and -o parameters are required for export diff function")
                return
            gbf.export_diff_files(args.file, args.output)
        elif args.copy:
            if not args.file:
                print("Error: -f parameter is required for copy function")
                return
            gbf.copy_diff_files(args.file)
        else:
            print("Please specify a git function: -e (export)")
    elif args.totp:
        # 处理 opt解析
        if not args.key:
            print("Error: -k parameters is required for totp function")
            return
        opt2fa.parseTotpCdoe(args.key)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
