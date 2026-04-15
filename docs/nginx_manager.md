# Nginx 站点配置管理

基于 zxtool.toml 配置文件，自动生成和管理 Nginx 站点配置，支持静态站点发布和 HTTPS 证书集成。

## 0x01. 功能特性

- **检查 Nginx**: 检测 Nginx 安装状态、版本、配置目录
- **生成配置**: 根据 zxtool.toml 中的项目配置批量生成 Nginx 站点配置
- **启用/禁用站点**: 通过符号链接管理站点启用状态（Debian/Ubuntu 模式）
- **重载配置**: 一键重载 Nginx 配置
- **HTTPS 支持**: 自动检测 Let's Encrypt 证书，生成 HTTPS 配置
- **独立配置文件**: 生成的配置文件独立存放，不修改 Nginx 默认配置

## 0x02. 快速开始

### 1. 检查 Nginx 状态

```bash
zxtool nginx check
```

**输出示例：**

```
Nginx 版本:      nginx/1.24.0
Nginx 路径:      /usr/sbin/nginx
配置目录:        /etc/nginx
sites-available: /etc/nginx/sites-available
sites-enabled:   /etc/nginx/sites-enabled
conf.d:          /etc/nginx/conf.d
```

### 2. 生成站点配置

根据 `~/.config/zxtool.toml` 中配置了 `domain` 和 `output_dir` 的项目自动生成 Nginx 配置：

```bash
# 使用默认配置文件生成
zxtool nginx generate

# 指定配置文件
zxtool nginx generate --config /path/to/zxtool.toml

# 指定输出目录
zxtool nginx generate -o /etc/nginx/sites-available

# 仅预览计划，不实际写入
zxtool nginx generate --dry-run
```

### 3. 启用/禁用站点

```bash
# 启用站点（创建符号链接到 sites-enabled）
zxtool nginx enable example.com

# 禁用站点（移除符号链接）
zxtool nginx disable example.com
```

> 仅适用于 Debian/Ubuntu 系统的 sites-available/sites-enabled 模式。

### 3. 重载 Nginx

```bash
zxtool nginx reload
```

## 0x03. 配置文件格式

`zxtool.toml` 中的项目配置需要指定 `domain` 和 `output_dir` 字段，可以通过 `[nginx]` 全局配置和项目级 `listen_port` 字段自定义端口：

```toml
# Nginx 全局配置
[nginx]
http_port = 80
https_port = 443

# Let's Encrypt 证书配置（用于 HTTPS）
[letsencrypt]
provider = "cloudflare"
output_dir = "/etc/letsencrypt"
staging = false

[letsencrypt.provider_config]
api_token = "your_api_token"
zone_id = "your_zone_id"

# 项目配置
[[projects]]
project_dir = "/var/www/myblog"
domain = "myblog.example.com"
output_dir = "/var/www/myblog/site"

[[projects]]
project_dir = "/var/www/docs"
domain = "*.docs.example.com"

# 项目级别端口覆盖（此站点监听 8080 端口）
[[projects]]
project_dir = "/var/www/dev-site"
domain = "dev.example.com"
listen_port = 8080
```

**字段说明：**

| 字段 | 说明 |
|------|------|
| `domain` | 站点域名，支持泛域名（如 `*.example.com`） |
| `output_dir` | MkDocs 构建输出目录，将作为 Nginx 的 root 路径 |
| `project_dir` | 项目目录路径 |
| `listen_port` | （可选）项目级 Nginx 监听端口，覆盖全局 `http_port` |

**Nginx 全局配置字段：**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `http_port` | integer | 80 | Nginx HTTP 监听端口 |
| `https_port` | integer | 443 | Nginx HTTPS 监听端口 |

## 0x04. 生成的配置内容

### HTTPS 配置（有 SSL 证书时）

当 Let's Encrypt 证书存在时，自动生成包含以下内容的配置：

- HTTP → HTTPS 301 重定向
- 443 端口 SSL/TLS 配置
- Let's Encrypt ACME 验证路径
- 安全头部（HSTS、X-Frame-Options 等）
- 静态资源缓存策略
- TLS 1.2/1.3 协议支持

### HTTP 配置（无 SSL 证书时）

当 SSL 证书不存在时，生成仅 HTTP 的配置：

- 80 端口静态站点服务
- ACME 验证路径（便于后续申请证书）
- 静态资源缓存策略

## 0x05. 配置文件存放位置

生成的配置文件按以下优先级存放：

1. **指定输出目录**：`zxtool nginx generate -o /path/to/dir`
2. **自动检测**：`/etc/nginx/sites-available/`（Debian/Ubuntu）
3. **回退**：`/etc/nginx/conf.d/`（RHEL/CentOS）
4. **最终回退**：当前目录

文件名基于域名生成：
- `example.com` → `example.com.conf`
- `*.example.com` → `wildcard.example.com.conf`

## 0x06. 注意事项

- 生成和启用站点配置可能需要 sudo 权限
- `enable` 和 `disable` 命令仅适用于 Debian/Ubuntu 的 sites-available/sites-enabled 模式
- 修改 Nginx 配置后需要运行 `zxtool nginx reload` 使配置生效
- 通配符域名（如 `*.example.com`）需要 DNS 解析支持
- 生成的配置文件头部包含注释标记，便于识别自动生成的配置