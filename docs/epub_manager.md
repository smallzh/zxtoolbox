# EPUB 转 Markdown

`zxtool epub convert` 用于把单个 `.epub` 文件转换成一个 Markdown 目录。

## 用法

```bash
zxtool epub convert ./book.epub -o ./book_md
```

## 输出结构

转换后的目录默认包含：

```text
book_md/
├── toc.md
├── chapters/
│   ├── 01-*.md
│   ├── 02-*.md
│   └── ...
└── assets/
    └── ...
```

- `toc.md`：目录文件，包含章节链接
- `chapters/`：按目录顺序拆分出的章节 Markdown
- `assets/`：静态图片资源

## 说明

- 章节文件名会按目录顺序自动编号
- 图片链接会自动重写到 `assets/` 目录
- 章节间链接会尽量转换成对应的 Markdown 相对链接
