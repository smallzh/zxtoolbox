## ADDED Requirements

### Requirement: Video download
Downloads a video from a given URL using yt-dlp, selecting the best available MP4 format.

#### Scenario: Downloads video from URL
- **WHEN** `download_video()` is called with a valid video URL
- **THEN** yt-dlp is invoked to download the video
- **AND** the best available MP4 format (`best[ext=mp4]`) is selected

#### Scenario: Errors on invalid URL
- **WHEN** the provided URL is unreachable or not a supported video platform
- **THEN** a clear error message is returned indicating the URL could not be resolved

### Requirement: Progress display
Shows a real-time progress bar during the download process.

#### Scenario: Shows download progress
- **WHEN** a video download is in progress
- **THEN** a progress indicator is displayed showing:
  - Download percentage
  - Download speed
  - Estimated time remaining
  - Total file size

#### Scenario: Progress updates in real-time
- **WHEN** the download progresses
- **THEN** the progress display is updated in real-time as yt-dlp outputs progress data

### Requirement: ffmpeg detection
Uses ffmpeg if available on the system to merge separate audio and video streams into a single MP4 file.

#### Scenario: Merges streams with ffmpeg
- **WHEN** ffmpeg is detected on the system PATH
- **THEN** yt-dlp is configured to use ffmpeg for merging separate audio and video streams into a single MP4 file

#### Scenario: Downloads without ffmpeg
- **WHEN** ffmpeg is not detected on the system PATH
- **THEN** yt-dlp downloads only the best single-stream format that already contains both audio and video

#### Scenario: Detects ffmpeg availability
- **WHEN** `download_video()` starts
- **THEN** it checks for `ffmpeg` on the system PATH
- **AND** logs whether ffmpeg is available

### Requirement: Custom output
Accepts an optional output path parameter to specify where the downloaded file should be saved.

#### Scenario: Saves to custom output path
- **WHEN** `download_video()` is called with an `--output` parameter
- **THEN** the downloaded video is saved at the specified output path

#### Scenario: Uses default output naming
- **WHEN** no output path is specified
- **THEN** the video is saved in the current working directory with yt-dlp's default naming template (`%(title)s.%(ext)s`)
