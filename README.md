# toolbox

Window、Mac、Linux系统中，对经常做的一些重复性事情的封装

## 0x01. 项目打包

```shell
uv sync
```

参考：[uv的Projects下的Creating projects](https://docs.astral.sh/uv/concepts/projects/init/)

## 0x02. 目录结构
```text
--|
  - doc: 文档目录
  - src: 代码目录
      - toolbox: 代码目录
            - __init__.py: 包文件
            - cli.py: 命令行入库
            - ssh_deploy.py: 通过 ssh的方式，部署项目
            - computer_info.py: 获取计算机的cpu、gpu、内存、硬盘相关信息
            - test : 测试目录
                - __init__.py: 包文件
                - test_cli.py: 测试文件
                - test_ssh_deploy.py: 测试文件
  - README.md
  - requirements.txt
  - test-requirements.txt
    
```

## 0x09. 依赖的包
1. paramiko, 网站:[https://www.paramiko.org/](https://www.paramiko.org/)
2. psutil, 网站:
3. py-cpuinfo, 网站:
4. GPUtil, 网站:

## 0x10. 运行单元测试

项目使用 `pytest` 作为测试框架，测试文件位于 `src/zxtoolbox/test/` 目录。

### 安装测试依赖

```shell
uv add --dev pytest
```

### 运行全部测试

```shell
uv run pytest src/zxtoolbox/test/ -v
```

### 运行单个测试文件

```shell
uv run pytest src/zxtoolbox/test/test_cli.py -v
```

### 运行指定测试类或方法

```shell
# 运行指定测试类
uv run pytest src/zxtoolbox/test/test_cli.py::TestCliGit -v

# 运行指定测试方法
uv run pytest src/zxtoolbox/test/test_cli.py::TestCliGit::test_git_config_check -v
```

### 查看测试覆盖率

```shell
uv add --dev pytest-cov
uv run pytest src/zxtoolbox/test/ --cov=zxtoolbox --cov-report=term-missing
```