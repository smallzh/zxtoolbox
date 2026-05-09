## Context

zxtoolbox 是一个基于 Python >= 3.13 的跨平台 CLI 工具集合，通过 `zxtool` 命令作为统一入口。项目采用 argparse 作为 CLI 框架，所有功能模块和 CLI 调度代码集中在 `src/zxtoolbox/` 目录下，遵循"瘦 CLI + 胖模块"的设计原则。当前项目已有完整的 CLI 调度架构、TOML 配置管理和 15+ 功能模块，但缺乏系统性架构文档。

## Goals / Non-Goals

**Goals:**
- 记录 CLI 调度架构和 argparse 解析器构建模式
- 记录 TOML 配置管理模块的设计和配置结构
- 记录各功能模块的外部接口和内部实现架构
- 记录跨平台适配策略（Windows/Mac/Linux）
- 记录测试策略和模块化设计原则

**Non-Goals:**
- 不修改现有代码行为
- 不引入新的依赖或功能
- 不重构现有模块

## Decisions

### 1. 瘦 CLI + 胖模块的调度模式

将 `cli.py` 限定为纯调度层，所有业务逻辑放入独立模块。`cli.py` 通过 `build_parser()` 构建 argparser 树，`main()` 函数根据 `args.command` 分发到 `handle_*()` 函数。每个 `handle_*()` 函数及其对应的 `_build_*_parser()` 在 `cli.py` 中集中定义，而实际业务逻辑在独立模块中实现。

**为什么而不是直接在 cli.py 中实现逻辑：** 保持 CLI 层的可测试性和可维护性，同时允许模块被其他 Python 代码直接导入使用（如 `feishu_client.py` 中直接调用 `gc.git_pull()`）。

### 2. TOML 配置驱动批处理

`~/.config/zxtool.toml` 采用 TOML 格式，通过 `tomllib`（Python 3.11+ 标准库）读取。配置结构支持 `[[projects]]` 数组、`[letsencrypt]`、`[nginx]`、`[git]`、`[logging]`、`[feishu]` 等节。

**为什么使用 TOML 而不是 YAML/JSON：** TOML 是 Python 社区事实标准（pyproject.toml），Python 3.11+ 原生支持 `tomllib`，无需额外依赖。TOML 的表格和数组语法适合表达层级配置。

**为什么允许多层配置覆盖：** 命令行参数 > 配置文件中的项目级配置 > 全局默认值。这种三层次优先级让用户在保持默认值的同时可以灵活覆盖。

### 3. 全局唯一日志初始化

`logging_manager.py` 通过 `_initialized` 全局变量确保 `setup_logging()` 只执行一次。日志使用 `TimedRotatingFileHandler` 按日切割，保留 7 天历史。

**为什么使用全局状态而不是依赖注入：** 日志初始化发生在 CLI 启动的最早阶段，全局状态简化了跨模块共享。测试通过 `reset_logging()` 重置状态。

### 4. 浏览器无头打印实现 Markdown 转 PDF

`mkpdf_manager.py` 先将 Markdown 渲染为 HTML（通过 `markdown` 库），然后调用 Edge/Chrome/Chromium 的无头模式进行 PDF 打印。

**为什么选择浏览器打印而非 wkhtmltopdf/WeasyPrint：** 浏览器渲染能原生支持 Mermaid 图表、CSS 分页、中文字体渲染等复杂场景。代价是需要安装浏览器、打包 Mermaid JS 资源。

### 5. 自建 XHTML 渲染引擎处理 EPUB 转换

`epub_manager.py` 实现了轻量级的 XHTML 到 Markdown 转换器 `_MarkdownRenderer`，不依赖 pandoc 或第三方 HTML 转 Markdown 库。

**为什么自建渲染器而不是调用 pandoc：** 保持零外部依赖，精确控制章节拆分、锚点注入、资源路径重写等 EPUB 特有需求。epublib 库处理 EPUB 解析，渲染器只负责格式转换。

### 6. acme.sh 封装实现 Let's Encrypt 集成

`letsencrypt.py` 通过封装 acme.sh shell 脚本实现 ACME v2 协议交互，而非直接使用 ACME 协议。

**为什么不直接使用 ACME 协议：** acme.sh 是成熟稳定的 ACME 客户端，已经处理了续签、密钥管理、DNS API 集成等细节。Python 封装提供了跨平台一致接口同时复用 acme.sh 的生态。

### 7. 跨平台路径和浏览器发现

`mkpdf_manager.py` 的 `_find_browser_executable()` 根据 `os.name` 和 `sys.platform` 分别构建 Windows/macOS/Linux 的候选浏览器路径列表。`ssl_cert.py` 的 OpenSSL 子进程调用使用 `capture_output=True` 跨平台兼容。`letsencrypt.py` 的 `AcmeShManager._build_command()` 处理 Windows 上 `.sh` 脚本的特殊执行路径。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| `setup_logging()` 全局状态在测试间泄漏 | `reset_logging()` 在测试 fixture 中清理，各测试模块独立 mock |
| 浏览器路径探测在 headless CI 环境可能失败 | 提供 `--browser` 参数允许用户显式指定路径 |
| acme.sh 在 Windows 上的兼容性有限 | `_run_stub_script_fallback()` 提供测试桩回退，但生产环境建议在 WSL 或 Linux 使用 |
| epub_manager.py ZIP 修复逻辑复杂 | 仅在中央目录损坏时触发，正常 EPUB 走标准解析路径 |
| mkpdf_manager.py 的 Mermaid 渲染依赖网络加载的 JS 文件 | 默认打包 mermaid.min.js 到项目 assets，不需网络访问 |
