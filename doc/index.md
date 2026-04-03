# zxtoolbox

Window、Mac、Linux系统中,对经常做的一些重复性事情的封装

## 功能特性

- **SSH 部署**: 通过 SSH 的方式,便捷地部署项目
- **计算机信息获取**: 获取计算机的 CPU、GPU、内存、硬盘等相关信息
- **Git 分支文件管理**: 导出 Git 分支文件信息,支持差异对比和文件复制
- **自签 SSL 证书**: 生成泛域名自签证书,支持多域名和 SAN,方便开发调试
- **Let's Encrypt 证书**: 通过 ACME v2 协议获取免费证书,支持自动续签

## 快速开始

### 安装

```bash
uv sync
```

参考:[uv的Projects下的Creating projects](https://docs.astral.sh/uv/concepts/projects/init/)

### 使用

```bash
zxtoolbox -h
```

## 项目结构

```
toolbox/
├── doc/                    # 文档目录
│   ├── index.md           # 首页
│   └── git_branch_file.md # Git 分支文件管理文档
├── src/                   # 代码目录
│   └── zxtoolbox/         # 主包
│       ├── __init__.py
│       ├── cli.py         # 命令行入口
│       ├── ssh_deploy.py  # SSH 部署功能
│       ├── computer_info.py # 计算机信息获取
│       └── git_branch_file.py # Git 分支文件管理
├── pyproject.toml        # 项目配置
└── README.md             # 项目说明
```

## 依赖项

| 包名 | 用途 | 网站 |
|------|------|------|
| paramiko | SSH 连接 | [paramiko.org](https://www.paramiko.org/) |
| prettytable | 表格美化 | [github.com](https://github.com/jazzband/prettytable) |
| psutil | 系统信息 | [psutil.readthedocs.io](https://psutil.readthedocs.io/) |
| py-cpuinfo | CPU 信息 | [github.com](https://github.com/workhorsy/py-cpuinfo) |
| pynvml | NVIDIA GPU 信息 | [github.com](https://github.com/gpuopenanalytics/pynvml) |