variable "subscription_id" {
  description = "Azure subscription ID."
  type        = string
}

variable "app_name" {
  description = "Short application name used to build resource names (lowercase, no spaces)."
  type        = string
  default     = "tfavmagent"
}

variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "eastus"
}

variable "image_name" {
  description = "Name of the container image (without registry prefix or tag)."
  type        = string
  default     = "tf-avm-agent-web"
}

variable "image_tag" {
  description = "Container image tag to deploy."
  type        = string
  default     = "latest"
}

variable "container_cpu" {
  description = "CPU allocated to the web container (in vCPU cores)."
  type        = number
  default     = 0.5
}

variable "container_memory" {
  description = "Memory allocated to the web container (e.g. '1Gi')."
  type        = string
  default     = "1Gi"
}

variable "min_replicas" {
  description = "Minimum number of container replicas (0 = scale to zero)."
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Maximum number of container replicas."
  type        = number
  default     = 3
}

variable "tags" {
  description = "Additional tags to merge with the default tag set."
  type        = map(string)
  default     = {}
}

# ── API Container App ────────────────────────────────────────────────────────

variable "api_image_name" {
  description = "Name of the MCP backend API container image (without registry prefix or tag)."
  type        = string
  default     = "tf-avm-agent-api"
}

variable "api_container_cpu" {
  description = "CPU allocated to the API container (in vCPU cores)."
  type        = number
  default     = 0.5
}

variable "api_container_memory" {
  description = "Memory allocated to the API container (e.g. '1Gi')."
  type        = string
  default     = "1Gi"
}

# ── Azure OpenAI ─────────────────────────────────────────────────────────────

variable "openai_deployment_name" {
  description = "Name for the Azure OpenAI model deployment."
  type        = string
  default     = "gpt-4o"
}

variable "openai_model_name" {
  description = "OpenAI model name to deploy (e.g. gpt-4o, gpt-4o-mini)."
  type        = string
  default     = "gpt-4o"
}

variable "openai_model_version" {
  description = "Version of the OpenAI model to deploy."
  type        = string
  default     = "2024-11-20"
}

variable "openai_capacity" {
  description = "Tokens-per-minute capacity in thousands (e.g. 30 = 30K TPM)."
  type        = number
  default     = 30
}
