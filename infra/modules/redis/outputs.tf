# Redis Outputs
output "instance_id" { value = google_redis_instance.main.id }
output "host" { value = google_redis_instance.main.host }
output "port" { value = google_redis_instance.main.port }
output "auth_string" { value = google_redis_instance.main.auth_string; sensitive = true }
output "connection_string" {
  value = "redis://:${google_redis_instance.main.auth_string}@${google_redis_instance.main.host}:${google_redis_instance.main.port}"
  sensitive = true
}
output "current_location_id" { value = google_redis_instance.main.current_location_id }
