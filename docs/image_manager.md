# 图片压缩与尺寸调整

<div align="center">
<img src = "../assets/images/hammer.webp" />
</div>

基于 Pillow 的图片处理模块，支持尺寸调整和文件大小压缩。

## 0x01. 功能概述

图片管理模块提供三个核心功能：

1. **尺寸调整 (resize)** - 改变图片的宽高尺寸，保持内容完整不变
2. **大小压缩 (compress)** - 减小图片文件体积，保持尺寸不变
3. **批量压缩 (batch)** - 将目录内全部图片统一转换为 WebP，可控制在目标大小内

## 0x02. 命令格式

```bash
zxtool image <子命令> [选项]
```

| 子命令 | 说明 |
|--------|------|
| `resize` | 调整图片尺寸 |
| `compress` | 压缩图片大小 |
| `batch` | 批量压缩目录内图片为 WebP |

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

## 0x05. batch — 批量压缩为 WebP

将目录内的所有图片（仅当前目录，不递归子目录）统一压缩为 WebP 格式，输出文件名与源文件同名（扩展名改为 `.webp`）。

```bash
zxtool image batch <directory> [-s MAX_SIZE] [-k] [--backup-dir DIR]
```

| 参数 | 说明 |
|------|------|
| `directory` | 输入图片目录（必需，只处理顶层文件） |
| `-s, --max-size` | 目标大小（如 `20K`、`100K`），默认 `20K` |
| `-k, --keep-original` | 保留原图：将原图移入备份目录而不是删除 |
| `--backup-dir` | 原图备份目录（与 `-k` 搭配，默认 `<directory>/originals`） |

**处理规则：**

- 源文件大小 ≤ 阈值（默认 20K）的图片**不压缩**，原地保留并跳过
- 超过阈值的图片做一次质量搜索压缩为 WebP：
  - 未传 `-k`：转换成功后**删除原文件**
  - 传了 `-k`：原文件先**移入备份目录**，主目录只留 WebP
- 若质量降到最低仍超过阈值，保留当前最优结果并给出 `[WARN]` 提示（不缩小分辨率）
- 文件名冲突时备份文件自动追加序号（如 `photo_1.jpg`）

**示例：**

```bash
# 将 photos 目录下所有大图压缩为 <20K 的 webp，原图删除
zxtool image batch ./photos

# 指定 100K 阈值
zxtool image batch ./photos -s 100K

# 保留原图：原图自动移入 ./photos/originals
zxtool image batch ./photos -k

# 自定义备份目录
zxtool image batch ./photos -k --backup-dir /backup/photos
```

## 0x06. 支持的文件格式

| 格式 | resize | compress | batch 转换 | 质量参数 |
|------|--------|----------|------------|----------|
| JPEG | ✅ | ✅ | ✅ | 支持（二分搜索质量） |
| PNG | ✅ | ✅ | ✅ | 不支持（仅 optimize） |
| WebP | ✅ | ✅ | ✅ | 支持（二分搜索质量） |
