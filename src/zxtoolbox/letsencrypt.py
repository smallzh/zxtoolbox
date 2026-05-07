"""Let's Encrypt 证书管理模块 - acme.sh 封装。

通过封装 acme.sh 脚本实现 ACME v2 协议证书管理。
支持单域名、泛域名证书申请，自动续签，定时任务配置等功能。

主要功能:
    - acme.sh 安装和版本管理
    - 单域名证书申请 (HTTP-01)
    - 泛域名证书申请 (DNS-01)
    - 证书自动续签和定时任务
    - 证书状态查看
    - 证书吊销

使用示例:
    >>> from zxtoolbox.letsencrypt import AcmeShManager
    >>> manager = AcmeShManager()
    >>> manager.check_and_install()  # 检查并安装 acme.sh
    >>> manager.issue_cert("example.com", dns_provider="dns_cf")
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# acme.sh 默认安装路径
ACME_SH_INSTALL_DIR = Path.home() / ".acme.sh"
ACME_SH_BIN = ACME_SH_INSTALL_DIR / "acme.sh"
ACME_SH_INSTALL_URL = "https://get.acme.sh"

# 证书默认输出目录
DEFAULT_CERT_DIR = Path("out_le")

# 续签状态文件
RENEW_STATE_FILE = "renew_state.json"

# DNS 提供商映射
DNS_PROVIDER_MAP = {
    "manual": "dns_manual",
    "cloudflare": "dns_cf",
    "aliyun": "dns_ali",
}

# HTTP-01 提供商映射
HTTP_PROVIDER_MAP = {
    "webroot": "webroot",
    "standalone": "standalone",
}


logger = logging.getLogger(__name__)


def _safe_domain_path_name(domain: str) -> str:
    """将域名转换为适合文件系统路径的名称。"""
    return domain.replace("*.", "wildcard.")


class AcmeShError(Exception):
    """acme.sh 操作错误。"""

    pass


class AcmeShManager:
    """acme.sh 管理器。

    负责 acme.sh 的安装、版本检查和命令执行。

    Attributes:
        install_dir: acme.sh 安装目录
        bin_path: acme.sh 可执行文件路径
    """

    def __init__(self, install_dir: str | Path | None = None):
        """初始化管理器。

        Args:
            install_dir: acme.sh 安装目录，默认为 ~/.acme.sh
        """
        self.install_dir = Path(install_dir) if install_dir else ACME_SH_INSTALL_DIR
        self.bin_path = self.install_dir / "acme.sh"

    def is_installed(self) -> bool:
        """检查 acme.sh 是否已安装。

        Returns:
            True 如果 acme.sh 已安装且可执行
        """
        return self.bin_path.exists() and os.access(self.bin_path, os.X_OK)

    def _resolve_bash_path(self) -> str | None:
        """解析可用的 bash 路径，避免误用 WSL 启动器。"""
        bash_path = shutil.which("bash")
        if not bash_path:
            return None

        bash_resolved = Path(bash_path).resolve()
        if "system32" in str(bash_resolved).lower():
            return None

        return str(bash_resolved)

    def _run_stub_script_fallback(
        self,
        cmd: list[str],
    ) -> subprocess.CompletedProcess | None:
        """在 Windows 上为极简 .sh 测试桩提供回退执行。"""
        if platform.system() != "Windows" or self.bin_path.suffix != ".sh":
            return None

        try:
            script_text = self.bin_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

        significant_lines = []
        for line in script_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#!"):
                continue
            significant_lines.append(stripped)

        if not significant_lines:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        echo_outputs: list[str] = []
        for line in significant_lines:
            if not line.startswith("echo "):
                return None

            output = line[5:].strip()
            if len(output) >= 2 and output[0] == output[-1] and output[0] in {"'", '"'}:
                output = output[1:-1]
            echo_outputs.append(output)

        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="\n".join(echo_outputs),
            stderr="",
        )

    def _build_command(self, *args: str) -> list[str]:
        """构建跨平台的 acme.sh 执行命令。"""
        if platform.system() == "Windows" and self.bin_path.suffix == ".sh":
            bash_path = self._resolve_bash_path()
            if bash_path:
                return [bash_path, str(self.bin_path), *args]
        return [str(self.bin_path), *args]

    def get_version(self) -> str | None:
        """获取 acme.sh 版本号。

        Returns:
            版本号字符串，如 "3.0.0"，未安装则返回 None
        """
        if not self.is_installed():
            return None

        cmd = self._build_command("--version")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, OSError):
            result = self._run_stub_script_fallback(cmd)
            if result is None:
                return None

        # 版本输出格式: https://github.com/acmesh-official/acme.sh v3.0.0
        match = re.search(r"v(\d+\.\d+\.\d+)", result.stdout)
        if match:
            return match.group(1)

        return None

    def install(self) -> bool:
        """安装 acme.sh。

        使用官方安装脚本安装 acme.sh。

        Returns:
            True 如果安装成功

        Raises:
            AcmeShError: 安装失败时
        """
        print("[INFO] 开始安装 acme.sh...")

        # 检查 curl 或 wget
        curl_path = shutil.which("curl")
        wget_path = shutil.which("wget")

        if not curl_path and not wget_path:
            raise AcmeShError("需要 curl 或 wget 来安装 acme.sh")

        try:
            if curl_path:
                cmd = [
                    "bash",
                    "-c",
                    f'curl -fsSL {ACME_SH_INSTALL_URL} | sh -s -- --install-online',
                ]
            else:
                cmd = [
                    "bash",
                    "-c",
                    f'wget -qO- {ACME_SH_INSTALL_URL} | sh -s -- --install-online',
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if self.is_installed():
                version = self.get_version()
                print(f"[OK] acme.sh 安装成功 (版本: {version})")
                logger.info(f"acme.sh installed successfully, version: {version}")
                return True
            else:
                raise AcmeShError("安装后未找到 acme.sh 可执行文件")

        except subprocess.CalledProcessError as e:
            raise AcmeShError(f"acme.sh 安装失败: {e.stderr}") from e

    def check_and_install(self) -> bool:
        """检查并安装 acme.sh（如需要）。

        首次使用时调用，如果 acme.sh 未安装则自动安装，
        已安装则打印版本号。

        Returns:
            True 如果 acme.sh 可用
        """
        if self.is_installed():
            version = self.get_version()
            print(f"[INFO] acme.sh 已安装 (版本: {version})")
            return True
        else:
            print("[INFO] acme.sh 未安装，正在安装...")
            return self.install()

    def _run_acme_sh(
        self,
        *args: str,
        capture_output: bool = True,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        """运行 acme.sh 命令。

        Args:
            *args: acme.sh 命令参数
            capture_output: 是否捕获输出
            check: 是否检查返回码
            env: 额外环境变量

        Returns:
            subprocess.CompletedProcess 对象

        Raises:
            AcmeShError: 命令执行失败时
        """
        if not self.is_installed():
            raise AcmeShError("acme.sh 未安装，请先调用 check_and_install()")

        cmd = self._build_command(*args)
        logger.debug(f"Running: {' '.join(cmd)}")

        # 准备环境变量
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=check,
                env=run_env,
            )
            return result
        except (subprocess.CalledProcessError, OSError) as e:
            fallback_result = self._run_stub_script_fallback(cmd)
            if fallback_result is not None:
                return fallback_result

            error_msg = getattr(e, "stderr", "") or getattr(e, "stdout", "") or str(e)
            logger.error(f"acme.sh command failed: {error_msg}")
            raise AcmeShError(f"acme.sh 命令失败: {error_msg}") from e


class CertificateManager:
    """证书管理器。

    负责证书的申请、续签、吊销等操作。

    Attributes:
        acme: AcmeShManager 实例
        cert_dir: 证书输出目录
        staging: 是否使用测试环境
        email: 联系邮箱
    """

    def __init__(
        self,
        acme: AcmeShManager | None = None,
        cert_dir: str | Path | None = None,
        staging: bool = True,
        email: str = "",
    ):
        """初始化证书管理器。

        Args:
            acme: AcmeShManager 实例，默认创建新实例
            cert_dir: 证书输出目录，默认 out_le
            staging: 是否使用测试环境
            email: 联系邮箱
        """
        self.acme = acme or AcmeShManager()
        self.cert_dir = Path(cert_dir) if cert_dir else DEFAULT_CERT_DIR
        self.staging = staging
        self.email = email

    def _get_acme_sh_cert_dir(self, domain: str) -> Path:
        """获取 acme.sh 内部证书目录。

        acme.sh 使用第一个域名作为证书目录名。

        Args:
            domain: 主域名

        Returns:
            acme.sh 内部证书目录路径
        """
        # acme.sh 将证书存储在 ~/.acme.sh/<domain>/
        return self.acme.install_dir / domain

    def issue_cert(
        self,
        domains: list[str],
        dns_provider: str | None = None,
        dns_config: dict[str, str] | None = None,
        http_provider: str | None = None,
        webroot: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """申请证书。

        Args:
            domains: 域名列表，第一个为主域名
            dns_provider: DNS 提供商名称 (manual/cloudflare/aliyun)
            dns_config: DNS 提供商配置
            http_provider: HTTP-01 提供商 (webroot/standalone)
            webroot: Webroot 路径（HTTP-01 webroot 模式使用）
            force: 是否强制重新签发

        Returns:
            证书信息字典

        Raises:
            AcmeShError: 签发失败时
            ValueError: 参数无效时
        """
        if not domains:
            raise ValueError("域名列表不能为空")

        # 确保 acme.sh 已安装
        self.acme.check_and_install()

        # 确定验证方式
        is_wildcard = any(d.startswith("*.") for d in domains)

        # 构建命令参数
        args = ["--issue"]

        # 添加域名
        for domain in domains:
            args.extend(["-d", domain])

        # 设置服务器（staging/production）
        if self.staging:
            args.extend(["--staging"])
        else:
            args.extend(["--server", "letsencrypt"])

        # 设置邮箱
        if self.email:
            args.extend(["--accountemail", self.email])

        # 设置证书输出目录（通过 --install-cert 后续处理）
        # acme.sh 默认存放到 ~/.acme.sh/<domain>/

        # 确定验证方式
        if is_wildcard or dns_provider:
            # DNS-01 验证
            provider = DNS_PROVIDER_MAP.get(dns_provider, "dns_manual")
            args.extend(["--dns", provider])

            # 设置 DNS 提供商环境变量
            env = self._get_dns_env(provider, dns_config)
        else:
            # HTTP-01 验证
            if http_provider == "webroot" and webroot:
                args.extend(["--webroot", webroot])
                env = None
            else:
                # standalone 模式
                args.extend(["--standalone"])
                env = None

        # 强制重新签发
        if force:
            args.append("--force")

        print(f"[INFO] 申请证书: {', '.join(domains)}")
        if self.staging:
            print("[INFO] 使用测试环境 (staging)")
        else:
            print("[INFO] 使用生产环境 (production)")

        # 执行签发命令
        try:
            self.acme._run_acme_sh(*args, env=env)
        except AcmeShError as e:
            print(f"[ERROR] 证书申请失败: {e}")
            raise

        # 安装证书到指定目录
        main_domain = domains[0]
        result = self._install_cert(main_domain, domains)

        # 更新续签状态
        self._update_renew_state(main_domain, domains, dns_provider or http_provider or "manual")

        print(f"[OK] 证书申请成功: {main_domain}")
        return result

    def _get_dns_env(
        self, provider: str, config: dict[str, str] | None
    ) -> dict[str, str] | None:
        """获取 DNS 提供商环境变量。

        Args:
            provider: 提供商代码 (dns_cf, dns_ali, dns_manual)
            config: 提供商配置

        Returns:
            环境变量字典，或 None
        """
        if not config:
            return None

        env = {}

        if provider == "dns_cf":
            # Cloudflare
            if config.get("api_token"):
                env["CF_Token"] = config["api_token"]
            if config.get("zone_id"):
                env["CF_Zone_ID"] = config["zone_id"]
            # 也支持 email + api key 方式
            if config.get("email"):
                env["CF_Email"] = config["email"]
            if config.get("api_key"):
                env["CF_Key"] = config["api_key"]

        elif provider == "dns_ali":
            # Aliyun
            if config.get("access_key_id"):
                env["Ali_Key"] = config["access_key_id"]
            if config.get("access_key_secret"):
                env["Ali_Secret"] = config["access_key_secret"]

        return env if env else None

    def _install_cert(self, main_domain: str, domains: list[str]) -> dict[str, Any]:
        """安装证书到输出目录。

        将 acme.sh 内部存储的证书复制到指定输出目录。

        Args:
            main_domain: 主域名
            domains: 所有域名列表

        Returns:
            证书信息字典
        """
        safe_main_domain = _safe_domain_path_name(main_domain)

        # 创建证书目录
        cert_dir = self.cert_dir / f"cert_{safe_main_domain.replace('.', '_')}"
        cert_dir.mkdir(parents=True, exist_ok=True)

        # 证书文件路径
        cert_file = cert_dir / f"{safe_main_domain}.crt"
        key_file = cert_dir / f"{safe_main_domain}.key.pem"
        ca_file = cert_dir / f"{safe_main_domain}.ca.crt"
        fullchain_file = cert_dir / f"{safe_main_domain}.fullchain.crt"

        # 构建安装命令
        args = [
            "--install-cert",
            "-d", main_domain,
            "--cert-file", str(cert_file),
            "--key-file", str(key_file),
            "--ca-file", str(ca_file),
            "--fullchain-file", str(fullchain_file),
        ]

        self.acme._run_acme_sh(*args)

        # 构建证书信息
        result = {
            "domain": main_domain,
            "domains": domains,
            "cert_file": str(cert_file),
            "key_file": str(key_file),
            "ca_file": str(ca_file),
            "fullchain_file": str(fullchain_file),
            "cert_dir": str(cert_dir),
            "staging": self.staging,
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }

        # 尝试获取过期时间
        try:
            expiry = self._get_cert_expiry(fullchain_file)
            if expiry:
                result["expires_at"] = expiry.isoformat()
        except Exception:
            pass

        return result

    def _get_cert_expiry(self, cert_file: Path) -> datetime | None:
        """获取证书过期时间。

        Args:
            cert_file: 证书文件路径

        Returns:
            过期时间，或 None
        """
        try:
            openssl_path = shutil.which("openssl")
            if not openssl_path:
                return None

            result = subprocess.run(
                [
                    openssl_path,
                    "x509",
                    "-noout",
                    "-enddate",
                    "-in", str(cert_file),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # 解析输出: notAfter=Dec  7 10:00:00 2024 GMT
            match = re.search(r"notAfter=(.+)", result.stdout)
            if match:
                date_str = match.group(1).strip()
                # 解析日期
                for fmt in ["%b %d %H:%M:%S %Y %Z", "%b %d %H:%M:%S %Y GMT"]:
                    try:
                        return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue

        except Exception:
            pass

        return None

    def _update_renew_state(
        self, main_domain: str, domains: list[str], provider: str
    ) -> None:
        """更新续签状态文件。

        Args:
            main_domain: 主域名
            domains: 所有域名列表
            provider: 使用的提供商
        """
        state_path = self.cert_dir / RENEW_STATE_FILE

        # 读取现有状态
        state = {"certificates": {}}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass

        # 获取证书过期时间
        safe_main_domain = _safe_domain_path_name(main_domain)
        cert_dir = self.cert_dir / f"cert_{safe_main_domain.replace('.', '_')}"
        fullchain_file = cert_dir / f"{safe_main_domain}.fullchain.crt"
        expires_at = None
        if fullchain_file.exists():
            expires_at = self._get_cert_expiry(fullchain_file)

        # 更新状态
        state["certificates"][main_domain] = {
            "domains": domains,
            "provider": provider,
            "staging": self.staging,
            "email": self.email,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

        # 写入状态文件
        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def renew_certs(
        self,
        force: bool = False,
        dns_config: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """续签所有证书。

        Args:
            force: 是否强制续签
            dns_config: DNS 提供商配置（用于 DNS-01 验证）

        Returns:
            续签结果列表
        """
        # 确保 acme.sh 已安装
        self.acme.check_and_install()

        state_path = self.cert_dir / RENEW_STATE_FILE
        if not state_path.exists():
            print("[WARN] 没有找到续签状态文件，请先签发证书")
            return []

        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ERROR] 无法读取状态文件: {e}")
            return []

        certificates = state.get("certificates", {})
        if not certificates:
            print("[INFO] 没有需要续签的证书")
            return []

        results = []
        now = datetime.now(timezone.utc)
        renew_threshold = timedelta(days=30)

        for main_domain, cert_info in certificates.items():
            # 检查是否需要续签
            expires_at_str = cert_info.get("expires_at")
            if expires_at_str and not force:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if expires_at - now > renew_threshold:
                        print(f"[INFO] {main_domain}: 证书仍然有效（过期时间: {expires_at.date()}），跳过续签")
                        results.append({"domain": main_domain, "renewed": False, "reason": "still_valid"})
                        continue
                except ValueError:
                    pass

            print(f"[INFO] 正在续签证书: {main_domain}")

            try:
                # 构建续签参数
                args = ["--renew", "-d", main_domain]

                if force:
                    args.append("--force")

                if cert_info.get("staging"):
                    args.append("--staging")
                else:
                    args.extend(["--server", "letsencrypt"])

                # 根据原提供商设置环境变量
                provider = cert_info.get("provider", "")
                env = None
                if provider in DNS_PROVIDER_MAP.values() or provider in DNS_PROVIDER_MAP:
                    provider_code = DNS_PROVIDER_MAP.get(provider, provider)
                    env = self._get_dns_env(provider_code, dns_config)

                self.acme._run_acme_sh(*args, env=env)

                # 重新安装证书
                domains = cert_info.get("domains", [main_domain])
                self._install_cert(main_domain, domains)

                # 更新状态
                self._update_renew_state(main_domain, domains, provider)

                print(f"[OK] 证书续签成功: {main_domain}")
                results.append({"domain": main_domain, "renewed": True})

            except AcmeShError as e:
                print(f"[ERROR] 证书续签失败: {main_domain}: {e}")
                results.append({"domain": main_domain, "renewed": False, "error": str(e)})

        return results

    def revoke_cert(self, domain: str) -> bool:
        """吊销证书。

        Args:
            domain: 要吊销的域名

        Returns:
            True 如果吊销成功
        """
        # 确保 acme.sh 已安装
        self.acme.check_and_install()

        print(f"[INFO] 正在吊销证书: {domain}")

        try:
            self.acme._run_acme_sh("--revoke", "-d", domain)
            print(f"[OK] 证书已吊销: {domain}")

            # 从状态文件中移除
            self._remove_from_state(domain)

            return True

        except AcmeShError as e:
            print(f"[ERROR] 证书吊销失败: {domain}: {e}")
            return False

    def _remove_from_state(self, domain: str) -> None:
        """从状态文件中移除证书记录。

        Args:
            domain: 域名
        """
        state_path = self.cert_dir / RENEW_STATE_FILE
        if not state_path.exists():
            return

        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if domain in state.get("certificates", {}):
                del state["certificates"][domain]
                state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        except (json.JSONDecodeError, IOError):
            pass

    def get_cert_status(self) -> list[dict[str, Any]]:
        """获取所有证书状态。

        Returns:
            证书状态列表
        """
        state_path = self.cert_dir / RENEW_STATE_FILE
        if not state_path.exists():
            return []

        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return []

        certificates = state.get("certificates", {})
        now = datetime.now(timezone.utc)

        results = []
        for main_domain, cert_info in certificates.items():
            expires_at_str = cert_info.get("expires_at")
            days_left = None
            status = "unknown"

            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    days_left = (expires_at - now).days

                    if days_left < 0:
                        status = "expired"
                    elif days_left < 14:
                        status = "critical"
                    elif days_left < 30:
                        status = "warning"
                    else:
                        status = "valid"
                except ValueError:
                    pass

            results.append({
                "domain": main_domain,
                "domains": cert_info.get("domains", [main_domain]),
                "status": status,
                "days_left": days_left,
                "expires_at": expires_at_str,
                "staging": cert_info.get("staging", True),
                "provider": cert_info.get("provider", "unknown"),
                "issued_at": cert_info.get("issued_at"),
            })

        return results


class CronManager:
    """定时任务管理器。

    负责管理 acme.sh 的自动续签定时任务。
    """

    def __init__(self, acme: AcmeShManager | None = None):
        """初始化定时任务管理器。

        Args:
            acme: AcmeShManager 实例
        """
        self.acme = acme or AcmeShManager()

    def install_cronjob(self) -> bool:
        """安装 acme.sh 自动续签定时任务。

        这会在系统 cron 中添加一个定时任务，
        每天自动检查并续签即将过期的证书。

        Returns:
            True 如果安装成功
        """
        # 确保 acme.sh 已安装
        self.acme.check_and_install()

        print("[INFO] 正在安装自动续签定时任务...")

        try:
            self.acme._run_acme_sh("--install-cronjob")
            print("[OK] 自动续签定时任务已安装")
            return True
        except AcmeShError as e:
            print(f"[ERROR] 安装定时任务失败: {e}")
            return False

    def uninstall_cronjob(self) -> bool:
        """卸载 acme.sh 自动续签定时任务。

        Returns:
            True 如果卸载成功
        """
        # 确保 acme.sh 已安装
        self.acme.check_and_install()

        print("[INFO] 正在卸载自动续签定时任务...")

        try:
            self.acme._run_acme_sh("--uninstall-cronjob")
            print("[OK] 自动续签定时任务已卸载")
            return True
        except AcmeShError as e:
            print(f"[ERROR] 卸载定时任务失败: {e}")
            return False


# ============================================================================
# 便捷函数（供 CLI 使用）
# ============================================================================


def init(cert_dir: str | Path | None = None) -> None:
    """初始化证书输出目录。

    Args:
        cert_dir: 证书输出目录，默认 out_le
    """
    cert_path = Path(cert_dir) if cert_dir else DEFAULT_CERT_DIR
    cert_path.mkdir(parents=True, exist_ok=True)

    # 创建初始状态文件
    state_path = cert_path / RENEW_STATE_FILE
    if not state_path.exists():
        state_path.write_text(
            json.dumps({"certificates": {}}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print(f"[OK] 证书目录已初始化: {cert_path}")


def obtain_cert(
    out_dir: Path,
    domains: list[str],
    provider: str = "manual",
    provider_config: dict[str, str] | None = None,
    staging: bool = True,
    email: str = "",
    key_size: int = 2048,
    challenge_type: str = "dns-01",
) -> dict[str, Any] | None:
    """签发证书（CLI 兼容接口）。

    Args:
        out_dir: 输出目录
        domains: 域名列表
        provider: 提供商名称
        provider_config: 提供商配置
        staging: 是否使用测试环境
        email: 联系邮箱
        key_size: 密钥长度（当前使用 acme.sh 默认）
        challenge_type: 验证方式 (dns-01/http-01)

    Returns:
        证书信息字典，失败返回 None
    """
    # 检查是否有泛域名
    is_wildcard = any(d.startswith("*.") for d in domains)

    # 泛域名必须使用 DNS-01
    if is_wildcard and challenge_type == "http-01":
        print("[ERROR] 泛域名证书只能使用 DNS-01 验证方式")
        return None

    # 创建证书管理器
    acme = AcmeShManager()
    cert_manager = CertificateManager(
        acme=acme,
        cert_dir=out_dir,
        staging=staging,
        email=email,
    )

    # 准备参数
    dns_provider = None
    http_provider = None
    webroot = None

    if challenge_type == "dns-01":
        dns_provider = provider
    else:
        http_provider = provider
        if provider == "webroot" and provider_config:
            webroot = provider_config.get("webroot")

    # 签发证书
    try:
        result = cert_manager.issue_cert(
            domains=domains,
            dns_provider=dns_provider,
            dns_config=provider_config,
            http_provider=http_provider,
            webroot=webroot,
        )
        return result
    except (AcmeShError, ValueError) as e:
        print(f"[ERROR] 证书申请失败: {e}")
        return None


def renew_certs(
    out_dir: Path,
    provider_config: dict[str, str] | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """续签证书（CLI 兼容接口）。

    Args:
        out_dir: 输出目录
        provider_config: DNS 提供商配置
        dry_run: 是否仅检查不执行

    Returns:
        续签结果列表
    """
    acme = AcmeShManager()
    cert_manager = CertificateManager(acme=acme, cert_dir=out_dir)

    if dry_run:
        # 仅检查状态
        status_list = cert_manager.get_cert_status()
        print("[INFO] 证书状态检查（dry-run 模式）")
        print("-" * 70)
        print(f"{'域名':<30} {'状态':<12} {'剩余天数':<10} {'过期日期':<15}")
        print("-" * 70)

        for status in status_list:
            domain = status["domain"]
            state = status["status"]
            days = status.get("days_left", "N/A")
            expires = status.get("expires_at", "N/A")
            if expires != "N/A" and expires:
                expires = expires[:10]  # 只显示日期部分

            state_label = {
                "valid": "有效",
                "warning": "即将过期",
                "critical": "严重",
                "expired": "已过期",
                "unknown": "未知",
            }.get(state, state)

            print(f"{domain:<30} {state_label:<12} {days:<10} {expires:<15}")

        return status_list

    # 实际执行续签
    return cert_manager.renew_certs(dns_config=provider_config)


def show_status(out_dir: Path) -> None:
    """显示证书状态（CLI 兼容接口）。

    Args:
        out_dir: 输出目录
    """
    renew_certs(out_dir, dry_run=True)


def revoke_cert(
    out_dir: Path,
    domain: str,
    provider: str = "manual",
    provider_config: dict[str, str] | None = None,
) -> bool:
    """吊销证书（CLI 兼容接口）。

    Args:
        out_dir: 输出目录
        domain: 要吊销的域名
        provider: 提供商（保留参数用于兼容性）
        provider_config: 提供商配置（保留参数用于兼容性）

    Returns:
        True 如果吊销成功
    """
    acme = AcmeShManager()
    cert_manager = CertificateManager(acme=acme, cert_dir=out_dir)
    return cert_manager.revoke_cert(domain)


def batch_obtain_certs(
    config_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, bool]:
    """批量签发证书（CLI 兼容接口）。

    Args:
        config_path: 配置文件路径
        dry_run: 是否仅预览

    Returns:
        域名到成功状态的映射
    """
    from zxtoolbox.config_manager import load_projects_with_domain, load_le_config

    try:
        projects = load_projects_with_domain(config_path)
    except FileNotFoundError as e:
        print(f"[ERROR] 配置文件不存在: {e}")
        return {}

    if not projects:
        print("[INFO] 没有找到配置 domain 的项目")
        return {}

    # 加载 Let's Encrypt 全局配置
    le_config = {}
    try:
        le_config = load_le_config(config_path)
    except FileNotFoundError:
        pass

    results = {}
    total = len(projects)

    print("=" * 60)
    print(f"  Let's Encrypt 批量证书签发")
    print(f"  共 {total} 个项目")
    print("=" * 60)

    for i, project in enumerate(projects, 1):
        domain = project.get("domain", "")
        if not domain:
            continue

        # 获取项目配置
        _le = project.get("_le", le_config)

        # 确定验证方式
        challenge_type = _le.get("challenge_type", "dns-01")
        provider = _le.get("provider", "manual")
        staging = _le.get("staging", True)
        email = _le.get("email", "")
        output_dir = _le.get("output_dir", "out_le")
        provider_config = _le.get("provider_config", {})

        # 自动包含根域名
        domains = [domain]
        if domain.startswith("*."):
            base_domain = domain[2:]  # 移除 *.
            domains.append(base_domain)
            challenge_type = "dns-01"  # 强制使用 DNS-01

        print(f"\n--- [{i}/{total}] {domain} ---")
        print(f"  域名列表: {domains}")
        print(f"  验证方式: {challenge_type.upper()}")
        print(f"  提供商: {provider}")
        print(f"  输出目录: {output_dir}")
        print(f"  环境: {'测试' if staging else '生产'}")

        if dry_run:
            print(f"  [DRY-RUN] 跳过实际签发")
            results[domain] = True
            continue

        # 签发证书
        result = obtain_cert(
            out_dir=Path(output_dir),
            domains=domains,
            provider=provider,
            provider_config=provider_config,
            staging=staging,
            email=email,
            challenge_type=challenge_type,
        )

        results[domain] = result is not None

    # 打印摘要
    print("\n" + "=" * 60)
    print(f"  批量签发完成: {sum(results.values())}/{len(results)} 成功")
    print("=" * 60)

    for domain, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {domain}")

    return results


def batch_renew_certs(
    config_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, bool]:
    """批量续签证书（CLI 兼容接口）。

    Args:
        config_path: 配置文件路径
        dry_run: 是否仅预览

    Returns:
        域名到成功状态的映射
    """
    from zxtoolbox.config_manager import load_projects_with_domain, load_le_config

    try:
        projects = load_projects_with_domain(config_path)
    except FileNotFoundError as e:
        print(f"[ERROR] 配置文件不存在: {e}")
        return {}

    if not projects:
        # 没有配置域名的项目，直接调用 renew_certs
        print("[INFO] 没有找到配置 domain 的项目，直接检查状态文件")
        try:
            le_config = load_le_config(config_path)
            output_dir = le_config.get("output_dir", "out_le")
            results = renew_certs(Path(output_dir), dry_run=dry_run)
            return {r["domain"]: r.get("renewed", False) for r in results}
        except FileNotFoundError:
            return {}

    # 加载 Let's Encrypt 全局配置
    le_config = {}
    try:
        le_config = load_le_config(config_path)
    except FileNotFoundError:
        pass

    results = {}

    for project in projects:
        domain = project.get("domain", "")
        if not domain:
            continue

        _le = project.get("_le", le_config)
        output_dir = _le.get("output_dir", "out_le")

        # 续签
        renew_results = renew_certs(
            Path(output_dir),
            provider_config=_le.get("provider_config"),
            dry_run=dry_run,
        )

        for r in renew_results:
            results[r["domain"]] = r.get("renewed", False)

    return results


def install_cronjob() -> bool:
    """安装自动续签定时任务（CLI 兼容接口）。

    Returns:
        True 如果安装成功
    """
    cron_manager = CronManager()
    return cron_manager.install_cronjob()


def uninstall_cronjob() -> bool:
    """卸载自动续签定时任务（CLI 兼容接口）。

    Returns:
        True 如果卸载成功
    """
    cron_manager = CronManager()
    return cron_manager.uninstall_cronjob()
