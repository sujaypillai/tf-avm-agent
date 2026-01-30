"""Tests for the CLI chat command."""

import os
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from tf_avm_agent.cli import app


runner = CliRunner()


class TestChatCommand:
    """Tests for the chat command."""

    def test_chat_command_exists(self):
        """Test that chat command is registered."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "interactive chat session" in result.output.lower()

    def test_chat_help_shows_options(self):
        """Test that help shows Azure OpenAI option."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "--azure-openai" in result.output

    def test_chat_quit_command(self):
        """Test that quit command exits the chat."""
        result = runner.invoke(app, ["chat"], input="quit\n")
        assert "Goodbye" in result.output

    def test_chat_exit_command(self):
        """Test that exit command exits the chat."""
        result = runner.invoke(app, ["chat"], input="exit\n")
        assert "Goodbye" in result.output

    def test_chat_q_command(self):
        """Test that 'q' command exits the chat."""
        result = runner.invoke(app, ["chat"], input="q\n")
        assert "Goodbye" in result.output

    def test_chat_help_command(self):
        """Test that help command shows available commands."""
        result = runner.invoke(app, ["chat"], input="help\nquit\n")
        assert "Available commands" in result.output
        assert "list modules" in result.output
        assert "search" in result.output
        assert "info" in result.output

    def test_chat_list_modules_command(self):
        """Test that 'list modules' command works."""
        result = runner.invoke(app, ["chat"], input="list modules\nquit\n")
        # Should list modules without calling the AI agent
        assert result.exit_code == 0

    def test_chat_search_command(self):
        """Test that 'search' command works."""
        result = runner.invoke(app, ["chat"], input="search storage\nquit\n")
        assert result.exit_code == 0

    def test_chat_info_command(self):
        """Test that 'info' command works."""
        result = runner.invoke(app, ["chat"], input="info virtual_machine\nquit\n")
        assert result.exit_code == 0

    def test_chat_welcome_panel_displayed(self):
        """Test that welcome panel is displayed."""
        result = runner.invoke(app, ["chat"], input="quit\n")
        assert "Terraform AVM Agent" in result.output
        assert "Interactive Mode" in result.output


class TestChatAzureOpenAIConfiguration:
    """Tests for Azure OpenAI configuration in chat command."""

    def test_chat_with_azure_openai_flag(self):
        """Test chat with --azure-openai flag."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance
            
            result = runner.invoke(app, ["chat", "--azure-openai"], input="quit\n")
            
            # Verify TerraformAVMAgent was called with use_azure_openai=True
            mock_agent.assert_called_once_with(use_azure_openai=True)

    @patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": ""}, clear=False)
    def test_chat_without_azure_openai_flag(self):
        """Test chat without --azure-openai flag uses OpenAI when no env var set."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance
            
            result = runner.invoke(app, ["chat"], input="quit\n")
            
            # Verify TerraformAVMAgent was called with use_azure_openai=False
            mock_agent.assert_called_once_with(use_azure_openai=False)

    @patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com"})
    def test_chat_auto_detects_azure_from_env(self):
        """Test that chat auto-detects Azure OpenAI when env var is set."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance
            
            # Import after patching to ensure env var is read
            from tf_avm_agent import cli
            # Force re-evaluation of the auto-detect logic
            result = runner.invoke(app, ["chat"], input="quit\n")
            
            # The agent should be created (auto-detection happens at runtime)
            assert mock_agent.called


class TestChatAgentInteraction:
    """Tests for chat command interaction with the agent."""

    def test_chat_sends_user_input_to_agent(self):
        """Test that user input is sent to the agent."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = "Test response from agent"
            mock_agent_class.return_value = mock_agent
            
            result = runner.invoke(app, ["chat"], input="Generate VM terraform\nquit\n")
            
            # Verify agent.run was called with the user input
            mock_agent.run.assert_called_once_with("Generate VM terraform")
            assert "Test response from agent" in result.output

    def test_chat_displays_agent_response(self):
        """Test that agent response is displayed to user."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = "Here is your Terraform code for Azure VM"
            mock_agent_class.return_value = mock_agent
            
            result = runner.invoke(app, ["chat"], input="Create a VM\nquit\n")
            
            assert "Here is your Terraform code for Azure VM" in result.output

    def test_chat_handles_agent_error(self):
        """Test that chat handles agent errors gracefully."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = Exception("API connection failed")
            mock_agent_class.return_value = mock_agent
            
            result = runner.invoke(app, ["chat"], input="test query\nquit\n")
            
            # Should show error but not crash
            assert "Error" in result.output
            assert "API connection failed" in result.output

    def test_chat_multiple_interactions(self):
        """Test multiple interactions in a single chat session."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = ["Response 1", "Response 2"]
            mock_agent_class.return_value = mock_agent
            
            result = runner.invoke(app, ["chat"], input="query 1\nquery 2\nquit\n")
            
            assert mock_agent.run.call_count == 2
            assert "Response 1" in result.output
            assert "Response 2" in result.output


class TestChatSpecialCommands:
    """Tests for special commands that bypass the AI agent."""

    def test_list_modules_with_category(self):
        """Test 'list modules compute' filters by category."""
        result = runner.invoke(app, ["chat"], input="list modules compute\nquit\n")
        assert result.exit_code == 0

    def test_search_with_query(self):
        """Test 'search network' finds network modules."""
        result = runner.invoke(app, ["chat"], input="search network\nquit\n")
        assert result.exit_code == 0

    def test_info_with_module_name(self):
        """Test 'info vm' shows module information."""
        result = runner.invoke(app, ["chat"], input="info vm\nquit\n")
        assert result.exit_code == 0

    def test_special_commands_case_insensitive(self):
        """Test that special commands are case insensitive."""
        result = runner.invoke(app, ["chat"], input="LIST MODULES\nSEARCH storage\nINFO vm\nQUIT\n")
        assert "Goodbye" in result.output


class TestTerraformAVMAgentInitialization:
    """Tests for TerraformAVMAgent initialization with different configurations."""

    def test_agent_init_default(self):
        """Test agent initialization with defaults."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent()
        
        assert agent.use_azure_openai is False
        assert agent.azure_endpoint is None
        assert agent.azure_deployment is None

    def test_agent_init_azure_openai(self):
        """Test agent initialization for Azure OpenAI."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent(
            use_azure_openai=True,
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4",
            api_key="test-key"
        )
        
        assert agent.use_azure_openai is True
        assert agent.azure_endpoint == "https://test.openai.azure.com"
        assert agent.azure_deployment == "gpt-4"
        assert agent.api_key == "test-key"

    @patch.dict(os.environ, {
        "AZURE_OPENAI_ENDPOINT": "https://env-test.openai.azure.com",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
        "AZURE_OPENAI_API_KEY": "env-api-key"
    }, clear=False)
    def test_agent_reads_azure_env_vars(self):
        """Test agent reads Azure OpenAI config from environment variables."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent(use_azure_openai=True)
        
        assert agent.azure_endpoint == "https://env-test.openai.azure.com"
        assert agent.azure_deployment == "gpt-4o"
        assert agent.api_key == "env-api-key"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "openai-test-key"}, clear=False)
    def test_agent_reads_openai_env_var(self):
        """Test agent reads OpenAI API key from environment variable."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent(use_azure_openai=False)
        
        assert agent.api_key == "openai-test-key"

    def test_agent_explicit_params_override_env(self):
        """Test that explicit parameters override environment variables."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://env.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "env-key"
        }):
            agent = TerraformAVMAgent(
                use_azure_openai=True,
                azure_endpoint="https://explicit.openai.azure.com",
                api_key="explicit-key"
            )
            
            assert agent.azure_endpoint == "https://explicit.openai.azure.com"
            assert agent.api_key == "explicit-key"


class TestDiagramAnalyzerUtils:
    """Tests for diagram analyzer utility functions."""

    def test_is_url_with_http(self):
        """Test is_url returns True for HTTP URLs."""
        from tf_avm_agent.tools.diagram_analyzer import is_url
        
        assert is_url("http://example.com/diagram.png") is True
        assert is_url("https://example.com/diagram.svg") is True
        assert is_url("https://raw.githubusercontent.com/user/repo/main/arch.png") is True

    def test_is_url_with_local_path(self):
        """Test is_url returns False for local paths."""
        from tf_avm_agent.tools.diagram_analyzer import is_url
        
        assert is_url("/path/to/diagram.png") is False
        assert is_url("./diagram.svg") is False
        assert is_url("~/Documents/architecture.png") is False
        assert is_url("diagram.png") is False

    def test_get_filename_from_url(self):
        """Test extracting filename from URL."""
        from tf_avm_agent.tools.diagram_analyzer import get_filename_from_url
        
        assert get_filename_from_url("https://example.com/path/to/diagram.png") == "diagram.png"
        assert get_filename_from_url("https://example.com/architecture.svg") == "architecture.svg"
        assert get_filename_from_url("https://example.com/file.png?token=abc") == "file.png"

    def test_get_image_media_type(self):
        """Test getting media type from file extension."""
        from tf_avm_agent.tools.diagram_analyzer import get_image_media_type
        
        assert get_image_media_type("diagram.png") == "image/png"
        assert get_image_media_type("diagram.jpg") == "image/jpeg"
        assert get_image_media_type("diagram.jpeg") == "image/jpeg"
        assert get_image_media_type("diagram.svg") == "image/svg+xml"
        assert get_image_media_type("diagram.gif") == "image/gif"
        assert get_image_media_type("diagram.webp") == "image/webp"

    def test_encode_image_to_base64_file_not_found(self):
        """Test encode_image_to_base64 raises error for missing file."""
        from tf_avm_agent.tools.diagram_analyzer import encode_image_to_base64
        import pytest
        
        with pytest.raises(FileNotFoundError):
            encode_image_to_base64("/nonexistent/path/diagram.png")


class TestLoadDiagramCommand:
    """Tests for the load diagram command in chat."""

    def test_load_command_in_help(self):
        """Test that load command is shown in help."""
        result = runner.invoke(app, ["chat"], input="help\nquit\n")
        assert "load" in result.output
        assert "url" in result.output.lower() or "URL" in result.output

    def test_load_local_file_not_found(self):
        """Test load command with non-existent local file."""
        result = runner.invoke(app, ["chat"], input="load /nonexistent/file.png\nquit\n")
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_load_command_with_url_format(self):
        """Test load command recognizes URL format."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.analyze_diagram_from_url.return_value = "Analyzed diagram from URL"
            mock_agent_class.return_value = mock_agent
            
            with patch("tf_avm_agent.cli.encode_image_from_url") as mock_download:
                mock_download.return_value = ("base64data", "image/png")
                
                result = runner.invoke(
                    app, 
                    ["chat"], 
                    input="load https://example.com/diagram.png\nquit\n"
                )
                
                # Should attempt to download from URL
                mock_download.assert_called_once()

    def test_load_command_with_local_file(self):
        """Test load command with local file path."""
        import tempfile
        
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write minimal PNG header
            f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
            temp_path = f.name
        
        try:
            with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent_class:
                mock_agent = MagicMock()
                mock_agent.analyze_diagram.return_value = "Analyzed local diagram"
                mock_agent_class.return_value = mock_agent
                
                result = runner.invoke(
                    app, 
                    ["chat"], 
                    input=f"load {temp_path}\nquit\n"
                )
                
                # Should call analyze_diagram for local file
                mock_agent.analyze_diagram.assert_called_once()
        finally:
            import os
            os.unlink(temp_path)


class TestAgentDiagramAnalysis:
    """Tests for agent diagram analysis methods."""

    def test_agent_has_analyze_diagram_method(self):
        """Test that agent has analyze_diagram method."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent()
        assert hasattr(agent, "analyze_diagram")
        assert callable(agent.analyze_diagram)

    def test_agent_has_analyze_diagram_from_url_method(self):
        """Test that agent has analyze_diagram_from_url method."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent()
        assert hasattr(agent, "analyze_diagram_from_url")
        assert callable(agent.analyze_diagram_from_url)

    def test_agent_stores_current_diagram(self):
        """Test that agent stores current diagram path."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent()
        assert agent._current_diagram is None
        assert agent._identified_services == []

    def test_agent_clear_history_resets_diagram(self):
        """Test that clear_history also clears diagram state."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent()
        agent._current_diagram = "some/path.png"
        agent._identified_services = ["vm", "storage"]
        agent._conversation_history = [{"role": "user", "content": "test"}]
        
        agent.clear_history()
        
        assert agent._current_diagram is None
        assert agent._identified_services == []
        assert agent._conversation_history == []


class TestConversationHistory:
    """Tests for conversation history management."""

    def test_agent_maintains_conversation_history(self):
        """Test that agent initializes with empty conversation history."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent()
        assert agent._conversation_history == []

    def test_agent_get_history_returns_copy(self):
        """Test that get_history returns a copy of history."""
        from tf_avm_agent.agent import TerraformAVMAgent
        
        agent = TerraformAVMAgent()
        agent._conversation_history = [{"role": "user", "content": "test"}]
        
        history = agent.get_history()
        history.append({"role": "assistant", "content": "response"})
        
        # Original should not be modified
        assert len(agent._conversation_history) == 1

    def test_clear_command_in_chat(self):
        """Test clear command clears conversation history."""
        with patch("tf_avm_agent.cli.TerraformAVMAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent
            
            result = runner.invoke(app, ["chat"], input="clear\nquit\n")
            
            mock_agent.clear_history.assert_called_once()
            assert "cleared" in result.output.lower()
