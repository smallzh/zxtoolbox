(function () {
    const config = window.__ZXTOOL_HTTP_VIDEO__;
    const startButton = document.getElementById("startButton");
    const pauseButton = document.getElementById("pauseButton");
    const screenshotButton = document.getElementById("screenshotButton");
    const statusText = document.getElementById("statusText");
    const savedPathText = document.getElementById("savedPathText");
    const shotPreview = document.getElementById("shotPreview");
    const shotEmpty = document.getElementById("shotEmpty");

    function setStatus(message, tone) {
        statusText.textContent = message;
        statusText.dataset.tone = tone || "info";
    }

    function setButtonsEnabled(enabled) {
        startButton.disabled = !enabled;
        pauseButton.disabled = !enabled;
        screenshotButton.disabled = !enabled;
    }

    function showScreenshot(dataUrl) {
        shotPreview.src = dataUrl;
        shotPreview.hidden = false;
        if (shotEmpty) {
            shotEmpty.hidden = true;
        }
    }

    function showSavedPath(pathText) {
        if (!savedPathText) {
            return;
        }

        savedPathText.hidden = false;
        savedPathText.textContent = "已保存到: " + pathText;
    }

    async function uploadScreenshot(dataUrl) {
        const response = await fetch(config.screenshotApiUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                imageDataUrl: dataUrl,
            }),
        });

        let payload = null;
        try {
            payload = await response.json();
        } catch (error) {
            throw new Error("服务端返回了无效响应。");
        }

        if (!response.ok || !payload || !payload.ok) {
            const message = payload && payload.message
                ? payload.message
                : "截图保存失败。";
            throw new Error(message);
        }

        return payload;
    }

    if (!config || !window.Player) {
        setStatus("播放器资源未加载完成，无法初始化页面。", "error");
        return;
    }

    const player = new window.Player({
        id: "player",
        url: config.videoUrl,
        poster: "",
        lang: "zh-cn",
        fluid: true,
        autoplay: false,
        playsinline: true,
        pip: false,
        download: false,
        screenShot: {
            saveImg: false,
            fitVideo: true,
            name: config.screenshotBaseName || "screenshot",
            format: ".png",
            type: "image/png",
            quality: 0.92,
        },
    });

    setButtonsEnabled(true);
    setStatus("播放器已就绪，可以开始播放。", "success");

    startButton.addEventListener("click", () => {
        const result = player.play();
        if (result && typeof result.catch === "function") {
            result.catch((error) => {
                console.error("Failed to start playback.", error);
                setStatus("浏览器阻止了播放，请再次点击开始。", "error");
            });
        }
    });

    pauseButton.addEventListener("click", () => {
        player.pause();
        setStatus("视频已暂停。", "info");
    });

    screenshotButton.addEventListener("click", async () => {
        const plugin = player.getPlugin("screenShot");
        if (!plugin || typeof plugin.shot !== "function") {
            setStatus("当前播放器未启用截屏功能。", "error");
            return;
        }

        screenshotButton.disabled = true;
        setStatus("正在生成并保存截屏...", "info");

        try {
            const dataUrl = await plugin.shot();
            showScreenshot(dataUrl);
            const payload = await uploadScreenshot(dataUrl);
            showSavedPath(payload.filePath || payload.fileName);
            setStatus("截屏已保存到视频所在目录。", "success");
        } catch (error) {
            console.error("Failed to capture or upload screenshot.", error);
            const message = error instanceof Error ? error.message : "截图失败。";
            setStatus(message, "error");
        } finally {
            screenshotButton.disabled = false;
        }
    });

    player.on("play", () => {
        setStatus("视频播放中。", "success");
    });

    player.on("pause", () => {
        if (!player.ended) {
            setStatus("视频已暂停。", "info");
        }
    });

    player.on("ended", () => {
        setStatus("视频播放结束。", "info");
    });

    player.on("error", (error) => {
        console.error("Player error.", error);
        setStatus("视频加载或播放失败，请检查文件是否可访问。", "error");
    });
})();
