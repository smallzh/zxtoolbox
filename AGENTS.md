# 项目上下文文档

## 项目概述

**zxtoolbox** 是一个跨平台（Windows、Mac、Linux）的工具集合，用于封装和处理常见的重复性任务。该项目使用 Python 开发，通过 uv 包管理器进行依赖管理和项目构建。

### 项目类型
这是一个 Python 代码项目，使用现代化的 Python 开发工具链。

### 主要技术栈
- **Python**: >= 3.13
- **包管理器**: uv
- **构建系统**: uv_build
- **命令行工具**: 通过 `[project.scripts]` 配置为 `zxtool` 命令

### 核心依赖
- `paramiko`: SSH 部署功能
- `prettytable`: 表格格式化输出
- `psutil`: 系统信息获取
- `py-cpuinfo`: CPU 信息获取
- `pynvml`: NVIDIA GPU 信息获取

## 项目结构

```
toolbox/
├── doc/                    # 文档目录
│   └── index.md           # 项目文档
├── src/                   # 源代码目录
│   └── zxtoolbox/         # 主包
│       ├── __init__.py    # 包初始化，包含 cowsay 函数
│       ├── cli.py         # 命令行入口
│       ├── computer_info.py  # 计算机信息获取（CPU、内存、硬盘）
│       └── video_download.py  # SSH 部署功能
├── dist/                  # 构建输出目录
├── .gitignore            # Git 忽略配置
├── .python-version       # Python 版本锁定
├── LICENSE               # 许可证
├── pyproject.toml        # 项目配置和依赖
├── README.md             # 项目说明
└── uv.lock               # uv 锁定的依赖版本
```

## 构建和运行

### 环境设置
```bash
# 同步依赖（安装项目依赖）
uv sync
```

### 运行项目
```bash
# 直接运行 CLI
zxtool

# 或使用 Python 运行模块
python -m zxtoolbox.cli
```

### 开发模式
```bash
# 使用 uv 运行
uv run zxtool
```

## 核心功能模块

### 1. CLI 入口 (`cli.py`)
- 主入口函数 `main()`
- 调用 `computer_info.get_all_info()` 显示系统信息
- 命令可通过 `zxtoolbox` 全局调用

### 2. 计算机信息获取 (`computer_info.py`)
提供以下功能：
- **CPU 信息**: 获取 CPU 详细信息（型号、频率、缓存等）
- **内存信息**: 获取物理内存和交换内存使用情况
- **磁盘信息**: 获取所有磁盘分区和使用情况
- **格式化**: 使用 PrettyTable 以表格形式美观展示信息

辅助函数：
- `convert_read_str(number)`: 将字节数转换为人类可读格式（KB/MB/GB）
- `init_table(table)`: 初始化表格样式

### 4. 工具函数 (`__init__.py`)
- `cowsay(msg)`: 终端 ASCII 艺术牛说话效果，用于友好的用户欢迎信息

## 开发约定

### 代码风格
- 使用 Python 3.13+ 语法特性
- 遵循 PEP 8 代码规范
- 函数使用描述性的文档字符串

### 模块导入约定
- 主包从 `zxtoolbox` 导入
- 使用绝对导入方式
- 示例：`from zxtoolbox import cowsay`

### 测试
- 测试文件应位于 `src/zxtoolbox/test/` 目录
- 测试文件命名规范：`test_*.py`
- 使用 `uv run pytest` 或类似命令运行测试

### 输出格式
- 使用 `prettytable` 库进行结构化数据输出
- 数值转换使用统一的 `convert_read_str()` 函数

## 常见任务

### 添加新功能
1. 在 `src/zxtoolbox/` 中创建新模块
2. 在 `cli.py` 中添加调用逻辑
3. 更新依赖（如需要）到 `pyproject.toml`
4. 运行 `uv sync` 同步依赖

### 更新依赖
```bash
# 编辑 pyproject.toml
uv sync
```

### 构建分发包
```bash
# uv 会自动使用 uv_build 构建系统
# 构建产物输出到 dist/ 目录
```

## 注意事项

1. **Python 版本**: 项目要求 Python >= 3.13，确保环境版本正确
2. **跨平台兼容**: 代码需要在 Windows、Mac、Linux 上都能运行
3. **SSH 部署模块**: `ssh_deploy.py` 当前为空，需要根据实际需求实现
4. **GPU 信息**: 使用 `pynvml` 库获取 NVIDIA GPU 信息，需要相应的硬件支持