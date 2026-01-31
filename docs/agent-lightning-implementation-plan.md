# Agent Lightning Implementation Plan for TF-AVM-Agent

## Executive Summary

This document outlines a detailed implementation plan for integrating [Agent Lightning](https://github.com/microsoft/agent-lightning), Microsoft's reinforcement learning (RL) framework for AI agents, into the Terraform AVM Agent. This integration will enable continuous improvement of the agent through training on real-world interactions, improving its ability to:

- Generate accurate Terraform code using Azure Verified Modules (AVM)
- Correctly analyze architecture diagrams and identify Azure services
- Provide relevant module recommendations
- Self-correct errors in generated Terraform configurations

## 1. Background and Motivation

### 1.1 Current TF-AVM-Agent Architecture

The TF-AVM-Agent is built on the Microsoft Agent Framework and provides:

- **Service-Based Generation**: Generates Terraform projects from a list of Azure services
- **Architecture Diagram Analysis**: Identifies Azure services from architecture diagrams
- **Interactive Chat Mode**: Conversational interface for exploring modules and generating code
- **AVM Module Registry**: Built-in knowledge of 100+ Azure Verified Modules

**Current Components:**
```
tf-avm-agent/
├── src/tf_avm_agent/
│   ├── agent.py           # TerraformAVMAgent (ChatAgent-based)
│   ├── cli.py             # CLI interface
│   ├── registry/          # AVM module registry
│   │   └── avm_modules.py # Module definitions and lookup
│   └── tools/             # Agent tools
│       ├── avm_lookup.py  # Module search and info
│       ├── terraform_generator.py  # Code generation
│       └── diagram_analyzer.py     # Image analysis
```

### 1.2 Why Agent Lightning?

Agent Lightning offers several advantages for improving the TF-AVM-Agent:

1. **Zero Code Change Integration**: Minimal modifications to existing agent code
2. **Framework Agnostic**: Works with Microsoft Agent Framework seamlessly
3. **Hierarchical RL Algorithm**: Sophisticated credit assignment for multi-step tasks
4. **Self-Correction Capabilities**: Agents can learn to identify and fix errors
5. **Continuous Improvement**: Models improve from real deployment interactions

### 1.3 Key Benefits for TF-AVM-Agent

| Benefit | Description |
|---------|-------------|
| **Improved Accuracy** | RL training on Terraform validation feedback improves code quality |
| **Better Service Recognition** | Training on diagram analysis results improves service identification |
| **Self-Correction** | Agent learns to validate and fix common Terraform errors |
| **Personalization** | Can be trained on organization-specific patterns and preferences |
| **Continuous Learning** | Ongoing improvement from production usage |

## 2. Agent Lightning Framework Overview

### 2.1 Core Architecture

Agent Lightning uses a training-agent disaggregation architecture:

```
┌──────────────────────────────────────────────────────────────────┐
│                    Agent Lightning Architecture                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐     ┌──────────────────┐    ┌─────────────┐ │
│  │  Agent Runs     │────▶│  LightningStore  │───▶│  Algorithm  │ │
│  │ (TF-AVM-Agent)  │     │  (Spans/Traces)  │    │  (RL/APO)   │ │
│  └─────────────────┘     └──────────────────┘    └─────────────┘ │
│         │                         │                      │        │
│         │                         │                      │        │
│         ▼                         ▼                      ▼        │
│  ┌─────────────────┐     ┌──────────────────┐    ┌─────────────┐ │
│  │   agl.emit_*()  │     │  Task/Resource   │    │   Trainer   │ │
│  │   (Telemetry)   │     │    Management    │    │  (Updates)  │ │
│  └─────────────────┘     └──────────────────┘    └─────────────┘ │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Components

1. **`agl.emit_*()`**: Lightweight telemetry functions to emit events
2. **LightningStore**: Central hub for tasks, resources, and traces
3. **Algorithm**: RL or Automatic Prompt Optimization algorithms
4. **Trainer**: Orchestrates training and model updates

### 2.3 Supported Algorithms

| Algorithm | Use Case | Description |
|-----------|----------|-------------|
| **LightningRL (GRPO)** | General RL | Group Relative Policy Optimization for agent training |
| **Flow-GRPO** | Long-horizon tasks | For sparse-reward, multi-step tasks |
| **Automatic Prompt Optimization (APO)** | Prompt tuning | Optimize system prompts based on feedback |
| **Supervised Fine-tuning (SFT)** | Initial training | Bootstrap from high-quality examples |

## 3. Integration Points Analysis

### 3.1 Agent Workflow as MDP

The TF-AVM-Agent workflow can be modeled as a Markov Decision Process:

```
┌─────────────────────────────────────────────────────────────────────┐
│                TF-AVM-Agent MDP States and Actions                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  State_0: User Request                                               │
│    │                                                                 │
│    ▼ Action: Analyze request / Parse services                        │
│  State_1: Services Identified                                        │
│    │                                                                 │
│    ▼ Action: Lookup AVM modules                                      │
│  State_2: Modules Selected                                           │
│    │                                                                 │
│    ▼ Action: Generate Terraform code                                 │
│  State_3: Code Generated                                             │
│    │                                                                 │
│    ▼ Action: Validate code (terraform validate/fmt)                  │
│  State_4: Validation Result                                          │
│    │                                                                 │
│    ├─▶ Reward: +1.0 if valid, -0.5 if errors                         │
│    │                                                                 │
│    ▼ Action: Self-correct if errors (loop back to State_3)           │
│  State_5: Final Output                                               │
│    │                                                                 │
│    ▼ Terminal Reward: Based on user acceptance/feedback              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Reward Signal Sources

| Reward Source | Signal Type | Description |
|--------------|-------------|-------------|
| **Terraform Validation** | Automatic | `terraform validate` output (syntax, references) |
| **Terraform Format** | Automatic | `terraform fmt -check` (style compliance) |
| **Module Resolution** | Automatic | AVM module exists and version is valid |
| **Plan Success** | Automatic | `terraform plan` executes without errors |
| **User Feedback** | Explicit | User rates output or provides corrections |
| **Apply Success** | Delayed | Deployment succeeds (optional long-term signal) |

### 3.3 Emit Points in TF-AVM-Agent

The following locations require `agl.emit_*()` instrumentation:

```python
# In agent.py - TerraformAVMAgent class

class TerraformAVMAgent:
    async def run_async(self, prompt: str) -> str:
        # EMIT: Start of agent run
        agl.emit_start(task_id=task_id, input=prompt)
        
        # Existing logic...
        response = await self._agent.run(context_prompt)
        
        # EMIT: LLM call completed
        agl.emit_action(action="llm_response", output=response_text)
        
        return response_text
    
    def generate_from_services(self, services, ...):
        # EMIT: Service generation start
        agl.emit_action(action="generate", input={"services": services})
        
        result = generate_terraform_project(...)
        
        # EMIT: Generation complete with validation result
        validation = validate_terraform_syntax(result.files[0].content)
        agl.emit_reward(
            reward=1.0 if validation[0] else -0.5,
            metadata={"validation": validation[1]}
        )
        
        return result
```

## 4. Detailed Implementation Plan

### 4.1 Phase 1: Foundation (Week 1-2)

#### 4.1.1 Install Agent Lightning

```bash
pip install agentlightning
```

Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing dependencies
    "agentlightning>=0.1.0",
]
```

#### 4.1.2 Create Lightning Configuration

Create `src/tf_avm_agent/lightning/config.py`:

```python
"""Agent Lightning configuration for TF-AVM-Agent."""

from agentlightning import LightningConfig, LightningStore

# Default configuration
DEFAULT_CONFIG = LightningConfig(
    # Store configuration
    store_backend="local",  # or "redis", "azure_blob" for production
    store_path="./lightning_store",
    
    # Telemetry settings
    enable_telemetry=True,
    trace_level="full",  # "minimal", "standard", "full"
    
    # Training settings
    algorithm="grpo",  # Group Relative Policy Optimization
    batch_size=32,
    learning_rate=1e-5,
    
    # Reward settings
    reward_normalization=True,
    discount_factor=0.99,
)

def get_lightning_store() -> LightningStore:
    """Get the Lightning store instance."""
    return LightningStore(config=DEFAULT_CONFIG)
```

#### 4.1.3 Create Telemetry Wrapper

Create `src/tf_avm_agent/lightning/telemetry.py`:

```python
"""Telemetry instrumentation for Agent Lightning."""

import functools
from typing import Any, Callable, TypeVar
import agentlightning as agl

F = TypeVar('F', bound=Callable[..., Any])

class TerraformAgentTracer:
    """Tracer for TF-AVM-Agent operations."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._task_id = None
    
    def start_task(self, task_id: str, input_data: dict) -> None:
        """Start tracking a new task."""
        if not self.enabled:
            return
        self._task_id = task_id
        agl.emit_start(task_id=task_id, input=input_data)
    
    def emit_action(
        self,
        action_type: str,
        input_data: dict | None = None,
        output_data: dict | None = None,
    ) -> None:
        """Emit an action event."""
        if not self.enabled:
            return
        agl.emit_action(
            task_id=self._task_id,
            action=action_type,
            input=input_data,
            output=output_data,
        )
    
    def emit_reward(self, reward: float, metadata: dict | None = None) -> None:
        """Emit a reward signal."""
        if not self.enabled:
            return
        agl.emit_reward(
            task_id=self._task_id,
            reward=reward,
            metadata=metadata or {},
        )
    
    def end_task(self, success: bool, output: Any = None) -> None:
        """End the current task."""
        if not self.enabled:
            return
        agl.emit_end(
            task_id=self._task_id,
            success=success,
            output=output,
        )
        self._task_id = None


def trace_tool(tool_name: str) -> Callable[[F], F]:
    """Decorator to trace tool invocations."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_global_tracer()
            tracer.emit_action(
                action_type=f"tool:{tool_name}",
                input_data={"args": str(args), "kwargs": str(kwargs)},
            )
            result = func(*args, **kwargs)
            tracer.emit_action(
                action_type=f"tool:{tool_name}:complete",
                output_data={"result": str(result)[:500]},  # Truncate large outputs
            )
            return result
        return wrapper
    return decorator


# Global tracer instance
_global_tracer: TerraformAgentTracer | None = None

def get_global_tracer() -> TerraformAgentTracer:
    """Get the global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = TerraformAgentTracer()
    return _global_tracer

def set_global_tracer(tracer: TerraformAgentTracer) -> None:
    """Set the global tracer instance."""
    global _global_tracer
    _global_tracer = tracer
```

### 4.2 Phase 2: Agent Instrumentation (Week 2-3)

#### 4.2.1 Modify TerraformAVMAgent

Update `src/tf_avm_agent/agent.py`:

```python
# Add imports
from tf_avm_agent.lightning.telemetry import (
    TerraformAgentTracer,
    get_global_tracer,
)
import uuid

class TerraformAVMAgent:
    def __init__(
        self,
        # ... existing params
        enable_lightning: bool = False,
    ):
        # ... existing init
        self._enable_lightning = enable_lightning
        self._tracer = TerraformAgentTracer(enabled=enable_lightning)
    
    async def run_async(self, prompt: str) -> str:
        task_id = str(uuid.uuid4())
        
        # Start lightning tracking
        self._tracer.start_task(
            task_id=task_id,
            input_data={"prompt": prompt, "services": self._identified_services},
        )
        
        try:
            # ... existing run logic ...
            response = await self._agent.run(context_prompt)
            response_text = response.text if hasattr(response, "text") else str(response)
            
            # Emit LLM response action
            self._tracer.emit_action(
                action_type="llm_response",
                input_data={"prompt_length": len(context_prompt)},
                output_data={"response_length": len(response_text)},
            )
            
            # ... existing post-processing ...
            
            self._tracer.end_task(success=True, output=response_text[:500])
            return response_text
            
        except Exception as e:
            self._tracer.end_task(success=False, output=str(e))
            raise
    
    def generate_from_services(
        self,
        services: list[str],
        project_name: str,
        location: str = "eastus",
        output_dir: str | None = None,
    ) -> TerraformProjectOutput:
        # Emit generation action
        self._tracer.emit_action(
            action_type="generate_from_services",
            input_data={
                "services": services,
                "project_name": project_name,
                "location": location,
            },
        )
        
        result = generate_terraform_project(
            project_name=project_name,
            services=services,
            location=location,
        )
        
        # Validate and emit reward
        self._emit_validation_reward(result)
        
        if output_dir:
            write_terraform_files(output_dir, result)
        
        return result
    
    def _emit_validation_reward(self, result: TerraformProjectOutput) -> None:
        """Emit reward based on Terraform validation."""
        # Get main.tf content for validation
        main_tf = next((f for f in result.files if f.filename == "main.tf"), None)
        if not main_tf:
            self._tracer.emit_reward(reward=-1.0, metadata={"error": "no_main_tf"})
            return
        
        # Validate syntax
        is_valid, message = validate_terraform_syntax(main_tf.content)
        
        # Calculate reward
        reward = 1.0 if is_valid else -0.5
        
        # Check for module resolution
        module_count = main_tf.content.count('module "')
        if module_count == 0:
            reward -= 0.3  # Penalty for no modules
        
        self._tracer.emit_reward(
            reward=reward,
            metadata={
                "validation_passed": is_valid,
                "validation_message": message,
                "module_count": module_count,
                "file_count": len(result.files),
            },
        )
```

#### 4.2.2 Instrument Tools

Update `src/tf_avm_agent/tools/avm_lookup.py`:

```python
from tf_avm_agent.lightning.telemetry import trace_tool

@trace_tool("list_available_avm_modules")
def list_available_avm_modules(
    category: Annotated[str | None, ...] = None,
) -> str:
    # ... existing implementation
    pass

@trace_tool("search_avm_modules")
def search_avm_modules(
    query: Annotated[str, ...],
) -> str:
    # ... existing implementation
    pass

@trace_tool("get_avm_module_info")
def get_avm_module_info(
    service_name: Annotated[str, ...],
    fetch_latest: bool = True,
) -> str:
    # ... existing implementation
    pass
```

### 4.3 Phase 3: Reward Engineering (Week 3-4)

#### 4.3.1 Create Reward Calculator

Create `src/tf_avm_agent/lightning/rewards.py`:

```python
"""Reward calculation for Agent Lightning training."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tf_avm_agent.tools.terraform_generator import (
    TerraformProjectOutput,
    validate_terraform_syntax,
)


@dataclass
class RewardResult:
    """Result of reward calculation."""
    total_reward: float
    components: dict[str, float]
    metadata: dict[str, Any]


class TerraformRewardCalculator:
    """Calculate rewards for Terraform code generation."""
    
    # Reward weights
    WEIGHTS = {
        "syntax_valid": 0.3,
        "format_valid": 0.1,
        "modules_used": 0.2,
        "dependencies_resolved": 0.1,
        "plan_success": 0.2,
        "user_feedback": 0.1,
    }
    
    def calculate_reward(
        self,
        output: TerraformProjectOutput,
        user_feedback: float | None = None,
    ) -> RewardResult:
        """Calculate total reward for generated output."""
        components = {}
        metadata = {}
        
        # 1. Syntax validation reward
        syntax_reward, syntax_meta = self._syntax_reward(output)
        components["syntax_valid"] = syntax_reward
        metadata.update(syntax_meta)
        
        # 2. Format validation reward
        format_reward, format_meta = self._format_reward(output)
        components["format_valid"] = format_reward
        metadata.update(format_meta)
        
        # 3. Module usage reward
        module_reward, module_meta = self._module_reward(output)
        components["modules_used"] = module_reward
        metadata.update(module_meta)
        
        # 4. Dependencies resolved reward
        dep_reward, dep_meta = self._dependency_reward(output)
        components["dependencies_resolved"] = dep_reward
        metadata.update(dep_meta)
        
        # 5. Plan success reward (optional, requires terraform)
        plan_reward, plan_meta = self._plan_reward(output)
        components["plan_success"] = plan_reward
        metadata.update(plan_meta)
        
        # 6. User feedback (if provided)
        if user_feedback is not None:
            components["user_feedback"] = user_feedback
        else:
            components["user_feedback"] = 0.0
        
        # Calculate weighted total
        total_reward = sum(
            components[key] * self.WEIGHTS[key]
            for key in self.WEIGHTS
        )
        
        return RewardResult(
            total_reward=total_reward,
            components=components,
            metadata=metadata,
        )
    
    def _syntax_reward(self, output: TerraformProjectOutput) -> tuple[float, dict]:
        """Calculate syntax validation reward."""
        main_tf = next((f for f in output.files if f.filename == "main.tf"), None)
        if not main_tf:
            return -1.0, {"syntax_error": "no_main_tf"}
        
        is_valid, message = validate_terraform_syntax(main_tf.content)
        return (
            1.0 if is_valid else -0.5,
            {"syntax_valid": is_valid, "syntax_message": message},
        )
    
    def _format_reward(self, output: TerraformProjectOutput) -> tuple[float, dict]:
        """Calculate format compliance reward."""
        # Check if terraform fmt would make changes
        for file in output.files:
            if not file.filename.endswith(".tf"):
                continue
            is_formatted, _ = self._check_terraform_format(file.content)
            if not is_formatted:
                return 0.0, {"format_issues": file.filename}
        return 1.0, {"format_valid": True}
    
    def _check_terraform_format(self, content: str) -> tuple[bool, str]:
        """Check if content is properly formatted."""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.tf', delete=False
            ) as f:
                f.write(content)
                temp_path = f.name
            
            result = subprocess.run(
                ["terraform", "fmt", "-check", temp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            Path(temp_path).unlink()
            return result.returncode == 0, result.stderr
        except Exception as e:
            return True, str(e)  # Assume valid if can't check
    
    def _module_reward(self, output: TerraformProjectOutput) -> tuple[float, dict]:
        """Calculate reward based on AVM module usage."""
        main_tf = next((f for f in output.files if f.filename == "main.tf"), None)
        if not main_tf:
            return 0.0, {"modules_count": 0}
        
        # Count module blocks
        module_count = main_tf.content.count('module "')
        
        # Reward based on module count (normalized)
        reward = min(1.0, module_count / 5.0)  # Max reward at 5+ modules
        
        return reward, {"modules_count": module_count}
    
    def _dependency_reward(self, output: TerraformProjectOutput) -> tuple[float, dict]:
        """Calculate reward for proper dependency handling."""
        main_tf = next((f for f in output.files if f.filename == "main.tf"), None)
        if not main_tf:
            return 0.0, {}
        
        # Check for depends_on usage where appropriate
        has_depends = "depends_on" in main_tf.content
        
        # Check for proper resource group references
        has_rg_ref = "azurerm_resource_group.main" in main_tf.content
        
        reward = 0.5 if has_rg_ref else 0.0
        if has_depends:
            reward += 0.5
        
        return reward, {
            "has_depends_on": has_depends,
            "has_rg_reference": has_rg_ref,
        }
    
    def _plan_reward(self, output: TerraformProjectOutput) -> tuple[float, dict]:
        """Calculate reward based on terraform plan success."""
        # This requires writing files and running terraform plan
        # Skip if terraform is not available
        try:
            import shutil
            if not shutil.which("terraform"):
                return 0.0, {"plan_skipped": "terraform_not_available"}
            
            # For safety, we don't actually run plan in automated training
            # This would be done in a sandboxed environment
            return 0.0, {"plan_skipped": "sandbox_required"}
            
        except Exception as e:
            return 0.0, {"plan_error": str(e)}
```

### 4.4 Phase 4: Training Pipeline (Week 4-5)

#### 4.4.1 Create Training Dataset Generator

Create `src/tf_avm_agent/lightning/dataset.py`:

```python
"""Dataset generation for Agent Lightning training."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from tf_avm_agent.registry.avm_modules import AVM_MODULES


@dataclass
class TrainingExample:
    """A single training example."""
    task_id: str
    input_prompt: str
    expected_services: list[str]
    expected_modules: list[str]
    ground_truth_code: str | None = None
    metadata: dict | None = None


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
            "services": ["kubernetes_cluster", "container_registry", "postgresql_flexible", "redis"],
            "prompt_templates": [
                "Create a microservices platform on Kubernetes",
                "I need AKS with container registry and databases",
                "Generate Terraform for a containerized application architecture",
            ],
        },
        {
            "name": "data_platform",
            "description": "Data analytics platform",
            "services": ["storage_account", "azure_openai", "ai_search", "log_analytics_workspace"],
            "prompt_templates": [
                "Create a data analytics platform with AI capabilities",
                "I need storage, AI, and search for a data application",
                "Generate infrastructure for an AI-powered data platform",
            ],
        },
        {
            "name": "secure_network",
            "description": "Secure network architecture",
            "services": ["virtual_network", "network_security_group", "application_gateway", "firewall"],
            "prompt_templates": [
                "Create a secure network with WAF and firewall",
                "I need a VNet with network security",
                "Generate Terraform for secure Azure networking",
            ],
        },
    ]
    
    def generate_examples(self) -> Iterator[TrainingExample]:
        """Generate training examples from patterns."""
        for pattern in self.ARCHITECTURE_PATTERNS:
            for i, prompt in enumerate(pattern["prompt_templates"]):
                yield TrainingExample(
                    task_id=f"{pattern['name']}_{i}",
                    input_prompt=prompt,
                    expected_services=pattern["services"],
                    expected_modules=pattern["services"],  # Same as services in this case
                    metadata={"pattern": pattern["name"]},
                )
    
    def generate_module_lookup_examples(self) -> Iterator[TrainingExample]:
        """Generate examples for module lookup training."""
        for module in AVM_MODULES.values():
            # Example: "What module should I use for virtual machines?"
            yield TrainingExample(
                task_id=f"lookup_{module.name}",
                input_prompt=f"What AVM module should I use for {module.azure_service}?",
                expected_services=[],
                expected_modules=[module.name],
                metadata={"module": module.name, "category": module.category},
            )
            
            # Also generate for aliases
            for alias in module.aliases[:2]:  # Limit to first 2 aliases
                yield TrainingExample(
                    task_id=f"lookup_{module.name}_{alias}",
                    input_prompt=f"Find the AVM module for {alias}",
                    expected_services=[],
                    expected_modules=[module.name],
                    metadata={"module": module.name, "alias": alias},
                )
    
    def save_to_jsonl(self, path: str) -> int:
        """Save dataset to JSONL file."""
        count = 0
        with open(path, 'w') as f:
            for example in self.generate_examples():
                f.write(json.dumps({
                    "task_id": example.task_id,
                    "input": example.input_prompt,
                    "expected_services": example.expected_services,
                    "expected_modules": example.expected_modules,
                    "metadata": example.metadata,
                }) + "\n")
                count += 1
            
            for example in self.generate_module_lookup_examples():
                f.write(json.dumps({
                    "task_id": example.task_id,
                    "input": example.input_prompt,
                    "expected_services": example.expected_services,
                    "expected_modules": example.expected_modules,
                    "metadata": example.metadata,
                }) + "\n")
                count += 1
        
        return count
```

#### 4.4.2 Create Training Script

Create `src/tf_avm_agent/lightning/train.py`:

```python
"""Training script for Agent Lightning integration."""

import argparse
import json
from pathlib import Path

import agentlightning as agl
from agentlightning import Trainer, TrainingConfig

from tf_avm_agent.agent import TerraformAVMAgent
from tf_avm_agent.lightning.config import DEFAULT_CONFIG, get_lightning_store
from tf_avm_agent.lightning.dataset import TerraformTrainingDataset
from tf_avm_agent.lightning.rewards import TerraformRewardCalculator


def create_training_config(
    model_name: str = "gpt-4",
    batch_size: int = 32,
    epochs: int = 3,
    learning_rate: float = 1e-5,
) -> TrainingConfig:
    """Create training configuration."""
    return TrainingConfig(
        algorithm="grpo",  # Group Relative Policy Optimization
        model_name=model_name,
        batch_size=batch_size,
        epochs=epochs,
        learning_rate=learning_rate,
        
        # RL-specific settings
        reward_normalization=True,
        discount_factor=0.99,
        clip_ratio=0.2,
        
        # Trajectory settings
        max_trajectory_length=10,
        trajectory_level_aggregation=True,
        
        # Checkpointing
        checkpoint_interval=100,
        checkpoint_dir="./checkpoints",
    )


def run_training(
    dataset_path: str,
    output_dir: str,
    config: TrainingConfig,
) -> dict:
    """Run the training loop."""
    # Initialize components
    store = get_lightning_store()
    reward_calculator = TerraformRewardCalculator()
    
    # Load dataset
    examples = []
    with open(dataset_path, 'r') as f:
        for line in f:
            examples.append(json.loads(line))
    
    print(f"Loaded {len(examples)} training examples")
    
    # Create trainer
    trainer = Trainer(
        config=config,
        store=store,
        reward_fn=lambda output: reward_calculator.calculate_reward(output).total_reward,
    )
    
    # Training loop
    metrics = trainer.train(
        examples=examples,
        validation_split=0.1,
    )
    
    # Save final model
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    trainer.save(output_dir)
    
    return metrics


def main():
    """Main entry point for training."""
    parser = argparse.ArgumentParser(description="Train TF-AVM-Agent with Agent Lightning")
    parser.add_argument(
        "--dataset",
        type=str,
        default="./data/training.jsonl",
        help="Path to training dataset",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./models/tf-avm-agent-rl",
        help="Output directory for trained model",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4",
        help="Base model to fine-tune",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Training batch size",
    )
    parser.add_argument(
        "--generate-dataset",
        action="store_true",
        help="Generate training dataset before training",
    )
    
    args = parser.parse_args()
    
    # Generate dataset if requested
    if args.generate_dataset:
        print("Generating training dataset...")
        dataset = TerraformTrainingDataset()
        count = dataset.save_to_jsonl(args.dataset)
        print(f"Generated {count} examples to {args.dataset}")
    
    # Create training config
    config = create_training_config(
        model_name=args.model,
        batch_size=args.batch_size,
        epochs=args.epochs,
    )
    
    # Run training
    print(f"Starting training with {args.model}...")
    metrics = run_training(args.dataset, args.output, config)
    
    print("Training complete!")
    print(f"Final metrics: {metrics}")


if __name__ == "__main__":
    main()
```

### 4.5 Phase 5: Self-Correction Loop (Week 5-6)

#### 4.5.1 Implement Self-Correction Agent

Create `src/tf_avm_agent/lightning/self_correction.py`:

```python
"""Self-correction capabilities for TF-AVM-Agent."""

import re
from dataclasses import dataclass
from typing import Any

from tf_avm_agent.lightning.telemetry import get_global_tracer
from tf_avm_agent.tools.terraform_generator import (
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
    errors_found: list[ValidationError]
    errors_fixed: list[str]
    iterations: int


class TerraformSelfCorrector:
    """Self-correction agent for Terraform code."""
    
    MAX_ITERATIONS = 3
    
    # Common error patterns and fixes
    ERROR_PATTERNS = {
        r"Missing required argument: \"(\w+)\"": "add_missing_argument",
        r"Reference to undefined resource \"(\w+)\"": "fix_resource_reference",
        r"Invalid value for variable \"(\w+)\"": "fix_variable_value",
        r"Module \"(\w+)\" not found": "fix_module_source",
        r"Expected '=' after argument name": "fix_syntax_error",
    }
    
    def __init__(self, agent: Any):
        """Initialize with reference to the agent."""
        self.agent = agent
        self.tracer = get_global_tracer()
    
    async def validate_and_correct(
        self,
        output: TerraformProjectOutput,
    ) -> CorrectionResult:
        """Validate output and attempt self-correction if needed."""
        errors_found = []
        errors_fixed = []
        current_output = output
        
        for iteration in range(self.MAX_ITERATIONS):
            # Validate current output
            validation_errors = self._validate_output(current_output)
            
            if not validation_errors:
                # No errors, we're done
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
                    corrected_output=current_output if iteration > 0 else None,
                    errors_found=errors_found,
                    errors_fixed=errors_fixed,
                    iterations=iteration,
                )
            
            errors_found.extend(validation_errors)
            
            # Emit action for correction attempt
            self.tracer.emit_action(
                action_type="self_correction_attempt",
                input_data={
                    "iteration": iteration,
                    "errors": [e.message for e in validation_errors],
                },
            )
            
            # Attempt to correct errors
            corrected_output, fixed = await self._correct_errors(
                current_output, validation_errors
            )
            
            if corrected_output:
                current_output = corrected_output
                errors_fixed.extend(fixed)
            else:
                # Couldn't fix, break out
                break
        
        # Failed to fully correct
        final_errors = self._validate_output(current_output)
        success = len(final_errors) == 0
        
        self.tracer.emit_reward(
            reward=0.5 if len(errors_fixed) > 0 else -0.5,
            metadata={
                "self_correction": True,
                "iterations": self.MAX_ITERATIONS,
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
            iterations=self.MAX_ITERATIONS,
        )
    
    def _validate_output(self, output: TerraformProjectOutput) -> list[ValidationError]:
        """Validate Terraform output and return errors."""
        errors = []
        
        for file in output.files:
            if not file.filename.endswith(".tf"):
                continue
            
            is_valid, message = validate_terraform_syntax(file.content)
            if not is_valid:
                # Parse error message to extract details
                error = self._parse_error_message(message, file.filename)
                if error:
                    errors.append(error)
        
        return errors
    
    def _parse_error_message(self, message: str, filename: str) -> ValidationError | None:
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
        
        # Generic error if no pattern matches
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
        # Build correction prompt
        error_descriptions = "\n".join(
            f"- {e.file}: {e.message}" for e in errors
        )
        
        correction_prompt = f"""The generated Terraform code has the following errors:

{error_descriptions}

Please fix these errors and regenerate the corrected code. Focus on:
1. Adding any missing required arguments
2. Fixing resource references
3. Correcting syntax errors

Provide the corrected main.tf content.
"""
        
        # Use agent to attempt correction
        try:
            response = await self.agent.run_async(correction_prompt)
            
            # Parse corrected code from response
            corrected_code = self._extract_terraform_code(response)
            if not corrected_code:
                return None, []
            
            # Create new output with corrected code
            new_files = []
            for file in output.files:
                if file.filename == "main.tf":
                    from tf_avm_agent.tools.terraform_generator import GeneratedFile
                    new_files.append(GeneratedFile(
                        filename=file.filename,
                        content=corrected_code,
                    ))
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
        # Look for HCL code blocks
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
```

### 4.6 Phase 6: CLI Integration (Week 6-7)

#### 4.6.1 Add Training Commands to CLI

Update `src/tf_avm_agent/cli.py` to add training commands:

```python
# Add to existing CLI imports
from tf_avm_agent.lightning.config import DEFAULT_CONFIG
from tf_avm_agent.lightning.dataset import TerraformTrainingDataset
from tf_avm_agent.lightning.train import create_training_config, run_training

# Add new command group
@app.command()
def train(
    dataset: str = typer.Option(
        "./data/training.jsonl",
        "--dataset", "-d",
        help="Path to training dataset (JSONL)",
    ),
    output: str = typer.Option(
        "./models/tf-avm-agent-rl",
        "--output", "-o",
        help="Output directory for trained model",
    ),
    epochs: int = typer.Option(
        3,
        "--epochs", "-e",
        help="Number of training epochs",
    ),
    batch_size: int = typer.Option(
        32,
        "--batch-size", "-b",
        help="Training batch size",
    ),
    generate_dataset: bool = typer.Option(
        False,
        "--generate",
        help="Generate training dataset before training",
    ),
):
    """Train the agent using Agent Lightning RL."""
    console = Console()
    
    with console.status("[bold green]Preparing training..."):
        if generate_dataset:
            dataset_gen = TerraformTrainingDataset()
            count = dataset_gen.save_to_jsonl(dataset)
            console.print(f"[green]Generated {count} training examples[/green]")
        
        config = create_training_config(
            batch_size=batch_size,
            epochs=epochs,
        )
    
    console.print("[bold blue]Starting Agent Lightning training...[/bold blue]")
    
    try:
        metrics = run_training(dataset, output, config)
        
        console.print("\n[bold green]Training Complete![/bold green]")
        console.print(f"Model saved to: {output}")
        console.print(f"Final metrics: {metrics}")
        
    except Exception as e:
        console.print(f"[bold red]Training failed: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def evaluate(
    model_path: str = typer.Argument(..., help="Path to trained model"),
    test_file: str = typer.Option(
        None,
        "--test", "-t",
        help="Test dataset file (JSONL)",
    ),
):
    """Evaluate a trained model."""
    console = Console()
    
    # Implementation for model evaluation
    console.print(f"Evaluating model from {model_path}")
    # ... evaluation logic
```

## 5. Deployment and Operations

### 5.1 Production Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Production Deployment                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐     ┌──────────────────┐    ┌────────────────┐ │
│  │   TF-AVM-Agent  │────▶│   Azure Redis    │───▶│ Azure ML       │ │
│  │   (Production)  │     │   (Lightning     │    │ (Training      │ │
│  │                 │     │    Store)        │    │  Compute)      │ │
│  └─────────────────┘     └──────────────────┘    └────────────────┘ │
│         │                         │                      │          │
│         │                         │                      │          │
│         ▼                         ▼                      ▼          │
│  ┌─────────────────┐     ┌──────────────────┐    ┌────────────────┐ │
│  │  Azure OpenAI   │     │  Azure Blob      │    │ Model Registry │ │
│  │  (Inference)    │     │  (Traces/Data)   │    │ (Versions)     │ │
│  └─────────────────┘     └──────────────────┘    └────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Monitoring and Observability

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `agent.reward.mean` | Average reward per generation | < 0.5 |
| `agent.validation.pass_rate` | Terraform validation pass rate | < 90% |
| `agent.correction.attempts` | Self-correction iterations | > 2 avg |
| `agent.latency.p95` | 95th percentile response time | > 30s |
| `training.loss` | Training loss | Increasing trend |

### 5.3 A/B Testing Strategy

```python
# Feature flag for gradual rollout
LIGHTNING_ENABLED = os.getenv("TF_AVM_LIGHTNING_ENABLED", "false") == "true"
LIGHTNING_ROLLOUT_PERCENTAGE = float(os.getenv("TF_AVM_LIGHTNING_ROLLOUT", "0.0"))

def should_use_lightning_model() -> bool:
    """Determine if Lightning-trained model should be used."""
    if not LIGHTNING_ENABLED:
        return False
    return random.random() < LIGHTNING_ROLLOUT_PERCENTAGE
```

## 6. Testing Strategy

### 6.1 Unit Tests

Create `tests/test_lightning_integration.py`:

```python
"""Tests for Agent Lightning integration."""

import pytest
from tf_avm_agent.lightning.telemetry import TerraformAgentTracer
from tf_avm_agent.lightning.rewards import TerraformRewardCalculator, RewardResult
from tf_avm_agent.tools.terraform_generator import TerraformProjectOutput, GeneratedFile


class TestTerraformAgentTracer:
    """Tests for the telemetry tracer."""
    
    def test_tracer_disabled(self):
        """Test tracer when disabled."""
        tracer = TerraformAgentTracer(enabled=False)
        # Should not raise
        tracer.start_task("test", {})
        tracer.emit_action("test", {}, {})
        tracer.emit_reward(1.0)
        tracer.end_task(True)
    
    def test_tracer_enabled(self):
        """Test tracer when enabled."""
        tracer = TerraformAgentTracer(enabled=True)
        tracer.start_task("test-123", {"prompt": "test"})
        assert tracer._task_id == "test-123"


class TestRewardCalculator:
    """Tests for reward calculation."""
    
    @pytest.fixture
    def calculator(self):
        return TerraformRewardCalculator()
    
    @pytest.fixture
    def valid_output(self):
        return TerraformProjectOutput(
            files=[
                GeneratedFile(
                    filename="main.tf",
                    content='''
resource "azurerm_resource_group" "main" {
  name     = "test-rg"
  location = "eastus"
}

module "test-vm" {
  source  = "Azure/avm-res-compute-virtualmachine/azurerm"
  version = "~> 0.0"
  
  depends_on = [azurerm_resource_group.main]
}
''',
                ),
            ],
            summary="Test output",
        )
    
    def test_reward_calculation(self, calculator, valid_output):
        """Test reward calculation for valid output."""
        result = calculator.calculate_reward(valid_output)
        
        assert isinstance(result, RewardResult)
        assert result.total_reward >= 0
        assert "syntax_valid" in result.components
        assert "modules_used" in result.components
    
    def test_reward_no_modules(self, calculator):
        """Test reward calculation with no modules."""
        output = TerraformProjectOutput(
            files=[
                GeneratedFile(filename="main.tf", content="# Empty"),
            ],
            summary="",
        )
        result = calculator.calculate_reward(output)
        assert result.components["modules_used"] == 0
```

### 6.2 Integration Tests

```python
"""Integration tests for Lightning-enabled agent."""

import pytest
from tf_avm_agent.agent import TerraformAVMAgent


@pytest.mark.integration
class TestLightningIntegration:
    """Integration tests for Agent Lightning."""
    
    @pytest.fixture
    def lightning_agent(self):
        return TerraformAVMAgent(enable_lightning=True)
    
    @pytest.mark.asyncio
    async def test_generation_with_tracing(self, lightning_agent):
        """Test that generation emits proper traces."""
        result = lightning_agent.generate_from_services(
            services=["virtual_machine"],
            project_name="test",
        )
        
        assert result is not None
        assert len(result.files) > 0
        # Verify tracer recorded events (would check store in real test)
    
    @pytest.mark.asyncio
    async def test_self_correction(self, lightning_agent):
        """Test self-correction capabilities."""
        # This would test the self-correction loop
        pass
```

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Training instability** | Model degradation | Implement checkpointing, validation holdout |
| **Reward hacking** | Agent gaming metrics | Multi-signal rewards, human oversight |
| **Increased latency** | User experience | Async telemetry, optimize hot paths |
| **Data privacy** | User data in training | Anonymization, opt-in telemetry |
| **Version conflicts** | Dependency issues | Pin versions, thorough testing |

### 7.1 Implementation Notes

The following considerations should be addressed during the actual implementation:

1. **Temporary File Cleanup**: Ensure all temporary files created during validation are properly cleaned up using `try-finally` blocks or context managers to prevent resource leaks.

2. **Sensitive Data Handling**: Implement proper filtering and sanitization in telemetry to avoid logging sensitive data (API keys, credentials, connection strings). Consider:
   - A blocklist of sensitive parameter names
   - Redaction of values matching credential patterns
   - Opt-in verbose logging with explicit consent

3. **Async Function Support**: The `trace_tool` decorator should support both sync and async functions. Use `asyncio.iscoroutinefunction()` to detect and wrap async functions appropriately.

4. **Magic Numbers**: Extract configurable constants for:
   - Module count reward threshold (currently 5.0)
   - Maximum self-correction iterations
   - Truncation lengths for outputs

5. **Terraform Binary Check**: Create a shared utility function to check for terraform availability and cache the result to avoid repeated subprocess calls.

6. **A/B Testing Determinism**: Use deterministic hashing (e.g., hash of user ID or session ID) for A/B rollout assignment to ensure consistent user experience across requests.

## 8. Success Metrics

| Metric | Baseline | Target (3 months) | Target (6 months) |
|--------|----------|-------------------|-------------------|
| Terraform validation pass rate | 85% | 95% | 98% |
| Self-correction success rate | N/A | 70% | 85% |
| Average response time | 15s | 12s | 10s |
| User satisfaction score | 3.5/5 | 4.0/5 | 4.5/5 |
| Module recommendation accuracy | 80% | 90% | 95% |

## 9. Timeline Summary

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Foundation | 2 weeks | Lightning installed, config, telemetry wrapper |
| Phase 2: Instrumentation | 1-2 weeks | Agent and tools instrumented |
| Phase 3: Rewards | 1 week | Reward calculator, validation integration |
| Phase 4: Training | 1-2 weeks | Dataset, training pipeline, first model |
| Phase 5: Self-Correction | 1-2 weeks | Self-correction loop, error patterns |
| Phase 6: CLI/Production | 1-2 weeks | CLI commands, monitoring, deployment |
| **Total** | **8-11 weeks** | **Full Agent Lightning integration** |

## 10. References

- [Agent Lightning GitHub Repository](https://github.com/microsoft/agent-lightning)
- [Agent Lightning Documentation](https://microsoft.github.io/agent-lightning/)
- [arXiv Paper: Agent Lightning: Train ANY AI Agents with Reinforcement Learning](https://arxiv.org/abs/2508.03680)
- [Microsoft Research Blog: Agent Lightning](https://www.microsoft.com/en-us/research/blog/agent-lightning-adding-reinforcement-learning-to-ai-agents-without-code-rewrites/)
- [Medium: Training AI Agents to Write and Self-correct SQL with RL](https://medium.com/@yugez/training-ai-agents-to-write-and-self-correct-sql-with-reinforcement-learning-571ed31281ad)
- [Azure Verified Modules](https://aka.ms/AVM)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)

## Appendix A: Example Training Data Format

```json
{
  "task_id": "web_app_0",
  "input": "Create a web application with a SQL database",
  "expected_services": ["app_service", "sql_database", "key_vault"],
  "expected_modules": ["app_service", "sql_database", "key_vault"],
  "metadata": {"pattern": "web_app"}
}
```

## Appendix B: Configuration Options

```python
# Full configuration reference
LIGHTNING_CONFIG = {
    # Store settings
    "store_backend": "redis",  # "local", "redis", "azure_blob"
    "store_connection": "redis://localhost:6379",
    
    # Telemetry settings
    "enable_telemetry": True,
    "trace_level": "full",  # "minimal", "standard", "full"
    "sampling_rate": 1.0,   # 0.0-1.0
    
    # Training settings
    "algorithm": "grpo",
    "batch_size": 32,
    "learning_rate": 1e-5,
    "epochs": 3,
    
    # RL settings
    "reward_normalization": True,
    "discount_factor": 0.99,
    "clip_ratio": 0.2,
    "entropy_coefficient": 0.01,
    
    # Self-correction settings
    "max_correction_iterations": 3,
    "correction_temperature": 0.7,
}
```
