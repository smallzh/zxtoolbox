"""Tests for zxtoolbox.backup_manager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from zxtoolbox.backup_manager import copy_directory_with_backup


@patch("zxtoolbox.backup_manager._find_git_dir", return_value=None)
def test_copy_directory_with_backup_creates_timestamped_backup_for_non_git_target(mock_find_git, tmp_path):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    (source_dir / "same.txt").write_text("new", encoding="utf-8")
    (source_dir / "only-src.txt").write_text("fresh", encoding="utf-8")
    (target_dir / "same.txt").write_text("old", encoding="utf-8")

    summary = copy_directory_with_backup(source_dir, target_dir)

    assert summary.target_is_git_repo is False
    assert summary.copied_files == 2
    assert summary.overwritten_files == 1
    assert summary.backup_dir is not None
    assert (target_dir / "same.txt").read_text(encoding="utf-8") == "new"
    assert (target_dir / "only-src.txt").read_text(encoding="utf-8") == "fresh"

    backup_files = list(summary.backup_dir.rglob("same_*.txt"))
    assert len(backup_files) == 1
    assert backup_files[0].read_text(encoding="utf-8") == "old"

    log_file = summary.backup_dir / "backup-records.md"
    assert log_file.exists()
    log_text = log_file.read_text(encoding="utf-8")
    assert "same.txt" in log_text
    assert "backed-up-and-replaced" in log_text


@patch("zxtoolbox.backup_manager.subprocess.run")
def test_copy_directory_with_backup_commits_when_target_is_git_repo(mock_run, tmp_path):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    git_dir = target_dir / ".git"
    source_dir.mkdir()
    target_dir.mkdir()
    git_dir.mkdir()

    (source_dir / "same.txt").write_text("new", encoding="utf-8")
    (target_dir / "same.txt").write_text("old", encoding="utf-8")

    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="", stderr=""),
        MagicMock(returncode=0, stdout=" M same.txt\n", stderr=""),
        MagicMock(returncode=0, stdout="[main abc123] sync\n", stderr=""),
    ]

    summary = copy_directory_with_backup(source_dir, target_dir, commit_message="custom message")

    assert summary.target_is_git_repo is True
    assert summary.commit_created is True
    assert (target_dir / "same.txt").read_text(encoding="utf-8") == "new"
    assert not (target_dir / ".zxtool_backups").exists()

    add_call = mock_run.call_args_list[0]
    status_call = mock_run.call_args_list[1]
    commit_call = mock_run.call_args_list[2]

    assert add_call.kwargs["cwd"] == str(target_dir)
    assert add_call.args[0] == ["git", "add", "-A"]
    assert status_call.args[0] == ["git", "status", "--porcelain"]
    assert commit_call.args[0] == ["git", "commit", "-m", "custom message"]


@patch("zxtoolbox.backup_manager.subprocess.run")
def test_copy_directory_with_backup_skips_commit_when_no_git_changes(mock_run, tmp_path):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    git_dir = target_dir / ".git"
    source_dir.mkdir()
    target_dir.mkdir()
    git_dir.mkdir()

    (source_dir / "same.txt").write_text("new", encoding="utf-8")
    (target_dir / "same.txt").write_text("old", encoding="utf-8")

    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="", stderr=""),
        MagicMock(returncode=0, stdout="", stderr=""),
    ]

    summary = copy_directory_with_backup(source_dir, target_dir)

    assert summary.commit_created is False
    assert len(mock_run.call_args_list) == 2


@patch("zxtoolbox.backup_manager.subprocess.run")
def test_copy_directory_with_backup_raises_on_git_command_failure(mock_run, tmp_path):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()
    (target_dir / ".git").mkdir()
    (source_dir / "same.txt").write_text("new", encoding="utf-8")

    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="fatal")

    try:
        copy_directory_with_backup(source_dir, target_dir)
    except RuntimeError as exc:
        assert "git command failed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError to be raised")
