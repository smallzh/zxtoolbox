# Git 仓库管理

管理 Git 仓库的 `.git/config` 中的 `user.name` 和 `user.email` 配置，以及从远程仓库拉取更新。

## 0x01. 功能特性

- **检查配置**: 快速查看项目的 git user 配置状态
- **自动填充**: 从 `~/.config/zxtool.toml` 的 `[[git.user]]` 节点读取默认配置
- **交互式输入**: 未找到配置时提示用户手动输入
- **命令行指定**: 通过 `--name` 和 `--email` 直接指定配置值
- **仓库自动发现**: 从指定目录向上查找 `.git` 目录，支持子目录执行
- **拉取更新**: 从远程仓库拉取最新内容（git pull）

## 0x02. 命令格式

```bash
zxtool git <子命令> [选项]
```

| 子命令 | 说明 |
|--------|------|
| `config` | 管理 Git 仓库 user 配置 |
| `pull` | 从远程仓库拉取更新（git pull） |

## 0x03. 配置管理（git config）

### 3.1 检查项目的 git user 配置

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

### 3.2 填充项目的 git user 配置

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

## 0x04. 拉取更新（git pull）

从远程仓库拉取最新内容并合并到当前分支。

```bash
zxtool git pull [项目路径] [--remote 远程名称] [--branch 分支名称]
```

| 参数 | 说明 |
|------|------|
| `project_dir` | 项目目录路径（可选，默认当前目录） |
| `--remote` | 远程仓库名称（默认使用仓库配置的 upstream） |
| `--branch` | 分支名称（默认使用当前分支） |

**示例：**

```bash
# 在当前目录拉取更新（使用默认 upstream 和当前分支）
zxtool git pull

# 指定项目路径拉取更新
zxtool git pull /path/to/my-project

# 从指定远程仓库拉取
zxtool git pull --remote origin

# 从指定远程仓库的指定分支拉取
zxtool git pull --remote upstream --branch main

# 指定项目路径和远程仓库
zxtool git pull /path/to/my-project --remote origin --branch develop
```

**输出示例：**

```
Updating abc1234..def5678
Fast-forward
 src/module.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

**常见错误：**

- `错误: 未找到 Git 仓库` — 指定目录不是 Git 仓库
- `错误: 未找到 git 命令` — 系统未安装 git
- `错误: git pull 超时（120 秒）` — 网络超时

## 0x05. 全局配置文件格式

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

## 0x06. 注意事项

- 项目必须是 Git 仓库（包含 `.git` 目录）
- 如果项目已配置完整的 user.name 和 user.email，`fill` 命令会显示现有配置并退出
- 交互式输入时，按 `Ctrl+C` 可取消操作
- 配置文件路径支持绝对路径和相对路径
- `git pull` 命令需要在系统 PATH 中安装 git
- `git pull` 默认超时时间为 120 秒
