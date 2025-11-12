# Cloud SQL PostgreSQL Variables

variable "project_id" { type = string }
variable "region" { type = string }
variable "instance_name" { type = string }
variable "postgres_version" { type = string; default = "POSTGRES_15" }
variable "environment" { type = string }

# Instance Configuration
variable "tier" { type = string; default = "db-f1-micro" }
variable "disk_size" { type = number; default = 20 }
variable "disk_type" { type = string; default = "PD_SSD" }
variable "disk_autoresize" { type = bool; default = true }
variable "disk_autoresize_limit" { type = number; default = 0 }
variable "deletion_protection" { type = bool; default = true }

# HA Configuration
variable "high_availability" { type = bool; default = false }
variable "read_replicas" { type = number; default = 0 }
variable "replica_region" { type = string; default = "" }
variable "replica_tier" { type = string; default = "" }
variable "replica_failover_target" { type = bool; default = false }

# Backup Configuration
variable "backup_enabled" { type = bool; default = true }
variable "backup_start_time" { type = string; default = "03:00" }
variable "retention_days" { type = number; default = 7 }
variable "point_in_time_recovery" { type = bool; default = false }
variable "transaction_log_retention_days" { type = number; default = 7 }

# Network Configuration
variable "network_id" { type = string }
variable "enable_public_ip" { type = bool; default = false }
variable "authorized_networks" {
  type = list(object({ name = string, cidr = string }))
  default = []
}

# Database Configuration
variable "database_name" { type = string; default = "octollm" }
variable "database_user" { type = string; default = "octollm" }
variable "database_password" { type = string; default = ""; sensitive = true }
variable "max_connections" { type = string; default = "100" }
variable "shared_buffers" { type = string; default = "256MB" }

# Monitoring
variable "enable_query_insights" { type = bool; default = true }

# Maintenance
variable "maintenance_window_day" { type = number; default = 7 }  # Sunday
variable "maintenance_window_hour" { type = number; default = 3 }  # 3 AM UTC
variable "maintenance_update_track" { type = string; default = "stable" }

variable "labels" { type = map(string); default = {} }
variable "network_depends_on" { type = any; default = null }
