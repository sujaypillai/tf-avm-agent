"""Agent Lightning configuration for TF-AVM-Agent."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tf_avm_agent.lightning import LIGHTNING_AVAILABLE

# Configurable constants (extracted from implementation plan Section 7.1)
MODULE_COUNT_REWARD_THRESHOLD: float = 5.0
MAX_SELF_CORRECTION_ITERATIONS: int = 3
OUTPUT_TRUNCATION_LENGTH: int = 500

TELEMETRY_BLOCKLIST_PARAMS: frozenset[str] = frozenset({
    "api_key",
    "password",
    "secret",
    "token",
    "connection_string",
    "client_secret",
    "sas_token",
    "access_key",
})


@dataclass
class LightningConfig:
    """Configuration for Agent Lightning integration."""

    # Store configuration
    store_backend: str = "local"
    store_path: str = str(
        Path.home() / ".cache" / "tf-avm-agent" / "lightning_store"
    )

    # Telemetry settings
    enable_telemetry: bool = True
    trace_level: str = "full"  # "minimal", "standard", "full"

    # Training settings
    algorithm: str = "grpo"
    batch_size: int = 32
    learning_rate: float = 1e-5

    # Reward settings
    reward_normalization: bool = True
    discount_factor: float = 0.99
    clip_ratio: float = 0.2

    # Trajectory settings
    max_trajectory_length: int = 10

    # Checkpointing
    checkpoint_interval: int = 100
    checkpoint_dir: str = "./checkpoints"


DEFAULT_CONFIG = LightningConfig()


def get_lightning_store(config: LightningConfig | None = None) -> Any:
    """Get a LightningStore instance.

    Returns None if agentlightning is not available.
    """
    if not LIGHTNING_AVAILABLE:
        return None
    from agentlightning import LightningStore  # type: ignore[import-untyped]

    cfg = config or DEFAULT_CONFIG
    return LightningStore(config=cfg)
