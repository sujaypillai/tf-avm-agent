"""Tests for the version fetcher module."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tf_avm_agent.registry.version_fetcher import (
    TERRAFORM_REGISTRY_API,
    ModuleVersion,
    VersionCache,
    batch_fetch_versions_async,
    clear_version_cache,
    fetch_all_versions_async,
    fetch_latest_version,
    fetch_latest_version_async,
    get_cached_version,
    parse_module_source,
    refresh_version,
)


class TestParseModuleSource:
    """Tests for parse_module_source function."""

    def test_valid_source(self):
        """Test parsing a valid module source."""
        namespace, name, provider = parse_module_source(
            "Azure/avm-res-compute-virtualmachine/azurerm"
        )
        assert namespace == "Azure"
        assert name == "avm-res-compute-virtualmachine"
        assert provider == "azurerm"

    def test_invalid_source_too_few_parts(self):
        """Test parsing an invalid source with too few parts."""
        with pytest.raises(ValueError, match="Invalid module source format"):
            parse_module_source("Azure/avm-module")

    def test_invalid_source_too_many_parts(self):
        """Test parsing an invalid source with too many parts."""
        with pytest.raises(ValueError, match="Invalid module source format"):
            parse_module_source("Azure/avm/res/compute/azurerm")


class TestVersionCache:
    """Tests for VersionCache class."""

    def test_cache_set_and_get(self):
        """Test setting and getting a cached value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            cache = VersionCache(cache_file=cache_file, ttl_seconds=3600)

            cache.set("test/module/provider", "1.0.0")
            result = cache.get("test/module/provider")

            assert result == "1.0.0"

    def test_cache_miss(self):
        """Test getting a non-existent cache entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            cache = VersionCache(cache_file=cache_file)

            result = cache.get("nonexistent/module/provider")

            assert result is None

    def test_cache_expired(self):
        """Test that expired cache entries are not returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            cache = VersionCache(cache_file=cache_file, ttl_seconds=0)  # Immediate expiry

            cache.set("test/module/provider", "1.0.0")
            # Entry should be immediately expired
            result = cache.get("test/module/provider")

            assert result is None

    def test_cache_clear(self):
        """Test clearing the cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            cache = VersionCache(cache_file=cache_file)

            cache.set("test/module/provider", "1.0.0")
            cache.clear()
            result = cache.get("test/module/provider")

            assert result is None
            assert not cache_file.exists()

    def test_cache_persistence(self):
        """Test that cache persists to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"

            # Create cache and set value
            cache1 = VersionCache(cache_file=cache_file, ttl_seconds=3600)
            cache1.set("test/module/provider", "1.0.0")

            # Create new cache instance and verify value is loaded
            cache2 = VersionCache(cache_file=cache_file, ttl_seconds=3600)
            result = cache2.get("test/module/provider")

            assert result == "1.0.0"


class TestFetchLatestVersionAsync:
    """Tests for fetch_latest_version_async function."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        """Test successful version fetch from registry."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"version": "0.20.0"}
        mock_response.raise_for_status = MagicMock()

        with patch("tf_avm_agent.registry.version_fetcher._version_cache") as mock_cache:
            mock_cache.get.return_value = None  # No cached version

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_client

                result = await fetch_latest_version_async(
                    "Azure/avm-res-compute-virtualmachine/azurerm"
                )

                assert result == "0.20.0"
                mock_cache.set.assert_called_once_with(
                    "Azure/avm-res-compute-virtualmachine/azurerm", "0.20.0"
                )

    @pytest.mark.asyncio
    async def test_cached_version_returned(self):
        """Test that cached version is returned without API call."""
        with patch("tf_avm_agent.registry.version_fetcher._version_cache") as mock_cache:
            mock_cache.get.return_value = "0.19.0"  # Cached version

            with patch("httpx.AsyncClient") as mock_client_class:
                result = await fetch_latest_version_async(
                    "Azure/avm-res-compute-virtualmachine/azurerm"
                )

                assert result == "0.19.0"
                mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_source_returns_none(self):
        """Test that invalid source returns None."""
        result = await fetch_latest_version_async("invalid-source")
        assert result is None


class TestFetchAllVersionsAsync:
    """Tests for fetch_all_versions_async function."""

    @pytest.mark.asyncio
    async def test_successful_fetch_all(self):
        """Test successful fetch of all versions."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "modules": [
                {
                    "versions": [
                        {"version": "0.20.0"},
                        {"version": "0.19.3"},
                        {"version": "0.19.2"},
                    ]
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await fetch_all_versions_async(
                "Azure/avm-res-compute-virtualmachine/azurerm"
            )

            assert result == ["0.20.0", "0.19.3", "0.19.2"]


class TestBatchFetchVersionsAsync:
    """Tests for batch_fetch_versions_async function."""

    @pytest.mark.asyncio
    async def test_batch_fetch(self):
        """Test batch fetching of multiple module versions."""
        sources = [
            "Azure/avm-res-compute-virtualmachine/azurerm",
            "Azure/avm-res-storage-storageaccount/azurerm",
        ]

        with patch(
            "tf_avm_agent.registry.version_fetcher.fetch_latest_version_async"
        ) as mock_fetch:
            mock_fetch.side_effect = ["0.20.0", "0.5.0"]

            result = await batch_fetch_versions_async(sources)

            assert result == {
                "Azure/avm-res-compute-virtualmachine/azurerm": "0.20.0",
                "Azure/avm-res-storage-storageaccount/azurerm": "0.5.0",
            }


class TestSyncWrappers:
    """Tests for synchronous wrapper functions."""

    def test_fetch_latest_version_sync(self):
        """Test synchronous fetch_latest_version wrapper."""
        with patch(
            "tf_avm_agent.registry.version_fetcher._version_cache"
        ) as mock_cache:
            mock_cache.get.return_value = "0.20.0"

            result = fetch_latest_version(
                "Azure/avm-res-compute-virtualmachine/azurerm"
            )

            assert result == "0.20.0"

    def test_get_cached_version(self):
        """Test get_cached_version function."""
        with patch(
            "tf_avm_agent.registry.version_fetcher._version_cache"
        ) as mock_cache:
            mock_cache.get.return_value = "0.20.0"

            result = get_cached_version(
                "Azure/avm-res-compute-virtualmachine/azurerm"
            )

            assert result == "0.20.0"

    def test_clear_version_cache(self):
        """Test clear_version_cache function."""
        with patch(
            "tf_avm_agent.registry.version_fetcher._version_cache"
        ) as mock_cache:
            clear_version_cache()

            mock_cache.clear.assert_called_once()
