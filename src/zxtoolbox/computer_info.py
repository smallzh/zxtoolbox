
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

def cpu_info():
    ignore_keys = ['python_version', 'cpuinfo_version', 'cpuinfo_version_string']
    cpu_table = PrettyTable()
    init_table(cpu_table)
    for key, value in get_cpu_info().items():
        if key not in ignore_keys:
            cpu_table.add_row([key, value if not key.endswith('_size') else convert_read_str(value)])
    print('CPU info:')
    print(cpu_table)

def memory_info():
    mem_table = PrettyTable()
    init_table(mem_table)
    mem = psutil.virtual_memory()
    s_mem = psutil.swap_memory()
    mem_table.add_divider()
    mem_table.add_row(['total', convert_read_str(mem.total)])
    mem_table.add_row(['available', convert_read_str(mem.available)])
    mem_table.add_row(['used', convert_read_str(mem.used)])
    mem_table.add_row(['free', convert_read_str(mem.free)])
    mem_table.add_divider()
    mem_table.add_row(['total', convert_read_str(s_mem.total)])
    mem_table.add_row(['used', convert_read_str(s_mem.used)])
    mem_table.add_row(['free', convert_read_str(s_mem.free)])

    print('Memory & Swap Memory info:')
    print(mem_table)

def disk_info():
    disk_table = PrettyTable()
    disk_table.field_names   = ["device", "mount", "fstype", "total", "used", "free"]
    disk_table.align = "l"
    #
    parts = psutil.disk_partitions()
    for part in parts:
        use = psutil.disk_usage(part.device)
        disk_table.add_row([part.device, part.mountpoint, part.fstype,
                            convert_read_str(use.total), convert_read_str(use.used), convert_read_str(use.free)])

    print('Disk info:')
    print(disk_table)

def get_all_info():
    cowsay("Wellcome to this Computer!")
    # get cpu info
    cpu_info()
    # get memory info
    memory_info()
    # get disk info
    disk_info()

if __name__ == '__main__':
    get_all_info()