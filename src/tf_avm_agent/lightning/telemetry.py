"""Telemetry instrumentation for Agent Lightning."""

import asyncio
import functools
import logging
from typing import Any, Callable, TypeVar

from tf_avm_agent.lightning import LIGHTNING_AVAILABLE
from tf_avm_agent.lightning.config import (
    OUTPUT_TRUNCATION_LENGTH,
    TELEMETRY_BLOCKLIST_PARAMS,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _sanitize_data(data: dict | None) -> dict | None:
    """Remove sensitive parameters from telemetry data."""
    if data is None:
        return None
    sanitized = {}
    for key, value in data.items():
        if key.lower() in TELEMETRY_BLOCKLIST_PARAMS:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, str) and any(
            pattern in value.lower()
            for pattern in ("password=", "key=", "token=", "secret=")
        ):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    return sanitized


class TerraformAgentTracer:
    """Tracer for TF-AVM-Agent operations."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled and LIGHTNING_AVAILABLE
        self._task_id: str | None = None

    def start_task(self, task_id: str, input_data: dict) -> None:
        """Start tracking a new task."""
        if not self.enabled:
            return
        self._task_id = task_id
        import agentlightning as agl  # type: ignore[import-untyped]

        agl.emit_start(task_id=task_id, input=_sanitize_data(input_data))

    def emit_action(
        self,
        action_type: str,
        input_data: dict | None = None,
        output_data: dict | None = None,
    ) -> None:
        """Emit an action event."""
        if not self.enabled:
            return
        import agentlightning as agl  # type: ignore[import-untyped]

        agl.emit_action(
            task_id=self._task_id,
            action=action_type,
            input=_sanitize_data(input_data),
            output=_sanitize_data(output_data),
        )

    def emit_reward(self, reward: float, metadata: dict | None = None) -> None:
        """Emit a reward signal."""
        if not self.enabled:
            return
        import agentlightning as agl  # type: ignore[import-untyped]

        agl.emit_reward(
            task_id=self._task_id,
            reward=reward,
            metadata=metadata or {},
        )

    def end_task(self, success: bool, output: Any = None) -> None:
        """End the current task."""
        if not self.enabled:
            return
        import agentlightning as agl  # type: ignore[import-untyped]

        output_str = str(output)[:OUTPUT_TRUNCATION_LENGTH] if output else None
        agl.emit_end(task_id=self._task_id, success=success, output=output_str)
        self._task_id = None


def trace_tool(tool_name: str) -> Callable[[F], F]:
    """Decorator to trace tool invocations. Supports both sync and async functions."""

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = get_global_tracer()
                tracer.emit_action(
                    action_type=f"tool:{tool_name}",
                    input_data={
                        "args": str(args)[:OUTPUT_TRUNCATION_LENGTH],
                        "kwargs": str(kwargs)[:OUTPUT_TRUNCATION_LENGTH],
                    },
                )
                try:
                    result = await func(*args, **kwargs)
                    tracer.emit_action(
                        action_type=f"tool:{tool_name}:complete",
                        output_data={
                            "result": str(result)[:OUTPUT_TRUNCATION_LENGTH]
                        },
                    )
                    return result
                except Exception as e:
                    tracer.emit_action(
                        action_type=f"tool:{tool_name}:error",
                        output_data={
                            "error": str(e)[:OUTPUT_TRUNCATION_LENGTH]
                        },
                    )
                    raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = get_global_tracer()
                tracer.emit_action(
                    action_type=f"tool:{tool_name}",
                    input_data={
                        "args": str(args)[:OUTPUT_TRUNCATION_LENGTH],
                        "kwargs": str(kwargs)[:OUTPUT_TRUNCATION_LENGTH],
                    },
                )
                try:
                    result = func(*args, **kwargs)
                    tracer.emit_action(
                        action_type=f"tool:{tool_name}:complete",
                        output_data={
                            "result": str(result)[:OUTPUT_TRUNCATION_LENGTH]
                        },
                    )
                    return result
                except Exception as e:
                    tracer.emit_action(
                        action_type=f"tool:{tool_name}:error",
                        output_data={
                            "error": str(e)[:OUTPUT_TRUNCATION_LENGTH]
                        },
                    )
                    raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


# Global tracer instance
_global_tracer: TerraformAgentTracer | None = None


def get_global_tracer() -> TerraformAgentTracer:
    """Get the global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = TerraformAgentTracer(enabled=False)
    return _global_tracer


def set_global_tracer(tracer: TerraformAgentTracer) -> None:
    """Set the global tracer instance."""
    global _global_tracer
    _global_tracer = tracer
