# Let's Encrypt ACME v2 证书管理

参考 [acme.sh](https://github.com/acmesh-official/acme.sh) 实现，通过 ACME v2 协议从 Let's Encrypt 获取免费证书。

## 特点

1. 支持泛域名证书（`*.example.com`），通过 DNS-01 验证
2. 支持多域名和泛二级域名混合签发
3. 可插拔 DNS 提供商：手动 / Cloudflare / 阿里云
4. 证书到期自动检测和续签
5. 支持定期执行（cron / systemd timer）

> **生产环境注意**：Let's Encrypt 有速率限制。开发测试时默认使用测试环境（staging），确认无误后再加 `--production` 参数。

## 系统要求

- Linux / macOS / Windows
- 已安装 `openssl`
- Python 依赖：`acme`, `cryptography`, `requests`, `pyOpenSSL`, `josepy`

```bash
uv add acme cryptography requests pyOpenSSL josepy
```

## 1. 签发证书

### 1.1 手动 DNS 验证（测试环境）

适用于不支持 API 的 DNS 提供商，或一次性使用场景。

```bash
# 测试环境签发（默认 staging，不会触及生产速率限制）
zxtool --le issue -d example.com "*.example.com"
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

### 1.2 Cloudflare 自动 DNS

通过 Cloudflare API 自动管理 DNS 记录，无需手动操作。

```bash
zxtool --le issue \
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

### 1.3 阿里云 DNS 自动签发

通过阿里云云解析 DNS API 自动管理 DNS 记录。

```bash
zxtool --le issue \
  -d example.com "*.example.com" \
  --provider aliyun \
  --provider-config '{"access_key_id":"你的AK","access_key_secret":"你的SK"}' \
  --production \
  --email admin@example.com
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-d, --domain` | 域名列表（必需） | - |
| `--provider` | DNS 提供商：`manual` / `cloudflare` / `aliyun` | `manual` |
| `--provider-config` | 提供商配置（JSON 字符串） | - |
| `--production` | 使用生产环境（不加则用测试环境） | 测试环境 |
| `--email` | 联系邮箱，接收到期通知 | 空 |
| `--key-size` | RSA 密钥长度：`2048` 或 `4096` | `2048` |
| `--output` | 输出目录 | `./out_le` |

## 2. 查看证书状态

```bash
zxtool --le status
```

输出示例：

```
域名                             状态         剩余天数     过期日期       环境
---------------------------------------------------------------------------
example.com                    有效         75         2026-06-15   staging
myapp.dev                      即将过期      12         2026-04-20   production
```

## 3. 续签证书

### 3.1 检查续签（dry-run）

仅检查哪些证书需要续签，不执行实际操作。

```bash
zxtool --le renew --dry-run
```

### 3.2 执行续签

自动续签 30 天内到期的证书。

```bash
# 手动续签（需要 DNS 提供商配置）
zxtool --le renew \
  --provider-config '{"api_token":"xxx","zone_id":"yyy"}'
```

### 3.3 定期自动续签

通过 cron 定时任务实现自动续签：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨 3 点检查并续签）
0 3 * * * cd /path/to/zxtoolbox && uv run zxtool --le renew --provider-config '{"api_token":"xxx","zone_id":"yyy"}' >> /var/log/le-renew.log 2>&1
```

或使用 systemd timer：

```ini
# /etc/systemd/system/le-renew.service
[Unit]
Description=Let's Encrypt Certificate Renewal

[Service]
Type=oneshot
ExecStart=/path/to/zxtoolbox/.venv/bin/zxtool --le renew --provider-config '{"api_token":"xxx","zone_id":"yyy"}'
WorkingDirectory=/path/to/zxtoolbox
```

```ini
# /etc/systemd/system/le-renew.timer
[Unit]
Description=Run LE renewal daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl enable --now le-renew.timer
```

## 4. 吊销证书

当私钥泄露或不再需要某个证书时，可以主动吊销。

```bash
zxtool --le revoke -d example.com
```

## 5. 初始化输出目录

```bash
zxtool --le init
```

## 生成的证书文件

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

## nginx 配置示例

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

## Let's Encrypt 限制

| 限制项 | 值 |
|--------|-----|
| 证书有效期 | 90 天 |
| 每域名每周签发次数 | 50 次 |
| 每 IP 每周新注册账户数 | 10 个 |
| 每证书最多域名数 | 100 个 |
| 泛域名验证方式 | 仅 DNS-01 |

## 常见问题

### Q1: 测试环境证书和正式证书有什么区别？

测试环境（staging）签发的证书不被浏览器信任，仅用于调试流程。确认 DNS 验证通过后，加 `--production` 参数获取正式证书。

### Q2: DNS-01 验证失败怎么办？

- 检查 TXT 记录是否正确（记录名、记录值）
- 等待更长时间让 DNS 传播（可能需要 5-10 分钟）
- 使用 `nslookup -type=TXT _acme-challenge.example.com 8.8.8.8` 验证记录是否生效

### Q3: 续签时提示 "DNS provider requires api_token"？

续签时需要重新提供 DNS 提供商配置。确保在 cron 或 systemd timer 中传入 `--provider-config` 参数。

### Q4: 如何切换测试环境和生产环境？

不加 `--production` 默认为测试环境，加上则为生产环境。账户密钥是分开的，互不影响。
