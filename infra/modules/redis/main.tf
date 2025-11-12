# Memorystore for Redis Module

resource "google_redis_instance" "main" {
  name           = var.instance_name
  project        = var.project_id
  region         = var.region
  tier           = var.tier
  memory_size_gb = var.memory_size_gb
  redis_version  = var.redis_version

  authorized_network = var.network_id
  connect_mode       = var.connect_mode

  redis_configs = var.redis_configs

  display_name = "${var.instance_name} (${var.environment})"

  labels = merge(
    var.labels,
    {
      environment = var.environment
      component   = "cache"
    }
  )

  maintenance_policy {
    weekly_maintenance_window {
      day = var.maintenance_day
      start_time {
        hours   = var.maintenance_hour
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }

  persistence_config {
    persistence_mode    = var.persistence_mode
    rdb_snapshot_period = var.rdb_snapshot_period
  }

  transit_encryption_mode = var.transit_encryption_mode
  auth_enabled           = var.auth_enabled

  read_replicas_mode  = var.read_replicas_mode
  replica_count       = var.replica_count

  lifecycle {
    prevent_destroy = var.prevent_destroy
  }
}
