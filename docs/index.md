# zxtoolbox

Window、Mac、Linux系统中,对经常做的一些重复性事情的封装

## 0x01. 功能特性

- **计算机信息获取**: 获取计算机的 CPU、GPU、内存、硬盘等相关信息
- **Git 仓库配置**: 管理 Git 仓库的 user.name 和 user.email 配置,支持自动填充
- **配置文件管理**: 交互式生成和管理全局 zxtool.toml 配置文件
- **自签 SSL 证书**: 生成泛域名自签证书,支持多域名和 SAN,方便开发调试
- **Let's Encrypt 证书**: 通过 ACME v2 协议获取免费证书,支持 DNS-01 自动验证和续签
- **MkDocs 项目管理**: 批量构建和发布 MkDocs 文档站点,支持开发服务器预览
- **Nginx 站点配置**: 根据配置自动生成和管理 Nginx 站点配置,支持 HTTPS 和批量发布
- **TOTP 2FA 解析**: 解析 TOTP 双因素认证密钥
- **在线视频下载**: 基于 yt-dlp 下载在线视频

## 0x02. 快速开始

### 安装

```bash
uv tool install zxtoolbox
```

### 使用

所有功能通过子命令调用：

```bash
zxtool --help
```

### 命令一览

| 子命令 | 说明 | 示例 |
|--------|------|------|
| `ci` | 显示计算机信息（默认简短） | `zxtool ci` / `zxtool ci --all` |
| `le` | Let's Encrypt 证书管理 | `zxtool le issue -d example.com` |
| `ssl` | 自签 SSL 证书生成 | `zxtool ssl cert -d example.dev` |
| `totp` | TOTP 双因素认证解析 | `zxtool totp -k SECRET_KEY` |
| `video` | 在线视频下载 | `zxtool video -u https://...` |
| `mkdocs` | MkDocs 项目管理 | `zxtool mkdocs serve ./my-docs` |
| `nginx` | Nginx 站点配置管理 | `zxtool nginx generate` |
| `config` | 配置文件管理 | `zxtool config init` |
| `git` | Git 仓库管理（配置/拉取） | `zxtool git config fill` / `zxtool git pull` |

## 0x03. 目录结构

```text
toolbox/
├── doc/                    # 文档目录
│   ├── index.md           # 项目文档
│   ├── ci.md              # 计算机信息获取文档
│   ├── config_manager.md  # 配置文件管理文档
│   ├── git_config.md      # Git 仓库配置文档
│   ├── letsencrypt.md     # Let's Encrypt 证书文档
│   ├── mkdocs_manager.md  # MkDocs 项目管理文档
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
│       ├── letsencrypt.py      # Let's Encrypt 证书管理
│       ├── mkdocs_manager.py   # MkDocs 项目管理
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