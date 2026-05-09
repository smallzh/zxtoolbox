# Computer Info

## ADDED Requirements

### Requirement: Summary info
`summary_info()` outputs OS/CPU/GPU/Memory/Disk/Network in PrettyTable format.

#### Scenario: Summary table printed to stdout
- **WHEN** `summary_info()` is called
- **THEN** it prints a PrettyTable with rows for OS, CPU, GPU, Memory, Disk, and Network showing key summary values

### Requirement: Detailed info
`detailed_info()` outputs OS, CPU, GPU, Memory, Disk, and Network detail sections.

#### Scenario: Detailed sections printed to stdout
- **WHEN** `detailed_info()` is called
- **THEN** it prints formatted detail sections for OS, CPU, GPU, Memory, Disk, and Network with comprehensive information in each section

### Requirement: GPU detection
Multiple backends (pynvml > nvidia-smi > GPUtil) for GPU information.

#### Scenario: GPU detection with pynvml
- **WHEN** `pynvml` is installed and NVIDIA drivers are available
- **THEN** GPU information is retrieved via pynvml bindings

#### Scenario: GPU detection fallback to nvidia-smi
- **WHEN** `pynvml` is unavailable but `nvidia-smi` is on the system PATH
- **THEN** GPU information is retrieved by running `nvidia-smi` as a subprocess

#### Scenario: GPU detection fallback to GPUtil
- **WHEN** neither `pynvml` nor `nvidia-smi` are available but `GPUtil` is installed
- **THEN** GPU information is retrieved via GPUtil

#### Scenario: No GPU detected
- **WHEN** no GPU detection backend is available or no GPU is present
- **THEN** the GPU section displays a "No GPU detected" message

### Requirement: Cross-platform OS detection
Windows, macOS, and Linux are supported via the `platform` module.

#### Scenario: Windows detection
- **WHEN** running on a Windows system
- **THEN** OS information is gathered using `platform.win32_ver()` and related Windows APIs

#### Scenario: macOS detection
- **WHEN** running on a macOS system
- **THEN** OS information is gathered using `platform.mac_ver()` and related APIs

#### Scenario: Linux detection
- **WHEN** running on a Linux system
- **THEN** OS information is gathered by reading `/etc/os-release` and related files

### Requirement: Memory display
Human-readable size formatting (KB/MB/GB).

#### Scenario: Memory size formatted with units
- **WHEN** memory or disk sizes are displayed
- **THEN** raw byte values are converted to human-readable strings with appropriate units (KB, MB, GB, TB)
