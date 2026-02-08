"""Tests for reward calculation."""

import pytest

from tf_avm_agent.lightning.rewards import RewardResult, TerraformRewardCalculator
from tf_avm_agent.tools.terraform_generator import GeneratedFile, TerraformProjectOutput


class TestRewardCalculator:
    """Tests for TerraformRewardCalculator."""

    @pytest.fixture
    def calculator(self):
        return TerraformRewardCalculator()

    def test_reward_with_valid_output(self, calculator, sample_terraform_output):
        """Valid output should produce a positive or neutral reward."""
        result = calculator.calculate_reward(sample_terraform_output)
        assert isinstance(result, RewardResult)
        assert -1.0 <= result.total_reward <= 1.0
        assert "syntax_valid" in result.components
        assert "modules_used" in result.components
        assert "dependencies_resolved" in result.components

    def test_reward_with_empty_output(self, calculator, empty_terraform_output):
        """Output without main.tf should get negative syntax reward."""
        result = calculator.calculate_reward(empty_terraform_output)
        assert result.components["syntax_valid"] == -1.0
        assert result.components["modules_used"] == 0.0

    def test_reward_with_user_feedback(self, calculator, sample_terraform_output):
        """User feedback should be included in components."""
        result = calculator.calculate_reward(
            sample_terraform_output, user_feedback=0.8
        )
        assert result.components["user_feedback"] == 0.8

    def test_reward_without_user_feedback(self, calculator, sample_terraform_output):
        """Without feedback, user_feedback component should be 0.0."""
        result = calculator.calculate_reward(sample_terraform_output)
        assert result.components["user_feedback"] == 0.0

    def test_custom_weights(self, sample_terraform_output):
        """Custom weights should be applied."""
        calc = TerraformRewardCalculator(
            weights={"syntax_valid": 1.0, "modules_used": 0.0}
        )
        result = calc.calculate_reward(sample_terraform_output)
        assert isinstance(result, RewardResult)

    def test_module_count_reward(self, calculator):
        """Module count should affect reward proportionally."""
        output_many = TerraformProjectOutput(
            files=[
                GeneratedFile(
                    filename="main.tf",
                    content=(
                        'module "a" {}\n'
                        'module "b" {}\n'
                        'module "c" {}\n'
                        'module "d" {}\n'
                        'module "e" {}\n'
                    ),
                ),
            ],
            summary="",
        )
        result = calculator.calculate_reward(output_many)
        assert result.components["modules_used"] == 1.0  # 5/5.0 = 1.0

    def test_dependency_reward(self, calculator):
        """Dependencies should affect reward."""
        output_deps = TerraformProjectOutput(
            files=[
                GeneratedFile(
                    filename="main.tf",
                    content=(
                        'resource "azurerm_resource_group" "main" {}\n'
                        'module "x" {\n'
                        "  depends_on = [azurerm_resource_group.main]\n"
                        "}\n"
                    ),
                ),
            ],
            summary="",
        )
        result = calculator.calculate_reward(output_deps)
        assert result.components["dependencies_resolved"] == 1.0

    def test_no_dependency_reward(self, calculator):
        """No dependencies should give 0 dependency reward."""
        output_no_deps = TerraformProjectOutput(
            files=[
                GeneratedFile(
                    filename="main.tf",
                    content='module "x" {\n  source = "test"\n}\n',
                ),
            ],
            summary="",
        )
        result = calculator.calculate_reward(output_no_deps)
        assert result.components["dependencies_resolved"] == 0.0

    def test_plan_reward_skipped(self, calculator, sample_terraform_output):
        """Plan reward should be 0 (requires sandbox)."""
        result = calculator.calculate_reward(sample_terraform_output)
        assert result.components["plan_success"] == 0.0
