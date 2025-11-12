# GKE Module Outputs

output "cluster_id" {
  description = "The GKE cluster ID"
  value       = google_container_cluster.primary.id
}

output "cluster_name" {
  description = "The GKE cluster name"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "The IP address of the Kubernetes API server"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "Base64 encoded public certificate for cluster CA"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "cluster_location" {
  description = "The location (region or zone) of the cluster"
  value       = google_container_cluster.primary.location
}

output "cluster_master_version" {
  description = "The current Kubernetes master version"
  value       = google_container_cluster.primary.master_version
}

output "node_pools" {
  description = "Map of node pool names to their configurations"
  value = {
    for k, v in google_container_node_pool.primary_nodes : k => {
      name         = v.name
      node_count   = v.node_count
      machine_type = v.node_config[0].machine_type
    }
  }
}

output "node_service_account" {
  description = "Service account used by GKE nodes"
  value       = var.node_service_account != "" ? var.node_service_account : google_service_account.node_sa[0].email
}

output "workload_identity_pool" {
  description = "Workload Identity pool for the cluster"
  value       = "${var.project_id}.svc.id.goog"
}

# kubectl configuration command
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${var.region} --project ${var.project_id}"
}
