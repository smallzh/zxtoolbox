# Git 仓库配置管理

管理 Git 仓库的 `.git/config` 中的 `user.name` 和 `user.email` 配置。支持检查现有配置、交互式填充、以及从全局配置文件自动填充。

## 功能特性

- **检查配置**: 快速查看项目的 git user 配置状态
- **自动填充**: 从 `~/.config/zxtool.toml` 的 `[[git.user]]` 节点读取默认配置
- **交互式输入**: 未找到配置时提示用户手动输入
- **命令行指定**: 通过 `--name` 和 `--email` 直接指定配置值
- **仓库自动发现**: 从指定目录向上查找 `.git` 目录，支持子目录执行

## 快速开始

### 1. 检查项目的 git user 配置

```bash
zxtool git config check [项目路径]
```

| 参数 | 说明 |
|------|------|
| `project_dir` | 项目目录路径（可选，默认当前目录） |

**示例：**

```bash
# 检查当前目录
zxtool git config check

# 检查指定项目
zxtool git config check /path/to/my-project
```

**输出示例（已配置）：**

```
name:  John Doe
email: john@example.com
```

**输出示例（未配置）：**

无输出（返回空表示未找到 user 配置）。

### 2. 填充项目的 git user 配置

```bash
zxtool git config fill [项目路径] [--config 配置文件] [--name 名称] [--email 邮箱]
```

| 参数 | 说明 |
|------|------|
| `project_dir` | 项目目录路径（可选，默认当前目录） |
| `--config` | zxtool.toml 配置文件路径（默认 `~/.config/zxtool.toml`） |
| `--name` | 直接指定 git user.name |
| `--email` | 直接指定 git user.email |

**配置填充优先级：**

1. 命令行指定的 `--name` 和 `--email`
2. 从 zxtool.toml 配置文件的 `[[git.user]]` 节点读取
3. 交互式提示用户输入

**示例：**

```bash
# 交互式填充（提示输入 name 和 email）
zxtool git config fill

# 从默认配置文件 (~/.config/zxtool.toml) 自动填充
zxtool git config fill

# 指定配置文件
zxtool git config fill --config ./my-config.toml

# 直接指定 name 和 email
zxtool git config fill --name "John Doe" --email "john@example.com"

# 指定项目路径
zxtool git config fill /path/to/my-project --name "John Doe" --email "john@example.com"
```

**输出示例：**

```
已配置 git user:
  name:  John Doe
  email: john@example.com
  仓库:  /path/to/my-project
```

## 全局配置文件格式

在 `~/.config/zxtool.toml` 中配置 `[[git.user]]` 节点：

```toml
[[git.user]]
name = "John Doe"
email = "john@example.com"

[[git.user]]
name = "Jane Smith"
email = "jane@company.com"
```

> **注意**: 目前使用第一个 `[[git.user]]` 条目作为默认配置。

**使用示例：**

```bash
# 配置后，fill 命令会自动读取
zxtool git config fill /path/to/project
# 输出:
# 已配置 git user:
#   name:  John Doe
#   email: john@example.com
#   仓库:  /path/to/project
```

## 注意事项

- 项目必须是 Git 仓库（包含 `.git` 目录）
- 如果项目已配置完整的 user.name 和 user.email，`fill` 命令会显示现有配置并退出
- 交互式输入时，按 `Ctrl+C` 可取消操作
- 配置文件路径支持绝对路径和相对路径
