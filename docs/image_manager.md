# 图片压缩与尺寸调整

<div align="center">
<img src = "../assets/images/hammer.webp" />
</div>

基于 Pillow 的图片处理模块，支持尺寸调整和文件大小压缩。

## 0x01. 功能概述

图片管理模块提供两个核心功能：

1. **尺寸调整 (resize)** - 改变图片的宽高尺寸，保持内容完整不变
2. **大小压缩 (compress)** - 减小图片文件体积，保持尺寸不变

## 0x02. 命令格式

```bash
zxtool image <子命令> [选项]
```

| 子命令 | 说明 |
|--------|------|
| `resize` | 调整图片尺寸 |
| `compress` | 压缩图片大小 |

## 0x03. resize — 尺寸调整

调整图片到指定的宽高尺寸。支持 JPEG、PNG、WebP 格式。

```bash
zxtool image resize <input> -w WIDTH [--height HEIGHT] [-o OUTPUT]
```

| 参数 | 说明 |
|------|------|
| `input` | 输入图片路径（必需） |
| `-w, --width` | 目标宽度（像素） |
| `--height` | 目标高度（像素） |
| `-o, --output` | 输出路径（默认自动生成） |

- 至少指定 `--width` 或 `--height` 中的一个
- 只指定一个参数时，另一个按原始宽高比自动计算
- 同时指定两个参数时，精确调整到指定尺寸（内容不变，比例可能变化）

**示例：**

```bash
# 将图片宽度调整为 128px，高度按比例自动缩放
zxtool image resize photo.jpg -w 128

# 精确调整到 100x100
zxtool image resize photo.png -w 100 --height 100

# 指定输出路径
zxtool image resize photo.jpg -w 640 -o thumbnail.jpg
```

## 0x04. compress — 大小压缩

压缩图片文件大小，保持原有尺寸不变。

```bash
zxtool image compress <input> [-s MAX_SIZE] [-q QUALITY] [-o OUTPUT] [-f FORMAT]
```

| 参数 | 说明 |
|------|------|
| `input` | 输入图片路径（必需） |
| `-s, --max-size` | 目标文件大小（如 `200K`、`1.5M`） |
| `-q, --quality` | 输出质量 1-100 |
| `-o, --output` | 输出路径（默认自动生成） |
| `-f, --format` | 输出格式：`jpeg`、`png`、`webp` |

- 指定 `--max-size` 时，自动通过二分法搜索最优质量参数
- 指定 `--quality` 时，使用指定质量编码（不保证文件大小）
- 不指定任何参数时，以默认质量保存（图片可能不会明显缩小）
- PNG 格式不支持质量参数，如需大幅压缩建议转换为 JPEG 或 WebP

**示例：**

```bash
# 压缩到 200KB 以内（自动搜索质量参数）
zxtool image compress photo.jpg -s 200K

# 指定质量为 50 保存
zxtool image compress photo.jpg -q 50

# 压缩并转换为 WebP 格式
zxtool image compress photo.png -s 500K -f webp

# 指定输出路径和格式
zxtool image compress photo.jpg -s 1M -o compressed.jpg
```

## 0x05. 支持的文件格式

| 格式 | resize | compress | 质量参数 |
|------|--------|----------|----------|
| JPEG | ✅ | ✅ | 支持（二分搜索质量） |
| PNG | ✅ | ✅ | 不支持（仅 optimize） |
| WebP | ✅ | ✅ | 支持（二分搜索质量） |
