# Cloud SQL PostgreSQL Module

resource "random_id" "db_name_suffix" {
  byte_length = 4
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  name             = "${var.instance_name}-${random_id.db_name_suffix.hex}"
  database_version = var.postgres_version
  region           = var.region
  project          = var.project_id

  settings {
    tier              = var.tier
    availability_type = var.high_availability ? "REGIONAL" : "ZONAL"
    disk_size         = var.disk_size
    disk_type         = var.disk_type
    disk_autoresize   = var.disk_autoresize
    disk_autoresize_limit = var.disk_autoresize_limit

    backup_configuration {
      enabled                        = var.backup_enabled
      start_time                     = var.backup_start_time
      point_in_time_recovery_enabled = var.point_in_time_recovery
      transaction_log_retention_days = var.transaction_log_retention_days
      backup_retention_settings {
        retained_backups = var.retention_days
      }
    }

    ip_configuration {
      ipv4_enabled    = var.enable_public_ip
      private_network = var.network_id
      require_ssl     = true

      dynamic "authorized_networks" {
        for_each = var.authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.cidr
        }
      }
    }

    database_flags {
      name  = "max_connections"
      value = var.max_connections
    }

    database_flags {
      name  = "shared_buffers"
      value = var.shared_buffers
    }

    insights_config {
      query_insights_enabled  = var.enable_query_insights
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
    }

    maintenance_window {
      day          = var.maintenance_window_day
      hour         = var.maintenance_window_hour
      update_track = var.maintenance_update_track
    }

    user_labels = merge(
      var.labels,
      {
        environment = var.environment
        component   = "database"
      }
    )
  }

  deletion_protection = var.deletion_protection

  lifecycle {
    ignore_changes = [
      settings[0].disk_size  # Allow auto-resize
    ]
  }

  depends_on = [var.network_depends_on]
}

# Database
resource "google_sql_database" "default" {
  name     = var.database_name
  instance = google_sql_database_instance.main.name
  project  = var.project_id
}

# User
resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "google_sql_user" "default" {
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  password = var.database_password != "" ? var.database_password : random_password.db_password.result
  project  = var.project_id
}

# Read Replicas
resource "google_sql_database_instance" "read_replica" {
  count = var.read_replicas

  name                 = "${var.instance_name}-replica-${count.index + 1}"
  database_version     = var.postgres_version
  region               = var.replica_region != "" ? var.replica_region : var.region
  master_instance_name = google_sql_database_instance.main.name
  project              = var.project_id

  replica_configuration {
    failover_target = var.replica_failover_target
  }

  settings {
    tier              = var.replica_tier != "" ? var.replica_tier : var.tier
    availability_type = "ZONAL"
    disk_size         = var.disk_size
    disk_type         = var.disk_type

    ip_configuration {
      ipv4_enabled    = var.enable_public_ip
      private_network = var.network_id
      require_ssl     = true
    }

    user_labels = merge(
      var.labels,
      {
        environment = var.environment
        component   = "database"
        replica     = "true"
      }
    )
  }

  deletion_protection = var.deletion_protection
}
