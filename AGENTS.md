# 项目上下文文档

## 0x01. 项目概述

**zxtoolbox** 是一个跨平台（Windows、Mac、Linux）的工具集合，用于封装和处理常见的重复性任务。该项目使用 Python 开发，通过 uv 包管理器进行依赖管理和项目构建。

### 项目类型
这是一个 Python 代码项目，使用现代化的 Python 开发工具链。

### 主要技术栈
- **Python**: >= 3.13
- **包管理器**: uv
- **构建系统**: uv_build
- **命令行工具**: 通过 `[project.scripts]` 配置为 `zxtool` 命令

### 核心依赖
- `paramiko`: SSH 连接
- `prettytable`: 表格格式化输出
- `psutil`: 系统信息获取
- `py-cpuinfo`: CPU 信息获取
- `pynvml`: NVIDIA GPU 信息获取
- `pyotp`: 2FA 一次性密码
- `yt-dlp`: 视频下载
- `pyyaml`: YAML 解析
- `cryptography`: 加密功能
- `requests`: HTTP 请求
- `mkdocs`: 文档站点构建
- `mkdocs-smzhbook-theme`: MkDocs 主题
- `lark-oapi`: 飞书客户端 SDK

## 0x02. 项目结构

```
toolbox/
├── doc/                    # 文档目录
│   ├── index.md           # 项目文档
│   ├── computer_info.md   # 计算机信息获取文档
│   ├── config_manager.md  # 配置文件管理文档
│   ├── git_config.md      # Git 仓库配置文档
│   ├── letsencrypt.md     # Let's Encrypt 证书文档
│   ├── mkdocs_manager.md  # MkDocs 项目管理文档
│   ├── nginx_manager.md   # Nginx 站点配置文档
│   ├── ssl_cert.md        # SSL 证书生成文档
│   ├── video_download.md  # 视频下载文档
│   └── feishu_client.md   # 飞书客户端使用说明
├── src/                   # 源代码目录
│   └── zxtoolbox/         # 主包
│       ├── __init__.py    # 包初始化，包含 cowsay 函数
│       ├── cli.py         # 命令行入口
│       ├── computer_info.py    # 计算机信息获取（CPU、内存、硬盘）
│       ├── config_manager.py   # 配置文件管理
│       ├── git_config.py       # Git 仓库配置管理
│       ├── letsencrypt.py      # Let's Encrypt 证书管理（acme.sh 封装）
│       ├── mkdocs_manager.py   # MkDocs 项目管理
│       ├── feishu_client.py    # 飞书客户端集成
│       ├── pyopt_2fa.py        # 2FA 工具
│       ├── ssl_cert.py         # SSL 证书生成
│       ├── video_download.py   # 视频下载
│       └── test/          # 测试目录
├── dist/                  # 构建输出目录
├── .gitignore            # Git 忽略配置
├── .python-version       # Python 版本锁定
├── LICENSE               # 许可证
├── pyproject.toml        # 项目配置和依赖
├── README.md             # 项目说明
└── uv.lock               # uv 锁定的依赖版本
```

## 0x03. 构建和运行

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

## 0x04. 核心功能模块

### 1. CLI 入口 (`cli.py`)
- 主入口函数 `main()`
- 支持多个子命令：computer、git、mkdocs、ssl、letsencrypt、config、video 等
- 命令通过 `zxtool` 全局调用

### 2. 计算机信息获取 (`computer_info.py`)
提供以下功能：
- **CPU 信息**: 获取 CPU 详细信息（型号、频率、缓存等）
- **内存信息**: 获取物理内存和交换内存使用情况
- **磁盘信息**: 获取所有磁盘分区和使用情况
- **GPU 信息**: 获取 NVIDIA GPU 信息
- **格式化**: 使用 PrettyTable 以表格形式美观展示信息

辅助函数：
- `convert_read_str(number)`: 将字节数转换为人类可读格式（KB/MB/GB）
- `init_table(table)`: 初始化表格样式

### 3. Git 仓库配置管理 (`git_config.py`)
- 检查 Git 仓库的 user.name 和 user.email 配置
- 支持从配置文件自动填充
- 支持交互式输入

### 4. 配置文件管理 (`config_manager.py`)
- 交互式初始化 zxtool.toml 配置文件
- 支持 MkDocs 批量构建配置
- 支持 Git 用户配置管理

### 5. MkDocs 项目管理 (`mkdocs_manager.py`)
- 创建新的 MkDocs 项目
- 构建 MkDocs 项目
- 批量构建多个 MkDocs 项目

### 6. SSL 证书生成 (`ssl_cert.py`)
- 生成泛域名自签 SSL 证书
- 支持多域名和 SAN
- 自动生成 Root CA

### 7. Let's Encrypt 证书管理 (`letsencrypt.py`)
- 通过 acme.sh 脚本获取免费证书
- 支持 DNS-01 验证（手动/Cloudflare/阿里云）
- 证书到期自动检测和续签
- 支持自动安装 acme.sh

### 8. 飞书客户端集成 (`feishu_client.py`)
- 使用 WebSocket 长连接接收飞书消息事件
- 支持通过飞书聊天执行 CLI 命令（git pull、mkdocs batch）
- 配置驱动的应用 ID 和密钥管理

### 9. 视频下载 (`video_download.py`)
- 基于 yt-dlp 下载在线视频
- 支持 FFmpeg 音视频合并

### 10. 2FA 工具 (`pyopt_2fa.py`)
- 生成 2FA 一次性密码

### 11. 工具函数 (`__init__.py`)
- `cowsay(msg)`: 终端 ASCII 艺术牛说话效果，用于友好的用户欢迎信息

## 0x05. 开发约定

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

## 0x06. 常见任务

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

## 0x07. 注意事项

1. **Python 版本**: 项目要求 Python >= 3.13，确保环境版本正确
2. **跨平台兼容**: 代码需要在 Windows、Mac、Linux 上都能运行
3. **GPU 信息**: 使用 `pynvml` 库获取 NVIDIA GPU 信息，需要相应的硬件支持