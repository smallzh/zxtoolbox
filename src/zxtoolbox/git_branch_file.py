import os
import json
import hashlib
import argparse
from datetime import datetime
from fnmatch import fnmatch


def get_file_md5(file_path: str) -> str:
    """计算文件的MD5值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_git_branch_name() -> str:
    """获取当前git分支名称"""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def get_project_name(project_path: str) -> str:
    """获取项目名称"""
    return os.path.basename(project_path)


def read_include_patterns(include_file: str) -> list:
    """读取包含文件模式"""
    patterns = []
    if os.path.exists(include_file):
        with open(include_file, "r", encoding="utf-8") as f:
            patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return patterns


def should_include_file(file_path: str, include_patterns: list) -> bool:
    """判断文件是否应该被包含"""
    if not include_patterns:
        return True
    
    file_name = os.path.basename(file_path)
    for pattern in include_patterns:
        if fnmatch(file_name, pattern) or fnmatch(file_path, pattern):
            return True
    return False


def summary_branch_files(include_file: str, output_dir: str, project_path: str = None):
    """汇总当前分支下的文件信息

    Args:
        include_file: 包含检测的文件列表(txt文件)
        output_dir: 输出目录
        project_path: 项目根目录路径，默认为当前工作目录
    """
    # 获取项目信息
    if project_path is None:
        project_path = os.getcwd()
    project_name = get_project_name(project_path)
    branch_name = get_git_branch_name()
    export_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 读取包含模式
    include_patterns = read_include_patterns(include_file)
    
    # 获取所有文件
    files_info = []
    for root, dirs, files in os.walk(project_path):
        # 跳过.git目录
        if ".git" in dirs:
            continue

        # 跳过.venv目录
        if ".venv" in dirs:
            continue

        # 跳过__pycache__目录
        if "__pycache__" in dirs:
            continue

        # 跳过dist目录
        if "dist" in dirs:
            continue

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, project_path)
            
            # 判断是否应该包含此文件
            if not should_include_file(relative_path, include_patterns):
                continue
            
            try:
                file_size = os.path.getsize(file_path)
                file_md5 = get_file_md5(file_path)
                fid = hashlib.md5(relative_path.encode()).hexdigest()[:8]
                
                files_info.append({
                    "fid": fid,
                    "path": relative_path.replace("\\", "/"),
                    "size": file_size,
                    "md5": file_md5
                })
            except (OSError, IOError) as e:
                print(f"Warning: Cannot read file {file_path}: {e}")
    
    # 构建输出数据
    output_data = {
        "name": branch_name,
        "export_time": export_time,
        "project_path": project_path,
        "files": files_info
    }
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成文件名
    filename = f"{project_name}-{branch_name}-files.json"
    output_file = os.path.join(output_dir, filename)
    
    # 写入JSON文件
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Summary complete! Output file: {output_file}")
    print(f"Total files: {len(files_info)}")


def compare_files(ref_data: dict, current_files_info: list) -> dict:
    """比较文件差异
    
    Args:
        ref_data: 参考数据(之前导出的JSON数据)
        current_files_info: 当前文件信息列表
        
    Returns:
        差异文件信息
    """
    ref_files = {f["path"]: f for f in ref_data["files"]}
    diff_files = []
    
    for current_file in current_files_info:
        path = current_file["path"]
        
        if path not in ref_files:
            # 新增文件
            diff_files.append(current_file)
        else:
            ref_file = ref_files[path]
            # 比较MD5值，检查是否有修改
            if current_file["md5"] != ref_file["md5"]:
                diff_files.append(current_file)
    
    return diff_files


def export_diff_files(ref_file: str, output_dir: str, project_path: str = None):
    """导出分支下的差异文件

    Args:
        ref_file: 参考文件(JSON格式)
        output_dir: 输出目录
        project_path: 项目根目录路径，默认使用参考文件中的路径
    """
    # 读取参考数据
    with open(ref_file, "r", encoding="utf-8") as f:
        ref_data = json.load(f)

    # 获取项目信息
    if project_path is None:
        project_path = ref_data.get("project_path", os.getcwd())
    project_name = get_project_name(project_path)
    branch_name = get_git_branch_name()
    export_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 获取当前文件信息
    current_files_info = []
    for root, dirs, files in os.walk(project_path):
        # 跳过.git目录
        if ".git" in dirs:
            continue

        # 跳过.venv目录
        if ".venv" in dirs:
            continue

        # 跳过__pycache__目录
        if "__pycache__" in dirs:
            continue

        # 跳过dist目录
        if "dist" in dirs:
            continue

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, project_path)
            
            try:
                file_size = os.path.getsize(file_path)
                file_md5 = get_file_md5(file_path)
                fid = hashlib.md5(relative_path.encode()).hexdigest()[:8]
                
                current_files_info.append({
                    "fid": fid,
                    "path": relative_path.replace("\\", "/"),
                    "size": file_size,
                    "md5": file_md5
                })
            except (OSError, IOError) as e:
                print(f"Warning: Cannot read file {file_path}: {e}")
    
    # 比较差异
    diff_files = compare_files(ref_data, current_files_info)
    
    if not diff_files:
        print("No diff files found!")
        return
    
    # 构建输出数据
    output_data = {
        "name": branch_name,
        "export_time": export_time,
        "project_path": project_path,
        "files": diff_files
    }
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成文件名
    filename = f"{project_name}-{branch_name}-diff-files.json"
    output_file = os.path.join(output_dir, filename)
    
    # 写入差异文件信息JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # 复制差异文件本身
    for diff_file in diff_files:
        src_path = os.path.join(project_path, diff_file["path"])
        
        # 将路径中的/替换为_作为文件名
        dest_filename = diff_file["path"].replace("/", "_").replace("\\", "_")
        dest_path = os.path.join(output_dir, dest_filename)
        
        try:
            with open(src_path, "rb") as src_f:
                with open(dest_path, "wb") as dest_f:
                    dest_f.write(src_f.read())
        except (OSError, IOError) as e:
            print(f"Warning: Cannot copy file {src_path}: {e}")
    
    print(f"Diff export complete! Output file: {output_file}")
    print(f"Total diff files: {len(diff_files)}")


def copy_diff_files(ref_file: str, project_path: str = None):
    """复制差异文件到对应目录

    Args:
        ref_file: 参考文件(JSON格式，包含差异文件信息)
        project_path: 项目根目录路径，默认使用参考文件中的路径
    """
    # 读取差异文件信息
    with open(ref_file, "r", encoding="utf-8") as f:
        diff_data = json.load(f)

    if project_path is None:
        project_path = diff_data.get("project_path", os.getcwd())
    diff_files = diff_data["files"]
    
    # 获取参考文件所在目录
    ref_dir = os.path.dirname(ref_file)
    
    copied_count = 0
    for diff_file in diff_files:
        # 源文件：在参考文件所在目录中，文件名是路径转换后的形式
        src_filename = diff_file["path"].replace("/", "_").replace("\\", "_")
        src_path = os.path.join(ref_dir, src_filename)
        
        # 目标文件：在项目路径中的原始位置
        dest_path = os.path.join(project_path, diff_file["path"])
        
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # 复制文件
            with open(src_path, "rb") as src_f:
                with open(dest_path, "wb") as dest_f:
                    dest_f.write(src_f.read())
            
            copied_count += 1
            print(f"Copied: {diff_file['path']}")
        except (OSError, IOError) as e:
            print(f"Warning: Cannot copy file {src_path} to {dest_path}: {e}")
    
    print(f"Copy complete! Total files copied: {copied_count}/{len(diff_files)}")


def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description="Git Branch File Tool")
    
    # git功能开关
    parser.add_argument("-g", "--git", action="store_true", help="激活git分支相关功能")
    
    # 子功能选择
    parser.add_argument("-s", "--summary", action="store_true", help="汇总当前分支文件信息")
    parser.add_argument("-e", "--export", action="store_true", help="导出分支差异文件")
    parser.add_argument("-c", "--copy", action="store_true", help="复制差异文件到对应目录")
    
    # 参数
    parser.add_argument("-i", "--include", help="包含检测的文件列表(txt文件)")
    parser.add_argument("-o", "--output", help="输出目录")
    parser.add_argument("-f", "--file", help="参考文件路径(JSON文件)")
    
    args = parser.parse_args()
    
    if not args.git:
        parser.print_help()
        return
    
    if args.summary:
        if not args.include or not args.output:
            print("Error: -i and -o parameters are required for summary function")
            return
        summary_branch_files(args.include, args.output)
    elif args.export:
        if not args.file or not args.output:
            print("Error: -f and -o parameters are required for export diff function")
            return
        export_diff_files(args.file, args.output)
    elif args.copy:
        if not args.file:
            print("Error: -f parameter is required for copy function")
            return
        copy_diff_files(args.file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()