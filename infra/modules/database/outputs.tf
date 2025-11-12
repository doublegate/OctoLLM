# Database Outputs

output "instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.main.name
}

output "instance_connection_name" {
  description = "Connection name for Cloud SQL Proxy"
  value       = google_sql_database_instance.main.connection_name
}

output "private_ip_address" {
  description = "Private IP address"
  value       = google_sql_database_instance.main.private_ip_address
}

output "public_ip_address" {
  description = "Public IP address"
  value       = google_sql_database_instance.main.public_ip_address
}

output "database_name" {
  value = google_sql_database.default.name
}

output "database_user" {
  value = google_sql_user.default.name
}

output "database_password" {
  value     = google_sql_user.default.password
  sensitive = true
}

output "replica_connection_names" {
  value = [for r in google_sql_database_instance.read_replica : r.connection_name]
}
