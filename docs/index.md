# zxtoolbox

`zxtoolbox` 是一个面向 Windows、Mac、Linux 的常用工具集合，用来封装重复性操作。

## 功能概览

- 计算机信息查看
- Git 仓库配置与批量拉取
- MkDocs 项目创建、构建、批量构建、预览
- Nginx 站点配置管理
- Let's Encrypt 证书管理
- 自签 SSL 证书生成
- 飞书客户端集成
- 在线视频下载
- TOTP 解析
- EPUB 转 Markdown
- 目录备份拷贝

## 安装

```bash
uv tool install zxtoolbox
```

## 基本用法

```bash
zxtool --help
```

## 命令一览

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `ci` | 显示计算机信息 | `zxtool ci --all` |
| `git` | Git 仓库配置和拉取 | `zxtool git pull` |
| `mkdocs` | MkDocs 项目管理 | `zxtool mkdocs build ./docs-site` |
| `nginx` | Nginx 配置管理 | `zxtool nginx generate` |
| `le` | Let's Encrypt 证书管理 | `zxtool le issue -d example.com` |
| `ssl` | 自签 SSL 证书生成 | `zxtool ssl cert -d example.dev` |
| `feishu` | 飞书客户端管理 | `zxtool feishu check` |
| `video` | 在线视频下载 | `zxtool video -u https://example.com/video` |
| `totp` | TOTP 解析 | `zxtool totp -k SECRET_KEY` |
| `epub` | EPUB 转 Markdown | `zxtool epub convert ./book.epub -o ./book_md` |
| `backup` | 目录备份拷贝 | `zxtool backup copy ./src ./dst` |
