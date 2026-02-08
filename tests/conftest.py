"""Shared test fixtures."""

import pytest

from tf_avm_agent.tools.terraform_generator import GeneratedFile, TerraformProjectOutput


@pytest.fixture
def sample_terraform_output():
    """A minimal valid TerraformProjectOutput for testing."""
    return TerraformProjectOutput(
        files=[
            GeneratedFile(
                filename="main.tf",
                content=(
                    'resource "azurerm_resource_group" "main" {\n'
                    '  name     = "test-rg"\n'
                    '  location = "eastus"\n'
                    "}\n\n"
                    'module "test-vm" {\n'
                    '  source  = "Azure/avm-res-compute-virtualmachine/azurerm"\n'
                    '  version = "~> 0.0"\n\n'
                    "  depends_on = [azurerm_resource_group.main]\n"
                    "}\n"
                ),
            ),
            GeneratedFile(
                filename="providers.tf",
                content='terraform {\n  required_version = ">= 1.9.0"\n}\n',
            ),
        ],
        summary="Test output",
    )


@pytest.fixture
def empty_terraform_output():
    """A TerraformProjectOutput with no main.tf."""
    return TerraformProjectOutput(
        files=[GeneratedFile(filename="README.md", content="# Test")],
        summary="Empty output",
    )
