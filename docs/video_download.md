# 视频工具

视频相关工具集合：下载在线视频、从本地视频提取音频。

## 0x01. 下载在线视频

### 命令格式

```bash
zxtool video download -u <URL> [-o <输出路径>]
```

| 选项 | 说明 |
|------|------|
| `-u, --url` | 在线视频 URL 地址（必需） |
| `-o, --output` | 视频输出路径（可选，默认当前目录） |

### 使用示例

```bash
# 下载视频到当前目录
zxtool video download -u "https://www.youtube.com/watch?v=xxxxx"

# 下载视频到指定目录
zxtool video download -u "https://www.youtube.com/watch?v=xxxxx" -o "/path/to/downloads"

# 下载视频并指定文件名
zxtool video download -u "https://www.youtube.com/watch?v=xxxxx" -o "/path/to/downloads/my_video.mp4"
```

## 0x02. 提取音频

从本地视频文件中提取音频并保存为音频文件（默认 mp3）。需要 ffmpeg 在 PATH 中。

### 命令格式

```bash
zxtool video audio -f <视频文件> [-o <输出路径>] [-t <音频格式>] [-b <比特率>]
```

| 选项 | 说明 |
|------|------|
| `-f, --file` | 本地视频文件路径（必需） |
| `-o, --output` | 输出路径，可以是音频文件或目录（可选，默认与源视频同目录同名） |
| `-t, --format` | 音频格式：mp3（默认）/ aac / m4a / opus / wav / flac |
| `-b, --bitrate` | 音频比特率，仅对有损格式生效（默认 192k） |

### 使用示例

```bash
# 提取为 mp3（默认 192k），输出为同目录的 video.mp3
zxtool video audio -f "./video.mp4"

# 指定输出目录（自动命名为 video.mp3）
zxtool video audio -f "./video.mp4" -o "/path/to/audios"

# 指定输出文件名与格式
zxtool video audio -f "./video.mp4" -o "/path/to/audios/sound.m4a" -t m4a

# 无损格式（忽略比特率）
zxtool video audio -f "./video.mp4" -t flac
```

## 0x03. FFmpeg 安装与配置（推荐）

FFmpeg 是一个强大的音视频处理工具，用于合并下载的视频和音频流。

### 2.1 Windows 安装

#### 方法一：使用 winget（推荐）
```powershell
winget install Gyan.FFmpeg
```

#### 方法二：手动安装
1. 访问 FFmpeg 官方下载页：https://www.gyan.dev/ffmpeg/builds/
2. 下载 `ffmpeg-release-essentials.zip`
3. 解压到 `C:\ffmpeg` 目录
4. 将 `C:\ffmpeg\bin` 添加到系统环境变量 PATH

#### 验证安装
```powershell
ffmpeg -version
```

### 2.2 macOS 安装

```bash
# 使用 Homebrew 安装
brew install ffmpeg
```

### 2.3 Linux 安装

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### 2.4 为什么需要 FFmpeg

许多视频网站（如 YouTube）将视频和音频分开存储：
- 视频流：高清画面，无声音
- 音频流：声音数据

FFmpeg 可以自动将这两个流合并成一个完整的视频文件。如果没有 FFmpeg，yt-dlp 会分别下载视频和音频文件。

## 0x04. 常见问题

### Q1: 提取音频时提示 ffmpeg not found？

### Q1: 提取音频时提示 ffmpeg not found？
- 提取音频依赖 ffmpeg，请按 0x03 节安装并确保它在系统 PATH 中

### Q2: 下载失败或速度慢？
- 检查网络连接
- 某些网站可能需要代理，设置环境变量：`set HTTP_PROXY=http://proxy:port`
- 尝试使用 `--format` 参数选择较低清晰度

### Q2: 下载的视频没有声音？
- 安装 FFmpeg 并确保它在系统 PATH 中
- 工具会自动检测并使用 FFmpeg 合并音视频