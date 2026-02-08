"""Reward calculation for Agent Lightning training."""

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any

from tf_avm_agent.lightning.config import MODULE_COUNT_REWARD_THRESHOLD
from tf_avm_agent.tools.terraform_generator import (
    TerraformProjectOutput,
    validate_terraform_syntax,
)
from tf_avm_agent.tools.terraform_utils import is_terraform_available


@dataclass
class RewardResult:
    """Result of reward calculation."""

    total_reward: float
    components: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class TerraformRewardCalculator:
    """Calculate rewards for Terraform code generation."""

    WEIGHTS: dict[str, float] = {
        "syntax_valid": 0.3,
        "format_valid": 0.1,
        "modules_used": 0.2,
        "dependencies_resolved": 0.1,
        "plan_success": 0.2,
        "user_feedback": 0.1,
    }

    def __init__(self, weights: dict[str, float] | None = None):
        if weights:
            self.WEIGHTS = {**self.WEIGHTS, **weights}

    def calculate_reward(
        self,
        output: TerraformProjectOutput,
        user_feedback: float | None = None,
    ) -> RewardResult:
        """Calculate total reward for generated output."""
        components: dict[str, float] = {}
        metadata: dict[str, Any] = {}

        syntax_r, syntax_m = self._syntax_reward(output)
        components["syntax_valid"] = syntax_r
        metadata.update(syntax_m)

        format_r, format_m = self._format_reward(output)
        components["format_valid"] = format_r
        metadata.update(format_m)

        module_r, module_m = self._module_reward(output)
        components["modules_used"] = module_r
        metadata.update(module_m)

        dep_r, dep_m = self._dependency_reward(output)
        components["dependencies_resolved"] = dep_r
        metadata.update(dep_m)

        plan_r, plan_m = self._plan_reward(output)
        components["plan_success"] = plan_r
        metadata.update(plan_m)

        components["user_feedback"] = (
            user_feedback if user_feedback is not None else 0.0
        )

        total = sum(components[k] * self.WEIGHTS[k] for k in self.WEIGHTS)

        return RewardResult(
            total_reward=total, components=components, metadata=metadata
        )

    def _syntax_reward(
        self, output: TerraformProjectOutput
    ) -> tuple[float, dict]:
        """Calculate syntax validation reward."""
        main_tf = next(
            (f for f in output.files if f.filename == "main.tf"), None
        )
        if not main_tf:
            return -1.0, {"syntax_error": "no_main_tf"}

        is_valid, message = validate_terraform_syntax(main_tf.content)
        return (
            (1.0 if is_valid else -0.5),
            {"syntax_valid": is_valid, "syntax_message": message},
        )

    def _format_reward(
        self, output: TerraformProjectOutput
    ) -> tuple[float, dict]:
        """Calculate format compliance reward."""
        if not is_terraform_available():
            return 0.0, {"format_skipped": "terraform_not_available"}

        for f in output.files:
            if not f.filename.endswith(".tf"):
                continue
            is_formatted, msg = self._check_terraform_format(f.content)
            if not is_formatted:
                return 0.0, {"format_issues": f.filename}
        return 1.0, {"format_valid": True}

    def _check_terraform_format(self, content: str) -> tuple[bool, str]:
        """Check if content is properly formatted."""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".tf", delete=False
            ) as f:
                f.write(content)
                temp_path = f.name

            result = subprocess.run(
                ["terraform", "fmt", "-check", temp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return result.returncode == 0, result.stderr
        except Exception as e:
            return True, str(e)  # Assume valid if can't check
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def _module_reward(
        self, output: TerraformProjectOutput
    ) -> tuple[float, dict]:
        """Calculate reward based on AVM module usage."""
        main_tf = next(
            (f for f in output.files if f.filename == "main.tf"), None
        )
        if not main_tf:
            return 0.0, {"modules_count": 0}

        count = main_tf.content.count('module "')
        reward = min(1.0, count / MODULE_COUNT_REWARD_THRESHOLD)

        return reward, {"modules_count": count}

    def _dependency_reward(
        self, output: TerraformProjectOutput
    ) -> tuple[float, dict]:
        """Calculate reward for proper dependency handling."""
        main_tf = next(
            (f for f in output.files if f.filename == "main.tf"), None
        )
        if not main_tf:
            return 0.0, {}

        has_depends = "depends_on" in main_tf.content
        has_rg_ref = "azurerm_resource_group.main" in main_tf.content

        reward = (0.5 if has_rg_ref else 0.0) + (0.5 if has_depends else 0.0)

        return reward, {
            "has_depends_on": has_depends,
            "has_rg_reference": has_rg_ref,
        }

    def _plan_reward(
        self, output: TerraformProjectOutput
    ) -> tuple[float, dict]:
        """Calculate reward based on terraform plan success."""
        if not is_terraform_available():
            return 0.0, {"plan_skipped": "terraform_not_available"}
        # For safety, we don't actually run plan in automated training
        return 0.0, {"plan_skipped": "sandbox_required"}
