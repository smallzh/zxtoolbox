# 配置文件管理

管理 `zxtool` 的全局配置文件 `~/.config/zxtool.toml`，支持 MkDocs 项目、Let's Encrypt 证书和 Git 仓库用户配置。

## 0x01. 功能特性

- **交互式初始化**: 通过向导式提示，轻松生成配置文件
- **Let's Encrypt 配置**: 全局配置 DNS 提供商、证书输出目录等
- **MkDocs 配置**: 配置多个 MkDocs 项目的批量构建参数
- **域名绑定**: 在项目中配置域名，支持 Let's Encrypt 自动证书签发
- **Git 配置**: 配置默认的 git user.name 和 user.email
- **配置查看**: 快速查看当前配置文件内容
- **强制覆盖**: 支持 `--force` 覆盖已有配置

## 0x02. 快速开始

### 1. 初始化配置文件

```bash
zxtool config init
```

运行后会启动交互式向导，依次询问：
1. Let's Encrypt 证书配置（DNS 提供商、输出目录、邮箱等）
2. 项目配置（路径、域名等）
3. Git 用户名和邮箱

**示例交互：**

```
==================================================
  zxtool.toml 配置初始化向导
==================================================

配置文件路径: /home/user/.config/zxtool.toml

--- Let's Encrypt 证书配置 ---
配置 Let's Encrypt? (y/N): y
  DNS 提供商 [manual/cloudflare/aliyun, 默认 manual]: cloudflare
  证书输出目录 [默认 out_le]: /etc/letsencrypt
  联系邮箱: admin@example.com
  使用测试环境? [Y/n]: n
  Cloudflare API Token: your_api_token
  Cloudflare Zone ID: your_zone_id
  [OK] Let's Encrypt 配置已添加

--- 项目配置 ---
添加项目（可配置 MkDocs 构建和域名，留空跳过）

项目路径 [1]: /var/www/myblog
  MkDocs 输出目录 [默认 site]: /var/www/myblog/site
  项目域名（用于 Let's Encrypt 证书，如 example.com）: myblog.example.com
  [OK] 已添加项目: /var/www/myblog (域名: myblog.example.com)

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

Let's Encrypt:
  DNS 提供商: cloudflare
  输出目录:   /etc/letsencrypt
  环境:       生产
  联系邮箱:   admin@example.com

项目: 1 个
  - /var/www/myblog (域名: myblog.example.com)

Git 用户: 1 个
  - John Doe <john@example.com>

确认生成配置文件? (Y/n): Y
[OK] 配置文件已创建: /home/user/.config/zxtool.toml

[OK] 配置初始化完成!

查看配置: cat /home/user/.config/zxtool.toml

使用方式:
  zxtool mkdocs batch              # 批量构建 MkDocs
  zxtool git config fill           # 填充 Git user 配置
  zxtool le batch                   # 根据配置批量申请/续签证书
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
# 用法:
#   zxtool mkdocs batch          # 批量构建 MkDocs 项目
#   zxtool git config fill       # 填充 Git 仓库 user 配置
#   zxtool le batch               # 根据配置批量申请/续签证书

[letsencrypt]
provider = "cloudflare"
...
```

### 4. 指定配置文件路径

```bash
# 初始化到自定义路径
zxtool config init --path ./my-config.toml

# 查看自定义配置文件
zxtool config show --path ./my-config.toml
```

## 0x03. 配置文件格式

`~/.config/zxtool.toml` 使用 TOML 格式，支持以下配置节：

### 完整示例

```toml
# zxtool 全局配置文件
# 路径: ~/.config/zxtool.toml
#
# 用法:
#   zxtool mkdocs batch          # 批量构建 MkDocs 项目
#   zxtool git config fill       # 填充 Git 仓库 user 配置
#   zxtool le batch               # 根据配置批量申请/续签证书

# ============================================
# Let's Encrypt 证书配置
# ============================================

[letsencrypt]
provider = "cloudflare"
output_dir = "/etc/letsencrypt"
staging = false
email = "admin@example.com"

[letsencrypt.provider_config]
api_token = "your_cloudflare_api_token"
zone_id = "your_cloudflare_zone_id"

# ============================================
# 项目配置
# ============================================

[[projects]]
project_dir = "/var/www/myblog"
domain = "myblog.example.com"
output_dir = "/var/www/myblog/site"

[[projects]]
project_dir = "/var/www/api-docs"
config_file = "custom-mkdocs.yml"
strict = true

[[projects]]
project_dir = "/var/www/main-site"
domain = "*.example.com"

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

#### Let's Encrypt 全局配置 (`[letsencrypt]`)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `provider` | string | ✅ | DNS 提供商：`manual` / `cloudflare` / `aliyun` |
| `output_dir` | string | ❌ | 证书输出目录（默认 `out_le`） |
| `staging` | boolean | ❌ | 是否使用测试环境（默认 `true`） |
| `email` | string | ❌ | 联系邮箱，用于接收证书到期通知 |

#### Let's Encrypt 提供商配置 (`[letsencrypt.provider_config]`)

Cloudflare 提供商：

| 字段 | 说明 |
|------|------|
| `api_token` | Cloudflare API Token（权限：Zone > DNS > Edit） |
| `zone_id` | Cloudflare Zone ID |

阿里云提供商：

| 字段 | 说明 |
|------|------|
| `access_key_id` | 阿里云 AccessKey ID |
| `access_key_secret` | 阿里云 AccessKey Secret |

#### 项目配置 (`[[projects]]`)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project_dir` | string | ✅ | 项目目录路径 |
| `output_dir` | string | ❌ | MkDocs 构建输出目录（默认使用 mkdocs.yml 配置） |
| `config_file` | string | ❌ | 自定义 MkDocs 配置文件（默认 mkdocs.yml） |
| `strict` | boolean | ❌ | 是否启用严格模式（默认 false） |
| `domain` | string | ❌ | 项目域名（用于 Let's Encrypt 证书自动签发，支持泛域名如 `*.example.com`） |

> **域名说明**: `domain` 字段为单个字符串。设置后，运行 `zxtool le batch` 可自动签发/续签该域名的 Let's Encrypt 证书。泛域名 `*.example.com` 会自动包含基础域名 `example.com`。

#### Git 用户配置 (`[[git.user]]`)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | git user.name |
| `email` | string | ✅ | git user.email |

## 0x04. 与其他命令的集成

### Let's Encrypt 批量证书签发

项目配置了 `domain` 字段后，可以直接运行：

```bash
# 根据配置文件中的项目域名，批量签发/续签证书
zxtool le batch

# 指定配置文件路径
zxtool le batch --le-config ./my-config.toml

# 仅查看计划，不实际执行
zxtool le batch --dry-run
```

每个项目域名的 DNS 提供商、邮箱、输出目录等设置自动从 `[letsencrypt]` 全局配置继承。

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

## 0x05. 注意事项

- 配置文件默认位于 `~/.config/zxtool.toml`
- 使用 `--force` 会覆盖已有配置，建议先备份
- TOML 格式对缩进敏感，手动编辑时注意保持格式正确
- `[[git.user]]` 目前使用第一个条目作为默认配置
- `[letsencrypt.provider_config]` 中的密钥信息请妥善保管，不要提交到版本控制系统