# Let's Encrypt ACME v2 证书管理

参考 [acme.sh](https://github.com/acmesh-official/acme.sh) 实现，通过 ACME v2 协议从 Let's Encrypt 获取免费证书。

## 0x01. 特点

1. 支持泛域名证书（`*.example.com`），通过 DNS-01 验证
2. 支持普通二级域名证书，通过 HTTP-01 验证（无需 DNS 操作）
3. 支持多域名和泛二级域名混合签发
4. 可插拔验证提供商：
   - DNS-01：手动 / Cloudflare / 阿里云
   - HTTP-01：webroot / standalone
5. 证书到期自动检测和续签
6. 支持配置文件驱动的批量签发和续签
7. 支持定期执行（cron / systemd timer）

> **生产环境注意**：Let's Encrypt 有速率限制。开发测试时默认使用测试环境（staging），确认无误后再加 `--production` 参数。

## 0x02. 验证方式对比

| 特性 | DNS-01 | HTTP-01 |
|------|--------|---------|
| 泛域名证书 | ✅ 支持 | ❌ 不支持 |
| 普通域名证书 | ✅ 支持 | ✅ 支持 |
| 无需 DNS 操作 | ❌ 需要添加 TXT 记录 | ✅ 无需 DNS 操作 |
| 无需 Web 服务器 | ✅ 不需要 | 视提供商而定 |
| 适用场景 | 泛域名、无公网 IP | 普通二级域名、有 Web 服务器 |
| 验证原理 | 在 DNS 中添加 TXT 记录 | 在 Web 服务器放置验证文件 |

### DNS-01 验证

在 DNS 中添加 `_acme-challenge.<domain>` 的 TXT 记录，Let's Encrypt 通过 DNS 查询验证域名所有权。这是唯一支持泛域名证书的验证方式。

### HTTP-01 验证

在 Web 服务器的 `/.well-known/acme-challenge/<token>` 路径下放置验证文件，Let's Encrypt 通过 HTTP 请求验证域名所有权。需要 80 端口可访问。

**HTTP-01 提供商：**

| 提供商 | 说明 | 适用场景 |
|--------|------|----------|
| `webroot` | 将验证文件写入 Web 服务器根目录 | 已有 Nginx/Apache 等 Web 服务器运行 |
| `standalone` | 启动临时 HTTP 服务器监听 80 端口 | 无 Web 服务器或可临时占用 80 端口 |

## 0x03. 系统要求

- Linux / macOS / Windows
- 已安装 `openssl`
- Python 依赖：`acme`, `cryptography`, `requests`, `pyOpenSSL`, `josepy`

```bash
uv add acme cryptography requests pyOpenSSL josepy
```

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

## 0x05. 签发证书

### 5.1 手动 DNS 验证（测试环境）

适用于不支持 API 的 DNS 提供商，或一次性使用场景。

```bash
# 测试环境签发（默认 staging，不会触及生产速率限制）
zxtool le issue -d example.com "*.example.com"
```

运行后会提示你手动添加 DNS TXT 记录：

```
============================================================
  DNS-01 验证 - 请手动添加 DNS TXT 记录
============================================================
  记录类型:  TXT
  记录名称:  _acme-challenge.example.com
  记录值:    xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

  请在你的 DNS 控制面板中添加上述 TXT 记录，
  并等待 DNS 生效（通常需要 1-5 分钟）。
============================================================

  添加完成后按 Enter 继续...
```

### 5.2 Cloudflare 自动 DNS

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

### 5.3 阿里云 DNS 自动签发

通过阿里云云解析 DNS API 自动管理 DNS 记录。

```bash
zxtool le issue \
  -d example.com "*.example.com" \
  --provider aliyun \
  --provider-config '{"access_key_id":"你的AK","access_key_secret":"你的SK"}' \
  --production \
  --email admin@example.com
```

### 5.4 HTTP-01 验证 - Webroot 方式

将验证文件写入已运行的 Web 服务器根目录。适用于已有 Nginx/Apache 等 Web 服务器运行的场景。

```bash
zxtool le issue \
  -d example.com \
  --challenge http-01 \
  --provider webroot \
  --provider-config '{"webroot":"/var/www/html"}' \
  --production \
  --email admin@example.com
```

**Nginx 配置提示：** 确保 Nginx 配置了 `.well-known` 路径的访问权限：

```nginx
server {
    listen 80;
    server_name example.com;

    # 允许 ACME 验证文件访问
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}
```

### 5.5 HTTP-01 验证 - Standalone 方式

启动一个临时 HTTP 服务器监听 80 端口，自动响应 ACME 验证请求。适用于没有 Web 服务器的场景，需要 80 端口可用。

```bash
zxtool le issue \
  -d example.com \
  --challenge http-01 \
  --provider standalone \
  --production \
  --email admin@example.com
```

> **注意：** Standalone 模式需要 80 端口未被占用。如果 80 端口被占用，可通过 `--provider-config` 指定其他选项（不建议修改端口，Let's Encrypt 仅验证 80 端口）。

### 签发参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-d, --domain` | 域名列表（必需） | - |
| `--challenge` | 验证方式：`dns-01` 或 `http-01` | `dns-01` |
| `--provider` | 验证提供商 | DNS-01: `manual`；HTTP-01: `standalone` |
| `--provider-config` | 提供商配置（JSON 字符串） | - |
| `--production` | 使用生产环境（不加则用测试环境） | 测试环境 |
| `--email` | 联系邮箱，接收到期通知 | 空 |
| `--key-size` | RSA 密钥长度：`2048` 或 `4096` | `2048` |
| `--output` | 输出目录 | `zxtool.toml` 中的 `output_dir`，默认 `./out_le` |

**提供商与验证方式的对应关系：**

| 验证方式 | 提供商 | provider-config |
|----------|--------|-----------------|
| `dns-01` | `manual` | 无需配置 |
| `dns-01` | `cloudflare` | `{"api_token":"...", "zone_id":"..."}` |
| `dns-01` | `aliyun` | `{"access_key_id":"...", "access_key_secret":"..."}` |
| `http-01` | `webroot` | `{"webroot":"/var/www/html"}` |
| `http-01` | `standalone` | 可选 `{"port":80, "bind_addr":"0.0.0.0"}` |

## 0x06. 配置驱动的批量签发

通过 `zxtool.toml` 配置文件，实现域名证书的自动签发和续签。

### 6.1 配置文件示例

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

**HTTP-01 Standalone 配置（无 Web 服务器）：**

```toml
[letsencrypt]
provider = "standalone"
challenge_type = "http-01"
output_dir = "/etc/letsencrypt"
staging = false
email = "admin@example.com"
```

> **泛域名说明**: 当 `domain = "*.example.com"` 时，无论 `challenge_type` 配置如何，都会自动使用 DNS-01 验证，因为 HTTP-01 不支持泛域名证书。

### 6.2 批量签发证书

```bash
# 使用默认配置文件 (~/.config/zxtool.toml) 批量签发
zxtool le batch

# 仅预览计划，不实际执行
zxtool le batch --dry-run

# 指定配置文件路径
zxtool le batch --le-config /path/to/zxtool.toml
```

**输出示例：**

```
============================================================
  Let's Encrypt 批量证书签发
  共 2 个项目需要签发证书
============================================================

--- [1/2] myblog.example.com ---
  域名列表: ['myblog.example.com']
  验证方式: HTTP-01
  提供商: webroot
  输出目录: /etc/letsencrypt
  环境: 生产
  邮箱: admin@example.com

步骤 1/4: 注册 ACME 账户...
步骤 2/4: 创建订单并提交 CSR...
步骤 3/4: 完成 HTTP-01 验证...
步骤 4/4: 保存证书文件...
  证书签发成功!

--- [2/2] *.api.example.com ---
  域名列表: ['*.api.example.com', 'api.example.com']
  验证方式: DNS-01
  提供商: cloudflare
  ...

============================================================
  批量签发完成: 2/2 成功
============================================================
  [OK] myblog.example.com
  [OK] *.api.example.com
```

### 6.3 自动续签

配置了域名的项目，可通过 cron 或 systemd timer 实现自动续签：

```bash
# 定期检查并续签（每天凌晨 3 点）
0 3 * * * cd /path/to/project && uv run zxtool le batch >> /var/log/le-batch.log 2>&1
```

或使用 systemd timer：

```ini
# /etc/systemd/system/le-batch.service
[Unit]
Description=Let's Encrypt Batch Certificate Management

[Service]
Type=oneshot
ExecStart=/path/to/zxtool le batch
WorkingDirectory=/path/to/project
```

```ini
# /etc/systemd/system/le-batch.timer
[Unit]
Description=Run LE batch daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl enable --now le-batch.timer
```

## 0x07. 查看证书状态

```bash
zxtool le status
```

输出示例：

```
域名                             状态         剩余天数     过期日期       环境
---------------------------------------------------------------------------
example.com                    有效         75         2026-06-15   staging
myblog.example.com            即将过期      12         2026-04-20   production
```

## 0x08. 续签证书

### 8.1 检查续签（dry-run）

仅检查哪些证书需要续签，不执行实际操作。

```bash
zxtool le renew --dry-run
```

### 8.2 执行续签

自动续签 30 天内到期的证书。

```bash
# 手动续签（需要提供商配置）
zxtool le renew \
  --provider-config '{"api_token":"xxx","zone_id":"yyy"}'
```

### 8.3 定期自动续签

通过 cron 定时任务实现自动续签：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨 3 点检查并续签）
0 3 * * * cd /path/to/zxtoolbox && uv run zxtool le renew --provider-config '{"api_token":"xxx","zone_id":"yyy"}' >> /var/log/le-renew.log 2>&1
```

## 0x09. 吊销证书

当私钥泄露或不再需要某个证书时，可以主动吊销。

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

> **注意**: 如果不指定 `--output`，将自动从 `zxtool.toml` 配置文件的 `[letsencrypt]` 节点读取 `output_dir`。如果配置文件不存在或未配置 `output_dir`，则默认使用 `out_le`。

## 0x0b. 生成的证书文件

```
out_le/
├── account.key                  # ACME 账户私钥
├── account.json                 # 账户注册信息
├── renew_state.json             # 续签状态跟踪
└── cert_example_com/
    ├── example.com.crt          # 服务器证书
    ├── example.com.chain.crt    # 中间证书链
    ├── example.com.bundle.crt   # 完整证书链
    ├── example.com.fullchain.crt # 服务器 + 中间（用于 nginx）
    └── example.com.key.pem      # 证书私钥
```

## 0x0c. nginx 配置示例

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

## 0x0d. Let's Encrypt 限制

| 限制项 | 值 |
|--------|-----|
| 证书有效期 | 90 天 |
| 每域名每周签发次数 | 50 次 |
| 每 IP 每周新注册账户数 | 10 个 |
| 每证书最多域名数 | 100 个 |
| 泛域名验证方式 | 仅 DNS-01 |
| HTTP-01 验证端口 | 仅 80 |

## 0x0e. 常见问题

### Q1: 测试环境证书和正式证书有什么区别？

测试环境（staging）签发的证书不被浏览器信任，仅用于调试流程。确认验证通过后，加 `--production` 参数获取正式证书。

### Q2: DNS-01 验证失败怎么办？

- 检查 TXT 记录是否正确（记录名、记录值）
- 等待更长时间让 DNS 传播（可能需要 5-10 分钟）
- 使用 `nslookup -type=TXT _acme-challenge.example.com 8.8.8.8` 验证记录是否生效

### Q3: HTTP-01 验证失败怎么办？

- 确保域名解析到正确的服务器 IP
- 确保 80 端口可从外部访问（防火墙、安全组等）
- Webroot 模式：确保 `.well-known/acme-challenge/` 目录可写，且 Nginx/Apache 配置了该路径的访问权限
- Webroot 模式：确保 `--provider-config` 中的 `webroot` 路径与 Nginx 的 `root` 指令一致（例如 Nginx 配置 `root /var/www/html;`，则 webroot 也应为 `/var/www/html`）
- Standalone 模式：确保 80 端口未被其他服务占用
- 如 Nginx 错误日志中出现 `No such file or directory`，请检查 webroot 路径是否正确，以及 Nginx 配置中 `server_name` 是否包含待验证域名

### Q4: 什么时候用 DNS-01，什么时候用 HTTP-01？

| 场景 | 推荐方式 | 原因 |
|------|----------|------|
| 泛域名证书（`*.example.com`） | DNS-01 | HTTP-01 不支持泛域名 |
| 普通二级域名（有 Web 服务器） | HTTP-01 | 无需 DNS 操作，更简单快捷 |
| 普通二级域名（无 Web 服务器） | HTTP-01 standalone | 临时启动服务器即可 |
| 内网域名（无公网 IP） | DNS-01 | HTTP-01 需要公网可访问 |
| 多个域名批量管理 | DNS-01（有 API 时）| 自动化程度更高 |

### Q5: 续签时提示 "DNS provider requires api_token"？

续签时需要重新提供验证提供商配置。确保在 cron 或 systemd timer 中传入 `--provider-config` 参数。

### Q6: 如何切换测试环境和生产环境？

不加 `--production` 默认为测试环境，加上则为生产环境。账户密钥是分开的，互不影响。

### Q7: 如何修改证书默认输出目录？

在 `zxtool.toml` 配置文件的 `[letsencrypt]` 节点中设置 `output_dir`：

```toml
[letsencrypt]
output_dir = "/etc/letsencrypt"
```

所有 `le` 子命令（`init`、`issue`、`renew`、`status`、`revoke`）在不指定 `--output` 时将自动使用此配置。如果未配置，默认使用 `out_le`。

### Q8: 批量签发时域名配置在哪里？

在 `zxtool.toml` 配置文件的 `[[projects]]` 节点中使用 `domain` 字段指定域名，`[letsencrypt]` 节点配置全局验证提供商信息。运行 `zxtool le batch` 即可自动读取配置并签发证书。