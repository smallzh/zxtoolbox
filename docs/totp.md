# TOTP 双因素认证解析

解析 TOTP（基于时间的一次性密码）密钥，生成 2FA 验证码。

## 0x01. 命令格式

```bash
zxtool totp -k <密钥>
```

| 选项 | 说明 |
|------|------|
| `-k, --key` | TOTP 密钥（必需） |

### 使用示例

```bash
# 解析 TOTP 密钥，生成当前验证码
zxtool totp -k JBSWY3DPEHPK3PXP
```

**输出示例：**

```
OTP Code: 123456
Remaining seconds: 25
```