"""
TF AVM Agent - An AI agent that generates Terraform code using Azure Verified Modules.

This agent can accept a list of Azure services or an architecture diagram as input
and generate a complete Terraform project using Azure Verified Modules (AVM).
"""

from tf_avm_agent.agent import PromptMode, TerraformAVMAgent

__version__ = "0.1.0"
__all__ = ["TerraformAVMAgent", "PromptMode"]
