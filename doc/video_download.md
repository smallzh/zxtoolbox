# 在线视频下载器

根据在线视频的播放URL地址，下载视频到本地


## 1. 在线视频下载

功能描述：根据在线视频的播放URL地址，下载视频到本地硬盘

命令行: `zxtoolbox -v -u http://xxxx/yyy --vo d:\file`，参数说明如下:

| 名称 | 说明                                                          |
|----|-------------------------------------------------------------|
| -v, --video  | 激活 在线视频下载功能                                                |
| -u, --url  | 在线视频的url地址                                                      |
| --vo, --video-output  | 本地硬盘的路径（可选，默认为当前目录）      |

### 使用示例

```bash
# 下载视频到当前目录
zxtoolbox -v -u "https://www.youtube.com/watch?v=xxxxx"

# 下载视频到指定目录
zxtoolbox -v -u "https://www.youtube.com/watch?v=xxxxx" --vo "D:\Downloads"

# 下载视频并指定文件名
zxtoolbox -v -u "https://www.youtube.com/watch?v=xxxxx" --vo "D:\Downloads\my_video.mp4"
```


## 2. FFmpeg 安装与配置（推荐）

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


## 3. 常见问题

### Q1: 下载失败或速度慢？
- 检查网络连接
- 某些网站可能需要代理，设置环境变量：`set HTTP_PROXY=http://proxy:port`
- 尝试使用 `--format` 参数选择较低清晰度

### Q2: 下载的视频没有声音？
- 安装 FFmpeg 并确保它在系统 PATH 中
- 工具会自动检测并使用 FFmpeg 合并音视频

