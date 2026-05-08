# zxtoolbox

Window、Mac、Linux系统中，对经常做的一些重复性事情的封装

<div align="center">

中文 | [英文](./README.md)

</div>

## 0x01. 安装

```shell
uv tool install zxtoolbox
```

## 0x02. 常用命令

### Markdown 转 PDF

```shell
# 单个 Markdown 文件转 PDF
zxtool mkpdf ./README.md

# 目录中的 Markdown 合并转 PDF
zxtool mkpdf ./docs -o ./dist/docs.pdf
```

说明：

- 支持常见 Markdown 样式：标题、列表、表格、引用、代码块、图片
- 目录模式下默认读取目录内的 `README.md`，也可通过 `--file` 指定入口 Markdown
- 默认内置 Mermaid 运行时文件，离线可用，不依赖 CDN
- 需要本机安装 Edge、Chrome 或 Chromium 之一用于无头打印 PDF

完整说明见 [docs/mkpdf_manager.md](./docs/mkpdf_manager.md)。

## 0x03. 目录结构
```text
toolbox/
├── doc/                    # 文档目录
│   ├── index.md           # 项目文档
│   ├── computer_info.md   # 计算机信息获取文档
│   ├── config_manager.md  # 配置文件管理文档
│   ├── git_config.md      # Git 仓库配置文档
│   ├── letsencrypt.md     # Let's Encrypt 证书文档
│   ├── mkdocs_manager.md  # MkDocs 项目管理文档
│   ├── mkpdf_manager.md   # Markdown 转 PDF 文档
│   ├── ssl_cert.md        # SSL 证书生成文档
│   └── video_download.md  # 视频下载文档
├── src/                   # 源代码目录
│   └── zxtoolbox/         # 主包
│       ├── __init__.py    # 包初始化
│       ├── cli.py         # 命令行入口
│       ├── computer_info.py    # 计算机信息获取
│       ├── config_manager.py   # 配置文件管理
│       ├── git_config.py       # Git 仓库配置管理
│       ├── letsencrypt.py      # Let's Encrypt 证书管理
│       ├── mkdocs_manager.py   # MkDocs 项目管理
│       ├── mkpdf_manager.py    # Markdown 转 PDF
│       ├── pyopt_2fa.py        # 2FA 工具
│       ├── ssl_cert.py         # SSL 证书生成
│       ├── video_download.py   # 视频下载
│       └── test/          # 测试目录
├── pyproject.toml        # 项目配置和依赖
├── README.md             # 项目说明
└── uv.lock               # uv 锁定的依赖版本
```

## 0x04. 依赖的包

### 核心依赖

| 包名 | 用途 | 网站 |
|------|------|------|
| paramiko | SSH 连接 | [paramiko.org](https://www.paramiko.org/) |
| prettytable | 表格美化 | [github.com](https://github.com/jazzband/prettytable) |
| psutil | 系统信息 | [psutil.readthedocs.io](https://psutil.readthedocs.io/) |
| py-cpuinfo | CPU 信息 | [github.com](https://github.com/workhorsy/py-cpuinfo) |
| pynvml | NVIDIA GPU 信息 | [github.com](https://github.com/gpuopenanalytics/pynvml) |
| pyotp | 2FA 一次性密码 | [github.com](https://github.com/pyauth/pyotp) |
| yt-dlp | 视频下载 | [github.com](https://github.com/yt-dlp/yt-dlp) |
| pyyaml | YAML 解析 | [pyyaml.org](https://pyyaml.org/) |
| acme | ACME 协议（Let's Encrypt） | [github.com](https://github.com/certbot/certbot) |
| cryptography | 加密功能 | [cryptography.io](https://cryptography.io/) |
| requests | HTTP 请求 | [requests.readthedocs.io](https://requests.readthedocs.io/) |
| mkdocs | Documentation site building | [mkdocs.org](https://www.mkdocs.org/) |
| mkdocs-smzhbook-theme | MkDocs theme | [github.com](https://github.com/smallzh/mkdocs-smzhbook-theme) |
| Markdown | Markdown 渲染 | [python-markdown.github.io](https://python-markdown.github.io/) |

## 0x05. 运行单元测试

项目使用 `pytest` 作为测试框架，测试文件位于 `src/zxtoolbox/test/` 目录。

### 安装测试依赖

```shell
uv add --dev pytest
```

### 运行全部测试

```shell
uv run pytest src/zxtoolbox/test/ -v
```

### 运行单个测试文件

```shell
uv run pytest src/zxtoolbox/test/test_cli.py -v
```

### 运行指定测试类或方法

```shell
# 运行指定测试类
uv run pytest src/zxtoolbox/test/test_cli.py::TestCliGit -v

# 运行指定测试方法
uv run pytest src/zxtoolbox/test/test_cli.py::TestCliGit::test_git_config_check -v
```

### 查看测试覆盖率

```shell
uv add --dev pytest-cov
uv run pytest src/zxtoolbox/test/ --cov=zxtoolbox --cov-report=term-missing
```
