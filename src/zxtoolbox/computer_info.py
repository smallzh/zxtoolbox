
import platform
import socket
import psutil
from cpuinfo import get_cpu_info
from prettytable import PrettyTable

from zxtoolbox import cowsay


def convert_read_str(number):
    kb = 1024
    mb_unit = 1024 ** 2
    gb_unit = 1024 ** 3

    if number / gb_unit > 1:
        return f"{number / gb_unit:.1f} GB"
    elif number / mb_unit > 1:
        return f"{number / mb_unit:.1f} MB"
    elif number / kb > 1:
        return f"{number / kb:.1f} KB"
    else:
        return f"{number} Bytes"


def init_table(table):
    table.field_names = ["property", "value"]
    table.align["value"] = "l"
    table.max_width["value"] = 50


def get_os_info():
    """获取操作系统信息"""
    system = platform.system()
    if system == "Windows":
        version = platform.win32_ver()[0]
        return f"Windows {version}"
    elif system == "Darwin":
        version = platform.mac_ver()[0]
        return f"macOS {version}"
    elif system == "Linux":
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        return line.split('=')[1].strip('"')
        except:
            return f"Linux {platform.release()}"
    return system


def get_cpu_summary():
    """获取CPU摘要信息"""
    cpu_count = psutil.cpu_count(logical=False)
    cpu_freq = psutil.cpu_freq()
    freq_str = f"{cpu_freq.max / 1000:.1f} GHz" if cpu_freq else "N/A"
    return f"{cpu_count} Cores, {freq_str}"


def get_gpu_summary():
    """获取GPU摘要信息"""
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            return f"{gpu.name}"
    except ImportError:
        pass
    
    # 尝试通过nvidia-smi获取
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    return "N/A"


def get_memory_summary():
    """获取内存摘要信息"""
    mem = psutil.virtual_memory()
    return convert_read_str(mem.total)


def get_disk_summary():
    """获取磁盘摘要信息"""
    # 获取主磁盘（通常是根目录或C盘）
    if platform.system() == "Windows":
        disk_usage = psutil.disk_usage('C:\\')
    else:
        disk_usage = psutil.disk_usage('/')
    return convert_read_str(disk_usage.total)


def get_network_summary():
    """获取网络IP摘要信息"""
    try:
        # 获取主网卡IP
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        return "N/A"


def summary_info():
    """输出简约汇总信息"""
    table = PrettyTable()
    table.field_names = ["类别", "详情"]
    table.align = "l"
    
    table.add_row(["OS", get_os_info()])
    table.add_row(["CPU", get_cpu_summary()])
    table.add_row(["GPU", get_gpu_summary()])
    table.add_row(["Memory", get_memory_summary()])
    table.add_row(["Disk", get_disk_summary()])
    table.add_row(["Network", get_network_summary()])
    
    print(table)


def cpu_info():
    """获取CPU详细信息"""
    ignore_keys = ['python_version', 'cpuinfo_version', 'cpuinfo_version_string']
    cpu_table = PrettyTable()
    init_table(cpu_table)
    for key, value in get_cpu_info().items():
        if key not in ignore_keys:
            cpu_table.add_row([key, value if not key.endswith('_size') else convert_read_str(value)])
    print('CPU info:')
    print(cpu_table)


def gpu_info():
    """获取GPU详细信息"""
    gpu_table = PrettyTable()
    init_table(gpu_table)
    
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            for i, gpu in enumerate(gpus):
                gpu_table.add_divider()
                gpu_table.add_row([f"GPU {i} Name", gpu.name])
                gpu_table.add_row([f"GPU {i} Driver", gpu.driver])
                gpu_table.add_row([f"GPU {i} Memory Total", convert_read_str(gpu.memoryTotal * 1024 * 1024)])
                gpu_table.add_row([f"GPU {i} Memory Free", convert_read_str(gpu.memoryFree * 1024 * 1024)])
                gpu_table.add_row([f"GPU {i} Memory Used", convert_read_str(gpu.memoryUsed * 1024 * 1024)])
                gpu_table.add_row([f"GPU {i} Temperature", f"{gpu.temperature}°C"])
                gpu_table.add_row([f"GPU {i} Load", f"{gpu.load * 100:.1f}%"])
        else:
            gpu_table.add_row(["GPU", "No GPU detected"])
    except ImportError:
        gpu_table.add_row(["GPU", "GPUtil not installed"])
    except Exception as e:
        gpu_table.add_row(["GPU", f"Error: {str(e)}"])
    
    print('GPU info:')
    print(gpu_table)


def memory_info():
    """获取内存详细信息"""
    mem_table = PrettyTable()
    init_table(mem_table)
    mem = psutil.virtual_memory()
    s_mem = psutil.swap_memory()
    mem_table.add_divider()
    mem_table.add_row(['total', convert_read_str(mem.total)])
    mem_table.add_row(['available', convert_read_str(mem.available)])
    mem_table.add_row(['used', convert_read_str(mem.used)])
    mem_table.add_row(['free', convert_read_str(mem.free)])
    mem_table.add_row(['percent', f"{mem.percent}%"])
    mem_table.add_divider()
    mem_table.add_row(['swap total', convert_read_str(s_mem.total)])
    mem_table.add_row(['swap used', convert_read_str(s_mem.used)])
    mem_table.add_row(['swap free', convert_read_str(s_mem.free)])
    mem_table.add_row(['swap percent', f"{s_mem.percent}%"])

    print('Memory & Swap Memory info:')
    print(mem_table)


def disk_info():
    """获取磁盘详细信息"""
    disk_table = PrettyTable()
    disk_table.field_names = ["device", "mount", "fstype", "total", "used", "free", "percent"]
    disk_table.align = "l"
    
    parts = psutil.disk_partitions()
    for part in parts:
        try:
            use = psutil.disk_usage(part.mountpoint)
            disk_table.add_row([part.device, part.mountpoint, part.fstype,
                                convert_read_str(use.total), convert_read_str(use.used), 
                                convert_read_str(use.free), f"{use.percent}%"])
        except PermissionError:
            continue

    print('Disk info:')
    print(disk_table)


def network_info():
    """获取网络详细信息"""
    net_table = PrettyTable()
    init_table(net_table)
    
    # 获取主机名
    hostname = socket.gethostname()
    net_table.add_row(["Hostname", hostname])
    
    # 获取本机IP
    try:
        ip = socket.gethostbyname(hostname)
        net_table.add_row(["Local IP", ip])
    except:
        net_table.add_row(["Local IP", "N/A"])
    
    # 获取所有网络接口信息
    net_io = psutil.net_io_counters()
    net_table.add_divider()
    net_table.add_row(["Bytes Sent", convert_read_str(net_io.bytes_sent)])
    net_table.add_row(["Bytes Received", convert_read_str(net_io.bytes_recv)])
    net_table.add_row(["Packets Sent", str(net_io.packets_sent)])
    net_table.add_row(["Packets Received", str(net_io.packets_recv)])
    
    # 获取网络接口详情
    net_table.add_divider()
    net_if_addrs = psutil.net_if_addrs()
    for iface, addrs in net_if_addrs.items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                net_table.add_row([f"Interface {iface}", addr.address])
                break
    
    print('Network info:')
    print(net_table)


def os_info():
    """获取操作系统详细信息"""
    os_table = PrettyTable()
    init_table(os_table)
    
    os_table.add_row(["System", platform.system()])
    os_table.add_row(["Node Name", platform.node()])
    os_table.add_row(["Release", platform.release()])
    os_table.add_row(["Version", platform.version()])
    os_table.add_row(["Machine", platform.machine()])
    os_table.add_row(["Processor", platform.processor()])
    
    if platform.system() == "Windows":
        os_table.add_divider()
        win_ver = platform.win32_ver()
        os_table.add_row(["Windows Version", win_ver[0]])
        os_table.add_row(["Service Pack", win_ver[2]])
    elif platform.system() == "Darwin":
        os_table.add_divider()
        mac_ver = platform.mac_ver()
        os_table.add_row(["macOS Version", mac_ver[0]])
    
    print('OS info:')
    print(os_table)


def detailed_info():
    """输出详细信息"""
    os_info()
    cpu_info()
    gpu_info()
    memory_info()
    disk_info()
    network_info()


def get_all_info():
    """获取所有信息（默认行为）"""
    cowsay("Welcome to this Computer!")
    detailed_info()


if __name__ == '__main__':
    get_all_info()