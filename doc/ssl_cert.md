# 自签泛域名 SSL 证书生成器

用于颁发泛域名证书，方便开发环境调试。

> **请勿用于生产环境**，生产环境请购买正式证书或使用 [Let's Encrypt](https://letsencrypt.org/) 申请免费证书。

## 优点

1. 可创建任意数量的网站证书，只需导入一次根证书
2. 减少重复的组织信息输入，创建证书时只需要输入域名
3. 泛域名证书可减少 nginx 配置，一个证书覆盖所有子域名
4. 支持 SAN（Subject Alternative Name），一个证书支持多个域名

## 系统要求

- Linux / macOS / Windows
- 系统已安装 `openssl`

## 1. 生成证书（完整流程）

功能描述：为指定域名签发泛域名 SSL 证书。首次运行时会自动生成 Root CA。

命令行: `zxtool --ssl --domain example.dev`

| 参数 | 说明 |
|------|------|
| `--ssl` | 激活 SSL 证书生成功能 |
| `-d, --domain` | 域名列表，如 `example.dev` `another.dev` |
| `--output` | 输出目录路径（可选，默认为 `./out`） |
| `--force` | 强制重新生成（覆盖已有证书） |

### 使用示例

```bash
# 为单个域名生成证书
zxtool --ssl --domain example.dev

# 为多个域名生成证书
zxtool --ssl --domain example.dev another.dev third.dev

# 指定输出目录
zxtool --ssl --domain example.dev --output /path/to/certs
```

### 输出示例

```
Issuing wildcard certificate for: example.dev, another.dev
  SAN: DNS:*.example.dev,DNS:example.dev,DNS:*.another.dev,DNS:another.dev

Certificates generated for: example.dev
  Domain dir: /path/to/out/example.dev

Files:
  example.dev.bundle.crt  — 完整证书链（可用于 nginx 配置）
  example.dev.crt         — 网站证书
  example.dev.key.pem     — 私钥
  root.crt                — 根证书（需导入系统并信任）
```

## 2. 仅初始化目录

功能描述：初始化输出目录结构，创建 OpenSSL CA 所需的文件。

```bash
zxtool --ssl --init
```

## 3. 仅生成 Root CA

功能描述：单独生成根证书，不签发网站证书。

```bash
# 生成 Root CA
zxtool --ssl --gen-root

# 强制重新生成 Root CA
zxtool --ssl --gen-root --force
```

## 4. 清空所有证书

功能描述：清空所有历史证书，包括根证书和网站证书。

```bash
zxtool --ssl --flush
```

## 生成的证书文件

```
out/
├── ca.cnf                      # OpenSSL CA 配置
├── root.crt                    # 根证书（需导入系统并信任）
├── root.key.pem                # 根证书私钥
├── cert.key.pem                # 证书私钥（所有网站证书共用）
├── index.txt                   # CA 数据库
├── serial                      # 证书序列号
├── newcerts/                   # CA 签发的证书备份
└── <domain>/
    ├── <domain>.crt            # 网站证书
    ├── <domain>.bundle.crt     # 拼接了 CA 的完整证书链（用于 nginx）
    ├── <domain>.key.pem -> ../cert.key.pem  # 私钥（符号链接）
    └── root.crt -> ../root.crt              # 根证书（符号链接）
```

其中 `<domain>.bundle.crt` 已拼接好 CA 证书，可直接添加到 nginx 配置中。

## 证书有效期

| 证书类型 | 默认有效期 | 修改方式 |
|----------|-----------|----------|
| 根证书 | 20 年（7300 天） | 修改 `DEFAULT_ROOT_DAYS` 常量 |
| 网站证书 | 2 年（730 天） | 修改 `DEFAULT_CERT_DAYS` 常量 |

## nginx 配置示例

```nginx
server {
    listen 443 ssl;
    server_name example.dev *.example.dev;

    ssl_certificate     /path/to/out/example.dev/example.dev.bundle.crt;
    ssl_certificate_key /path/to/out/example.dev/example.dev.key.pem;

    # ... 其他配置
}
```

## 信任根证书

生成证书后，需要将 `out/root.crt` 导入操作系统的信任存储：

### macOS

```bash
# 添加到钥匙串
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain out/root.crt
```

### Linux (Ubuntu/Debian)

```bash
sudo cp out/root.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

### Windows

1. 双击 `root.crt` 文件
2. 点击"安装证书"
3. 选择"本地计算机"
4. 选择"将所有的证书都放入下列存储"
5. 浏览并选择"受信任的根证书颁发机构"
6. 完成安装

## Chrome 信任证书

如果 Chrome 不信任证书，可参考：
- 确保根证书已正确导入系统信任存储
- 重启 Chrome 浏览器
- 访问 `chrome://restart` 强制重启
