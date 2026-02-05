# PyPI 发布流程指南

本文档详细说明如何将 `zxtoolbox` 项目发布到 PyPI（Python Package Index）。

## 前置准备

### 1. 注册 PyPI 账号
- 访问 [PyPI 官网](https://pypi.org/account/register/) 注册账号
- 建议同时注册 [TestPyPI](https://test.pypi.org/account/register/) 用于测试发布

### 2. 安装必要工具
确保已安装 `uv` 和 `twine`：
```shell
# 使用 uv 管理 Python 环境（项目已使用）
# 安装 twine 用于上传包
uv pip install twine
```

### 3. 准备 API Token
1. 登录 PyPI 账号
2. 进入 Account settings → API tokens
3. 创建新的 API token（建议命名为 "zxtoolbox publishing"）
4. 范围选择 "Entire account" 或仅限 "zxtoolbox" 项目
5. **重要**：保存生成的 token（只显示一次）

4. 对于 TestPyPI，同样生成测试环境的 API token

## 第一步：检查项目配置

### 1. 验证 pyproject.toml
确认 `pyproject.toml` 包含以下必要信息：

```toml
[project]
name = "zxtoolbox"              # 包名（唯一）
version = "0.1.0"               # 版本号（每次发布必须递增）
description = "some used tool collections"
readme = "README.md"            # 项目说明
requires-python = ">=3.13"      # Python 版本要求
dependencies = [                # 依赖列表
    "paramiko>=3.5.1",
    "prettytable>=3.16.0",
    "psutil>=7.0.0",
    "py-cpuinfo>=9.0.0",
    "pynvml>=12.0.0",
]

[project.optional-dependencies]
docs = [
    "mkdocs>=1.6.0",
    "mkdocs-gitbook>=0.0.1",
]

[project.scripts]
zxtoolbox = "zxtoolbox.cli:main"  # 命令行入口

[build-system]
requires = ["uv_build>=0.8.9,<0.9.0"]
build-backend = "uv_build"
```

### 2. 完善 README.md
确保 README.md 包含：
- 项目简介
- 安装说明
- 使用示例
- 功能列表
- 贡献指南（可选）

### 3. 检查包结构
```
src/
└── zxtoolbox/
    ├── __init__.py  # 必须包含版本号
    ├── cli.py
    ├── computer_info.py
    ├── git_branch_file.py
    └── ssh_deploy.py
```

在 `__init__.py` 中添加版本信息：
```python
__version__ = "0.1.0"
```

## 第二步：构建发布包

### 1. 清理旧的构建文件
```shell
# Windows PowerShell
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

# 或使用命令
if (Test-Path dist) { Remove-Item -Recurse dist }
if (Test-Path build) { Remove-Item -Recurse build }
```

### 2. 使用 uv 构建分发包
```shell
uv build
```

这将在 `dist/` 目录下生成：
- `zxtoolbox-0.1.0.tar.gz`（源码包）
- `zxtoolbox-0.1.0-py3-none-any.whl`（wheel 包）

### 3. 验证构建结果
```shell
# 检查 dist 目录内容
dir dist
```

## 第三步：本地测试包

### 1. 创建测试环境
```shell
# 创建临时虚拟环境
uv venv .venv-test
.\.venv-test\Scripts\activate
```

### 2. 安装本地包
```shell
uv pip install dist\zxtoolbox-0.1.0-py3-none-any.whl
```

### 3. 测试安装
```shell
# 测试导入
python -c "import zxtoolbox; print(zxtoolbox.__version__)"

# 测试命令行
zxtoolbox --help
```

### 4. 卸载测试包
```shell
uv pip uninstall zxtoolbox
deactivate
```

## 第四步：发布到 TestPyPI（推荐）

### 1. 配置 TestPyPI 认证
创建或编辑 `%USERPROFILE%\.pypirc` 文件：

```ini
[distutils]
index-servers =
    pypi
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-你的testpypi-token

[pypi]
username = __token__
password = pypi-你的pypi-token
```

### 2. 上传到 TestPyPI
```shell
uv twine upload --repository testpypi dist\*
```

或使用 twine：
```shell
twine upload --repository testpypi dist\*
```

### 3. 从 TestPyPI 安装测试
```shell
# 创建新的测试环境
uv venv .venv-test
.\.venv-test\Scripts\activate

# 从 TestPyPI 安装
uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ zxtoolbox

# 测试功能
python -c "import zxtoolbox; print(zxtoolbox.__version__)"
zxtoolbox --help

# 卸载
uv pip uninstall zxtoolbox
deactivate
```

### 4. 访问 TestPyPI 查看包
打开 [TestPyPI zxtoolbox 页面](https://test.pypi.org/project/zxtoolbox/) 确认发布成功

## 第五步：发布到正式 PyPI

⚠️ **注意**：PyPI 上的包名一旦发布就**无法删除**，只能 yank（标记为过时）。

### 1. 最后检查
- 版本号是否正确
- README.md 是否完整
- 依赖是否正确
- 功能是否测试通过

### 2. 上传到 PyPI
```shell
uv twine upload dist\*
```

或使用 twine：
```shell
twine upload dist\*
```

### 3. 验证发布
```shell
# 等待几分钟后（通常 1-5 分钟）
uv pip install zxtoolbox

# 测试安装
python -c "import zxtoolbox; print(zxtoolbox.__version__)"
zxtoolbox --help
```

### 4. 访问 PyPI 查看包
打开 [PyPI zxtoolbox 页面](https://pypi.org/project/zxtoolbox/)

## 后续版本发布

### 1. 更新版本号
在 `pyproject.toml` 和 `src/zxtoolbox/__init__.py` 中更新版本号：

```toml
# pyproject.toml
version = "0.1.1"  # 递增版本号
```

```python
# src/zxtoolbox/__init__.py
__version__ = "0.1.1"
```

### 2. 重复构建和发布流程
```shell
# 清理
Remove-Item -Recurse dist, build -ErrorAction SilentlyContinue

# 构建
uv build

# 测试（可选但推荐）
# ... 本地测试和 TestPyPI 测试 ...

# 发布
uv twine upload dist\*
```

### 3. 更新变更日志（可选）
在 README.md 或单独的 CHANGELOG.md 中记录版本变更。

## 常见问题排查

### 问题 1：上传失败 - 包名已存在
- PyPI 上包名必须唯一
- 如果包名已被占用，需要更换包名

### 问题 2：版本号冲突
- 同一版本号不能重复发布
- 必须递增版本号（遵循语义化版本：MAJOR.MINOR.PATCH）

### 问题 3：依赖解析失败
- 检查 `pyproject.toml` 中的依赖版本约束
- 确保依赖在 PyPI 上存在

### 问题 4：构建警告
```
warning: no previously-included files found matching ...
```
- 检查 `.gitignore` 和 `MANIFEST.in`（如果存在）
- 确保包含必要的文件

### 问题 5：上传超时
```shell
# 增加超时时间
twine upload --verbose dist\*
```

## 安全最佳实践

1. **不要提交 API Token 到版本控制**
   - API Token 应存储在本地配置文件中
   - 不要在 `.pypirc` 中明文存储（使用 `__token__` 机制）

2. **使用 Trusted Publishing（推荐）**
   - 配置 GitHub Actions 自动发布
   - 无需存储 API Token

3. **验证包完整性**
   ```shell
   # 下载并验证
   uv pip download zxtoolbox --no-deps
   # 检查哈希值
   ```

4. **定期更新依赖**
   - 保持依赖包安全

## 自动化发布（进阶）

### 使用 GitHub Actions 自动发布

创建 `.github/workflows/publish.yml`：

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: read

jobs:
  pypi-publish:
    name: Upload release to PyPI
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/zxtoolbox
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - name: Build package
        run: uv build
      - name: Publish package distributions to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

发布时只需打标签：
```shell
git tag v0.1.0
git push origin v0.1.0
```

## 参考资源

- [PyPI 官方文档](https://packaging.python.org/)
- [PyPI 项目打包指南](https://packaging.python.org/tutorials/packaging-projects/)
- [uv 文档](https://docs.astral.sh/uv/)
- [twine 文档](https://twine.readthedocs.io/)
- [PEP 440 - 版本标识规范](https://peps.python.org/pep-0440/)
- [语义化版本控制](https://semver.org/)

## 快速命令参考

```shell
# 完整发布流程
Remove-Item -Recurse dist, build -ErrorAction SilentlyContinue
uv build
uv twine upload dist\*

# TestPyPI 发布
uv twine upload --repository testpypi dist\*

# 验证安装
uv pip install zxtoolbox
python -c "import zxtoolbox; print(zxtoolbox.__version__)"
```