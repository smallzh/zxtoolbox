# 音频提取

从本地视频文件中提取音频并保存为音频文件（默认 mp3）。需要 ffmpeg 在 PATH 中。


## 0x01. 提取音频

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

## 0x02. FFmpeg 安装与配置（推荐）

FFmpeg 是一个强大的音视频处理工具，音频提取依赖它。

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

## 0x03. 常见问题

### Q1: 提取音频时提示 ffmpeg not found？
- 提取音频依赖 ffmpeg，请按 0x02 节安装并确保它在系统 PATH 中
