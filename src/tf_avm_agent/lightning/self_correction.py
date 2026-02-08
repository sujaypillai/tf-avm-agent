"""Self-correction capabilities for TF-AVM-Agent."""

import re
from dataclasses import dataclass, field
from typing import Any

from tf_avm_agent.lightning.config import MAX_SELF_CORRECTION_ITERATIONS
from tf_avm_agent.lightning.telemetry import get_global_tracer
from tf_avm_agent.tools.terraform_generator import (
    GeneratedFile,
    TerraformProjectOutput,
    validate_terraform_syntax,
)


@dataclass
class ValidationError:
    """A validation error in generated Terraform code."""

    error_type: str
    message: str
    file: str
    line: int | None = None
    suggestion: str | None = None


@dataclass
class CorrectionResult:
    """Result of a self-correction attempt."""

    success: bool
    original_output: TerraformProjectOutput
    corrected_output: TerraformProjectOutput | None
    errors_found: list[ValidationError] = field(default_factory=list)
    errors_fixed: list[str] = field(default_factory=list)
    iterations: int = 0


class TerraformSelfCorrector:
    """Self-correction agent for Terraform code."""

    # Common error patterns and fixes
    ERROR_PATTERNS: dict[str, str] = {
        r'Missing required argument: "(\w+)"': "add_missing_argument",
        r'Reference to undefined resource "(\w+)"': "fix_resource_reference",
        r'Invalid value for variable "(\w+)"': "fix_variable_value",
        r'Module "(\w+)" not found': "fix_module_source",
        r"Expected '=' after argument name": "fix_syntax_error",
    }

    def __init__(self, agent: Any):
        """Initialize with reference to the agent.

        Args:
            agent: A TerraformAVMAgent instance used for LLM-based correction.
        """
        self.agent = agent
        self.tracer = get_global_tracer()

    async def validate_and_correct(
        self,
        output: TerraformProjectOutput,
    ) -> CorrectionResult:
        """Validate output and attempt self-correction if needed."""
        errors_found: list[ValidationError] = []
        errors_fixed: list[str] = []
        current_output = output

        for iteration in range(MAX_SELF_CORRECTION_ITERATIONS):
            validation_errors = self._validate_output(current_output)

            if not validation_errors:
                self.tracer.emit_reward(
                    reward=1.0,
                    metadata={
                        "self_correction": True,
                        "iterations": iteration,
                        "errors_fixed": len(errors_fixed),
                    },
                )
                return CorrectionResult(
                    success=True,
                    original_output=output,
                    corrected_output=current_output
                    if iteration > 0
                    else None,
                    errors_found=errors_found,
                    errors_fixed=errors_fixed,
                    iterations=iteration,
                )

            errors_found.extend(validation_errors)

            self.tracer.emit_action(
                action_type="self_correction_attempt",
                input_data={
                    "iteration": iteration,
                    "errors": [e.message for e in validation_errors],
                },
            )

            corrected_output, fixed = await self._correct_errors(
                current_output, validation_errors
            )

            if corrected_output:
                current_output = corrected_output
                errors_fixed.extend(fixed)
            else:
                break

        # Check final state
        final_errors = self._validate_output(current_output)
        success = len(final_errors) == 0

        self.tracer.emit_reward(
            reward=0.5 if len(errors_fixed) > 0 else -0.5,
            metadata={
                "self_correction": True,
                "iterations": MAX_SELF_CORRECTION_ITERATIONS,
                "errors_fixed": len(errors_fixed),
                "errors_remaining": len(final_errors),
            },
        )

        return CorrectionResult(
            success=success,
            original_output=output,
            corrected_output=current_output if errors_fixed else None,
            errors_found=errors_found,
            errors_fixed=errors_fixed,
            iterations=MAX_SELF_CORRECTION_ITERATIONS,
        )

    def _validate_output(
        self, output: TerraformProjectOutput
    ) -> list[ValidationError]:
        """Validate Terraform output and return errors."""
        errors = []
        for file in output.files:
            if not file.filename.endswith(".tf"):
                continue

            is_valid, message = validate_terraform_syntax(file.content)
            if not is_valid:
                error = self._parse_error_message(message, file.filename)
                if error:
                    errors.append(error)
        return errors

    def _parse_error_message(
        self, message: str, filename: str
    ) -> ValidationError | None:
        """Parse error message into structured ValidationError."""
        for pattern, fix_type in self.ERROR_PATTERNS.items():
            match = re.search(pattern, message)
            if match:
                return ValidationError(
                    error_type=fix_type,
                    message=message,
                    file=filename,
                    suggestion=f"Apply fix: {fix_type}",
                )

        if message.strip():
            return ValidationError(
                error_type="unknown",
                message=message,
                file=filename,
            )

        return None

    async def _correct_errors(
        self,
        output: TerraformProjectOutput,
        errors: list[ValidationError],
    ) -> tuple[TerraformProjectOutput | None, list[str]]:
        """Attempt to correct errors using the agent."""
        error_descriptions = "\n".join(
            f"- {e.file}: {e.message}" for e in errors
        )

        correction_prompt = (
            "The generated Terraform code has the following errors:\n\n"
            f"{error_descriptions}\n\n"
            "Please fix these errors and regenerate the corrected code. Focus on:\n"
            "1. Adding any missing required arguments\n"
            "2. Fixing resource references\n"
            "3. Correcting syntax errors\n\n"
            "Provide the corrected main.tf content."
        )

        try:
            response = await self.agent.run_async(correction_prompt)

            corrected_code = self._extract_terraform_code(response)
            if not corrected_code:
                return None, []

            new_files = []
            for file in output.files:
                if file.filename == "main.tf":
                    new_files.append(
                        GeneratedFile(
                            filename=file.filename,
                            content=corrected_code,
                        )
                    )
                else:
                    new_files.append(file)

            new_output = TerraformProjectOutput(
                files=new_files,
                summary=output.summary + "\n[Self-corrected]",
            )

            fixed = [e.error_type for e in errors]
            return new_output, fixed

        except Exception as e:
            self.tracer.emit_action(
                action_type="self_correction_failed",
                output_data={"error": str(e)},
            )
            return None, []

    def _extract_terraform_code(self, response: str) -> str | None:
        """Extract Terraform code block from agent response."""
        patterns = [
            r"```hcl\n(.*?)```",
            r"```terraform\n(.*?)```",
            r"```\n(.*?)```",
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()

        return None
