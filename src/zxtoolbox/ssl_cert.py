"""
自签泛域名 SSL 证书生成器

用于颁发泛域名证书，方便开发环境调试。

功能：
- 生成 Root CA 证书（20年有效期）
- 为多个域名签发泛域名证书（2年有效期）
- 支持 SAN（Subject Alternative Name）多域名
- 输出可直接用于 nginx 配置的 bundle 证书
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# 默认配置（对应 ca.cnf / gen.root.sh / gen.cert.sh 中的硬编码值）
# ============================================================

DEFAULT_COUNTRY = "CN"
DEFAULT_STATE = "Guangdong"
DEFAULT_LOCALITY = "Guangzhou"
DEFAULT_ORG = "Fishdrowned"
DEFAULT_ROOT_CN = "Fishdrowned ROOT CA"
DEFAULT_ROOT_DAYS = 7300  # ~20 年
DEFAULT_CERT_DAYS = 730  # 2 年
RSA_BITS = 2048


# ============================================================
# OpenSSL 配置文件模板（对应 ca.cnf）
# ============================================================

CA_CNF_TEMPLATE = """\
[ ca ]
default_ca = Fishdrowned_ROOT_CA

[ Fishdrowned_ROOT_CA ]
new_certs_dir   = {newcerts_dir}
certificate     = {root_crt}
database        = {index_txt}
private_key     = {root_key}
serial          = {serial_file}
unique_subject  = no
default_days    = {default_days}
default_md      = sha256
policy          = policy_loose
x509_extensions = ca_extensions
copy_extensions = copy

[ policy_loose ]
countryName             = optional
stateOrProvinceName     = optional
localityName            = optional
organizationName        = optional
organizationalUnitName  = optional
commonName              = supplied
emailAddress            = optional

[ ca_extensions ]
basicConstraints = CA:false
nsComment = "OpenSSL Generated Server Certificate"
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always
keyUsage = digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth

[ req ]
default_bits        = 2048
distinguished_name  = req_distinguished_name
string_mask         = utf8only
default_md          = sha256
x509_extensions     = v3_ca

[ req_distinguished_name ]
countryName                     = Country Name (2 letter code)
stateOrProvinceName             = State or Province Name
localityName                    = Locality Name
0.organizationName              = Organization Name
organizationalUnitName          = Organizational Unit Name
commonName                      = Common Name
emailAddress                    = Email Address
countryName_default             = {country}
stateOrProvinceName_default     = {state}
localityName_default            = {locality}
0.organizationName_default      = {org}
organizationalUnitName_default  =
emailAddress_default            =

[ v3_ca ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true
keyUsage = critical, digitalSignature, cRLSign, keyCertSign

[ v3_intermediate_ca ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true, pathlen:0
keyUsage = critical, digitalSignature, cRLSign, keyCertSign

[ usr_cert ]
basicConstraints = CA:FALSE
nsCertType = client, email
nsComment = "OpenSSL Generated Client Certificate"
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
keyUsage = critical, nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth, emailProtection

[ server_cert ]
basicConstraints = CA:FALSE
nsCertType = server
nsComment = "OpenSSL Generated Server Certificate"
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer:always
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[ ocsp ]
basicConstraints = CA:FALSE
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, OCSPSigning
"""


# ============================================================
# 辅助函数
# ============================================================


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """执行 openssl 命令，失败时抛出异常。"""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
        raise RuntimeError(f"OpenSSL command failed: {' '.join(cmd)}")
    return result


def _write_ca_cnf(out_dir: Path):
    """生成 ca.cnf 配置文件到输出目录。"""
    cnf_path = out_dir / "ca.cnf"
    content = CA_CNF_TEMPLATE.format(
        newcerts_dir=str(out_dir / "newcerts"),
        root_crt=str(out_dir / "root.crt"),
        index_txt=str(out_dir / "index.txt"),
        root_key=str(out_dir / "root.key.pem"),
        serial_file=str(out_dir / "serial"),
        default_days=DEFAULT_CERT_DAYS,
        country=DEFAULT_COUNTRY,
        state=DEFAULT_STATE,
        locality=DEFAULT_LOCALITY,
        org=DEFAULT_ORG,
    )
    cnf_path.write_text(content, encoding="utf-8")
    return cnf_path


# ============================================================
# 核心功能
# ============================================================


def init(out_dir: Path):
    """
    初始化输出目录结构（对应 flush.sh）。

    创建 out/newcerts/、out/index.txt、out/serial 等 OpenSSL CA 所需文件。
    """
    print("Initializing output directory...")

    if out_dir.exists():
        import shutil

        shutil.rmtree(out_dir)
        print(f"Removed existing directory: {out_dir}")

    newcerts = out_dir / "newcerts"
    newcerts.mkdir(parents=True, exist_ok=True)

    (out_dir / "index.txt").touch()
    (out_dir / "index.txt.attr").write_text("unique_subject = no\n")
    (out_dir / "serial").write_text("1000\n")

    _write_ca_cnf(out_dir)

    print(f"Output structure created at: {out_dir}")
    print("Done")


def generate_root(out_dir: Path, force: bool = False):
    """
    生成 Root CA 证书（对应 gen.root.sh）。

    - RSA 2048 位密钥
    - 20 年有效期
    - 输出: out/root.crt, out/root.key.pem
    """
    root_crt = out_dir / "root.crt"
    root_key = out_dir / "root.key.pem"
    cert_key = out_dir / "cert.key.pem"
    cnf_path = out_dir / "ca.cnf"

    if root_crt.exists() and not force:
        print("Root certificate already exists. Use --force to regenerate.")
        return False

    # 确保目录结构存在
    if not (out_dir / "index.txt").exists():
        init(out_dir)

    # 重新写入 ca.cnf（确保路径正确）
    _write_ca_cnf(out_dir)

    print("Generating Root CA certificate...")

    # 生成 Root CA（自签名 x509）
    _run(
        [
            "openssl",
            "req",
            "-config",
            str(cnf_path),
            "-newkey",
            f"rsa:{RSA_BITS}",
            "-nodes",
            "-keyout",
            str(root_key),
            "-new",
            "-x509",
            "-days",
            str(DEFAULT_ROOT_DAYS),
            "-out",
            str(root_crt),
            "-subj",
            f"/C={DEFAULT_COUNTRY}/ST={DEFAULT_STATE}/L={DEFAULT_LOCALITY}"
            f"/O={DEFAULT_ORG}/CN={DEFAULT_ROOT_CN}",
        ]
    )

    # 生成用于签发网站证书的私钥
    _run(
        [
            "openssl",
            "genrsa",
            "-out",
            str(cert_key),
            str(RSA_BITS),
        ]
    )

    print(f"Root certificate: {root_crt}")
    print(f"Root key:         {root_key}")
    print(f"Cert key:         {cert_key}")
    print("Root CA generated successfully.")
    return True


def generate_cert(out_dir: Path, domains: list[str]):
    """
    为指定域名签发泛域名 SSL 证书（对应 gen.cert.sh）。

    参数：
        domains: 域名列表，如 ["example.dev", "another.dev"]
                 第一个域名作为主域名用于目录命名。

    输出：
        out/<domain>/<domain>.crt          — 网站证书
        out/<domain>/<domain>.bundle.crt   — 拼接了 CA 的完整证书链
        out/<domain>/<domain>.key.pem      — 私钥（符号链接）
        out/<domain>/root.crt              — 根证书（符号链接）
    """
    if not domains:
        print("Error: at least one domain is required.")
        return

    # 确保 Root CA 存在
    root_crt = out_dir / "root.crt"
    if not root_crt.exists():
        print("Root CA not found, generating...")
        generate_root(out_dir)

    cnf_path = out_dir / "ca.cnf"
    root_key = out_dir / "root.key.pem"
    cert_key = out_dir / "cert.key.pem"

    primary = domains[0]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    domain_dir = out_dir / primary
    version_dir = domain_dir / timestamp

    version_dir.mkdir(parents=True, exist_ok=True)

    # 构建 SAN 字符串: DNS:*.example.dev,DNS:example.dev,DNS:*.another.dev,DNS:another.dev
    san_parts = []
    for d in domains:
        san_parts.append(f"DNS:*.{d}")
        san_parts.append(f"DNS:{d}")
    san = ",".join(san_parts)

    # 构建 OU（用逗号分隔多域名）
    ou = ",".join(domains)

    # 主域名的 CN
    cn = f"*.{primary}"

    csr_path = version_dir / f"{primary}.csr.pem"
    crt_path = version_dir / f"{primary}.crt"

    print(f"Issuing wildcard certificate for: {', '.join(domains)}")
    print(f"  SAN: {san}")

    # 生成 CSR（使用动态 SAN 配置）
    # 通过进程内拼接 SAN 到 ca.cnf，与原 bash 脚本的 <(cat ... <(...)) 等效
    san_config = f"[SAN]\nsubjectAltName={san}"

    # 写入临时配置文件（包含 SAN 扩展）
    temp_cnf = version_dir / "temp.cnf"
    base_cnf = cnf_path.read_text()
    temp_cnf.write_text(base_cnf + "\n" + san_config, encoding="utf-8")

    subj = (
        f"/C={DEFAULT_COUNTRY}/ST={DEFAULT_STATE}/L={DEFAULT_LOCALITY}"
        f"/O={DEFAULT_ORG}/OU={ou}/CN={cn}"
    )

    _run(
        [
            "openssl",
            "req",
            "-new",
            "-out",
            str(csr_path),
            "-key",
            str(cert_key),
            "-reqexts",
            "SAN",
            "-config",
            str(temp_cnf),
            "-subj",
            subj,
        ]
    )

    # 用 CA 签发证书
    _run(
        [
            "openssl",
            "ca",
            "-config",
            str(cnf_path),
            "-batch",
            "-notext",
            "-in",
            str(csr_path),
            "-out",
            str(crt_path),
            "-cert",
            str(root_crt),
            "-keyfile",
            str(root_key),
            "-extensions",
            "SAN",
        ]
    )

    # 拼接证书链（网站证书 + Root CA）
    bundle_path = version_dir / f"{primary}.bundle.crt"
    cert_pem = crt_path.read_text()
    root_pem = root_crt.read_text()
    bundle_path.write_text(cert_pem + root_pem, encoding="utf-8")

    # 创建符号链接（指向最新版本）
    def _symlink(target: Path, link: Path):
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(target)

    _symlink(bundle_path, domain_dir / f"{primary}.bundle.crt")
    _symlink(crt_path, domain_dir / f"{primary}.crt")
    _symlink(cert_key, domain_dir / f"{primary}.key.pem")
    _symlink(root_crt, domain_dir / "root.crt")

    # 输出结果
    print()
    print(f"Certificates generated for: {primary}")
    print(f"  Domain dir: {domain_dir}")
    print()
    print("Files:")
    for f in sorted(domain_dir.iterdir()):
        if f.is_symlink():
            print(f"  {f.name} -> {f.resolve()}")
        else:
            print(f"  {f.name}")
    print()
    print(f"  {primary}.bundle.crt  — 完整证书链（可用于 nginx 配置）")
    print(f"  {primary}.crt         — 网站证书")
    print(f"  {primary}.key.pem     — 私钥")
    print(f"  root.crt              — 根证书（需导入系统并信任）")
    print()
    print("Done! Import root.crt into your OS trust store to enable HTTPS.")


# ============================================================
# CLI 入口
# ============================================================


def main():
    """SSL 证书生成器命令行入口。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="自签泛域名 SSL 证书生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 为单个域名生成证书
  zxtool --ssl --domain example.dev

  # 为多个域名生成证书
  zxtool --ssl --domain example.dev another.dev third.dev

  # 仅初始化目录
  zxtool --ssl --init

  # 仅生成 Root CA
  zxtool --ssl --gen-root

  # 强制重新生成 Root CA
  zxtool --ssl --gen-root --force

  # 清空所有证书
  zxtool --ssl --flush

输出:
  out/root.crt              — 根证书（需导入系统信任）
  out/cert.key.pem           — 证书私钥
  out/<domain>/<domain>.crt  — 网站证书
  out/<domain>/<domain>.bundle.crt — 拼接 CA 的完整证书链（用于 nginx）
        """,
    )

    ssl_group = parser.add_argument_group("SSL", "自签泛域名 SSL 证书生成")
    ssl_group.add_argument("--ssl", action="store_true", help="激活 SSL 证书生成功能")
    ssl_group.add_argument(
        "-d", "--domain", nargs="+", help="域名列表，如 example.dev another.dev"
    )
    ssl_group.add_argument("--init", action="store_true", help="仅初始化输出目录结构")
    ssl_group.add_argument(
        "--gen-root", action="store_true", help="仅生成 Root CA 证书"
    )
    ssl_group.add_argument("--flush", action="store_true", help="清空所有历史证书")
    ssl_group.add_argument(
        "--force", action="store_true", help="强制重新生成（覆盖已有证书）"
    )
    ssl_group.add_argument(
        "--output", type=str, default=None, help="输出目录路径（默认: ./out）"
    )

    args = parser.parse_args()

    if not args.ssl:
        parser.print_help()
        return

    out_dir = Path(args.output) if args.output else Path("out")
    out_dir = out_dir.resolve()

    if args.flush:
        init(out_dir)
        return

    if args.init:
        init(out_dir)
        return

    if args.gen_root:
        generate_root(out_dir, force=args.force)
        return

    if args.domain:
        generate_cert(out_dir, args.domain)
    else:
        print("Error: --domain is required to generate certificates.")
        print("Usage: zxtool --ssl --domain example.dev [another.dev ...]")


if __name__ == "__main__":
    main()
