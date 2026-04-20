# Let's Encrypt ACME v2 证书管理

基于 [acme.sh](https://github.com/acmesh-official/acme.sh) 封装的 Let's Encrypt 证书管理模块。

## 0x01. 特点

1. **基于 acme.sh** - 使用业界最流行的 shell 脚本方案，稳定可靠
2. **自动安装** - 首次使用时自动检查并安装 acme.sh
3. **支持泛域名证书**（`*.example.com`），通过 DNS-01 验证
4. **支持普通域名证书**，通过 HTTP-01 验证
5. **多 DNS 提供商** - Cloudflare、阿里云、手动验证
6. **自动续签** - 支持 cron 定时任务自动续签
7. **配置驱动** - 支持 zxtool.toml 配置文件批量管理

> **注意**: acme.sh 需要在支持 POSIX shell 的环境运行（Linux、macOS、WSL、Git Bash）。纯 Windows CMD/PowerShell 环境不支持。

## 0x02. 系统要求

- Linux / macOS / WSL / Git Bash（不支持原生 Windows CMD）
- `curl` 或 `wget`（用于安装 acme.sh）
- `openssl`（用于证书信息解析）

## 0x03. 验证方式对比

| 特性 | DNS-01 | HTTP-01 |
|------|--------|---------|
| 泛域名证书 | ✅ 支持 | ❌ 不支持 |
| 普通域名证书 | ✅ 支持 | ✅ 支持 |
| 无需 DNS 操作 | ❌ 需要添加 TXT 记录 | ✅ 无需 DNS 操作 |
| 无需 Web 服务器 | ✅ 不需要 | 视提供商而定 |
| 适用场景 | 泛域名、无公网 IP | 普通二级域名、有 Web 服务器 |
| 验证原理 | 在 DNS 中添加 TXT 记录 | 在 Web 服务器放置验证文件 |

## 0x04. 命令格式

```bash
zxtool le <子命令> [选项]
```

| 子命令 | 说明 |
|--------|------|
| `issue` | 签发新证书 |
| `renew` | 续签即将到期的证书 |
| `batch` | 根据配置文件批量签发/续签证书 |
| `status` | 查看证书状态 |
| `revoke` | 吊销证书 |
| `init` | 初始化输出目录 |
| `cron` | 管理自动续签定时任务 |

## 0x05. 首次使用

首次使用 `le` 模块时，会自动检查 acme.sh 是否已安装：

```bash
# 检查并自动安装 acme.sh
zxtool le init
```

输出示例：
```
[INFO] acme.sh 未安装，正在安装...
[INFO] 开始安装 acme.sh...
[OK] acme.sh 安装成功 (版本: 3.0.0)
[OK] 证书目录已初始化: out_le
```

如果已安装，会显示版本号：
```
[INFO] acme.sh 已安装 (版本: 3.0.0)
[OK] 证书目录已初始化: out_le
```

## 0x06. 签发证书

### 6.1 手动 DNS 验证（测试环境）

适用于不支持 API 的 DNS 提供商，或一次性使用场景。

```bash
# 测试环境签发（默认 staging，不会触及生产速率限制）
zxtool le issue -d example.com "*.example.com"
```

acme.sh 会自动处理 DNS 验证流程。对于手动模式，它会暂停并提示你如何添加 TXT 记录。

### 6.2 Cloudflare 自动 DNS

通过 Cloudflare API 自动管理 DNS 记录，无需手动操作。

```bash
zxtool le issue \
  -d example.com "*.example.com" \
  --provider cloudflare \
  --provider-config '{"api_token":"你的API_TOKEN","zone_id":"你的ZONE_ID"}' \
  --production \
  --email admin@example.com
```

**获取 Cloudflare API Token：**
1. 登录 Cloudflare → My Profile → API Tokens
2. 创建 Token，使用 "Edit zone DNS" 模板
3. 复制 Token 和 Zone ID（在域名 Overview 页面底部）

### 6.3 阿里云 DNS 自动签发

通过阿里云云解析 DNS API 自动管理 DNS 记录。

```bash
zxtool le issue \
  -d example.com "*.example.com" \
  --provider aliyun \
  --provider-config '{"access_key_id":"你的AK","access_key_secret":"你的SK"}' \
  --production \
  --email admin@example.com
```

### 6.4 HTTP-01 验证 - Webroot 方式

将验证文件写入已运行的 Web 服务器根目录。

```bash
zxtool le issue \
  -d example.com \
  --challenge http-01 \
  --provider webroot \
  --provider-config '{"webroot":"/var/www/html"}' \
  --production \
  --email admin@example.com
```

### 6.5 HTTP-01 验证 - Standalone 方式

启动临时 HTTP 服务器监听 80 端口。

```bash
zxtool le issue \
  -d example.com \
  --challenge http-01 \
  --provider standalone \
  --production \
  --email admin@example.com
```

### 签发参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-d, --domain` | 域名列表（必需） | - |
| `--challenge` | 验证方式：`dns-01` 或 `http-01` | `dns-01` |
| `--provider` | 验证提供商 | DNS-01: `manual`；HTTP-01: `standalone` |
| `--provider-config` | 提供商配置（JSON 字符串） | - |
| `--production` | 使用生产环境 | 测试环境 |
| `--email` | 联系邮箱 | 空 |
| `--key-size` | RSA 密钥长度：`2048` 或 `4096` | `2048` |
| `--output` | 输出目录 | `./out_le` |

**提供商与验证方式的对应关系：**

| 验证方式 | 提供商 | provider-config |
|----------|--------|-----------------|
| `dns-01` | `manual` | 无需配置 |
| `dns-01` | `cloudflare` | `{"api_token":"...", "zone_id":"..."}` |
| `dns-01` | `aliyun` | `{"access_key_id":"...", "access_key_secret":"..."}` |
| `http-01` | `webroot` | `{"webroot":"/var/www/html"}` |
| `http-01` | `standalone` | 无需配置 |

## 0x07. 配置驱动的批量签发

### 7.1 配置文件示例

**DNS-01 验证配置（泛域名）：**

```toml
# Let's Encrypt 全局配置
[letsencrypt]
provider = "cloudflare"
challenge_type = "dns-01"
output_dir = "/etc/letsencrypt"
staging = false
email = "admin@example.com"

[letsencrypt.provider_config]
api_token = "your_cloudflare_api_token"
zone_id = "your_cloudflare_zone_id"

# 项目配置（domain 字段关联域名证书）
[[projects]]
project_dir = "/var/www/myblog"
domain = "myblog.example.com"
output_dir = "/var/www/myblog/site"

[[projects]]
project_dir = "/var/www/api"
domain = "*.api.example.com"
```

**HTTP-01 验证配置（普通域名）：**

```toml
# Let's Encrypt 全局配置 - HTTP-01 验证
[letsencrypt]
provider = "webroot"
challenge_type = "http-01"
output_dir = "/etc/letsencrypt"
staging = false
email = "admin@example.com"

[letsencrypt.provider_config]
webroot = "/var/www/html"

# 项目配置
[[projects]]
project_dir = "/var/www/myblog"
domain = "myblog.example.com"
```

### 7.2 批量签发证书

```bash
# 使用默认配置文件 (~/.config/zxtool.toml) 批量签发
zxtool le batch

# 仅预览计划，不实际执行
zxtool le batch --dry-run

# 指定配置文件路径
zxtool le batch --le-config /path/to/zxtool.toml
```

### 7.3 自动续签

```bash
# 检查续签状态（dry-run）
zxtool le renew --dry-run

# 实际续签即将到期的证书
zxtool le renew
```

## 0x08. 查看证书状态

```bash
zxtool le status
```

输出示例：

```
域名                             状态       剩余天数   过期日期
---------------------------------------------------------------------
example.com                    有效         75       2026-06-15
myblog.example.com            即将过期      12       2026-04-20
```

## 0x09. 吊销证书

```bash
zxtool le revoke -d example.com
```

## 0x0a. 初始化输出目录

```bash
# 使用 zxtool.toml 中配置的 output_dir（默认 out_le）
zxtool le init

# 指定自定义输出目录
zxtool le init --output /etc/letsencrypt
```

## 0x0b. 定时任务管理

### 11.1 安装自动续签定时任务

```bash
zxtool le cron install
```

这会安装一个系统 cron 任务，acme.sh 会自动每天检查并续签即将到期的证书。

### 11.2 卸载定时任务

```bash
zxtool le cron uninstall
```

## 0x0c. 生成的证书文件

```
out_le/
├── cert_example_com/
│   ├── example.com.crt           # 服务器证书
│   ├── example.com.key.pem       # 证书私钥
│   ├── example.com.ca.crt        # 中间证书链
│   └── example.com.fullchain.crt # 完整证书链（用于 nginx）
└── renew_state.json               # 续签状态跟踪
```

## 0x0d. nginx 配置示例

```nginx
server {
    listen 443 ssl;
    server_name example.com *.example.com;

    ssl_certificate     /path/to/out_le/cert_example_com/example.com.fullchain.crt;
    ssl_certificate_key /path/to/out_le/cert_example_com/example.com.key.pem;

    # 推荐的安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... 其他配置
}
```

## 0x0e. 常见问题

### Q1: Windows 原生环境支持吗？

不支持。acme.sh 是 shell 脚本，需要 POSIX 环境。Windows 用户请使用 WSL 或 Git Bash。

### Q2: 如何查看 acme.sh 版本？

```bash
zxtool le init
```

输出中会显示当前安装的 acme.sh 版本。

### Q3: acme.sh 安装在哪个目录？

默认安装在 `~/.acme.sh/` 目录下。证书也存储在该目录中。

### Q4: 如何切换到生产环境？

添加 `--production` 参数即可：

```bash
zxtool le issue -d example.com --production
```

### Q5: 测试环境和生产环境有什么区别？

- **测试环境（staging）**：证书不被浏览器信任，用于调试
- **生产环境（production）**：浏览器信任的正式证书，有速率限制

### Q6: 为什么使用 acme.sh 而不是 Python acme 库？

acme.sh 的优势：
- 更成熟稳定，社区广泛使用
- 支持更多 DNS 提供商
- 自动续签机制完善
- 跨平台兼容性好（在支持的 shell 环境下）

### Q7: 续签失败怎么办？

1. 检查 DNS 提供商配置是否正确
2. 检查 acme.sh 是否正常运行：`zxtool le init`
3. 查看详细错误日志：检查 `~/.acme.sh/acme.sh.log`
4. 手动强制续签：`zxtool le renew --force`

### Q8: 如何修改证书默认输出目录？

在 `zxtool.toml` 配置文件的 `[letsencrypt]` 节点中设置 `output_dir`：

```toml
[letsencrypt]
output_dir = "/etc/letsencrypt"
```

### Q9: 证书有效期是多长？

Let's Encrypt 证书有效期为 90 天。建议在 30 天内续签。

### Q10: 如何配置自定义 DNS 解析等待时间？

acme.sh 默认等待 120 秒让 DNS 记录传播。如需调整，可直接使用 acme.sh 命令：

```bash
~/.acme.sh/acme.sh --issue -d example.com --dns dns_cf --dnssleep 60
```
