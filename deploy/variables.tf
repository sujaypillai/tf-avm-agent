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

variable "backend_url" {
  description = "URL of the tf-avm-agent backend API (used by nginx to proxy /api/ requests). Example: 'backend-svc:8000'."
  type        = string
  default     = "localhost:8000"
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
