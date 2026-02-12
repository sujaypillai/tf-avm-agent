"""Dataset generation for Agent Lightning training."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from tf_avm_agent.registry.avm_modules import AVM_MODULES


@dataclass
class TrainingExample:
    """A single training example."""

    task_id: str
    input_prompt: str
    expected_services: list[str]
    expected_modules: list[str]
    ground_truth_code: str | None = None
    metadata: dict[str, Any] | None = None


class TerraformTrainingDataset:
    """Dataset for training the TF-AVM-Agent."""

    # Common architecture patterns for training
    ARCHITECTURE_PATTERNS = [
        {
            "name": "web_app",
            "description": "Simple web application with database",
            "services": ["app_service", "sql_database", "key_vault"],
            "prompt_templates": [
                "Create a web application with a SQL database",
                "I need Terraform for a website with database backend",
                "Generate infrastructure for a web app with secure secrets",
            ],
        },
        {
            "name": "microservices",
            "description": "Microservices architecture with AKS",
            "services": [
                "kubernetes_cluster",
                "container_registry",
                "postgresql_flexible",
                "redis",
            ],
            "prompt_templates": [
                "Create a microservices platform on Kubernetes",
                "I need AKS with container registry and databases",
                "Generate Terraform for a containerized application architecture",
            ],
        },
        {
            "name": "data_platform",
            "description": "Data analytics platform",
            "services": [
                "storage_account",
                "azure_openai",
                "ai_search",
                "log_analytics_workspace",
            ],
            "prompt_templates": [
                "Create a data analytics platform with AI capabilities",
                "I need storage, AI, and search for a data application",
                "Generate infrastructure for an AI-powered data platform",
            ],
        },
        {
            "name": "secure_network",
            "description": "Secure network architecture",
            "services": [
                "virtual_network",
                "network_security_group",
                "application_gateway",
                "firewall",
            ],
            "prompt_templates": [
                "Create a secure network with WAF and firewall",
                "I need a VNet with network security",
                "Generate Terraform for secure Azure networking",
            ],
        },
    ]

    def generate_examples(self) -> Iterator[TrainingExample]:
        """Generate training examples from architecture patterns."""
        for pattern in self.ARCHITECTURE_PATTERNS:
            for i, prompt in enumerate(pattern["prompt_templates"]):
                yield TrainingExample(
                    task_id=f"{pattern['name']}_{i}",
                    input_prompt=prompt,
                    expected_services=pattern["services"],
                    expected_modules=pattern["services"],
                    metadata={"pattern": pattern["name"]},
                )

    def generate_module_lookup_examples(self) -> Iterator[TrainingExample]:
        """Generate examples for module lookup training."""
        for module in AVM_MODULES.values():
            yield TrainingExample(
                task_id=f"lookup_{module.name}",
                input_prompt=f"What AVM module should I use for {module.azure_service}?",
                expected_services=[],
                expected_modules=[module.name],
                metadata={
                    "module": module.name,
                    "category": module.category,
                },
            )

            for alias in module.aliases[:2]:
                yield TrainingExample(
                    task_id=f"lookup_{module.name}_{alias}",
                    input_prompt=f"Find the AVM module for {alias}",
                    expected_services=[],
                    expected_modules=[module.name],
                    metadata={"module": module.name, "alias": alias},
                )

    def save_to_jsonl(self, path: str) -> int:
        """Save dataset to JSONL file.

        Returns:
            Number of examples written.
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with open(path, "w") as f:
            for example in self.generate_examples():
                f.write(
                    json.dumps(
                        {
                            "task_id": example.task_id,
                            "input": example.input_prompt,
                            "expected_services": example.expected_services,
                            "expected_modules": example.expected_modules,
                            "metadata": example.metadata,
                        }
                    )
                    + "\n"
                )
                count += 1

            for example in self.generate_module_lookup_examples():
                f.write(
                    json.dumps(
                        {
                            "task_id": example.task_id,
                            "input": example.input_prompt,
                            "expected_services": example.expected_services,
                            "expected_modules": example.expected_modules,
                            "metadata": example.metadata,
                        }
                    )
                    + "\n"
                )
                count += 1

        return count
