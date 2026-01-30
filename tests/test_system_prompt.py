"""Tests for custom system prompt functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tf_avm_agent.agent import (
    AGENT_SYSTEM_PROMPT,
    PromptMode,
    TerraformAVMAgent,
)
from tf_avm_agent.cli import app


runner = CliRunner()


class TestPromptMode:
    """Tests for PromptMode enum."""

    def test_prompt_mode_values(self):
        """Test that PromptMode has correct values."""
        assert PromptMode.REPLACE.value == "replace"
        assert PromptMode.PREPEND.value == "prepend"
        assert PromptMode.APPEND.value == "append"

    def test_prompt_mode_from_string(self):
        """Test PromptMode can be created from string."""
        assert PromptMode("replace") == PromptMode.REPLACE
        assert PromptMode("prepend") == PromptMode.PREPEND
        assert PromptMode("append") == PromptMode.APPEND

    def test_prompt_mode_invalid_string_raises(self):
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            PromptMode("invalid")


class TestSystemPromptResolution:
    """Tests for system prompt resolution."""

    def test_default_prompt_when_no_custom(self):
        """Test that default prompt is used when no custom prompt provided."""
        agent = TerraformAVMAgent()
        assert agent.system_prompt == AGENT_SYSTEM_PROMPT

    def test_direct_prompt_replacement(self):
        """Test direct prompt string replaces default."""
        custom = "You are a custom assistant."
        agent = TerraformAVMAgent(system_prompt=custom)
        assert agent.system_prompt == custom

    def test_prompt_prepend_mode(self):
        """Test prepend mode adds custom prompt before default."""
        custom = "Additional context here."
        agent = TerraformAVMAgent(
            system_prompt=custom,
            prompt_mode=PromptMode.PREPEND,
        )
        assert agent.system_prompt.startswith(custom)
        assert AGENT_SYSTEM_PROMPT in agent.system_prompt
        assert agent.system_prompt == f"{custom}\n\n{AGENT_SYSTEM_PROMPT}"

    def test_prompt_append_mode(self):
        """Test append mode adds custom prompt after default."""
        custom = "Additional context here."
        agent = TerraformAVMAgent(
            system_prompt=custom,
            prompt_mode=PromptMode.APPEND,
        )
        assert agent.system_prompt.endswith(custom)
        assert AGENT_SYSTEM_PROMPT in agent.system_prompt
        assert agent.system_prompt == f"{AGENT_SYSTEM_PROMPT}\n\n{custom}"

    def test_prompt_from_file(self):
        """Test loading prompt from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Custom prompt from file.")
            temp_path = f.name

        try:
            agent = TerraformAVMAgent(system_prompt_file=temp_path)
            assert agent.system_prompt == "Custom prompt from file."
        finally:
            os.unlink(temp_path)

    def test_prompt_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            TerraformAVMAgent(system_prompt_file="/nonexistent/path.txt")

    def test_string_prompt_mode_conversion(self):
        """Test that string prompt_mode is converted to enum."""
        agent = TerraformAVMAgent(
            system_prompt="Custom",
            prompt_mode="append",  # String instead of enum
        )
        assert AGENT_SYSTEM_PROMPT in agent.system_prompt
        assert agent.system_prompt.endswith("Custom")

    def test_prompt_file_with_prepend_mode(self):
        """Test loading prompt from file with prepend mode."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Prepended content.")
            temp_path = f.name

        try:
            agent = TerraformAVMAgent(
                system_prompt_file=temp_path,
                prompt_mode=PromptMode.PREPEND,
            )
            assert agent.system_prompt.startswith("Prepended content.")
            assert AGENT_SYSTEM_PROMPT in agent.system_prompt
        finally:
            os.unlink(temp_path)

    def test_direct_prompt_takes_priority_over_file(self):
        """Test that direct prompt takes priority over file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("File content.")
            temp_path = f.name

        try:
            agent = TerraformAVMAgent(
                system_prompt="Direct content.",
                system_prompt_file=temp_path,
            )
            assert agent.system_prompt == "Direct content."
        finally:
            os.unlink(temp_path)

    def test_system_prompt_property(self):
        """Test that system_prompt property returns the resolved prompt."""
        custom = "Custom prompt."
        agent = TerraformAVMAgent(system_prompt=custom)
        assert agent.system_prompt == custom

    def test_empty_custom_prompt_uses_default(self):
        """Test that empty custom prompt falls back to default."""
        agent = TerraformAVMAgent(system_prompt="")
        # Empty string is falsy, so default should be used
        assert agent.system_prompt == AGENT_SYSTEM_PROMPT


class TestEnvironmentVariablePrompt:
    """Tests for environment variable based prompts."""

    @patch.dict(os.environ, {"TF_AVM_AGENT_SYSTEM_PROMPT": "Env var prompt"})
    def test_env_var_prompt(self):
        """Test that TF_AVM_AGENT_SYSTEM_PROMPT env var is used."""
        agent = TerraformAVMAgent()
        assert agent.system_prompt == "Env var prompt"

    @patch.dict(os.environ, {"TF_AVM_AGENT_SYSTEM_PROMPT": "Env var prompt"})
    def test_direct_param_overrides_env_var(self):
        """Test that direct parameter overrides env var."""
        agent = TerraformAVMAgent(system_prompt="Direct param")
        assert agent.system_prompt == "Direct param"

    def test_env_var_file_prompt(self):
        """Test that TF_AVM_AGENT_SYSTEM_PROMPT_FILE env var is used."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Prompt from env var file.")
            temp_path = f.name

        try:
            with patch.dict(os.environ, {"TF_AVM_AGENT_SYSTEM_PROMPT_FILE": temp_path}):
                agent = TerraformAVMAgent()
                assert agent.system_prompt == "Prompt from env var file."
        finally:
            os.unlink(temp_path)

    @patch.dict(os.environ, {"TF_AVM_AGENT_SYSTEM_PROMPT": "Direct env var"})
    def test_direct_env_var_takes_priority_over_file_env_var(self):
        """Test that TF_AVM_AGENT_SYSTEM_PROMPT takes priority over FILE variant."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("File env var content.")
            temp_path = f.name

        try:
            with patch.dict(
                os.environ,
                {
                    "TF_AVM_AGENT_SYSTEM_PROMPT": "Direct env var",
                    "TF_AVM_AGENT_SYSTEM_PROMPT_FILE": temp_path,
                },
            ):
                agent = TerraformAVMAgent()
                assert agent.system_prompt == "Direct env var"
        finally:
            os.unlink(temp_path)

    def test_env_var_file_nonexistent_uses_default(self):
        """Test that nonexistent env var file falls back to default."""
        with patch.dict(
            os.environ, {"TF_AVM_AGENT_SYSTEM_PROMPT_FILE": "/nonexistent/file.txt"}
        ):
            agent = TerraformAVMAgent()
            assert agent.system_prompt == AGENT_SYSTEM_PROMPT


class TestPromptModeImport:
    """Tests for PromptMode import from package."""

    def test_prompt_mode_importable_from_package(self):
        """Test that PromptMode can be imported from tf_avm_agent."""
        from tf_avm_agent import PromptMode

        assert PromptMode.REPLACE.value == "replace"


class TestCLISystemPromptOptions:
    """Tests for CLI system prompt options."""

    def test_chat_help_shows_system_prompt_options(self):
        """Test that chat help shows system prompt options."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "--system-prompt" in result.output
        assert "--system-prompt-file" in result.output
        assert "--prompt-mode" in result.output

    def test_generate_help_shows_system_prompt_options(self):
        """Test that generate help shows system prompt options."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--system-prompt" in result.output
        assert "--system-prompt-file" in result.output
        assert "--prompt-mode" in result.output

    def test_chat_with_system_prompt(self):
        """Test chat command with custom system prompt."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent:
            mock_instance = mock_agent.return_value

            result = runner.invoke(
                app,
                ["chat", "--system-prompt", "Custom prompt"],
                input="quit\n",
            )

            mock_agent.assert_called_once()
            call_kwargs = mock_agent.call_args[1]
            assert call_kwargs["system_prompt"] == "Custom prompt"

    def test_chat_with_prompt_mode(self):
        """Test chat command with prompt mode."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent:
            mock_instance = mock_agent.return_value

            result = runner.invoke(
                app,
                ["chat", "--system-prompt", "Extra", "--prompt-mode", "append"],
                input="quit\n",
            )

            mock_agent.assert_called_once()
            call_kwargs = mock_agent.call_args[1]
            assert call_kwargs["prompt_mode"] == "append"

    def test_chat_with_system_prompt_file(self):
        """Test chat command with system prompt file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Prompt from file.")
            temp_path = f.name

        try:
            with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent:
                mock_instance = mock_agent.return_value

                result = runner.invoke(
                    app,
                    ["chat", "--system-prompt-file", temp_path],
                    input="quit\n",
                )

                mock_agent.assert_called_once()
                call_kwargs = mock_agent.call_args[1]
                assert call_kwargs["system_prompt"] == "Prompt from file."
        finally:
            os.unlink(temp_path)
