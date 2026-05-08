# zxtoolbox

`zxtoolbox` 是一个面向 Windows、Mac、Linux 的常用工具集合，用来封装重复性操作。

## 功能概览


- **计算机信息获取**: 获取计算机的 CPU、GPU、内存、硬盘等相关信息
- **Git 仓库配置**: 管理 Git 仓库的 user.name 和 user.email 配置,支持自动填充
- **配置文件管理**: 交互式生成和管理全局 zxtool.toml 配置文件
- **自签 SSL 证书**: 生成泛域名自签证书,支持多域名和 SAN,方便开发调试
- **Let's Encrypt 证书**: 通过 ACME v2 协议获取免费证书,支持 DNS-01 自动验证和续签
- **MkDocs 项目管理**: 批量构建和发布 MkDocs 文档站点,支持开发服务器预览
- **Markdown 转 PDF**: 将单个 Markdown 或文档目录转换为 PDF,支持 Mermaid 图形
- **HTTP 静态文件服务**: 快速启动本地静态文件 HTTP 服务,用于预览和临时共享目录
- **Nginx 站点配置**: 根据配置自动生成和管理 Nginx 站点配置,支持 HTTPS 和批量发布
- **TOTP 2FA 解析**: 解析 TOTP 双因素认证密钥
- **在线视频下载**: 基于 yt-dlp 下载在线视频
- **EPUB 转 Markdown**: 将Epub文件转换成Markdown目录
- **目录备份拷贝**: 备份一个目录到目标目录

## 安装

```bash
uv tool install zxtoolbox
```

## 基本用法

```bash
zxtool --help
```

## 命令一览

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `ci` | 显示计算机信息 | `zxtool ci --all` |
| `mkdocs` | MkDocs 项目管理 | `zxtool mkdocs build ./docs-site` |
| `mkpdf` | Markdown 转 PDF | `zxtool mkpdf ./docs -o ./dist/docs.pdf` |
| `nginx` | Nginx 配置管理 | `zxtool nginx generate` |
| `le` | Let's Encrypt 证书管理 | `zxtool le issue -d example.com` |
| `ssl` | 自签 SSL 证书生成 | `zxtool ssl cert -d example.dev` |
| `feishu` | 飞书客户端管理 | `zxtool feishu check` |
| `video` | 在线视频下载 | `zxtool video -u https://example.com/video` |
| `totp` | TOTP 解析 | `zxtool totp -k SECRET_KEY` |
| `epub` | EPUB 转 Markdown | `zxtool epub convert ./book.epub -o ./book_md` |
| `backup` | 目录备份拷贝 | `zxtool backup copy ./src ./dst` |
| `http` | 静态文件 HTTP 服务 | `zxtool http serve ./dist -p 8000` |
| `config` | 配置文件管理 | `zxtool config init` |
| `git` | Git 仓库管理（配置/拉取） | `zxtool git config fill` / `zxtool git pull` |

## 0x03. 目录结构

```text
toolbox/
├── docs/                  # 文档目录
│   ├── index.md           # 项目文档
│   ├── computer_info.md   # 计算机信息获取文档
│   ├── config_manager.md  # 配置文件管理文档
│   ├── git_config.md      # Git 仓库配置文档
│   ├── http_server.md     # HTTP 静态文件服务文档
│   ├── letsencrypt.md     # Let's Encrypt 证书文档
│   ├── mkdocs_manager.md  # MkDocs 项目管理文档
│   ├── mkpdf_manager.md   # Markdown 转 PDF 文档
│   ├── nginx_manager.md   # Nginx 配置文档
│   ├── ssl_cert.md        # SSL 证书生成文档
│   ├── totp.md            # TOTP 2FA 文档
│   └── video_download.md  # 视频下载文档
├── src/                   # 源代码目录
│   └── zxtoolbox/         # 主包
│       ├── __init__.py    # 包初始化
│       ├── cli.py         # 命令行入口
│       ├── computer_info.py    # 计算机信息获取
│       ├── config_manager.py   # 配置文件管理
│       ├── git_config.py       # Git 仓库配置管理
│       ├── http_server.py      # HTTP 静态文件服务
│       ├── letsencrypt.py      # Let's Encrypt 证书管理
│       ├── mkdocs_manager.py   # MkDocs 项目管理
│       ├── mkpdf_manager.py    # Markdown 转 PDF
│       ├── nginx_manager.py    # Nginx 配置管理
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
| nvidia-ml-py | NVIDIA GPU 信息 | [github.com](https://github.com/NVIDIA/nvidia-ml-py) |
| pyotp | 2FA 一次性密码 | [github.com](https://github.com/pyauth/pyotp) |
| yt-dlp | 视频下载 | [github.com](https://github.com/yt-dlp/yt-dlp) |
| pyyaml | YAML 解析 | [pyyaml.org](https://pyyaml.org/) |
| acme | ACME 协议（Let's Encrypt） | [github.com](https://github.com/certbot/certbot) |
| cryptography | 加密功能 | [cryptography.io](https://cryptography.io/) |
| requests | HTTP 请求 | [requests.readthedocs.io](https://requests.readthedocs.io/) |
| mkdocs | 文档站点构建 | [mkdocs.org](https://www.mkdocs.org/) |
| mkdocs-smzhbook-theme | MkDocs smzhbook 主题 | [github.com](https://github.com/smallzh/mkdocs-smzhbook-theme) |
| Markdown | Markdown 渲染 | [python-markdown.github.io](https://python-markdown.github.io/) |
