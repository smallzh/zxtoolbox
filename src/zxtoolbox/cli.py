"""ZX Toolbox command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from zxtoolbox import __version__

import zxtoolbox.backup_manager as bpm
import zxtoolbox.computer_info as cpi
import zxtoolbox.config_manager as cm
import zxtoolbox.epub_manager as em
import zxtoolbox.git_config as gc
import zxtoolbox.http_server as hs
import zxtoolbox.logging_manager as lm
import zxtoolbox.mkpdf_manager as mpdf
import zxtoolbox.pyopt_2fa as opt2fa
import zxtoolbox.ssl_cert as ssl
import zxtoolbox.video_download as vd


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        description="ZX Toolbox - cross-platform utilities for repetitive tasks.",
    )
    parser.set_defaults(_command_parser=parser)
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"zxtoolbox {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="available commands")

    ci_parser = subparsers.add_parser("ci", help="show computer information")
    ci_parser.set_defaults(_command_parser=ci_parser)
    ci_parser.add_argument("-a", "--all", action="store_true", help="show detailed information")

    totp_parser = subparsers.add_parser("totp", help="parse a TOTP key")
    totp_parser.set_defaults(_command_parser=totp_parser)
    totp_parser.add_argument("-k", "--key", type=str, required=True, help="TOTP secret key")

    video_parser = subparsers.add_parser("video", help="download online video")
    video_parser.set_defaults(_command_parser=video_parser)
    video_parser.add_argument("-u", "--url", type=str, required=True, help="video URL")
    video_parser.add_argument("-o", "--output", type=str, default=None, help="output path")

    _build_http_parser(subparsers)
    _build_ssl_parser(subparsers)
    _build_mkdocs_parser(subparsers)
    _build_nginx_parser(subparsers)
    _build_config_parser(subparsers)
    _build_git_parser(subparsers)
    _build_epub_parser(subparsers)
    _build_backup_parser(subparsers)
    _build_mkpdf_parser(subparsers)
    _build_le_parser(subparsers)
    _build_feishu_parser(subparsers)

    return parser


def _build_http_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    http_parser = subparsers.add_parser("http", help="serve static files over HTTP")
    http_parser.set_defaults(_command_parser=http_parser)
    http_subparsers = http_parser.add_subparsers(dest="http_command", help="http subcommands")

    http_serve_parser = http_subparsers.add_parser("serve", help="start a static file HTTP server")
    http_serve_parser.set_defaults(_command_parser=http_serve_parser)
    http_serve_parser.add_argument("directory", nargs="?", default=".", help="directory to serve")
    http_serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="bind host")
    http_serve_parser.add_argument("-p", "--port", type=int, default=8000, help="bind port")


def _build_ssl_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ssl_parser = subparsers.add_parser("ssl", help="generate self-signed SSL certificates")
    ssl_parser.set_defaults(_command_parser=ssl_parser)
    ssl_subparsers = ssl_parser.add_subparsers(dest="ssl_command", help="ssl subcommands")

    ssl_init_parser = ssl_subparsers.add_parser("init", help="initialize output directory structure")
    ssl_init_parser.set_defaults(_command_parser=ssl_init_parser)
    ssl_init_parser.add_argument("--output", type=str, default=None, help="output directory")

    ssl_root_parser = ssl_subparsers.add_parser("root", help="generate Root CA")
    ssl_root_parser.set_defaults(_command_parser=ssl_root_parser)
    ssl_root_parser.add_argument("--output", type=str, default=None, help="output directory")
    ssl_root_parser.add_argument("--force", action="store_true", help="overwrite existing root certs")

    ssl_cert_parser = ssl_subparsers.add_parser("cert", help="generate domain certificates")
    ssl_cert_parser.set_defaults(_command_parser=ssl_cert_parser)
    ssl_cert_parser.add_argument("-d", "--domain", nargs="+", required=True, help="domain list")
    ssl_cert_parser.add_argument("--output", type=str, default=None, help="output directory")


def _build_mkdocs_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    mkdocs_parser = subparsers.add_parser("mkdocs", help="manage MkDocs projects")
    mkdocs_parser.set_defaults(_command_parser=mkdocs_parser)
    mkdocs_subparsers = mkdocs_parser.add_subparsers(dest="mkdocs_command", help="mkdocs subcommands")

    mkdocs_create_parser = mkdocs_subparsers.add_parser("create", help="create a new MkDocs project")
    mkdocs_create_parser.set_defaults(_command_parser=mkdocs_create_parser)
    mkdocs_create_parser.add_argument("project_dir", help="project directory")
    mkdocs_create_parser.add_argument("--name", type=str, default=None, help="site name")

    mkdocs_build_parser = mkdocs_subparsers.add_parser("build", help="build a MkDocs project")
    mkdocs_build_parser.set_defaults(_command_parser=mkdocs_build_parser)
    mkdocs_build_parser.add_argument("project_dir", nargs="?", default=None, help="project directory")
    mkdocs_build_parser.add_argument("-o", "--output", type=str, default=None, help="output directory")
    mkdocs_build_parser.add_argument("-c", "--config", type=str, default=None, help="config file path")
    mkdocs_build_parser.add_argument("--name", type=str, default=None, help="project name from zxtool config")
    mkdocs_build_parser.add_argument("--strict", action="store_true", help="enable strict mode")

    mkdocs_batch_parser = mkdocs_subparsers.add_parser("batch", help="batch build MkDocs projects")
    mkdocs_batch_parser.set_defaults(_command_parser=mkdocs_batch_parser)
    mkdocs_batch_parser.add_argument("config_file", nargs="?", default=None, help="TOML config file path")
    mkdocs_batch_parser.add_argument("--dry-run", action="store_true", help="print plan only")

    mkdocs_serve_parser = mkdocs_subparsers.add_parser("serve", help="serve a MkDocs project")
    mkdocs_serve_parser.set_defaults(_command_parser=mkdocs_serve_parser)
    mkdocs_serve_parser.add_argument("project_dir", help="project directory")
    mkdocs_serve_parser.add_argument("-a", "--dev-addr", type=str, default=None, help="dev server address")
    mkdocs_serve_parser.add_argument("-c", "--config", type=str, default=None, help="config file path")
    mkdocs_serve_parser.add_argument("--no-livereload", action="store_true", help="disable livereload")


def _build_nginx_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    nginx_parser = subparsers.add_parser("nginx", help="manage Nginx site configuration")
    nginx_parser.set_defaults(_command_parser=nginx_parser)
    nginx_subparsers = nginx_parser.add_subparsers(dest="nginx_command", help="nginx subcommands")

    nginx_check_parser = nginx_subparsers.add_parser("check", help="check whether Nginx is available")
    nginx_check_parser.set_defaults(_command_parser=nginx_check_parser)

    nginx_generate_parser = nginx_subparsers.add_parser("generate", help="generate Nginx config from zxtool.toml")
    nginx_generate_parser.set_defaults(_command_parser=nginx_generate_parser)
    nginx_generate_parser.add_argument("--config", type=str, default=None, help="zxtool config path")
    nginx_generate_parser.add_argument("-o", "--output", type=str, default=None, help="output directory")
    nginx_generate_parser.add_argument("--dry-run", action="store_true", help="print plan only")

    nginx_enable_parser = nginx_subparsers.add_parser("enable", help="enable one generated site config")
    nginx_enable_parser.set_defaults(_command_parser=nginx_enable_parser)
    nginx_enable_parser.add_argument("domain", help="site domain")

    nginx_disable_parser = nginx_subparsers.add_parser("disable", help="disable one generated site config")
    nginx_disable_parser.set_defaults(_command_parser=nginx_disable_parser)
    nginx_disable_parser.add_argument("domain", help="site domain")

    nginx_reload_parser = nginx_subparsers.add_parser("reload", help="reload Nginx configuration")
    nginx_reload_parser.set_defaults(_command_parser=nginx_reload_parser)


def _build_config_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    config_parser = subparsers.add_parser("config", help="manage zxtool configuration")
    config_parser.set_defaults(_command_parser=config_parser)
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="config subcommands")

    config_init_parser = config_subparsers.add_parser("init", help="initialize a config file interactively")
    config_init_parser.set_defaults(_command_parser=config_init_parser)
    config_init_parser.add_argument("--path", type=str, default=None, help="config path")
    config_init_parser.add_argument("--force", action="store_true", help="overwrite existing config file")

    config_show_parser = config_subparsers.add_parser("show", help="show current configuration")
    config_show_parser.set_defaults(_command_parser=config_show_parser)
    config_show_parser.add_argument("--path", type=str, default=None, help="config path")


def _build_git_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    git_parser = subparsers.add_parser("git", help="manage Git repositories")
    git_parser.set_defaults(_command_parser=git_parser)
    git_subparsers = git_parser.add_subparsers(dest="git_command", help="git subcommands")

    git_config_parser = git_subparsers.add_parser("config", help="manage git user configuration")
    git_config_parser.set_defaults(_command_parser=git_config_parser)
    git_config_parser.add_argument("config_command", nargs="?", default=None, help="check or fill")
    git_config_parser.add_argument("project_dir", nargs="?", default=None, help="project directory")
    git_config_parser.add_argument("--config", type=str, default=None, help="zxtool config path")
    git_config_parser.add_argument("--name", type=str, default=None, help="git user.name")
    git_config_parser.add_argument("--email", type=str, default=None, help="git user.email")

    git_pull_parser = git_subparsers.add_parser("pull", help="pull one Git repository or all configured projects")
    git_pull_parser.set_defaults(_command_parser=git_pull_parser)
    git_pull_parser.add_argument("project_dir", nargs="?", default=None, help="project directory")
    git_pull_parser.add_argument("--name", type=str, default=None, help="project name from zxtool config")
    git_pull_parser.add_argument("--remote", type=str, default=None, help="remote name")
    git_pull_parser.add_argument("--branch", type=str, default=None, help="branch name")
    git_pull_parser.add_argument("--config", type=str, default=None, help="zxtool config path")


def _build_epub_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    epub_parser = subparsers.add_parser("epub", help="convert EPUB books to Markdown directories")
    epub_parser.set_defaults(_command_parser=epub_parser)
    epub_subparsers = epub_parser.add_subparsers(dest="epub_command", help="epub subcommands")

    epub_convert_parser = epub_subparsers.add_parser("convert", help="convert one EPUB file")
    epub_convert_parser.set_defaults(_command_parser=epub_convert_parser)
    epub_convert_parser.add_argument("epub_file", help="EPUB file path")
    epub_convert_parser.add_argument("-o", "--output", type=str, default=None, help="output directory")


def _build_backup_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    backup_parser = subparsers.add_parser("backup", help="copy directories with backup or git commit behavior")
    backup_parser.set_defaults(_command_parser=backup_parser)
    backup_subparsers = backup_parser.add_subparsers(dest="backup_command", help="backup subcommands")

    backup_copy_parser = backup_subparsers.add_parser("copy", help="copy source directory contents to target directory")
    backup_copy_parser.set_defaults(_command_parser=backup_copy_parser)
    backup_copy_parser.add_argument("source_dir", help="source directory")
    backup_copy_parser.add_argument("target_dir", help="target directory")
    backup_copy_parser.add_argument(
        "--backup-dir-name",
        type=str,
        default=bpm.DEFAULT_BACKUP_DIR_NAME,
        help="backup directory name for non-git targets",
    )
    backup_copy_parser.add_argument(
        "--backup-log-name",
        type=str,
        default=bpm.DEFAULT_BACKUP_LOG_NAME,
        help="backup record filename",
    )
    backup_copy_parser.add_argument("--commit-message", type=str, default=None, help="custom git commit message")


def _build_mkpdf_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    mkpdf_parser = subparsers.add_parser(
        "mkpdf",
        help="convert one Markdown file or Markdown directory into a PDF file",
    )
    mkpdf_parser.set_defaults(_command_parser=mkpdf_parser)
    mkpdf_parser.add_argument("input_path", help="Markdown file path or directory path")
    mkpdf_parser.add_argument(
        "--file",
        type=str,
        default="README.md",
        help="entry Markdown file inside a directory input; defaults to README.md",
    )
    mkpdf_parser.add_argument("-o", "--output", type=str, default=None, help="output PDF path or directory")
    mkpdf_parser.add_argument("--title", type=str, default=None, help="document title override")
    mkpdf_parser.add_argument("--browser", type=str, default=None, help="Chrome/Edge/Chromium executable path")
    mkpdf_parser.add_argument(
        "--mermaid-js",
        type=str,
        default=None,
        help="Mermaid JavaScript path or URL; defaults to the bundled project asset",
    )
    mkpdf_parser.add_argument(
        "--no-mermaid",
        action="store_true",
        help="disable Mermaid diagram rendering",
    )
    mkpdf_parser.add_argument(
        "--render-wait-ms",
        type=int,
        default=mpdf.DEFAULT_RENDER_WAIT_MS,
        help="browser render wait time in milliseconds before printing PDF",
    )


def _build_le_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    le_parser = subparsers.add_parser("le", help="manage Let's Encrypt ACME v2 certificates")
    le_parser.set_defaults(_command_parser=le_parser)
    le_subparsers = le_parser.add_subparsers(dest="le_command", help="le subcommands")

    le_issue_parser = le_subparsers.add_parser("issue", help="issue a new certificate")
    le_issue_parser.set_defaults(_command_parser=le_issue_parser)
    le_issue_parser.add_argument("-d", "--domain", nargs="+", required=True, help="domain list")
    le_issue_parser.add_argument("--provider", default=None, help="validation provider")
    le_issue_parser.add_argument("--provider-config", type=str, default=None, help="provider config as JSON")
    le_issue_parser.add_argument("--challenge", default=None, choices=["dns-01", "http-01"], help="challenge type")
    le_issue_parser.add_argument("--production", action="store_true", default=None, help="use production environment")
    le_issue_parser.add_argument("--email", default=None, help="contact email")
    le_issue_parser.add_argument("--key-size", type=int, default=2048, choices=[2048, 4096], help="RSA key size")
    le_issue_parser.add_argument("--output", type=str, default=None, help="output directory")
    le_issue_parser.add_argument("--le-config", type=str, default=None, help="zxtool config path")

    le_renew_parser = le_subparsers.add_parser("renew", help="renew certificates that are close to expiration")
    le_renew_parser.set_defaults(_command_parser=le_renew_parser)
    le_renew_parser.add_argument("--dry-run", action="store_true", help="check only")
    le_renew_parser.add_argument("--provider-config", type=str, default=None, help="provider config as JSON")
    le_renew_parser.add_argument("--output", type=str, default=None, help="output directory")

    le_batch_parser = le_subparsers.add_parser("batch", help="batch issue or renew certificates from config")
    le_batch_parser.set_defaults(_command_parser=le_batch_parser)
    le_batch_parser.add_argument("--le-config", type=str, default=None, help="zxtool config path")
    le_batch_parser.add_argument("--dry-run", action="store_true", help="print plan only")

    le_status_parser = le_subparsers.add_parser("status", help="show certificate status")
    le_status_parser.set_defaults(_command_parser=le_status_parser)
    le_status_parser.add_argument("--output", type=str, default=None, help="output directory")

    le_revoke_parser = le_subparsers.add_parser("revoke", help="revoke one certificate")
    le_revoke_parser.set_defaults(_command_parser=le_revoke_parser)
    le_revoke_parser.add_argument("-d", "--domain", required=True, help="domain to revoke")
    le_revoke_parser.add_argument("--provider", default="manual", help="DNS provider")
    le_revoke_parser.add_argument("--provider-config", type=str, default=None, help="provider config as JSON")
    le_revoke_parser.add_argument("--output", type=str, default=None, help="output directory")

    le_init_parser = le_subparsers.add_parser("init", help="initialize certificate output directory")
    le_init_parser.set_defaults(_command_parser=le_init_parser)
    le_init_parser.add_argument("--output", type=str, default=None, help="output directory")

    le_cron_parser = le_subparsers.add_parser("cron", help="manage auto-renew scheduled tasks")
    le_cron_parser.set_defaults(_command_parser=le_cron_parser)
    le_cron_subparsers = le_cron_parser.add_subparsers(dest="cron_command", help="cron subcommands")

    le_cron_install_parser = le_cron_subparsers.add_parser("install", help="install auto-renew task")
    le_cron_install_parser.set_defaults(_command_parser=le_cron_install_parser)

    le_cron_uninstall_parser = le_cron_subparsers.add_parser("uninstall", help="uninstall auto-renew task")
    le_cron_uninstall_parser.set_defaults(_command_parser=le_cron_uninstall_parser)


def _build_feishu_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    feishu_parser = subparsers.add_parser("feishu", help="manage Feishu client integration")
    feishu_parser.set_defaults(_command_parser=feishu_parser)
    feishu_subparsers = feishu_parser.add_subparsers(dest="feishu_command", help="feishu subcommands")

    feishu_start_parser = feishu_subparsers.add_parser("start", help="start the Feishu WebSocket client")
    feishu_start_parser.set_defaults(_command_parser=feishu_start_parser)
    feishu_start_parser.add_argument("--config", type=str, default=None, help="config path")
    feishu_start_parser.add_argument("--app-id", type=str, default=None, help="Feishu app ID")
    feishu_start_parser.add_argument("--app-secret", type=str, default=None, help="Feishu app secret")

    feishu_check_parser = feishu_subparsers.add_parser("check", help="check Feishu configuration")
    feishu_check_parser.set_defaults(_command_parser=feishu_check_parser)
    feishu_check_parser.add_argument("--config", type=str, default=None, help="config path")


def main() -> None:
    """CLI main entry point."""
    lm.setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ci":
        if args.all:
            cpi.detailed_info()
        else:
            cpi.summary_info()
        return

    if args.command == "totp":
        opt2fa.parseTotpCdoe(args.key)
        return

    if args.command == "video":
        vd.download_with_progress(args.url, args.output)
        return

    if args.command == "http":
        handle_http(args)
        return

    if args.command == "ssl":
        handle_ssl(args)
        return

    if args.command == "mkdocs":
        handle_mkdocs(args)
        return

    if args.command == "nginx":
        handle_nginx(args)
        return

    if args.command == "config":
        handle_config(args)
        return

    if args.command == "git":
        handle_git(args)
        return

    if args.command == "epub":
        handle_epub(args)
        return

    if args.command == "backup":
        handle_backup(args)
        return

    if args.command == "mkpdf":
        handle_mkpdf(args)
        return

    if args.command == "le":
        handle_le(args)
        return

    if args.command == "feishu":
        handle_feishu(args)
        return

    _print_help(args)


def handle_http(args: argparse.Namespace) -> None:
    """Dispatch http subcommands."""
    http_cmd = getattr(args, "http_command", None)
    if http_cmd == "serve":
        hs.serve_directory(
            directory=args.directory,
            host=args.host,
            port=args.port,
        )
    else:
        _print_help(args)


def handle_ssl(args: argparse.Namespace) -> None:
    """Dispatch ssl subcommands."""
    ssl_cmd = getattr(args, "ssl_command", None)
    if ssl_cmd == "init":
        out_dir = Path(args.output).resolve() if args.output else Path("out").resolve()
        ssl.init(out_dir)
    elif ssl_cmd == "root":
        out_dir = Path(args.output).resolve() if args.output else Path("out").resolve()
        ssl.generate_root(out_dir, force=args.force)
    elif ssl_cmd == "cert":
        out_dir = Path(args.output).resolve() if args.output else Path("out").resolve()
        ssl.generate_cert(out_dir, args.domain)
    else:
        _print_help(args)


def handle_mkdocs(args: argparse.Namespace) -> None:
    """Dispatch mkdocs subcommands."""
    import zxtoolbox.mkdocs_manager as mdm

    mkdocs_cmd = getattr(args, "mkdocs_command", None)
    if mkdocs_cmd == "create":
        mdm.create_project(args.project_dir, site_name=args.name)
    elif mkdocs_cmd == "build":
        if getattr(args, "name", None):
            mdm.build_project_by_name(
                name=args.name,
                config_path=args.config,
                output_dir=args.output,
                strict=args.strict,
            )
        else:
            mdm.build_project(
                project_dir=args.project_dir,
                output_dir=args.output,
                config_file=args.config,
                strict=args.strict,
            )
    elif mkdocs_cmd == "batch":
        mdm.batch_build(
            config_path=args.config_file,
            dry_run=args.dry_run,
        )
    elif mkdocs_cmd == "serve":
        mdm.serve_project(
            project_dir=args.project_dir,
            dev_addr=args.dev_addr,
            config_file=args.config,
            no_livereload=args.no_livereload,
        )
    else:
        _print_help(args)


def handle_nginx(args: argparse.Namespace) -> None:
    """Dispatch nginx subcommands."""
    import zxtoolbox.nginx_manager as ngm

    nginx_cmd = getattr(args, "nginx_command", None)
    if nginx_cmd == "check":
        info = ngm.check_nginx()
        if info["available"]:
            print(f"Nginx version:   {info.get('version', 'unknown')}")
            print(f"Nginx path:      {info.get('nginx_path', 'unknown')}")
            print(f"Config dir:      {info.get('config_dir', 'unknown')}")
            print(f"sites-available: {info.get('sites_available', 'missing')}")
            print(f"sites-enabled:   {info.get('sites_enabled', 'missing')}")
            print(f"conf.d:          {info.get('conf_d', 'missing')}")
        else:
            print("[ERROR] Nginx is not installed.")
            print("Hint: install Nginx first.")
    elif nginx_cmd == "generate":
        ngm.generate_from_config(
            config_path=args.config,
            output_dir=args.output,
            dry_run=args.dry_run,
        )
    elif nginx_cmd == "enable":
        ngm.enable_site(args.domain)
    elif nginx_cmd == "disable":
        ngm.disable_site(args.domain)
    elif nginx_cmd == "reload":
        ngm.reload_nginx()
    else:
        _print_help(args)


def handle_config(args: argparse.Namespace) -> None:
    """Dispatch config subcommands."""
    config_cmd = getattr(args, "config_command", None)
    if config_cmd == "init":
        cm.interactive_init(config_path=args.path, force=args.force)
    elif config_cmd == "show":
        cm.show_config(config_path=args.path)
    else:
        _print_help(args)


def handle_git(args: argparse.Namespace) -> None:
    """Dispatch git subcommands."""
    git_cmd = getattr(args, "git_command", None)
    if git_cmd == "config":
        config_cmd = getattr(args, "config_command", None)
        if config_cmd == "check":
            result = gc.check_git_config(args.project_dir)
            if result:
                print(f"name:  {result['name']}")
                print(f"email: {result['email']}")
        elif config_cmd == "fill":
            gc.fill_git_config(
                project_dir=args.project_dir,
                config_file=args.config,
                name=args.name,
                email=args.email,
            )
        else:
            _print_help(args)
    elif git_cmd == "pull":
        if getattr(args, "name", None):
            gc.git_pull_by_name(
                name=args.name,
                config_path=args.config,
                remote=args.remote,
                branch=args.branch,
            )
        elif args.project_dir:
            gc.git_pull(
                project_dir=args.project_dir,
                remote=args.remote,
                branch=args.branch,
            )
        else:
            if gc.find_git_dir():
                gc.git_pull(
                    project_dir=None,
                    remote=args.remote,
                    branch=args.branch,
                )
            else:
                gc.git_pull_all_projects(
                    config_path=args.config,
                    remote=args.remote,
                    branch=args.branch,
                )
    else:
        _print_help(args)


def handle_epub(args: argparse.Namespace) -> None:
    """Dispatch epub subcommands."""
    epub_cmd = getattr(args, "epub_command", None)
    if epub_cmd == "convert":
        try:
            em.convert_epub_to_markdown(
                epub_file=args.epub_file,
                output_dir=args.output,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"[ERROR] {exc}")
    else:
        _print_help(args)


def handle_backup(args: argparse.Namespace) -> None:
    """Dispatch backup subcommands."""
    backup_cmd = getattr(args, "backup_command", None)
    if backup_cmd == "copy":
        bpm.copy_directory_with_backup(
            source_dir=args.source_dir,
            target_dir=args.target_dir,
            backup_dir_name=args.backup_dir_name,
            backup_log_name=args.backup_log_name,
            commit_message=args.commit_message,
        )
    else:
        _print_help(args)


def handle_mkpdf(args: argparse.Namespace) -> None:
    """Dispatch mkpdf command."""
    try:
        mpdf.convert_markdown_to_pdf(
            input_path=args.input_path,
            output_path=args.output,
            title=args.title,
            directory_file=args.file,
            browser_path=args.browser,
            mermaid_js=args.mermaid_js,
            enable_mermaid=not args.no_mermaid,
            render_wait_ms=args.render_wait_ms,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[ERROR] {exc}")


def handle_le(args: argparse.Namespace) -> None:
    """Dispatch Let's Encrypt subcommands."""
    import zxtoolbox.letsencrypt as le

    le_cmd = getattr(args, "le_command", None)
    provider_config = None
    if getattr(args, "provider_config", None):
        try:
            provider_config = json.loads(args.provider_config)
        except json.JSONDecodeError as exc:
            print(f"Error: --provider-config must be valid JSON: {exc}")
            return

    if getattr(args, "output", None):
        out_dir = Path(args.output).resolve()
    else:
        try:
            le_config = cm.load_le_config(getattr(args, "le_config", None))
            default_out = le_config.get("output_dir", "out_le")
        except (FileNotFoundError, PermissionError):
            default_out = "out_le"
        out_dir = Path(default_out).resolve()

    if le_cmd == "issue":
        try:
            le_cfg = cm.load_le_config(config_path=getattr(args, "le_config", None))
        except (FileNotFoundError, PermissionError, ValueError):
            le_cfg = {}

        issue_provider = args.provider or le_cfg.get("provider", "manual")
        issue_challenge = args.challenge or le_cfg.get("challenge_type", "dns-01")
        issue_staging = not args.production if args.production is not None else le_cfg.get("staging", True)
        issue_email = args.email if args.email is not None else le_cfg.get("email", "")
        issue_provider_config = provider_config if provider_config is not None else le_cfg.get("provider_config") or None
        issue_out_dir = Path(args.output).resolve() if args.output else Path(le_cfg.get("output_dir", "out_le")).resolve()

        le.obtain_cert(
            out_dir=issue_out_dir,
            domains=args.domain,
            provider=issue_provider,
            provider_config=issue_provider_config,
            staging=issue_staging,
            email=issue_email,
            key_size=args.key_size,
            challenge_type=issue_challenge,
        )
    elif le_cmd == "renew":
        le.renew_certs(
            out_dir=out_dir,
            provider_config=provider_config,
            dry_run=args.dry_run,
        )
    elif le_cmd == "batch":
        le.batch_obtain_certs(
            config_path=args.le_config,
            dry_run=args.dry_run,
        )
    elif le_cmd == "status":
        le.show_status(out_dir)
    elif le_cmd == "revoke":
        le.revoke_cert(
            out_dir=out_dir,
            domain=args.domain,
            provider=args.provider,
            provider_config=provider_config,
        )
    elif le_cmd == "init":
        le.init(out_dir)
    elif le_cmd == "cron":
        cron_cmd = getattr(args, "cron_command", None)
        if cron_cmd == "install":
            le.install_cronjob()
        elif cron_cmd == "uninstall":
            le.uninstall_cronjob()
        else:
            _print_help(args)
    else:
        _print_help(args)


def handle_feishu(args: argparse.Namespace) -> None:
    """Dispatch feishu subcommands."""
    from zxtoolbox.config_manager import load_feishu_config
    from zxtoolbox.feishu_client import FeishuClient, create_client_from_config

    feishu_cmd = getattr(args, "feishu_command", None)
    if feishu_cmd == "start":
        if args.app_id and args.app_secret:
            client = FeishuClient(app_id=args.app_id, app_secret=args.app_secret)
            client.start()
            return

        try:
            client = create_client_from_config(args.config)
            client.start()
        except FileNotFoundError as exc:
            print(f"[ERROR] config file not found: {exc}")
            print("Run `zxtool config init` or provide --app-id and --app-secret.")
        except ValueError as exc:
            print(f"[ERROR] invalid configuration: {exc}")
    elif feishu_cmd == "check":
        try:
            config = load_feishu_config(args.config)
            if config.get("app_id") and config.get("app_secret"):
                print("[OK] Feishu configuration is valid")
                print(f"  App ID: {config['app_id'][:10]}...")
                print("  Status: configured")
            else:
                print("[WARN] Feishu configuration is incomplete")
                print("Add the following to zxtool.toml:")
                print("[feishu]")
                print('app_id = "cli_xxxxxxxxxxxxx"')
                print('app_secret = "xxxxxxxxxxxxxxxxxxxx"')
        except FileNotFoundError:
            print("[ERROR] config file not found")
            print("Run `zxtool config init` to initialize configuration.")
    else:
        _print_help(args)


def _print_help(args: argparse.Namespace) -> None:
    """Print help for the most specific parser attached to current args."""
    help_parser = getattr(args, "_command_parser", None)
    if help_parser is not None:
        help_parser.print_help()


if __name__ == "__main__":
    main()
