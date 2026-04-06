# 配置文件管理

管理 `zxtool` 的全局配置文件 `~/.config/zxtool.toml`，支持 MkDocs 批量构建和 Git 仓库用户配置。

## 功能特性

- **交互式初始化**: 通过向导式提示，轻松生成配置文件
- **MkDocs 配置**: 配置多个 MkDocs 项目的批量构建参数
- **Git 配置**: 配置默认的 git user.name 和 user.email
- **配置查看**: 快速查看当前配置文件内容
- **强制覆盖**: 支持 `--force` 覆盖已有配置

## 快速开始

### 1. 初始化配置文件

```bash
zxtool config init
```

运行后会启动交互式向导，依次询问：
1. MkDocs 项目路径和构建参数
2. Git 用户名和邮箱

**示例交互：**

```
==================================================
  zxtool.toml 配置初始化向导
==================================================

配置文件路径: /home/user/.config/zxtool.toml

--- MkDocs 批量构建配置 ---
添加需要批量构建的 MkDocs 项目（留空跳过）

项目路径 [1]: /path/to/docs-project1
  输出目录 [默认 site]: /var/www/docs1
  自定义配置文件 [默认 mkdocs.yml]:
  启用严格模式? (y/N):
  [OK] 已添加项目: /path/to/docs-project1

项目路径 [2]:

--- Git 仓库用户配置 ---
添加 Git user.name 和 user.email（留空跳过）

git user.name [1]: John Doe
git user.email: john@example.com
  [OK] 已添加用户: John Doe <john@example.com>

git user.name [2]:

==================================================
  配置摘要
==================================================

MkDocs 项目: 1 个
  - /path/to/docs-project1
    输出: /var/www/docs1

Git 用户: 1 个
  - John Doe <john@example.com>

确认生成配置文件? (Y/n): Y
[OK] 配置文件已创建: /home/user/.config/zxtool.toml

[OK] 配置初始化完成!
```

### 2. 覆盖已有配置

```bash
zxtool config init --force
```

### 3. 查看当前配置

```bash
zxtool config show
```

**输出示例：**

```
配置文件: /home/user/.config/zxtool.toml
----------------------------------------
# zxtool 全局配置文件
# 路径: ~/.config/zxtool.toml
...
```

### 4. 指定配置文件路径

```bash
# 初始化到自定义路径
zxtool config init --path ./my-config.toml

# 查看自定义配置文件
zxtool config show --path ./my-config.toml
```

## 配置文件格式

`~/.config/zxtool.toml` 使用 TOML 格式，支持以下配置节：

### 完整示例

```toml
# zxtool 全局配置文件
# 路径: ~/.config/zxtool.toml
#
# 用法:
#   zxtool mkdocs batch          # 批量构建 MkDocs 项目
#   zxtool git config fill       # 填充 Git 仓库 user 配置

# ============================================
# MkDocs 批量构建配置
# ============================================

[[projects]]
project_dir = "/path/to/docs-project1"
output_dir = "/var/www/docs1"

[[projects]]
project_dir = "/path/to/docs-project2"
output_dir = "/var/www/docs2"
config_file = "custom-mkdocs.yml"
strict = true

# ============================================
# Git 仓库用户配置
# ============================================

[git]

[[git.user]]
name = "John Doe"
email = "john@example.com"

[[git.user]]
name = "Jane Smith"
email = "jane@company.com"
```

### 配置项说明

#### MkDocs 项目配置 (`[[projects]]`)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project_dir` | string | ✅ | MkDocs 项目目录路径 |
| `output_dir` | string | ❌ | 构建输出目录（默认使用 mkdocs.yml 中的 site_dir） |
| `config_file` | string | ❌ | 自定义 MkDocs 配置文件（默认 mkdocs.yml） |
| `strict` | boolean | ❌ | 是否启用严格模式（默认 false） |

#### Git 用户配置 (`[[git.user]]`)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | git user.name |
| `email` | string | ✅ | git user.email |

## 与其他命令的集成

### MkDocs 批量构建

配置完成后，可以直接运行：

```bash
# 使用默认配置文件 (~/.config/zxtool.toml)
zxtool mkdocs batch

# 预览构建计划
zxtool mkdocs batch --dry-run

# 使用自定义配置文件
zxtool mkdocs batch ./my-config.toml
```

### Git 仓库配置填充

配置完成后，`git config fill` 命令会自动读取 `[[git.user]]` 中的第一个用户配置：

```bash
# 自动从配置文件填充
zxtool git config fill /path/to/project

# 输出:
# 已配置 git user:
#   name:  John Doe
#   email: john@example.com
#   仓库:  /path/to/project
```

## 注意事项

- 配置文件默认位于 `~/.config/zxtool.toml`
- 使用 `--force` 会覆盖已有配置，建议先备份
- TOML 格式对缩进敏感，手动编辑时注意保持格式正确
- `[[git.user]]` 目前使用第一个条目作为默认配置
