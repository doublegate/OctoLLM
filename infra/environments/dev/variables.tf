# Development Environment Variables

variable "project_id" {
  description = "GCP project ID for development"
  type        = string
  default     = "octollm-dev"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}
