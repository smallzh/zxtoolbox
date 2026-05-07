# HTTP 静态文件服务

`zxtool http serve` 用于快速启动一个本地静态文件 HTTP 服务，适合预览构建产物、临时共享前端页面或测试纯静态资源目录。

## 基本用法

```bash
zxtool http serve
```

默认行为：

- 服务目录为当前目录
- 监听地址为 `127.0.0.1`
- 监听端口为 `8000`

启动后可通过 `http://127.0.0.1:8000` 访问，按 `Ctrl+C` 停止服务。

## 指定静态目录

```bash
zxtool http serve ./dist
```

上面的命令会将 `./dist` 目录作为站点根目录对外提供。

## 指定监听地址和端口

```bash
zxtool http serve ./site --host 0.0.0.0 --port 9000
```

适用于以下场景：

- 局域网内其他设备访问当前机器上的静态资源
- 避免和本机其他服务占用相同端口

## 常见场景

### 预览前端构建产物

```bash
zxtool http serve ./dist -p 8080
```

### 预览 MkDocs 构建后的站点目录

```bash
zxtool mkdocs build ./my-docs -o ./site
zxtool http serve ./site
```

## 注意事项

- 目标路径必须存在且必须是目录
- 如果端口已被占用，命令会直接输出错误信息并退出
- 这是静态文件服务器，不包含热更新、反向代理或认证能力
