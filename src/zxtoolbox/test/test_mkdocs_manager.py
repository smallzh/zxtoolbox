"""Tests for zxtoolbox.mkdocs_manager module."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

from zxtoolbox.mkdocs_manager import (
    create_project,
    build_project,
    _load_batch_config,
    batch_build,
)


class TestCreateProject:
    """Test MkDocs project creation."""

    def test_create_project_basic(self, tmp_path):
        """Test basic project creation."""
        project_dir = tmp_path / "my-docs"
        result = create_project(str(project_dir))

        assert result == project_dir
        assert project_dir.exists()
        assert (project_dir / "docs").exists()
        assert (project_dir / "mkdocs.yml").exists()
        assert (project_dir / "docs" / "index.md").exists()

    def test_create_project_with_site_name(self, tmp_path):
        """Test project creation with custom site name."""
        project_dir = tmp_path / "my-docs"
        create_project(str(project_dir), site_name="My Custom Site")

        mkdocs_yml = project_dir / "mkdocs.yml"
        content = mkdocs_yml.read_text()
        assert "My Custom Site" in content

    def test_create_project_existing_files(self, tmp_path, capsys):
        """Test project creation when files already exist."""
        project_dir = tmp_path / "my-docs"
        project_dir.mkdir()
        (project_dir / "mkdocs.yml").write_text("existing")
        (project_dir / "docs").mkdir()
        (project_dir / "docs" / "index.md").write_text("existing")

        create_project(str(project_dir))

        captured = capsys.readouterr()
        assert "已存在" in captured.out or "WARN" in captured.out

    def test_create_project_nested(self, tmp_path):
        """Test creating project in nested directory."""
        project_dir = tmp_path / "a" / "b" / "my-docs"
        result = create_project(str(project_dir))
        assert result.exists()
        assert (result / "mkdocs.yml").exists()


class TestBuildProject:
    """Test MkDocs project building."""

    @patch("zxtoolbox.mkdocs_manager.subprocess.run")
    def test_build_success(self, mock_run, tmp_path, capsys):
        """Test successful project build."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        project_dir = tmp_path / "my-docs"
        project_dir.mkdir()
        (project_dir / "mkdocs.yml").write_text("site_name: Test\n")

        result = build_project(str(project_dir))

        assert result is True
        mock_run.assert_called_once()

    @patch("zxtoolbox.mkdocs_manager.subprocess.run")
    def test_build_with_output_dir(self, mock_run, tmp_path):
        """Test build with custom output directory."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        project_dir = tmp_path / "my-docs"
        project_dir.mkdir()
        (project_dir / "mkdocs.yml").write_text("site_name: Test\n")
        output_dir = tmp_path / "output"

        build_project(str(project_dir), output_dir=str(output_dir))

        call_args = mock_run.call_args[0][0]
        assert "-d" in call_args
        assert str(output_dir) in call_args

    @patch("zxtoolbox.mkdocs_manager.subprocess.run")
    def test_build_strict_mode(self, mock_run, tmp_path):
        """Test build with strict mode."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        project_dir = tmp_path / "my-docs"
        project_dir.mkdir()
        (project_dir / "mkdocs.yml").write_text("site_name: Test\n")

        build_project(str(project_dir), strict=True)

        call_args = mock_run.call_args[0][0]
        assert "--strict" in call_args

    @patch("zxtoolbox.mkdocs_manager.subprocess.run")
    def test_build_failure(self, mock_run, tmp_path, capsys):
        """Test failed project build."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Build error")

        project_dir = tmp_path / "my-docs"
        project_dir.mkdir()
        (project_dir / "mkdocs.yml").write_text("site_name: Test\n")

        result = build_project(str(project_dir))

        assert result is False

    def test_build_missing_config(self, tmp_path, capsys):
        """Test build with missing config file."""
        project_dir = tmp_path / "my-docs"
        project_dir.mkdir()

        result = build_project(str(project_dir), config_file="nonexistent.yml")

        assert result is False

    @patch("zxtoolbox.mkdocs_manager.subprocess.run")
    def test_build_custom_config(self, mock_run, tmp_path):
        """Test build with custom config file."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        project_dir = tmp_path / "my-docs"
        project_dir.mkdir()
        custom_config = project_dir / "custom.yml"
        custom_config.write_text("site_name: Custom\n")

        build_project(str(project_dir), config_file="custom.yml")

        call_args = mock_run.call_args[0][0]
        assert str(custom_config) in call_args


class TestLoadBatchConfig:
    """Test batch config loading."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid batch config."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[[projects]]\nproject_dir = "/path/1"\noutput_dir = "/out/1"\n'
            '[[projects]]\nproject_dir = "/path/2"\n'
        )

        result = _load_batch_config(str(config_file))

        assert len(result) == 2
        assert result[0]["project_dir"] == "/path/1"
        assert result[0]["output_dir"] == "/out/1"
        assert result[1]["project_dir"] == "/path/2"

    def test_load_missing_config(self, tmp_path):
        """Test loading a non-existent config file."""
        with pytest.raises(FileNotFoundError):
            _load_batch_config(tmp_path / "nonexistent.toml")

    def test_load_empty_projects(self, tmp_path):
        """Test loading config with no projects."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("# empty config\n")

        with pytest.raises(ValueError):
            _load_batch_config(str(config_file))


class TestBatchBuild:
    """Test batch building."""

    @patch("zxtoolbox.mkdocs_manager.build_project", return_value=True)
    @patch("zxtoolbox.mkdocs_manager._load_batch_config")
    def test_batch_build_all_success(self, mock_load, mock_build, tmp_path, capsys):
        """Test batch build where all projects succeed."""
        mock_load.return_value = [
            {"project_dir": "/path/1", "output_dir": "/out/1"},
            {"project_dir": "/path/2"},
        ]

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[[projects]]\nproject_dir = "/path/1"\n'
            '[[projects]]\nproject_dir = "/path/2"\n'
        )

        result = batch_build(str(config_file))

        assert len(result) == 2
        assert all(result.values())
        assert mock_build.call_count == 2

    @patch("zxtoolbox.mkdocs_manager.build_project", side_effect=[True, False, True])
    @patch("zxtoolbox.mkdocs_manager._load_batch_config")
    def test_batch_build_partial_failure(self, mock_load, mock_build, tmp_path):
        """Test batch build with some failures."""
        mock_load.return_value = [
            {"project_dir": "/path/1"},
            {"project_dir": "/path/2"},
            {"project_dir": "/path/3"},
        ]

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[[projects]]\nproject_dir = "/path/1"\n'
            '[[projects]]\nproject_dir = "/path/2"\n'
            '[[projects]]\nproject_dir = "/path/3"\n'
        )

        result = batch_build(str(config_file))

        assert len(result) == 3
        assert result["/path/1"] is True
        assert result["/path/2"] is False
        assert result["/path/3"] is True

    @patch("zxtoolbox.mkdocs_manager._load_batch_config")
    def test_batch_build_missing_config(self, mock_load, tmp_path, capsys):
        """Test batch build with missing config file."""
        mock_load.side_effect = FileNotFoundError("Config not found")

        result = batch_build(tmp_path / "nonexistent.toml")

        assert result == {}

    @patch("zxtoolbox.mkdocs_manager._load_batch_config")
    def test_batch_build_no_projects(self, mock_load, tmp_path, capsys):
        """Test batch build with no projects in config."""
        mock_load.side_effect = ValueError("No projects found")

        result = batch_build(tmp_path / "config.toml")

        assert result == {}

    @patch("zxtoolbox.mkdocs_manager.build_project")
    @patch("zxtoolbox.mkdocs_manager._load_batch_config")
    def test_batch_build_dry_run(self, mock_load, mock_build, tmp_path, capsys):
        """Test batch build dry-run mode."""
        mock_load.return_value = [
            {"project_dir": "/path/1", "output_dir": "/out/1"},
        ]

        config_file = tmp_path / "config.toml"
        config_file.write_text('[[projects]]\nproject_dir = "/path/1"\n')

        result = batch_build(str(config_file), dry_run=True)

        assert len(result) == 1
        mock_build.assert_not_called()

    @patch("zxtoolbox.mkdocs_manager.build_project", return_value=True)
    @patch("zxtoolbox.mkdocs_manager._load_batch_config")
    def test_batch_build_missing_project_dir(self, mock_load, mock_build, tmp_path):
        """Test batch build with missing project_dir."""
        mock_load.return_value = [{"output_dir": "/out/1"}]

        config_file = tmp_path / "config.toml"
        config_file.write_text('[[projects]]\noutput_dir = "/out/1"\n')

        result = batch_build(str(config_file))

        # Should skip the project with missing project_dir
        mock_build.assert_not_called()
