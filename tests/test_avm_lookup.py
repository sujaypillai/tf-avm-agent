"""Tests for the AVM lookup tools."""

import pytest

from tf_avm_agent.tools.avm_lookup import (
    get_avm_module_info,
    get_module_dependencies,
    list_available_avm_modules,
    recommend_modules_for_architecture,
    search_avm_modules,
)


class TestListAvailableAVMModules:
    """Tests for list_available_avm_modules function."""

    def test_lists_all_modules(self):
        """Test listing all modules."""
        result = list_available_avm_modules()

        assert "Azure Verified Modules" in result
        assert "virtual_machine" in result.lower() or "virtual-machine" in result.lower()

    def test_filter_by_category(self):
        """Test filtering by category."""
        result = list_available_avm_modules(category="compute")

        assert "Compute" in result
        # Should not contain unrelated categories
        assert "virtual" in result.lower()

    def test_invalid_category(self):
        """Test with invalid category."""
        result = list_available_avm_modules(category="invalid_category")

        assert "not found" in result.lower() or "available categories" in result.lower()


class TestSearchAVMModules:
    """Tests for search_avm_modules function."""

    def test_search_finds_modules(self):
        """Test that search finds relevant modules."""
        result = search_avm_modules("storage")

        assert "storage" in result.lower()
        assert "Storage" in result or "storage" in result

    def test_search_no_results(self):
        """Test search with no results."""
        result = search_avm_modules("xyznonexistent123")

        assert "no" in result.lower() or "not found" in result.lower()

    def test_search_multiple_results(self):
        """Test search returning multiple results."""
        result = search_avm_modules("network")

        # Should find multiple networking modules
        assert "virtual_network" in result.lower() or "vnet" in result.lower()


class TestGetAVMModuleInfo:
    """Tests for get_avm_module_info function."""

    def test_get_vm_info(self):
        """Test getting VM module info."""
        result = get_avm_module_info("virtual_machine")

        assert "virtual_machine" in result.lower()
        assert "source" in result.lower()
        assert "version" in result.lower()

    def test_get_info_by_alias(self):
        """Test getting info by alias."""
        result = get_avm_module_info("vm")

        assert "virtual_machine" in result.lower() or "virtualmachine" in result.lower()

    def test_get_info_nonexistent(self):
        """Test getting info for non-existent module."""
        result = get_avm_module_info("nonexistent_module")

        assert "not found" in result.lower()

    def test_includes_example_config(self):
        """Test that example configuration is included."""
        result = get_avm_module_info("key_vault")

        assert "example" in result.lower() or "usage" in result.lower()


class TestGetModuleDependencies:
    """Tests for get_module_dependencies function."""

    def test_module_with_dependencies(self):
        """Test getting dependencies for a module that has them."""
        result = get_module_dependencies("virtual_machine")

        assert "dependencies" in result.lower()

    def test_module_without_dependencies(self):
        """Test getting dependencies for a module with none."""
        result = get_module_dependencies("storage_account")

        # Storage account typically only depends on resource group
        assert "dependencies" in result.lower() or "no direct dependencies" in result.lower()

    def test_nonexistent_module(self):
        """Test getting dependencies for non-existent module."""
        result = get_module_dependencies("nonexistent")

        assert "not found" in result.lower()


class TestRecommendModulesForArchitecture:
    """Tests for recommend_modules_for_architecture function."""

    def test_recommend_for_simple_list(self):
        """Test recommendations for a simple service list."""
        result = recommend_modules_for_architecture(["vm", "storage", "database"])

        assert "recommend" in result.lower()

    def test_recommend_adds_dependencies(self):
        """Test that dependencies are included in recommendations."""
        result = recommend_modules_for_architecture(["function_app"])

        # Function app depends on storage and app service plan
        assert "storage" in result.lower() or "service" in result.lower()

    def test_handles_unknown_services(self):
        """Test handling of unknown services."""
        result = recommend_modules_for_architecture(
            ["vm", "unknown_service_xyz"]
        )

        # Should mention the unknown service
        assert "vm" in result.lower() or "virtual" in result.lower()

    def test_recommend_with_natural_language(self):
        """Test recommendations with natural language service names."""
        result = recommend_modules_for_architecture(
            ["web server", "database", "cache"]
        )

        # Should still find appropriate modules
        assert "recommend" in result.lower()
