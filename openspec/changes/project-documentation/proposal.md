## Why

zxtoolbox 是一个跨平台的 Python CLI 工具集合，目前已有 15+ 个功能模块和完整的 CLI 调度架构。项目缺乏完整的规格文档和设计记录，导致新成员上手成本高、变更影响评估困难、测试覆盖难以追溯。需要通过 OpenSpec 文档体系对项目进行系统化归档，为后续特性开发和维护建立规范基础。

## What Changes

- 创建项目概览提案文档，定义 zxtoolbox 的核心定位和能力边界
- 创建设计文档，记录 CLI 调度架构、模块划分、配置管理、跨平台适配等关键技术决策
- 为每个功能模块创建规格文档（spec），描述其接口、行为和约束
- 创建实现任务列表，覆盖 CLI、配置管理、日志、各功能模块的开发任务

## Capabilities

### New Capabilities

- `cli-dispatch`: CLI 入口和子命令调度机制，包括 argparse 解析器构建和路由分发
- `config-management`: TOML 配置文件管理，包含交互式初始化、多段配置读写、项目配置查找
- `logging`: 日志系统，基于 TimedRotatingFileHandler 的按日轮转日志
- `computer-info`: 系统信息采集，涵盖 CPU/GPU/内存/磁盘/网络/OS 信息汇总和详细展示
- `git-config`: Git 仓库配置检查与填充，支持从 TOML 配置读取默认用户信息
- `git-pull`: Git 仓库批量拉取和克隆，支持按项目名称从配置文件查找
- `mkdocs-management`: MkDocs 项目创建、构建（单项目/批量/按名称）、本地预览服务
- `mkpdf-conversion`: Markdown 转 PDF，基于浏览器无头打印，支持 Mermaid 图表渲染
- `self-signed-ssl`: 自签泛域名 SSL 证书生成，基于 OpenSSL 实现 CA 和站点证书链管理
- `nginx-config`: Nginx 站点配置生成、启用/禁用、配置重载
- `lets-encrypt`: Let's Encrypt ACME v2 证书管理，基于 acme.sh 封装，支持 DNS-01/HTTP-01
- `epub-conversion`: EPUB 转 Markdown 目录结构，包含章节拆分、资源提取和目录生成
- `directory-backup`: 目录复制与备份，支持 Git 仓库自动提交和非 Git 目录历史备份
- `video-download`: 在线视频下载，基于 yt-dlp 带进度显示
- `totp-generator`: TOTP 双因素认证码生成
- `http-server`: 静态文件 HTTP 服务
- `feishu-bot`: 飞书（Lark）客户端集成，通过 WebSocket 长连接接收消息并执行 CLI 命令

### Modified Capabilities

- 无（初始文档化，无已有规格需要修改）

## Impact

- 仅添加文档文件，不影响现有代码结构和功能
- 新增文件位于 `openspec/changes/project-documentation/` 目录
- 规格文档位于 `openspec/specs/` 目录
- 为后续 OpenSpec 驱动的开发工作流奠定基础
