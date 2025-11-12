# Global Outputs
# These outputs are available after terraform apply
# Environment-specific outputs are in environments/*/outputs.tf

output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}
