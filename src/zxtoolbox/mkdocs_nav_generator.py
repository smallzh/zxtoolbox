"""
Mkdocs导航自动生成模块

根据指定目录下的md文件结构和内容，自动生成mkdocs的nav导航配置。
"""

import os
import yaml


def get_md_title(file_path: str) -> str:
    """
    从md文件中提取标题

    Args:
        file_path: md文件路径

    Returns:
        文件标题，如果未找到则返回文件名（不含扩展名）
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('# '):
                    return line[2:].strip()
    except Exception:
        pass

    # 如果没有找到标题，使用文件名
    return os.path.splitext(os.path.basename(file_path))[0]


def scan_doc_files(doc_dir: str) -> dict:
    """
    扫描文档目录，返回按目录层级组织的文件结构

    Args:
        doc_dir: 文档根目录

    Returns:
        字典，键为文件相对路径，值为文件标题
    """
    files_dict = {}

    for root, dirs, files in os.walk(doc_dir):
        # 跳过隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, doc_dir)
                title = get_md_title(file_path)
                files_dict[relative_path] = title

    return files_dict


def build_nav_tree(files_dict: dict) -> list:
    """
    根据文件结构构建导航树

    Args:
        files_dict: 文件字典，键为相对路径，值为标题

    Returns:
        导航列表
    """
    # 按路径排序
    sorted_files = sorted(files_dict.items())

    nav_tree = []

    for file_path, title in sorted_files:
        # 跳过 index.md，我们最后单独处理
        if file_path == 'index.md' or file_path.endswith('/index.md'):
            continue

        parts = file_path.replace('\\', '/').split('/')

        if len(parts) == 1:
            # 根目录下的文件
            nav_tree.append({title: file_path})
        else:
            # 子目录下的文件
            # 这里简化处理，只处理一级目录嵌套
            group_name = parts[0]
            # 查找是否已存在这个组
            found = False
            for item in nav_tree:
                if group_name in item:
                    item[group_name].append({title: file_path})
                    found = True
                    break
            if not found:
                nav_tree.append({group_name: [{title: file_path}]})

    # 按文件名排序
    def sort_nav(nav_list):
        if isinstance(nav_list, list):
            nav_list.sort(key=lambda x: list(x.values())[0] if isinstance(x, dict) else str(x))
            for item in nav_list:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, list):
                            sort_nav(value)

    sort_nav(nav_tree)

    # 添加 index.md 到最前面
    if 'index.md' in files_dict:
        nav_tree.insert(0, {files_dict['index.md']: 'index.md'})

    return nav_tree


def generate_nav(doc_dir: str = "doc"):
    """
    生成mkdocs的nav导航配置

    Args:
        doc_dir: 文档目录名称
    """
    # 检查目录是否存在
    if not os.path.isdir(doc_dir):
        print(f"Error: Directory '{doc_dir}' does not exist.")
        return

    # 扫描文档文件
    files_dict = scan_doc_files(doc_dir)

    if not files_dict:
        print(f"No markdown files found in '{doc_dir}' directory.")
        return

    # 构建导航树
    nav_tree = build_nav_tree(files_dict)

    # 生成YAML输出
    nav_config = {"nav": nav_tree}

    # 输出导航配置
    print("# Generated navigation configuration")
    print("# Copy the following to your mkdocs.yml under 'nav:' section")
    print("")

    # 直接输出nav部分
    yaml_output = yaml.dump(nav_tree, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(yaml_output)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mkdocs Navigation Generator")
    parser.add_argument("-d", "--doc", type=str, default="doc", help="Documentation directory name")

    args = parser.parse_args()
    generate_nav(args.doc)
