# toolbox

Window、Mac、Linux系统中，对经常做的一些重复性事情的封装

## 0x01. 项目打包

```shell
uv sync
```

## 0x02. 目录结构
```text
--|
  - doc: 文档目录
  - toolbox: 代码目录
        - __init__.py: 包文件
        - cli.py: 命令行入库
        - ssh_deploy.py: 通过 ssh的方式，部署项目
        - computer_info.py: 获取计算机的cpu、gpu、内存、硬盘相关信息
        - test : 测试目录
            - __init__.py: 包文件
            - test_cli.py: 测试文件
            - test_ssh_deploy.py: 测试文件
  - setup.py
  - README.md
  - requirements.txt
  - test-requirements.txt
    
```

## 0x09. 依赖的包
1. paramiko, 网站:[https://www.paramiko.org/](https://www.paramiko.org/)
2. psutil, 网站:
3. py-cpuinfo, 网站:
4. GPUtil, 网站: