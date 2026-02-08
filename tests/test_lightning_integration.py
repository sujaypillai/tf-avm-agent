"""Integration tests for Lightning-enabled agent."""

from unittest.mock import patch

import pytest

from tf_avm_agent.agent import TerraformAVMAgent
from tf_avm_agent.lightning import LIGHTNING_AVAILABLE
from tf_avm_agent.lightning.ab_testing import should_use_lightning_model
from tf_avm_agent.lightning.config import (
    DEFAULT_CONFIG,
    LightningConfig,
    MODULE_COUNT_REWARD_THRESHOLD,
    MAX_SELF_CORRECTION_ITERATIONS,
    OUTPUT_TRUNCATION_LENGTH,
    get_lightning_store,
)


class TestLightningAgentInit:
    """Tests for agent initialization with lightning."""

    def test_agent_init_default_no_lightning(self):
        """By default, lightning should be disabled."""
        agent = TerraformAVMAgent()
        assert agent._enable_lightning is False
        assert agent._tracer.enabled is False

    def test_agent_init_with_lightning_disabled(self):
        """Explicit disable should work."""
        agent = TerraformAVMAgent(enable_lightning=False)
        assert agent._enable_lightning is False
        assert agent._tracer.enabled is False

    def test_agent_init_with_lightning_enabled_no_package(self):
        """When agentlightning is not installed, tracer is disabled."""
        agent = TerraformAVMAgent(enable_lightning=True)
        # LIGHTNING_AVAILABLE is False since agentlightning is not installed
        assert agent._enable_lightning is True
        assert agent._tracer.enabled is False


class TestGenerateWithLightning:
    """Tests for generate_from_services with lightning instrumentation."""

    def test_generate_still_works_with_lightning_enabled(self):
        """generate_from_services should work with lightning enabled."""
        agent = TerraformAVMAgent(enable_lightning=True)
        result = agent.generate_from_services(
            services=["storage_account"],
            project_name="test-lightning",
        )
        assert result is not None
        assert len(result.files) > 0
        filenames = [f.filename for f in result.files]
        assert "main.tf" in filenames

    def test_generate_regression_without_lightning(self):
        """Regression: existing generate_from_services works with lightning disabled."""
        agent = TerraformAVMAgent()
        result = agent.generate_from_services(
            services=["virtual_machine"],
            project_name="regression-test",
        )
        assert result is not None
        filenames = [f.filename for f in result.files]
        assert "main.tf" in filenames
        assert "providers.tf" in filenames


class TestLightningConfig:
    """Tests for lightning configuration."""

    def test_default_config(self):
        assert DEFAULT_CONFIG.algorithm == "grpo"
        assert DEFAULT_CONFIG.batch_size == 32
        assert DEFAULT_CONFIG.discount_factor == 0.99

    def test_custom_config(self):
        config = LightningConfig(batch_size=64, learning_rate=1e-4)
        assert config.batch_size == 64
        assert config.learning_rate == 1e-4

    def test_constants_exported(self):
        assert MODULE_COUNT_REWARD_THRESHOLD == 5.0
        assert MAX_SELF_CORRECTION_ITERATIONS == 3
        assert OUTPUT_TRUNCATION_LENGTH == 500

    def test_lightning_store_returns_none(self):
        """Without agentlightning, store should return None."""
        store = get_lightning_store()
        assert store is None


class TestABTesting:
    """Tests for A/B testing utility."""

    def test_disabled_by_default(self):
        """A/B testing should be disabled by default."""
        assert should_use_lightning_model("session-1") is False

    def test_disabled_without_session(self):
        """Should return False without session_id."""
        with patch.dict(
            "os.environ",
            {"TF_AVM_LIGHTNING_ENABLED": "true", "TF_AVM_LIGHTNING_ROLLOUT": "1.0"},
        ):
            assert should_use_lightning_model(None) is False

    def test_deterministic_assignment(self):
        """Same session_id should always get same assignment."""
        with patch.dict(
            "os.environ",
            {"TF_AVM_LIGHTNING_ENABLED": "true", "TF_AVM_LIGHTNING_ROLLOUT": "0.5"},
        ):
            result1 = should_use_lightning_model("session-abc")
            result2 = should_use_lightning_model("session-abc")
            assert result1 == result2

    def test_full_rollout(self):
        """100% rollout should include all sessions."""
        with patch.dict(
            "os.environ",
            {"TF_AVM_LIGHTNING_ENABLED": "true", "TF_AVM_LIGHTNING_ROLLOUT": "1.0"},
        ):
            assert should_use_lightning_model("any-session") is True

    def test_zero_rollout(self):
        """0% rollout should exclude all sessions."""
        with patch.dict(
            "os.environ",
            {"TF_AVM_LIGHTNING_ENABLED": "true", "TF_AVM_LIGHTNING_ROLLOUT": "0.0"},
        ):
            assert should_use_lightning_model("any-session") is False


class TestLightningAvailability:
    """Tests for the LIGHTNING_AVAILABLE flag."""

    def test_lightning_not_available(self):
        """agentlightning should not be available in test environment."""
        assert LIGHTNING_AVAILABLE is False
