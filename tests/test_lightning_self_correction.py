"""Tests for self-correction capabilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tf_avm_agent.lightning.self_correction import (
    CorrectionResult,
    TerraformSelfCorrector,
    ValidationError,
)
from tf_avm_agent.tools.terraform_generator import GeneratedFile, TerraformProjectOutput


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_creation(self):
        error = ValidationError(
            error_type="add_missing_argument",
            message='Missing required argument: "name"',
            file="main.tf",
        )
        assert error.error_type == "add_missing_argument"
        assert error.line is None
        assert error.suggestion is None

    def test_creation_with_optional_fields(self):
        error = ValidationError(
            error_type="fix_syntax_error",
            message="Syntax error",
            file="main.tf",
            line=42,
            suggestion="Check bracket balance",
        )
        assert error.line == 42
        assert error.suggestion == "Check bracket balance"


class TestCorrectionResult:
    """Tests for CorrectionResult dataclass."""

    def test_creation(self, sample_terraform_output):
        result = CorrectionResult(
            success=True,
            original_output=sample_terraform_output,
            corrected_output=None,
        )
        assert result.success is True
        assert result.errors_found == []
        assert result.errors_fixed == []
        assert result.iterations == 0


class TestTerraformSelfCorrector:
    """Tests for TerraformSelfCorrector."""

    @pytest.fixture
    def mock_agent(self):
        agent = MagicMock()
        agent.run_async = AsyncMock(
            return_value='Here is the fix:\n```hcl\nresource "test" "main" {}\n```'
        )
        return agent

    @pytest.fixture
    def corrector(self, mock_agent):
        with patch(
            "tf_avm_agent.lightning.self_correction.get_global_tracer"
        ) as mock_tracer:
            mock_tracer.return_value = MagicMock()
            return TerraformSelfCorrector(agent=mock_agent)

    def test_parse_missing_argument_error(self, corrector):
        """Should parse 'Missing required argument' errors."""
        err = corrector._parse_error_message(
            'Missing required argument: "name"', "main.tf"
        )
        assert err is not None
        assert err.error_type == "add_missing_argument"
        assert err.file == "main.tf"

    def test_parse_undefined_resource_error(self, corrector):
        """Should parse undefined resource errors."""
        err = corrector._parse_error_message(
            'Reference to undefined resource "my_vm"', "main.tf"
        )
        assert err is not None
        assert err.error_type == "fix_resource_reference"

    def test_parse_module_not_found_error(self, corrector):
        """Should parse module not found errors."""
        err = corrector._parse_error_message(
            'Module "test_module" not found', "main.tf"
        )
        assert err is not None
        assert err.error_type == "fix_module_source"

    def test_parse_syntax_error(self, corrector):
        """Should parse syntax errors."""
        err = corrector._parse_error_message(
            "Expected '=' after argument name", "main.tf"
        )
        assert err is not None
        assert err.error_type == "fix_syntax_error"

    def test_parse_unknown_error(self, corrector):
        """Unknown errors should have type 'unknown'."""
        err = corrector._parse_error_message(
            "Some completely unknown error message", "variables.tf"
        )
        assert err is not None
        assert err.error_type == "unknown"
        assert err.file == "variables.tf"

    def test_parse_empty_message(self, corrector):
        """Empty messages should return None."""
        err = corrector._parse_error_message("", "main.tf")
        assert err is None

    def test_extract_hcl_code_block(self, corrector):
        """Should extract code from ```hcl blocks."""
        response = 'Fix:\n```hcl\nresource "test" "main" {\n  name = "test"\n}\n```'
        code = corrector._extract_terraform_code(response)
        assert code == 'resource "test" "main" {\n  name = "test"\n}'

    def test_extract_terraform_code_block(self, corrector):
        """Should extract code from ```terraform blocks."""
        response = '```terraform\nmodule "vm" {}\n```'
        code = corrector._extract_terraform_code(response)
        assert code == 'module "vm" {}'

    def test_extract_plain_code_block(self, corrector):
        """Should extract code from plain ``` blocks."""
        response = '```\nresource "test" {}\n```'
        code = corrector._extract_terraform_code(response)
        assert code == 'resource "test" {}'

    def test_extract_no_code_block(self, corrector):
        """Should return None when no code block found."""
        response = "No code blocks here, just text."
        code = corrector._extract_terraform_code(response)
        assert code is None

    def test_validate_output_no_tf_files(self, corrector):
        """Output with no .tf files should have no errors."""
        output = TerraformProjectOutput(
            files=[GeneratedFile(filename="README.md", content="# Test")],
            summary="",
        )
        errors = corrector._validate_output(output)
        assert errors == []
