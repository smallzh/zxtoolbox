# 飞书客户端集成

通过飞书（Feishu/Lark）机器人实现远程 CLI 命令执行。

## 0x01. 功能概述

飞书客户端模块允许你：
1. **远程执行命令** - 在飞书聊天窗口中执行 `git pull`、`mkdocs batch` 等命令
2. **实时接收结果** - 命令执行结果直接返回到飞书聊天
3. **多人协作** - 团队成员可通过飞书共同管理项目

## 0x02. 系统要求

- **飞书企业自建应用** - 需要创建自建应用并获取 App ID 和 App Secret
- **长连接权限** - 需要开通 WebSocket 连接权限
- **事件订阅配置** - 需要配置接收消息事件

## 0x03. 配置飞书应用

### 3.1 创建自建应用

1. 进入 [飞书开发者平台](https://open.feishu.cn/app)
2. 点击「创建企业自建应用」
3. 填写应用名称和描述
4. 记录 **App ID** 和 **App Secret**

### 3.2 配置权限

在「权限管理」中开通以下权限：
- `im:chat:read` - 读取群组信息
- `im:message:send` - 发送消息
- `im:message.group_msg` - 接收群消息
- `im:message.p2p_msg` - 接收单聊消息

### 3.3 配置事件订阅

1. 进入「事件订阅」页面
2. 选择「使用长连接接收事件」
3. 在「添加事件」中订阅：
   - **消息事件** - 接收消息 v2.0（im.message.receive_v1）

### 3.4 发布应用

1. 进入「版本管理与发布」
2. 创建版本并填写发布信息
3. 申请发布，等待管理员审批

## 0x04. 配置 zxtool

### 4.1 在配置文件中添加飞书设置

```toml
[feishu]
app_id = "cli_xxxxxxxxxxxxx"
app_secret = "xxxxxxxxxxxxxxxxxxxx"
```

### 4.2 使用交互式配置

```bash
zxtool config init
```

在向导中选择配置飞书客户端：
```
--- 飞书客户端配置 ---
配置飞书客户端? (y/N): y
  飞书 App ID (如 cli_xxxxxxxxxxxxx): cli_xxxxxxxxxxxxx
  飞书 App Secret: xxxxxxxxxxxxxxxxxxxx
  [OK] 飞书配置已添加
```

### 4.3 验证配置

```bash
zxtool feishu check
```

## 0x05. 启动飞书客户端

### 5.1 使用配置文件启动

```bash
zxtool feishu start
```

### 5.2 使用命令行参数启动

```bash
zxtool feishu start --app-id cli_xxxxxxxxxxxxx --app-secret xxxxxxxxxxxxxxxxxxxx
```

### 5.3 指定配置文件

```bash
zxtool feishu start --config /path/to/zxtool.toml
```

### 5.4 后台运行（Linux/macOS）

```bash
# 使用 nohup
nohup zxtool feishu start > feishu.log 2>&1 &

# 或使用 systemd
```

## 0x06. 支持的命令

### 6.1 Git 操作

**拉取所有项目：**
```
git pull
```

**拉取指定项目：**
```
git pull myproject
```

**指定远程和分支：**
```
git pull myproject origin main
```

### 6.2 MkDocs 操作

**批量构建：**
```
mkdocs batch
```

### 6.3 帮助

**查看帮助：**
```
help
```
或
```
?
```

## 0x07. 使用示例

### 场景 1：日常代码更新

1. 团队成员在飞书中发送：
   ```
   git pull myproject
   ```

2. 机器人回复：
   ```
   ✅ Git pull 成功
   
   项目 myproject：
   - 更新文件：3 个
   - 最新提交：fix: update styles
   ```

### 场景 2：文档构建

1. 编辑在飞书中发送：
   ```
   mkdocs batch
   ```

2. 机器人回复：
   ```
   📊 构建结果: 2/2 成功
   
   ✅ project1 构建成功
   ✅ project2 构建成功
   ```

### 场景 3：多人协作

团队成员可以在群聊中共同管理项目：

```
成员 A: git pull project1
机器人: ✅ project1 已更新到最新版本

成员 B: mkdocs batch
机器人: 📊 构建完成，2 个项目成功
```

## 0x08. 安全注意事项

### 8.1 权限控制

- **限制应用可见范围** - 在飞书管理后台设置应用的可见成员
- **保护配置文件** - 配置文件包含敏感信息，注意权限设置
- **使用环境变量** - 生产环境建议使用环境变量传递密钥

### 8.2 配置文件权限

```bash
# 设置配置文件权限为仅所有者可读写
chmod 600 ~/.config/zxtool.toml
```

### 8.3 网络安全

- **防火墙配置** - 确保服务器可以访问飞书 API（域名：open.feishu.cn）
- **内网部署** - 如需在内网使用，需要配置代理

## 0x09. 故障排查

### 9.1 无法连接飞书

**问题：** 启动后没有响应或连接失败

**检查：**
1. 确认 App ID 和 App Secret 正确
2. 检查应用是否已发布并通过审核
3. 确认已开通 WebSocket 权限
4. 查看日志文件排查错误

### 9.2 消息发送失败

**问题：** 能接收消息但无法回复

**检查：**
1. 确认应用有 `im:message:send` 权限
2. 检查用户是否已安装应用
3. 确认应用可见范围包含该用户

### 9.3 命令执行失败

**问题：** 机器人回复执行失败

**检查：**
1. 确认项目目录正确
2. 检查 Git/MkDocs 是否已安装
3. 查看详细错误信息

### 9.4 查看日志

```bash
# 查看日志文件
cat ~/.config/zxtool_logs/zxtool_$(date +%Y-%m-%d).log
```

## 0x0a. 高级配置

### 10.1 使用 systemd 服务（Linux）

创建 `/etc/systemd/system/zxtool-feishu.service`：

```ini
[Unit]
Description=ZXToolbox Feishu Client
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username
ExecStart=/usr/local/bin/zxtool feishu start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable zxtool-feishu
sudo systemctl start zxtool-feishu
sudo systemctl status zxtool-feishu
```

### 10.2 Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.13-slim

RUN pip install zxtoolbox

COPY zxtool.toml /root/.config/zxtool.toml

CMD ["zxtool", "feishu", "start"]
```

构建和运行：
```bash
docker build -t zxtool-feishu .
docker run -d --name feishu-client zxtool-feishu
```

## 0x0b. 限制说明

| 项目 | 限制 |
|------|------|
| **消息长度** | 单条消息最多 6000 字符 |
| **命令超时** | Git pull: 5 分钟，MkDocs: 10 分钟 |
| **并发处理** | 单连接，消息顺序处理 |
| **连接数** | 单个应用最多 50 个 WebSocket 连接 |

## 0x0c. 参考资料

- **飞书开放平台** - https://open.feishu.cn/
- **lark-oapi SDK** - https://github.com/larksuite/oapi-sdk-python
- **事件订阅文档** - https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-/use-websocket
- **消息 API** - https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create

## 0x0d. 常见问题

### Q1: 飞书个人版可以使用吗？

不可以。飞书客户端集成需要企业自建应用，个人版不支持。

### Q2: 可以同时运行多个客户端吗？

可以，但不建议。多个客户端会导致消息重复处理。如果需要高可用，可以使用集群模式（只有一个客户端接收事件）。

### Q3: 如何在群聊中使用？

1. 将应用添加到群聊
2. 在群聊中直接发送命令
3. 机器人会回复到群聊中

### Q4: 支持私聊吗？

支持。私聊和群聊都可以使用。

### Q5: 如何停止客户端？

在终端中按 `Ctrl+C`，或使用 `kill` 命令：

```bash
# 查找进程
ps aux | grep "zxtool feishu"

# 停止进程
kill <PID>
```

### Q6: 可以扩展其他命令吗？

可以。在 `feishu_client.py` 的 `_parse_command` 和 `_execute_xxx` 方法中添加新命令。
