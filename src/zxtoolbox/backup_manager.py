"""Directory copy with git-aware and backup-aware behaviors."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
DEFAULT_BACKUP_DIR_NAME = ".zxtool_backups"
DEFAULT_BACKUP_LOG_NAME = "backup-records.md"


@dataclass(frozen=True)
class CopyRecord:
    """One copied file record."""

    relative_path: str
    action: str
    backup_path: str | None = None


@dataclass(frozen=True)
class CopySummary:
    """Summary for a directory copy operation."""

    source_dir: Path
    target_dir: Path
    target_is_git_repo: bool
    copied_files: int
    overwritten_files: int
    backup_dir: Path | None
    commit_created: bool
    records: tuple[CopyRecord, ...]


def copy_directory_with_backup(
    source_dir: str | Path,
    target_dir: str | Path,
    *,
    backup_dir_name: str = DEFAULT_BACKUP_DIR_NAME,
    backup_log_name: str = DEFAULT_BACKUP_LOG_NAME,
    commit_message: str | None = None,
) -> CopySummary:
    """Copy source directory contents into target directory with backup strategy."""
    src_path = Path(source_dir).resolve()
    dst_path = Path(target_dir).resolve()

    if not src_path.exists():
        raise FileNotFoundError(f"Source directory not found: {src_path}")
    if not src_path.is_dir():
        raise ValueError(f"Source path is not a directory: {src_path}")

    dst_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    git_dir = _find_git_dir(dst_path)
    target_is_git_repo = git_dir is not None
    backup_dir = None if target_is_git_repo else dst_path / backup_dir_name
    if backup_dir is not None:
        backup_dir.mkdir(parents=True, exist_ok=True)

    records: list[CopyRecord] = []
    copied_files = 0
    overwritten_files = 0

    for source_file in sorted(path for path in src_path.rglob("*") if path.is_file()):
        relative_path = source_file.relative_to(src_path)
        target_file = dst_path / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)

        if target_file.exists():
            overwritten_files += 1
            if target_is_git_repo:
                target_file.unlink()
                action = "replaced-git"
                backup_path = None
            else:
                assert backup_dir is not None
                backup_target = _build_backup_target(backup_dir, relative_path, timestamp)
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target_file, backup_target)
                action = "backed-up-and-replaced"
                backup_path = backup_target.relative_to(dst_path).as_posix()
            shutil.copy2(source_file, target_file)
        else:
            action = "created"
            backup_path = None
            shutil.copy2(source_file, target_file)

        copied_files += 1
        records.append(
            CopyRecord(
                relative_path=relative_path.as_posix(),
                action=action,
                backup_path=backup_path,
            )
        )

    if backup_dir is not None:
        _append_backup_log(
            log_path=backup_dir / backup_log_name,
            timestamp=timestamp,
            source_dir=src_path,
            target_dir=dst_path,
            records=records,
        )

    commit_created = False
    if target_is_git_repo:
        commit_created = _commit_target_repo(
            repo_root=git_dir.parent,
            target_dir=dst_path,
            commit_message=commit_message or _default_commit_message(src_path, timestamp),
        )

    print(f"[OK] directory copy completed: {src_path} -> {dst_path}")
    print(f"  copied:      {copied_files}")
    print(f"  overwritten: {overwritten_files}")
    print(f"  git repo:    {'yes' if target_is_git_repo else 'no'}")
    if backup_dir is not None:
        print(f"  backup dir:  {backup_dir}")
    if target_is_git_repo:
        print(f"  committed:   {'yes' if commit_created else 'no changes'}")

    return CopySummary(
        source_dir=src_path,
        target_dir=dst_path,
        target_is_git_repo=target_is_git_repo,
        copied_files=copied_files,
        overwritten_files=overwritten_files,
        backup_dir=backup_dir,
        commit_created=commit_created,
        records=tuple(records),
    )


def _build_backup_target(backup_dir: Path, relative_path: Path, timestamp: str) -> Path:
    """Build the timestamped backup file path."""
    stem = relative_path.stem
    suffix = relative_path.suffix
    renamed = f"{stem}_{timestamp}{suffix}" if stem else f"{relative_path.name}_{timestamp}"
    return backup_dir / relative_path.parent / renamed


def _append_backup_log(
    log_path: Path,
    timestamp: str,
    source_dir: Path,
    target_dir: Path,
    records: list[CopyRecord],
) -> None:
    """Append backup information to the Markdown log file."""
    lines = [
        f"## {timestamp}",
        "",
        f"- source: `{source_dir}`",
        f"- target: `{target_dir}`",
        f"- records: {len(records)}",
        "",
        "| file | action | backup |",
        "| --- | --- | --- |",
    ]

    for record in records:
        backup_value = record.backup_path or "-"
        lines.append(f"| `{record.relative_path}` | `{record.action}` | `{backup_value}` |")

    lines.append("")

    if log_path.exists():
        previous = log_path.read_text(encoding="utf-8").rstrip()
        content = f"{previous}\n\n" + "\n".join(lines) + "\n"
    else:
        header = [
            "# Backup Records",
            "",
            "This file is generated by `zxtool backup copy`.",
            "",
        ]
        content = "\n".join(header + lines) + "\n"

    log_path.write_text(content, encoding="utf-8")


def _default_commit_message(source_dir: Path, timestamp: str) -> str:
    """Build the default git commit message."""
    return f"zxtool backup sync from {source_dir.name} at {timestamp}"


def _find_git_dir(start_path: Path) -> Path | None:
    """Find a .git directory from start_path upward."""
    current = start_path.resolve()
    while True:
        git_dir = current / ".git"
        if git_dir.is_dir():
            return git_dir
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _commit_target_repo(repo_root: Path, target_dir: Path, commit_message: str) -> bool:
    """Stage target directory changes and commit them when there is any diff."""
    relative_target = target_dir.relative_to(repo_root).as_posix()

    add_command = ["git", "add", "-A"]
    status_command = ["git", "status", "--porcelain"]
    if relative_target != ".":
        add_command.extend(["--", relative_target])
        status_command.extend(["--", relative_target])

    _run_git_command(add_command, cwd=repo_root)

    status_result = _run_git_command(
        status_command,
        cwd=repo_root,
        capture_output=True,
    )
    if not status_result.stdout.strip():
        return False

    _run_git_command(["git", "commit", "-m", commit_message], cwd=repo_root)
    return True


def _run_git_command(
    command: list[str],
    *,
    cwd: Path,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a git command and raise a readable error on failure."""
    result = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=capture_output,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        payload = {
            "command": command,
            "cwd": str(cwd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
        raise RuntimeError(f"git command failed: {json.dumps(payload, ensure_ascii=False)}")
    return result
