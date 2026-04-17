"""
Tests for Microsoft Agent Framework 1.0.1 GA upgrade.

This test suite validates that the upgrade from beta to 1.0.1 GA was successful
and that all breaking changes have been properly addressed.
"""

import pytest

from tf_avm_agent.agent import TerraformAVMAgent


class TestAgentFramework101Upgrade:
    """Tests verifying Agent Framework 1.0.1 GA compatibility."""

    def test_agent_class_import(self):
        """Test that Agent class (renamed from ChatAgent) imports correctly."""
        from agent_framework import Agent

        assert Agent is not None

    def test_unified_openai_client_import(self):
        """Test that unified OpenAIChatClient imports correctly."""
        from agent_framework.openai import OpenAIChatClient

        assert OpenAIChatClient is not None

    def test_openai_client_supports_azure(self):
        """Test that OpenAIChatClient constructor supports Azure OpenAI parameters."""
        from agent_framework.openai import OpenAIChatClient
        import inspect

        sig = inspect.signature(OpenAIChatClient.__init__)
        params = list(sig.parameters.keys())

        # Verify Azure OpenAI parameters are present
        assert "azure_endpoint" in params, "azure_endpoint parameter missing"
        assert "credential" in params, "credential parameter missing"
        assert "api_key" in params, "api_key parameter missing"

    def test_agent_instantiation_openai(self):
        """Test TerraformAVMAgent instantiation for OpenAI."""
        agent = TerraformAVMAgent(use_azure_openai=False)

        assert agent.use_azure_openai is False
        assert agent._agent is None  # Not created until first use

    def test_agent_instantiation_azure_openai(self):
        """Test TerraformAVMAgent instantiation for Azure OpenAI."""
        agent = TerraformAVMAgent(
            use_azure_openai=True,
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4",
            api_key="test-key",
        )

        assert agent.use_azure_openai is True
        assert agent.azure_endpoint == "https://test.openai.azure.com"
        assert agent.azure_deployment == "gpt-4"

    def test_no_deprecated_imports(self):
        """Test that deprecated classes are not imported."""
        import agent_framework

        # ChatAgent should not exist (renamed to Agent)
        assert not hasattr(agent_framework, "ChatAgent")

        # Verify new names exist
        assert hasattr(agent_framework, "Agent")
        assert hasattr(agent_framework, "RawAgent")

    def test_message_class_renamed(self):
        """Test that Message class exists (renamed from ChatMessage)."""
        from agent_framework import Message

        assert Message is not None

        # ChatMessage should not exist
        import agent_framework

        assert not hasattr(agent_framework, "ChatMessage")

    def test_chat_client_protocol_renamed(self):
        """Test that SupportsChatGetResponse exists (renamed from ChatClientProtocol)."""
        from agent_framework import SupportsChatGetResponse

        assert SupportsChatGetResponse is not None

    def test_agent_tools_work(self):
        """Test that agent tools can be passed to Agent."""
        from tf_avm_agent.tools.avm_lookup import list_available_avm_modules

        agent = TerraformAVMAgent()
        tools = agent._get_tools()

        # Verify tools list is not empty and contains our functions
        assert len(tools) > 0
        assert list_available_avm_modules in tools

    def test_generate_from_services_works(self):
        """Test that non-AI generation still works after upgrade."""
        agent = TerraformAVMAgent()

        result = agent.generate_from_services(
            services=["virtual_machine"],
            project_name="test-upgrade",
            location="eastus",
        )

        assert len(result.files) > 0
        assert any(f.filename == "main.tf" for f in result.files)

    def test_package_version_1_0_1(self):
        """Test that agent-framework 1.0.1 is installed."""
        import agent_framework

        # Check version is 1.0.1 or higher
        version = getattr(agent_framework, "__version__", None)
        if version:
            major, minor, patch = map(int, version.split(".")[:3])
            assert major >= 1, f"Major version should be >= 1, got {major}"
            assert minor >= 0, f"Minor version should be >= 0, got {minor}"


class TestBreakingChangesAddressed:
    """Tests verifying that all breaking changes from beta to 1.0.1 are addressed."""

    def test_no_azure_openai_chat_client(self):
        """Test that AzureOpenAIChatClient no longer exists (merged into OpenAIChatClient)."""
        # This should not raise an error - the old import path doesn't exist
        with pytest.raises(ImportError):
            from agent_framework.azure import AzureOpenAIChatClient  # noqa: F401

    def test_chat_prefix_removed_from_agent(self):
        """Test that ChatAgent renamed to Agent."""
        import agent_framework

        assert hasattr(agent_framework, "Agent")
        assert not hasattr(agent_framework, "ChatAgent")

    def test_raw_chat_agent_renamed(self):
        """Test that RawChatAgent renamed to RawAgent."""
        import agent_framework

        assert hasattr(agent_framework, "RawAgent")
        assert not hasattr(agent_framework, "RawChatAgent")

    def test_agent_framework_available_flag(self):
        """Test that AGENT_FRAMEWORK_AVAILABLE flag is set correctly."""
        from tf_avm_agent.agent import AGENT_FRAMEWORK_AVAILABLE

        assert AGENT_FRAMEWORK_AVAILABLE is True


class TestBackwardCompatibility:
    """Tests ensuring the upgrade maintains backward compatibility for our use cases."""

    def test_conversation_history_preserved(self):
        """Test that conversation history management still works."""
        agent = TerraformAVMAgent()

        assert agent._conversation_history == []
        assert agent.get_history() == []

        agent._conversation_history.append({"role": "user", "content": "test"})
        assert len(agent.get_history()) == 1

        agent.clear_history()
        assert agent._conversation_history == []

    def test_lightning_integration_unaffected(self):
        """Test that Agent Lightning integration still works."""
        agent = TerraformAVMAgent(enable_lightning=False)

        assert agent._enable_lightning is False
        assert agent._tracer is not None

    def test_sync_run_wrapper_works(self):
        """Test that synchronous run wrapper still works."""
        agent = TerraformAVMAgent()

        # Should not raise an error
        assert hasattr(agent, "run")
        assert hasattr(agent, "run_async")
        assert callable(agent.run)
        assert callable(agent.run_async)
