"""Tests for Agent Lightning telemetry."""

from unittest.mock import MagicMock, patch

import pytest

from tf_avm_agent.lightning.telemetry import (
    TerraformAgentTracer,
    _sanitize_data,
    get_global_tracer,
    set_global_tracer,
    trace_tool,
)


class TestSanitizeData:
    """Tests for sensitive data filtering."""

    def test_returns_none_for_none(self):
        assert _sanitize_data(None) is None

    def test_passes_through_safe_data(self):
        data = {"prompt": "hello", "count": 42}
        result = _sanitize_data(data)
        assert result == data

    def test_redacts_blocklisted_keys(self):
        data = {
            "prompt": "hello",
            "api_key": "sk-secret123",
            "password": "p@ss",
            "token": "tok123",
        }
        result = _sanitize_data(data)
        assert result["prompt"] == "hello"
        assert result["api_key"] == "***REDACTED***"
        assert result["password"] == "***REDACTED***"
        assert result["token"] == "***REDACTED***"

    def test_redacts_values_with_sensitive_patterns(self):
        data = {"connection": "Server=x;Password=secret123;"}
        result = _sanitize_data(data)
        assert result["connection"] == "***REDACTED***"

    def test_case_insensitive_key_matching(self):
        data = {"API_KEY": "secret", "Password": "secret"}
        result = _sanitize_data(data)
        assert result["API_KEY"] == "***REDACTED***"
        assert result["Password"] == "***REDACTED***"


class TestTerraformAgentTracer:
    """Tests for the telemetry tracer."""

    def test_tracer_disabled_when_lightning_unavailable(self):
        """When LIGHTNING_AVAILABLE is False, tracer is disabled."""
        tracer = TerraformAgentTracer(enabled=True)
        # Since agentlightning is not installed, enabled should be False
        assert tracer.enabled is False

    def test_tracer_disabled_does_not_raise(self):
        """Disabled tracer should be a no-op."""
        tracer = TerraformAgentTracer(enabled=False)
        tracer.start_task("test", {"prompt": "hello"})
        tracer.emit_action("test_action")
        tracer.emit_action("test", {"key": "val"}, {"out": "val"})
        tracer.emit_reward(1.0)
        tracer.emit_reward(0.5, {"meta": "data"})
        tracer.end_task(True)
        tracer.end_task(False, output="error")

    def test_task_id_tracking(self):
        """Tracer stores task_id when started (even if disabled)."""
        tracer = TerraformAgentTracer(enabled=False)
        assert tracer._task_id is None
        # When disabled, start_task doesn't set _task_id
        tracer.start_task("test-123", {"prompt": "test"})
        assert tracer._task_id is None  # disabled, so no-op


class TestTraceToolDecorator:
    """Tests for the trace_tool decorator."""

    def test_sync_function_preserved(self):
        """trace_tool preserves sync function behavior and metadata."""

        @trace_tool("test_tool")
        def add_one(x: int) -> int:
            """Add one to x."""
            return x + 1

        assert add_one(5) == 6
        assert add_one.__name__ == "add_one"
        assert add_one.__doc__ == "Add one to x."

    @pytest.mark.asyncio
    async def test_async_function_preserved(self):
        """trace_tool preserves async function behavior and metadata."""

        @trace_tool("test_async_tool")
        async def add_one_async(x: int) -> int:
            """Add one to x async."""
            return x + 1

        result = await add_one_async(5)
        assert result == 6
        assert add_one_async.__name__ == "add_one_async"
        assert add_one_async.__doc__ == "Add one to x async."

    def test_sync_exception_propagates(self):
        """trace_tool re-raises exceptions from sync functions."""

        @trace_tool("failing_tool")
        def fail():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            fail()

    @pytest.mark.asyncio
    async def test_async_exception_propagates(self):
        """trace_tool re-raises exceptions from async functions."""

        @trace_tool("failing_async_tool")
        async def fail_async():
            raise ValueError("async test error")

        with pytest.raises(ValueError, match="async test error"):
            await fail_async()


class TestGlobalTracer:
    """Tests for global tracer management."""

    def test_get_global_tracer_returns_default(self):
        """Default global tracer should be disabled."""
        # Reset global state
        import tf_avm_agent.lightning.telemetry as mod

        mod._global_tracer = None

        tracer = get_global_tracer()
        assert tracer is not None
        assert tracer.enabled is False

    def test_set_global_tracer(self):
        """set_global_tracer replaces the global instance."""
        custom = TerraformAgentTracer(enabled=False)
        set_global_tracer(custom)
        assert get_global_tracer() is custom

        # Clean up
        import tf_avm_agent.lightning.telemetry as mod

        mod._global_tracer = None
