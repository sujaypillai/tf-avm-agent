"""Tests for the AVM module registry."""

import pytest

from tf_avm_agent.registry.avm_modules import (
    AVM_MODULES,
    get_all_categories,
    get_module_by_service,
    get_modules_by_category,
    search_modules,
)


class TestAVMModuleRegistry:
    """Tests for the AVM module registry."""

    def test_registry_not_empty(self):
        """Test that the registry contains modules."""
        assert len(AVM_MODULES) > 0

    def test_all_modules_have_required_fields(self):
        """Test that all modules have required fields."""
        for name, module in AVM_MODULES.items():
            assert module.name, f"Module {name} missing name"
            assert module.source, f"Module {name} missing source"
            assert module.version, f"Module {name} missing version"
            assert module.description, f"Module {name} missing description"
            assert module.category, f"Module {name} missing category"

    def test_module_sources_follow_convention(self):
        """Test that module sources follow the AVM naming convention."""
        for name, module in AVM_MODULES.items():
            assert module.source.startswith("Azure/avm-"), (
                f"Module {name} source doesn't follow AVM convention: {module.source}"
            )


class TestGetModuleByService:
    """Tests for get_module_by_service function."""

    def test_direct_match(self):
        """Test getting module by direct name."""
        module = get_module_by_service("virtual_machine")
        assert module is not None
        assert module.name == "virtual_machine"

    def test_alias_match(self):
        """Test getting module by alias."""
        module = get_module_by_service("vm")
        assert module is not None
        assert module.name == "virtual_machine"

        module = get_module_by_service("aks")
        assert module is not None
        assert module.name == "kubernetes_cluster"

    def test_case_insensitive(self):
        """Test that lookup is case insensitive."""
        module1 = get_module_by_service("virtual_machine")
        module2 = get_module_by_service("Virtual_Machine")
        module3 = get_module_by_service("VIRTUAL_MACHINE")

        assert module1 is not None
        assert module2 is not None
        assert module3 is not None
        assert module1.name == module2.name == module3.name

    def test_not_found_returns_none(self):
        """Test that non-existent module returns None."""
        module = get_module_by_service("nonexistent_service")
        assert module is None


class TestSearchModules:
    """Tests for search_modules function."""

    def test_search_by_name(self):
        """Test searching by module name."""
        results = search_modules("virtual")
        assert len(results) > 0
        assert any("virtual" in m.name.lower() for m in results)

    def test_search_by_description(self):
        """Test searching by description."""
        results = search_modules("container")
        assert len(results) > 0

    def test_search_by_alias(self):
        """Test searching by alias."""
        results = search_modules("k8s")
        assert len(results) > 0

    def test_search_no_results(self):
        """Test search with no results."""
        results = search_modules("zzzznonexistent")
        assert len(results) == 0


class TestGetModulesByCategory:
    """Tests for get_modules_by_category function."""

    def test_get_compute_modules(self):
        """Test getting compute modules."""
        modules = get_modules_by_category("compute")
        assert len(modules) > 0
        assert all(m.category == "compute" for m in modules)

    def test_get_networking_modules(self):
        """Test getting networking modules."""
        modules = get_modules_by_category("networking")
        assert len(modules) > 0
        assert all(m.category == "networking" for m in modules)

    def test_nonexistent_category(self):
        """Test getting modules from non-existent category."""
        modules = get_modules_by_category("nonexistent")
        assert len(modules) == 0


class TestGetAllCategories:
    """Tests for get_all_categories function."""

    def test_returns_categories(self):
        """Test that categories are returned."""
        categories = get_all_categories()
        assert len(categories) > 0

    def test_expected_categories_present(self):
        """Test that expected categories are present."""
        categories = get_all_categories()
        expected = ["compute", "networking", "storage", "database", "security"]
        for cat in expected:
            assert cat in categories, f"Expected category '{cat}' not found"
