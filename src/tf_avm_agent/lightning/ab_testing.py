"""Deterministic A/B testing for Lightning model rollout."""

import hashlib
import os


def should_use_lightning_model(session_id: str | None = None) -> bool:
    """Determine if the Lightning-trained model should be used.

    Uses deterministic hashing of the session ID for consistent
    assignment across requests in the same session.

    Args:
        session_id: Unique session identifier for deterministic assignment.

    Returns:
        True if the Lightning model should be used for this session.
    """
    enabled = os.getenv("TF_AVM_LIGHTNING_ENABLED", "false") == "true"
    if not enabled:
        return False

    rollout_pct = float(os.getenv("TF_AVM_LIGHTNING_ROLLOUT", "0.0"))
    if session_id is None:
        return False

    hash_val = (
        int(hashlib.sha256(session_id.encode()).hexdigest(), 16) % 100
    )
    return hash_val < (rollout_pct * 100)
