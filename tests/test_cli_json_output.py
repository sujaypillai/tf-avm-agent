"""Tests for CLI JSON output format."""

import json
import re
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from tf_avm_agent.cli import app


runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class TestListModulesJsonOutput:
    """Tests for list-modules command with JSON output."""

    def test_list_modules_json_format(self):
        """Test that list-modules supports JSON output format."""
        result = runner.invoke(app, ["list-modules", "--output-format", "json"])
        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.stdout)
        assert "modules" in output
        assert isinstance(output["modules"], dict)
        assert len(output["modules"]) > 0

        # Check structure of first module
        first_module = next(iter(output["modules"].values()))
        assert "source" in first_module
        assert "version" in first_module
        assert "category" in first_module
        assert "description" in first_module
        assert "aliases" in first_module

    def test_list_modules_json_with_category_filter(self):
        """Test that list-modules JSON output respects category filter."""
        result = runner.invoke(app, ["list-modules", "-c", "compute", "-f", "json"])
        assert result.exit_code == 0

        output = json.loads(result.stdout)
        assert "modules" in output

        # All modules should be in compute category
        for module_data in output["modules"].values():
            assert module_data["category"] == "compute"

    def test_list_modules_json_no_ansi_codes(self):
        """Test that JSON output has no ANSI codes."""
        result = runner.invoke(app, ["list-modules", "--output-format", "json"])
        assert result.exit_code == 0

        # JSON output should not contain ANSI escape codes
        assert "\x1b[" not in result.stdout


class TestSearchJsonOutput:
    """Tests for search command with JSON output."""

    def test_search_json_format(self):
        """Test that search supports JSON output format."""
        result = runner.invoke(app, ["search", "storage", "--output-format", "json"])
        assert result.exit_code == 0

        output = json.loads(result.stdout)
        assert "query" in output
        assert output["query"] == "storage"
        assert "modules" in output
        assert isinstance(output["modules"], list)

    def test_search_json_module_structure(self):
        """Test the structure of modules in search JSON output."""
        result = runner.invoke(app, ["search", "virtual", "-f", "json"])
        assert result.exit_code == 0

        output = json.loads(result.stdout)
        if output["modules"]:  # If there are results
            module = output["modules"][0]
            assert "name" in module
            assert "source" in module
            assert "version" in module
            assert "category" in module
            assert "description" in module
            assert "aliases" in module
            assert "azure_service" in module


class TestInfoJsonOutput:
    """Tests for info command with JSON output."""

    def test_info_json_format(self):
        """Test that info supports JSON output format."""
        result = runner.invoke(app, ["info", "virtual_machine", "--output-format", "json"])
        assert result.exit_code == 0

        output = json.loads(result.stdout)
        assert "name" in output
        assert "source" in output
        assert "version" in output
        assert "category" in output
        assert "description" in output
        assert "azure_service" in output
        assert "aliases" in output
        assert "dependencies" in output
        assert "required_variables" in output
        assert "optional_variables" in output
        assert "outputs" in output

    def test_info_json_variable_structure(self):
        """Test the structure of variables in info JSON output."""
        result = runner.invoke(app, ["info", "storage", "-f", "json"])
        assert result.exit_code == 0

        output = json.loads(result.stdout)
        if output["required_variables"]:
            var = output["required_variables"][0]
            assert "name" in var
            assert "type" in var
            assert "description" in var
            assert "required" in var

    def test_info_json_module_not_found(self):
        """Test that info returns JSON error for non-existent module."""
        result = runner.invoke(app, ["info", "nonexistent_module_xyz", "--output-format", "json"])
        assert result.exit_code == 1

        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "message" in output
        assert "code" in output
        assert output["code"] == "MODULE_NOT_FOUND"


class TestGenerateJsonOutput:
    """Tests for generate command with JSON output."""

    def test_generate_json_format(self):
        """Test that generate supports JSON output format."""
        with patch("tf_avm_agent.cli._require_agent_extra") as mock_require:
            # Mock the generate_terraform function
            mock_generate = MagicMock()
            mock_result = MagicMock()
            mock_result.files = [
                MagicMock(filename="main.tf", content="# main"),
                MagicMock(filename="variables.tf", content="# variables"),
            ]
            mock_generate.return_value = mock_result
            mock_require.return_value = (MagicMock(), mock_generate)

            result = runner.invoke(
                app,
                [
                    "generate",
                    "-s", "storage",
                    "-n", "test-project",
                    "-o", "/tmp/test-output",
                    "--output-format", "json"
                ]
            )

            assert result.exit_code == 0
            output = json.loads(result.stdout)

            assert output["status"] == "success"
            assert "project_name" in output
            assert output["project_name"] == "test-project"
            assert "output_dir" in output
            assert "modules_used" in output
            assert "files_written" in output
            assert "warnings" in output

    def test_generate_json_missing_services_error(self):
        """Test that generate returns JSON error when services missing."""
        result = runner.invoke(
            app,
            ["generate", "-n", "test-project", "--output-format", "json"]
        )

        assert result.exit_code == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "message" in output
        assert "code" in output

    def test_generate_json_interactive_not_supported(self):
        """Test that generate returns error for interactive mode with JSON."""
        result = runner.invoke(
            app,
            [
                "generate",
                "-s", "storage",
                "-n", "test-project",
                "-i",
                "--output-format", "json"
            ]
        )

        assert result.exit_code == 1
        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "Interactive mode" in output["message"]


class TestJsonOutputNoAnsiCodes:
    """Tests to ensure JSON output has no ANSI codes."""

    def test_list_modules_json_pure_json(self):
        """Test that list-modules JSON output is pure JSON."""
        result = runner.invoke(app, ["list-modules", "-f", "json"])
        assert result.exit_code == 0
        # Should be valid JSON without any decoration
        output = json.loads(result.stdout)
        assert isinstance(output, dict)

    def test_search_json_pure_json(self):
        """Test that search JSON output is pure JSON."""
        result = runner.invoke(app, ["search", "database", "-f", "json"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert isinstance(output, dict)

    def test_info_json_pure_json(self):
        """Test that info JSON output is pure JSON."""
        result = runner.invoke(app, ["info", "storage", "-f", "json"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert isinstance(output, dict)
