"""zxtoolbox.letsencrypt - Let's Encrypt ACME v2 证书签发模块

参考 https://github.com/acmesh-official/acme.sh 实现。

功能：
- 通过 ACME v2 协议从 Let's Encrypt 获取证书
- 支持 DNS-01 验证（唯一支持泛域名 *.example.com 的方式）
- 支持 HTTP-01 验证（适用于普通二级域名，无需 DNS 操作）
- 支持多域名和泛二级域名混合签发
- 可插拔 DNS 提供商接口（手动 / Cloudflare / 阿里云）
- 可插拔 HTTP-01 验证方式（webroot / standalone）
- 证书到期自动检测和续签
- 定期执行支持（cron / systemd timer）

ACME v2 协议流程：
1. 获取 Directory（服务端点列表）
2. 注册/加载 ACME 账户
3. 创建订单（newOrder），提交 CSR
4. 对每个域名完成验证（DNS-01 或 HTTP-01）
5. 完成订单（finalize），获取证书
6. 下载证书链并保存到本地

验证方式对比：
- DNS-01：支持泛域名 (*.example.com)，需要 DNS 提供商 API 或手动操作
- HTTP-01：仅支持普通域名，需要在 Web 服务器放置验证文件或启动临时服务器
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import urllib
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ============================================================
# 可选依赖导入
# ============================================================

try:
    import josepy as jose
    from acme import challenges as acme_challenges
    from acme import errors as acme_errors
    from acme import messages
    from acme.client import ClientNetwork, ClientV2
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, rsa
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )
    from cryptography.x509.oid import NameOID
    import requests
    import OpenSSL

    _HAS_ACME = True
except ImportError:
    _HAS_ACME = False
    jose = None
    acme_challenges = None
    acme_errors = None
    messages = None
    ClientNetwork = None
    ClientV2 = None
    x509 = None
    default_backend = None
    hashes = None
    ec = None
    rsa = None
    serialization = None
    PrivateFormat = None
    Encoding = None
    NoEncryption = None
    NameOID = None
    requests = None
    OpenSSL = None

logger = logging.getLogger("zxtoolbox.letsencrypt")

# ============================================================
# 常量
# ============================================================

STAGING_URL = "https://acme-staging-v02.api.letsencrypt.org/directory"
PRODUCTION_URL = "https://acme-v02.api.letsencrypt.org/directory"
DEFAULT_EMAIL = ""
DNS_POLL_INTERVAL = 5
DNS_POLL_MAX = 60
CHALLENGE_POLL_INTERVAL = 3
CHALLENGE_POLL_MAX = 30
DNS_PROPAGATION_WAIT = 10
RENEW_DAYS_BEFORE = 30

# ============================================================
# DNS-01 提供商接口
# ============================================================


class DNSProvider:
    """DNS-01 验证提供商基类。

    所有 DNS 提供商必须实现 add_txt_record 和 del_txt_record 方法。
    ACME 协议要求在每个待验证域名的 _acme-challenge.<domain> 下
    添加一条 TXT 记录，记录值为 key authorization 的 SHA-256 摘要。
    """

    name = "base"

    def add_txt_record(self, domain: str, record_name: str, record_value: str) -> None:
        """在 DNS 中添加一条 TXT 记录。

        Args:
            domain: 原始域名（如 example.com）
            record_name: 完整记录名（如 _acme-challenge.example.com）
            record_value: TXT 记录值（key authorization 的 SHA-256 摘要）
        """
        raise NotImplementedError

    def del_txt_record(self, domain: str, record_name: str, record_value: str) -> None:
        """删除之前添加的 TXT 记录。

        验证完成后调用，用于清理 DNS 记录。
        """
        raise NotImplementedError


class ManualProvider(DNSProvider):
    """手动 DNS 提供商。

    提示用户在 DNS 控制面板中手动添加 TXT 记录，
    等待用户确认后再继续验证流程。
    适用于不支持 API 的 DNS 提供商或一次性使用场景。
    """

    name = "manual"

    def add_txt_record(self, domain: str, record_name: str, record_value: str) -> None:
        print()
        print("=" * 60)
        print("  DNS-01 验证 - 请手动添加 DNS TXT 记录")
        print("=" * 60)
        print(f"  记录类型:  TXT")
        print(f"  记录名称:  {record_name}")
        print(f"  记录值:    {record_value}")
        print()
        print("  请在你的 DNS 控制面板中添加上述 TXT 记录，")
        print(f"  并等待 DNS 生效（通常需要 1-5 分钟）。")
        print("=" * 60)
        print()
        input("  添加完成后按 Enter 继续...")

    def del_txt_record(self, domain: str, record_name: str, record_value: str) -> None:
        print(f"  提示: 验证已完成，你可以手动删除 TXT 记录: {record_name}")


class CloudflareProvider(DNSProvider):
    """Cloudflare DNS 提供商。

    通过 Cloudflare API v4 自动管理 DNS TXT 记录。
    需要 API Token（权限：Zone > DNS > Edit）。

    provider_config 必须包含：
        api_token: Cloudflare API Token
        zone_id:   Cloudflare Zone ID（可在域名 Overview 页面找到）
    """

    name = "cloudflare"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._token = (config or {}).get("api_token", "")
        self._zone_id = (config or {}).get("zone_id", "")
        self._created_record_ids: List[str] = []

        if not self._token or not self._zone_id:
            raise ValueError(
                "CloudflareProvider 需要 api_token 和 zone_id 配置。\n"
                '示例: --provider-config \'{"api_token":"xxx","zone_id":"yyy"}\''
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def add_txt_record(self, domain: str, record_name: str, record_value: str) -> None:
        url = f"https://api.cloudflare.com/client/v4/zones/{self._zone_id}/dns_records"
        payload = {
            "type": "TXT",
            "name": record_name,
            "content": record_value,
            "ttl": 120,
        }
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Cloudflare API 错误: {data.get('errors', data)}")
        record_id = data["result"]["id"]
        self._created_record_ids.append(record_id)
        logger.info("Cloudflare TXT 记录已添加: %s -> %s", record_name, record_value)

    def del_txt_record(self, domain: str, record_name: str, record_value: str) -> None:
        for record_id in list(self._created_record_ids):
            url = f"https://api.cloudflare.com/client/v4/zones/{self._zone_id}/dns_records/{record_id}"
            try:
                resp = requests.delete(url, headers=self._headers(), timeout=30)
                resp.raise_for_status()
                logger.info("Cloudflare TXT 记录已删除: %s", record_name)
            except Exception as e:
                logger.warning("Cloudflare TXT 记录清理失败: %s - %s", record_name, e)
        self._created_record_ids.clear()


class AliyunProvider(DNSProvider):
    """阿里云 DNS（云解析 DNS）提供商。

    通过阿里云 OpenAPI 自动管理 DNS TXT 记录。
    需要 AccessKey ID 和 AccessKey Secret。

    provider_config 必须包含：
        access_key_id:     阿里云 AccessKey ID
        access_key_secret: 阿里云 AccessKey Secret
    """

    name = "aliyun"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._access_key_id = (config or {}).get("access_key_id", "")
        self._access_key_secret = (config or {}).get("access_key_secret", "")
        self._created_records: List[Dict[str, str]] = []

        if not self._access_key_id or not self._access_key_secret:
            raise ValueError(
                "AliyunProvider 需要 access_key_id 和 access_key_secret 配置。\n"
                '示例: --provider-config \'{"access_key_id":"xxx","access_key_secret":"yyy"}\''
            )

    def _sign_request(self, params: Dict[str, str]) -> Dict[str, str]:
        """对阿里云 API 请求进行签名（HMAC-SHA1）。"""
        import hmac
        import hashlib
        import urllib.parse

        sorted_params = sorted(params.items())
        query_string = urllib.parse.urlencode(sorted_params)
        string_to_sign = f"GET&%2F&{urllib.parse.quote(query_string, safe='')}"
        key = (self._access_key_secret + "&").encode("utf-8")
        signature = hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha1).digest()
        signature_b64 = base64.b64encode(signature).decode("utf-8")
        params["Signature"] = signature_b64
        return params

    def _api_call(self, action: str, params: Dict[str, str]) -> Dict[str, Any]:
        """调用阿里云 DNS API。"""
        import uuid
        from datetime import datetime as _dt

        base_params = {
            "AccessKeyId": self._access_key_id,
            "Action": action,
            "Format": "JSON",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid4()),
            "SignatureVersion": "1.0",
            "Timestamp": _dt.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Version": "2015-01-09",
        }
        base_params.update(params)
        signed_params = self._sign_request(base_params)
        url = "https://alidns.aliyuncs.com/?" + urllib.parse.urlencode(signed_params)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def add_txt_record(self, domain: str, record_name: str, record_value: str) -> None:
        """添加 DNS TXT 记录。

        阿里云要求 RR（记录名前缀）和 Domain（主域名）分开。
        例如 _acme-challenge.example.com → RR=_acme-challenge, Domain=example.com
        """
        import urllib.parse

        rr, main_domain = self._split_rr_domain(record_name, domain)
        result = self._api_call(
            "AddDomainRecord",
            {
                "DomainName": main_domain,
                "RR": rr,
                "Type": "TXT",
                "Value": record_value,
                "TTL": "600",
            },
        )
        if "RecordId" in result:
            self._created_records.append(
                {
                    "record_id": result["RecordId"],
                    "domain": main_domain,
                    "rr": rr,
                }
            )
            logger.info("阿里云 TXT 记录已添加: %s -> %s", record_name, record_value)
        else:
            raise RuntimeError(f"阿里云 API 错误: {result}")

    def del_txt_record(self, domain: str, record_name: str, record_value: str) -> None:
        for rec in list(self._created_records):
            try:
                self._api_call(
                    "DeleteDomainRecord",
                    {
                        "RecordId": rec["record_id"],
                    },
                )
                logger.info("阿里云 TXT 记录已删除: %s", record_name)
            except Exception as e:
                logger.warning("阿里云 TXT 记录清理失败: %s - %s", record_name, e)
        self._created_records.clear()

    @staticmethod
    def _split_rr_domain(record_name: str, domain: str) -> tuple:
        """从完整记录名中分离 RR 和主域名。

        例如: _acme-challenge.example.com, example.com
        → RR="_acme-challenge", Domain="example.com"

        泛域名: _acme-challenge.*.example.com, example.com
        → RR="_acme-challenge.*", Domain="example.com"
        """
        suffix = f".{domain}"
        if record_name.endswith(suffix):
            rr = record_name[: -len(suffix)]
        else:
            rr = record_name.replace(f".{domain}", "")
        return rr, domain


# ============================================================
# 提供商工厂
# ============================================================

_PROVIDER_MAP: Dict[str, type[DNSProvider]] = {
    "manual": ManualProvider,
    "cloudflare": CloudflareProvider,
    "aliyun": AliyunProvider,
}


def get_provider(name: str, config: Optional[Dict[str, Any]] = None) -> DNSProvider:
    """根据名称获取 DNS 提供商实例。"""
    cls = _PROVIDER_MAP.get(name.lower())
    if cls is None:
        raise ValueError(
            f"不支持的 DNS 提供商: {name}。支持的: {list(_PROVIDER_MAP.keys())}"
        )
    # ManualProvider doesn't accept config in __init__
    if name.lower() == "manual":
        return cls()
    return cls(config)


# ============================================================
# HTTP-01 验证提供商接口
# ============================================================


class HTTP01Provider:
    """HTTP-01 验证提供商基类。

    所有 HTTP-01 提供商必须实现 setup_challenge 和 cleanup_challenge 方法。
    ACME 协议要求在待验证域名的
    http://<domain>/.well-known/acme-challenge/<token>
    路径下提供 key authorization 文件。
    """

    name = "base"

    def setup_challenge(
        self, domain: str, token: str, key_authorization: str
    ) -> None:
        """设置 HTTP-01 验证资源。

        在验证开始前调用，用于准备验证文件或启动服务器。

        Args:
            domain: 待验证的域名
            token: ACME 挑战 token
            key_authorization: key authorization 字符串（token.thumbprint）
        """
        raise NotImplementedError

    def cleanup_challenge(
        self, domain: str, token: str, key_authorization: str
    ) -> None:
        """清理 HTTP-01 验证资源。

        验证完成后调用，用于删除验证文件或停止服务器。
        """
        raise NotImplementedError


class WebrootProvider(HTTP01Provider):
    """Webroot HTTP-01 验证提供商。

    将验证文件写入 Web 服务器的根目录下的
    .well-known/acme-challenge/ 路径中。
    适用于已有 Web 服务器（如 Nginx、Apache）运行的场景。

    provider_config 必须包含：
        webroot: Web 服务器根目录路径
            例如: /var/www/html 或 /usr/share/nginx/html
    """

    name = "webroot"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._webroot = (config or {}).get("webroot", "")
        self._written_files: List[Path] = []

        if not self._webroot:
            raise ValueError(
                "WebrootProvider 需要 webroot 配置。\n"
                '示例: --provider-config \'{"webroot":"/var/www/html"}\''
            )

        self._webroot_path = Path(self._webroot)

    def setup_challenge(
        self, domain: str, token: str, key_authorization: str
    ) -> None:
        """将验证文件写入 webroot 目录。"""
        challenge_dir = self._webroot_path / ".well-known" / "acme-challenge"
        challenge_dir.mkdir(parents=True, exist_ok=True)

        challenge_file = challenge_dir / token
        challenge_file.write_text(key_authorization, encoding="utf-8")
        self._written_files.append(challenge_file)

        logger.info(
            "HTTP-01 验证文件已写入: %s (域名: %s)",
            challenge_file,
            domain,
        )

    def cleanup_challenge(
        self, domain: str, token: str, key_authorization: str
    ) -> None:
        """删除验证文件。"""
        challenge_dir = self._webroot_path / ".well-known" / "acme-challenge"

        for challenge_file in list(self._written_files):
            try:
                if challenge_file.exists():
                    challenge_file.unlink()
                    logger.info("已删除验证文件: %s", challenge_file)
            except Exception as e:
                logger.warning("删除验证文件失败: %s - %s", challenge_file, e)
        self._written_files.clear()

        # 尝试清理 .well-known/acme-challenge 目录（如果为空）
        try:
            if challenge_dir.exists() and not any(challenge_dir.iterdir()):
                challenge_dir.rmdir()
                acme_dir = challenge_dir.parent
                if not any(acme_dir.iterdir()):
                    acme_dir.rmdir()
        except Exception:
            pass


class StandaloneProvider(HTTP01Provider):
    """独立服务器 HTTP-01 验证提供商。

    启动一个临时 HTTP 服务器监听 80 端口，自动响应 ACME 验证请求。
    适用于没有 Web 服务器的场景（需要 80 端口可用）。

    provider_config 可选包含：
        port: 监听端口（默认 80）
        bind_addr: 绑定地址（默认 0.0.0.0）
    """

    name = "standalone"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        config = config or {}
        self._port = config.get("port", 80)
        self._bind_addr = config.get("bind_addr", "0.0.0.0")
        self._server: Any = None
        self._resources: set = set()

    def setup_challenge(
        self, domain: str, token: str, key_authorization: str
    ) -> None:
        """准备验证资源（不启动服务器，start_server 时启动）。"""
        # 资源会在 _start_http01_server 中使用
        logger.info(
            "HTTP-01 standalone 验证准备: 域名=%s, 端口=%d",
            domain,
            self._port,
        )

    def cleanup_challenge(
        self, domain: str, token: str, key_authorization: str
    ) -> None:
        """停止服务器。"""
        self._stop_server()

    def start_server(self, resources: set) -> None:
        """启动 HTTP-01 服务器。

        Args:
            resources: HTTP01RequestHandler.HTTP01Resource 集合
        """
        if not _HAS_ACME:
            raise RuntimeError("缺少 acme 库依赖")

        from acme import standalone as acme_standalone

        self._resources = resources
        logger.info("启动 HTTP-01 服务器: %s:%d", self._bind_addr, self._port)
        try:
            self._server = acme_standalone.HTTP01Server(
                (self._bind_addr, self._port), resources
            )
        except OSError as e:
            if "bind" in str(e).lower() or "10048" in str(e) or "98" in str(e):
                raise RuntimeError(
                    f"无法绑定端口 {self._port}，请确保该端口未被占用。\n"
                    f"错误详情: {e}"
                ) from e
            raise

    def _stop_server(self) -> None:
        """停止 HTTP-01 服务器。"""
        if self._server is not None:
            logger.info("停止 HTTP-01 服务器")
            self._server.shutdown()
            self._server = None


# ============================================================
# HTTP-01 提供商工厂
# ============================================================

_HTTP01_PROVIDER_MAP: Dict[str, type[HTTP01Provider]] = {
    "webroot": WebrootProvider,
    "standalone": StandaloneProvider,
}


def get_http01_provider(
    name: str, config: Optional[Dict[str, Any]] = None
) -> HTTP01Provider:
    """根据名称获取 HTTP-01 验证提供商实例。"""
    cls = _HTTP01_PROVIDER_MAP.get(name.lower())
    if cls is None:
        raise ValueError(
            f"不支持的 HTTP-01 提供商: {name}。"
            f"支持的: {list(_HTTP01_PROVIDER_MAP.keys())}"
        )
    return cls(config)


# ============================================================
# 密钥和 CSR 生成
# ============================================================


def _generate_account_key(key_size: int = 2048) -> rsa.RSAPrivateKey:
    """生成 ACME 账户 RSA 私钥。

    账户密钥用于与 ACME 服务器通信时进行 JWS 签名。
    建议至少 2048 位，可重复使用于所有证书操作。
    """
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )


def _generate_cert_key(key_size: int = 2048) -> rsa.RSAPrivateKey:
    """生成证书 RSA 私钥。

    每个证书使用独立的私钥，与账户密钥分离。
    """
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )


def _save_pem_key(key, path: Path) -> None:
    """将私钥保存为 PEM 格式文件。"""
    pem = key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=NoEncryption(),
    )
    path.write_bytes(pem)


def _load_pem_key(path: Path):
    """从 PEM 文件加载私钥。"""
    data = path.read_bytes()
    return serialization.load_pem_private_key(
        data, password=None, backend=default_backend()
    )


def _build_csr(domains: List[str], private_key) -> bytes:
    """构建包含所有域名的 CSR（证书签名请求）。

    使用 SAN（Subject Alternative Name）扩展支持多域名。
    第一个域名作为 Common Name，其余全部放入 SAN。

    Args:
        domains: 域名列表，如 ["example.com", "*.example.com", "www.example.com"]
        private_key: 证书私钥

    Returns:
        CSR 的 PEM 编码字节
    """
    san = x509.SubjectAlternativeName([x509.DNSName(d) for d in domains])
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(
            x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, domains[0]),
                ]
            )
        )
        .add_extension(san, critical=False)
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    return csr.public_bytes(Encoding.PEM)


# ============================================================
# DNS-01 验证核心逻辑
# ============================================================


def _compute_dns01_validation(key_auth: str) -> str:
    """计算 DNS-01 验证值。

    根据 ACME 协议 RFC 8555，DNS-01 验证值是 key authorization
    的 SHA-256 摘要的 base64url 编码。

    key_authorization = token + "." + base64url(sha256(account_public_key))
    dns_validation = base64url(sha256(key_authorization))

    Args:
        key_auth: 完整的 key authorization 字符串

    Returns:
        用于 DNS TXT 记录的验证值
    """
    digest = hashlib.sha256(key_auth.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")


def _wait_for_dns_propagation(
    record_name: str,
    expected_value: str,
    max_attempts: int = DNS_POLL_MAX,
    interval: int = DNS_POLL_INTERVAL,
) -> bool:
    """等待 DNS TXT 记录全局生效。

    通过反复查询 DNS 来确认记录已传播到公共 DNS 服务器。
    使用 Google Public DNS (8.8.8.8) 作为查询源。

    Args:
        record_name: 完整记录名（如 _acme-challenge.example.com）
        expected_value: 期望的 TXT 记录值
        max_attempts: 最大尝试次数
        interval: 每次尝试间隔（秒）

    Returns:
        True 如果记录已生效，False 如果超时
    """
    import subprocess

    for attempt in range(1, max_attempts + 1):
        try:
            result = subprocess.run(
                ["nslookup", "-type=TXT", record_name, "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if expected_value in result.stdout:
                logger.info(
                    "DNS 记录已生效: %s (尝试 %d/%d)",
                    record_name,
                    attempt,
                    max_attempts,
                )
                return True
        except Exception:
            pass
        if attempt < max_attempts:
            time.sleep(interval)
    return False


# ============================================================
# ACME v2 客户端封装
# ============================================================


class ACMEClient:
    """ACME v2 协议客户端封装。

    封装了完整的 ACME v2 流程：
    1. 账户注册/加载
    2. 订单创建
    3. DNS-01 挑战验证
    4. 证书签发和下载

    使用 certbot 的 acme 库作为底层实现。
    """

    def __init__(self, directory_url: str, account_key_path: Path) -> None:
        """初始化 ACME 客户端。

        Args:
            directory_url: ACME 服务器 Directory URL
                - 测试环境: https://acme-staging-v02.api.letsencrypt.org/directory
                - 生产环境: https://acme-v02.api.letsencrypt.org/directory
            account_key_path: 账户私钥文件路径
        """
        self.directory_url = directory_url
        self.account_key_path = account_key_path
        self.client: Optional[ClientV2] = None
        self.account_key = None
        self.account_jwk = None
        self.registration = None

    def setup_account(self, email: str = "") -> None:
        """设置 ACME 账户。

        加载已有账户密钥或生成新密钥，然后注册到 ACME 服务器。
        如果账户已存在（ConflictError），则加载现有账户信息。

        Args:
            email: 联系邮箱，用于接收证书到期通知
        """
        # 加载或生成账户私钥
        if self.account_key_path.exists():
            self.account_key = _load_pem_key(self.account_key_path)
            logger.info("已加载现有账户密钥: %s", self.account_key_path)
        else:
            self.account_key = _generate_account_key()
            _save_pem_key(self.account_key, self.account_key_path)
            logger.info("已生成新账户密钥: %s", self.account_key_path)

        # 转换为 JWK 格式（acme 库要求）
        self.account_jwk = jose.JWKRSA(key=self.account_key)

        # 创建网络客户端（处理 JWS 签名和 nonce）
        net = ClientNetwork(self.account_jwk, alg=jose.RS256)

        # 获取 Directory（服务端点列表）
        directory = messages.Directory.from_json(
            requests.get(self.directory_url, timeout=30).json()
        )

        # 创建 ACME v2 客户端
        self.client = ClientV2(directory, net)

        # 注册账户
        try:
            self.registration = self.client.new_account(
                messages.NewRegistration.from_data(
                    contact=[f"mailto:{email}"] if email else [],
                    terms_of_service_agreed=True,
                )
            )
            logger.info("ACME 账户注册成功: %s", self.registration.uri)
        except acme_errors.ConflictError:
            # 账户已存在，通过 only_return_existing 查询现有账户
            logger.info("ACME 账户已存在，正在加载...")
            temp_regr = messages.RegistrationResource(
                body=messages.Registration.from_data(
                    contact=[f"mailto:{email}"] if email else [],
                    only_return_existing=True,
                ),
                uri="",
            )
            self.registration = self.client.query_registration(temp_regr)
            logger.info("ACME 账户已加载: %s", self.registration.uri)

        # 保存账户信息
        account_info = {
            "uri": self.registration.uri,
            "email": email,
            "directory_url": self.directory_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        account_json_path = self.account_key_path.parent / "account.json"
        account_json_path.write_text(
            json.dumps(account_info, indent=2, ensure_ascii=False)
        )

    def obtain_certificate(
        self,
        domains: List[str],
        cert_key_path: Path,
        challenge_type: str = "dns-01",
        dns_provider: Optional[DNSProvider] = None,
        http01_provider: Optional[HTTP01Provider] = None,
    ) -> Dict[str, bytes]:
        """获取证书。

        完整的 ACME v2 证书获取流程：
        1. 生成证书私钥和 CSR
        2. 创建订单（newOrder）
        3. 对每个授权完成验证（DNS-01 或 HTTP-01）
        4. 完成订单并下载证书

        Args:
            domains: 要包含在证书中的域名列表
            cert_key_path: 证书私钥保存路径
            challenge_type: 验证方式 ("dns-01" 或 "http-01")
            dns_provider: DNS-01 验证提供商（challenge_type 为 dns-01 时必填）
            http01_provider: HTTP-01 验证提供商（challenge_type 为 http-01 时必填）

        Returns:
            包含以下键的字典：
                - cert_pem: 服务器证书（PEM 格式）
                - chain_pem: 中间证书链（PEM 格式）
                - fullchain_pem: 完整证书链（服务器 + 中间证书）
                - cert_key_pem: 证书私钥（PEM 格式）

        Raises:
            ValueError: 验证方式不支持或对应提供商缺失
            RuntimeError: 验证失败
        """
        # 验证参数
        if challenge_type == "dns-01":
            if dns_provider is None:
                raise ValueError("DNS-01 验证方式需要提供 dns_provider")
        elif challenge_type == "http-01":
            if http01_provider is None:
                raise ValueError("HTTP-01 验证方式需要提供 http01_provider")
        else:
            raise ValueError(
                f"不支持的验证方式: {challenge_type}。"
                f"支持: dns-01, http-01"
            )

        # 步骤 1: 生成证书私钥
        cert_key = _generate_cert_key()
        _save_pem_key(cert_key, cert_key_path)
        cert_key_pem = cert_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=NoEncryption(),
        )

        # 步骤 2: 构建 CSR
        csr_pem = _build_csr(domains, cert_key)
        logger.info("CSR 已生成，包含 %d 个域名: %s", len(domains), domains)

        # 步骤 3: 创建订单
        order = self.client.new_order(csr_pem)
        logger.info("订单已创建: %s", order.uri)

        # 用于追踪需要清理的资源
        cleanup_tasks: List[Dict[str, Any]] = []

        try:
            # 步骤 4: 对每个授权完成验证
            for authz in order.authorizations:
                domain = authz.body.identifier.value
                logger.info(
                    "处理域名授权: %s (验证方式: %s)", domain, challenge_type
                )

                if challenge_type == "dns-01":
                    assert dns_provider is not None
                    self._fulfill_dns01_challenge(
                        authz, domain, dns_provider
                    )
                elif challenge_type == "http-01":
                    assert http01_provider is not None
                    self._fulfill_http01_challenge(
                        authz, domain, http01_provider, cleanup_tasks
                    )

            # 步骤 5: 完成订单，获取证书
            logger.info("所有域名验证通过，正在完成订单...")
            deadline = datetime.now(timezone.utc) + timedelta(seconds=90)

            try:
                finalized_order = self.client.finalize_order(order, deadline)
            except Exception as e:
                logger.error("订单完成失败: %s", e)
                raise

        finally:
            # 清理验证资源
            self._cleanup_challenges(challenge_type, cleanup_tasks, dns_provider)

        # 提取证书数据
        fullchain_pem = finalized_order.fullchain_pem.encode("utf-8")

        # 分离服务器证书和证书链
        # fullchain 格式: [服务器证书]\n[中间证书]\n
        pem_marker = b"-----END CERTIFICATE-----\n-----BEGIN CERTIFICATE-----"
        if pem_marker in fullchain_pem:
            parts = fullchain_pem.split(pem_marker, 1)
            cert_pem = parts[0] + b"-----END CERTIFICATE-----\n"
            chain_pem = b"-----BEGIN CERTIFICATE-----\n" + parts[1]
        else:
            # 只有一个证书（不应该发生）
            cert_pem = fullchain_pem
            chain_pem = b""

        logger.info("证书获取成功")

        return {
            "cert_pem": cert_pem,
            "chain_pem": chain_pem,
            "fullchain_pem": fullchain_pem,
            "cert_key_pem": cert_key_pem,
        }

    def _fulfill_dns01_challenge(
        self,
        authz: Any,
        domain: str,
        dns_provider: DNSProvider,
    ) -> None:
        """完成 DNS-01 验证。

        Args:
            authz: ACME 授权对象
            domain: 待验证域名
            dns_provider: DNS 提供商实例
        """
        # 从授权的挑战列表中找到 DNS-01 挑战
        dns_challenge = None
        for chall_body in authz.body.challenges:
            if isinstance(chall_body.chall, acme_challenges.DNS01):
                dns_challenge = chall_body
                break

        if dns_challenge is None:
            raise RuntimeError(
                f"域名 {domain} 的授权不包含 DNS-01 挑战。"
                f"可用挑战类型: {[cb.chall.typ for cb in authz.body.challenges]}"
            )

        # 计算验证值
        key_auth = dns_challenge.chall.key_authorization(self.account_jwk)
        validation = _compute_dns01_validation(key_auth)

        # DNS-01 要求记录名为 _acme-challenge.<domain>
        # 泛域名 *.example.com 的记录名也是 _acme-challenge.example.com（去掉 *.）
        clean_domain = domain.lstrip("*.")
        record_name = f"_acme-challenge.{clean_domain}"

        logger.info("DNS-01 挑战: 域名=%s, 记录=%s", domain, record_name)

        # 添加 DNS TXT 记录
        try:
            dns_provider.add_txt_record(clean_domain, record_name, validation)
        except Exception as e:
            logger.error("添加 DNS TXT 记录失败: %s", e)
            raise

        # 等待 DNS 传播
        logger.info("等待 DNS 传播 (%d 秒)...", DNS_PROPAGATION_WAIT)
        time.sleep(DNS_PROPAGATION_WAIT)

        # 可选：验证 DNS 记录已生效
        if _wait_for_dns_propagation(record_name, validation):
            logger.info("DNS 记录已确认生效")
        else:
            logger.warning("DNS 记录可能尚未完全传播，继续尝试验证...")

        # 通知 ACME 服务器验证挑战
        response = dns_challenge.chall.response(self.account_jwk)
        self.client.answer_challenge(dns_challenge, response)
        logger.info("已提交 DNS-01 挑战响应")

        # 轮询等待验证完成
        self._poll_authorization(authz, domain, "DNS-01")

        # 清理 DNS 记录
        try:
            dns_provider.del_txt_record(clean_domain, record_name, validation)
        except Exception as e:
            logger.warning("DNS 记录清理失败: %s", e)

    def _fulfill_http01_challenge(
        self,
        authz: Any,
        domain: str,
        http01_provider: HTTP01Provider,
        cleanup_tasks: List[Dict[str, Any]],
    ) -> None:
        """完成 HTTP-01 验证。

        Args:
            authz: ACME 授权对象
            domain: 待验证域名
            http01_provider: HTTP-01 提供商实例
            cleanup_tasks: 清理任务列表（用于 finally 清理）
        """
        # 从授权的挑战列表中找到 HTTP-01 挑战
        http_challenge = None
        for chall_body in authz.body.challenges:
            if isinstance(chall_body.chall, acme_challenges.HTTP01):
                http_challenge = chall_body
                break

        if http_challenge is None:
            raise RuntimeError(
                f"域名 {domain} 的授权不包含 HTTP-01 挑战。"
                f"可用挑战类型: {[cb.chall.typ for cb in authz.body.challenges]}"
            )

        # 计算 key authorization（HTTP-01 直接使用，不做哈希）
        key_auth = http_challenge.chall.key_authorization(self.account_jwk)
        token = http_challenge.chall.encode("token")

        logger.info(
            "HTTP-01 挑战: 域名=%s, 路径=/.well-known/acme-challenge/%s",
            domain,
            token,
        )

        # 设置验证资源
        if isinstance(http01_provider, StandaloneProvider):
            # Standalone 模式：启动临时 HTTP 服务器
            from acme import standalone as acme_standalone

            response, validation = http_challenge.chall.response_and_validation(
                self.account_jwk
            )
            resource = acme_standalone.HTTP01RequestHandler.HTTP01Resource(
                chall=http_challenge.chall,
                response=response,
                validation=validation,
            )
            http01_provider.start_server({resource})
            logger.info("HTTP-01 standalone 服务器已启动")
        else:
            # Webroot 模式：写入验证文件
            http01_provider.setup_challenge(domain, token, key_auth)

        # 记录清理任务
        cleanup_tasks.append({
            "type": "http-01",
            "domain": domain,
            "token": token,
            "key_auth": key_auth,
            "provider": http01_provider,
        })

        # 通知 ACME 服务器验证挑战
        response = http_challenge.chall.response(self.account_jwk)
        self.client.answer_challenge(http_challenge, response)
        logger.info("已提交 HTTP-01 挑战响应")

        # 轮询等待验证完成
        self._poll_authorization(authz, domain, "HTTP-01")

        # 清理验证资源
        try:
            http01_provider.cleanup_challenge(domain, token, key_auth)
        except Exception as e:
            logger.warning("HTTP-01 资源清理失败: %s", e)

    def _poll_authorization(
        self, authz: Any, domain: str, challenge_label: str
    ) -> None:
        """轮询等待 ACME 授权验证完成。

        Args:
            authz: ACME 授权对象
            domain: 域名
            challenge_label: 挑战类型标签（用于日志）
        """
        validated = False
        for attempt in range(1, CHALLENGE_POLL_MAX + 1):
            updated_authz, _ = self.client.poll(authz)
            status = updated_authz.body.status
            logger.info(
                "  域名 %s 验证状态: %s (尝试 %d/%d)",
                domain,
                status,
                attempt,
                CHALLENGE_POLL_MAX,
            )

            if status == "valid":
                validated = True
                break
            elif status == "invalid":
                # 获取错误详情
                for chall in updated_authz.body.challenges:
                    if chall.error:
                        logger.error("  验证失败详情: %s", chall.error)
                raise RuntimeError(f"{challenge_label} 验证失败: {domain}")
            elif status == "pending":
                time.sleep(CHALLENGE_POLL_INTERVAL)
            else:
                raise RuntimeError(f"未知的验证状态: {status}")

        if not validated:
            raise RuntimeError(f"{challenge_label} 验证超时: {domain}")

    def _cleanup_challenges(
        self,
        challenge_type: str,
        cleanup_tasks: List[Dict[str, Any]],
        dns_provider: Optional[DNSProvider] = None,
    ) -> None:
        """清理验证资源（失败时的安全网）。

        在异常发生时确保资源被清理。
        """
        for task in cleanup_tasks:
            try:
                if task["type"] == "http-01":
                    provider = task["provider"]
                    provider.cleanup_challenge(
                        task["domain"], task["token"], task["key_auth"]
                    )
            except Exception as e:
                logger.warning("资源清理失败: %s", e)


# ============================================================
# 公共 API
# ============================================================


def init(out_dir: Path) -> None:
    """初始化 Let's Encrypt 输出目录结构。

    创建必要的子目录和初始状态文件。
    """
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 初始化续签状态文件
    state_path = out_dir / "renew_state.json"
    if not state_path.exists():
        state_path.write_text(
            json.dumps({"certificates": {}}, indent=2, ensure_ascii=False)
        )

    logger.info("LE 输出目录已初始化: %s", out_dir)
    print(f"输出目录已初始化: {out_dir}")


def obtain_cert(
    out_dir: Path,
    domains: List[str],
    provider: str = "manual",
    provider_config: Optional[Dict[str, Any]] = None,
    staging: bool = True,
    email: str = DEFAULT_EMAIL,
    key_size: int = 2048,
    challenge_type: str = "dns-01",
) -> None:
    """从 Let's Encrypt 获取证书。

    这是 CLI 调用的主要入口函数。执行完整的 ACME v2 流程：
    账户注册 → 订单创建 → 验证（DNS-01 或 HTTP-01） → 证书签发 → 保存输出。

    Args:
        out_dir: 证书输出目录
        domains: 域名列表，支持泛域名
            示例: ["example.com", "*.example.com", "www.example.com"]
        provider: 验证提供商名称
            DNS-01: "manual", "cloudflare", "aliyun"
            HTTP-01: "webroot", "standalone"
        provider_config: 提供商配置字典
            DNS-01 (cloudflare): {"api_token": "...", "zone_id": "..."}
            DNS-01 (aliyun): {"access_key_id": "...", "access_key_secret": "..."}
            HTTP-01 (webroot): {"webroot": "/var/www/html"}
            HTTP-01 (standalone): {"port": 80, "bind_addr": "0.0.0.0"}
        staging: 是否使用测试服务器（默认 True，避免触及生产环境速率限制）
        email: 联系邮箱，用于接收证书到期通知
        key_size: RSA 密钥长度（2048 或 4096）
        challenge_type: 验证方式
            "dns-01": DNS 验证，支持泛域名（默认）
            "http-01": HTTP 验证，适用于普通二级域名，无需 DNS 操作

    输出文件结构:
        out_dir/
        ├── account.key              # ACME 账户私钥
        ├── account.json             # 账户注册信息
        ├── renew_state.json         # 续签状态跟踪
        └── <domain_label>/
            ├── <domain>.crt         # 服务器证书
            ├── <domain>.chain.crt   # 中间证书链
            ├── <domain>.bundle.crt  # 完整证书链（服务器 + 中间 + 根）
            ├── <domain>.fullchain.crt  # 服务器 + 中间（用于 nginx ssl_certificate）
            └── <domain>.key.pem     # 证书私钥

    Raises:
        ValueError: 验证方式不支持或泛域名使用了 HTTP-01
    """
    if not _HAS_ACME:
        print("错误: 缺少 acme 库依赖。请运行以下命令安装:")
        print("  uv add acme cryptography requests pyOpenSSL josepy")
        print()
        print("或者使用自签证书模块: zxtool --ssl --domain example.dev")
        return

    # 泛域名只能使用 DNS-01 验证
    has_wildcard = any(d.startswith("*.") for d in domains)
    if has_wildcard and challenge_type == "http-01":
        raise ValueError(
            "泛域名证书只能使用 DNS-01 验证方式。"
            f"以下域名包含通配符: {[d for d in domains if d.startswith('*.')]}\n"
            "请使用 --challenge dns-01 替代。"
        )

    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 域名标签用于目录名（将 *.example.com 转为 cert__example_com）
    primary = domains[0]
    domain_label = primary.replace("*.", "").replace(".", "_")
    cert_dir = out_dir / f"cert_{domain_label}"
    cert_dir.mkdir(parents=True, exist_ok=True)

    directory_url = STAGING_URL if staging else PRODUCTION_URL
    env_label = "测试环境 (staging)" if staging else "生产环境 (production)"
    challenge_label = "DNS-01" if challenge_type == "dns-01" else "HTTP-01"

    print()
    print("=" * 60)
    print(f"  Let's Encrypt 证书签发")
    print(f"  环境: {env_label}")
    print(f"  域名: {', '.join(domains)}")
    print(f"  验证方式: {challenge_label}")
    print(f"  提供商: {provider}")
    print(f"  输出目录: {cert_dir}")
    print("=" * 60)
    print()

    # 根据验证方式获取提供商
    dns_provider: Optional[DNSProvider] = None
    http01_provider: Optional[HTTP01Provider] = None

    if challenge_type == "dns-01":
        dns_provider = get_provider(provider, provider_config)
    elif challenge_type == "http-01":
        http01_provider = get_http01_provider(provider, provider_config)
    else:
        raise ValueError(
            f"不支持的验证方式: {challenge_type}。支持: dns-01, http-01"
        )

    # 创建 ACME 客户端
    account_key_path = out_dir / "account.key"
    client = ACMEClient(directory_url, account_key_path)

    # 注册/加载账户
    print("步骤 1/4: 注册 ACME 账户...")
    client.setup_account(email)

    # 获取证书
    print(f"步骤 2/4: 创建订单并提交 CSR...")
    print(f"步骤 3/4: 完成 {challenge_label} 验证...")
    cert_key_path = cert_dir / f"{primary}.key.pem"
    result = client.obtain_certificate(
        domains=domains,
        cert_key_path=cert_key_path,
        challenge_type=challenge_type,
        dns_provider=dns_provider,
        http01_provider=http01_provider,
    )

    # 保存证书文件
    print("步骤 4/4: 保存证书文件...")

    cert_path = cert_dir / f"{primary}.crt"
    chain_path = cert_dir / f"{primary}.chain.crt"
    bundle_path = cert_dir / f"{primary}.bundle.crt"
    fullchain_path = cert_dir / f"{primary}.fullchain.crt"

    cert_path.write_bytes(result["cert_pem"])
    chain_path.write_bytes(result["chain_pem"])
    bundle_path.write_bytes(result["fullchain_pem"])
    fullchain_path.write_bytes(result["fullchain_pem"])

    # 更新续签状态
    _update_renew_state(out_dir, primary, domains, provider, staging, challenge_type=challenge_type)

    # 输出结果
    print()
    print("=" * 60)
    print("  证书签发成功!")
    print("=" * 60)
    print()
    print(f"  服务器证书:  {cert_path}")
    print(f"  证书链:      {chain_path}")
    print(f"  完整证书链:  {bundle_path}")
    print(f"  nginx 配置:  {fullchain_path}")
    print(f"  私钥:        {cert_key_path}")
    print()
    print("  nginx 配置示例:")
    print(f"    ssl_certificate     {fullchain_path};")
    print(f"    ssl_certificate_key {cert_key_path};")
    print()
    if staging:
        print("  注意: 当前使用的是测试环境证书。")
        print("  如需生产环境证书，请添加 --production 参数。")
    print("=" * 60)


def renew_certs(
    out_dir: Path,
    provider_config: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
) -> None:
    """检查并续签即将到期的证书。

    读取 renew_state.json 中跟踪的所有证书，检查哪些将在
    RENEW_DAYS_BEFORE（默认 30）天内到期，然后自动续签。

    此函数设计为定期执行（cron / systemd timer）。

    Args:
        out_dir: 证书输出目录
        provider_config: DNS 提供商配置（用于自动续签）
        dry_run: 仅检查不执行实际续签

    使用示例（crontab）:
        # 每天凌晨 3 点检查并续签
        0 3 * * * cd /path/to/project && uv run python -c "from zxtoolbox.letsencrypt import renew_certs; renew_certs(Path('out_le'), provider_config={'api_token': 'xxx', 'zone_id': 'yyy'})"
    """
    out_dir = Path(out_dir).resolve()
    state_path = out_dir / "renew_state.json"

    if not state_path.exists():
        print(f"续签状态文件不存在: {state_path}")
        print("请先使用 obtain_cert 获取证书。")
        return

    state = json.loads(state_path.read_text())
    certs = state.get("certificates", {})

    if not certs:
        print("没有需要续签的证书。")
        return

    now = datetime.now(timezone.utc)
    renewed = 0
    skipped = 0

    for label, info in certs.items():
        expires_str = info.get("expires_at", "")
        if not expires_str:
            continue

        try:
            expires_at = datetime.fromisoformat(expires_str)
        except ValueError:
            logger.warning("无法解析过期时间: %s", expires_str)
            continue

        days_left = (expires_at - now).days

        print(
            f"  {label}: 剩余 {days_left} 天 (过期: {expires_at.strftime('%Y-%m-%d')})"
        )

        if days_left > RENEW_DAYS_BEFORE:
            skipped += 1
            continue

        if dry_run:
            print(f"    → 需要续签 (dry-run 模式，跳过)")
            continue

        print(f"    → 正在续签...")
        domains = info.get("domains", [label])
        provider = info.get("provider", "manual")
        staging = info.get("staging", True)

        try:
            obtain_cert(
                out_dir=out_dir,
                domains=domains,
                provider=provider,
                provider_config=provider_config,
                staging=staging,
            )
            renewed += 1
        except Exception as e:
            logger.error("续签失败 [%s]: %s", label, e)
            print(f"    → 续签失败: {e}")

    print()
    if dry_run:
        print(f"检查完成: {skipped} 个证书无需续签。")
    else:
        print(f"续签完成: {renewed} 个证书已续签, {skipped} 个证书无需续签。")


def show_status(out_dir: Path) -> None:
    """显示证书状态和续签信息。

    列出所有已签发的证书、域名、过期时间和续签状态。
    """
    out_dir = Path(out_dir).resolve()
    state_path = out_dir / "renew_state.json"

    if not state_path.exists():
        print("没有证书状态信息。请先使用 obtain_cert 获取证书。")
        return

    state = json.loads(state_path.read_text())
    certs = state.get("certificates", {})

    if not certs:
        print("没有已签发的证书。")
        return

    now = datetime.now(timezone.utc)

    print()
    print(f"{'域名':<30} {'状态':<10} {'剩余天数':<10} {'过期日期':<12} {'环境'}")
    print("-" * 75)

    for label, info in certs.items():
        domains = info.get("domains", [])
        expires_str = info.get("expires_at", "")
        env = "staging" if info.get("staging") else "production"

        if expires_str:
            try:
                expires_at = datetime.fromisoformat(expires_str)
                days_left = (expires_at - now).days
                status = "即将过期" if days_left <= RENEW_DAYS_BEFORE else "有效"
                expires_display = expires_at.strftime("%Y-%m-%d")
            except ValueError:
                days_left = -1
                status = "未知"
                expires_display = "未知"
        else:
            days_left = -1
            status = "未知"
            expires_display = "未知"

        domain_display = domains[0] if domains else label
        print(
            f"{domain_display:<30} {status:<10} {days_left:<10} {expires_display:<12} {env}"
        )

    print()


def revoke_cert(
    out_dir: Path,
    domain: str,
    provider: str = "manual",
    provider_config: Optional[Dict[str, Any]] = None,
) -> None:
    """吊销已签发的证书。

    当私钥泄露或不再需要某个证书时，可以主动吊销。
    吊销后浏览器将不再信任该证书。

    Args:
        out_dir: 证书输出目录
        domain: 要吊销的证书主域名
        provider: DNS 提供商名称
        provider_config: DNS 提供商配置
    """
    if not _HAS_ACME:
        print("错误: 缺少 acme 库依赖。")
        return

    out_dir = Path(out_dir).resolve()
    account_key_path = out_dir / "account.key"

    if not account_key_path.exists():
        print(f"账户密钥不存在: {account_key_path}")
        return

    # 读取证书文件
    domain_label = domain.replace("*.", "").replace(".", "_")
    cert_dir = out_dir / f"cert_{domain_label}"
    cert_path = cert_dir / f"{domain}.crt"

    if not cert_path.exists():
        print(f"证书文件不存在: {cert_path}")
        return

    cert_pem = cert_path.read_bytes()

    # 加载账户密钥
    account_key = _load_pem_key(account_key_path)
    account_jwk = jose.JWKRSA(key=account_key)

    # 读取账户信息获取 directory URL
    account_json_path = out_dir / "account.json"
    if account_json_path.exists():
        account_info = json.loads(account_json_path.read_text())
        directory_url = account_info.get("directory_url", PRODUCTION_URL)
    else:
        directory_url = PRODUCTION_URL

    # 创建客户端
    net = ClientNetwork(account_jwk, alg=jose.RS256)
    directory = messages.Directory.from_json(
        requests.get(directory_url, timeout=30).json()
    )
    client = ClientV2(directory, net)

    # 加载证书
    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_pem)

    # 吊销证书（reason=0 表示未指定原因）
    client.revoke(jose.ComparableX509(cert), 0)

    print(f"证书已吊销: {domain}")
    print(f"证书路径: {cert_path}")


def _update_renew_state(
    out_dir: Path,
    primary_domain: str,
    domains: List[str],
    provider: str,
    staging: bool,
    challenge_type: str = "dns-01",
) -> None:
    """更新续签状态文件。

    记录每次证书签发的信息，用于后续自动续签判断。
    Let's Encrypt 证书有效期为 90 天。
    """
    state_path = out_dir / "renew_state.json"

    if state_path.exists():
        state = json.loads(state_path.read_text())
    else:
        state = {"certificates": {}}

    if "certificates" not in state:
        state["certificates"] = {}

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=90)  # Let's Encrypt 证书有效期 90 天

    state["certificates"][primary_domain] = {
        "domains": domains,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "provider": provider,
        "staging": staging,
        "challenge_type": challenge_type,
    }

    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    logger.info(
        "续签状态已更新: %s (过期: %s)", primary_domain, expires_at.strftime("%Y-%m-%d")
    )


# ============================================================
# 配置驱动的批量操作
# ============================================================


def batch_obtain_certs(
    config_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, bool]:
    """根据配置文件批量签发证书。

    读取 zxtool.toml 中 [[projects]] 的 domain 字段和 [letsencrypt] 全局配置，
    为每个配置了 domain 的项目自动签发 Let's Encrypt 证书。

    对于泛域名（如 *.example.com），会自动将基础域名一同包含在证书中。
    例如 domain = "*.example.com" 会签发包含 ["*.example.com", "example.com"] 的证书。

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。
        dry_run: 仅打印计划，不实际执行。

    Returns:
        每个域名的签发结果 {domain: success}
    """
    from zxtoolbox.config_manager import load_projects_with_domain

    projects = load_projects_with_domain(config_path)

    if not projects:
        print("[INFO] 配置文件中没有配置 domain 的项目。")
        print("提示: 在 [[projects]] 中添加 domain 字段，例如:")
        print('  domain = "example.com"')
        print('  domain = "*.example.com"')
        return {}

    print()
    print("=" * 60)
    print("  Let's Encrypt 批量证书签发")
    print(f"  共 {len(projects)} 个项目需要签发证书")
    print("=" * 60)
    print()

    results: dict[str, bool] = {}

    for i, proj in enumerate(projects, 1):
        domain = proj["domain"]
        le_config = proj["_le"]

        # 对于泛域名，自动添加基础域名
        if domain.startswith("*."):
            domain_list = [domain, domain[2:]]  # *.example.com -> [*.example.com, example.com]
        else:
            domain_list = [domain]

        provider = le_config["provider"]
        provider_config = le_config.get("provider_config", {})
        out_dir = Path(le_config["output_dir"]).resolve()
        staging = le_config.get("staging", True)
        email = le_config.get("email", "")
        challenge_type = le_config.get("challenge_type", "dns-01")
        # 泛域名强制使用 DNS-01
        if domain.startswith("*.") and challenge_type == "http-01":
            challenge_type = "dns-01"
            logger.info("泛域名 %s 强制使用 DNS-01 验证", domain)

        # 根据验证方式选择提供商名称标签
        challenge_label = "DNS-01" if challenge_type == "dns-01" else "HTTP-01"

        print(f"--- [{i}/{len(projects)}] {domain} ---")
        print(f"  域名列表: {domain_list}")
        print(f"  验证方式: {challenge_label}")
        print(f"  提供商: {provider}")
        print(f"  输出目录: {out_dir}")
        print(f"  环境: {'测试' if staging else '生产'}")
        if email:
            print(f"  邮箱: {email}")

        if dry_run:
            print(f"  [DRY-RUN] 跳过证书签发")
            results[domain] = True
            print()
            continue

        try:
            obtain_cert(
                out_dir=out_dir,
                domains=domain_list,
                provider=provider,
                provider_config=provider_config if provider_config else None,
                staging=staging,
                email=email,
                challenge_type=challenge_type,
            )
            results[domain] = True
        except Exception as e:
            logger.error("证书签发失败 [%s]: %s", domain, e)
            print(f"  [ERROR] 证书签发失败: {e}")
            results[domain] = False

        print()

    # 汇总
    success_count = sum(1 for v in results.values() if v)
    print("=" * 60)
    print(f"  批量签发完成: {success_count}/{len(projects)} 成功")
    print("=" * 60)

    for domain_result, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {domain_result}")
    print()

    return results


def batch_renew_certs(
    config_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, bool]:
    """根据配置文件批量续签即将到期的证书。

    读取 zxtool.toml 中 [letsencrypt] 和 [[projects]] 的 domain 配置，
    对每个配置了 domain 的项目检查证书到期时间并自动续签。

    续签逻辑：
    1. 读取全局 [letsencrypt] 配置获取 output_dir 和 DNS 提供商信息
    2. 对每个有 domain 的项目，检查 renew_state.json 中的证书状态
    3. 如果证书即将到期（默认 30 天内）或不存在，则执行续签

    Args:
        config_path: 配置文件路径，默认为 ~/.config/zxtool.toml。
        dry_run: 仅检查，不执行续签。

    Returns:
        每个域名的续签结果 {domain: success}
    """
    from zxtoolbox.config_manager import load_projects_with_domain, load_le_config

    le_config = load_le_config(config_path)
    out_dir = Path(le_config["output_dir"]).resolve()
    provider = le_config["provider"]
    provider_config = le_config.get("provider_config", {})
    staging = le_config.get("staging", True)
    email = le_config.get("email", "")
    challenge_type = le_config.get("challenge_type", "dns-01")

    projects = load_projects_with_domain(config_path)

    if not projects:
        # 即使没有项目配置了 domain，也检查已有证书的续签
        print("[INFO] 配置文件中没有配置 domain 的项目。")
        print("尝试从已有 renew_state.json 检查续签...")
        renew_certs(
            out_dir=out_dir,
            provider_config=provider_config if provider_config else None,
            dry_run=dry_run,
        )
        return {}

    print()
    print("=" * 60)
    print("  Let's Encrypt 批量证书续签")
    print("=" * 60)
    print()

    results: dict[str, bool] = {}

    for i, proj in enumerate(projects, 1):
        domain = proj["domain"]

        # 对于泛域名，自动添加基础域名
        if domain.startswith("*."):
            domain_list = [domain, domain[2:]]
        else:
            domain_list = [domain]

        # 检查续签状态
        state_path = out_dir / "renew_state.json"
        needs_renew = True  # 默认需要签发（可能首次）

        if state_path.exists():
            state = json.loads(state_path.read_text())
            certs = state.get("certificates", {})
            cert_info = certs.get(domain)

            if cert_info:
                expires_str = cert_info.get("expires_at", "")
                if expires_str:
                    try:
                        expires_at = datetime.fromisoformat(expires_str)
                        days_left = (expires_at - datetime.now(timezone.utc)).days
                        print(f"  [{i}/{len(projects)}] {domain}: 剩余 {days_left} 天")

                        if days_left > RENEW_DAYS_BEFORE:
                            print(f"    → 证书有效，无需续签")
                            needs_renew = False
                            results[domain] = True
                            continue
                        else:
                            print(f"    → 证书即将过期，需要续签")
                    except ValueError:
                        print(f"  [{i}/{len(projects)}] {domain}: 无法解析过期时间，将重新签发")

        if not needs_renew:
            continue

        if dry_run:
            print(f"  [{i}/{len(projects)}] {domain}: 需要签发/续签 (dry-run，跳过)")
            results[domain] = True
            continue

        # 泛域名强制使用 DNS-01
        domain_challenge = challenge_type
        if domain.startswith("*.") and domain_challenge == "http-01":
            domain_challenge = "dns-01"

        try:
            obtain_cert(
                out_dir=out_dir,
                domains=domain_list,
                provider=provider,
                provider_config=provider_config if provider_config else None,
                staging=staging,
                email=email,
                challenge_type=domain_challenge,
            )
            results[domain] = True
        except Exception as e:
            logger.error("证书续签失败 [%s]: %s", domain, e)
            print(f"  [ERROR] 证书续签失败 [{i}/{len(projects)}] {domain}: {e}")
            results[domain] = False

    # 汇总
    print()
    if results:
        success_count = sum(1 for v in results.values() if v)
        print(f"续签完成: {success_count}/{len(results)} 成功")

        for domain_result, success in results.items():
            status = "[OK]" if success else "[FAIL]"
            print(f"  {status} {domain_result}")
    print()

    return results


# ============================================================
# CLI 入口
# ============================================================


def main() -> None:
    """Let's Encrypt 证书管理命令行入口。

    支持以下子命令：
        issue    - 签发新证书
        renew    - 续签即将到期的证书
        status   - 查看证书状态
        revoke   - 吊销证书
        init     - 初始化输出目录
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Let's Encrypt ACME v2 证书管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 测试环境签发证书（手动 DNS）
  zxtool --le issue -d example.com "*.example.com"

  # 生产环境签发证书（Cloudflare 自动 DNS）
  zxtool --le issue -d example.com "*.example.com" \\
    --provider cloudflare \\
    --provider-config '{"api_token":"xxx","zone_id":"yyy"}' \\
    --production \\
    --email admin@example.com

  # 阿里云 DNS 自动签发
  zxtool --le issue -d example.com "*.example.com" \\
    --provider aliyun \\
    --provider-config '{"access_key_id":"xxx","access_key_secret":"yyy"}' \\
    --production

  # HTTP-01 验证签发证书（webroot 方式）
  zxtool --le issue -d example.com \\
    --challenge http-01 \\
    --provider webroot \\
    --provider-config '{"webroot":"/var/www/html"}' \\
    --production

  # HTTP-01 验证签发证书（standalone 方式，需要 80 端口）
  zxtool --le issue -d example.com \\
    --challenge http-01 \\
    --provider standalone \\
    --production

  # 查看证书状态
  zxtool --le status

  # 续签检查（dry-run）
  zxtool --le renew --dry-run

  # 执行续签
  zxtool --le renew \\
    --provider-config '{"api_token":"xxx","zone_id":"yyy"}'

  # 吊销证书
  zxtool --le revoke -d example.com

  # 定期执行（crontab 示例）
  # 每天凌晨 3 点自动续签
  0 3 * * * cd /path/to/project && uv run zxtool --le renew --provider-config '{"api_token":"xxx","zone_id":"yyy"}'
        """,
    )

    parser.add_argument("--le", action="store_true", help="激活 Let's Encrypt 证书管理")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # issue - 签发证书
    issue_parser = subparsers.add_parser("issue", help="签发新证书")
    issue_parser.add_argument(
        "-d", "--domain", nargs="+", required=True, help="域名列表"
    )
    issue_parser.add_argument(
        "--provider", default="manual", help="验证提供商 (DNS-01: manual/cloudflare/aliyun; HTTP-01: webroot/standalone)"
    )
    issue_parser.add_argument(
        "--provider-config", type=str, default=None, help="提供商配置 (JSON 字符串)"
    )
    issue_parser.add_argument(
        "--challenge",
        default="dns-01",
        choices=["dns-01", "http-01"],
        help="验证方式 (dns-01: 支持*泛域名, 需要 DNS 操作; http-01: 仅普通域名, 无需 DNS 操作, 默认 dns-01)",
    )
    issue_parser.add_argument(
        "--production", action="store_true", help="使用生产环境（默认测试环境）"
    )
    issue_parser.add_argument("--email", default="", help="联系邮箱")
    issue_parser.add_argument(
        "--key-size", type=int, default=2048, choices=[2048, 4096], help="RSA 密钥长度"
    )
    issue_parser.add_argument("--output", type=str, default=None, help="输出目录")

    # renew - 续签
    renew_parser = subparsers.add_parser("renew", help="续签即将到期的证书")
    renew_parser.add_argument(
        "--dry-run", action="store_true", help="仅检查，不执行续签"
    )
    renew_parser.add_argument(
        "--provider-config", type=str, default=None, help="提供商配置 (JSON 字符串)"
    )
    renew_parser.add_argument("--output", type=str, default=None, help="输出目录")

    # status - 查看状态
    status_parser = subparsers.add_parser("status", help="查看证书状态")
    status_parser.add_argument("--output", type=str, default=None, help="输出目录")

    # revoke - 吊销
    revoke_parser = subparsers.add_parser("revoke", help="吊销证书")
    revoke_parser.add_argument("-d", "--domain", required=True, help="要吊销的域名")
    revoke_parser.add_argument("--provider", default="manual", help="DNS 提供商")
    revoke_parser.add_argument(
        "--provider-config", type=str, default=None, help="提供商配置 (JSON 字符串)"
    )
    revoke_parser.add_argument("--output", type=str, default=None, help="输出目录")

    # init - 初始化
    init_parser = subparsers.add_parser("init", help="初始化输出目录")
    init_parser.add_argument("--output", type=str, default=None, help="输出目录")

    args = parser.parse_args()

    if not args.le:
        parser.print_help()
        return

    # 解析 provider-config JSON
    provider_config = None
    if getattr(args, "provider_config", None):
        try:
            provider_config = json.loads(args.provider_config)
        except json.JSONDecodeError as e:
            print(f"错误: --provider-config 必须是有效的 JSON: {e}")
            return

    out_dir = Path(args.output) if getattr(args, "output", None) else Path("out_le")
    out_dir = out_dir.resolve()

    if args.command == "init":
        init(out_dir)
    elif args.command == "issue":
        challenge_type = getattr(args, "challenge", "dns-01")
        obtain_cert(
            out_dir=out_dir,
            domains=args.domain,
            provider=args.provider,
            provider_config=provider_config,
            staging=not args.production,
            email=args.email,
            key_size=args.key_size,
            challenge_type=challenge_type,
        )
    elif args.command == "renew":
        renew_certs(
            out_dir=out_dir,
            provider_config=provider_config,
            dry_run=args.dry_run,
        )
    elif args.command == "status":
        show_status(out_dir)
    elif args.command == "revoke":
        revoke_cert(
            out_dir=out_dir,
            domain=args.domain,
            provider=args.provider,
            provider_config=provider_config,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
