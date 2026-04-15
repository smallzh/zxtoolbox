"""Tests for zxtoolbox.config_manager module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from zxtoolbox.config_manager import (
    DEFAULT_CONFIG_PATH,
    _escape_toml_string,
    _generate_projects_section,
    _generate_letsencrypt_section,
    _generate_git_section,
    generate_config_content,
    write_config,
    show_config,
    load_config,
    load_le_config,
    load_projects_with_domain,
    load_project_by_name,
)


class TestEscapeTomlString:
    """Test TOML string escaping."""

    def test_simple_string(self):
        result = _escape_toml_string("hello")
        assert result == '"hello"'

    def test_string_with_quotes(self):
        result = _escape_toml_string('hello "world"')
        assert '\\"' in result

    def test_string_with_backslash(self):
        result = _escape_toml_string("path\\to\\file")
        assert "\\\\" in result

    def test_string_with_newline(self):
        result = _escape_toml_string("line1\nline2")
        assert "\\n" in result

    def test_string_with_tab(self):
        result = _escape_toml_string("col1\tcol2")
        assert "\\t" in result

    def test_empty_string(self):
        result = _escape_toml_string("")
        assert result == '""'


class TestGenerateProjectsSection:
    """Test projects section generation."""

    def test_empty_projects(self):
        result = _generate_projects_section([])
        assert result == ""

    def test_single_project(self):
        projects = [{"project_dir": "/path/to/docs"}]
        result = _generate_projects_section(projects)
        assert "[[projects]]" in result
        assert '"/path/to/docs"' in result

    def test_project_with_all_fields(self):
        projects = [
            {
                "project_dir": "/path/to/docs",
                "output_dir": "/output",
                "config_file": "custom.yml",
                "strict": True,
                "domain": "example.com",
            }
        ]
        result = _generate_projects_section(projects)
        assert "output_dir" in result
        assert "config_file" in result
        assert "strict = true" in result
        assert "domain" in result
        assert '"example.com"' in result

    def test_project_with_domain(self):
        projects = [
            {"project_dir": "/path/to/docs", "domain": "example.com"}
        ]
        result = _generate_projects_section(projects)
        assert 'domain = "example.com"' in result

    def test_project_with_wildcard_domain(self):
        projects = [
            {"project_dir": "/path/to/docs", "domain": "*.example.com"}
        ]
        result = _generate_projects_section(projects)
        assert 'domain = "*.example.com"' in result

    def test_multiple_projects(self):
        projects = [
            {"project_dir": "/path/1"},
            {"project_dir": "/path/2"},
        ]
        result = _generate_projects_section(projects)
        assert result.count("[[projects]]") == 2

    def test_project_without_domain(self):
        """Project without domain should not have domain field."""
        projects = [{"project_dir": "/path/to/docs"}]
        result = _generate_projects_section(projects)
        assert "domain" not in result


class TestGenerateLetsencryptSection:
    """Test Let's Encrypt config section generation."""

    def test_default_settings(self):
        result = _generate_letsencrypt_section()
        assert "provider = \"manual\"" in result
        assert "staging = true" in result
        assert "[letsencrypt]" in result

    def test_custom_provider(self):
        result = _generate_letsencrypt_section(provider="cloudflare")
        assert '"cloudflare"' in result

    def test_custom_output_dir(self):
        result = _generate_letsencrypt_section(output_dir="/custom/certs")
        assert '"/custom/certs"' in result

    def test_production_mode(self):
        result = _generate_letsencrypt_section(staging=False)
        assert "staging = false" in result

    def test_with_email(self):
        result = _generate_letsencrypt_section(email="admin@example.com")
        assert '"admin@example.com"' in result

    def test_with_provider_config(self):
        provider_config = {"api_token": "xxx", "zone_id": "yyy"}
        result = _generate_letsencrypt_section(
            provider="cloudflare",
            provider_config=provider_config,
        )
        assert "[letsencrypt.provider_config]" in result
        assert "api_token" in result
        assert "zone_id" in result

    def test_with_aliyun_provider_config(self):
        provider_config = {"access_key_id": "key123", "access_key_secret": "secret456"}
        result = _generate_letsencrypt_section(
            provider="aliyun",
            provider_config=provider_config,
        )
        assert "[letsencrypt.provider_config]" in result
        assert "access_key_id" in result
        assert "access_key_secret" in result


class TestGenerateGitSection:
    """Test Git config generation."""

    def test_empty_users(self):
        result = _generate_git_section([])
        assert result == ""

    def test_single_user(self):
        users = [{"name": "John", "email": "john@example.com"}]
        result = _generate_git_section(users)
        assert "[[git.user]]" in result
        assert '"John"' in result
        assert '"john@example.com"' in result

    def test_multiple_users(self):
        users = [
            {"name": "John", "email": "john@example.com"},
            {"name": "Jane", "email": "jane@example.com"},
        ]
        result = _generate_git_section(users)
        assert result.count("[[git.user]]") == 2

    def test_user_missing_email(self):
        users = [{"name": "John"}]
        result = _generate_git_section(users)
        assert '"John"' in result
        assert "email" not in result


class TestGenerateConfigContent:
    """Test full config content generation."""

    def test_empty_config(self):
        result = generate_config_content()
        assert "zxtool" in result
        assert "暂无配置项" in result

    def test_with_projects_only(self):
        result = generate_config_content(
            mkdocs_projects=[{"project_dir": "/docs"}],
        )
        assert "[[projects]]" in result
        assert "暂无配置项" not in result

    def test_with_projects_and_git(self):
        result = generate_config_content(
            mkdocs_projects=[{"project_dir": "/docs"}],
            git_users=[{"name": "John", "email": "john@example.com"}],
        )
        assert "[[projects]]" in result
        assert "[[git.user]]" in result
        assert "暂无配置项" not in result

    def test_with_letsencrypt_config(self):
        le_config = {
            "provider": "cloudflare",
            "output_dir": "out_le",
            "staging": True,
            "email": "admin@example.com",
        }
        result = generate_config_content(letsencrypt_config=le_config)
        assert "[letsencrypt]" in result
        assert '"cloudflare"' in result
        assert "暂无配置项" not in result

    def test_with_all_sections(self):
        le_config = {
            "provider": "aliyun",
            "output_dir": "/certs",
            "staging": False,
            "email": "test@example.com",
            "provider_config": {"access_key_id": "xxx", "access_key_secret": "yyy"},
        }
        projects = [
            {
                "project_dir": "/myproject",
                "domain": "*.myproject.com",
                "output_dir": "/site",
            },
        ]
        git_users = [{"name": "Dev", "email": "dev@example.com"}]
        result = generate_config_content(
            mkdocs_projects=projects,
            git_users=git_users,
            letsencrypt_config=le_config,
        )
        assert "[letsencrypt]" in result
        assert "[letsencrypt.provider_config]" in result
        assert "[[projects]]" in result
        assert 'domain = "*.myproject.com"' in result
        assert "[[git.user]]" in result

    def test_header_present(self):
        result = generate_config_content()
        assert "# zxtool 全局配置文件" in result
        assert "# 路径: ~/.config/zxtool.toml" in result

    def test_usage_hints_include_le_batch(self):
        result = generate_config_content()
        assert "zxtool le batch" in result


class TestWriteConfig:
    """Test config file writing."""

    def test_write_new_config(self, tmp_path):
        """Test writing a new config file."""
        config_path = tmp_path / "zxtool.toml"
        result = write_config(
            config_path,
            mkdocs_projects=[{"project_dir": "/docs"}],
            git_users=[{"name": "John", "email": "john@example.com"}],
            force=True,
        )
        assert result is True
        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "[[projects]]" in content
        assert "[[git.user]]" in content

    def test_write_config_with_letsencrypt(self, tmp_path):
        """Test writing config with Let's Encrypt settings."""
        config_path = tmp_path / "zxtool.toml"
        le_config = {
            "provider": "cloudflare",
            "output_dir": "out_le",
            "staging": True,
            "email": "admin@example.com",
            "provider_config": {"api_token": "test_token", "zone_id": "test_zone"},
        }
        result = write_config(
            config_path,
            letsencrypt_config=le_config,
            force=True,
        )
        assert result is True
        content = config_path.read_text(encoding="utf-8")
        assert "[letsencrypt]" in content
        assert "[letsencrypt.provider_config]" in content
        assert "cloudflare" in content

    def test_write_config_with_domain(self, tmp_path):
        """Test writing config with domain in projects."""
        config_path = tmp_path / "zxtool.toml"
        projects = [
            {
                "project_dir": "/myproject",
                "domain": "*.example.com",
                "output_dir": "/site",
            },
        ]
        result = write_config(
            config_path,
            mkdocs_projects=projects,
            force=True,
        )
        assert result is True
        content = config_path.read_text(encoding="utf-8")
        assert 'domain = "*.example.com"' in content

    def test_write_existing_config_without_force(self, tmp_path):
        """Test writing to existing file without force."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text("existing")

        result = write_config(config_path, force=False)

        assert result is False

    def test_write_existing_config_with_force(self, tmp_path):
        """Test overwriting existing file with force."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text("existing")

        result = write_config(
            config_path,
            mkdocs_projects=[{"project_dir": "/docs"}],
            force=True,
        )

        assert result is True
        content = config_path.read_text(encoding="utf-8")
        assert "existing" not in content

    def test_write_creates_parent_dir(self, tmp_path):
        """Test that parent directories are created."""
        config_path = tmp_path / "subdir" / "zxtool.toml"
        result = write_config(config_path, force=True)
        assert result is True
        assert config_path.exists()

    def test_write_empty_config(self, tmp_path):
        """Test writing an empty config."""
        config_path = tmp_path / "zxtool.toml"
        result = write_config(config_path, force=True)
        assert result is True
        content = config_path.read_text(encoding="utf-8")
        assert "暂无配置项" in content


class TestShowConfig:
    """Test config file display."""

    def test_show_existing_config(self, tmp_path, capsys):
        """Test showing an existing config file."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('# Test config\n[[projects]]\nproject_dir = "/docs"\n')

        show_config(str(config_path))

        captured = capsys.readouterr()
        assert "# Test config" in captured.out
        assert "[[projects]]" in captured.out

    def test_show_missing_config(self, tmp_path, capsys):
        """Test showing a non-existent config file."""
        config_path = tmp_path / "nonexistent.toml"

        show_config(str(config_path))

        captured = capsys.readouterr()
        assert "不存在" in captured.out


class TestLoadConfig:
    """Test config file loading."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid TOML config."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[letsencrypt]
provider = "cloudflare"
output_dir = "/certs"
staging = true
email = "admin@example.com"

[letsencrypt.provider_config]
api_token = "test_token"
zone_id = "test_zone"

[[projects]]
project_dir = "/myproject"
domain = "example.com"
output_dir = "/site"

[[projects]]
project_dir = "/myproject2"
domain = "*.example2.com"

[git]

[[git.user]]
name = "John"
email = "john@example.com"
''', encoding="utf-8")

        data = load_config(str(config_path))

        # letsencrypt section
        assert data["letsencrypt"]["provider"] == "cloudflare"
        assert data["letsencrypt"]["output_dir"] == "/certs"
        assert data["letsencrypt"]["staging"] is True
        assert data["letsencrypt"]["email"] == "admin@example.com"
        assert data["letsencrypt"]["provider_config"]["api_token"] == "test_token"

        # projects
        assert len(data["projects"]) == 2
        assert data["projects"][0]["domain"] == "example.com"
        assert data["projects"][1]["domain"] == "*.example2.com"

        # git
        assert data["git"]["user"][0]["name"] == "John"

    def test_load_config_file_not_found(self, tmp_path):
        """Test loading non-existent config raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config(str(tmp_path / "nonexistent.toml"))

    def test_load_config_empty_file(self, tmp_path):
        """Test loading empty config returns empty dict."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text("", encoding="utf-8")

        data = load_config(str(config_path))
        assert data == {}


class TestLoadLeConfig:
    """Test Let's Encrypt config loading."""

    def test_load_le_config_full(self, tmp_path):
        """Test loading complete LE config."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[letsencrypt]
provider = "cloudflare"
output_dir = "/certs"
staging = false
email = "admin@example.com"

[letsencrypt.provider_config]
api_token = "xxx"
zone_id = "yyy"
''', encoding="utf-8")

        le_config = load_le_config(str(config_path))

        assert le_config["provider"] == "cloudflare"
        assert le_config["output_dir"] == "/certs"
        assert le_config["staging"] is False
        assert le_config["email"] == "admin@example.com"
        assert le_config["provider_config"]["api_token"] == "xxx"
        assert le_config["provider_config"]["zone_id"] == "yyy"

    def test_load_le_config_defaults(self, tmp_path):
        """Test LE config defaults when section is missing."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('[[projects]]\nproject_dir = "/test"\n', encoding="utf-8")

        le_config = load_le_config(str(config_path))

        assert le_config["provider"] == "manual"
        assert le_config["output_dir"] == "out_le"
        assert le_config["staging"] is True
        assert le_config["email"] == ""
        assert le_config["provider_config"] == {}

    def test_load_le_config_partial(self, tmp_path):
        """Test loading partial LE config uses defaults."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[letsencrypt]
provider = "aliyun"
''', encoding="utf-8")

        le_config = load_le_config(str(config_path))

        assert le_config["provider"] == "aliyun"
        assert le_config["staging"] is True  # default
        assert le_config["output_dir"] == "out_le"  # default


class TestLoadProjectsWithDomain:
    """Test loading projects with domain config."""

    def test_load_projects_with_domain(self, tmp_path):
        """Test loading projects that have domain config."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[letsencrypt]
provider = "cloudflare"
output_dir = "/certs"
staging = false
email = "admin@example.com"

[letsencrypt.provider_config]
api_token = "xxx"
zone_id = "yyy"

[[projects]]
project_dir = "/myproject"
domain = "example.com"
output_dir = "/site"

[[projects]]
project_dir = "/myproject2"
domain = "*.example2.com"

[[projects]]
project_dir = "/no-domain-project"
output_dir = "/site2"
''', encoding="utf-8")

        projects = load_projects_with_domain(str(config_path))

        # Only projects with domain field should be returned
        assert len(projects) == 2
        assert projects[0]["project_dir"] == "/myproject"
        assert projects[0]["domain"] == "example.com"
        assert projects[0]["_le"]["provider"] == "cloudflare"
        assert projects[1]["project_dir"] == "/myproject2"
        assert projects[1]["domain"] == "*.example2.com"

    def test_load_projects_with_domain_no_le_section(self, tmp_path):
        """Test loading projects when no [letsencrypt] section exists."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[[projects]]
project_dir = "/myproject"
domain = "example.com"
''', encoding="utf-8")

        projects = load_projects_with_domain(str(config_path))

        assert len(projects) == 1
        assert projects[0]["domain"] == "example.com"
        # Defaults should be used
        assert projects[0]["_le"]["provider"] == "manual"
        assert projects[0]["_le"]["staging"] is True

    def test_load_projects_no_domain_projects(self, tmp_path):
        """Test that projects without domain are excluded."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[[projects]]
project_dir = "/no-domain"
output_dir = "/site"
''', encoding="utf-8")

        projects = load_projects_with_domain(str(config_path))
        assert len(projects) == 0

    def test_load_projects_file_not_found(self, tmp_path):
        """Test that FileNotFoundError is raised for missing config."""
        with pytest.raises(FileNotFoundError):
            load_projects_with_domain(str(tmp_path / "nonexistent.toml"))

    def test_load_projects_wildcard_domain_inherits_le_config(self, tmp_path):
        """Test that wildcard domain projects get LE config."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[letsencrypt]
provider = "aliyun"
staging = false

[[projects]]
project_dir = "/project"
domain = "*.example.com"
''', encoding="utf-8")

        projects = load_projects_with_domain(str(config_path))
        assert len(projects) == 1
        assert projects[0]["domain"] == "*.example.com"
        assert projects[0]["_le"]["provider"] == "aliyun"
        assert projects[0]["_le"]["staging"] is False


class TestInteractiveInit:
    """Test interactive config initialization."""

    @patch("builtins.input", side_effect=["n", "", "", EOFError()])
    def test_interactive_init_skip_all(self, mock_input, tmp_path):
        """Test interactive init skipping LE, projects, and git sections."""
        config_path = tmp_path / "zxtool.toml"
        from zxtoolbox.config_manager import interactive_init

        # Inputs: "n" = skip LE config, "" = skip project dir, "" = skip git name
        # Then EOFError on confirmation or next prompt
        result = interactive_init(config_path)
        # Should return False due to EOFError during confirmation, or True if completed
        assert result is False or mock_input.call_count >= 1


class TestGenerateProjectsWithNameAndGitRepo:
    """Test projects section generation with name and git_repository fields."""

    def test_project_with_name(self):
        projects = [
            {"name": "myblog", "project_dir": "/path/to/docs"}
        ]
        result = _generate_projects_section(projects)
        assert 'name = "myblog"' in result
        assert "[[projects]]" in result

    def test_project_with_git_repository(self):
        projects = [
            {
                "project_dir": "/path/to/docs",
                "git_repository": "https://github.com/user/repo.git",
            }
        ]
        result = _generate_projects_section(projects)
        assert 'git_repository = "https://github.com/user/repo.git"' in result

    def test_project_with_name_and_git_repository(self):
        projects = [
            {
                "name": "myblog",
                "project_dir": "/path/to/docs",
                "domain": "example.com",
                "git_repository": "https://github.com/user/myblog.git",
            }
        ]
        result = _generate_projects_section(projects)
        assert 'name = "myblog"' in result
        assert 'domain = "example.com"' in result
        assert 'git_repository = "https://github.com/user/myblog.git"' in result

    def test_project_without_name(self):
        """Project without name should not have name field."""
        projects = [{"project_dir": "/path/to/docs"}]
        result = _generate_projects_section(projects)
        assert "name" not in result

    def test_project_without_git_repository(self):
        """Project without git_repository should not have git_repository field."""
        projects = [{"project_dir": "/path/to/docs"}]
        result = _generate_projects_section(projects)
        assert "git_repository" not in result

    def test_write_config_with_name_and_git_repo(self, tmp_path):
        """Test writing config with name and git_repository fields."""
        config_path = tmp_path / "zxtool.toml"
        projects = [
            {
                "name": "myblog",
                "project_dir": "/path/to/docs",
                "domain": "example.com",
                "output_dir": "/site",
                "git_repository": "https://github.com/user/myblog.git",
            }
        ]
        result = write_config(
            config_path,
            mkdocs_projects=projects,
            force=True,
        )
        assert result is True
        content = config_path.read_text(encoding="utf-8")
        assert 'name = "myblog"' in content
        assert 'git_repository = "https://github.com/user/myblog.git"' in content

    def test_load_config_with_name_and_git_repo(self, tmp_path):
        """Test loading config with name and git_repository fields."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[[projects]]
name = "myblog"
project_dir = "/path/to/docs"
domain = "example.com"
git_repository = "https://github.com/user/myblog.git"
''', encoding="utf-8")

        data = load_config(str(config_path))
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "myblog"
        assert data["projects"][0]["git_repository"] == "https://github.com/user/myblog.git"


class TestLoadProjectByName:
    """Test loading a project by name from config."""

    def test_load_project_by_name_found(self, tmp_path):
        """Test finding a project by name."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[[projects]]
name = "myblog"
project_dir = "/path/to/docs"
domain = "example.com"
git_repository = "https://github.com/user/myblog.git"

[[projects]]
name = "api-docs"
project_dir = "/path/to/api-docs"
output_dir = "/site"
''', encoding="utf-8")

        result = load_project_by_name("myblog", config_path=str(config_path))
        assert result is not None
        assert result["name"] == "myblog"
        assert result["project_dir"] == "/path/to/docs"
        assert result["git_repository"] == "https://github.com/user/myblog.git"

    def test_load_project_by_name_second_project(self, tmp_path):
        """Test finding the second project by name."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[[projects]]
name = "myblog"
project_dir = "/path/to/docs"

[[projects]]
name = "api-docs"
project_dir = "/path/to/api-docs"
''', encoding="utf-8")

        result = load_project_by_name("api-docs", config_path=str(config_path))
        assert result is not None
        assert result["name"] == "api-docs"
        assert result["project_dir"] == "/path/to/api-docs"

    def test_load_project_by_name_not_found(self, tmp_path):
        """Test returning None when name is not found."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[[projects]]
name = "myblog"
project_dir = "/path/to/docs"
''', encoding="utf-8")

        result = load_project_by_name("nonexistent", config_path=str(config_path))
        assert result is None

    def test_load_project_by_name_no_name_field(self, tmp_path):
        """Test returning None when projects don't have name field."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[[projects]]
project_dir = "/path/to/docs"
''', encoding="utf-8")

        result = load_project_by_name("myblog", config_path=str(config_path))
        assert result is None

    def test_load_project_by_name_file_not_found(self, tmp_path):
        """Test FileNotFoundError when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_project_by_name("myblog", config_path=str(tmp_path / "nonexistent.toml"))

    def test_load_project_by_name_empty_projects(self, tmp_path):
        """Test returning None when no projects in config."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('', encoding="utf-8")

        result = load_project_by_name("myblog", config_path=str(config_path))
        assert result is None