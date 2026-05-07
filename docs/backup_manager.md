# 目录备份拷贝

`zxtool backup copy` 用于把源目录内容拷贝到目标目录，并根据目标目录是否受 Git 管理采用不同策略。

## 用法

```bash
zxtool backup copy ./source ./target
```

可选参数：

```bash
zxtool backup copy ./source ./target \
  --backup-dir-name .zxtool_backups \
  --backup-log-name backup-records.md \
  --commit-message "sync content"
```

## 行为说明

### 目标目录是 Git 仓库

- 如果目标中存在同名文件，会先删除旧文件，再复制源文件
- 全部复制完成后自动执行 Git 提交
- 默认提交信息格式为：

```text
zxtool backup sync from <source_dir_name> at <timestamp>
```

### 目标目录不是 Git 仓库

- 如果目标中存在同名文件，会先备份旧文件
- 备份文件会放到专门的备份目录，文件名尾部追加时间戳
- 会生成备份记录文档，记录每次覆盖和备份结果

## 默认备份输出

```text
target/
├── ...
└── .zxtool_backups/
    ├── backup-records.md
    └── ...
```
