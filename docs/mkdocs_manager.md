# MkDocs 项目管理

基于 MkDocs 的项目管理工具，支持创建、构建和批量发布文档站点。

## 0x01. 功能特性

- **创建项目**: 快速初始化新的 MkDocs 文档项目
- **构建项目**: 将 MkDocs 项目构建为静态 HTML，输出到指定目录
- **批量构建**: 通过 TOML 配置文件，一次性构建并发布多个 MkDocs 项目

## 0x02. 快速开始

### 1. 创建新的 MkDocs 项目

```bash
zxtool mkdocs create <项目目录> [--name <站点名称>]
```

| 参数 | 说明 |
|------|------|
| `project_dir` | 项目目录路径（不存在则自动创建） |
| `--name` | 站点名称（默认使用目录名） |

**示例：**

```bash
# 创建名为 "My Docs" 的项目
zxtool mkdocs create ./my-docs --name "My Docs"

# 创建后目录结构：
# my-docs/
# ├── mkdocs.yml      # MkDocs 配置文件
# └── docs/
#     └── index.md    # 文档首页
```

### 2. 构建单个项目

```bash
zxtool mkdocs build <项目目录> [-o <输出目录>] [-c <配置文件>] [--strict]
```

| 参数 | 说明 |
|------|------|
| `project_dir` | MkDocs 项目目录（包含 mkdocs.yml） |
| `-o, --output` | 输出目录（默认使用 mkdocs.yml 中的 site_dir） |
| `-c, --config` | 配置文件路径（相对或绝对路径，默认 mkdocs.yml） |
| `--strict` | 严格模式（警告视为错误） |

**示例：**

```bash
# 构建到默认 site 目录
zxtool mkdocs build ./my-docs

# 构建到指定输出目录
zxtool mkdocs build ./my-docs -o ./output/html

# 使用自定义配置文件
zxtool mkdocs build ./my-docs -o ./output/html -c custom-mkdocs.yml

# 严格模式构建
zxtool mkdocs build ./my-docs -o ./output/html --strict
```

### 3. 批量构建多个项目

```bash
zxtool mkdocs batch [配置文件] [--dry-run]
```

| 参数 | 说明 |
|------|------|
| `config_file` | TOML 配置文件路径（可选，默认读取 `~/.config/zxtool.toml`） |
| `--dry-run` | 仅打印构建计划，不实际执行 |

**配置文件路径优先级：**

1. 命令行指定：`zxtool mkdocs batch ./my-config.toml`
2. 默认路径：`~/.config/zxtool.toml`（不指定配置文件时自动读取）

**TOML 配置文件格式：**

```toml
[[projects]]
project_dir = "/path/to/project1"
output_dir = "/path/to/output1"

[[projects]]
project_dir = "/path/to/project2"
output_dir = "/path/to/output2"

[[projects]]
project_dir = "/path/to/project3"
output_dir = "/path/to/output3"
config_file = "custom-mkdocs.yml"  # 可选，使用自定义配置文件
strict = true                       # 可选，启用严格模式
```

**示例：**

```bash
# 使用默认配置文件 (~/.config/zxtool.toml)
zxtool mkdocs batch

# 预览构建计划（使用默认配置）
zxtool mkdocs batch --dry-run

# 使用自定义配置文件
zxtool mkdocs batch ./batch-config.toml --dry-run

# 执行批量构建（自定义配置）
zxtool mkdocs batch ./batch-config.toml
```

**输出示例：**

```
加载配置文件: ./batch-config.toml
共 3 个项目待构建

--- [1/3] ---
构建项目: /path/to/project1
配置文件: /path/to/project1/mkdocs.yml
输出目录: /path/to/output1
[OK] 构建成功: /path/to/output1

--- [2/3] ---
...

========================================
批量构建完成: 3/3 成功
========================================
  [OK] /path/to/project1
  [OK] /path/to/project2
  [OK] /path/to/project3
```

## 0x03. 预览文档

### 1. 启动开发服务器

```bash
zxtool mkdocs serve <项目目录> [-a <地址:端口>] [-c <配置文件>] [--no-livereload]
```

| 参数 | 说明 |
|------|------|
| `project_dir` | MkDocs 项目目录（包含 mkdocs.yml） |
| `-a, --dev-addr` | 开发服务器地址（格式: IP:PORT，默认 127.0.0.1:8000） |
| `-c, --config` | 配置文件路径（相对或绝对路径，默认 mkdocs.yml） |
| `--no-livereload` | 禁用热重载功能 |

**示例：**

```bash
# 在默认地址启动预览
zxtool mkdocs serve ./my-docs

# 指定地址和端口
zxtool mkdocs serve ./my-docs -a 0.0.0.0:8080

# 使用自定义配置文件
zxtool mkdocs serve ./my-docs -c custom-mkdocs.yml

# 禁用热重载
zxtool mkdocs serve ./my-docs --no-livereload
```

开发服务器启动后，在浏览器中访问指定地址即可实时预览文档。编辑源文件后，页面会自动刷新（热重载模式下）。按 `Ctrl+C` 停止服务器。

## 0x04. 注意事项

- MkDocs 为核心依赖，安装 zxtoolbox 时自动安装（`uv sync` 或 `uv tool install zxtoolbox`）
- MkDocs 主题（如 smzhbook）为可选依赖，需要额外安装：`uv sync --extra docs`
- 输出目录不存在时会自动创建
- 批量构建时，单个项目失败不影响其他项目的构建

