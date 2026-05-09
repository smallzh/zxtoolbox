## 1. CLI 调度层

- [ ] 1.1 实现 `cli.py` 的 argparse 解析器构建（`build_parser()`），包含 14 个顶级子命令（ci, totp, video, http, ssl, mkdocs, nginx, config, git, epub, backup, mkpdf, le, feishu）
- [ ] 1.2 实现 `main()` 函数的路由分发逻辑，根据 `args.command` 分发到对应的 `handle_*()` 函数
- [ ] 1.3 实现每个子命令的 `_build_*_parser()` 函数，定义参数和标志
- [ ] 1.4 实现每个子命令的 `handle_*()` 函数，解析参数后调用功能模块
- [ ] 1.5 实现版本输出支持（`-v`/`--version`）
- [ ] 1.6 实现帮助信息输出回退（`_print_help()`）

## 2. 配置管理模块

- [ ] 2.1 实现 TOML 配置文件读写：`load_config()`、`write_config()`、`generate_config_content()`
- [ ] 2.2 实现各配置段加载器：`load_le_config()`、`load_nginx_config()`、`load_logging_config()`、`load_feishu_config()`
- [ ] 2.3 实现项目配置查找：`load_project_by_name()`、`load_projects_with_domain()`
- [ ] 2.4 实现交互式配置初始化向导 `interactive_init()`
- [ ] 2.5 实现配置文件内容显示 `show_config()`
- [ ] 2.6 实现各配置段的 TOML 生成函数（`_generate_letsencrypt_section`、`_generate_nginx_section` 等）

## 3. 日志系统

- [ ] 3.1 实现 `setup_logging()` 使用 `TimedRotatingFileHandler` 按日轮转
- [ ] 3.2 实现日志配置从 `~/.config/zxtool.toml` 读取
- [ ] 3.3 实现日志目录自动创建和不可写回退
- [ ] 3.4 实现测试用 `reset_logging()` 状态重置

## 4. 系统信息采集

- [ ] 4.1 实现 `summary_info()` 输出操作系统/CPU/GPU/内存/磁盘/网络摘要
- [ ] 4.2 实现 `detailed_info()` 输出各子系统的详细信息
- [ ] 4.3 实现 GPU 检测：pynvml → nvidia-smi → GPUtil 三级回退
- [ ] 4.4 实现跨平台操作系统检测（Windows/macOS/Linux）
- [ ] 4.5 实现内存大小人类可读格式化

## 5. Git 配置管理

- [ ] 5.1 实现 `.git` 目录向上查找 `find_git_dir()`
- [ ] 5.2 实现 `.git/config` 读写（使用 configparser）
- [ ] 5.3 实现 `check_git_config()` 检查 user.name 和 user.email
- [ ] 5.4 实现 `fill_git_config()` 填充配置（CLI 参数 > zxtool.toml > 交互输入）

## 6. Git 拉取和克隆

- [ ] 6.1 实现单仓库 `git_pull()` 带超时和错误处理
- [ ] 6.2 实现 `git_clone()` 远程仓库克隆
- [ ] 6.3 实现按名称 `git_pull_by_name()`（目录存在则 pull，不存在则 clone）
- [ ] 6.4 实现批量操作 `git_pull_all_projects()` 带进度和汇总

## 7. MkDocs 项目管理

- [ ] 7.1 实现 `create_project()` 生成 mkdocs.yml 和 docs/index.md
- [ ] 7.2 实现 `build_project()` 带输出目录和严格模式
- [ ] 7.3 实现 `build_project_by_name()` 从配置查找项目
- [ ] 7.4 实现 `batch_build()` 批量构建和 dry-run
- [ ] 7.5 实现 `serve_project()` 开发服务器

## 8. Markdown 转 PDF

- [ ] 8.1 实现 Markdown 源收集和文档标题提取
- [ ] 8.2 实现 HTML 文档构建，包含内置 CSS 样式
- [ ] 8.3 实现跨平台浏览器自动发现
- [ ] 8.4 实现 Mermaid 代码块预处理和渲染（含 Mermaid JS 资源解析）
- [ ] 8.5 实现浏览器无头 PDF 打印

## 9. 自签 SSL 证书

- [ ] 9.1 实现 CA 目录结构初始化 `init()`
- [ ] 9.2 实现 Root CA 生成 `generate_root()`
- [ ] 9.3 实现域名证书签发 `generate_cert()`，含 SAN 和通配符
- [ ] 9.4 实现证书链捆绑和版本化输出

## 10. Nginx 配置管理

- [ ] 10.1 实现 `check_nginx()` 检测 Nginx 安装和配置目录
- [ ] 10.2 实现 `generate_site_config()` 生成 HTTPS/HTTP 站点配置
- [ ] 10.3 实现 `generate_from_config()` 批量生成
- [ ] 10.4 实现 SSL 证书路径自动解析
- [ ] 10.5 实现 `enable_site()` 和 `disable_site()` 符号链接管理
- [ ] 10.6 实现 `reload_nginx()` 配置重载

## 11. Let's Encrypt 证书管理

- [ ] 11.1 实现 `AcmeShManager`：安装检查、版本获取、命令执行
- [ ] 11.2 实现 `CertificateManager.issue_cert()` 支持 DNS-01/HTTP-01
- [ ] 11.3 实现证书安装到输出目录（`_install_cert()`）
- [ ] 11.4 实现 `renew_certs()` 自动续签（30 天阈值）
- [ ] 11.5 实现 `revoke_cert()` 吊销和状态清理
- [ ] 11.6 实现 `batch_obtain_certs()` 批量操作
- [ ] 11.7 实现 `CronManager` 定时任务安装/卸载
- [ ] 11.8 实现证书状态查看和展示

## 12. EPUB 转 Markdown

- [ ] 12.1 实现 EPUB 文件解析（manifest/spine/TOC）
- [ ] 12.2 实现 nav.xhtml 和 toc.ncx 的 TOC 解析
- [ ] 12.3 实现 `_MarkdownRenderer` XHTML 转 Markdown 渲染
- [ ] 12.4 实现章节拆分和编号文件名生成
- [ ] 12.5 实现图片资产提取和路径重写
- [ ] 12.6 实现 `toc.md` 目录文件生成
- [ ] 12.7 实现损坏 EPUB 的 ZIP 修复

## 13. 目录备份

- [ ] 13.1 实现 `copy_directory_with_backup()` 目录复制
- [ ] 13.2 实现 Git 仓库检测和自动提交
- [ ] 13.3 实现非 Git 目录的存档式备份（带时间戳）
- [ ] 13.4 实现备份记录 Markdown 日志

## 14. 其他功能模块

- [ ] 14.1 实现 `video_download.py`：基于 yt-dlp 的视频下载和进度显示
- [ ] 14.2 实现 `pyopt_2fa.py`：TOTP 验证码生成
- [ ] 14.3 实现 `http_server.py`：静态文件 HTTP 服务
- [ ] 14.4 实现 `feishu_client.py`：飞书 WebSocket 客户端

## 15. 测试

- [ ] 15.1 为 `test_cli.py` 编写所有 CLI 子命令的 mock 测试
- [ ] 15.2 为 `test_config_manager.py` 编写配置读写和初始化测试
- [ ] 15.3 为 `test_git_config.py` 编写 Git 配置检查/填充测试
- [ ] 15.4 为 `test_mkdocs_manager.py` 编写 MkDocs 创建/构建测试
- [ ] 15.5 为 `test_mkpdf_manager.py` 编写 Markdown 转 PDF 测试
- [ ] 15.6 为 `test_letsencrypt.py` 编写证书管理测试
- [ ] 15.7 为 `test_nginx_manager.py` 编写 Nginx 配置测试
- [ ] 15.8 为 `test_ssl_cert.py` 编写 SSL 证书测试
- [ ] 15.9 为 `test_epub_manager.py` 编写 EPUB 转换测试
- [ ] 15.10 为 `test_backup_manager.py` 编写目录备份测试
- [ ] 15.11 为 `test_pyopt_2fa.py` 编写 TOTP 测试
- [ ] 15.12 为 `test_video_download.py` 编写视频下载测试
- [ ] 15.13 为 `test_computer_info.py` 编写系统信息测试
- [ ] 15.14 为 `test_http_server.py` 编写 HTTP 服务器测试
- [ ] 15.15 为 `test_logging_manager.py` 编写日志系统测试
