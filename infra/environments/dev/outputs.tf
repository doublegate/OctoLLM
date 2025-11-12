# Development Environment Outputs

output "gke_cluster_name" {
  value = module.gke.cluster_name
}

output "gke_cluster_endpoint" {
  value     = module.gke.cluster_endpoint
  sensitive = true
}

output "kubectl_config_command" {
  value = module.gke.kubectl_config_command
}

output "database_instance_name" {
  value = module.database.instance_name
}

output "database_connection_name" {
  value = module.database.instance_connection_name
}

output "database_private_ip" {
  value = module.database.private_ip_address
}

output "redis_host" {
  value = module.redis.host
}

output "redis_port" {
  value = module.redis.port
}

output "storage_buckets" {
  value = module.storage.bucket_names
}

output "network_name" {
  value = module.networking.network_name
}
