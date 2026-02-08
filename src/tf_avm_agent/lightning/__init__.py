"""
Agent Lightning integration for TF-AVM-Agent.

This module provides optional RL training capabilities via Microsoft's
Agent Lightning framework. All features are behind an ``enable_lightning``
flag and degrade gracefully when the agentlightning package is not installed.
"""

try:
    import agentlightning  # noqa: F401

    LIGHTNING_AVAILABLE = True
except ImportError:
    LIGHTNING_AVAILABLE = False

__all__ = ["LIGHTNING_AVAILABLE"]
