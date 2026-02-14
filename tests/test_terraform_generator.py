"""Tests for the Terraform code generator."""

import pytest

from tf_avm_agent.tools.terraform_generator import (
    TerraformModuleConfig,
    TerraformProjectConfig,
    generate_main_tf,
    generate_outputs_tf,
    generate_providers_tf,
    generate_terraform_module,
    generate_terraform_project,
    generate_variables_tf,
)


class TestGenerateTerraformModule:
    """Tests for generate_terraform_module function."""

    def test_generate_vm_module(self):
        """Test generating a virtual machine module."""
        code = generate_terraform_module(
            service_name="virtual_machine",
            module_instance_name="my-vm",
        )

        assert 'module "my-vm"' in code
        assert "Azure/avm-res-compute-virtualmachine/azurerm" in code
        assert "version" in code

    def test_generate_storage_module(self):
        """Test generating a storage account module."""
        code = generate_terraform_module(
            service_name="storage_account",
            module_instance_name="my-storage",
        )

        assert 'module "my-storage"' in code
        assert "Azure/avm-res-storage-storageaccount/azurerm" in code

    def test_generate_with_variables(self):
        """Test generating with custom variables."""
        code = generate_terraform_module(
            service_name="storage_account",
            module_instance_name="custom-storage",
            variables={
                "account_tier": "Premium",
                "account_replication_type": "ZRS",
            },
        )

        assert "Premium" in code
        assert "ZRS" in code

    def test_generate_nonexistent_module(self):
        """Test generating code for non-existent module."""
        code = generate_terraform_module(
            service_name="nonexistent_service",
            module_instance_name="test",
        )

        assert "Error" in code


class TestGenerateProvidersTf:
    """Tests for generate_providers_tf function."""

    def test_generates_valid_terraform_block(self):
        """Test that valid terraform block is generated."""
        code = generate_providers_tf()

        assert "terraform {" in code
        assert "required_version" in code
        assert "required_providers" in code
        assert "azurerm" in code

    def test_includes_azurerm_provider(self):
        """Test that azurerm provider is included."""
        code = generate_providers_tf()

        assert 'provider "azurerm"' in code
        assert "features" in code

    def test_with_subscription_id(self):
        """Test with subscription ID."""
        code = generate_providers_tf(subscription_id="test-sub-id")

        assert "test-sub-id" in code


class TestGenerateVariablesTf:
    """Tests for generate_variables_tf function."""

    def test_generates_location_variable(self):
        """Test that location variable is generated."""
        config = TerraformProjectConfig(
            project_name="test",
            location="westeurope",
            resource_group_name="rg-test",
        )
        code = generate_variables_tf(config)

        assert 'variable "location"' in code
        assert "westeurope" in code

    def test_generates_resource_group_variable(self):
        """Test that resource group variable is generated."""
        config = TerraformProjectConfig(
            project_name="test",
            location="eastus",
            resource_group_name="rg-custom",
        )
        code = generate_variables_tf(config)

        assert 'variable "resource_group_name"' in code
        assert "rg-custom" in code


class TestGenerateMainTf:
    """Tests for generate_main_tf function."""

    def test_includes_resource_group(self):
        """Test that resource group is included."""
        code = generate_main_tf(
            modules=[],
            resource_group_name="rg-test",
            location="eastus",
        )

        assert 'resource "azurerm_resource_group"' in code

    def test_includes_modules(self):
        """Test that modules are included."""
        modules = [
            TerraformModuleConfig(
                module_name="test-vm",
                avm_module="virtual_machine",
                variables={},
            )
        ]
        code = generate_main_tf(
            modules=modules,
            resource_group_name="rg-test",
        )

        assert 'module "test-vm"' in code

    def test_includes_data_sources(self):
        """Test that data sources are included."""
        code = generate_main_tf(
            modules=[],
            resource_group_name="rg-test",
        )

        assert "data \"azurerm_client_config\"" in code


class TestGenerateOutputsTf:
    """Tests for generate_outputs_tf function."""

    def test_includes_resource_group_outputs(self):
        """Test that resource group outputs are included."""
        code = generate_outputs_tf(modules=[])

        assert "resource_group_name" in code
        assert "resource_group_id" in code

    def test_includes_module_outputs(self):
        """Test that module outputs are included."""
        modules = [
            TerraformModuleConfig(
                module_name="my-storage",
                avm_module="storage_account",
                variables={},
            )
        ]
        code = generate_outputs_tf(modules)

        assert "my-storage_resource_id" in code


class TestGenerateTerraformProject:
    """Tests for generate_terraform_project function."""

    def test_generates_all_files(self):
        """Test that all required files are generated."""
        result = generate_terraform_project(
            project_name="test-project",
            services=["storage_account"],
            location="eastus",
        )

        filenames = [f.filename for f in result.files]
        assert "providers.tf" in filenames
        assert "variables.tf" in filenames
        assert "main.tf" in filenames
        assert "outputs.tf" in filenames
        assert "README.md" in filenames

    def test_generates_summary(self):
        """Test that summary is generated."""
        result = generate_terraform_project(
            project_name="test-project",
            services=["storage_account"],
            location="eastus",
        )

        assert result.summary
        assert "test-project" in result.summary

    def test_includes_dependencies(self):
        """Test that module dependencies are included."""
        result = generate_terraform_project(
            project_name="test",
            services=["function_app"],  # Has dependencies on app_service_plan, storage
            location="eastus",
        )

        main_tf = next(f for f in result.files if f.filename == "main.tf")
        # Function app depends on app service plan
        assert "app-service-plan" in main_tf.content or "serverfarm" in main_tf.content.lower()

    def test_multiple_services(self):
        """Test with multiple services."""
        result = generate_terraform_project(
            project_name="multi-service",
            services=["virtual_machine", "storage_account", "key_vault"],
            location="eastus",
        )

        main_tf = next(f for f in result.files if f.filename == "main.tf")
        assert "virtual-machine" in main_tf.content
        assert "storage" in main_tf.content.lower()
        assert "key-vault" in main_tf.content or "keyvault" in main_tf.content.lower()


class TestTerraformCodeValidation:
    """Tests for Terraform code generation validation (bug fixes)."""

    def test_tags_variable_does_not_reference_other_variables(self):
        """Test that tags variable default does not reference var.environment (Issue #1)."""
        result = generate_terraform_project(
            project_name="test-project",
            services=["storage_account"],
            location="eastus",
        )

        variables_tf = next(f for f in result.files if f.filename == "variables.tf")
        # The tags variable should not contain "var.environment" in its default block
        # We need to check that the default block doesn't have any var. references
        tags_section = variables_tf.content.split('variable "tags"')[1].split("}")[0]
        assert "var." not in tags_section, "Tags variable default should not reference other variables"

    def test_tags_merged_with_environment_in_locals(self):
        """Test that environment is merged into tags via locals block."""
        result = generate_terraform_project(
            project_name="test-project",
            services=["storage_account"],
            location="eastus",
        )

        main_tf = next(f for f in result.files if f.filename == "main.tf")
        # Check that locals block merges tags with environment
        assert "locals {" in main_tf.content
        # Check for the merge function with environment
        assert "merge(var.tags" in main_tf.content
        assert "environment = var.environment" in main_tf.content

    def test_module_versions_not_zero_zero(self):
        """Test that module versions are not ~> 0.0 (Issue #2)."""
        result = generate_terraform_project(
            project_name="test-project",
            services=["virtual_machine", "storage_account", "key_vault"],
            location="eastus",
        )

        main_tf = next(f for f in result.files if f.filename == "main.tf")
        # Should not contain "~> 0.0"
        assert '~> 0.0"' not in main_tf.content, "Module versions should not be ~> 0.0"
        # Should contain proper version constraints like ~> 0.20, ~> 0.5, etc.
        assert 'version = "~>' in main_tf.content

    def test_vm_module_has_os_type_default(self):
        """Test that VM module has virtualmachine_os_type set (Issue #3)."""
        result = generate_terraform_project(
            project_name="test-project",
            services=["virtual_machine"],
            location="eastus",
        )

        main_tf = next(f for f in result.files if f.filename == "main.tf")
        # VM module should have virtualmachine_os_type set to a value, not commented
        assert "virtualmachine_os_type" in main_tf.content
        assert '# virtualmachine_os_type' not in main_tf.content, "virtualmachine_os_type should not be commented"

    def test_depends_on_uses_correct_module_names(self):
        """Test that depends_on uses hyphens not underscores (Issue #4)."""
        result = generate_terraform_project(
            project_name="test-project",
            services=["virtual_machine"],  # Depends on virtual_network
            location="eastus",
        )

        main_tf = next(f for f in result.files if f.filename == "main.tf")
        # Check for the VM module's depends_on
        if "depends_on" in main_tf.content:
            # Should use module.virtual-network not module.virtual_network
            assert "module.virtual-network" in main_tf.content or "depends_on" not in main_tf.content
            assert "module.virtual_network]" not in main_tf.content, "depends_on should use hyphens not underscores"

    def test_storage_account_name_includes_suffix(self):
        """Test that storage account name includes random suffix (Issue #5)."""
        result = generate_terraform_project(
            project_name="test-project",
            services=["storage_account"],
            location="eastus",
        )

        main_tf = next(f for f in result.files if f.filename == "main.tf")
        # Storage account name should reference local.name_suffix
        assert "local.name_suffix" in main_tf.content
        # Check that storage module name includes the suffix
        assert "sa${local.name_suffix}" in main_tf.content, "Storage account name should include random suffix"

    def test_key_vault_name_includes_suffix(self):
        """Test that key vault name includes random suffix (Issue #5)."""
        result = generate_terraform_project(
            project_name="test-project",
            services=["key_vault"],
            location="eastus",
        )

        main_tf = next(f for f in result.files if f.filename == "main.tf")
        # Key vault name should reference local.name_suffix
        assert "local.name_suffix" in main_tf.content
        # Check that key vault module name includes the suffix
        assert "kv-${local.name_suffix}" in main_tf.content, "Key vault name should include random suffix"
